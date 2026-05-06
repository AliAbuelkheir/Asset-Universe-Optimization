from __future__ import annotations

from app.core import available_months, health, risk_levels, run_fast_simulation, select_assets


def test_health_reports_artifact_availability() -> None:
    payload = health()
    assert payload["ppoRootExists"] is True
    assert payload["predictionsAvailable"] is True
    assert payload["dailyMarketAvailable"] is True
    assert payload["monthlyPanelAvailable"] is True
    assert payload["optimizerMode"] == "mock_equal_weight"


def test_available_months_include_validation_and_test() -> None:
    months = available_months()
    month_labels = {row["month"] for row in months}
    assert "2023-01" in month_labels
    assert "2026-01" in month_labels


def test_select_assets_returns_bucket_assets() -> None:
    selected, split = select_assets("2025-03", "medium")
    assert split == "test"
    assert not selected.empty
    assert selected["PredictedRankPct"].between(0.25, 0.75, inclusive="both").all()


def test_fast_simulation_builds_forward_report() -> None:
    report = run_fast_simulation("2025-03", "medium", duration_months=3)
    assert report["month"] == "2025-03"
    assert report["riskLevel"] == "medium"
    assert report["optimizerMode"] == "mock_equal_weight"
    assert report["durationMonths"] == 3
    assert report["requestedDurationMonths"] == 3
    assert len(report["chartIntervals"]) == 4
    assert len(report["selectedAssets"]) > 0
    assert "predictedRisk" not in report["selectedAssets"][0]
    assert "weight" not in report["selectedAssets"][0]
    assert {"realizedVol", "realizedDownsideDev", "realizedMaxDrawdown"}.issubset(report["selectedAssets"][0])
    assert len(report["monthlyReturns"]) >= 1
    assert "optimizedPortfolio" not in report["monthlyReturns"][0]
    assert len(report["riskComponents"]) == 3
    assert {"realizedVol", "realizedDownsideDev", "realizedMaxDrawdown"}.issubset(
        report["riskComponents"][0]["components"]
    )
    assert len(report["rawRiskComponents"]) == 3
    assert {"annualizedVolatility", "annualizedDownsideDeviation", "maxDrawdown", "observations"}.issubset(
        report["rawRiskComponents"][0]["components"]
    )
    assert {row["id"] for row in report["comparison"]} == {
        "assignedRiskBucket",
        "allEqualWeight",
        "egx30",
    }
    assert report["assumptions"]


def test_duration_reports_requested_and_available_months() -> None:
    report = run_fast_simulation("2025-12", "low", duration_months=12)
    assert report["requestedDurationMonths"] == 12
    assert report["durationMonths"] < 12

def test_risk_level_contracts_are_exposed() -> None:
    levels = risk_levels()
    assert [level["id"] for level in levels] == ["low", "medium", "high"]
