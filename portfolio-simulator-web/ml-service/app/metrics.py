from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def equal_weights(asset_ids: list[str]) -> dict[str, float]:
    weight = 1.0 / len(asset_ids)
    return {asset_id: weight for asset_id in asset_ids}


def portfolio_monthly_returns(
    monthly_returns: pd.DataFrame,
    months: list[str],
    weights: dict[str, float],
) -> list[float]:
    rows: list[float] = []
    for month in months:
        frame = monthly_returns.loc[monthly_returns["Date"].eq(month)]
        returns = frame.set_index("AssetID")["MonthlyReturn"].to_dict()
        available = {asset_id: weight for asset_id, weight in weights.items() if asset_id in returns}
        if not available:
            rows.append(0.0)
            continue
        total_weight = sum(available.values())
        rows.append(float(sum((weight / total_weight) * returns[asset_id] for asset_id, weight in available.items())))
    return rows


def egx30_returns(monthly_returns: pd.DataFrame, months: list[str]) -> list[float]:
    egx = monthly_returns.loc[monthly_returns["AssetID"].eq("EGX30")].set_index("Date")["MonthlyReturn"].to_dict()
    return [float(egx.get(month, 0.0)) for month in months]


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
    running_peak = np.maximum.accumulate(cumulative_curve)
    drawdowns = cumulative_curve / running_peak - 1.0
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
    available = [candidate for candidate in all_months if start_month <= candidate <= "2026-01"]
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
