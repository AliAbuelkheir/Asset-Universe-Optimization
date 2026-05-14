from __future__ import annotations

import uuid
from typing import Any

from .data import (
    DAILY_MARKET_PATH,
    MONTHLY_PANEL_PATH,
    PPO_ROOT,
    PREDICTIONS_PATH,
    VALID_SPLITS,
    read_daily_market,
    read_monthly_returns,
    read_predictions,
    select_assets,
)
from .metrics import (
    egx30_returns,
    equal_weights,
    month_interval_days,
    performance_metrics,
    portfolio_monthly_returns,
    resolve_forward_months,
)
from .optimizer import optimizer_available, run_weight_optimizer
from .questionnaire import predict_questionnaire_risk, questionnaire_model_available


def health() -> dict[str, Any]:
    questionnaire_available = questionnaire_model_available()
    optimizer_is_available = optimizer_available()
    return {
        "status": "ok"
        if PREDICTIONS_PATH.exists()
        and DAILY_MARKET_PATH.exists()
        and MONTHLY_PANEL_PATH.exists()
        and questionnaire_available
        and optimizer_is_available
        else "degraded",
        "ppoRootExists": PPO_ROOT.exists(),
        "predictionsAvailable": PREDICTIONS_PATH.exists(),
        "dailyMarketAvailable": DAILY_MARKET_PATH.exists(),
        "monthlyPanelAvailable": MONTHLY_PANEL_PATH.exists(),
        "questionnaireModelAvailable": questionnaire_available,
        "optimizerMode": "external_model" if optimizer_is_available else "unavailable",
    }


def run_questionnaire_simulation(
    month: str,
    questionnaire: dict[str, Any],
    duration_months: int | None = None,
) -> dict[str, Any]:
    inference = predict_questionnaire_risk(questionnaire)
    report = run_fast_simulation(month, str(inference["riskLevel"]), duration_months)
    report["questionnaireInference"] = inference
    return report


def _pipeline_asset(
    row: Any,
    selected_ids: set[str],
    selected_equal_weights: dict[str, float],
    selected_optimizer_weights: dict[str, float],
) -> dict[str, Any]:
    asset_id = str(row["AssetID"])
    selected_by_filter = asset_id in selected_ids
    return {
        "assetId": asset_id,
        "assetName": str(row["AssetName"]),
        "assetGroup": str(row["AssetGroup"]),
        "selectedByFilter": selected_by_filter,
        "equalWeight": selected_equal_weights.get(asset_id) if selected_by_filter else None,
        "optimizedWeight": selected_optimizer_weights.get(asset_id) if selected_by_filter else None,
    }


def run_fast_simulation(month: str, risk_level: str, duration_months: int | None = None) -> dict[str, Any]:
    selected, split = select_assets(month, risk_level)
    predictions = read_predictions()
    monthly_returns = read_monthly_returns()
    daily_market = read_daily_market()
    all_months = sorted(monthly_returns["Date"].astype(str).unique())
    forward_months = resolve_forward_months(all_months, month, duration_months)
    if not forward_months:
        raise ValueError(f"No forward return window is available for month {month}")

    selected_asset_ids = selected["AssetID"].astype(str).tolist()
    selected_weights = equal_weights(selected_asset_ids)

    same_month_universe = predictions.loc[
        predictions["Date"].eq(month) & predictions["Split"].isin(VALID_SPLITS)
    ].copy()
    all_universe_asset_ids = same_month_universe["AssetID"].astype(str).tolist()
    all_universe_weights = equal_weights(all_universe_asset_ids)

    optimized_selected = run_weight_optimizer(
        tier=risk_level,
        target_month=month,
        asset_ids=selected_asset_ids,
        daily_market=daily_market,
    )
    optimized_raw_universe = run_weight_optimizer(
        tier=risk_level,
        target_month=month,
        asset_ids=all_universe_asset_ids,
        daily_market=daily_market,
    )

    optimized_returns = portfolio_monthly_returns(monthly_returns, forward_months, optimized_selected.weights)
    optimized_raw_universe_returns = portfolio_monthly_returns(
        monthly_returns, forward_months, optimized_raw_universe.weights
    )
    bucket_returns = portfolio_monthly_returns(monthly_returns, forward_months, selected_weights)
    all_equal_returns = portfolio_monthly_returns(monthly_returns, forward_months, all_universe_weights)
    egx_returns = egx30_returns(monthly_returns, forward_months)

    monthly_points = [
        {
            "month": forward_months[index],
            "optimizedPortfolio": optimized_returns[index],
            "optimizedRawUniverse": optimized_raw_universe_returns[index],
            "assignedRiskBucket": bucket_returns[index],
            "allEqualWeight": all_equal_returns[index],
            "egx30": egx_returns[index],
        }
        for index in range(len(forward_months))
    ]

    selected_id_set = set(selected_asset_ids)
    active_assets = [
        _pipeline_asset(row, selected_id_set, selected_weights, optimized_selected.weights)
        for _, row in same_month_universe.iterrows()
    ]
    selected_assets = [asset for asset in active_assets if asset["selectedByFilter"]]

    comparison = [
        {
            "id": "optimizedPortfolio",
            "label": "Full pipeline: PPO-filtered assets + optimizer weights",
            "metrics": performance_metrics(optimized_returns),
        },
        {
            "id": "optimizedRawUniverse",
            "label": "Skip asset filter: all active assets + optimizer weights",
            "metrics": performance_metrics(optimized_raw_universe_returns),
        },
        {
            "id": "assignedRiskBucket",
            "label": "Skip weight optimizer: PPO-filtered assets + equal weights",
            "metrics": performance_metrics(bucket_returns),
        },
        {
            "id": "allEqualWeight",
            "label": "Skip asset filter and optimizer: all active assets + equal weights",
            "metrics": performance_metrics(all_equal_returns),
        },
        {"id": "egx30", "label": "EGX30 index benchmark", "metrics": performance_metrics(egx_returns)},
    ]

    return {
        "simulationId": str(uuid.uuid4()),
        "month": month,
        "riskLevel": risk_level,
        "split": split,
        "durationMonths": len(forward_months),
        "requestedDurationMonths": duration_months,
        "chartIntervals": month_interval_days(forward_months),
        "thesisSafeSummary": (
            "This report is a historical simulation diagnostic. It compares realized outcomes after a selected "
            "decision month and should not be read as proof of guaranteed portfolio optimization improvement. "
            "Optimizer rows show historical outcomes for model weights, not future performance guarantees."
        ),
        "optimizerMode": "external_model",
        "monthlyReturns": monthly_points,
        "comparison": comparison,
        "pipeline": {
            "activeUniverse": active_assets,
            "selectedAssets": selected_assets,
            "activeUniverseCount": len(active_assets),
            "selectedAssetCount": len(selected_assets),
            "optimizerWeightSum": optimized_selected.sum_check,
            "optimizerDecisionDate": optimized_selected.decision_date,
        },
        "questionnaireInference": None,
    }
