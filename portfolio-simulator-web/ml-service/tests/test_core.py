from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import optimizer as optimizer_module
from app import questionnaire as questionnaire_module
from app.data import available_months, risk_levels, select_assets
from app.main import app
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


def test_fast_simulation_builds_trimmed_forward_report() -> None:
    report = run_fast_simulation("2025-03", "medium", duration_months=3)
    assert report["month"] == "2025-03"
    assert report["riskLevel"] == "medium"
    assert report["optimizerMode"] == "external_model"
    assert report["durationMonths"] == 3
    assert report["requestedDurationMonths"] == 3
    assert len(report["chartIntervals"]) == 4
    assert len(report["monthlyReturns"]) == 3
    assert set(report["monthlyReturns"][0]) == {
        "month",
        "optimizedPortfolio",
        "optimizedRawUniverse",
        "assignedRiskBucket",
        "allEqualWeight",
        "egx30",
    }
    assert {row["id"] for row in report["comparison"]} == {
        "optimizedPortfolio",
        "optimizedRawUniverse",
        "assignedRiskBucket",
        "allEqualWeight",
        "egx30",
    }
    assert "selectedAssets" not in report
    assert "filterImpact" not in report
    assert "riskComponents" not in report
    assert "rawRiskComponents" not in report
    assert "optimizerDiagnostics" not in report
    assert "requiredExternalContracts" not in report


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
    assert build_feature_vector(SAMPLE_QUESTIONNAIRE) == [29.0, 1.0, 2.0, 2.0, 1.0, 1.0, 0.0, 0.0, 1.0]


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


def test_questionnaire_simulation_attaches_inference_metadata() -> None:
    report = run_questionnaire_simulation("2025-03", SAMPLE_QUESTIONNAIRE, duration_months=1)
    inference = report["questionnaireInference"]
    assert report["riskLevel"] == inference["riskLevel"]
    assert report["durationMonths"] == 1
    assert "featureVector" not in inference


def test_questionnaire_endpoint_returns_model_inference_metadata() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/simulations/questionnaire",
        json={"month": "2025-03", "durationMonths": 1, "questionnaire": SAMPLE_QUESTIONNAIRE},
    )
    assert response.status_code == 200
    payload = response.json()
    inference = payload["questionnaireInference"]
    assert payload["riskLevel"] == inference["riskLevel"]
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
