"""High-level predict() entry point.

Workflow:
  1. Parse + validate input (raw OHLCV or pre-computed features)
  2. Compute the 18 technical features if needed
  3. Attach 4 macro features (broadcast from bundled Excel)
  4. Cross-sectional z-score
  5. Build the env, reset, step the model up to target_month
  6. Capture the predicted weights and return them
"""

from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

from .features import (
    RL_FEATURE_NAMES,
    compute_features_for_universe,
    cross_sectional_zscore,
)
from .macro import build_macro_tensor
from .env_min import PortfolioEnvMin
from .loader import load_model, ModelBundle
from .schemas import (
    AssetTimeSeries,
    AssetWeight,
    ConstraintsOverride,
    InferenceRequest,
    InferenceResponse,
)


MACRO_FEATURE_NAMES = [
    'headline_inflation_mom',
    'core_inflation_mom',
    'deposit_rate_short',
    'lending_rate_corporate',
]


# ── input normalization ────────────────────────────────────────────────

def _asset_series_to_df(asset_ts: AssetTimeSeries) -> pd.DataFrame:
    """Turn an AssetTimeSeries (lists) into a Date-indexed DataFrame."""
    dates = pd.to_datetime(asset_ts.dates)
    close = pd.Series(asset_ts.close, index=dates).astype(float)
    df = pd.DataFrame({'Close': close})
    df['Open'] = pd.Series(asset_ts.open, index=dates) if asset_ts.open is not None else close
    df['High'] = pd.Series(asset_ts.high, index=dates) if asset_ts.high is not None else close
    df['Low'] = pd.Series(asset_ts.low, index=dates) if asset_ts.low is not None else close
    df['Volume'] = (pd.Series(asset_ts.volume, index=dates).astype(float)
                    if asset_ts.volume is not None else 0.0)
    return df.sort_index()


def _detect_input_kind(asset_data) -> Literal['raw_ohlcv', 'precomputed_features']:
    """Auto-detect whether the input is raw OHLCV or has pre-computed features.

    Heuristic: if every asset's DataFrame has all 18 RL feature columns, it's
    pre-computed. Otherwise it's raw OHLCV.
    """
    if isinstance(asset_data, list):  # list of AssetTimeSeries (always raw)
        return 'raw_ohlcv'
    if isinstance(asset_data, dict):  # in-memory DataFrames
        return 'precomputed_features'
    if isinstance(asset_data, str):  # path to CSV; need to peek
        df = pd.read_csv(asset_data, nrows=1)
        if all(f in df.columns for f in RL_FEATURE_NAMES):
            return 'precomputed_features'
        return 'raw_ohlcv'
    raise ValueError(f"Unsupported asset_data type: {type(asset_data)}")


# ── feature tensor builder ─────────────────────────────────────────────

def _build_feature_tensor(
    asset_data: list[AssetTimeSeries] | str,
    target_month: str,
    egx30_ohlcv: AssetTimeSeries | None,
    macro_dir: Path,
    input_kind: str,
) -> tuple[np.ndarray, np.ndarray, list[str], list[pd.Timestamp]]:
    """Return (feature_tensor, active_matrix, asset_names_input_order, dates).

    feature_tensor: (T, N, 22) float32, normalized
    active_matrix: (T, N) float32 (we assume all assets active throughout)
    asset_names_input_order: the asset names IN THE ORDER THEY WERE PROVIDED
    dates: list of business days from earliest data to (last day of target_month)
    """
    target_month_end = pd.Timestamp(target_month + '-01') + pd.offsets.MonthEnd(0)

    # 1. Turn each asset's input into a Date-indexed DataFrame
    if isinstance(asset_data, list):
        asset_dfs = {a.asset: _asset_series_to_df(a) for a in asset_data}
        asset_names = [a.asset for a in asset_data]
    elif isinstance(asset_data, dict):
        asset_dfs = {
            str(asset): df.copy().sort_index()
            for asset, df in asset_data.items()
        }
        asset_names = [str(asset) for asset in asset_data.keys()]
    else:
        # Pre-computed CSV path
        full_df = pd.read_csv(asset_data, parse_dates=['Date'])
        asset_dfs = {a: g.set_index('Date').sort_index()
                     for a, g in full_df.groupby('Asset')}
        asset_names = list(asset_dfs.keys())

    # 2. Compute features if needed
    if input_kind == 'raw_ohlcv':
        egx30_df = _asset_series_to_df(egx30_ohlcv) if egx30_ohlcv else None
        asset_dfs = compute_features_for_universe(asset_dfs, egx30_ohlcv=egx30_df)

    # 3. Union of all dates, filtered to <= target_month_end
    all_dates = sorted(set().union(*[df.index for df in asset_dfs.values()]))
    all_dates = [d for d in all_dates if d <= target_month_end]

    # 4. Build the (T, N, 18) per-asset feature tensor in input order
    n_dates = len(all_dates)
    n_assets = len(asset_names)
    n_rl = len(RL_FEATURE_NAMES)
    feature_tensor = np.zeros((n_dates, n_assets, n_rl), dtype=np.float32)
    active_matrix = np.zeros((n_dates, n_assets), dtype=np.float32)

    for j, asset in enumerate(asset_names):
        df = asset_dfs[asset]
        # Reindex to the universal date axis
        df_re = df.reindex(all_dates)
        for i, feat in enumerate(RL_FEATURE_NAMES):
            if feat in df_re.columns:
                feature_tensor[:, j, i] = df_re[feat].fillna(0.0).values.astype(np.float32)
        # Active = wherever Close is non-null
        if 'Close' in df_re.columns:
            active_matrix[:, j] = (~df_re['Close'].isna()).astype(np.float32).values

    # 5. Append 4 macro features (broadcast across assets)
    macro_tensor = build_macro_tensor(
        macro_dir, all_dates, n_assets, MACRO_FEATURE_NAMES
    )  # (T, N, 4)
    feature_tensor = np.concatenate([feature_tensor, macro_tensor], axis=2)  # (T, N, 22)

    # 6. Cross-sectional z-score (matches training pipeline)
    feature_tensor = cross_sectional_zscore(feature_tensor, active_matrix)
    feature_tensor = np.nan_to_num(feature_tensor, nan=0.0, posinf=0.0, neginf=0.0)

    return feature_tensor, active_matrix, asset_names, all_dates


# ── the main entry point ───────────────────────────────────────────────

def predict(
    request: InferenceRequest | dict,
    model_bundle: ModelBundle | None = None,
    macro_dir: Path | None = None,
    model_dir: Path | None = None,
) -> InferenceResponse:
    """Run a single inference and return model-generated weights for target_month.

    Args:
        request: InferenceRequest object OR a dict that will be coerced.
        model_bundle: optional pre-loaded bundle (avoids reloading on every call)
        macro_dir: where to find the bundled Excel macro files; defaults to
                   `deployment/data/`
        model_dir: where to find the trained models; defaults to
                   `deployment/models/`
    """
    # Coerce dict → InferenceRequest if needed
    if isinstance(request, dict):
        from .schemas import request_from_dict
        request = request_from_dict(request)

    # Resolve paths
    pkg_dir = Path(__file__).resolve().parent.parent
    macro_dir = Path(macro_dir) if macro_dir else (pkg_dir / 'data')
    model_dir = Path(model_dir) if model_dir else (pkg_dir / 'models')

    # Auto-detect input kind if not specified
    input_kind = request.input_kind or _detect_input_kind(request.asset_data)

    # Build the (T, N, 22) feature tensor + active matrix
    feature_tensor, active_matrix, asset_names, dates = _build_feature_tensor(
        request.asset_data, request.target_month, request.egx30_ohlcv,
        macro_dir, input_kind,
    )
    n_assets = len(asset_names)
    T = len(dates)

    # Load model if not provided
    if model_bundle is None:
        model_bundle = load_model(request.tier, n_assets, model_dir=model_dir)

    # Apply constraint overrides if given
    max_w = model_bundle.max_weight
    min_w = model_bundle.min_weight
    if request.constraints_override:
        if request.constraints_override.max_weight is not None:
            max_w = request.constraints_override.max_weight
        if request.constraints_override.min_weight is not None:
            min_w = request.constraints_override.min_weight

    # Build inference env that holds the data
    env = PortfolioEnvMin(
        feature_tensor=feature_tensor,
        active_matrix=active_matrix,
        max_weight=max_w,
        min_weight=min_w,
        dirichlet_prior=model_bundle.dirichlet_prior,
        lookback_window=model_bundle.lookback_window,
    )

    # Find the index of the LAST trading day of the month BEFORE target_month
    target_first = pd.Timestamp(request.target_month + '-01')
    prev_month_end_idx = max((i for i, d in enumerate(dates) if d < target_first),
                             default=T - 1)
    # We want the obs at prev_month_end_idx so the model "decides for target_month"
    if prev_month_end_idx < env.lookback_window - 1:
        raise ValueError(
            f"Need at least {env.lookback_window} trading days of history before "
            f"the start of {request.target_month}, but only {prev_month_end_idx + 1} given. "
            f"Provide more historical OHLCV in asset_data."
        )

    # Manually position the env at the decision date, then call model.predict once
    env.reset()
    env.t = prev_month_end_idx
    obs = env._get_obs()
    # VecNormalize expects (n_envs, *obs_shape), so wrap & normalize
    obs_batched = np.expand_dims(obs, axis=0).astype(np.float32)
    obs_norm = model_bundle.vecnormalize.normalize_obs(obs_batched)

    action, _ = model_bundle.model.predict(obs_norm, deterministic=True)

    # Convert logits → valid weights using the same projection PPO uses internally
    weights = env._masked_softmax(action.flatten(), active_matrix[prev_month_end_idx])

    # Build the response (preserve input asset order, then sort by weight desc)
    decision_date = dates[prev_month_end_idx].strftime('%Y-%m-%d')
    ordered = [AssetWeight(asset=name, weight=float(w))
               for name, w in zip(asset_names, weights)]
    ordered_sorted = sorted(ordered, key=lambda x: -x.weight)

    return InferenceResponse(
        tier=request.tier,
        target_month=request.target_month,
        decision_date=decision_date,
        lookback_window=env.lookback_window,
        asset_weights=ordered_sorted,
        cash_position=0.0,
        sum_check=float(sum(w.weight for w in ordered_sorted)),
        constraints_applied={
            'max_weight': max_w,
            'min_weight': min_w,
            'dirichlet_prior': model_bundle.dirichlet_prior,
            'long_only': True,
            'leverage': False,
            'sum_to_one': True,
        },
    )
