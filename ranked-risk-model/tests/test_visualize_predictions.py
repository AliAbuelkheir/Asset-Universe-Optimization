from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.training import visualize_predictions


def _write_mock_artifacts(artifact_dir: Path) -> None:
    predictions = pd.DataFrame(
        [
            {
                "Date": "2025-03",
                "Split": "test",
                "AssetID": "MoneyMarket",
                "AssetName": "91-Day T-Bills",
                "AssetGroup": "MoneyMarket",
                "realized_risk": 0.00,
                "PredictedRisk": 0.10,
                "realized_rank": 1.0,
                "PredictedRank": 1.0,
                "PredictedRankPct": 0.0,
                "PredictionError": 0.10,
            },
            {
                "Date": "2025-03",
                "Split": "test",
                "AssetID": "Gold",
                "AssetName": "24K Gold (EGP)",
                "AssetGroup": "Gold",
                "realized_risk": 0.33,
                "PredictedRisk": 0.35,
                "realized_rank": 2.0,
                "PredictedRank": 2.0,
                "PredictedRankPct": 1.0 / 3.0,
                "PredictionError": 0.02,
            },
            {
                "Date": "2025-03",
                "Split": "test",
                "AssetID": "EGX30",
                "AssetName": "EGX30 Index",
                "AssetGroup": "EquityIndex",
                "realized_risk": 0.66,
                "PredictedRisk": 0.60,
                "realized_rank": 3.0,
                "PredictedRank": 3.0,
                "PredictedRankPct": 2.0 / 3.0,
                "PredictionError": -0.06,
            },
            {
                "Date": "2025-03",
                "Split": "test",
                "AssetID": "ABUK.CA",
                "AssetName": "Abou Kir Fertilizers",
                "AssetGroup": "Equity",
                "realized_risk": 1.00,
                "PredictedRisk": 0.80,
                "realized_rank": 4.0,
                "PredictedRank": 4.0,
                "PredictedRankPct": 1.0,
                "PredictionError": -0.20,
            },
            {
                "Date": "2025-04",
                "Split": "test",
                "AssetID": "MoneyMarket",
                "AssetName": "91-Day T-Bills",
                "AssetGroup": "MoneyMarket",
                "realized_risk": 0.00,
                "PredictedRisk": 0.08,
                "realized_rank": 1.0,
                "PredictedRank": 1.0,
                "PredictedRankPct": 0.0,
                "PredictionError": 0.08,
            },
            {
                "Date": "2025-04",
                "Split": "test",
                "AssetID": "Gold",
                "AssetName": "24K Gold (EGP)",
                "AssetGroup": "Gold",
                "realized_risk": 1.00,
                "PredictedRisk": 0.95,
                "realized_rank": 4.0,
                "PredictedRank": 4.0,
                "PredictedRankPct": 1.0,
                "PredictionError": -0.05,
            },
            {
                "Date": "2025-04",
                "Split": "test",
                "AssetID": "EGX30",
                "AssetName": "EGX30 Index",
                "AssetGroup": "EquityIndex",
                "realized_risk": 0.33,
                "PredictedRisk": 0.40,
                "realized_rank": 2.0,
                "PredictedRank": 2.0,
                "PredictedRankPct": 1.0 / 3.0,
                "PredictionError": 0.07,
            },
            {
                "Date": "2025-04",
                "Split": "test",
                "AssetID": "ABUK.CA",
                "AssetName": "Abou Kir Fertilizers",
                "AssetGroup": "Equity",
                "realized_risk": 0.66,
                "PredictedRisk": 0.55,
                "realized_rank": 3.0,
                "PredictedRank": 3.0,
                "PredictedRankPct": 2.0 / 3.0,
                "PredictionError": -0.11,
            },
            {
                "Date": "2025-02",
                "Split": "validation",
                "AssetID": "MoneyMarket",
                "AssetName": "91-Day T-Bills",
                "AssetGroup": "MoneyMarket",
                "realized_risk": 0.00,
                "PredictedRisk": 0.05,
                "realized_rank": 1.0,
                "PredictedRank": 1.0,
                "PredictedRankPct": 0.0,
                "PredictionError": 0.05,
            },
        ]
    )
    monthly_metrics = pd.DataFrame(
        [
            {"date": "2025-03", "split": "test", "active_assets": 4, "spearman": 0.80, "mse": 0.012, "reward": 0.8564},
            {"date": "2025-04", "split": "test", "active_assets": 4, "spearman": 1.00, "mse": 0.004, "reward": 0.9988},
            {"date": "2025-02", "split": "validation", "active_assets": 4, "spearman": 0.75, "mse": 0.010, "reward": 0.8220},
        ]
    )

    predictions.to_csv(artifact_dir / "ranked_predictions.csv", index=False)
    monthly_metrics.to_csv(artifact_dir / "monthly_metrics.csv", index=False)
    with (artifact_dir / "setup_summary.json").open("w", encoding="utf-8") as handle:
        json.dump({"SetupID": "TEST-VISUAL-SETUP"}, handle)


def test_generate_split_diagnostic_pack_writes_expected_outputs(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "experiment"
    artifact_dir.mkdir()
    _write_mock_artifacts(artifact_dir)

    output_dir = visualize_predictions.generate_split_diagnostic_pack(artifact_dir, split_name="test")

    expected_files = {
        visualize_predictions.RANK_ALIGNMENT_FILE_NAME,
        visualize_predictions.MONTHLY_PERFORMANCE_FILE_NAME,
        visualize_predictions.BEST_MONTH_RANK_FILE_NAME,
        visualize_predictions.RANK_GAP_FILE_NAME,
        visualize_predictions.EXTREME_RANK_OVERLAP_FILE_NAME,
        visualize_predictions.SUMMARY_FILE_NAME,
    }
    assert {path.name for path in output_dir.iterdir()} == expected_files

    with (output_dir / visualize_predictions.SUMMARY_FILE_NAME).open("r", encoding="utf-8") as handle:
        summary = json.load(handle)

    assert summary["setup_label"] == "TEST-VISUAL-SETUP"
    assert summary["split_name"] == "test"
    assert summary["row_count"] == 8
    assert summary["month_count"] == 2
    assert summary["best_month_by_reward"]["date"] == "2025-04"
    assert summary["best_month_by_spearman"]["date"] == "2025-04"
    assert Path(summary["plot_files"]["best_month_rank_comparison"]).exists()
    assert Path(summary["plot_files"]["monthly_rank_gap"]).exists()
    assert Path(summary["plot_files"]["extreme_rank_overlap"]).exists()
    assert "risk_distribution" not in summary["plot_files"]
