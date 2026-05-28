"""Shared month-level metrics for PPO training and evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src import config
from src.training.panel_utils import split_name_for_month
from src.training.experiment_profiles import (
    ObjectiveProfile,
    RewardProfile,
    get_objective_profile,
    get_reward_profile,
)


PREDICTION_COLUMN = "PredictedRisk"


@dataclass(frozen=True)
class MonthMetrics:
    date: str
    split: str
    active_assets: int
    spearman: float
    mse: float
    high_risk_top25_overlap: float
    low_risk_top25_overlap: float
    reward: float


def _tail_count(active_assets: int) -> int:
    return max(1, int(math.ceil(active_assets * 0.25)))


def _top_overlap(predicted: np.ndarray, realized: np.ndarray, highest: bool) -> float:
    active_count = int(predicted.size)
    tail_count = _tail_count(active_count)
    predicted_order = np.argsort(predicted, kind="mergesort")
    realized_order = np.argsort(realized, kind="mergesort")
    if highest:
        predicted_tail = set(predicted_order[-tail_count:].tolist())
        realized_tail = set(realized_order[-tail_count:].tolist())
    else:
        predicted_tail = set(predicted_order[:tail_count].tolist())
        realized_tail = set(realized_order[:tail_count].tolist())
    return float(len(predicted_tail & realized_tail) / tail_count)


def compute_month_metrics(
    predicted: np.ndarray,
    realized: np.ndarray,
    date: str,
    reward_profile: str | RewardProfile = "reward_v1_rank70_mse30",
) -> MonthMetrics:
    predicted_values = np.asarray(predicted, dtype=float)
    realized_values = np.asarray(realized, dtype=float)
    if predicted_values.shape != realized_values.shape:
        raise ValueError("Predicted and realized arrays must have the same shape.")
    if predicted_values.ndim != 1:
        raise ValueError("Predicted and realized arrays must be one-dimensional.")
    if predicted_values.size < config.MIN_ASSETS_PER_MONTH:
        raise ValueError("Month-level metrics require at least the minimum number of active assets.")

    profile = reward_profile if isinstance(reward_profile, RewardProfile) else get_reward_profile(reward_profile)

    spearman = float(spearmanr(predicted_values, realized_values).statistic)
    if np.isnan(spearman):
        spearman = 0.0
    mse = float(np.mean(np.square(predicted_values - realized_values)))
    high_overlap = _top_overlap(predicted_values, realized_values, highest=True)
    low_overlap = _top_overlap(predicted_values, realized_values, highest=False)
    reward = float(
        (profile.spearman_weight * spearman)
        + (profile.mse_weight * (1.0 - mse))
        + (profile.high_risk_overlap_weight * high_overlap)
    )
    return MonthMetrics(
        date=date,
        split=split_name_for_month(date),
        active_assets=int(predicted_values.size),
        spearman=spearman,
        mse=mse,
        high_risk_top25_overlap=high_overlap,
        low_risk_top25_overlap=low_overlap,
        reward=reward,
    )


def tail_overlap_details(
    month_frame: pd.DataFrame,
    score_column: str = PREDICTION_COLUMN,
    target_column: str = "realized_risk",
) -> dict[str, Any]:
    active_count = int(len(month_frame))
    tail_count = _tail_count(active_count)
    predicted_high = set(month_frame.nlargest(tail_count, score_column, keep="first")["AssetID"].astype(str))
    realized_high = set(month_frame.nlargest(tail_count, target_column, keep="first")["AssetID"].astype(str))
    predicted_low = set(month_frame.nsmallest(tail_count, score_column, keep="first")["AssetID"].astype(str))
    realized_low = set(month_frame.nsmallest(tail_count, target_column, keep="first")["AssetID"].astype(str))
    return {
        "tail_count": tail_count,
        "high_risk_top25_overlap": float(len(predicted_high & realized_high) / tail_count),
        "low_risk_top25_overlap": float(len(predicted_low & realized_low) / tail_count),
        "high_risk_top25_missed": ",".join(sorted(realized_high - predicted_high)),
        "high_risk_top25_false_positives": ",".join(sorted(predicted_high - realized_high)),
    }


def add_prediction_ranks(predictions: pd.DataFrame, score_column: str = PREDICTION_COLUMN) -> pd.DataFrame:
    ranked = predictions.copy()
    if "Split" not in ranked.columns:
        ranked["Split"] = ranked["Date"].astype(str).map(split_name_for_month)
    ranked["PredictedRank"] = ranked.groupby("Date")[score_column].rank(method="average", ascending=True)
    month_sizes = ranked.groupby("Date")[score_column].transform("count")
    ranked["PredictedRankPct"] = np.where(
        month_sizes <= 1,
        0.5,
        (ranked["PredictedRank"] - 1.0) / (month_sizes - 1.0),
    )
    ranked["PredictionError"] = ranked[score_column] - ranked["realized_risk"]
    return ranked


def evaluate_prediction_frame(
    predictions: pd.DataFrame,
    score_column: str = PREDICTION_COLUMN,
    target_column: str = "realized_risk",
    reward_profile: str | RewardProfile = "reward_v1_rank70_mse30",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required_columns = {"Date", "AssetID", score_column, target_column}
    missing = required_columns.difference(predictions.columns)
    if missing:
        raise ValueError(f"Predictions are missing required columns: {sorted(missing)}")

    monthly_rows: list[dict[str, Any]] = []
    for date, month_frame in predictions.groupby("Date", sort=True):
        metrics = compute_month_metrics(
            predicted=month_frame[score_column].to_numpy(dtype=float),
            realized=month_frame[target_column].to_numpy(dtype=float),
            date=str(date),
            reward_profile=reward_profile,
        )
        row = asdict(metrics)
        if "Split" in month_frame.columns and month_frame["Split"].notna().any():
            row["split"] = str(month_frame["Split"].iloc[0])
        row.update(tail_overlap_details(month_frame, score_column=score_column, target_column=target_column))
        monthly_rows.append(row)

    monthly_metrics = pd.DataFrame.from_records(monthly_rows).sort_values("date").reset_index(drop=True)
    split_summary = (
        monthly_metrics.groupby("split", sort=False)
        .agg(
            months=("date", "count"),
            mean_active_assets=("active_assets", "mean"),
            mean_spearman=("spearman", "mean"),
            mean_mse=("mse", "mean"),
            mean_high_risk_top25_overlap=("high_risk_top25_overlap", "mean"),
            worst_high_risk_top25_overlap=("high_risk_top25_overlap", "min"),
            mean_low_risk_top25_overlap=("low_risk_top25_overlap", "mean"),
            worst_low_risk_top25_overlap=("low_risk_top25_overlap", "min"),
            mean_reward=("reward", "mean"),
            total_reward=("reward", "sum"),
        )
        .reset_index()
    )
    split_summary["mean_active_assets"] = split_summary["mean_active_assets"].astype(float)
    return monthly_metrics, split_summary


def apply_objective_profile(
    panel: pd.DataFrame,
    objective_profile: str | ObjectiveProfile = "risk_v1_equal_333",
) -> pd.DataFrame:
    profile = objective_profile if isinstance(objective_profile, ObjectiveProfile) else get_objective_profile(objective_profile)
    adjusted = panel.copy()
    adjusted["realized_risk"] = profile.compute_realized_risk(adjusted)
    adjusted["realized_rank"] = adjusted.groupby("Date")["realized_risk"].rank(method="average", ascending=True)
    return adjusted
