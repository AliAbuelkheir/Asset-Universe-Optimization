"""Set-based (permutation-invariant) Actor-Critic policy for portfolio RL.

Pairs with `feature_extractor_setbased.SetBasedFeatureExtractor`.

Architecture:
    - POLICY: per-asset shared MLP applied to (b, N, hidden_dim) — outputs N action means
    - VALUE: pooled features (b, 256) → MLP → scalar value
    - LOG_STD: single scalar nn.Parameter, broadcast to N at distribution time

The scalar log_std design makes the policy fully N-invariant: weights trained on N=10
deploy unchanged on any N (no shape mismatch on the Gaussian distribution's std).
"""

from typing import Tuple

import gymnasium as gym
import torch
import torch.nn as nn

from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.distributions import DiagGaussianDistribution


class _IdentityMlpExtractor(nn.Module):
    """Pass-through MLP extractor to satisfy SB3's _build_mlp_extractor contract.

    SB3 expects this attribute to expose latent_dim_pi and latent_dim_vf.
    Our actual policy/value heads override forward() so this is just a stub.
    """

    def __init__(self, dim: int):
        super().__init__()
        self.latent_dim_pi = dim
        self.latent_dim_vf = dim

    def forward(self, features: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        return features, features

    def forward_actor(self, features: torch.Tensor) -> torch.Tensor:
        return features

    def forward_critic(self, features: torch.Tensor) -> torch.Tensor:
        return features


class SetBasedActorCriticPolicy(ActorCriticPolicy):
    """N-invariant Actor-Critic.

    Action: shared per-asset MLP → N means; scalar log_std broadcast to N.
    Value:  pooled features → MLP → scalar V(s).

    The features extractor must be SetBasedFeatureExtractor, which stashes
    `_per_asset_cache` (b, n, hidden_dim) on each forward pass for us to read.
    """

    def __init__(
        self,
        observation_space: gym.spaces.Space,
        action_space: gym.spaces.Space,
        lr_schedule,
        hidden_dim: int = 64,
        head_dim: int = 64,
        **kwargs,
    ):
        # Cache these so _build() can read them. Have to set BEFORE super() because
        # super() calls _build() which uses them.
        self._setbased_hidden_dim = hidden_dim
        self._setbased_head_dim = head_dim
        super().__init__(observation_space, action_space, lr_schedule, **kwargs)

    def _build_mlp_extractor(self) -> None:
        """Provide a pass-through so SB3's _build() contract is satisfied.
        The features_dim of our extractor (256) is the latent dim for both heads."""
        self.mlp_extractor = _IdentityMlpExtractor(self.features_dim)

    def _build(self, lr_schedule) -> None:
        """Build N-invariant action + value heads + scalar log_std."""
        self._build_mlp_extractor()

        h = self._setbased_hidden_dim
        head = self._setbased_head_dim

        # POLICY: shared per-asset MLP applied to (b, N, h) → (b, N, 1) → (b, N)
        self.policy_per_asset = nn.Sequential(
            nn.Linear(h, head),
            nn.Tanh(),
            nn.Linear(head, 1),
        )

        # VALUE: pooled features (b, features_dim) → MLP → (b, 1)
        self.value_pooled = nn.Sequential(
            nn.Linear(self.features_dim, head),
            nn.Tanh(),
            nn.Linear(head, head),
            nn.Tanh(),
            nn.Linear(head, 1),
        )

        # LOG_STD: a single scalar, broadcast to N at distribution-build time.
        if isinstance(self.action_dist, DiagGaussianDistribution):
            self.log_std = nn.Parameter(
                torch.tensor(self.log_std_init, dtype=torch.float32),
                requires_grad=True,
            )

        # SB3 expects these attributes (we don't use them but they need to exist)
        self.action_net = nn.Identity()
        self.value_net = nn.Identity()

        # Standard SB3 weight init
        for module in [self.policy_per_asset, self.value_pooled]:
            module.apply(lambda m: self.init_weights(m, gain=2 ** 0.5))

        self.optimizer = self.optimizer_class(
            self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs
        )

    # ───── helpers ─────

    def _action_means(self, per_asset_features: torch.Tensor) -> torch.Tensor:
        """(b, N, h) → (b, N) action means."""
        return self.policy_per_asset(per_asset_features).squeeze(-1)

    def _log_std_broadcast(self, n_assets: int) -> torch.Tensor:
        """Broadcast scalar log_std to (n_assets,) for the Gaussian distribution."""
        return self.log_std.expand(n_assets)

    def _values(self, pooled_features: torch.Tensor) -> torch.Tensor:
        return self.value_pooled(pooled_features)

    # ───── SB3 contract methods ─────

    def forward(self, obs: torch.Tensor, deterministic: bool = False):
        pooled = self.extract_features(obs)
        per_asset = self.features_extractor._per_asset_cache
        mean = self._action_means(per_asset)
        values = self._values(pooled)
        log_std = self._log_std_broadcast(mean.shape[1])

        dist = self.action_dist.proba_distribution(mean, log_std)
        actions = dist.get_actions(deterministic=deterministic)
        log_prob = dist.log_prob(actions)
        actions = actions.reshape((-1, *self.action_space.shape))
        return actions, values, log_prob

    def evaluate_actions(self, obs: torch.Tensor, actions: torch.Tensor):
        pooled = self.extract_features(obs)
        per_asset = self.features_extractor._per_asset_cache
        mean = self._action_means(per_asset)
        values = self._values(pooled)
        log_std = self._log_std_broadcast(mean.shape[1])

        dist = self.action_dist.proba_distribution(mean, log_std)
        log_prob = dist.log_prob(actions)
        entropy = dist.entropy()
        return values, log_prob, entropy

    def _predict(self, obs: torch.Tensor, deterministic: bool = False) -> torch.Tensor:
        pooled = self.extract_features(obs)
        per_asset = self.features_extractor._per_asset_cache
        mean = self._action_means(per_asset)
        log_std = self._log_std_broadcast(mean.shape[1])

        dist = self.action_dist.proba_distribution(mean, log_std)
        return dist.get_actions(deterministic=deterministic)

    def predict_values(self, obs: torch.Tensor) -> torch.Tensor:
        pooled = self.extract_features(obs)
        return self._values(pooled)
