from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.training import portfolio_evaluation


def _write_mock_inputs(tmp_path: Path) -> tuple[Path, Path]:
    artifact_dir = tmp_path / "best_model"
    artifact_dir.mkdir()
    predictions = pd.DataFrame(
        [
            {
                "Date": "2025-03",
                "Split": "test",
                "AssetID": "A",
                "AssetName": "A",
                "AssetGroup": "Equity",
                "PredictedRisk": 0.10,
                "PredictedRankPct": 0.0,
                "realized_risk": 0.10,
            },
            {
                "Date": "2025-03",
                "Split": "test",
                "AssetID": "B",
                "AssetName": "B",
                "AssetGroup": "Equity",
                "PredictedRisk": 0.30,
                "PredictedRankPct": 1.0 / 3.0,
                "realized_risk": 0.30,
            },
            {
                "Date": "2025-03",
                "Split": "test",
                "AssetID": "C",
                "AssetName": "C",
                "AssetGroup": "Equity",
                "PredictedRisk": 0.70,
                "PredictedRankPct": 2.0 / 3.0,
                "realized_risk": 0.70,
            },
            {
                "Date": "2025-03",
                "Split": "test",
                "AssetID": "D",
                "AssetName": "D",
                "AssetGroup": "Equity",
                "PredictedRisk": 0.90,
                "PredictedRankPct": 1.0,
                "realized_risk": 0.90,
            },
            {
                "Date": "2025-04",
                "Split": "test",
                "AssetID": "A",
                "AssetName": "A",
                "AssetGroup": "Equity",
                "PredictedRisk": 0.10,
                "PredictedRankPct": 0.0,
                "realized_risk": 0.10,
            },
            {
                "Date": "2025-04",
                "Split": "test",
                "AssetID": "B",
                "AssetName": "B",
                "AssetGroup": "Equity",
                "PredictedRisk": 0.30,
                "PredictedRankPct": 1.0 / 3.0,
                "realized_risk": 0.30,
            },
            {
                "Date": "2025-04",
                "Split": "test",
                "AssetID": "C",
                "AssetName": "C",
                "AssetGroup": "Equity",
                "PredictedRisk": 0.70,
                "PredictedRankPct": 2.0 / 3.0,
                "realized_risk": 0.70,
            },
            {
                "Date": "2025-04",
                "Split": "test",
                "AssetID": "D",
                "AssetName": "D",
                "AssetGroup": "Equity",
                "PredictedRisk": 0.90,
                "PredictedRankPct": 1.0,
                "realized_risk": 0.90,
            },
        ]
    )
    predictions.to_csv(artifact_dir / portfolio_evaluation.PREDICTIONS_FILE_NAME, index=False)

    daily_path = tmp_path / "daily_market_series.csv"
    daily_rows = []
    monthly_returns = {
        ("2025-03", "A"): [0.01, 0.02],
        ("2025-03", "B"): [0.03, 0.01],
        ("2025-03", "C"): [-0.02, 0.01],
        ("2025-03", "D"): [-0.05, -0.02],
        ("2025-04", "A"): [0.02, 0.01],
        ("2025-04", "B"): [0.01, 0.02],
        ("2025-04", "C"): [-0.01, -0.01],
        ("2025-04", "D"): [-0.03, -0.04],
    }
    for (month, asset_id), returns in monthly_returns.items():
        for day_index, value in enumerate(returns, start=1):
            daily_rows.append(
                {
                    "Date": f"{month}-{day_index:02d}",
                    "AssetID": asset_id,
                    "ReturnFromPrice": value,
                }
            )
    pd.DataFrame(daily_rows).to_csv(daily_path, index=False)
    return artifact_dir, daily_path


def test_compute_monthly_asset_returns_compounds_daily_returns(tmp_path: Path) -> None:
    _, daily_path = _write_mock_inputs(tmp_path)

    monthly = portfolio_evaluation.compute_monthly_asset_returns(daily_path)

    row = monthly.loc[(monthly["Date"] == "2025-03") & (monthly["AssetID"] == "A")].iloc[0]
    assert row["MonthlyReturn"] == pytest.approx((1.01 * 1.02) - 1.0)


def test_run_portfolio_evaluation_writes_bucket_report(tmp_path: Path) -> None:
    artifact_dir, daily_path = _write_mock_inputs(tmp_path)
    output_dir = tmp_path / "portfolio_report"

    payload = portfolio_evaluation.run_portfolio_evaluation(
        artifact_dir=artifact_dir,
        daily_market_series=daily_path,
        output_dir=output_dir,
        split_name="test",
        random_repeats=5,
        random_seed=123,
        write_method_comparison=False,
    )

    assert payload["bucket_count"] == 4
    assert payload["month_count"] == 2
    assert payload["risk_separation_checks"]["mean_realized_risk_monotonic_low_medium_high"] is True
    assert payload["risk_separation_checks"]["low_realized_risk_below_full"] is True
    assert payload["risk_separation_checks"]["high_realized_risk_above_full"] is True
    assert (output_dir / portfolio_evaluation.BUCKET_RETURNS_FILE_NAME).exists()
    assert (output_dir / portfolio_evaluation.BUCKET_SUMMARY_FILE_NAME).exists()
    assert (output_dir / portfolio_evaluation.MONTHLY_RISK_SEPARATION_FILE_NAME).exists()
    assert (output_dir / portfolio_evaluation.RANDOM_BENCHMARK_SUMMARY_FILE_NAME).exists()
    assert (output_dir / portfolio_evaluation.ORACLE_SUMMARY_FILE_NAME).exists()
    assert (output_dir / portfolio_evaluation.REPORT_FILE_NAME).exists()

    bucket_returns = pd.read_csv(output_dir / portfolio_evaluation.BUCKET_RETURNS_FILE_NAME)
    march_low = bucket_returns.loc[
        (bucket_returns["Date"] == "2025-03") & (bucket_returns["BucketID"] == "low_risk")
    ].iloc[0]
    march_medium = bucket_returns.loc[
        (bucket_returns["Date"] == "2025-03") & (bucket_returns["BucketID"] == "medium_risk")
    ].iloc[0]
    march_high = bucket_returns.loc[
        (bucket_returns["Date"] == "2025-03") & (bucket_returns["BucketID"] == "high_risk")
    ].iloc[0]

    assert march_low["AssetIDs"] == "A,B"
    assert march_medium["AssetIDs"] == "B,C"
    assert march_high["AssetIDs"] == "C,D"
    assert march_low["PortfolioReturn"] > march_high["PortfolioReturn"]

    with (output_dir / portfolio_evaluation.SUMMARY_FILE_NAME).open("r", encoding="utf-8") as handle:
        summary = json.load(handle)
    assert summary["split_name"] == "test"

    bucket_summary = pd.read_csv(output_dir / portfolio_evaluation.BUCKET_SUMMARY_FILE_NAME)
    low_summary = bucket_summary.loc[bucket_summary["BucketID"] == "low_risk"].iloc[0]
    high_summary = bucket_summary.loc[bucket_summary["BucketID"] == "high_risk"].iloc[0]
    assert low_summary["MeanRealizedRiskDeltaVsFull"] < 0.0
    assert high_summary["MeanRealizedRiskDeltaVsFull"] > 0.0

    oracle_returns = pd.read_csv(output_dir / portfolio_evaluation.ORACLE_RETURNS_FILE_NAME)
    assert oracle_returns["IsInvestable"].eq(False).all()


def test_max_drawdown_includes_initial_wealth() -> None:
    assert portfolio_evaluation._max_drawdown(pd.Series([-0.10, 0.05])) == pytest.approx(-0.10)


def test_random_benchmark_is_reproducible(tmp_path: Path) -> None:
    artifact_dir, daily_path = _write_mock_inputs(tmp_path)
    predictions = portfolio_evaluation.load_predictions(artifact_dir)
    monthly_returns = portfolio_evaluation.compute_monthly_asset_returns(daily_path)

    first = portfolio_evaluation.build_random_bucket_monthly_returns(
        predictions,
        monthly_returns,
        repeats=3,
        seed=99,
    )
    second = portfolio_evaluation.build_random_bucket_monthly_returns(
        predictions,
        monthly_returns,
        repeats=3,
        seed=99,
    )

    pd.testing.assert_frame_equal(first, second)


def test_bucket_method_registry_uses_rank_percentile_bands() -> None:
    assert set(portfolio_evaluation.BUCKET_METHODS) >= {
        "overlap_40_50",
        "tercile_no_overlap",
        "wide_overlap_50_60",
        "tail_30_overlap",
    }
    for method in portfolio_evaluation.BUCKET_METHODS.values():
        assert method.buckets[0].bucket_id == "all_universe"
        for bucket in method.buckets:
            assert 0.0 <= bucket.min_rank_pct <= bucket.max_rank_pct <= 1.0
