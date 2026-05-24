from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Literal

from .data import (
    DAILY_MARKET_PATH,
    MONTHLY_PANEL_PATH,
    PPO_ROOT,
    PREDICTIONS_PATH,
    VALID_SPLITS,
    read_daily_market,
    read_daily_market_index,
    read_monthly_returns,
    read_predictions,
    select_assets,
)
from .metrics import (
    egx30_returns,
    equal_weights,
    index_monthly_returns,
    month_interval_days,
    performance_metrics,
    portfolio_monthly_returns,
    resolve_forward_months,
)
from .mvo import run_mvo_allocation
from .optimizer import optimizer_available, optimizer_runtime_available, run_weight_optimizer
from .questionnaire import predict_questionnaire_risk, questionnaire_model_available

SimulatorMode = Literal["single", "monthly_rebalance"]


@dataclass(frozen=True)
class DecisionContext:
    month: str
    active_assets: list[dict[str, Any]]
    selected_assets: list[dict[str, Any]]
    selected_equal_weights: dict[str, float]
    selected_optimizer_weights: dict[str, float]
    full_universe_optimizer_weights: dict[str, float]
    selected_mvo_weights: dict[str, float]
    full_universe_mvo_weights: dict[str, float]
    optimizer_weight_sum: float
    optimizer_decision_date: str


def health() -> dict[str, Any]:
    questionnaire_available = questionnaire_model_available()
    optimizer_is_available = optimizer_available()
    optimizer_runtime_is_available = optimizer_runtime_available()
    return {
        "status": "ok"
        if PREDICTIONS_PATH.exists()
        and DAILY_MARKET_PATH.exists()
        and MONTHLY_PANEL_PATH.exists()
        and questionnaire_available
        and optimizer_is_available
        and optimizer_runtime_is_available
        else "degraded",
        "ppoRootExists": PPO_ROOT.exists(),
        "predictionsAvailable": PREDICTIONS_PATH.exists(),
        "dailyMarketAvailable": DAILY_MARKET_PATH.exists(),
        "monthlyPanelAvailable": MONTHLY_PANEL_PATH.exists(),
        "questionnaireModelAvailable": questionnaire_available,
        "optimizerMode": "external_model" if optimizer_is_available else "unavailable",
        "optimizerRuntimeAvailable": optimizer_runtime_is_available,
    }


def run_questionnaire_simulation(
    month: str,
    questionnaire: dict[str, Any],
    duration_months: int | None = None,
    simulator_mode: SimulatorMode = "single",
) -> dict[str, Any]:
    inference = predict_questionnaire_risk(questionnaire)
    report = run_fast_simulation(month, str(inference["riskLevel"]), duration_months, simulator_mode)
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


def _build_decision_context(
    *,
    month: str,
    risk_level: str,
    predictions: Any,
    daily_market: Any,
) -> DecisionContext:
    try:
        selected = select_assets(month, risk_level, predictions=predictions)
    except ValueError as exc:
        raise ValueError(f"{exc} while building simulator decision for {month}") from exc

    selected_asset_ids = selected["AssetID"].astype(str).tolist()
    selected_equal_weights = equal_weights(selected_asset_ids)

    same_month_universe = predictions.loc[
        predictions["Date"].eq(month) & predictions["Split"].isin(VALID_SPLITS)
    ].copy()
    if same_month_universe.empty:
        raise ValueError(f"No reportable predictions found for month {month}")
    all_universe_asset_ids = same_month_universe["AssetID"].astype(str).tolist()

    optimized_selected = run_weight_optimizer(
        tier=risk_level,
        target_month=month,
        asset_ids=selected_asset_ids,
        daily_market=daily_market,
    )
    optimized_full_universe = run_weight_optimizer(
        tier=risk_level,
        target_month=month,
        asset_ids=all_universe_asset_ids,
        daily_market=daily_market,
    )
    mvo_selected = run_mvo_allocation(
        risk_level=risk_level,
        target_month=month,
        asset_ids=selected_asset_ids,
        daily_market=daily_market,
    )
    mvo_full_universe = run_mvo_allocation(
        risk_level=risk_level,
        target_month=month,
        asset_ids=all_universe_asset_ids,
        daily_market=daily_market,
    )

    selected_id_set = set(selected_asset_ids)
    active_assets = [
        _pipeline_asset(row, selected_id_set, selected_equal_weights, optimized_selected.weights)
        for _, row in same_month_universe.iterrows()
    ]
    selected_assets = [asset for asset in active_assets if asset["selectedByFilter"]]

    return DecisionContext(
        month=month,
        active_assets=active_assets,
        selected_assets=selected_assets,
        selected_equal_weights=selected_equal_weights,
        selected_optimizer_weights=optimized_selected.weights,
        full_universe_optimizer_weights=optimized_full_universe.weights,
        selected_mvo_weights=mvo_selected.weights,
        full_universe_mvo_weights=mvo_full_universe.weights,
        optimizer_weight_sum=optimized_selected.sum_check,
        optimizer_decision_date=optimized_selected.decision_date,
    )


def _portfolio_return_for_month(monthly_returns: Any, month: str, weights: dict[str, float]) -> float:
    return portfolio_monthly_returns(monthly_returns, [month], weights)[0]


def _timeline_point(
    context: DecisionContext,
    *,
    starting_value: float,
    monthly_return: float,
) -> dict[str, Any]:
    ending_value = starting_value * (1.0 + monthly_return)
    return {
        "month": context.month,
        "optimizerDecisionDate": context.optimizer_decision_date,
        "startingValue": float(starting_value),
        "monthlyReturn": float(monthly_return),
        "endingValue": float(ending_value),
        "activeUniverseCount": len(context.active_assets),
        "selectedAssetCount": len(context.selected_assets),
        "optimizerWeightSum": context.optimizer_weight_sum,
        "selectedAssets": context.selected_assets,
    }


def _pipeline_from_context(context: DecisionContext) -> dict[str, Any]:
    return {
        "activeUniverse": context.active_assets,
        "selectedAssets": context.selected_assets,
        "activeUniverseCount": len(context.active_assets),
        "selectedAssetCount": len(context.selected_assets),
        "optimizerWeightSum": context.optimizer_weight_sum,
        "optimizerDecisionDate": context.optimizer_decision_date,
    }


def _monthly_points(
    months: list[str],
    optimized_returns: list[float],
    optimizer_full_universe_returns: list[float],
    mvo_filtered_universe_returns: list[float],
    mvo_full_universe_returns: list[float],
    egx_returns: list[float],
) -> list[dict[str, Any]]:
    return [
        {
            "month": months[index],
            "optimizedPortfolio": optimized_returns[index],
            "optimizerFullUniverse": optimizer_full_universe_returns[index],
            "mvoFilteredUniverse": mvo_filtered_universe_returns[index],
            "mvoFullUniverse": mvo_full_universe_returns[index],
            "egx30": egx_returns[index],
        }
        for index in range(len(months))
    ]


def _comparison_rows(
    *,
    optimized_returns: list[float],
    optimizer_full_universe_returns: list[float],
    mvo_filtered_universe_returns: list[float],
    mvo_full_universe_returns: list[float],
    egx_returns: list[float],
) -> list[dict[str, Any]]:
    return [
        {
            "id": "optimizedPortfolio",
            "label": "Profile optimizer portfolio",
            "metrics": performance_metrics(optimized_returns),
        },
        {
            "id": "optimizerFullUniverse",
            "label": "Full-universe optimizer benchmark",
            "metrics": performance_metrics(optimizer_full_universe_returns),
        },
        {
            "id": "mvoFilteredUniverse",
            "label": "Profile MVO benchmark",
            "metrics": performance_metrics(mvo_filtered_universe_returns),
        },
        {
            "id": "mvoFullUniverse",
            "label": "Full-universe MVO benchmark",
            "metrics": performance_metrics(mvo_full_universe_returns),
        },
        {"id": "egx30", "label": "EGX30", "metrics": performance_metrics(egx_returns)},
    ]


def _thesis_safe_summary(simulator_mode: SimulatorMode, duration_months: int) -> str:
    if simulator_mode == "monthly_rebalance":
        summary = (
            "This report is a historical monthly review diagnostic. It reapplies profile selection and "
            "weighting at each plotted month, compounds realized monthly outcomes, and should not be read "
            "as proof of guaranteed investment performance."
        )
        if duration_months >= 6:
            summary += (
                " Long monthly review windows can take noticeably longer because profile selection and "
                "weighting are recomputed each month."
            )
        return summary
    return (
        "This report is a historical simulation diagnostic. It compares realized outcomes after profile "
        "selection and weighting are applied for the requested month range and should not be read as proof "
        "of guaranteed investment performance."
    )


def _build_report(
    *,
    month: str,
    risk_level: str,
    simulator_mode: SimulatorMode,
    duration_months: int | None,
    forward_months: list[str],
    initial_context: DecisionContext,
    monthly_points: list[dict[str, Any]],
    comparison: list[dict[str, Any]],
    rebalance_timeline: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "simulationId": str(uuid.uuid4()),
        "month": month,
        "riskLevel": risk_level,
        "simulatorMode": simulator_mode,
        "durationMonths": len(forward_months),
        "requestedDurationMonths": duration_months,
        "chartIntervals": month_interval_days(forward_months),
        "thesisSafeSummary": _thesis_safe_summary(simulator_mode, len(forward_months)),
        "optimizerMode": "external_model",
        "monthlyReturns": monthly_points,
        "comparison": comparison,
        "pipeline": _pipeline_from_context(initial_context),
        "rebalanceTimeline": rebalance_timeline,
        "questionnaireInference": None,
    }


def _run_single_simulation(
    *,
    month: str,
    risk_level: str,
    duration_months: int | None,
    forward_months: list[str],
    predictions: Any,
    monthly_returns: Any,
    daily_market: Any,
) -> dict[str, Any]:
    context = _build_decision_context(
        month=month,
        risk_level=risk_level,
        predictions=predictions,
        daily_market=daily_market,
    )
    optimized_returns = portfolio_monthly_returns(monthly_returns, forward_months, context.selected_optimizer_weights)
    optimizer_full_universe_returns = portfolio_monthly_returns(
        monthly_returns, forward_months, context.full_universe_optimizer_weights
    )
    mvo_filtered_universe_returns = portfolio_monthly_returns(
        monthly_returns, forward_months, context.selected_mvo_weights
    )
    mvo_full_universe_returns = portfolio_monthly_returns(
        monthly_returns, forward_months, context.full_universe_mvo_weights
    )
    egx_returns = egx30_returns(monthly_returns, forward_months)
    monthly_points = _monthly_points(
        forward_months,
        optimized_returns,
        optimizer_full_universe_returns,
        mvo_filtered_universe_returns,
        mvo_full_universe_returns,
        egx_returns,
    )
    comparison = _comparison_rows(
        optimized_returns=optimized_returns,
        optimizer_full_universe_returns=optimizer_full_universe_returns,
        mvo_filtered_universe_returns=mvo_filtered_universe_returns,
        mvo_full_universe_returns=mvo_full_universe_returns,
        egx_returns=egx_returns,
    )
    rebalance_timeline = [
        _timeline_point(
            context,
            starting_value=1.0,
            monthly_return=optimized_returns[0] if optimized_returns else 0.0,
        )
    ]

    return _build_report(
        month=month,
        risk_level=risk_level,
        simulator_mode="single",
        duration_months=duration_months,
        forward_months=forward_months,
        initial_context=context,
        monthly_points=monthly_points,
        comparison=comparison,
        rebalance_timeline=rebalance_timeline,
    )


def _run_monthly_rebalance_simulation(
    *,
    month: str,
    risk_level: str,
    duration_months: int | None,
    forward_months: list[str],
    predictions: Any,
    monthly_returns: Any,
    daily_market: Any,
) -> dict[str, Any]:
    initial_context: DecisionContext | None = None
    optimized_returns: list[float] = []
    optimizer_full_universe_returns: list[float] = []
    mvo_filtered_universe_returns: list[float] = []
    mvo_full_universe_returns: list[float] = []
    rebalance_timeline: list[dict[str, Any]] = []
    current_value = 1.0

    for decision_month in forward_months:
        context = _build_decision_context(
            month=decision_month,
            risk_level=risk_level,
            predictions=predictions,
            daily_market=daily_market,
        )
        if initial_context is None:
            initial_context = context

        optimized_return = _portfolio_return_for_month(
            monthly_returns, decision_month, context.selected_optimizer_weights
        )
        optimizer_full_return = _portfolio_return_for_month(
            monthly_returns, decision_month, context.full_universe_optimizer_weights
        )
        mvo_filtered_return = _portfolio_return_for_month(
            monthly_returns, decision_month, context.selected_mvo_weights
        )
        mvo_return = _portfolio_return_for_month(
            monthly_returns, decision_month, context.full_universe_mvo_weights
        )

        optimized_returns.append(optimized_return)
        optimizer_full_universe_returns.append(optimizer_full_return)
        mvo_filtered_universe_returns.append(mvo_filtered_return)
        mvo_full_universe_returns.append(mvo_return)
        rebalance_timeline.append(
            _timeline_point(context, starting_value=current_value, monthly_return=optimized_return)
        )
        current_value *= 1.0 + optimized_return

    if initial_context is None:
        raise ValueError(f"No forward return window is available for month {month}")

    egx_returns = egx30_returns(monthly_returns, forward_months)
    monthly_points = _monthly_points(
        forward_months,
        optimized_returns,
        optimizer_full_universe_returns,
        mvo_filtered_universe_returns,
        mvo_full_universe_returns,
        egx_returns,
    )
    comparison = _comparison_rows(
        optimized_returns=optimized_returns,
        optimizer_full_universe_returns=optimizer_full_universe_returns,
        mvo_filtered_universe_returns=mvo_filtered_universe_returns,
        mvo_full_universe_returns=mvo_full_universe_returns,
        egx_returns=egx_returns,
    )

    return _build_report(
        month=month,
        risk_level=risk_level,
        simulator_mode="monthly_rebalance",
        duration_months=duration_months,
        forward_months=forward_months,
        initial_context=initial_context,
        monthly_points=monthly_points,
        comparison=comparison,
        rebalance_timeline=rebalance_timeline,
    )


def run_fast_simulation(
    month: str,
    risk_level: str,
    duration_months: int | None = None,
    simulator_mode: SimulatorMode = "single",
) -> dict[str, Any]:
    if simulator_mode not in {"single", "monthly_rebalance"}:
        raise ValueError(f"Unknown simulator mode: {simulator_mode}")

    predictions = read_predictions()
    monthly_returns = read_monthly_returns()
    monthly_return_index = index_monthly_returns(monthly_returns)
    daily_market = read_daily_market_index()
    reporting_months = sorted(
        set(monthly_returns["Date"].astype(str)).intersection(
            predictions.loc[predictions["Split"].isin(VALID_SPLITS), "Date"].astype(str)
        )
    )
    forward_months = resolve_forward_months(reporting_months, month, duration_months)
    if not forward_months:
        raise ValueError(f"No forward return window is available for month {month}")

    if simulator_mode == "monthly_rebalance":
        return _run_monthly_rebalance_simulation(
            month=month,
            risk_level=risk_level,
            duration_months=duration_months,
            forward_months=forward_months,
            predictions=predictions,
            monthly_returns=monthly_return_index,
            daily_market=daily_market,
        )

    return _run_single_simulation(
        month=month,
        risk_level=risk_level,
        duration_months=duration_months,
        forward_months=forward_months,
        predictions=predictions,
        monthly_returns=monthly_return_index,
        daily_market=daily_market,
    )
