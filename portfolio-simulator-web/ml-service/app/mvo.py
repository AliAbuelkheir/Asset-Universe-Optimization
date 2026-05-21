from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf

RiskLevel = Literal["low", "medium", "high"]

LOOKBACK_MONTHS = 9
MAX_ASSET_WEIGHT = 0.20
MIN_RETURN_ROWS = 20
RISK_AVERSION: dict[RiskLevel, float] = {
    "low": 8.0,
    "medium": 4.0,
    "high": 2.0,
}


@dataclass(frozen=True)
class MvoRun:
    weights: dict[str, float]
    sum_check: float
    decision_date: str
    ineligible_assets: list[str]


def _trailing_returns(
    *,
    daily_market: pd.DataFrame,
    asset_ids: list[str],
    target_month: str,
) -> pd.DataFrame:
    target_first = pd.Timestamp(f"{target_month}-01")
    history_start = target_first - pd.DateOffset(months=LOOKBACK_MONTHS)
    requested_ids = [str(asset_id) for asset_id in asset_ids]
    frame = daily_market.loc[
        daily_market["AssetID"].astype(str).isin(requested_ids)
        & daily_market["Date"].lt(target_first)
        & daily_market["Date"].ge(history_start),
        ["Date", "AssetID", "ReturnFromPrice", "IsObserved"],
    ].copy()
    if frame.empty:
        raise ValueError(f"MVO needs trailing return history before {target_month}, but found no rows.")

    frame["AssetID"] = frame["AssetID"].astype(str)
    frame["ReturnFromPrice"] = pd.to_numeric(frame["ReturnFromPrice"], errors="coerce")
    frame["IsObserved"] = pd.to_numeric(frame["IsObserved"], errors="coerce").fillna(0).astype(int)
    frame = frame.loc[frame["IsObserved"].eq(1)].copy()
    if frame.empty:
        raise ValueError(f"MVO needs observed trailing return history before {target_month}, but found no rows.")
    returns_by_asset = (
        frame.dropna(subset=["Date", "AssetID", "ReturnFromPrice"])
        .pivot_table(index="Date", columns="AssetID", values="ReturnFromPrice", aggfunc="last")
        .sort_index()
    )
    returns_by_asset = returns_by_asset.reindex(columns=requested_ids)
    eligible_assets = [
        asset_id for asset_id in requested_ids if int(returns_by_asset[asset_id].dropna().shape[0]) >= MIN_RETURN_ROWS
    ]
    if not eligible_assets:
        raise ValueError(
            f"MVO needs at least {MIN_RETURN_ROWS} trailing return rows before {target_month}, but no asset qualifies."
        )

    returns = returns_by_asset[eligible_assets].replace([np.inf, -np.inf], np.nan).dropna(axis=0, how="any")
    if len(returns) < MIN_RETURN_ROWS:
        raise ValueError(
            f"MVO needs at least {MIN_RETURN_ROWS} complete trailing return rows before {target_month}, but found {len(returns)}."
        )
    return returns


def run_mvo_full_universe(
    *,
    risk_level: RiskLevel,
    target_month: str,
    asset_ids: list[str],
    daily_market: pd.DataFrame,
) -> MvoRun:
    if not asset_ids:
        raise ValueError("MVO received an empty asset universe.")

    returns = _trailing_returns(daily_market=daily_market, asset_ids=asset_ids, target_month=target_month)
    ordered_assets = [str(asset_id) for asset_id in returns.columns]
    n_assets = len(ordered_assets)
    if n_assets * MAX_ASSET_WEIGHT < 1.0 - 1e-9:
        raise ValueError(
            f"MVO max weight cap {MAX_ASSET_WEIGHT:.0%} is infeasible for {n_assets} asset(s)."
        )

    expected_returns = returns.mean().to_numpy(dtype=float)
    covariance = LedoitWolf().fit(returns.to_numpy(dtype=float)).covariance_
    gamma = RISK_AVERSION[risk_level]

    def objective(weights: np.ndarray) -> float:
        portfolio_return = float(weights @ expected_returns)
        portfolio_variance = float(weights @ covariance @ weights)
        return -(portfolio_return - 0.5 * gamma * portfolio_variance)

    initial = np.full(n_assets, 1.0 / n_assets, dtype=float)
    bounds = [(0.0, MAX_ASSET_WEIGHT) for _ in ordered_assets]
    constraints = [{"type": "eq", "fun": lambda weights: float(np.sum(weights) - 1.0)}]
    result = minimize(
        objective,
        initial,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 1000, "ftol": 1e-12},
    )
    if not result.success:
        raise ValueError(f"MVO failed for {target_month}: {result.message}")

    weights = np.clip(np.asarray(result.x, dtype=float), 0.0, MAX_ASSET_WEIGHT)
    total_weight = float(weights.sum())
    if total_weight <= 0:
        raise ValueError(f"MVO produced non-positive total weight for {target_month}.")
    if abs(total_weight - 1.0) > 1e-6:
        raise ValueError(f"MVO weights for {target_month} sum to {total_weight:.8f}, not 1.0.")
    if float(weights.max()) > MAX_ASSET_WEIGHT + 1e-6:
        raise ValueError(f"MVO exceeded the {MAX_ASSET_WEIGHT:.0%} asset cap for {target_month}.")

    return MvoRun(
        weights={asset_id: float(weight) for asset_id, weight in zip(ordered_assets, weights)},
        sum_check=float(weights.sum()),
        decision_date=str(returns.index.max().date()),
        ineligible_assets=sorted(set(str(asset_id) for asset_id in asset_ids).difference(ordered_assets)),
    )
