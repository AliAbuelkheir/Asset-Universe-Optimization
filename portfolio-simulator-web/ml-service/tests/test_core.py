from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import pandas as pd
from fastapi.testclient import TestClient

from app import optimizer as optimizer_module
from app import questionnaire as questionnaire_module
from app import simulation as simulation_module
from app.data import VALID_SPLITS, available_months, read_predictions, risk_levels, select_assets
from app.main import app
from app.metrics import performance_metrics, portfolio_monthly_returns
from app.questionnaire import build_feature_vector, predict_questionnaire_risk
from app.simulation import health, run_fast_simulation, run_questionnaire_simulation


SAMPLE_QUESTIONNAIRE = {
    "gender": "Male",
    "age": 29,
    "Duration": "Less than 1 year",
    "Invest_Monitor": "Weekly",
    "Expect": "20%-30%",
    "Objective": "Growth",
    "Purpose": "Wealth Creation",
    "What are your savings objectives?": "Health Care",
}


def test_health_reports_real_artifact_availability() -> None:
    payload = health()
    assert payload["ppoRootExists"] is True
    assert payload["predictionsAvailable"] is True
    assert payload["dailyMarketAvailable"] is True
    assert payload["monthlyPanelAvailable"] is True
    assert payload["questionnaireModelAvailable"] is True
    assert payload["optimizerMode"] == "external_model"
    assert payload["status"] == "ok"


def test_available_months_include_validation_and_test() -> None:
    months = available_months()
    month_labels = {row["month"] for row in months}
    assert "2023-01" in month_labels
    assert "2026-01" in month_labels


def test_risk_level_contracts_are_exposed() -> None:
    levels = risk_levels()
    assert [level["id"] for level in levels] == ["low", "medium", "high"]
    assert levels[0]["maxRankPct"] == 0.30
    assert levels[2]["minRankPct"] == 0.70


def test_select_assets_returns_bucket_assets() -> None:
    selected, split = select_assets("2025-03", "medium")
    assert split == "test"
    assert not selected.empty
    assert selected["PredictedRankPct"].between(0.20, 0.80, inclusive="both").all()


def test_performance_metrics_count_first_month_drawdown() -> None:
    metrics = performance_metrics([-0.10, 0.05])

    assert metrics["cumulativeReturn"] == pytest.approx(-0.055)
    assert metrics["maxDrawdown"] == pytest.approx(-0.10)


def test_portfolio_monthly_returns_fail_on_missing_weighted_asset() -> None:
    monthly_returns = pd.DataFrame(
        [
            {"Date": "2025-03", "AssetID": "A", "MonthlyReturn": 0.10},
        ]
    )

    with pytest.raises(ValueError, match="Missing monthly returns.*2025-03.*B"):
        portfolio_monthly_returns(monthly_returns, ["2025-03"], {"A": 0.5, "B": 0.5})


def test_fast_simulation_builds_trimmed_forward_report() -> None:
    report = run_fast_simulation("2025-03", "medium", duration_months=3)
    assert report["month"] == "2025-03"
    assert report["riskLevel"] == "medium"
    assert report["simulatorMode"] == "single"
    assert report["optimizerMode"] == "external_model"
    assert report["durationMonths"] == 3
    assert report["requestedDurationMonths"] == 3
    assert len(report["chartIntervals"]) == 4
    assert len(report["monthlyReturns"]) == 3
    assert set(report["monthlyReturns"][0]) == {
        "month",
        "split",
        "optimizedPortfolio",
        "optimizedRawUniverse",
        "assignedRiskBucket",
        "egx30",
    }
    assert [row["split"] for row in report["monthlyReturns"]] == ["test", "test", "test"]
    assert {row["id"] for row in report["comparison"]} == {
        "optimizedPortfolio",
        "optimizedRawUniverse",
        "assignedRiskBucket",
        "egx30",
    }
    assert report["pipeline"]["activeUniverseCount"] >= report["pipeline"]["selectedAssetCount"] > 0
    assert len(report["pipeline"]["activeUniverse"]) == report["pipeline"]["activeUniverseCount"]
    assert len(report["pipeline"]["selectedAssets"]) == report["pipeline"]["selectedAssetCount"]
    assert report["pipeline"]["optimizerWeightSum"] == pytest.approx(1.0)
    assert len(report["rebalanceTimeline"]) == 1
    assert report["rebalanceTimeline"][0]["month"] == "2025-03"
    assert report["rebalanceTimeline"][0]["startingValue"] == pytest.approx(1.0)
    assert report["rebalanceTimeline"][0]["endingValue"] == pytest.approx(
        1.0 + report["rebalanceTimeline"][0]["monthlyReturn"]
    )
    selected_asset_ids = {asset["assetId"] for asset in report["pipeline"]["selectedAssets"]}
    assert selected_asset_ids
    assert all(asset["selectedByFilter"] for asset in report["pipeline"]["selectedAssets"])
    assert all(asset["optimizedWeight"] is not None for asset in report["pipeline"]["selectedAssets"])
    assert selected_asset_ids.issubset({asset["assetId"] for asset in report["pipeline"]["activeUniverse"]})
    assert all("predictedRisk" not in asset for asset in report["pipeline"]["activeUniverse"])
    assert all("predictedRankPct" not in asset for asset in report["pipeline"]["activeUniverse"])
    assert "selectedAssets" not in report
    assert "filterImpact" not in report
    assert "riskComponents" not in report
    assert "rawRiskComponents" not in report
    assert "optimizerDiagnostics" not in report
    assert "requiredExternalContracts" not in report


def test_explicit_single_simulation_mode_matches_single_contract() -> None:
    report = run_fast_simulation("2025-03", "medium", duration_months=1, simulator_mode="single")

    assert report["simulatorMode"] == "single"
    assert report["durationMonths"] == 1
    assert len(report["rebalanceTimeline"]) == 1
    assert report["rebalanceTimeline"][0]["selectedAssetCount"] == report["pipeline"]["selectedAssetCount"]


def test_production_profile_exposes_public_benchmark_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIMULATOR_PROFILE", "production")

    report = run_fast_simulation("2025-03", "medium", duration_months=1, simulator_mode="single")

    assert [row["id"] for row in report["comparison"]] == [
        "egx30",
        "optimizedRawUniverse",
        "optimizedPortfolio",
    ]
    assert [row["label"] for row in report["comparison"]] == [
        "EGX30",
        "MVO on FULL Asset universe",
        "FULL pipeline",
    ]
    with pytest.raises(ValueError, match="Monthly rebalance simulator mode is available only"):
        run_fast_simulation("2025-03", "medium", duration_months=1, simulator_mode="monthly_rebalance")


def test_monthly_rebalance_recomputes_decisions_for_each_month(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, tuple[str, ...]]] = []

    def fake_optimizer(*, tier: str, target_month: str, asset_ids: list[str], daily_market):
        calls.append((target_month, tuple(asset_ids)))
        weight = 1.0 / len(asset_ids)
        return SimpleNamespace(
            weights={asset_id: weight for asset_id in asset_ids},
            sum_check=1.0,
            decision_date=f"{target_month}-01",
        )

    monkeypatch.setattr(simulation_module, "run_weight_optimizer", fake_optimizer)
    report = simulation_module.run_fast_simulation(
        "2025-03",
        "medium",
        duration_months=3,
        simulator_mode="monthly_rebalance",
    )

    assert report["simulatorMode"] == "monthly_rebalance"
    assert report["durationMonths"] == 3
    assert [row["month"] for row in report["rebalanceTimeline"]] == ["2025-03", "2025-04", "2025-05"]
    assert len(calls) == 6
    assert [month for month, _assets in calls] == [
        "2025-03",
        "2025-03",
        "2025-04",
        "2025-04",
        "2025-05",
        "2025-05",
    ]
    predictions = read_predictions()
    for index, month in enumerate(["2025-03", "2025-04", "2025-05"]):
        selected, _split = select_assets(month, "medium")
        expected_selected = tuple(selected["AssetID"].astype(str).tolist())
        expected_universe = tuple(
            predictions.loc[
                predictions["Date"].eq(month) & predictions["Split"].isin(VALID_SPLITS),
                "AssetID",
            ]
            .astype(str)
            .tolist()
        )
        assert calls[index * 2] == (month, expected_selected)
        assert calls[(index * 2) + 1] == (month, expected_universe)
    assert calls[0][1] != calls[2][1]
    assert report["rebalanceTimeline"][1]["startingValue"] == pytest.approx(
        report["rebalanceTimeline"][0]["endingValue"]
    )
    assert [row["split"] for row in report["monthlyReturns"]] == ["test", "test", "test"]
    assert {row["id"] for row in report["comparison"]} == {
        "optimizedPortfolio",
        "optimizedRawUniverse",
        "assignedRiskBucket",
        "egx30",
    }
    assert report["comparison"][0]["label"].startswith("Monthly rebalanced")


def test_fast_endpoint_serializes_multi_month_rebalance(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_optimizer(*, tier: str, target_month: str, asset_ids: list[str], daily_market):
        weight = 1.0 / len(asset_ids)
        return SimpleNamespace(
            weights={asset_id: weight for asset_id in asset_ids},
            sum_check=1.0,
            decision_date=f"{target_month}-01",
        )

    monkeypatch.setattr(simulation_module, "run_weight_optimizer", fake_optimizer)
    client = TestClient(app)
    response = client.post(
        "/api/simulations/fast",
        json={
            "month": "2025-03",
            "riskLevel": "medium",
            "durationMonths": 3,
            "simulatorMode": "monthly_rebalance",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["simulatorMode"] == "monthly_rebalance"
    assert [row["month"] for row in payload["rebalanceTimeline"]] == ["2025-03", "2025-04", "2025-05"]
    assert [row["month"] for row in payload["monthlyReturns"]] == ["2025-03", "2025-04", "2025-05"]
    assert [row["split"] for row in payload["monthlyReturns"]] == ["test", "test", "test"]
    assert payload["rebalanceTimeline"][1]["startingValue"] == pytest.approx(
        payload["rebalanceTimeline"][0]["endingValue"]
    )
    assert "Long monthly rebalance windows" not in payload["thesisSafeSummary"]


def test_long_monthly_rebalance_reports_runtime_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_optimizer(*, tier: str, target_month: str, asset_ids: list[str], daily_market):
        weight = 1.0 / len(asset_ids)
        return SimpleNamespace(
            weights={asset_id: weight for asset_id in asset_ids},
            sum_check=1.0,
            decision_date=f"{target_month}-01",
        )

    monkeypatch.setattr(simulation_module, "run_weight_optimizer", fake_optimizer)
    report = simulation_module.run_fast_simulation(
        "2025-03",
        "medium",
        duration_months=6,
        simulator_mode="monthly_rebalance",
    )

    assert "Long monthly rebalance windows can take noticeably longer" in report["thesisSafeSummary"]


def test_duration_reports_requested_and_available_months() -> None:
    report = run_fast_simulation("2025-12", "low", duration_months=12)
    assert report["requestedDurationMonths"] == 12
    assert report["durationMonths"] < 12


def test_optimizer_missing_artifacts_return_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(optimizer_module, "MODEL_DIR", Path(__file__).resolve().parent / "missing-optimizer-models")
    optimizer_module._load_bundle.cache_clear()
    client = TestClient(app)
    response = client.post("/api/simulations/fast", json={"month": "2025-03", "riskLevel": "medium"})
    assert response.status_code == 503
    assert "Missing weight optimizer deployment artifacts" in response.json()["detail"]
    optimizer_module._load_bundle.cache_clear()


def test_questionnaire_feature_vector_uses_exact_order() -> None:
    assert build_feature_vector(SAMPLE_QUESTIONNAIRE) == [29.0, 1.0, 2.0, 2.0, 1.0, 0.0, 1.0, 0.0, 1.0]


def test_questionnaire_model_predicts_valid_risk_level() -> None:
    inference = predict_questionnaire_risk(SAMPLE_QUESTIONNAIRE)
    assert inference["riskClass"] in {0, 1, 2}
    assert inference["riskLevel"] in {"low", "medium", "high"}
    assert inference["riskLabel"] in {"Conservative", "Moderate", "Aggressive"}
    assert set(inference["probabilities"]).issubset({"Conservative", "Moderate", "Aggressive"})
    assert sum(inference["probabilities"].values()) == pytest.approx(1.0)
    assert 0.0 <= inference["riskScore"] <= 100.0
    assert "featureNames" not in inference
    assert "featureVector" not in inference


def test_questionnaire_mapping_matches_controlled_profiles() -> None:
    conservative = {
        "gender": "Female",
        "age": 60,
        "Duration": "Less than 1 year",
        "Invest_Monitor": "Monthly",
        "Expect": "10%-20%",
        "Objective": "Income",
        "Purpose": "Savings for Future",
        "What are your savings objectives?": "Retirement Plan",
    }
    aggressive = {
        "gender": "Male",
        "age": 22,
        "Duration": "More than 5 years",
        "Invest_Monitor": "Daily",
        "Expect": "30%-40%",
        "Objective": "Growth",
        "Purpose": "Wealth Creation",
        "What are your savings objectives?": "Education",
    }

    assert predict_questionnaire_risk(conservative)["riskLevel"] == "low"
    assert predict_questionnaire_risk(aggressive)["riskLevel"] == "high"


def test_questionnaire_simulation_attaches_inference_metadata() -> None:
    report = run_questionnaire_simulation("2025-03", SAMPLE_QUESTIONNAIRE, duration_months=1)
    inference = report["questionnaireInference"]
    assert report["riskLevel"] == inference["riskLevel"]
    assert report["simulatorMode"] == "single"
    assert report["durationMonths"] == 1
    assert "featureVector" not in inference


def test_questionnaire_endpoint_returns_model_inference_metadata() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/simulations/questionnaire",
        json={
            "month": "2025-03",
            "durationMonths": 1,
            "simulatorMode": "monthly_rebalance",
            "questionnaire": SAMPLE_QUESTIONNAIRE,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    inference = payload["questionnaireInference"]
    assert payload["riskLevel"] == inference["riskLevel"]
    assert payload["simulatorMode"] == "monthly_rebalance"
    assert len(payload["rebalanceTimeline"]) == 1
    assert sum(inference["probabilities"].values()) == pytest.approx(1.0)
    assert "featureVector" not in inference


def test_questionnaire_endpoint_validates_invalid_category() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/simulations/questionnaire",
        json={
            "month": "2025-03",
            "durationMonths": 1,
            "questionnaire": {**SAMPLE_QUESTIONNAIRE, "Expect": "50%-60%"},
        },
    )
    assert response.status_code == 422


def test_questionnaire_missing_model_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(questionnaire_module, "_MODEL", None)
    monkeypatch.setattr(questionnaire_module, "MODEL_PATH", Path(__file__).resolve().parent / "missing.pkl")
    client = TestClient(app)
    response = client.post(
        "/api/simulations/questionnaire",
        json={"month": "2025-03", "durationMonths": 1, "questionnaire": SAMPLE_QUESTIONNAIRE},
    )
    assert response.status_code == 503
    assert "Missing risk-tolerance model" in response.json()["detail"]
    monkeypatch.setattr(questionnaire_module, "_MODEL", None)
