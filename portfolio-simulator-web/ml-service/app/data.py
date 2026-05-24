from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .paths import artifact_root

REPO_ROOT = artifact_root()
PPO_ROOT = REPO_ROOT / "model-artifacts" / "ppo-risk-model" if (REPO_ROOT / "model-artifacts").exists() else REPO_ROOT / "ppo-risk-model"
BEST_MODEL_DIR = PPO_ROOT / "outputs" / "best_model"
PREDICTIONS_PATH = BEST_MODEL_DIR / "ranked_predictions.csv"
DAILY_MARKET_PATH = PPO_ROOT / "data" / "ready" / "daily_market_series.csv"
MONTHLY_PANEL_PATH = PPO_ROOT / "data" / "ready" / "monthly_asset_panel.csv"

VALID_SPLITS = {"validation", "test"}
RISK_BUCKETS: dict[str, dict[str, Any]] = {
    "low": {
        "id": "low",
        "label": "Low risk",
        "minRankPct": 0.0,
        "maxRankPct": 0.30,
        "description": "Lowest predicted-risk 30% of the active universe.",
    },
    "medium": {
        "id": "medium",
        "label": "Medium risk",
        "minRankPct": 0.20,
        "maxRankPct": 0.80,
        "description": "Broad central predicted-risk band with overlap into both tails.",
    },
    "high": {
        "id": "high",
        "label": "High risk",
        "minRankPct": 0.70,
        "maxRankPct": 1.0,
        "description": "Highest predicted-risk 30% of the active universe.",
    },
}


def read_predictions() -> pd.DataFrame:
    if not PREDICTIONS_PATH.exists():
        raise FileNotFoundError(f"Missing PPO ranked predictions at {PREDICTIONS_PATH}")
    predictions = pd.read_csv(PREDICTIONS_PATH)
    required = {"Date", "Split", "AssetID", "AssetName", "AssetGroup", "PredictedRisk", "PredictedRankPct"}
    missing = sorted(required.difference(predictions.columns))
    if missing:
        display_missing = ["dataset partition" if column == "Split" else column for column in missing]
        raise ValueError(f"ranked_predictions.csv is missing required fields: {display_missing}")
    predictions["Date"] = predictions["Date"].astype(str)
    predictions["Split"] = predictions["Split"].astype(str)
    predictions["PredictedRisk"] = pd.to_numeric(predictions["PredictedRisk"], errors="coerce")
    predictions["PredictedRankPct"] = pd.to_numeric(predictions["PredictedRankPct"], errors="coerce")
    known_splits = {"train", "inner_validation", *VALID_SPLITS}
    invalid_splits = sorted(set(predictions["Split"].dropna()).difference(known_splits))
    if invalid_splits:
        raise ValueError(f"ranked_predictions.csv contains unsupported dataset partitions: {invalid_splits}")
    if predictions[["Date", "AssetID", "Split"]].isna().any().any():
        raise ValueError("ranked_predictions.csv contains missing Date, AssetID, or dataset partition values.")
    if not np.isfinite(predictions["PredictedRisk"]).all():
        raise ValueError("ranked_predictions.csv contains non-finite PredictedRisk values.")
    if not np.isfinite(predictions["PredictedRankPct"]).all():
        raise ValueError("ranked_predictions.csv contains non-finite PredictedRankPct values.")
    if not predictions["PredictedRankPct"].between(0.0, 1.0, inclusive="both").all():
        raise ValueError("ranked_predictions.csv contains PredictedRankPct values outside [0, 1].")
    duplicate_rows = predictions.duplicated(subset=["Date", "Split", "AssetID"], keep=False)
    if duplicate_rows.any():
        duplicates = (
            predictions.loc[duplicate_rows, ["Date", "Split", "AssetID"]]
            .rename(columns={"Split": "Partition"})
            .head(5)
            .to_dict(orient="records")
        )
        raise ValueError(f"ranked_predictions.csv contains duplicate month/partition/asset rows: {duplicates}")
    split_counts = predictions.groupby("Date")["Split"].nunique()
    multi_split_months = split_counts[split_counts > 1]
    if not multi_split_months.empty:
        sample = ", ".join(str(month) for month in multi_split_months.index[:5])
        raise ValueError(f"ranked_predictions.csv contains multiple dataset partitions for month(s): {sample}")
    return predictions


def read_monthly_returns() -> pd.DataFrame:
    if not DAILY_MARKET_PATH.exists():
        raise FileNotFoundError(f"Missing daily market series at {DAILY_MARKET_PATH}")
    daily = pd.read_csv(DAILY_MARKET_PATH, usecols=["Date", "AssetID", "ReturnFromPrice"])
    daily["Date"] = pd.to_datetime(daily["Date"], errors="coerce")
    daily["ReturnFromPrice"] = pd.to_numeric(daily["ReturnFromPrice"], errors="coerce")
    daily = daily.dropna(subset=["Date", "AssetID", "ReturnFromPrice"]).copy()
    daily["Month"] = daily["Date"].dt.to_period("M").astype(str)
    return (
        daily.groupby(["Month", "AssetID"], sort=True)["ReturnFromPrice"]
        .agg(lambda values: float(np.prod(1.0 + values.to_numpy(dtype=float)) - 1.0))
        .reset_index()
        .rename(columns={"Month": "Date", "ReturnFromPrice": "MonthlyReturn"})
    )


def read_daily_market() -> pd.DataFrame:
    if not DAILY_MARKET_PATH.exists():
        raise FileNotFoundError(f"Missing daily market series at {DAILY_MARKET_PATH}")
    daily = pd.read_csv(
        DAILY_MARKET_PATH,
        usecols=[
            "Date",
            "AssetID",
            "PriceForReturn",
            "OpenPriceForRange",
            "HighPriceForRange",
            "LowPriceForRange",
            "Volume",
            "ReturnFromPrice",
            "IsObserved",
        ],
    )
    daily["Date"] = pd.to_datetime(daily["Date"], errors="coerce")
    daily["IsObserved"] = pd.to_numeric(daily["IsObserved"], errors="coerce").fillna(0).astype(int)
    daily["ReturnFromPrice"] = pd.to_numeric(daily["ReturnFromPrice"], errors="coerce")
    return daily.dropna(subset=["Date", "AssetID", "PriceForReturn"]).copy()


def available_months() -> list[dict[str, Any]]:
    predictions = read_predictions()
    subset = predictions.loc[predictions["Split"].isin(VALID_SPLITS)].copy()
    grouped = (
        subset.groupby("Date", sort=True)["AssetID"]
        .count()
        .reset_index()
        .rename(columns={"Date": "month", "AssetID": "assetCount"})
    )
    return grouped.to_dict(orient="records")


def risk_levels() -> list[dict[str, Any]]:
    return [RISK_BUCKETS[key] for key in ("low", "medium", "high")]


def select_assets(month: str, risk_level: str) -> pd.DataFrame:
    if risk_level not in RISK_BUCKETS:
        raise ValueError(f"Unknown risk level: {risk_level}")
    predictions = read_predictions()
    month_frame = predictions.loc[predictions["Date"].eq(month) & predictions["Split"].isin(VALID_SPLITS)].copy()
    if month_frame.empty:
        raise ValueError(f"No reportable predictions found for month {month}")
    bucket = RISK_BUCKETS[risk_level]
    selected = month_frame.loc[
        month_frame["PredictedRankPct"].between(bucket["minRankPct"], bucket["maxRankPct"], inclusive="both")
    ].copy()
    if selected.empty:
        raise ValueError(f"No selected assets for month {month} and risk level {risk_level}")
    selected = selected.sort_values(["PredictedRankPct", "PredictedRisk", "AssetID"]).reset_index(drop=True)
    return selected
