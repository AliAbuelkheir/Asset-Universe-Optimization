from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import config
from src.data_processing import build_model_dataset as builder


ROOT = Path(__file__).resolve().parents[1]


def test_parse_volume_handles_suffixes_and_missing_values() -> None:
    series = pd.Series(["1.5K", "2M", "3B", "42", "", "-", np.nan])
    parsed = builder.parse_volume(series)

    assert parsed.iloc[0] == pytest.approx(1_500.0)
    assert parsed.iloc[1] == pytest.approx(2_000_000.0)
    assert parsed.iloc[2] == pytest.approx(3_000_000_000.0)
    assert parsed.iloc[3] == pytest.approx(42.0)
    assert math.isnan(parsed.iloc[4])
    assert math.isnan(parsed.iloc[5])
    assert math.isnan(parsed.iloc[6])


def test_align_to_egx_calendar_forward_fills_price_only_with_limit() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2023-01-01", "2023-01-10"]),
            "QuotedValue": [100.0, 110.0],
            "PriceForReturn": [100.0, 110.0],
            "Volume": [1_000.0, 2_000.0],
            "ChangePctRaw": [0.01, 0.02],
        }
    )

    aligned = builder.align_to_egx_calendar(frame)
    aligned = aligned.set_index("Date")

    filled_date = pd.Timestamp("2023-01-08")
    over_limit_date = pd.Timestamp("2023-01-09")

    assert aligned.loc[filled_date, "IsObserved"] == 0
    assert aligned.loc[filled_date, "PriceForReturn"] == pytest.approx(100.0)
    assert aligned.loc[filled_date, "ReturnFromPrice"] == pytest.approx(0.0)
    assert math.isnan(aligned.loc[filled_date, "Volume"])
    assert math.isnan(aligned.loc[filled_date, "ChangePctRaw"])

    assert aligned.loc[over_limit_date, "IsObserved"] == 0
    assert math.isnan(aligned.loc[over_limit_date, "PriceForReturn"])
    assert math.isnan(aligned.loc[over_limit_date, "ReturnFromPrice"])


def test_compute_downside_deviation_matches_manual_formula() -> None:
    returns = pd.Series([-0.10, 0.02, -0.20])
    expected = math.sqrt(((0.10**2) + 0.0 + (0.20**2)) / 3.0) * math.sqrt(config.TRADING_DAYS_PER_YEAR)

    actual = builder.compute_downside_deviation(returns)

    assert actual == pytest.approx(expected)


def test_compute_max_drawdown_matches_manual_formula() -> None:
    returns = pd.Series([0.10, -0.20, 0.05, -0.10])
    growth = (1.0 + returns).cumprod()
    expected = abs(((growth / growth.cummax()) - 1.0).min())

    actual = builder.compute_max_drawdown(returns)

    assert actual == pytest.approx(expected)


def test_compute_trailing_volume_uses_sum_and_defaults_to_zero() -> None:
    assert builder.compute_trailing_volume(pd.Series([100.0, 200.0, np.nan])) == pytest.approx(300.0)
    assert builder.compute_trailing_volume(pd.Series([np.nan, np.nan])) == pytest.approx(0.0)


def test_walk_forward_egarch_month_stats_ignore_future_months() -> None:
    dates = pd.bdate_range("2020-01-01", periods=66)
    base_returns = pd.Series(np.linspace(-0.02, 0.02, len(dates)))
    months = dates.to_period("M")

    frame = pd.DataFrame(
        {
            "Date": dates,
            "Month": months,
            "ReturnFromPrice": base_returns,
            "IsObserved": 1,
            "AssetName": "Asset",
            "AssetGroup": "Equity",
        }
    )
    modified = frame.copy()
    future_month = pd.Period("2020-03", freq="M")
    modified.loc[modified["Month"] == future_month, "ReturnFromPrice"] = 0.35

    original_stats = builder.compute_walk_forward_egarch_month_stats(frame)
    modified_stats = builder.compute_walk_forward_egarch_month_stats(modified)

    assert original_stats[pd.Period("2020-01", freq="M")]["mean"] == pytest.approx(
        modified_stats[pd.Period("2020-01", freq="M")]["mean"]
    )
    assert original_stats[pd.Period("2020-02", freq="M")]["mean"] == pytest.approx(
        modified_stats[pd.Period("2020-02", freq="M")]["mean"]
    )


def test_load_cpi_series_removes_blank_header_and_trailing_notes(tmp_path: Path) -> None:
    raw_dir = tmp_path / "rawData"
    raw_dir.mkdir()
    (raw_dir / "CPI.csv").write_text(
        ",,,,\n"
        "Date,Headline (m/m),Core (m/m),Regulated Items (m/m),Fruits and Vegetables (m/m)\n"
        "Jan 2020,1.000%,,,\n"
        "Dec 2019,0.500%,,,\n"
        "note,,,,\n",
        encoding="utf-8",
    )

    cpi = builder.load_cpi_series(raw_dir)

    assert list(cpi["Month"].astype(str)) == ["2019-12", "2020-01"]
    assert list(cpi["HeadlineMoM"]) == pytest.approx([0.005, 0.01])


def test_prepare_asset_series_converts_yield_quotes_before_returns(tmp_path: Path) -> None:
    raw_dir = tmp_path / "rawData"
    raw_dir.mkdir()
    csv_path = raw_dir / "MoneyMarket.csv"
    csv_path.write_text(
        '"Date","Price","Vol.","Change %"\n'
        '"01/10/2023","10.0","","0.00%"\n'
        '"01/09/2023","20.0","","0.00%"\n',
        encoding="utf-8",
    )

    spec = builder.AssetSpec(
        asset_id="MoneyMarket",
        asset_name="91-Day T-Bills",
        asset_group="MoneyMarket",
        file_name="MoneyMarket.csv",
        series_kind="yield",
        maturity_days=config.MONEY_MARKET_MATURITY_DAYS,
    )

    aligned, _ = builder.prepare_asset_series(raw_dir, spec)
    observed = aligned.loc[aligned["IsObserved"] == 1, ["Date", "QuotedValue", "PriceForReturn", "ReturnFromPrice"]]
    observed = observed.set_index("Date").sort_index()

    expected_prices = builder.convert_yield_to_price_proxy(pd.Series([20.0, 10.0]), config.MONEY_MARKET_MATURITY_DAYS)
    expected_return = (expected_prices.iloc[1] / expected_prices.iloc[0]) - 1.0

    assert observed.iloc[0]["PriceForReturn"] == pytest.approx(expected_prices.iloc[0])
    assert observed.iloc[1]["PriceForReturn"] == pytest.approx(expected_prices.iloc[1])
    assert observed.iloc[1]["ReturnFromPrice"] == pytest.approx(expected_return)


def test_compute_monthly_panel_builds_expected_normalized_features() -> None:
    macro_features = {
        pd.Period("2010-11", freq="M"): {
            "usd_vol": 0.25,
            "cpi_trajectory": 0.05,
        }
    }

    def asset_frame(
        asset_id: str,
        asset_name: str,
        feature_returns: list[float],
        target_returns: list[float],
        feature_volumes: list[float],
        target_volumes: list[float],
    ) -> pd.DataFrame:
        months = pd.PeriodIndex(["2010-08", "2010-09", "2010-10", "2010-11", "2010-11"], freq="M")
        return pd.DataFrame(
            {
                "Date": pd.to_datetime(["2010-08-01", "2010-09-01", "2010-10-01", "2010-11-01", "2010-11-02"]),
                "Month": months,
                "ReturnFromPrice": feature_returns + target_returns,
                "Volume": feature_volumes + target_volumes,
                "IsObserved": [1, 1, 1, 1, 1],
                "AssetName": [asset_name] * 5,
                "AssetGroup": ["Equity"] * 5,
            }
        )

    daily_assets = {
        "A": asset_frame("A", "Asset A", [0.0, -0.01, 0.0], [0.0, -0.02], [100.0, 100.0, 100.0], [50.0, 50.0]),
        "B": asset_frame("B", "Asset B", [0.0, -0.02, 0.0], [0.0, -0.03], [200.0, 200.0, 200.0], [50.0, 50.0]),
        "C": asset_frame("C", "Asset C", [0.0, -0.03, 0.0], [0.0, -0.04], [300.0, 300.0, 300.0], [50.0, 50.0]),
    }
    egarch_month_stats_by_asset = {
        "A": {
            pd.Period("2010-08", freq="M"): {"sum": 0.10, "count": 1, "mean": 0.10},
            pd.Period("2010-09", freq="M"): {"sum": 0.10, "count": 1, "mean": 0.10},
            pd.Period("2010-10", freq="M"): {"sum": 0.10, "count": 1, "mean": 0.10},
            pd.Period("2010-11", freq="M"): {"sum": 0.20, "count": 1, "mean": 0.20},
        },
        "B": {
            pd.Period("2010-08", freq="M"): {"sum": 0.20, "count": 1, "mean": 0.20},
            pd.Period("2010-09", freq="M"): {"sum": 0.20, "count": 1, "mean": 0.20},
            pd.Period("2010-10", freq="M"): {"sum": 0.20, "count": 1, "mean": 0.20},
            pd.Period("2010-11", freq="M"): {"sum": 0.40, "count": 1, "mean": 0.40},
        },
        "C": {
            pd.Period("2010-08", freq="M"): {"sum": 0.30, "count": 1, "mean": 0.30},
            pd.Period("2010-09", freq="M"): {"sum": 0.30, "count": 1, "mean": 0.30},
            pd.Period("2010-10", freq="M"): {"sum": 0.30, "count": 1, "mean": 0.30},
            pd.Period("2010-11", freq="M"): {"sum": 0.60, "count": 1, "mean": 0.60},
        },
    }

    panel = builder.compute_monthly_panel(daily_assets, macro_features, egarch_month_stats_by_asset)
    panel = panel.sort_values("AssetID").reset_index(drop=True)

    expected_levels = [0.0, 0.5, 1.0]
    assert list(panel["Date"].unique()) == ["2010-11"]
    assert list(panel["egarch_vol"]) == pytest.approx(expected_levels)
    assert list(panel["downside_dev"]) == pytest.approx(expected_levels)
    assert list(panel["max_drawdown"]) == pytest.approx(expected_levels)
    assert list(panel["volume"]) == pytest.approx(expected_levels)
    assert list(panel["realized_egarch_vol"]) == pytest.approx(expected_levels)
    assert list(panel["realized_downside_dev"]) == pytest.approx(expected_levels)
    assert list(panel["realized_max_drawdown"]) == pytest.approx(expected_levels)
    assert list(panel["realized_risk"]) == pytest.approx(expected_levels)
    assert list(panel["realized_rank"]) == pytest.approx([1.0, 2.0, 3.0])
    assert panel["usd_vol"].nunique() == 1
    assert panel["cpi_trajectory"].nunique() == 1


@pytest.fixture(scope="session")
def built_outputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    daily_path = ROOT / config.READY_DATA_DIR / config.DAILY_MARKET_SERIES_NAME
    panel_path = ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME

    if not daily_path.exists() or not panel_path.exists():
        builder.main()

    daily = pd.read_csv(daily_path)
    panel = pd.read_csv(panel_path)
    return daily, panel


def test_monthly_panel_matches_recomputed_panel_from_daily_output(built_outputs: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    daily, stored_panel = built_outputs

    daily = daily.copy()
    daily["Date"] = pd.to_datetime(daily["Date"])
    daily["Month"] = daily["Date"].dt.to_period("M")

    usd_daily = daily.loc[daily["AssetID"] == "USD"].copy()
    scoring_daily = daily.loc[daily["AssetID"] != "USD"].copy()

    cpi = builder.load_cpi_series(ROOT / config.RAW_DATA_DIR)
    macro_features = builder.compute_macro_features(usd_daily, cpi)

    daily_assets: dict[str, pd.DataFrame] = {}
    for asset_id, frame in scoring_daily.groupby("AssetID", sort=False):
        daily_assets[asset_id] = frame.copy()

    recomputed = builder.compute_monthly_panel(daily_assets, macro_features)
    stored = stored_panel.sort_values(["Date", "AssetID"]).reset_index(drop=True)
    recomputed = recomputed.sort_values(["Date", "AssetID"]).reset_index(drop=True)

    assert list(stored[["Date", "AssetID"]].itertuples(index=False, name=None)) == list(
        recomputed[["Date", "AssetID"]].itertuples(index=False, name=None)
    )

    for col in ["usd_vol", "cpi_trajectory"]:
        assert np.allclose(stored[col], recomputed[col], atol=1e-12, rtol=1e-12)

    month_sizes = stored.groupby("Date")["AssetID"].transform("count").to_numpy()
    max_rank_step = 1.0 / (month_sizes - 1)

    normalized_columns = [
        "egarch_vol",
        "downside_dev",
        "max_drawdown",
        "volume",
        "realized_egarch_vol",
        "realized_downside_dev",
        "realized_max_drawdown",
        "realized_risk",
    ]
    for col in normalized_columns:
        diffs = np.abs(stored[col].to_numpy() - recomputed[col].to_numpy())
        assert np.all(
            diffs <= (max_rank_step + 1e-12)
        ), f"{col} drift exceeded one monthly rank step after CSV roundtrip"

    rank_diffs = np.abs(stored["realized_rank"].to_numpy() - recomputed["realized_rank"].to_numpy())
    assert np.all(rank_diffs <= 2.0)
