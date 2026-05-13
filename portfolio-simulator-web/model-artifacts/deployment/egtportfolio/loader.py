"""Load set-based PPO models for inference.

Handles the SB3 quirk that `PPO.load(env=...)` strictly checks observation/action
space shapes against the saved model — which breaks for N-invariant models when
deployment N != training N. We load policy weights with `strict=False` and skip
shape-mismatched parameters (none, since scalar log_std and shared MLPs are
size-agnostic, but the safeguard catches future changes).
"""

import io
import sys
import types
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import torch

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from .env_min import PortfolioEnvMin
from . import feature_extractor_setbased, policy_setbased
from .feature_extractor_setbased import SetBasedFeatureExtractor
from .policy_setbased import SetBasedActorCriticPolicy


# ── src.* module shim ────────────────────────────────────────────────
# Models were trained from the parent repo where the classes live in
# `src.feature_extractor_setbased` and `src.policy_setbased`. When loading
# in deployment, the cloudpickle deserialization needs those import paths
# to resolve. We register our bundled copies under the `src.*` namespace
# so loading just works.
def _install_src_shim():
    if 'src' not in sys.modules:
        sys.modules['src'] = types.ModuleType('src')
    sys.modules['src.feature_extractor_setbased'] = feature_extractor_setbased
    sys.modules['src.policy_setbased'] = policy_setbased


_install_src_shim()


# Tier-specific weight caps (matches src/config.py:get_config tier_overrides)
TIER_MAX_WEIGHT = {'low': 0.30, 'medium': 0.20, 'high': 0.15}
TIER_MIN_WEIGHT = {'low': 0.0, 'medium': 0.01, 'high': 0.01}
TIER_DIRICHLET_PRIOR = {'low': 0.2, 'medium': 0.5, 'high': 0.5}


@dataclass
class ModelBundle:
    """A fully-loaded model + its inference environment + canonical constraints."""
    tier: Literal['low', 'medium', 'high']
    model: PPO
    vecnormalize: VecNormalize
    max_weight: float
    min_weight: float
    dirichlet_prior: float
    lookback_window: int = 63


def _make_dummy_env(n_assets: int, n_features: int = 22, lookback: int = 63,
                    max_weight: float = 0.25, min_weight: float = 0.0,
                    dirichlet_prior: float = 0.5):
    """Build a tiny env with the right observation/action shapes so we can attach VecNormalize."""
    T = lookback + 2  # enough timesteps for one reset+step
    feature_tensor = np.zeros((T, n_assets, n_features), dtype=np.float32)
    active_matrix = np.ones((T, n_assets), dtype=np.float32)
    simple_returns = np.zeros((T, n_assets), dtype=np.float64)
    return DummyVecEnv([lambda: PortfolioEnvMin(
        feature_tensor=feature_tensor,
        active_matrix=active_matrix,
        simple_returns=simple_returns,
        max_weight=max_weight,
        min_weight=min_weight,
        dirichlet_prior=dirichlet_prior,
        lookback_window=lookback,
    )])


def load_model(
    tier: Literal['low', 'medium', 'high'],
    n_assets: int,
    model_dir: Path | None = None,
) -> ModelBundle:
    """Load a set-based model for a given tier and target n_assets.

    Args:
        tier: which tier model to load ('low', 'medium', 'high')
        n_assets: how many assets the deployment universe has
        model_dir: directory containing models/; if None, looks for
                   `<package>/../models/`.

    Returns:
        A ModelBundle ready for inference.
    """
    if model_dir is None:
        # Package is at deployment/egtportfolio/; models at deployment/models/
        model_dir = Path(__file__).resolve().parent.parent / 'models'
    else:
        model_dir = Path(model_dir)

    model_path = model_dir / f'ppo_{tier}_seed42_setbased'
    vecnorm_path = model_dir / f'vecnorm_{tier}_seed42_setbased.pkl'

    if not (model_path.with_suffix('.zip')).exists():
        raise FileNotFoundError(
            f"Model not found: {model_path}.zip. "
            "Ensure the deployment package's models/ folder contains "
            "the set-based models for the requested tier."
        )

    max_w = TIER_MAX_WEIGHT[tier]
    min_w = TIER_MIN_WEIGHT[tier]
    prior = TIER_DIRICHLET_PRIOR[tier]

    # Build a dummy env with the deployment-time n_assets so PPO.load can size
    # the policy's spaces correctly.
    env = _make_dummy_env(
        n_assets=n_assets, n_features=22, lookback=63,
        max_weight=max_w, min_weight=min_w, dirichlet_prior=prior,
    )

    # Attach VecNormalize stats — these are learned at training time.
    # VecNormalize's stats are running mean/var over the FLATTENED observation,
    # which has shape (lookback, n_assets, 23). When deployment n_assets differs
    # from training, the saved stats won't match. We load with `training=False`
    # so VecNormalize doesn't update, and accept that normalization is approximate
    # for out-of-distribution N. For N == training N, this is exact.
    try:
        env = VecNormalize.load(str(vecnorm_path), env)
        env.training = False
        env.norm_reward = False
    except Exception as e:
        # If shape mismatch on VecNorm stats, fall back to identity (no normalization).
        # The model was trained with VecNormalize so this is suboptimal, but won't crash.
        print(f"  WARNING: VecNormalize.load failed ({e}); using identity normalization.")
        env = VecNormalize(env, training=False, norm_reward=False, norm_obs=False)

    # Build a fresh PPO shell and load only policy.pth from the zip. This avoids
    # cloudpickle deserialization of training-time schedules such as FloatSchedule,
    # which can differ across SB3 versions and has caused Linux deployment crashes.
    model = PPO(
        SetBasedActorCriticPolicy,
        env,
        policy_kwargs=dict(
            features_extractor_class=SetBasedFeatureExtractor,
            features_extractor_kwargs=dict(features_dim=256, hidden_dim=64),
            hidden_dim=64, head_dim=64,
            normalize_images=False,
        ),
        verbose=0,
    )
    with zipfile.ZipFile(str(model_path) + '.zip') as zf:
        with zf.open('policy.pth') as f:
            saved_state = torch.load(io.BytesIO(f.read()), weights_only=False, map_location='cpu')
    fresh_state = model.policy.state_dict()
    filtered = {k: v for k, v in saved_state.items()
                if k in fresh_state and fresh_state[k].shape == v.shape}
    model.policy.load_state_dict(filtered, strict=False)

    return ModelBundle(
        tier=tier,
        model=model,
        vecnormalize=env,
        max_weight=max_w,
        min_weight=min_w,
        dirichlet_prior=prior,
    )
