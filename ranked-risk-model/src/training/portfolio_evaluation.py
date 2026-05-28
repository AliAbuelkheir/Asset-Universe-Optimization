"""Evaluate ranked-risk predictions through simple bucket portfolio simulations."""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config

PREDICTIONS_FILE_NAME = "ranked_predictions.csv"
MONTHLY_RETURNS_FILE_NAME = "monthly_asset_returns.csv"
BUCKET_RETURNS_FILE_NAME = "bucket_monthly_returns.csv"
BUCKET_SUMMARY_FILE_NAME = "bucket_performance_summary.csv"
MONTHLY_RISK_SEPARATION_FILE_NAME = "monthly_risk_separation.csv"
RANDOM_BENCHMARK_RETURNS_FILE_NAME = "random_bucket_monthly_returns.csv"
RANDOM_BENCHMARK_SUMMARY_FILE_NAME = "random_bucket_summary.csv"
ORACLE_RETURNS_FILE_NAME = "oracle_bucket_monthly_returns.csv"
ORACLE_SUMMARY_FILE_NAME = "oracle_bucket_summary.csv"
SUMMARY_FILE_NAME = "portfolio_evaluation_summary.json"
REPORT_FILE_NAME = "portfolio_evaluation_report.md"
METHOD_COMPARISON_FILE_NAME = "bucket_method_comparison.csv"
METHOD_COMPARISON_REPORT_FILE_NAME = "bucket_method_comparison_report.md"
DEFAULT_RANDOM_REPEATS = 20
DEFAULT_RANDOM_SEED = 20260430


@dataclass(frozen=True)
class BucketSpec:
    bucket_id: str
    label: str
    min_rank_pct: float
    max_rank_pct: float
    description: str


@dataclass(frozen=True)
class BucketMethod:
    method_id: str
    label: str
    description: str
    buckets: tuple[BucketSpec, ...]


DEFAULT_BUCKETS = (
    BucketSpec(
        bucket_id="all_universe",
        label="Full universe",
        min_rank_pct=0.0,
        max_rank_pct=1.0,
        description="Equal-weight investment in every active asset with a model prediction.",
    ),
    BucketSpec(
        bucket_id="low_risk",
        label="Low-risk bucket",
        min_rank_pct=0.0,
        max_rank_pct=0.40,
        description="Lowest predicted-risk 40% of the active universe.",
    ),
    BucketSpec(
        bucket_id="medium_risk",
        label="Medium-risk bucket",
        min_rank_pct=0.25,
        max_rank_pct=0.75,
        description="Middle predicted-risk band with overlap into low and high buckets.",
    ),
    BucketSpec(
        bucket_id="high_risk",
        label="High-risk bucket",
        min_rank_pct=0.60,
        max_rank_pct=1.0,
        description="Highest predicted-risk 40% of the active universe.",
    ),
)


BUCKET_METHODS = {
    "overlap_40_50": BucketMethod(
        method_id="overlap_40_50",
        label="Overlapping 40/50 bands",
        description="Current thesis default: low and high use 40% tails; medium uses the central 50%.",
        buckets=DEFAULT_BUCKETS,
    ),
    "tercile_no_overlap": BucketMethod(
        method_id="tercile_no_overlap",
        label="Non-overlapping terciles",
        description="Three mutually exclusive risk-tolerance groups with roughly equal rank-percentile width.",
        buckets=(
            DEFAULT_BUCKETS[0],
            BucketSpec("low_risk", "Low-risk bucket", 0.0, 1.0 / 3.0, "Lowest predicted-risk third of the active universe."),
            BucketSpec("medium_risk", "Medium-risk bucket", 1.0 / 3.0, 2.0 / 3.0, "Middle predicted-risk third of the active universe."),
            BucketSpec("high_risk", "High-risk bucket", 2.0 / 3.0, 1.0, "Highest predicted-risk third of the active universe."),
        ),
    ),
    "wide_overlap_50_60": BucketMethod(
        method_id="wide_overlap_50_60",
        label="Wide overlapping bands",
        description="More inclusive investor universes: low/high halves and a broad middle 60%.",
        buckets=(
            DEFAULT_BUCKETS[0],
            BucketSpec("low_risk", "Low-risk bucket", 0.0, 0.50, "Lowest predicted-risk half of the active universe."),
            BucketSpec("medium_risk", "Medium-risk bucket", 0.20, 0.80, "Broad central predicted-risk band."),
            BucketSpec("high_risk", "High-risk bucket", 0.50, 1.0, "Highest predicted-risk half of the active universe."),
        ),
    ),
    "tail_30_overlap": BucketMethod(
        method_id="tail_30_overlap",
        label="Narrow tail overlap",
        description="More selective low/high tails with a broad middle bucket for balanced investors.",
        buckets=(
            DEFAULT_BUCKETS[0],
            BucketSpec("low_risk", "Low-risk bucket", 0.0, 0.30, "Lowest predicted-risk 30% of the active universe."),
            BucketSpec("medium_risk", "Medium-risk bucket", 0.20, 0.80, "Broad central predicted-risk band with overlap into both tails."),
            BucketSpec("high_risk", "High-risk bucket", 0.70, 1.0, "Highest predicted-risk 30% of the active universe."),
        ),
    ),
}

DEFAULT_BUCKET_METHOD_ID = "overlap_40_50"
DEFAULT_COMPARE_BUCKET_METHOD_IDS = tuple(BUCKET_METHODS)


def load_predictions(artifact_dir: str | Path) -> pd.DataFrame:
    predictions_path = Path(artifact_dir).resolve() / PREDICTIONS_FILE_NAME
    if not predictions_path.exists():
        raise FileNotFoundError(f"Missing ranked predictions artifact: {predictions_path}")
    predictions = pd.read_csv(predictions_path)
    required = {"Date", "Split", "AssetID", "PredictedRisk"}
    missing = sorted(required.difference(predictions.columns))
    if missing:
        raise ValueError(f"Prediction artifact is missing required columns: {', '.join(missing)}")
    return _ensure_predicted_rank_pct(predictions)


def _ensure_predicted_rank_pct(predictions: pd.DataFrame) -> pd.DataFrame:
    prepared = predictions.copy()
    prepared["Date"] = prepared["Date"].astype(str)
    prepared["Split"] = prepared["Split"].astype(str)
    prepared["PredictedRisk"] = pd.to_numeric(prepared["PredictedRisk"], errors="coerce")
    if prepared["PredictedRisk"].isna().any():
        raise ValueError("PredictedRisk contains missing or non-numeric values.")

    if "PredictedRankPct" not in prepared.columns:
        prepared["PredictedRank"] = prepared.groupby("Date")["PredictedRisk"].rank(method="average", ascending=True)
        month_sizes = prepared.groupby("Date")["AssetID"].transform("count")
        prepared["PredictedRankPct"] = np.where(
            month_sizes <= 1,
            0.5,
            (prepared["PredictedRank"] - 1.0) / (month_sizes - 1.0),
        )
    else:
        prepared["PredictedRankPct"] = pd.to_numeric(prepared["PredictedRankPct"], errors="coerce")
    if prepared["PredictedRankPct"].isna().any():
        raise ValueError("PredictedRankPct contains missing or non-numeric values.")
    if "realized_risk" in prepared.columns:
        prepared["realized_risk"] = pd.to_numeric(prepared["realized_risk"], errors="coerce")
    return prepared


def compute_monthly_asset_returns(daily_market_series: str | Path) -> pd.DataFrame:
    daily_path = Path(daily_market_series).resolve()
    if not daily_path.exists():
        raise FileNotFoundError(f"Missing daily market series: {daily_path}")

    daily = pd.read_csv(daily_path, usecols=["Date", "AssetID", "ReturnFromPrice"])
    daily["Date"] = pd.to_datetime(daily["Date"], errors="coerce")
    daily["ReturnFromPrice"] = pd.to_numeric(daily["ReturnFromPrice"], errors="coerce")
    daily = daily.dropna(subset=["Date", "AssetID", "ReturnFromPrice"]).copy()
    daily["Month"] = daily["Date"].dt.strftime(config.DATE_FORMAT_MONTHLY)

    monthly = (
        daily.groupby(["Month", "AssetID"], sort=True)["ReturnFromPrice"]
        .agg(lambda returns: float(np.prod(1.0 + returns.to_numpy(dtype=float)) - 1.0))
        .reset_index()
        .rename(columns={"Month": "Date", "ReturnFromPrice": "MonthlyReturn"})
    )
    return monthly


def _select_bucket(frame: pd.DataFrame, bucket: BucketSpec) -> pd.DataFrame:
    rank_pct = pd.to_numeric(frame["PredictedRankPct"], errors="coerce")
    return frame.loc[rank_pct.between(bucket.min_rank_pct, bucket.max_rank_pct, inclusive="both")].copy()


def _select_bucket_by_column(frame: pd.DataFrame, bucket: BucketSpec, rank_pct_column: str) -> pd.DataFrame:
    rank_pct = pd.to_numeric(frame[rank_pct_column], errors="coerce")
    return frame.loc[rank_pct.between(bucket.min_rank_pct, bucket.max_rank_pct, inclusive="both")].copy()


def build_bucket_monthly_returns(
    predictions: pd.DataFrame,
    monthly_returns: pd.DataFrame,
    split_name: str = "test",
    buckets: tuple[BucketSpec, ...] = DEFAULT_BUCKETS,
) -> pd.DataFrame:
    selected_predictions = predictions.loc[predictions["Split"].astype(str).eq(split_name)].copy()
    if selected_predictions.empty:
        raise ValueError(f"No predictions found for split {split_name}.")

    merged = selected_predictions.merge(monthly_returns, on=["Date", "AssetID"], how="left")
    missing_returns = merged.loc[merged["MonthlyReturn"].isna(), ["Date", "AssetID"]].drop_duplicates()
    if not missing_returns.empty:
        sample = missing_returns.head(5).to_dict(orient="records")
        raise ValueError(f"Missing monthly returns for prediction rows. Sample: {sample}")

    rows: list[dict[str, Any]] = []
    for date, month_frame in merged.groupby("Date", sort=True):
        for bucket in buckets:
            bucket_frame = _select_bucket(month_frame, bucket)
            if bucket_frame.empty:
                continue
            returns = pd.to_numeric(bucket_frame["MonthlyReturn"], errors="coerce").dropna()
            realized_risk = pd.to_numeric(bucket_frame.get("realized_risk", pd.Series(dtype=float)), errors="coerce")
            rows.append(
                {
                    "Date": str(date),
                    "Split": split_name,
                    "BucketID": bucket.bucket_id,
                    "BucketLabel": bucket.label,
                    "BucketMinRankPct": bucket.min_rank_pct,
                    "BucketMaxRankPct": bucket.max_rank_pct,
                    "AssetCount": int(len(bucket_frame)),
                    "PortfolioReturn": float(returns.mean()),
                    "MeanPredictedRisk": float(pd.to_numeric(bucket_frame["PredictedRisk"], errors="coerce").mean()),
                    "MeanPredictedRankPct": float(pd.to_numeric(bucket_frame["PredictedRankPct"], errors="coerce").mean()),
                    "MeanRealizedRisk": float(realized_risk.mean()) if not realized_risk.empty else math.nan,
                    "SelectionRule": "model_predicted_rank",
                    "IsInvestable": True,
                    "AssetIDs": ",".join(bucket_frame.sort_values("PredictedRankPct")["AssetID"].astype(str)),
                }
            )

    result = pd.DataFrame.from_records(rows)
    if result.empty:
        raise ValueError("Bucket simulation produced no monthly rows.")
    return result


def build_oracle_bucket_monthly_returns(
    predictions: pd.DataFrame,
    monthly_returns: pd.DataFrame,
    split_name: str = "test",
    buckets: tuple[BucketSpec, ...] = DEFAULT_BUCKETS,
) -> pd.DataFrame:
    selected_predictions = predictions.loc[predictions["Split"].astype(str).eq(split_name)].copy()
    if selected_predictions.empty:
        raise ValueError(f"No predictions found for split {split_name}.")
    if "realized_risk" not in selected_predictions.columns:
        raise ValueError("Oracle bucket evaluation requires realized_risk in predictions.")

    merged = selected_predictions.merge(monthly_returns, on=["Date", "AssetID"], how="left")
    merged["RealizedRank"] = merged.groupby("Date")["realized_risk"].rank(method="average", ascending=True)
    month_sizes = merged.groupby("Date")["AssetID"].transform("count")
    merged["RealizedRankPct"] = np.where(
        month_sizes <= 1,
        0.5,
        (merged["RealizedRank"] - 1.0) / (month_sizes - 1.0),
    )

    rows: list[dict[str, Any]] = []
    for date, month_frame in merged.groupby("Date", sort=True):
        for bucket in buckets:
            bucket_frame = _select_bucket_by_column(month_frame, bucket, "RealizedRankPct")
            if bucket_frame.empty:
                continue
            returns = pd.to_numeric(bucket_frame["MonthlyReturn"], errors="coerce").dropna()
            realized_risk = pd.to_numeric(bucket_frame["realized_risk"], errors="coerce")
            rows.append(
                {
                    "Date": str(date),
                    "Split": split_name,
                    "BucketID": bucket.bucket_id,
                    "BucketLabel": f"Oracle {bucket.label}",
                    "BucketMinRankPct": bucket.min_rank_pct,
                    "BucketMaxRankPct": bucket.max_rank_pct,
                    "AssetCount": int(len(bucket_frame)),
                    "PortfolioReturn": float(returns.mean()),
                    "MeanPredictedRisk": float(pd.to_numeric(bucket_frame["PredictedRisk"], errors="coerce").mean()),
                    "MeanPredictedRankPct": float(pd.to_numeric(bucket_frame["PredictedRankPct"], errors="coerce").mean()),
                    "MeanRealizedRisk": float(realized_risk.mean()),
                    "SelectionRule": "realized_risk_oracle",
                    "IsInvestable": False,
                    "AssetIDs": ",".join(bucket_frame.sort_values("RealizedRankPct")["AssetID"].astype(str)),
                }
            )
    result = pd.DataFrame.from_records(rows)
    if result.empty:
        raise ValueError("Oracle bucket simulation produced no monthly rows.")
    return result


def build_random_bucket_monthly_returns(
    predictions: pd.DataFrame,
    monthly_returns: pd.DataFrame,
    split_name: str = "test",
    buckets: tuple[BucketSpec, ...] = DEFAULT_BUCKETS,
    repeats: int = DEFAULT_RANDOM_REPEATS,
    seed: int = DEFAULT_RANDOM_SEED,
) -> pd.DataFrame:
    selected_predictions = predictions.loc[predictions["Split"].astype(str).eq(split_name)].copy()
    if selected_predictions.empty:
        raise ValueError(f"No predictions found for split {split_name}.")
    if repeats <= 0:
        raise ValueError("Random benchmark repeats must be positive.")

    merged = selected_predictions.merge(monthly_returns, on=["Date", "AssetID"], how="left")
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for repeat in range(repeats):
        for date, month_frame in merged.groupby("Date", sort=True):
            shuffled = month_frame.copy()
            asset_count = int(len(shuffled))
            if asset_count <= 1:
                shuffled["RandomRankPct"] = 0.5
            else:
                shuffled["RandomRankPct"] = rng.permutation(np.linspace(0.0, 1.0, asset_count))
            for bucket in buckets:
                bucket_frame = _select_bucket_by_column(shuffled, bucket, "RandomRankPct")
                if bucket_frame.empty:
                    continue
                returns = pd.to_numeric(bucket_frame["MonthlyReturn"], errors="coerce").dropna()
                realized_risk = pd.to_numeric(bucket_frame.get("realized_risk", pd.Series(dtype=float)), errors="coerce")
                rows.append(
                    {
                        "RandomRepeat": repeat,
                        "Date": str(date),
                        "Split": split_name,
                        "BucketID": bucket.bucket_id,
                        "BucketLabel": f"Random {bucket.label}",
                        "BucketMinRankPct": bucket.min_rank_pct,
                        "BucketMaxRankPct": bucket.max_rank_pct,
                        "AssetCount": int(len(bucket_frame)),
                        "PortfolioReturn": float(returns.mean()),
                        "MeanPredictedRisk": float(pd.to_numeric(bucket_frame["PredictedRisk"], errors="coerce").mean()),
                        "MeanPredictedRankPct": float(pd.to_numeric(bucket_frame["PredictedRankPct"], errors="coerce").mean()),
                        "MeanRealizedRisk": float(realized_risk.mean()) if not realized_risk.empty else math.nan,
                        "SelectionRule": "random_rank",
                        "IsInvestable": False,
                        "AssetIDs": "",
                    }
                )
    result = pd.DataFrame.from_records(rows)
    if result.empty:
        raise ValueError("Random benchmark simulation produced no monthly rows.")
    return result


def _max_drawdown(monthly_returns: pd.Series) -> float:
    wealth = pd.concat(
        [
            pd.Series([1.0], dtype=float),
            (1.0 + monthly_returns.astype(float)).cumprod(),
        ],
        ignore_index=True,
    )
    running_max = wealth.cummax()
    drawdowns = (wealth / running_max) - 1.0
    return float(drawdowns.min())


def summarize_bucket_performance(bucket_returns: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for bucket_id, frame in bucket_returns.groupby("BucketID", sort=False):
        returns = pd.to_numeric(frame["PortfolioReturn"], errors="coerce").dropna()
        if returns.empty:
            continue
        periods = int(returns.size)
        cumulative_return = float(np.prod(1.0 + returns.to_numpy(dtype=float)) - 1.0)
        mean_monthly_return = float(returns.mean())
        monthly_vol = float(returns.std(ddof=0))
        annualized_return = float((1.0 + cumulative_return) ** (12.0 / periods) - 1.0) if periods > 0 else math.nan
        annualized_vol = float(monthly_vol * math.sqrt(12.0))
        downside = returns.loc[returns < 0.0]
        downside_dev = float(np.sqrt(np.mean(np.square(downside)))) if not downside.empty else 0.0
        annualized_downside_dev = float(downside_dev * math.sqrt(12.0))
        sharpe = float(annualized_return / annualized_vol) if annualized_vol > 0.0 else math.nan
        sortino = float(annualized_return / annualized_downside_dev) if annualized_downside_dev > 0.0 else math.nan
        rows.append(
            {
                "BucketID": str(bucket_id),
                "BucketLabel": str(frame["BucketLabel"].iloc[0]),
                "Months": periods,
                "MeanAssetCount": float(pd.to_numeric(frame["AssetCount"], errors="coerce").mean()),
                "CumulativeReturn": cumulative_return,
                "AnnualizedReturn": annualized_return,
                "MeanMonthlyReturn": mean_monthly_return,
                "MonthlyVolatility": monthly_vol,
                "MonthlyDownsideDeviation": downside_dev,
                "AnnualizedVolatility": annualized_vol,
                "AnnualizedDownsideDeviation": annualized_downside_dev,
                "MaxDrawdown": _max_drawdown(returns),
                "SharpeNoRf": sharpe,
                "SortinoNoRf": sortino,
                "WorstMonthlyReturn": float(returns.min()),
                "BestMonthlyReturn": float(returns.max()),
                "MeanPredictedRisk": float(pd.to_numeric(frame["MeanPredictedRisk"], errors="coerce").mean()),
                "MeanRealizedRisk": float(pd.to_numeric(frame["MeanRealizedRisk"], errors="coerce").mean()),
            }
        )
    return pd.DataFrame.from_records(rows)


def add_deltas_vs_full_universe(bucket_summary: pd.DataFrame) -> pd.DataFrame:
    enriched = bucket_summary.copy()
    full = enriched.loc[enriched["BucketID"].eq("all_universe")]
    if full.empty:
        raise ValueError("Bucket summary must include all_universe to compute deltas.")
    full_row = full.iloc[0]
    delta_columns = [
        "CumulativeReturn",
        "AnnualizedReturn",
        "MeanMonthlyReturn",
        "MonthlyVolatility",
        "AnnualizedVolatility",
        "MaxDrawdown",
        "MeanPredictedRisk",
        "MeanRealizedRisk",
    ]
    for column in delta_columns:
        enriched[f"{column}DeltaVsFull"] = pd.to_numeric(enriched[column], errors="coerce") - float(full_row[column])
    return enriched


def summarize_random_benchmark(random_returns: pd.DataFrame) -> pd.DataFrame:
    repeat_summaries = []
    for repeat, frame in random_returns.groupby("RandomRepeat", sort=True):
        summary = summarize_bucket_performance(frame)
        summary["RandomRepeat"] = int(repeat)
        repeat_summaries.append(summary)
    combined = pd.concat(repeat_summaries, ignore_index=True)
    rows: list[dict[str, Any]] = []
    for bucket_id, frame in combined.groupby("BucketID", sort=False):
        row = {
            "BucketID": str(bucket_id),
            "BucketLabel": str(frame["BucketLabel"].iloc[0]),
            "RandomRepeats": int(frame["RandomRepeat"].nunique()),
        }
        for column in [
            "CumulativeReturn",
            "MeanMonthlyReturn",
            "MonthlyVolatility",
            "MaxDrawdown",
            "MeanPredictedRisk",
            "MeanRealizedRisk",
        ]:
            values = pd.to_numeric(frame[column], errors="coerce").dropna()
            row[f"{column}Mean"] = float(values.mean())
            row[f"{column}P05"] = float(values.quantile(0.05))
            row[f"{column}P95"] = float(values.quantile(0.95))
        rows.append(row)
    return pd.DataFrame.from_records(rows)


def compute_monthly_risk_separation(bucket_returns: pd.DataFrame) -> pd.DataFrame:
    focused = bucket_returns.loc[bucket_returns["BucketID"].isin(["low_risk", "medium_risk", "high_risk"])].copy()
    pivot = focused.pivot(index="Date", columns="BucketID", values="MeanRealizedRisk").reset_index()
    pivot.columns.name = None
    for column in ["low_risk", "medium_risk", "high_risk"]:
        if column not in pivot.columns:
            pivot[column] = math.nan
    pivot["LowMinusMediumRealizedRisk"] = pivot["low_risk"] - pivot["medium_risk"]
    pivot["HighMinusMediumRealizedRisk"] = pivot["high_risk"] - pivot["medium_risk"]
    pivot["HighMinusLowRealizedRisk"] = pivot["high_risk"] - pivot["low_risk"]
    pivot["IsRealizedRiskMonotonic"] = pivot["low_risk"].lt(pivot["medium_risk"]) & pivot["medium_risk"].lt(pivot["high_risk"])
    return pivot[
        [
            "Date",
            "low_risk",
            "medium_risk",
            "high_risk",
            "LowMinusMediumRealizedRisk",
            "HighMinusMediumRealizedRisk",
            "HighMinusLowRealizedRisk",
            "IsRealizedRiskMonotonic",
        ]
    ]


def compute_risk_separation_checks(bucket_summary: pd.DataFrame, monthly_risk_separation: pd.DataFrame) -> dict[str, Any]:
    by_bucket = bucket_summary.set_index("BucketID")
    required = ["all_universe", "low_risk", "medium_risk", "high_risk"]
    missing = [bucket for bucket in required if bucket not in by_bucket.index]
    if missing:
        raise ValueError(f"Missing buckets for risk-separation checks: {missing}")
    predicted = by_bucket["MeanPredictedRisk"]
    realized = by_bucket["MeanRealizedRisk"]
    return {
        "mean_predicted_risk_monotonic_low_medium_high": bool(
            predicted["low_risk"] < predicted["medium_risk"] < predicted["high_risk"]
        ),
        "mean_realized_risk_monotonic_low_medium_high": bool(
            realized["low_risk"] < realized["medium_risk"] < realized["high_risk"]
        ),
        "low_realized_risk_below_full": bool(realized["low_risk"] < realized["all_universe"]),
        "high_realized_risk_above_full": bool(realized["high_risk"] > realized["all_universe"]),
        "low_realized_risk_delta_vs_full": float(realized["low_risk"] - realized["all_universe"]),
        "high_realized_risk_delta_vs_full": float(realized["high_risk"] - realized["all_universe"]),
        "high_minus_low_realized_risk": float(realized["high_risk"] - realized["low_risk"]),
        "monthly_realized_risk_monotonic_months": int(monthly_risk_separation["IsRealizedRiskMonotonic"].sum()),
        "monthly_realized_risk_monotonic_share": float(monthly_risk_separation["IsRealizedRiskMonotonic"].mean()),
    }


def _score_bucket_method(checks: dict[str, Any]) -> float:
    monotonic_bonus = 1.0 if checks["mean_realized_risk_monotonic_low_medium_high"] else 0.0
    monthly_bonus = float(checks["monthly_realized_risk_monotonic_share"])
    spread = float(checks["high_minus_low_realized_risk"])
    low_full_gap = abs(float(checks["low_realized_risk_delta_vs_full"]))
    high_full_gap = abs(float(checks["high_realized_risk_delta_vs_full"]))
    return float(spread + 0.25 * low_full_gap + 0.25 * high_full_gap + 0.10 * monotonic_bonus + 0.10 * monthly_bonus)


def compare_bucket_methods(
    artifact_dir: str | Path = config.BEST_MODEL_OUTPUT_DIR,
    daily_market_series: str | Path = Path(config.READY_DATA_DIR) / config.DAILY_MARKET_SERIES_NAME,
    output_dir: str | Path = Path(config.GENERATED_REPORT_OUTPUT_DIR) / "portfolio_evaluation",
    split_name: str = "test",
    method_ids: tuple[str, ...] = DEFAULT_COMPARE_BUCKET_METHOD_IDS,
    random_repeats: int = DEFAULT_RANDOM_REPEATS,
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> pd.DataFrame:
    resolved_output = Path(output_dir).resolve()
    rows: list[dict[str, Any]] = []
    for method_id in method_ids:
        if method_id not in BUCKET_METHODS:
            raise ValueError(f"Unknown bucket method id: {method_id}")
        method = BUCKET_METHODS[method_id]
        method_output = resolved_output / "methods" / method_id
        payload = run_portfolio_evaluation(
            artifact_dir=artifact_dir,
            daily_market_series=daily_market_series,
            output_dir=method_output,
            split_name=split_name,
            buckets=method.buckets,
            bucket_method_id=method.method_id,
            bucket_method_label=method.label,
            bucket_method_description=method.description,
            random_repeats=random_repeats,
            random_seed=random_seed,
            write_method_comparison=False,
        )
        checks = payload["risk_separation_checks"]
        summary = pd.read_csv(method_output / BUCKET_SUMMARY_FILE_NAME).set_index("BucketID")
        rows.append(
            {
                "BucketMethodID": method.method_id,
                "BucketMethodLabel": method.label,
                "Description": method.description,
                "MeanRealizedRiskMonotonic": bool(checks["mean_realized_risk_monotonic_low_medium_high"]),
                "MonthlyMonotonicShare": float(checks["monthly_realized_risk_monotonic_share"]),
                "LowRealizedRisk": float(summary.loc["low_risk", "MeanRealizedRisk"]),
                "MediumRealizedRisk": float(summary.loc["medium_risk", "MeanRealizedRisk"]),
                "HighRealizedRisk": float(summary.loc["high_risk", "MeanRealizedRisk"]),
                "LowDeltaVsFull": float(checks["low_realized_risk_delta_vs_full"]),
                "HighDeltaVsFull": float(checks["high_realized_risk_delta_vs_full"]),
                "HighMinusLowRealizedRisk": float(checks["high_minus_low_realized_risk"]),
                "LowMeanAssetCount": float(summary.loc["low_risk", "MeanAssetCount"]),
                "MediumMeanAssetCount": float(summary.loc["medium_risk", "MeanAssetCount"]),
                "HighMeanAssetCount": float(summary.loc["high_risk", "MeanAssetCount"]),
                "LowCumulativeReturn": float(summary.loc["low_risk", "CumulativeReturn"]),
                "MediumCumulativeReturn": float(summary.loc["medium_risk", "CumulativeReturn"]),
                "HighCumulativeReturn": float(summary.loc["high_risk", "CumulativeReturn"]),
                "MethodScore": _score_bucket_method(checks),
                "ReportFile": str(method_output / REPORT_FILE_NAME),
            }
        )
    comparison = pd.DataFrame.from_records(rows).sort_values("MethodScore", ascending=False).reset_index(drop=True)
    comparison.to_csv(resolved_output / METHOD_COMPARISON_FILE_NAME, index=False)
    write_method_comparison_report(resolved_output, comparison, split_name)
    return comparison


def _format_pct(value: float) -> str:
    if pd.isna(value):
        return ""
    return f"{100.0 * float(value):.2f}%"


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    display = frame.loc[:, columns].copy()
    for column in columns:
        if pd.api.types.is_bool_dtype(display[column]):
            display[column] = display[column].map(lambda value: "True" if bool(value) else "False")
        elif column in {
            "CumulativeReturn",
            "AnnualizedReturn",
            "MeanMonthlyReturn",
            "MonthlyVolatility",
            "MonthlyDownsideDeviation",
            "AnnualizedVolatility",
            "AnnualizedDownsideDeviation",
            "MaxDrawdown",
            "WorstMonthlyReturn",
            "BestMonthlyReturn",
            "CumulativeReturnDeltaVsFull",
            "AnnualizedReturnDeltaVsFull",
            "MeanMonthlyReturnDeltaVsFull",
            "MonthlyVolatilityDeltaVsFull",
            "AnnualizedVolatilityDeltaVsFull",
            "MaxDrawdownDeltaVsFull",
        } or column.startswith("CumulativeReturn") or column.endswith("CumulativeReturn") or column.startswith("MeanMonthlyReturn") or column.startswith("MonthlyVolatility") or column.startswith("MaxDrawdown"):
            display[column] = display[column].map(_format_pct)
        elif (
            column in {"SharpeNoRf", "SortinoNoRf", "MeanPredictedRisk", "MeanRealizedRisk", "MeanAssetCount", "MethodScore"}
            or column.startswith("MeanPredictedRisk")
            or column.startswith("MeanRealizedRisk")
            or column.endswith("RealizedRisk")
            or column.endswith("MeanAssetCount")
            or column == "HighMinusLowRealizedRisk"
            or column == "MonthlyMonotonicShare"
        ):
            display[column] = display[column].map(lambda value: "" if pd.isna(value) else f"{float(value):.3f}")
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    rows = []
    for _, row in display.iterrows():
        values = [str(row[column]) if not pd.isna(row[column]) else "" for column in columns]
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join([header, separator, *rows])


def write_method_comparison_report(output_dir: Path, comparison: pd.DataFrame, split_name: str) -> None:
    table = _markdown_table(
        comparison,
        [
            "BucketMethodID",
            "MeanRealizedRiskMonotonic",
            "MonthlyMonotonicShare",
            "LowRealizedRisk",
            "MediumRealizedRisk",
            "HighRealizedRisk",
            "HighMinusLowRealizedRisk",
            "LowMeanAssetCount",
            "MediumMeanAssetCount",
            "HighMeanAssetCount",
            "MethodScore",
        ],
    )
    best = comparison.iloc[0]
    report = (
        "# Bucket Method Comparison\n\n"
        f"Evaluated split: `{split_name}`\n\n"
        "All methods use predicted rank percentiles, so bucket sizes adapt to the active universe in each month instead of hardcoding an asset count.\n\n"
        "## Comparison Summary\n\n"
        f"{table}\n\n"
        "## Selection Rule\n\n"
        "Prefer a method that keeps mean realized risk monotonic from low to medium to high, keeps monthly monotonicity high, and creates a large high-minus-low realized-risk spread. "
        "Return metrics remain secondary because the PPO model predicts risk, not expected return.\n\n"
        "## Current Recommendation\n\n"
        f"- Recommended method: `{best['BucketMethodID']}` ({best['BucketMethodLabel']})\n"
        f"- Reason: realized-risk spread `{float(best['HighMinusLowRealizedRisk']):.3f}` with monthly monotonicity `{float(best['MonthlyMonotonicShare']):.2%}`.\n"
    )
    (output_dir / METHOD_COMPARISON_REPORT_FILE_NAME).write_text(report, encoding="utf-8")


def write_report(
    output_dir: Path,
    split_name: str,
    bucket_method_id: str,
    bucket_method_label: str,
    bucket_method_description: str,
    bucket_summary: pd.DataFrame,
    bucket_returns: pd.DataFrame,
    monthly_risk_separation: pd.DataFrame,
    random_summary: pd.DataFrame,
    oracle_summary: pd.DataFrame,
    risk_checks: dict[str, Any],
    buckets: tuple[BucketSpec, ...],
) -> None:
    bucket_lines = "\n".join(
        f"- `{bucket.bucket_id}`: {bucket.description} Rank-percentile band `{bucket.min_rank_pct:.2f}` to `{bucket.max_rank_pct:.2f}`."
        for bucket in buckets
    )
    risk_table = _markdown_table(
        bucket_summary,
        [
            "BucketLabel",
            "Months",
            "MeanAssetCount",
            "MeanPredictedRisk",
            "MeanRealizedRisk",
            "MeanRealizedRiskDeltaVsFull",
        ],
    )
    performance_table = _markdown_table(
        bucket_summary,
        [
            "BucketLabel",
            "CumulativeReturn",
            "MeanMonthlyReturn",
            "MonthlyVolatility",
            "MaxDrawdown",
            "SharpeNoRf",
        ],
    )
    random_table = _markdown_table(
        random_summary,
        [
            "BucketLabel",
            "RandomRepeats",
            "MeanRealizedRiskMean",
            "MeanRealizedRiskP05",
            "MeanRealizedRiskP95",
            "CumulativeReturnMean",
        ],
    )
    oracle_table = _markdown_table(
        oracle_summary,
        [
            "BucketLabel",
            "MeanAssetCount",
            "MeanRealizedRisk",
            "CumulativeReturn",
        ],
    )
    monotonic_months = risk_checks["monthly_realized_risk_monotonic_months"]
    monotonic_share = risk_checks["monthly_realized_risk_monotonic_share"]
    report = (
        "# Portfolio Bucket Evaluation\n\n"
        "This report evaluates the promoted risk-ranking model as an asset preselection signal. "
        "The primary evidence is risk separation, not portfolio optimization. Each bucket is rebalanced monthly with equal weights, "
        "so the comparison isolates whether predicted risk ranks create economically different realized-risk groups.\n\n"
        f"Evaluated split: `{split_name}`\n\n"
        f"Bucket method: `{bucket_method_id}` ({bucket_method_label})\n\n"
        f"{bucket_method_description}\n\n"
        "## Bucket Rules\n\n"
        f"{bucket_lines}\n\n"
        "## Primary Evidence: Risk Separation\n\n"
        f"{risk_table}\n\n"
        f"- Mean predicted risk monotonic low < medium < high: `{risk_checks['mean_predicted_risk_monotonic_low_medium_high']}`\n"
        f"- Mean realized risk monotonic low < medium < high: `{risk_checks['mean_realized_risk_monotonic_low_medium_high']}`\n"
        f"- Low-risk realized risk below full universe: `{risk_checks['low_realized_risk_below_full']}`\n"
        f"- High-risk realized risk above full universe: `{risk_checks['high_realized_risk_above_full']}`\n"
        f"- Monthly realized-risk monotonicity: `{monotonic_months}` months, `{monotonic_share:.2%}` of evaluated months\n\n"
        "## Secondary Evidence: Economic Behavior\n\n"
        f"{performance_table}\n\n"
        "Return, Sharpe, and Sortino figures are secondary diagnostics. The PPO target is realized risk, not expected return, "
        "and the test period is short and strongly positive for the full universe.\n\n"
        "## Benchmark Context\n\n"
        "Random buckets use repeated random rank assignments with the same bucket bands. The oracle uses realized risk ranks and is not investable.\n\n"
        f"{random_table}\n\n"
        f"{oracle_table}\n\n"
        "## Thesis Interpretation\n\n"
        "- Thesis-safe claim: the model creates distinct realized-risk buckets from predicted ranks.\n"
        "- Thesis-unsafe claim: the model improves portfolio optimization returns.\n"
        "- The high-risk bucket earning the highest return in this window is consistent with a risk/return gradient, not proof of return prediction.\n\n"
        "## Generated Files\n\n"
        f"- `{MONTHLY_RETURNS_FILE_NAME}`\n"
        f"- `{BUCKET_RETURNS_FILE_NAME}`\n"
        f"- `{BUCKET_SUMMARY_FILE_NAME}`\n"
        f"- `{MONTHLY_RISK_SEPARATION_FILE_NAME}`\n"
        f"- `{RANDOM_BENCHMARK_RETURNS_FILE_NAME}`\n"
        f"- `{RANDOM_BENCHMARK_SUMMARY_FILE_NAME}`\n"
        f"- `{ORACLE_RETURNS_FILE_NAME}`\n"
        f"- `{ORACLE_SUMMARY_FILE_NAME}`\n"
        f"- `{SUMMARY_FILE_NAME}`\n"
    )
    (output_dir / REPORT_FILE_NAME).write_text(report, encoding="utf-8")


def run_portfolio_evaluation(
    artifact_dir: str | Path = config.BEST_MODEL_OUTPUT_DIR,
    daily_market_series: str | Path = Path(config.READY_DATA_DIR) / config.DAILY_MARKET_SERIES_NAME,
    output_dir: str | Path = Path(config.GENERATED_REPORT_OUTPUT_DIR) / "portfolio_evaluation",
    split_name: str = "test",
    buckets: tuple[BucketSpec, ...] = DEFAULT_BUCKETS,
    bucket_method_id: str = DEFAULT_BUCKET_METHOD_ID,
    bucket_method_label: str | None = None,
    bucket_method_description: str | None = None,
    random_repeats: int = DEFAULT_RANDOM_REPEATS,
    random_seed: int = DEFAULT_RANDOM_SEED,
    write_method_comparison: bool = True,
) -> dict[str, Any]:
    resolved_output = Path(output_dir).resolve()
    resolved_output.mkdir(parents=True, exist_ok=True)
    bucket_method_label = bucket_method_label or BUCKET_METHODS.get(bucket_method_id, BUCKET_METHODS[DEFAULT_BUCKET_METHOD_ID]).label
    bucket_method_description = bucket_method_description or BUCKET_METHODS.get(
        bucket_method_id,
        BUCKET_METHODS[DEFAULT_BUCKET_METHOD_ID],
    ).description

    predictions = load_predictions(artifact_dir)
    monthly_returns = compute_monthly_asset_returns(daily_market_series)
    bucket_returns = build_bucket_monthly_returns(
        predictions=predictions,
        monthly_returns=monthly_returns,
        split_name=split_name,
        buckets=buckets,
    )
    bucket_summary = add_deltas_vs_full_universe(summarize_bucket_performance(bucket_returns))
    monthly_risk_separation = compute_monthly_risk_separation(bucket_returns)
    risk_checks = compute_risk_separation_checks(bucket_summary, monthly_risk_separation)
    random_returns = build_random_bucket_monthly_returns(
        predictions=predictions,
        monthly_returns=monthly_returns,
        split_name=split_name,
        buckets=buckets,
        repeats=random_repeats,
        seed=random_seed,
    )
    random_summary = summarize_random_benchmark(random_returns)
    oracle_returns = build_oracle_bucket_monthly_returns(
        predictions=predictions,
        monthly_returns=monthly_returns,
        split_name=split_name,
        buckets=buckets,
    )
    oracle_summary = add_deltas_vs_full_universe(summarize_bucket_performance(oracle_returns))

    monthly_returns.to_csv(resolved_output / MONTHLY_RETURNS_FILE_NAME, index=False)
    bucket_returns.to_csv(resolved_output / BUCKET_RETURNS_FILE_NAME, index=False)
    bucket_summary.to_csv(resolved_output / BUCKET_SUMMARY_FILE_NAME, index=False)
    monthly_risk_separation.to_csv(resolved_output / MONTHLY_RISK_SEPARATION_FILE_NAME, index=False)
    random_returns.to_csv(resolved_output / RANDOM_BENCHMARK_RETURNS_FILE_NAME, index=False)
    random_summary.to_csv(resolved_output / RANDOM_BENCHMARK_SUMMARY_FILE_NAME, index=False)
    oracle_returns.to_csv(resolved_output / ORACLE_RETURNS_FILE_NAME, index=False)
    oracle_summary.to_csv(resolved_output / ORACLE_SUMMARY_FILE_NAME, index=False)

    payload = {
        "artifact_dir": str(Path(artifact_dir).resolve()),
        "daily_market_series": str(Path(daily_market_series).resolve()),
        "output_dir": str(resolved_output),
        "split_name": split_name,
        "bucket_method_id": bucket_method_id,
        "bucket_method_label": bucket_method_label,
        "bucket_method_description": bucket_method_description,
        "bucket_specs": [asdict(bucket) for bucket in buckets],
        "bucket_count": int(bucket_summary.shape[0]),
        "month_count": int(bucket_returns["Date"].nunique()),
        "random_repeats": int(random_repeats),
        "random_seed": int(random_seed),
        "risk_separation_checks": risk_checks,
        "summary_file": str(resolved_output / BUCKET_SUMMARY_FILE_NAME),
        "report_file": str(resolved_output / REPORT_FILE_NAME),
    }
    (resolved_output / SUMMARY_FILE_NAME).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_report(
        output_dir=resolved_output,
        split_name=split_name,
        bucket_method_id=bucket_method_id,
        bucket_method_label=bucket_method_label,
        bucket_method_description=bucket_method_description,
        bucket_summary=bucket_summary,
        bucket_returns=bucket_returns,
        monthly_risk_separation=monthly_risk_separation,
        random_summary=random_summary,
        oracle_summary=oracle_summary,
        risk_checks=risk_checks,
        buckets=buckets,
    )
    if write_method_comparison:
        compare_bucket_methods(
            artifact_dir=artifact_dir,
            daily_market_series=daily_market_series,
            output_dir=resolved_output,
            split_name=split_name,
            method_ids=DEFAULT_COMPARE_BUCKET_METHOD_IDS,
            random_repeats=random_repeats,
            random_seed=random_seed,
        )
    return payload


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", default=config.BEST_MODEL_OUTPUT_DIR)
    parser.add_argument("--daily-market-series", default=str(Path(config.READY_DATA_DIR) / config.DAILY_MARKET_SERIES_NAME))
    parser.add_argument("--output-dir", default=str(Path(config.GENERATED_REPORT_OUTPUT_DIR) / "portfolio_evaluation"))
    parser.add_argument("--split-name", default="test")
    parser.add_argument(
        "--bucket-method",
        default="compare_all",
        help=f"Bucket method id to run, or compare_all. Available: {', '.join(BUCKET_METHODS)}",
    )
    parser.add_argument("--random-repeats", type=int, default=DEFAULT_RANDOM_REPEATS)
    parser.add_argument("--random-seed", type=int, default=DEFAULT_RANDOM_SEED)
    args = parser.parse_args(argv)

    if args.bucket_method == "compare_all":
        comparison = compare_bucket_methods(
            artifact_dir=args.artifact_dir,
            daily_market_series=args.daily_market_series,
            output_dir=args.output_dir,
            split_name=args.split_name,
            method_ids=DEFAULT_COMPARE_BUCKET_METHOD_IDS,
            random_repeats=args.random_repeats,
            random_seed=args.random_seed,
        )
        best_method_id = str(comparison.iloc[0]["BucketMethodID"])
        method = BUCKET_METHODS[best_method_id]
        payload = run_portfolio_evaluation(
            artifact_dir=args.artifact_dir,
            daily_market_series=args.daily_market_series,
            output_dir=args.output_dir,
            split_name=args.split_name,
            buckets=method.buckets,
            bucket_method_id=method.method_id,
            bucket_method_label=method.label,
            bucket_method_description=method.description,
            random_repeats=args.random_repeats,
            random_seed=args.random_seed,
            write_method_comparison=False,
        )
        payload["method_comparison_file"] = str(Path(args.output_dir).resolve() / METHOD_COMPARISON_FILE_NAME)
        payload["method_comparison_report_file"] = str(Path(args.output_dir).resolve() / METHOD_COMPARISON_REPORT_FILE_NAME)
    else:
        if args.bucket_method not in BUCKET_METHODS:
            raise ValueError(f"Unknown bucket method id: {args.bucket_method}")
        method = BUCKET_METHODS[args.bucket_method]
        payload = run_portfolio_evaluation(
            artifact_dir=args.artifact_dir,
            daily_market_series=args.daily_market_series,
            output_dir=args.output_dir,
            split_name=args.split_name,
            buckets=method.buckets,
            bucket_method_id=method.method_id,
            bucket_method_label=method.label,
            bucket_method_description=method.description,
            random_repeats=args.random_repeats,
            random_seed=args.random_seed,
            write_method_comparison=False,
        )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
