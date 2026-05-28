from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Literal

from .data import DAILY_MARKET_PATH, MONTHLY_PANEL_PATH, PPO_ROOT, PREDICTIONS_PATH
from .metrics import month_interval_days, performance_metrics, resolve_forward_months
from .precompute.store import (
    STRATEGY_IDS,
    STRATEGY_LABELS,
    connect_runtime_store,
    precomputed_store_available,
)
from .questionnaire import predict_questionnaire_risk, questionnaire_model_available

SimulatorMode = Literal["single", "monthly_rebalance"]


@dataclass(frozen=True)
class DecisionContext:
    month: str
    active_assets: list[dict[str, Any]]
    selected_assets: list[dict[str, Any]]
    optimizer_weight_sum: float
    optimizer_decision_date: str


def health() -> dict[str, Any]:
    questionnaire_available = questionnaire_model_available()
    precomputed_available = precomputed_store_available()
    return {
        "status": "ok"
        if PREDICTIONS_PATH.exists()
        and DAILY_MARKET_PATH.exists()
        and MONTHLY_PANEL_PATH.exists()
        and questionnaire_available
        and precomputed_available
        else "degraded",
        "ppoRootExists": PPO_ROOT.exists(),
        "predictionsAvailable": PREDICTIONS_PATH.exists(),
        "dailyMarketAvailable": DAILY_MARKET_PATH.exists(),
        "monthlyPanelAvailable": MONTHLY_PANEL_PATH.exists(),
        "questionnaireModelAvailable": questionnaire_available,
        "optimizerMode": "external_model" if precomputed_available else "unavailable",
        "optimizerRuntimeAvailable": precomputed_available,
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


def _reportable_months(connection: Any) -> list[str]:
    return [
        str(row["month"])
        for row in connection.execute("SELECT month FROM reportable_months ORDER BY month").fetchall()
    ]


def _build_decision_context(connection: Any, *, month: str, risk_level: str) -> DecisionContext:
    snapshot = connection.execute(
        """
        SELECT
            active_universe_count,
            selected_asset_count,
            selected_optimizer_weight_sum,
            selected_optimizer_decision_date
        FROM decision_snapshots
        WHERE decision_month = ? AND risk_level = ?
        """,
        (month, risk_level),
    ).fetchone()
    if snapshot is None:
        raise ValueError(f"No precomputed simulator decision found for month {month} and risk level {risk_level}")

    rows = connection.execute(
        """
        SELECT
            asset_id,
            asset_name,
            asset_group,
            selected_by_filter,
            equal_weight,
            optimized_weight
        FROM decision_assets
        WHERE decision_month = ? AND risk_level = ?
        ORDER BY active_order
        """,
        (month, risk_level),
    ).fetchall()
    active_assets = [
        {
            "assetId": str(row["asset_id"]),
            "assetName": str(row["asset_name"]),
            "assetGroup": str(row["asset_group"]),
            "selectedByFilter": bool(row["selected_by_filter"]),
            "equalWeight": float(row["equal_weight"]) if row["selected_by_filter"] else None,
            "optimizedWeight": float(row["optimized_weight"]) if row["selected_by_filter"] else None,
        }
        for row in rows
    ]
    selected_assets = [asset for asset in active_assets if asset["selectedByFilter"]]
    if len(active_assets) != int(snapshot["active_universe_count"]):
        raise ValueError(f"Precomputed active universe count mismatch for {month}/{risk_level}")
    if len(selected_assets) != int(snapshot["selected_asset_count"]):
        raise ValueError(f"Precomputed selected asset count mismatch for {month}/{risk_level}")

    return DecisionContext(
        month=month,
        active_assets=active_assets,
        selected_assets=selected_assets,
        optimizer_weight_sum=float(snapshot["selected_optimizer_weight_sum"]),
        optimizer_decision_date=str(snapshot["selected_optimizer_decision_date"]),
    )


def _monthly_point(
    connection: Any,
    *,
    risk_level: str,
    decision_month: str,
    return_month: str,
) -> dict[str, Any]:
    rows = connection.execute(
        """
        SELECT strategy_id, monthly_return
        FROM strategy_monthly_returns
        WHERE decision_month = ? AND risk_level = ? AND return_month = ?
        """,
        (decision_month, risk_level, return_month),
    ).fetchall()
    returns = {str(row["strategy_id"]): float(row["monthly_return"]) for row in rows}
    missing = [strategy_id for strategy_id in STRATEGY_IDS if strategy_id not in returns]
    if missing:
        raise ValueError(
            f"Precomputed monthly returns are missing for {decision_month}/{risk_level}/{return_month}: {missing}"
        )
    return {
        "month": return_month,
        "optimizedPortfolio": returns["optimizedPortfolio"],
        "optimizerFullUniverse": returns["optimizerFullUniverse"],
        "mvoFilteredUniverse": returns["mvoFilteredUniverse"],
        "mvoFullUniverse": returns["mvoFullUniverse"],
        "egx30": returns["egx30"],
    }


def _comparison_rows(monthly_points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": strategy_id,
            "label": STRATEGY_LABELS[strategy_id],
            "metrics": performance_metrics([float(point[strategy_id]) for point in monthly_points]),
        }
        for strategy_id in STRATEGY_IDS
    ]


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


def _thesis_safe_summary(simulator_mode: SimulatorMode, duration_months: int) -> str:
    if simulator_mode == "monthly_rebalance":
        return (
            "This report is a historical monthly review diagnostic. It reapplies profile selection and "
            "weighting at each plotted month, compounds realized monthly outcomes, and should not be read "
            "as proof of guaranteed investment performance."
        )
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
        "comparison": _comparison_rows(monthly_points),
        "pipeline": _pipeline_from_context(initial_context),
        "rebalanceTimeline": rebalance_timeline,
        "questionnaireInference": None,
    }


def _run_single_simulation(
    *,
    connection: Any,
    month: str,
    risk_level: str,
    duration_months: int | None,
    forward_months: list[str],
) -> dict[str, Any]:
    context = _build_decision_context(connection, month=month, risk_level=risk_level)
    monthly_points = [
        _monthly_point(connection, risk_level=risk_level, decision_month=month, return_month=return_month)
        for return_month in forward_months
    ]
    rebalance_timeline = [
        _timeline_point(
            context,
            starting_value=1.0,
            monthly_return=float(monthly_points[0]["optimizedPortfolio"]) if monthly_points else 0.0,
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
        rebalance_timeline=rebalance_timeline,
    )


def _run_monthly_rebalance_simulation(
    *,
    connection: Any,
    month: str,
    risk_level: str,
    duration_months: int | None,
    forward_months: list[str],
) -> dict[str, Any]:
    initial_context: DecisionContext | None = None
    monthly_points: list[dict[str, Any]] = []
    rebalance_timeline: list[dict[str, Any]] = []
    current_value = 1.0

    for decision_month in forward_months:
        context = _build_decision_context(connection, month=decision_month, risk_level=risk_level)
        if initial_context is None:
            initial_context = context
        point = _monthly_point(
            connection,
            risk_level=risk_level,
            decision_month=decision_month,
            return_month=decision_month,
        )
        monthly_return = float(point["optimizedPortfolio"])
        monthly_points.append(point)
        rebalance_timeline.append(
            _timeline_point(context, starting_value=current_value, monthly_return=monthly_return)
        )
        current_value *= 1.0 + monthly_return

    if initial_context is None:
        raise ValueError(f"No forward return window is available for month {month}")

    return _build_report(
        month=month,
        risk_level=risk_level,
        simulator_mode="monthly_rebalance",
        duration_months=duration_months,
        forward_months=forward_months,
        initial_context=initial_context,
        monthly_points=monthly_points,
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

    with connect_runtime_store() as connection:
        forward_months = resolve_forward_months(_reportable_months(connection), month, duration_months)
        if not forward_months:
            raise ValueError(f"No forward return window is available for month {month}")

        if simulator_mode == "monthly_rebalance":
            return _run_monthly_rebalance_simulation(
                connection=connection,
                month=month,
                risk_level=risk_level,
                duration_months=duration_months,
                forward_months=forward_months,
            )

        return _run_single_simulation(
            connection=connection,
            month=month,
            risk_level=risk_level,
            duration_months=duration_months,
            forward_months=forward_months,
        )
