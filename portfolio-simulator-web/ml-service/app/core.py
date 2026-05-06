from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .contracts import RISK_TOLERANCE_MODEL_CONTRACT, WEIGHT_OPTIMIZER_MODEL_CONTRACT

REPO_ROOT = Path(__file__).resolve().parents[3]
PPO_ROOT = REPO_ROOT / "ppo-risk-model"
BEST_MODEL_DIR = PPO_ROOT / "outputs" / "best_model"
PREDICTIONS_PATH = BEST_MODEL_DIR / "ranked_predictions.csv"
DAILY_MARKET_PATH = PPO_ROOT / "data" / "ready" / "daily_market_series.csv"
MONTHLY_PANEL_PATH = PPO_ROOT / "data" / "ready" / "monthly_asset_panel.csv"

VALID_SPLITS = {"validation", "test"}
RISK_BUCKETS = {
    "low": {
        "id": "low",
        "label": "Low risk",
        "minRankPct": 0.0,
        "maxRankPct": 0.40,
        "description": "Lowest predicted-risk 40% of the active universe.",
    },
    "medium": {
        "id": "medium",
        "label": "Medium risk",
        "minRankPct": 0.25,
        "maxRankPct": 0.75,
        "description": "Central predicted-risk band with overlap into both tails.",
    },
    "high": {
        "id": "high",
        "label": "High risk",
        "minRankPct": 0.60,
        "maxRankPct": 1.0,
        "description": "Highest predicted-risk 40% of the active universe.",
    },
}


@dataclass(frozen=True)
class ServiceHealth:
    status: str
    ppoRootExists: bool
    predictionsAvailable: bool
    dailyMarketAvailable: bool
    monthlyPanelAvailable: bool
    optimizerMode: str


def _read_predictions() -> pd.DataFrame:
    if not PREDICTIONS_PATH.exists():
        raise FileNotFoundError(f"Missing PPO ranked predictions at {PREDICTIONS_PATH}")
    predictions = pd.read_csv(PREDICTIONS_PATH)
    required = {"Date", "Split", "AssetID", "AssetName", "AssetGroup", "PredictedRisk", "PredictedRankPct"}
    missing = sorted(required.difference(predictions.columns))
    if missing:
        raise ValueError(f"ranked_predictions.csv is missing required columns: {missing}")
    predictions["Date"] = predictions["Date"].astype(str)
    predictions["Split"] = predictions["Split"].astype(str)
    predictions["PredictedRisk"] = pd.to_numeric(predictions["PredictedRisk"], errors="coerce")
    predictions["PredictedRankPct"] = pd.to_numeric(predictions["PredictedRankPct"], errors="coerce")
    if "realized_risk" in predictions.columns:
        predictions["realized_risk"] = pd.to_numeric(predictions["realized_risk"], errors="coerce")
    return predictions


def _read_monthly_panel_targets() -> pd.DataFrame:
    if not MONTHLY_PANEL_PATH.exists():
        raise FileNotFoundError(f"Missing monthly asset panel at {MONTHLY_PANEL_PATH}")
    panel = pd.read_csv(
        MONTHLY_PANEL_PATH,
        usecols=[
            "Date",
            "AssetID",
            "realized_vol",
            "realized_downside_dev",
            "realized_max_drawdown",
        ],
    )
    panel["Date"] = panel["Date"].astype(str)
    for column in ("realized_vol", "realized_downside_dev", "realized_max_drawdown"):
        panel[column] = pd.to_numeric(panel[column], errors="coerce")
    return panel


def _read_monthly_returns() -> pd.DataFrame:
    if not DAILY_MARKET_PATH.exists():
        raise FileNotFoundError(f"Missing daily market series at {DAILY_MARKET_PATH}")
    daily = pd.read_csv(DAILY_MARKET_PATH, usecols=["Date", "AssetID", "ReturnFromPrice"])
    daily["Date"] = pd.to_datetime(daily["Date"], errors="coerce")
    daily["ReturnFromPrice"] = pd.to_numeric(daily["ReturnFromPrice"], errors="coerce")
    daily = daily.dropna(subset=["Date", "AssetID", "ReturnFromPrice"]).copy()
    daily["Month"] = daily["Date"].dt.to_period("M").astype(str)
    monthly = (
        daily.groupby(["Month", "AssetID"], sort=True)["ReturnFromPrice"]
        .agg(lambda values: float(np.prod(1.0 + values.to_numpy(dtype=float)) - 1.0))
        .reset_index()
        .rename(columns={"Month": "Date", "ReturnFromPrice": "MonthlyReturn"})
    )
    return monthly


def _read_daily_returns() -> pd.DataFrame:
    if not DAILY_MARKET_PATH.exists():
        raise FileNotFoundError(f"Missing daily market series at {DAILY_MARKET_PATH}")
    daily = pd.read_csv(DAILY_MARKET_PATH, usecols=["Date", "AssetID", "ReturnFromPrice"])
    daily["Date"] = pd.to_datetime(daily["Date"], errors="coerce")
    daily["ReturnFromPrice"] = pd.to_numeric(daily["ReturnFromPrice"], errors="coerce")
    daily = daily.dropna(subset=["Date", "AssetID", "ReturnFromPrice"]).copy()
    daily["Month"] = daily["Date"].dt.to_period("M").astype(str)
    return daily


def health() -> dict[str, Any]:
    payload = ServiceHealth(
        status="ok"
        if PREDICTIONS_PATH.exists() and DAILY_MARKET_PATH.exists() and MONTHLY_PANEL_PATH.exists()
        else "degraded",
        ppoRootExists=PPO_ROOT.exists(),
        predictionsAvailable=PREDICTIONS_PATH.exists(),
        dailyMarketAvailable=DAILY_MARKET_PATH.exists(),
        monthlyPanelAvailable=MONTHLY_PANEL_PATH.exists(),
        optimizerMode="mock_equal_weight",
    )
    return payload.__dict__


def available_months() -> list[dict[str, Any]]:
    predictions = _read_predictions()
    subset = predictions.loc[predictions["Split"].isin(VALID_SPLITS)].copy()
    grouped = (
        subset.groupby(["Date", "Split"], sort=True)["AssetID"]
        .count()
        .reset_index()
        .rename(columns={"Date": "month", "Split": "split", "AssetID": "assetCount"})
    )
    return grouped.to_dict(orient="records")


def risk_levels() -> list[dict[str, Any]]:
    return [RISK_BUCKETS[key] for key in ("low", "medium", "high")]


def select_assets(month: str, risk_level: str) -> tuple[pd.DataFrame, str]:
    if risk_level not in RISK_BUCKETS:
        raise ValueError(f"Unknown risk level: {risk_level}")
    predictions = _read_predictions()
    month_frame = predictions.loc[predictions["Date"].eq(month) & predictions["Split"].isin(VALID_SPLITS)].copy()
    if month_frame.empty:
        raise ValueError(f"No validation/test predictions found for month {month}")
    bucket = RISK_BUCKETS[risk_level]
    selected = month_frame.loc[
        month_frame["PredictedRankPct"].between(bucket["minRankPct"], bucket["maxRankPct"], inclusive="both")
    ].copy()
    if selected.empty:
        raise ValueError(f"No selected assets for month {month} and risk level {risk_level}")
    selected = selected.sort_values(["PredictedRankPct", "PredictedRisk", "AssetID"]).reset_index(drop=True)
    return selected, str(month_frame["Split"].iloc[0])


def _equal_weights(asset_ids: list[str]) -> dict[str, float]:
    weight = 1.0 / len(asset_ids)
    return {asset_id: weight for asset_id in asset_ids}


def _portfolio_monthly_returns(
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


def _portfolio_daily_returns(
    daily_returns: pd.DataFrame,
    month: str,
    weights: dict[str, float],
) -> list[float]:
    frame = daily_returns.loc[daily_returns["Month"].eq(month)].copy()
    if frame.empty:
        return []
    rows: list[float] = []
    for _date, day_frame in frame.groupby("Date", sort=True):
        returns = day_frame.set_index("AssetID")["ReturnFromPrice"].to_dict()
        available = {asset_id: weight for asset_id, weight in weights.items() if asset_id in returns}
        if not available:
            continue
        total_weight = sum(available.values())
        rows.append(float(sum((weight / total_weight) * returns[asset_id] for asset_id, weight in available.items())))
    return rows


def _raw_risk_metrics(daily_returns: list[float]) -> dict[str, float | int]:
    if not daily_returns:
        return {
            "annualizedVolatility": 0.0,
            "annualizedDownsideDeviation": 0.0,
            "maxDrawdown": 0.0,
            "observations": 0,
        }
    values = np.asarray(daily_returns, dtype=float)
    volatility = float(values.std(ddof=1) * math.sqrt(252)) if len(values) > 1 else 0.0
    downside = values[values < 0]
    downside_dev = float(downside.std(ddof=1) * math.sqrt(252)) if len(downside) > 1 else 0.0
    cumulative_curve = np.cumprod(1.0 + values)
    running_peak = np.maximum.accumulate(cumulative_curve)
    drawdowns = cumulative_curve / running_peak - 1.0
    return {
        "annualizedVolatility": volatility,
        "annualizedDownsideDeviation": downside_dev,
        "maxDrawdown": float(drawdowns.min()),
        "observations": int(len(values)),
    }


def _egx30_returns(monthly_returns: pd.DataFrame, months: list[str]) -> list[float]:
    egx = monthly_returns.loc[monthly_returns["AssetID"].eq("EGX30")].set_index("Date")["MonthlyReturn"].to_dict()
    return [float(egx.get(month, 0.0)) for month in months]


def _attach_realized_components(frame: pd.DataFrame, panel_targets: pd.DataFrame) -> pd.DataFrame:
    return frame.merge(panel_targets, on=["Date", "AssetID"], how="left")


def _weighted_risk_components(frame: pd.DataFrame, weights: dict[str, float]) -> dict[str, float]:
    if frame.empty:
        return {"realizedVol": 0.0, "realizedDownsideDev": 0.0, "realizedMaxDrawdown": 0.0}
    working = frame.copy()
    working["Weight"] = working["AssetID"].astype(str).map(weights).fillna(0.0)
    working = working.loc[working["Weight"] > 0].copy()
    if working.empty:
        return {"realizedVol": 0.0, "realizedDownsideDev": 0.0, "realizedMaxDrawdown": 0.0}
    total_weight = float(working["Weight"].sum())
    normalized_weight = working["Weight"] / total_weight
    return {
        "realizedVol": float((working["realized_vol"] * normalized_weight).sum()),
        "realizedDownsideDev": float((working["realized_downside_dev"] * normalized_weight).sum()),
        "realizedMaxDrawdown": float((working["realized_max_drawdown"] * normalized_weight).sum()),
    }


def _risk_component_rows(
    selected: pd.DataFrame,
    same_month_universe: pd.DataFrame,
    optimized_weights: dict[str, float],
    all_universe_weights: dict[str, float],
    risk_level: str,
) -> list[dict[str, Any]]:
    egx_frame = same_month_universe.loc[same_month_universe["AssetID"].astype(str).eq("EGX30")].copy()
    egx_weights = {"EGX30": 1.0} if not egx_frame.empty else {}
    return [
        {
            "id": "assignedRiskBucket",
            "label": "Assigned risk bucket equal weight",
            "components": _weighted_risk_components(selected, _equal_weights(selected["AssetID"].astype(str).tolist())),
        },
        {
            "id": "allEqualWeight",
            "label": "All active universe equal weight",
            "components": _weighted_risk_components(same_month_universe, all_universe_weights),
        },
        {
            "id": "egx30",
            "label": "EGX30 benchmark",
            "components": _weighted_risk_components(egx_frame, egx_weights),
        },
    ]


def _raw_risk_rows(
    daily_returns: pd.DataFrame,
    month: str,
    selected_weights: dict[str, float],
    all_universe_weights: dict[str, float],
) -> list[dict[str, Any]]:
    return [
        {
            "id": "assignedRiskBucket",
            "label": "Assigned risk bucket equal weight",
            "components": _raw_risk_metrics(_portfolio_daily_returns(daily_returns, month, selected_weights)),
        },
        {
            "id": "allEqualWeight",
            "label": "All active universe equal weight",
            "components": _raw_risk_metrics(_portfolio_daily_returns(daily_returns, month, all_universe_weights)),
        },
        {
            "id": "egx30",
            "label": "EGX30 benchmark",
            "components": _raw_risk_metrics(_portfolio_daily_returns(daily_returns, month, {"EGX30": 1.0})),
        },
    ]


def _metrics(returns: list[float]) -> dict[str, float | None | dict[str, str]]:
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
    cumulative_return = float(cumulative_curve[-1] - 1.0)
    volatility = float(values.std(ddof=1) * math.sqrt(12)) if len(values) > 1 else 0.0
    mean_monthly = float(values.mean())
    sharpe = float((mean_monthly * 12) / volatility) if volatility > 0 else None
    downside = values[values < 0]
    downside_vol = float(downside.std(ddof=1) * math.sqrt(12)) if len(downside) > 1 else 0.0
    sortino = float((mean_monthly * 12) / downside_vol) if downside_vol > 0 else None
    running_peak = np.maximum.accumulate(cumulative_curve)
    drawdowns = cumulative_curve / running_peak - 1.0
    ratio_notes = {
        "sharpe": "" if sharpe is not None else "n/a because the selected duration has fewer than two months or zero return volatility.",
        "sortino": ""
        if sortino is not None
        else "n/a because the selected duration has fewer than two negative-return months, so downside volatility is undefined.",
    }
    return {
        "cumulativeReturn": cumulative_return,
        "annualizedVolatility": volatility,
        "sharpe": sharpe,
        "sortino": sortino,
        "maxDrawdown": float(drawdowns.min()),
        "bestMonth": float(values.max()),
        "worstMonth": float(values.min()),
        "ratioNotes": ratio_notes,
    }


def _resolve_forward_months(all_months: list[str], start_month: str, duration_months: int | None) -> list[str]:
    available = [candidate for candidate in all_months if start_month <= candidate <= "2026-01"]
    if duration_months is None:
        return available
    if duration_months < 1:
        raise ValueError("durationMonths must be at least 1 when provided.")
    return available[:duration_months]


def _month_interval_days(months: list[str]) -> list[dict[str, Any]]:
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


def run_fast_simulation(month: str, risk_level: str, duration_months: int | None = None) -> dict[str, Any]:
    selected, split = select_assets(month, risk_level)
    predictions = _read_predictions()
    panel_targets = _read_monthly_panel_targets()
    selected = _attach_realized_components(selected, panel_targets)
    monthly_returns = _read_monthly_returns()
    daily_returns = _read_daily_returns()
    all_months = sorted(monthly_returns["Date"].astype(str).unique())
    forward_months = _resolve_forward_months(all_months, month, duration_months)
    if not forward_months:
        raise ValueError(f"No forward return window is available for month {month}")

    selected_asset_ids = selected["AssetID"].astype(str).tolist()
    selected_weights = _equal_weights(selected_asset_ids)

    same_month_universe = predictions.loc[predictions["Date"].eq(month) & predictions["Split"].isin(VALID_SPLITS)].copy()
    same_month_universe = _attach_realized_components(same_month_universe, panel_targets)
    all_universe_weights = _equal_weights(same_month_universe["AssetID"].astype(str).tolist())

    bucket_returns = _portfolio_monthly_returns(monthly_returns, forward_months, selected_weights)
    all_equal_returns = _portfolio_monthly_returns(monthly_returns, forward_months, all_universe_weights)
    egx_returns = _egx30_returns(monthly_returns, forward_months)

    selected_assets = []
    for row in selected.to_dict(orient="records"):
        selected_assets.append(
            {
                "assetId": str(row["AssetID"]),
                "assetName": str(row["AssetName"]),
                "assetGroup": str(row["AssetGroup"]),
                "predictedRankPct": float(row["PredictedRankPct"]),
                "realizedVol": None if pd.isna(row.get("realized_vol")) else float(row.get("realized_vol")),
                "realizedDownsideDev": None
                if pd.isna(row.get("realized_downside_dev"))
                else float(row.get("realized_downside_dev")),
                "realizedMaxDrawdown": None
                if pd.isna(row.get("realized_max_drawdown"))
                else float(row.get("realized_max_drawdown")),
            }
        )

    monthly_points = [
        {
            "month": forward_months[index],
            "assignedRiskBucket": bucket_returns[index],
            "allEqualWeight": all_equal_returns[index],
            "egx30": egx_returns[index],
        }
        for index in range(len(forward_months))
    ]

    comparison = [
        {"id": "assignedRiskBucket", "label": "Assigned risk bucket equal weight", "metrics": _metrics(bucket_returns)},
        {"id": "allEqualWeight", "label": "All active universe equal weight", "metrics": _metrics(all_equal_returns)},
        {"id": "egx30", "label": "EGX30 benchmark", "metrics": _metrics(egx_returns)},
    ]
    risk_components = _risk_component_rows(
        selected=selected,
        same_month_universe=same_month_universe,
        optimized_weights=selected_weights,
        all_universe_weights=all_universe_weights,
        risk_level=risk_level,
    )
    raw_risk_components = _raw_risk_rows(
        daily_returns=daily_returns,
        month=month,
        selected_weights=selected_weights,
        all_universe_weights=all_universe_weights,
    )

    return {
        "simulationId": str(uuid.uuid4()),
        "month": month,
        "riskLevel": risk_level,
        "split": split,
        "durationMonths": len(forward_months),
        "requestedDurationMonths": duration_months,
        "chartIntervals": _month_interval_days(forward_months),
        "thesisSafeSummary": (
            "This report is a historical simulation diagnostic. It compares realized outcomes after a selected "
            "decision month and should not be read as proof of guaranteed portfolio optimization improvement."
        ),
        "optimizerMode": "mock_equal_weight",
        "selectedAssets": selected_assets,
        "monthlyReturns": monthly_points,
        "comparison": comparison,
        "riskComponents": risk_components,
        "rawRiskComponents": raw_risk_components,
        "assumptions": [
            "Asset selection is fixed at the selected historical decision month.",
            "Equal-weight benchmark returns are computed with the selected month asset set and carried forward.",
            "If an asset has no return in a future month, weights are renormalized across assets with available returns.",
            "Risk-rank components are cross-sectional ranks inside the decision month; lower rank values indicate lower realized component risk.",
        ],
        "requiredExternalContracts": {
            "riskToleranceModel": RISK_TOLERANCE_MODEL_CONTRACT,
            "weightOptimizerModel": WEIGHT_OPTIMIZER_MODEL_CONTRACT,
        },
    }
