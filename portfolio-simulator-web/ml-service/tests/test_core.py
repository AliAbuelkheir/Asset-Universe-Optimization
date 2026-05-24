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
from app.mvo import MAX_ASSET_WEIGHT, run_mvo_full_universe
from app.optimizer import OptimizerContractError
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

INTERNAL_SUMMARY_TERMS = (
    "PPO",
    "external optimizer",
    "external weight optimizer",
    "external weights",
    "MVO",
    "predicted rank",
    "decision date",
    "optimizer inference",
    "model weights",
)

BENCHMARK_IDS = [
    "optimizedPortfolio",
    "optimizerFullUniverse",
    "mvoFilteredUniverse",
    "mvoFullUniverse",
    "egx30",
]

BENCHMARK_LABELS = [
    "Profile optimizer portfolio",
    "Full-universe optimizer benchmark",
    "Profile MVO benchmark",
    "Full-universe MVO benchmark",
    "EGX30",
]


def assert_public_historical_summary(summary: str) -> None:
    assert "historical" in summary
    assert "realized" in summary
    assert "guaranteed investment performance" in summary
    for term in INTERNAL_SUMMARY_TERMS:
        assert term.lower() not in summary.lower()


def test_health_reports_real_artifact_availability() -> None:
    payload = health()
    assert payload["ppoRootExists"] is True
    assert payload["predictionsAvailable"] is True
    assert payload["dailyMarketAvailable"] is True
    assert payload["monthlyPanelAvailable"] is True
    assert payload["questionnaireModelAvailable"] is True
    assert payload["optimizerMode"] == "external_model"
    assert payload["optimizerRuntimeAvailable"] is True
    assert payload["status"] == "ok"


def test_available_months_include_reportable_months() -> None:
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
    selected = select_assets("2025-03", "medium")
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
        "optimizedPortfolio",
        "optimizerFullUniverse",
        "mvoFilteredUniverse",
        "mvoFullUniverse",
        "egx30",
    }
    assert "optimizedRawUniverse" not in report["monthlyReturns"][0]
    assert "assignedRiskBucket" not in report["monthlyReturns"][0]
    assert [row["id"] for row in report["comparison"]] == BENCHMARK_IDS
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
    assert_public_historical_summary(report["thesisSafeSummary"])


def test_explicit_single_simulation_mode_matches_single_contract() -> None:
    report = run_fast_simulation("2025-03", "medium", duration_months=1, simulator_mode="single")

    assert report["simulatorMode"] == "single"
    assert report["durationMonths"] == 1
    assert len(report["rebalanceTimeline"]) == 1
    assert report["rebalanceTimeline"][0]["selectedAssetCount"] == report["pipeline"]["selectedAssetCount"]


def test_production_profile_exposes_core_benchmark_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIMULATOR_PROFILE", "production")

    report = run_fast_simulation("2025-03", "medium", duration_months=1, simulator_mode="single")

    assert [row["id"] for row in report["comparison"]] == BENCHMARK_IDS
    assert [row["label"] for row in report["comparison"]] == BENCHMARK_LABELS

    monthly_report = run_fast_simulation("2025-03", "medium", duration_months=1, simulator_mode="monthly_rebalance")
    assert monthly_report["simulatorMode"] == "monthly_rebalance"
    assert [row["id"] for row in monthly_report["comparison"]] == BENCHMARK_IDS
    assert len(monthly_report["rebalanceTimeline"]) == 1


def test_local_profile_exposes_same_core_benchmark_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIMULATOR_PROFILE", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    report = run_fast_simulation("2025-03", "medium", duration_months=1, simulator_mode="single")

    assert [row["id"] for row in report["comparison"]] == BENCHMARK_IDS


def test_mvo_full_universe_weights_are_long_only_capped_and_historical() -> None:
    predictions = read_predictions()
    target_month = "2025-03"
    asset_ids = (
        predictions.loc[
            predictions["Date"].eq(target_month) & predictions["Split"].isin(VALID_SPLITS),
            "AssetID",
        ]
        .astype(str)
        .tolist()
    )
    run = run_mvo_full_universe(
        risk_level="medium",
        target_month=target_month,
        asset_ids=asset_ids,
        daily_market=simulation_module.read_daily_market(),
    )

    assert sum(run.weights.values()) == pytest.approx(1.0)
    assert all(0.0 <= weight <= MAX_ASSET_WEIGHT + 1e-8 for weight in run.weights.values())
    assert run.decision_date < f"{target_month}-01"


def test_mvo_ignores_synthetic_forward_filled_rows() -> None:
    observed_dates = pd.date_range("2024-06-03", periods=24, freq="B")
    synthetic_dates = pd.date_range("2024-07-08", periods=24, freq="B")
    rows = []
    for asset_id, base_return in [("A", 0.01), ("B", 0.002), ("C", -0.001), ("D", 0.003), ("E", 0.004)]:
        for index, date in enumerate(observed_dates):
            rows.append(
                {
                    "Date": date,
                    "AssetID": asset_id,
                    "ReturnFromPrice": base_return + index * 0.0001,
                    "IsObserved": 1,
                }
            )
        for date in synthetic_dates:
            rows.append(
                {
                    "Date": date,
                    "AssetID": asset_id,
                    "ReturnFromPrice": 0.50,
                    "IsObserved": 0,
                }
            )
    daily_market = pd.DataFrame(rows)

    run = run_mvo_full_universe(
        risk_level="medium",
        target_month="2024-08",
        asset_ids=["A", "B", "C", "D", "E"],
        daily_market=daily_market,
    )

    assert run.decision_date == str(observed_dates[-1].date())
    assert sum(run.weights.values()) == pytest.approx(1.0)


def test_optimizer_rejects_non_finite_sum_check() -> None:
    with pytest.raises(OptimizerContractError, match="non-finite sum_check"):
        optimizer_module._validate_optimizer_weights(
            requested_asset_ids=["A", "B"],
            weights={"A": 0.5, "B": 0.5},
            sum_check=float("nan"),
            target_month="2025-03",
        )


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

    def fake_mvo(*, risk_level: str, target_month: str, asset_ids: list[str], daily_market):
        weight = 1.0 / len(asset_ids)
        return SimpleNamespace(
            weights={asset_id: weight for asset_id in asset_ids},
            sum_check=1.0,
            decision_date=f"{target_month}-01",
        )

    monkeypatch.setattr(simulation_module, "run_weight_optimizer", fake_optimizer)
    monkeypatch.setattr(simulation_module, "run_mvo_allocation", fake_mvo)
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
    for index, month in enumerate(["2025-03", "2025-04", "2025-05"]):
        selected = select_assets(month, "medium")
        expected_selected = tuple(selected["AssetID"].astype(str).tolist())
        assert calls[index * 2] == (month, expected_selected)
        assert len(calls[index * 2 + 1][1]) >= len(expected_selected)
    assert calls[0][1] != calls[2][1]
    assert report["rebalanceTimeline"][1]["startingValue"] == pytest.approx(
        report["rebalanceTimeline"][0]["endingValue"]
    )
    assert [row["id"] for row in report["comparison"]] == BENCHMARK_IDS
    assert report["comparison"][0]["label"] == "Profile optimizer portfolio"


def test_fast_endpoint_serializes_multi_month_rebalance(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_optimizer(*, tier: str, target_month: str, asset_ids: list[str], daily_market):
        weight = 1.0 / len(asset_ids)
        return SimpleNamespace(
            weights={asset_id: weight for asset_id in asset_ids},
            sum_check=1.0,
            decision_date=f"{target_month}-01",
        )

    def fake_mvo(*, risk_level: str, target_month: str, asset_ids: list[str], daily_market):
        weight = 1.0 / len(asset_ids)
        return SimpleNamespace(
            weights={asset_id: weight for asset_id in asset_ids},
            sum_check=1.0,
            decision_date=f"{target_month}-01",
        )

    monkeypatch.setattr(simulation_module, "run_weight_optimizer", fake_optimizer)
    monkeypatch.setattr(simulation_module, "run_mvo_allocation", fake_mvo)
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
    assert "optimizerFullUniverse" in payload["monthlyReturns"][0]
    assert "mvoFilteredUniverse" in payload["monthlyReturns"][0]
    assert "mvoFullUniverse" in payload["monthlyReturns"][0]
    assert "assignedRiskBucket" not in payload["monthlyReturns"][0]
    assert "optimizedRawUniverse" not in payload["monthlyReturns"][0]
    assert payload["rebalanceTimeline"][1]["startingValue"] == pytest.approx(
        payload["rebalanceTimeline"][0]["endingValue"]
    )
    assert "Long monthly review windows" not in payload["thesisSafeSummary"]
    assert "historical monthly review diagnostic" in payload["thesisSafeSummary"]
    assert_public_historical_summary(payload["thesisSafeSummary"])


def test_long_monthly_rebalance_reports_runtime_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_optimizer(*, tier: str, target_month: str, asset_ids: list[str], daily_market):
        weight = 1.0 / len(asset_ids)
        return SimpleNamespace(
            weights={asset_id: weight for asset_id in asset_ids},
            sum_check=1.0,
            decision_date=f"{target_month}-01",
        )

    def fake_mvo(*, risk_level: str, target_month: str, asset_ids: list[str], daily_market):
        weight = 1.0 / len(asset_ids)
        return SimpleNamespace(
            weights={asset_id: weight for asset_id in asset_ids},
            sum_check=1.0,
            decision_date=f"{target_month}-01",
        )

    monkeypatch.setattr(simulation_module, "run_weight_optimizer", fake_optimizer)
    monkeypatch.setattr(simulation_module, "run_mvo_allocation", fake_mvo)
    report = simulation_module.run_fast_simulation(
        "2025-03",
        "medium",
        duration_months=6,
        simulator_mode="monthly_rebalance",
    )

    assert "Long monthly review windows can take noticeably longer" in report["thesisSafeSummary"]
    assert_public_historical_summary(report["thesisSafeSummary"])


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
