from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

WEIGHT_SUM_TOLERANCE = 1e-4


def equal_weights(asset_ids: list[str]) -> dict[str, float]:
    if not asset_ids:
        raise ValueError("Cannot build equal weights for an empty asset list.")
    weight = 1.0 / len(asset_ids)
    return {asset_id: weight for asset_id in asset_ids}


def validate_portfolio_weights(weights: dict[str, float], *, context: str) -> None:
    if not weights:
        raise ValueError(f"Portfolio weights for {context} cannot be empty.")
    values = np.asarray(list(weights.values()), dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(f"Portfolio weights for {context} contain non-finite values.")
    if (values < -1e-12).any():
        raise ValueError(f"Portfolio weights for {context} must be non-negative.")
    total_weight = float(values.sum())
    if abs(total_weight - 1.0) > WEIGHT_SUM_TOLERANCE:
        raise ValueError(
            f"Portfolio weights for {context} must sum to 1.0 within {WEIGHT_SUM_TOLERANCE:g}; got {total_weight:.8f}."
        )


def index_monthly_returns(monthly_returns: pd.DataFrame) -> dict[tuple[str, str], float]:
    frame = monthly_returns.loc[:, ["Date", "AssetID", "MonthlyReturn"]].copy()
    frame["Date"] = frame["Date"].astype(str)
    frame["AssetID"] = frame["AssetID"].astype(str)
    return {
        (str(row.Date), str(row.AssetID)): float(row.MonthlyReturn)
        for row in frame.itertuples(index=False)
    }


def portfolio_monthly_returns(
    monthly_returns: pd.DataFrame | Mapping[tuple[str, str], float],
    months: list[str],
    weights: dict[str, float],
) -> list[float]:
    rows: list[float] = []
    for month in months:
        if isinstance(monthly_returns, Mapping):
            returns = {asset_id: monthly_returns.get((month, asset_id)) for asset_id in weights}
        else:
            frame = monthly_returns.loc[monthly_returns["Date"].eq(month)]
            returns = frame.set_index("AssetID")["MonthlyReturn"].to_dict()
        missing = sorted(asset_id for asset_id in weights if returns.get(asset_id) is None)
        if missing:
            raise ValueError(
                f"Missing monthly returns for {len(missing)} weighted asset(s) in {month}: {', '.join(missing)}"
            )
        validate_portfolio_weights(weights, context=month)
        rows.append(float(sum(weight * float(returns[asset_id]) for asset_id, weight in weights.items())))
    return rows


def egx30_returns(monthly_returns: pd.DataFrame | Mapping[tuple[str, str], float], months: list[str]) -> list[float]:
    if isinstance(monthly_returns, Mapping):
        egx = {month: monthly_returns.get((month, "EGX30")) for month in months}
    else:
        egx = monthly_returns.loc[monthly_returns["AssetID"].eq("EGX30")].set_index("Date")["MonthlyReturn"].to_dict()
    missing = [month for month in months if egx.get(month) is None]
    if missing:
        raise ValueError(f"Missing EGX30 monthly returns for: {', '.join(missing)}")
    return [float(egx[month]) for month in months]


def performance_metrics(returns: list[float]) -> dict[str, Any]:
    if not returns:
        return {
            "cumulativeReturn": 0.0,
            "annualizedVolatility": 0.0,
            "sharpe": None,
            "sortino": None,
            "maxDrawdown": 0.0,
            "bestMonth": 0.0,
            "worstMonth": 0.0,
            "ratioNotes": {
                "sharpe": "n/a because no monthly returns are available.",
                "sortino": "n/a because no monthly returns are available.",
            },
        }
    values = np.asarray(returns, dtype=float)
    cumulative_curve = np.cumprod(1.0 + values)
    volatility = float(values.std(ddof=1) * math.sqrt(12)) if len(values) > 1 else 0.0
    mean_monthly = float(values.mean())
    sharpe = float((mean_monthly * 12) / volatility) if volatility > 0 else None
    downside = values[values < 0]
    downside_vol = float(downside.std(ddof=1) * math.sqrt(12)) if len(downside) > 1 else 0.0
    sortino = float((mean_monthly * 12) / downside_vol) if downside_vol > 0 else None
    wealth_curve = np.concatenate(([1.0], cumulative_curve))
    running_peak = np.maximum.accumulate(wealth_curve)
    drawdowns = wealth_curve / running_peak - 1.0
    return {
        "cumulativeReturn": float(cumulative_curve[-1] - 1.0),
        "annualizedVolatility": volatility,
        "sharpe": sharpe,
        "sortino": sortino,
        "maxDrawdown": float(drawdowns.min()),
        "bestMonth": float(values.max()),
        "worstMonth": float(values.min()),
        "ratioNotes": {
            "sharpe": ""
            if sharpe is not None
            else "n/a because the selected duration has fewer than two months or zero return volatility.",
            "sortino": ""
            if sortino is not None
            else "n/a because the selected duration has fewer than two negative-return months, so downside volatility is undefined.",
        },
    }


def resolve_forward_months(all_months: list[str], start_month: str, duration_months: int | None) -> list[str]:
    available = [candidate for candidate in all_months if start_month <= candidate]
    if duration_months is None:
        return available
    if duration_months < 1:
        raise ValueError("durationMonths must be at least 1 when provided.")
    return available[:duration_months]


def month_interval_days(months: list[str]) -> list[dict[str, Any]]:
    labels = ["Start"] + months
    rows: list[dict[str, Any]] = []
    for index, label in enumerate(labels):
        if index == 0:
            rows.append({"label": label, "daysSincePrevious": 0})
            continue
        previous_period = pd.Period(months[index - 2], freq="M") if index > 1 else pd.Period(months[0], freq="M") - 1
        current_period = pd.Period(months[index - 1], freq="M")
        previous_end = previous_period.end_time.normalize()
        current_end = current_period.end_time.normalize()
        rows.append({"label": label, "daysSincePrevious": int((current_end - previous_end).days)})
    return rows
