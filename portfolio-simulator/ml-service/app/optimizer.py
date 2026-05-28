from __future__ import annotations

import os
import sys
from dataclasses import dataclass
import importlib.util
from collections import OrderedDict
from collections.abc import Mapping
from functools import lru_cache
import math
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import numpy as np

from .paths import MODEL_ARTIFACTS_ROOT

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("TORCH_NUM_THREADS", "1")

DEPLOYMENT_ROOT = MODEL_ARTIFACTS_ROOT / "deployment"
MODEL_DIR = DEPLOYMENT_ROOT / "models"
MACRO_DIR = DEPLOYMENT_ROOT / "data"

TRAINING_ASSET_COUNTS = {"low": 10, "medium": 12, "high": 16}
MIN_HISTORY_DAYS = 123
WEIGHT_SUM_TOLERANCE = 1e-4
OPTIMIZER_RUNTIME_MODULES = (
    "egtportfolio",
    "torch",
    "stable_baselines3",
    "gymnasium",
    "openpyxl",
    "sklearn",
    "scipy",
)


def _non_negative_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return max(0, int(raw_value))
    except ValueError:
        return default


def _optimizer_bundle_cache_size() -> int:
    return _non_negative_int_env("OPTIMIZER_BUNDLE_CACHE_SIZE", 2)


OPTIMIZER_BUNDLE_CACHE_SIZE = _optimizer_bundle_cache_size()
OPTIMIZER_FEATURE_CACHE_SIZE = _non_negative_int_env("OPTIMIZER_FEATURE_CACHE_SIZE", 256)


@dataclass(frozen=True)
class OptimizerRun:
    weights: dict[str, float]
    asset_weights: list[dict[str, float | str]]
    sum_check: float
    decision_date: str
    constraints_applied: dict[str, Any]
    diagnostics: dict[str, Any]


class OptimizerContractError(RuntimeError):
    pass


def optimizer_available() -> bool:
    if not DEPLOYMENT_ROOT.exists() or not MODEL_DIR.exists() or not MACRO_DIR.exists():
        return False
    required = []
    for tier in ("low", "medium", "high"):
        required.extend(
            [
                MODEL_DIR / f"ppo_{tier}_seed42_setbased.zip",
                MODEL_DIR / f"vecnorm_{tier}_seed42_setbased.pkl",
            ]
        )
    return all(path.exists() for path in required)


def optimizer_runtime_available() -> bool:
    if not optimizer_available():
        return False
    if not any(MACRO_DIR.glob("*.xlsx")):
        return False
    if str(DEPLOYMENT_ROOT) not in sys.path:
        sys.path.insert(0, str(DEPLOYMENT_ROOT))
    return all(
        importlib.util.find_spec(module_name) is not None
        for module_name in OPTIMIZER_RUNTIME_MODULES
    )


def _import_package():
    if str(DEPLOYMENT_ROOT) not in sys.path:
        sys.path.insert(0, str(DEPLOYMENT_ROOT))
    try:
        import torch

        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    from egtportfolio import InferenceRequest, load_model, predict

    return load_model, predict, InferenceRequest


@lru_cache(maxsize=OPTIMIZER_BUNDLE_CACHE_SIZE)
def _load_bundle(tier: Literal["low", "medium", "high"], n_assets: int):
    load_model, _predict, _inference_request = _import_package()
    return load_model(tier=tier, n_assets=n_assets, model_dir=MODEL_DIR)


_FEATURE_FRAME_CACHE: OrderedDict[tuple[Any, str, str], pd.DataFrame] = OrderedDict()


def _daily_rows_for_asset(
    daily_market: Any,
    asset_id: str,
) -> pd.DataFrame:
    if hasattr(daily_market, "by_asset"):
        return daily_market.by_asset.get(str(asset_id), pd.DataFrame())
    if isinstance(daily_market, Mapping):
        return daily_market.get(str(asset_id), pd.DataFrame())
    return daily_market.loc[daily_market["AssetID"].astype(str).eq(str(asset_id))].sort_values("Date")


def _market_cache_identity(daily_market: Any) -> Any:
    version = getattr(daily_market, "version", None)
    if version is not None:
        return version
    return ("object", id(daily_market))


def _history_frame_for_asset(daily_market: Any, asset_id: str, target_month: str) -> pd.DataFrame:
    target_first = pd.Timestamp(f"{target_month}-01")
    history_start = target_first - pd.DateOffset(months=9)
    asset_rows = _daily_rows_for_asset(daily_market, asset_id)
    if asset_rows.empty:
        frame = asset_rows
    else:
        frame = asset_rows.loc[
            asset_rows["Date"].lt(target_first)
            & asset_rows["Date"].ge(history_start)
            & asset_rows["IsObserved"].eq(1)
        ]

    if len(frame) < MIN_HISTORY_DAYS:
        raise ValueError(
            f"Weight optimizer needs at least {MIN_HISTORY_DAYS} daily rows before {target_month} "
            f"for {asset_id}, but found {len(frame)}."
        )
    return frame


def _series_for_asset(
    daily_market: Any,
    asset_id: str,
    target_month: str,
) -> dict[str, Any]:
    frame = _history_frame_for_asset(daily_market, asset_id, target_month)
    close = frame["PriceForReturn"].astype(float)
    return {
        "asset": asset_id,
        "dates": frame["Date"].dt.strftime("%Y-%m-%d").tolist(),
        "close": close.tolist(),
        "open": frame["OpenPriceForRange"].fillna(close).astype(float).tolist(),
        "high": frame["HighPriceForRange"].fillna(close).astype(float).tolist(),
        "low": frame["LowPriceForRange"].fillna(close).astype(float).tolist(),
        "volume": frame["Volume"].fillna(0.0).astype(float).tolist(),
    }


def _raw_ohlcv_frame_for_asset(daily_market: Any, asset_id: str, target_month: str) -> pd.DataFrame:
    frame = _history_frame_for_asset(daily_market, asset_id, target_month)
    close = frame["PriceForReturn"].astype(float)
    raw = pd.DataFrame(
        {
            "Close": close.to_numpy(dtype=float),
            "Open": frame["OpenPriceForRange"].fillna(close).astype(float).to_numpy(),
            "High": frame["HighPriceForRange"].fillna(close).astype(float).to_numpy(),
            "Low": frame["LowPriceForRange"].fillna(close).astype(float).to_numpy(),
            "Volume": frame["Volume"].fillna(0.0).astype(float).to_numpy(),
        },
        index=pd.DatetimeIndex(frame["Date"]),
    )
    return raw.sort_index()


def _cache_feature_frame(key: tuple[Any, str, str], frame: pd.DataFrame) -> None:
    if OPTIMIZER_FEATURE_CACHE_SIZE <= 0:
        return
    _FEATURE_FRAME_CACHE[key] = frame
    _FEATURE_FRAME_CACHE.move_to_end(key)
    while len(_FEATURE_FRAME_CACHE) > OPTIMIZER_FEATURE_CACHE_SIZE:
        _FEATURE_FRAME_CACHE.popitem(last=False)


def _cached_feature_frame(key: tuple[Any, str, str]) -> pd.DataFrame | None:
    frame = _FEATURE_FRAME_CACHE.get(key)
    if frame is not None:
        _FEATURE_FRAME_CACHE.move_to_end(key)
    return frame


def _feature_frames_for_assets(
    daily_market: Any,
    asset_ids: list[str],
    target_month: str,
) -> dict[str, pd.DataFrame]:
    from egtportfolio.features import compute_features_one_asset

    market_identity = _market_cache_identity(daily_market)
    egx30 = _raw_ohlcv_frame_for_asset(daily_market, "EGX30", target_month)
    egx30_log_returns = np.log(egx30["Close"] / egx30["Close"].shift(1)).clip(-0.5, 0.5)
    frames: dict[str, pd.DataFrame] = {}
    for asset_id in asset_ids:
        asset_key = str(asset_id)
        cache_key = (market_identity, target_month, asset_key)
        cached = _cached_feature_frame(cache_key)
        if cached is not None:
            frames[asset_key] = cached
            continue
        raw = _raw_ohlcv_frame_for_asset(daily_market, asset_key, target_month)
        featured = compute_features_one_asset(raw, egx30_log_returns)
        _cache_feature_frame(cache_key, featured)
        frames[asset_key] = featured
    return frames


def _validate_optimizer_weights(
    *,
    requested_asset_ids: list[str],
    weights: dict[str, float],
    sum_check: float,
    target_month: str,
) -> None:
    requested = [str(asset_id) for asset_id in requested_asset_ids]
    requested_set = set(requested)
    actual_set = set(weights)
    missing = sorted(requested_set.difference(actual_set))
    extra = sorted(actual_set.difference(requested_set))
    if missing or extra:
        raise OptimizerContractError(
            f"Weight optimizer returned an asset mismatch for {target_month}; missing={missing}, extra={extra}."
        )
    values = [float(weights[asset_id]) for asset_id in requested]
    if not values or not all(math.isfinite(value) for value in values):
        raise OptimizerContractError(f"Weight optimizer returned non-finite weights for {target_month}.")
    if any(value < -1e-12 for value in values):
        raise OptimizerContractError(f"Weight optimizer returned negative weights for {target_month}.")
    total = float(sum(values))
    reported_total = float(sum_check)
    if not math.isfinite(reported_total):
        raise OptimizerContractError(f"Weight optimizer returned a non-finite sum_check for {target_month}.")
    if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE or abs(reported_total - 1.0) > WEIGHT_SUM_TOLERANCE:
        raise OptimizerContractError(
            f"Weight optimizer weights for {target_month} must sum to 1.0; got total={total:.8f}, sum_check={reported_total:.8f}."
        )


def run_weight_optimizer(
    *,
    tier: Literal["low", "medium", "high"],
    target_month: str,
    asset_ids: list[str],
    daily_market: Any,
) -> OptimizerRun:
    if not asset_ids:
        raise ValueError("Weight optimizer received an empty asset universe.")
    if not optimizer_available():
        raise FileNotFoundError(f"Missing weight optimizer deployment artifacts under {DEPLOYMENT_ROOT}")

    _load_model, predict, inference_request = _import_package()
    request = inference_request(
        tier=tier,
        target_month=target_month,
        input_kind="precomputed_features",
        asset_data=_feature_frames_for_assets(daily_market, asset_ids, target_month),
    )
    bundle = _load_bundle(tier, len(asset_ids))
    result = predict(
        request,
        model_bundle=bundle,
        macro_dir=MACRO_DIR,
        model_dir=MODEL_DIR,
    )
    try:
        asset_weights = result.to_dict()["asset_weights"]
        if not isinstance(asset_weights, list):
            raise TypeError("asset_weights must be a list")
        asset_ids_from_result = [str(row["asset"]) for row in asset_weights]
        if len(asset_ids_from_result) != len(set(asset_ids_from_result)):
            raise ValueError("asset_weights contains duplicate assets")
        weights = {str(row["asset"]): float(row["weight"]) for row in asset_weights}
        sum_check = float(result.sum_check)
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise OptimizerContractError(f"Weight optimizer returned malformed output for {target_month}: {exc}") from exc
    _validate_optimizer_weights(
        requested_asset_ids=asset_ids,
        weights=weights,
        sum_check=sum_check,
        target_month=target_month,
    )
    training_n = TRAINING_ASSET_COUNTS[tier]
    return OptimizerRun(
        weights=weights,
        asset_weights=asset_weights,
        sum_check=sum_check,
        decision_date=str(result.decision_date),
        constraints_applied=dict(result.constraints_applied),
        diagnostics={
            "tier": tier,
            "assetCount": len(asset_ids),
            "trainingAssetCount": training_n,
            "usesIdentityVecNormalizeFallback": len(asset_ids) != training_n,
            "modelVersion": str(getattr(result, "model_version", "unknown")),
            "packageVersion": str(getattr(result, "package_version", "unknown")),
        },
    )
