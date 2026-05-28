from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from src import config
from src.data_processing import build_feature_candidate_dataset as candidate_builder
from src.data_processing import build_model_dataset as builder
from src.feature_candidates import (
    ADDITIVE_CANDIDATES,
    REPLACEMENT_CANDIDATES,
    get_shadow_candidate,
    ratio_tail_shortlist_candidate_ids,
)
from src.feature_profiles import feature_profile_ids, get_feature_profile
from src.input_feature_sets import get_input_feature_set


ROOT = Path(__file__).resolve().parents[1]


def make_asset_frame(
    asset_name: str,
    asset_group: str,
    base_close: float,
    daily_step: float,
    spread: float,
    volume_base: float,
    start: str = "2010-08-01",
    end: str = "2010-12-31",
) -> pd.DataFrame:
    dates = pd.date_range(start, end, freq=builder.EGX_BUSINESS_DAY)
    idx = np.arange(len(dates), dtype=float)
    close = base_close + (daily_step * idx) + (0.15 * np.sin(idx / 4.0))
    open_price = close - (daily_step / 2.0)
    high = np.maximum(open_price, close) + spread
    low = np.minimum(open_price, close) - spread
    returns = pd.Series(close).pct_change()
    volume = volume_base + (10.0 * idx)

    return pd.DataFrame(
        {
            "Date": dates,
            "Month": dates.to_period("M"),
            "QuotedValue": close,
            "OpenQuotedValue": open_price,
            "HighQuotedValue": high,
            "LowQuotedValue": low,
            "PriceForReturn": close,
            "OpenPriceForRange": open_price,
            "HighPriceForRange": high,
            "LowPriceForRange": low,
            "Volume": volume,
            "ChangePctRaw": returns,
            "ReturnFromPrice": returns,
            "IsObserved": 1,
            "AssetName": asset_name,
            "AssetGroup": asset_group,
        }
    )


def make_egarch_month_stats(*asset_ids: str) -> dict[str, dict[pd.Period, dict[str, float | int]]]:
    months = pd.period_range("2010-08", "2010-12", freq="M")
    stats: dict[str, dict[pd.Period, dict[str, float | int]]] = {}
    for idx, asset_id in enumerate(asset_ids, start=1):
        asset_stats: dict[pd.Period, dict[str, float | int]] = {}
        for month_idx, month in enumerate(months, start=1):
            mean = float(idx * month_idx / 10.0)
            asset_stats[month] = {
                "sum": mean * 5.0,
                "count": 5,
                "mean": mean,
                "last": mean + 0.01,
            }
        stats[asset_id] = asset_stats
    return stats


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


def test_feature_profile_registry_exposes_base_drop_and_first_wave_variants() -> None:
    assert config.DEFAULT_FEATURE_PROFILE_ID in feature_profile_ids()

    base = get_feature_profile(config.DEFAULT_FEATURE_PROFILE_ID)
    promoted_baseline = get_feature_profile("full_current_v2_no_distance_to_3m_high")
    drop_rsi = get_feature_profile("drop_rsi_14")
    atr_variant = get_feature_profile("atr_pct_14")
    macro_variant = get_feature_profile("cpi_last_mom")
    monthly_only = get_feature_profile("monthly_only_rows_v1")

    assert base.active_features == tuple(config.MODEL_FEATURE_COLUMNS)
    assert base.row_feature_window_months == config.WINDOW_MONTHS
    assert "distance_to_3m_high" not in promoted_baseline.active_features
    assert len(promoted_baseline.active_features) == len(config.MODEL_FEATURE_COLUMNS) - 1
    assert drop_rsi.change_type == "drop_feature"
    assert "rsi_14" not in drop_rsi.active_features
    assert atr_variant.atr_period == 14
    assert macro_variant.cpi_mode == "last_mom"
    assert monthly_only.row_feature_window_months == 1
    assert monthly_only.technical_min_periods_mode == "available"
    assert monthly_only.egarch_mode == "realized_vol_proxy"


def test_shadow_candidate_registry_classifies_replacement_and_additive_sets_without_mutating_canonical_schema() -> None:
    replacement = get_shadow_candidate("distance_to_1m_high")
    additive = get_shadow_candidate("distance_to_1m_low")
    additive_input_set = get_input_feature_set(additive.input_feature_set_id)

    assert replacement in REPLACEMENT_CANDIDATES
    assert replacement.candidate_type == "replacement"
    assert replacement.replacement_feature == "distance_to_3m_high"
    assert replacement.input_feature_set_id == config.DEFAULT_INPUT_FEATURE_SET_ID

    assert additive in ADDITIVE_CANDIDATES
    assert additive.candidate_type == "additive"
    assert additive.replacement_feature is None
    assert additive_input_set.feature_columns[:-1] == tuple(config.MODEL_FEATURE_COLUMNS)
    assert additive_input_set.feature_columns[-1] == "distance_to_1m_low"
    assert config.MODEL_FEATURE_COLUMNS == [
        "egarch_vol",
        "downside_dev",
        "max_drawdown",
        "volume",
        "atr_pct_20",
        "beta_to_egx30",
        "price_to_sma20",
        "rsi_14",
        "distance_to_3m_high",
        "usd_vol",
        "cpi_trajectory",
    ]


def test_canonical_panel_keeps_october_2025_test_month_with_36_active_assets() -> None:
    panel = pd.read_csv(ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME)
    october = panel.loc[panel["Date"].eq("2025-10")]

    assert len(october) == 36
    assert october["AssetID"].nunique() == 36
    assert "2025-10" >= config.TEST_START
    assert "2025-10" <= config.TEST_END


def test_ratio_and_tail_shadow_candidates_are_registered_in_shortlist_order() -> None:
    expected_ids = (
        "sortino_3m",
        "sortino_1m",
        "calmar_3m",
        "calmar_1m",
        "expected_shortfall_95_3m",
        "drawdown_duration_3m",
        "worst_return_1m",
        "max_abs_return_1m",
        "vol_of_vol_3m",
        "downside_tail_ratio_3m",
        "worst_return_3m",
        "max_abs_return_3m",
    )

    assert ratio_tail_shortlist_candidate_ids() == expected_ids
    additive_ids = tuple(candidate.candidate_id for candidate in ADDITIVE_CANDIDATES)
    for candidate_id in expected_ids:
        assert candidate_id in additive_ids
        feature_set = get_input_feature_set(f"shadow_add_{candidate_id}")
        assert feature_set.feature_columns[:-1] == tuple(config.MODEL_FEATURE_COLUMNS)
        assert feature_set.feature_columns[-1] == candidate_id


def test_top_positive_shadow_candidates_prefers_explicit_audit_flags() -> None:
    audit = pd.DataFrame(
        [
            {
                "CandidateID": "candidate_b",
                "StandaloneMeanSpearman": 0.30,
                "EligibleForRLScreen": True,
                "RLScreenOrder": 2,
            },
            {
                "CandidateID": "candidate_a",
                "StandaloneMeanSpearman": 0.10,
                "EligibleForRLScreen": True,
                "RLScreenOrder": 1,
            },
            {
                "CandidateID": "candidate_c",
                "StandaloneMeanSpearman": 0.40,
                "EligibleForRLScreen": False,
                "RLScreenOrder": pd.NA,
            },
        ]
    )

    assert candidate_builder.top_positive_shadow_candidates(audit) == ["candidate_a", "candidate_b"]


def test_apply_rl_screen_shortlist_override_marks_ratio_and_tail_wave_candidates() -> None:
    audit = pd.DataFrame(
        [
            {"CandidateID": "distance_to_1m_low", "StandaloneMeanSpearman": 0.30},
            {"CandidateID": "sortino_3m", "StandaloneMeanSpearman": -0.05},
            {"CandidateID": "calmar_3m", "StandaloneMeanSpearman": 0.01},
        ]
    )

    overridden = candidate_builder.apply_rl_screen_shortlist_override(audit)
    eligible = overridden.loc[overridden["EligibleForRLScreen"].fillna(False)].sort_values("RLScreenOrder")

    assert eligible["CandidateID"].tolist() == ["sortino_3m", "calmar_3m"]
    assert eligible["RLScreenOrder"].tolist() == [1, 3]
    assert eligible["RLScreenReason"].tolist() == ["approved_shortlist", "approved_shortlist"]
    assert not bool(
        overridden.loc[overridden["CandidateID"] == "distance_to_1m_low", "EligibleForRLScreen"].iloc[0]
    )


def test_compute_sortino_ratio_uses_zero_hurdle_and_downside_floor() -> None:
    returns = pd.Series([0.02, -0.01, 0.03, -0.02], dtype=float)
    expected = builder.compute_compounded_return(returns) / builder.compute_downside_deviation(returns)

    actual = candidate_builder._compute_sortino_ratio(returns)

    assert actual == pytest.approx(expected)
    assert math.isfinite(candidate_builder._compute_sortino_ratio(pd.Series([0.01, 0.02, 0.03], dtype=float)))


def test_compute_calmar_ratio_uses_drawdown_floor_and_ratio_clip_helper() -> None:
    returns = pd.Series([0.04, -0.03, 0.02, -0.01], dtype=float)
    expected = builder.compute_compounded_return(returns) / builder.compute_max_drawdown(returns)

    actual = candidate_builder._compute_calmar_ratio(returns)

    assert actual == pytest.approx(expected)
    assert math.isnan(candidate_builder._sanitize_ratio_candidate_value(float("inf")))
    assert candidate_builder._sanitize_ratio_candidate_value(12.5) == pytest.approx(10.0)
    assert candidate_builder._sanitize_ratio_candidate_value(-12.5) == pytest.approx(-10.0)


def test_compute_expected_shortfall_95_uses_worst_available_tail_slice() -> None:
    returns = pd.Series([-0.10, -0.04, 0.02, 0.03], dtype=float)

    assert candidate_builder._compute_expected_shortfall_95(returns) == pytest.approx(-0.10)


def test_compute_drawdown_duration_counts_longest_underwater_run() -> None:
    returns = pd.Series([0.10, -0.05, -0.02, 0.01, -0.03, 0.08], dtype=float)

    assert candidate_builder._compute_drawdown_duration(returns) == pytest.approx(5.0)


def test_compute_shock_candidate_helpers_use_clean_daily_returns() -> None:
    returns = pd.Series([0.02, -0.08, np.nan, 0.04, -0.03], dtype=float)

    assert candidate_builder._compute_worst_return(returns) == pytest.approx(-0.08)
    assert candidate_builder._compute_max_abs_return(returns) == pytest.approx(0.08)
    assert candidate_builder._compute_downside_tail_ratio(returns) == pytest.approx(0.08 / 0.17)


def test_compute_vol_of_vol_uses_monthly_return_volatility() -> None:
    frame = pd.DataFrame(
        {
            "Month": [
                pd.Period("2025-07", freq="M"),
                pd.Period("2025-07", freq="M"),
                pd.Period("2025-08", freq="M"),
                pd.Period("2025-08", freq="M"),
                pd.Period("2025-09", freq="M"),
                pd.Period("2025-09", freq="M"),
            ],
            "ReturnFromPrice": [0.01, -0.01, 0.03, -0.03, 0.05, -0.05],
        }
    )
    months = tuple(pd.period_range("2025-07", "2025-09", freq="M"))

    assert candidate_builder._compute_vol_of_vol_3m(frame, months) == pytest.approx(np.std([0.01, 0.03, 0.05]))


def test_load_market_csv_parses_ohlc_and_volume_fields(tmp_path: Path) -> None:
    raw_path = tmp_path / "sample.csv"
    raw_path.write_text(
        '"Date","Price","Open","High","Low","Vol.","Change %"\n'
        '"01/10/2023","10.5","10.0","11.0","9.5","1.5M","1.25%"\n',
        encoding="utf-8",
    )

    frame = builder.load_market_csv(raw_path)

    assert list(frame.columns) == [
        "Date",
        "QuotedValue",
        "OpenQuotedValue",
        "HighQuotedValue",
        "LowQuotedValue",
        "Volume",
        "ChangePctRaw",
    ]
    assert frame.iloc[0]["QuotedValue"] == pytest.approx(10.5)
    assert frame.iloc[0]["OpenQuotedValue"] == pytest.approx(10.0)
    assert frame.iloc[0]["HighQuotedValue"] == pytest.approx(11.0)
    assert frame.iloc[0]["LowQuotedValue"] == pytest.approx(9.5)
    assert frame.iloc[0]["Volume"] == pytest.approx(1_500_000.0)
    assert frame.iloc[0]["ChangePctRaw"] == pytest.approx(0.0125)


def test_align_to_egx_calendar_forward_fills_only_close_fields_and_keeps_ohlc_nan() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2023-01-01", "2023-01-10"]),
            "QuotedValue": [100.0, 110.0],
            "OpenQuotedValue": [99.0, 109.0],
            "HighQuotedValue": [101.0, 111.0],
            "LowQuotedValue": [98.0, 108.0],
            "PriceForReturn": [100.0, 110.0],
            "OpenPriceForRange": [99.0, 109.0],
            "HighPriceForRange": [101.0, 111.0],
            "LowPriceForRange": [98.0, 108.0],
            "Volume": [1_000.0, 2_000.0],
            "ChangePctRaw": [0.01, 0.02],
        }
    )

    aligned = builder.align_to_egx_calendar(frame).set_index("Date")
    filled_date = pd.Timestamp("2023-01-08")
    over_limit_date = pd.Timestamp("2023-01-09")

    assert aligned.loc[filled_date, "IsObserved"] == 0
    assert aligned.loc[filled_date, "PriceForReturn"] == pytest.approx(100.0)
    assert aligned.loc[filled_date, "ReturnFromPrice"] == pytest.approx(0.0)
    assert math.isnan(aligned.loc[filled_date, "OpenQuotedValue"])
    assert math.isnan(aligned.loc[filled_date, "HighPriceForRange"])
    assert math.isnan(aligned.loc[filled_date, "Volume"])

    assert aligned.loc[over_limit_date, "IsObserved"] == 0
    assert math.isnan(aligned.loc[over_limit_date, "PriceForReturn"])
    assert math.isnan(aligned.loc[over_limit_date, "ReturnFromPrice"])
    assert math.isnan(aligned.loc[over_limit_date, "LowPriceForRange"])


def test_annualized_volatility_matches_manual_formula() -> None:
    returns = pd.Series([0.01, 0.02, -0.01, 0.03])
    expected = returns.std(ddof=0) * math.sqrt(config.TRADING_DAYS_PER_YEAR)

    actual = builder.annualized_volatility(returns)

    assert actual == pytest.approx(expected)


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


def test_compute_price_to_sma_matches_manual_formula() -> None:
    closes = pd.Series(np.arange(1.0, 26.0))
    expected = (25.0 / np.mean(np.arange(6.0, 26.0))) - 1.0

    actual = builder.compute_price_to_sma(closes, window=20)

    assert actual == pytest.approx(expected)


def test_compute_wilder_rsi_matches_manual_formula() -> None:
    closes = pd.Series(
        [
            100.0,
            101.0,
            100.0,
            102.0,
            101.0,
            103.0,
            104.0,
            103.0,
            105.0,
            106.0,
            105.0,
            107.0,
            106.0,
            108.0,
            109.0,
            108.0,
        ]
    )
    deltas = closes.diff().dropna()
    gains = deltas.clip(lower=0.0)
    losses = -deltas.clip(upper=0.0)
    initial_gain = float(gains.iloc[:14].mean())
    initial_loss = float(losses.iloc[:14].mean())
    final_gain = ((initial_gain * 13) + float(gains.iloc[14])) / 14.0
    final_loss = ((initial_loss * 13) + float(losses.iloc[14])) / 14.0
    expected = 100.0 - (100.0 / (1.0 + (final_gain / final_loss)))

    actual = builder.compute_wilder_rsi(closes, periods=14)

    assert actual == pytest.approx(expected)


def test_compute_atr_pct_matches_manual_formula() -> None:
    frame = pd.DataFrame(
        {
            "PriceForReturn": np.arange(100.0, 121.0),
            "HighPriceForRange": np.arange(101.0, 122.0),
            "LowPriceForRange": np.arange(99.0, 120.0),
        }
    )
    prev_close = frame["PriceForReturn"].shift(1)
    true_range = pd.concat(
        [
            frame["HighPriceForRange"] - frame["LowPriceForRange"],
            (frame["HighPriceForRange"] - prev_close).abs(),
            (frame["LowPriceForRange"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    expected = true_range.tail(20).mean() / frame["PriceForReturn"].iloc[-1]

    actual = builder.compute_atr_pct(frame, period=20)

    assert actual == pytest.approx(expected)


def test_compute_beta_to_benchmark_matches_manual_formula() -> None:
    asset = pd.DataFrame(
        {
            "Date": pd.date_range("2023-01-01", periods=4),
            "ReturnFromPrice": [0.02, 0.01, 0.03, 0.04],
        }
    )
    benchmark = pd.DataFrame(
        {
            "Date": pd.date_range("2023-01-01", periods=4),
            "BenchmarkReturn": [0.01, 0.02, 0.02, 0.03],
        }
    )
    asset_values = asset["ReturnFromPrice"].to_numpy()
    benchmark_values = benchmark["BenchmarkReturn"].to_numpy()
    expected = np.mean((asset_values - asset_values.mean()) * (benchmark_values - benchmark_values.mean())) / np.mean(
        np.square(benchmark_values - benchmark_values.mean())
    )

    actual = builder.compute_beta_to_benchmark(asset, benchmark)

    assert actual == pytest.approx(expected)


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


def test_prepare_asset_series_converts_yield_quotes_before_returns_and_ranges(tmp_path: Path) -> None:
    raw_dir = tmp_path / "rawData"
    raw_dir.mkdir()
    csv_path = raw_dir / "MoneyMarket.csv"
    csv_path.write_text(
        '"Date","Price","Open","High","Low","Change %"\n'
        '"01/10/2023","10.0","11.0","12.0","9.0","0.00%"\n'
        '"01/09/2023","20.0","21.0","22.0","19.0","0.00%"\n',
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
    observed = aligned.loc[
        aligned["IsObserved"] == 1,
        ["Date", "QuotedValue", "PriceForReturn", "OpenPriceForRange", "HighPriceForRange", "LowPriceForRange", "ReturnFromPrice"],
    ]
    observed = observed.set_index("Date").sort_index()

    close_prices = builder.convert_yield_to_price_proxy(pd.Series([20.0, 10.0]), config.MONEY_MARKET_MATURITY_DAYS)
    open_prices = builder.convert_yield_to_price_proxy(pd.Series([21.0, 11.0]), config.MONEY_MARKET_MATURITY_DAYS)
    high_prices = builder.convert_yield_to_price_proxy(pd.Series([22.0, 12.0]), config.MONEY_MARKET_MATURITY_DAYS)
    low_prices = builder.convert_yield_to_price_proxy(pd.Series([19.0, 9.0]), config.MONEY_MARKET_MATURITY_DAYS)
    expected_return = (close_prices.iloc[1] / close_prices.iloc[0]) - 1.0

    assert observed.iloc[0]["PriceForReturn"] == pytest.approx(close_prices.iloc[0])
    assert observed.iloc[1]["PriceForReturn"] == pytest.approx(close_prices.iloc[1])
    assert observed.iloc[1]["OpenPriceForRange"] == pytest.approx(open_prices.iloc[1])
    assert observed.iloc[1]["HighPriceForRange"] == pytest.approx(
        max(close_prices.iloc[1], open_prices.iloc[1], high_prices.iloc[1], low_prices.iloc[1])
    )
    assert observed.iloc[1]["LowPriceForRange"] == pytest.approx(
        min(close_prices.iloc[1], open_prices.iloc[1], high_prices.iloc[1], low_prices.iloc[1])
    )
    assert observed.iloc[1]["ReturnFromPrice"] == pytest.approx(expected_return)


def test_compute_monthly_panel_builds_expected_schema_and_replaces_target_egarch() -> None:
    macro_features = {
        pd.Period("2010-10", freq="M"): {
            "usd_vol": 0.25,
            "cpi_trajectory": 0.05,
        }
    }

    daily_assets = {
        "EGX30": make_asset_frame("EGX30 Index", "EquityIndex", 100.0, 0.18, 0.9, 500.0),
        "A": make_asset_frame("Asset A", "Equity", 80.0, 0.05, 0.4, 100.0),
        "B": make_asset_frame("Asset B", "Equity", 95.0, 0.12, 0.7, 200.0),
        "C": make_asset_frame("Asset C", "Equity", 120.0, -0.02, 1.1, 300.0),
    }
    egarch_stats = make_egarch_month_stats("EGX30", "A", "B", "C")

    panel = builder.compute_monthly_panel(daily_assets, macro_features, egarch_stats)
    panel = panel.sort_values("AssetID").reset_index(drop=True)

    assert list(panel["Date"].unique()) == ["2010-10"]
    assert "realized_egarch_vol" not in panel.columns
    for column in config.MODEL_FEATURE_COLUMNS:
        assert column in panel.columns
        assert panel[column].between(0.0, 1.0).all()
    for column in config.TARGET_COLUMNS:
        assert column in panel.columns
    assert panel["realized_vol"].between(0.0, 1.0).all()
    assert panel["usd_vol"].nunique() == 1
    assert panel["cpi_trajectory"].nunique() == 1


def test_compute_monthly_panel_neutralizes_dropped_feature_without_changing_schema() -> None:
    macro_features = {
        pd.Period("2010-10", freq="M"): {
            "usd_vol": 0.25,
            "cpi_trajectory": 0.05,
        }
    }
    daily_assets = {
        "EGX30": make_asset_frame("EGX30 Index", "EquityIndex", 100.0, 0.18, 0.9, 500.0),
        "A": make_asset_frame("Asset A", "Equity", 80.0, 0.05, 0.4, 100.0),
        "B": make_asset_frame("Asset B", "Equity", 95.0, 0.12, 0.7, 200.0),
        "C": make_asset_frame("Asset C", "Equity", 120.0, -0.02, 1.1, 300.0),
    }
    egarch_stats = make_egarch_month_stats("EGX30", "A", "B", "C")

    panel = builder.compute_monthly_panel(
        daily_assets,
        macro_features,
        feature_profile=get_feature_profile("drop_rsi_14"),
        egarch_month_stats_by_asset=egarch_stats,
    )

    assert list(panel.columns) == config.PANEL_METADATA_COLUMNS + config.MODEL_FEATURE_COLUMNS + config.TARGET_COLUMNS
    assert panel["rsi_14"].nunique() == 1
    assert panel["rsi_14"].iloc[0] == pytest.approx(0.5)
    assert panel["atr_pct_20"].nunique() > 1


def test_compute_monthly_panel_preserves_schema_for_promoted_distance_removal_baseline() -> None:
    macro_features = {
        pd.Period("2010-10", freq="M"): {
            "usd_vol": 0.25,
            "cpi_trajectory": 0.05,
        }
    }
    daily_assets = {
        "EGX30": make_asset_frame("EGX30 Index", "EquityIndex", 100.0, 0.18, 0.9, 500.0),
        "A": make_asset_frame("Asset A", "Equity", 80.0, 0.05, 0.4, 100.0),
        "B": make_asset_frame("Asset B", "Equity", 95.0, 0.12, 0.7, 200.0),
        "C": make_asset_frame("Asset C", "Equity", 120.0, -0.02, 1.1, 300.0),
    }
    egarch_stats = make_egarch_month_stats("EGX30", "A", "B", "C")

    panel = builder.compute_monthly_panel(
        daily_assets,
        macro_features,
        feature_profile=get_feature_profile("full_current_v2_no_distance_to_3m_high"),
        egarch_month_stats_by_asset=egarch_stats,
    )

    assert list(panel.columns) == config.PANEL_METADATA_COLUMNS + config.MODEL_FEATURE_COLUMNS + config.TARGET_COLUMNS
    assert panel["distance_to_3m_high"].nunique() == 1
    assert panel["distance_to_3m_high"].iloc[0] == pytest.approx(0.5)
    assert panel["rsi_14"].nunique() > 1


def test_monthly_only_rows_profile_uses_current_month_not_prior_month_returns() -> None:
    macro_features = {
        pd.Period("2010-10", freq="M"): {"usd_vol": 0.25, "cpi_trajectory": 0.05},
        pd.Period("2010-11", freq="M"): {"usd_vol": 0.30, "cpi_trajectory": 0.06},
        pd.Period("2010-12", freq="M"): {"usd_vol": 0.35, "cpi_trajectory": 0.07},
    }
    original_assets = {
        "EGX30": make_asset_frame("EGX30 Index", "EquityIndex", 100.0, 0.18, 0.9, 500.0),
        "A": make_asset_frame("Asset A", "Equity", 80.0, 0.05, 0.4, 100.0),
        "B": make_asset_frame("Asset B", "Equity", 95.0, 0.12, 0.7, 200.0),
        "C": make_asset_frame("Asset C", "Equity", 120.0, -0.02, 1.1, 300.0),
    }
    prior_modified = {asset_id: frame.copy() for asset_id, frame in original_assets.items()}
    september_mask = prior_modified["A"]["Month"] == pd.Period("2010-09", freq="M")
    prior_modified["A"].loc[september_mask, "ReturnFromPrice"] = 0.35
    prior_modified["A"].loc[september_mask, "PriceForReturn"] *= 3.0
    prior_modified["A"].loc[september_mask, "HighPriceForRange"] *= 3.0
    prior_modified["A"].loc[september_mask, "LowPriceForRange"] *= 3.0

    current_modified = {asset_id: frame.copy() for asset_id, frame in original_assets.items()}
    october_mask = current_modified["A"]["Month"] == pd.Period("2010-10", freq="M")
    current_modified["A"].loc[october_mask, "ReturnFromPrice"] = -0.20
    current_modified["A"].loc[october_mask, "PriceForReturn"] *= 2.0
    current_modified["A"].loc[october_mask, "HighPriceForRange"] *= 2.0
    current_modified["A"].loc[october_mask, "LowPriceForRange"] *= 2.0

    profile = get_feature_profile("monthly_only_rows_v1")
    egarch_stats = make_egarch_month_stats("EGX30", "A", "B", "C")
    original_panel = builder.compute_monthly_panel(
        original_assets,
        macro_features,
        feature_profile=profile,
        egarch_month_stats_by_asset=egarch_stats,
    )
    prior_modified_panel = builder.compute_monthly_panel(
        prior_modified,
        macro_features,
        feature_profile=profile,
        egarch_month_stats_by_asset=egarch_stats,
    )
    current_modified_panel = builder.compute_monthly_panel(
        current_modified,
        macro_features,
        feature_profile=profile,
        egarch_month_stats_by_asset=egarch_stats,
    )

    columns_to_compare = config.MODEL_FEATURE_COLUMNS + config.TARGET_COLUMNS
    original_oct = original_panel.loc[original_panel["Date"] == "2010-10", ["AssetID"] + columns_to_compare]
    prior_modified_oct = prior_modified_panel.loc[prior_modified_panel["Date"] == "2010-10", ["AssetID"] + columns_to_compare]
    current_modified_oct = current_modified_panel.loc[current_modified_panel["Date"] == "2010-10", ["AssetID"] + columns_to_compare]

    assert_frame_equal(
        original_oct.sort_values("AssetID").reset_index(drop=True),
        prior_modified_oct.sort_values("AssetID").reset_index(drop=True),
    )
    assert not original_oct.sort_values("AssetID").reset_index(drop=True).equals(
        current_modified_oct.sort_values("AssetID").reset_index(drop=True)
    )


def test_monthly_only_rows_profile_matches_month_only_raw_downside_and_drawdown_ranks() -> None:
    macro_features = {
        pd.Period("2010-10", freq="M"): {"usd_vol": 0.25, "cpi_trajectory": 0.05},
    }
    daily_assets = {
        "EGX30": make_asset_frame("EGX30 Index", "EquityIndex", 100.0, 0.18, 0.9, 500.0),
        "A": make_asset_frame("Asset A", "Equity", 80.0, 0.05, 0.4, 100.0),
        "B": make_asset_frame("Asset B", "Equity", 95.0, 0.12, 0.7, 200.0),
        "C": make_asset_frame("Asset C", "Equity", 120.0, -0.02, 1.1, 300.0),
    }
    profile = get_feature_profile("monthly_only_rows_v1")
    egarch_stats = make_egarch_month_stats("EGX30", "A", "B", "C")

    panel = builder.compute_monthly_panel(
        daily_assets,
        macro_features,
        feature_profile=profile,
        egarch_month_stats_by_asset=egarch_stats,
    )
    month_panel = panel.loc[panel["Date"] == "2010-10"].sort_values("AssetID").reset_index(drop=True)
    raw = []
    for asset_id in month_panel["AssetID"]:
        month_returns = daily_assets[asset_id].loc[
            daily_assets[asset_id]["Month"] == pd.Period("2010-10", freq="M"),
            "ReturnFromPrice",
        ]
        raw.append(
            {
                "AssetID": asset_id,
                "downside_raw": builder.compute_downside_deviation(month_returns),
                "drawdown_raw": builder.compute_max_drawdown(month_returns),
            }
        )
    raw_frame = pd.DataFrame(raw).sort_values("AssetID").reset_index(drop=True)

    expected_downside = builder.rank_to_unit_interval(raw_frame["downside_raw"]).to_numpy()
    expected_drawdown = builder.rank_to_unit_interval(raw_frame["drawdown_raw"]).to_numpy()
    assert month_panel["downside_dev"].to_numpy() == pytest.approx(expected_downside)
    assert month_panel["max_drawdown"].to_numpy() == pytest.approx(expected_drawdown)


def test_monthly_only_rows_profile_keeps_short_month_rows_for_sma_atr_rsi() -> None:
    dates = pd.to_datetime(["2010-10-03", "2010-10-04", "2010-10-05", "2010-10-06"])

    def short_asset(asset_name: str, asset_group: str, closes: list[float], volume_base: float) -> pd.DataFrame:
        close = pd.Series(closes, dtype=float)
        returns = close.pct_change()
        return pd.DataFrame(
            {
                "Date": dates,
                "Month": dates.to_period("M"),
                "QuotedValue": close,
                "OpenQuotedValue": close,
                "HighQuotedValue": close + 1.0,
                "LowQuotedValue": close - 1.0,
                "PriceForReturn": close,
                "OpenPriceForRange": close,
                "HighPriceForRange": close + 1.0,
                "LowPriceForRange": close - 1.0,
                "Volume": volume_base,
                "ChangePctRaw": returns,
                "ReturnFromPrice": returns,
                "IsObserved": 1,
                "AssetName": asset_name,
                "AssetGroup": asset_group,
            }
        )

    macro_features = {pd.Period("2010-10", freq="M"): {"usd_vol": 0.25, "cpi_trajectory": 0.05}}
    daily_assets = {
        "EGX30": short_asset("EGX30 Index", "EquityIndex", [100.0, 101.0, 99.0, 102.0], 500.0),
        "A": short_asset("Asset A", "Equity", [80.0, 81.0, 80.5, 82.0], 100.0),
        "B": short_asset("Asset B", "Equity", [95.0, 94.0, 96.0, 97.0], 200.0),
        "C": short_asset("Asset C", "Equity", [120.0, 119.0, 121.0, 118.0], 300.0),
    }
    panel = builder.compute_monthly_panel(
        daily_assets,
        macro_features,
        feature_profile=get_feature_profile("monthly_only_rows_v1"),
        egarch_month_stats_by_asset=make_egarch_month_stats("EGX30", "A", "B", "C"),
    )

    assert set(panel["AssetID"]) == {"EGX30", "A", "B", "C"}
    assert panel["price_to_sma20"].notna().all()
    assert panel["atr_pct_20"].notna().all()
    assert panel["rsi_14"].notna().all()


def test_feature_variants_support_lookback_formula_and_macro_change_families() -> None:
    observed = make_asset_frame("Asset A", "Equity", 80.0, 0.05, 0.4, 100.0)
    observed_closes = observed["PriceForReturn"]
    base_profile = get_feature_profile(config.DEFAULT_FEATURE_PROFILE_ID)
    atr_profile = get_feature_profile("atr_pct_14")
    ema_profile = get_feature_profile("price_to_ema20")

    atr_frame = pd.DataFrame(
        {
            "PriceForReturn": np.linspace(100.0, 130.0, 30),
            "HighPriceForRange": np.linspace(101.0, 131.0, 30) + (2.0 * np.sin(np.arange(30))),
            "LowPriceForRange": np.linspace(99.0, 129.0, 30) - (2.5 * np.cos(np.arange(30))),
        }
    )
    base_atr = builder.compute_atr_pct(atr_frame, base_profile.atr_period)
    atr_14 = builder.compute_atr_pct(atr_frame, atr_profile.atr_period)
    base_price_to_ma = builder.compute_price_to_sma(observed_closes, base_profile.ma_period)
    ema_price_to_ma = builder.compute_price_to_ema(observed_closes, ema_profile.ma_period)

    cpi = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2010-08-01", "2010-09-01", "2010-10-01"]),
            "HeadlineMoM": [0.01, 0.02, 0.03],
            "Month": pd.period_range("2010-08", "2010-10", freq="M"),
        }
    )
    usd_daily = pd.concat(
        [
            frame.assign(AssetID=asset_id)
            for asset_id, frame in {"USD": make_asset_frame("USD/EGP", "Macro", 5.0, 0.01, 0.03, 0.0)}.items()
        ],
        ignore_index=True,
    )
    macro_base = builder.compute_macro_features(usd_daily, cpi, feature_profile=get_feature_profile(config.DEFAULT_FEATURE_PROFILE_ID))
    macro_cpi_last = builder.compute_macro_features(usd_daily, cpi, feature_profile=get_feature_profile("cpi_last_mom"))

    assert base_atr != pytest.approx(atr_14)
    assert base_price_to_ma != pytest.approx(ema_price_to_ma)
    assert macro_base[pd.Period("2010-10", freq="M")]["cpi_trajectory"] == pytest.approx((1.01 * 1.02 * 1.03) - 1.0)
    assert macro_cpi_last[pd.Period("2010-10", freq="M")]["cpi_trajectory"] == pytest.approx(0.03)


def test_compute_monthly_panel_does_not_leak_future_asset_or_benchmark_data() -> None:
    macro_features = {
        pd.Period("2010-10", freq="M"): {
            "usd_vol": 0.25,
            "cpi_trajectory": 0.05,
        },
        pd.Period("2010-11", freq="M"): {
            "usd_vol": 0.30,
            "cpi_trajectory": 0.06,
        },
    }

    original_assets = {
        "EGX30": make_asset_frame("EGX30 Index", "EquityIndex", 100.0, 0.18, 0.9, 500.0),
        "A": make_asset_frame("Asset A", "Equity", 80.0, 0.05, 0.4, 100.0),
        "B": make_asset_frame("Asset B", "Equity", 95.0, 0.12, 0.7, 200.0),
        "C": make_asset_frame("Asset C", "Equity", 120.0, -0.02, 1.1, 300.0),
    }
    modified_assets = {asset_id: frame.copy() for asset_id, frame in original_assets.items()}
    november_mask_a = modified_assets["A"]["Month"] == pd.Period("2010-11", freq="M")
    modified_assets["A"].loc[november_mask_a, "PriceForReturn"] *= 4.0
    modified_assets["A"].loc[november_mask_a, "HighPriceForRange"] *= 4.5
    modified_assets["A"].loc[november_mask_a, "LowPriceForRange"] *= 3.5
    modified_assets["A"].loc[november_mask_a, "ReturnFromPrice"] = 0.40

    november_mask_benchmark = modified_assets["EGX30"]["Month"] == pd.Period("2010-11", freq="M")
    modified_assets["EGX30"].loc[november_mask_benchmark, "ReturnFromPrice"] = -0.25

    egarch_stats = make_egarch_month_stats("EGX30", "A", "B", "C")
    original_panel = builder.compute_monthly_panel(original_assets, macro_features, egarch_stats)
    modified_panel = builder.compute_monthly_panel(modified_assets, macro_features, egarch_stats)

    columns_to_compare = config.MODEL_FEATURE_COLUMNS + config.TARGET_COLUMNS
    original_oct = original_panel.loc[original_panel["Date"] == "2010-10", ["AssetID"] + columns_to_compare]
    modified_oct = modified_panel.loc[modified_panel["Date"] == "2010-10", ["AssetID"] + columns_to_compare]
    original_oct = original_oct.sort_values("AssetID").reset_index(drop=True)
    modified_oct = modified_oct.sort_values("AssetID").reset_index(drop=True)

    assert_frame_equal(original_oct, modified_oct)


def test_compute_monthly_panel_does_not_leak_future_macro_data() -> None:
    base_macro = {
        pd.Period("2010-10", freq="M"): {
            "usd_vol": 0.25,
            "cpi_trajectory": 0.05,
        },
        pd.Period("2010-11", freq="M"): {
            "usd_vol": 0.30,
            "cpi_trajectory": 0.06,
        },
    }
    modified_macro = {
        month: values.copy()
        for month, values in base_macro.items()
    }
    modified_macro[pd.Period("2010-11", freq="M")] = {
        "usd_vol": 0.95,
        "cpi_trajectory": 0.90,
    }

    daily_assets = {
        "EGX30": make_asset_frame("EGX30 Index", "EquityIndex", 100.0, 0.18, 0.9, 500.0),
        "A": make_asset_frame("Asset A", "Equity", 80.0, 0.05, 0.4, 100.0),
        "B": make_asset_frame("Asset B", "Equity", 95.0, 0.12, 0.7, 200.0),
        "C": make_asset_frame("Asset C", "Equity", 120.0, -0.02, 1.1, 300.0),
    }
    egarch_stats = make_egarch_month_stats("EGX30", "A", "B", "C")

    original_panel = builder.compute_monthly_panel(daily_assets, base_macro, egarch_stats)
    modified_panel = builder.compute_monthly_panel(daily_assets, modified_macro, egarch_stats)

    original_oct = original_panel.loc[original_panel["Date"] == "2010-10"].sort_values("AssetID").reset_index(drop=True)
    modified_oct = modified_panel.loc[modified_panel["Date"] == "2010-10"].sort_values("AssetID").reset_index(drop=True)

    assert_frame_equal(original_oct, modified_oct)


def ensure_current_outputs() -> None:
    daily_path = ROOT / config.READY_DATA_DIR / config.DAILY_MARKET_SERIES_NAME
    panel_path = ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME
    if not daily_path.exists() or not panel_path.exists():
        builder.main([])
        return

    daily_columns = list(pd.read_csv(daily_path, nrows=0).columns)
    panel_columns = list(pd.read_csv(panel_path, nrows=0).columns)
    expected_panel_columns = config.PANEL_METADATA_COLUMNS + config.MODEL_FEATURE_COLUMNS + config.TARGET_COLUMNS
    panel_preview = pd.read_csv(panel_path, usecols=["Date"], nrows=5)
    panel_start = str(panel_preview["Date"].min()) if not panel_preview.empty else ""
    if (
        daily_columns != config.DAILY_MARKET_COLUMNS
        or panel_columns != expected_panel_columns
        or panel_start != config.PANEL_STATE_START
    ):
        builder.main([])


def test_non_base_feature_profile_defaults_to_profile_specific_output_dir() -> None:
    output_dir = builder.resolve_output_dir("drop_rsi_14")

    assert output_dir == ROOT / config.FEATURE_PROFILE_OUTPUT_DIR / "drop_rsi_14"
    assert "outputs/generated/datasets/feature_profiles" in output_dir.as_posix()


@pytest.fixture(scope="session")
def built_outputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_current_outputs()
    daily_path = ROOT / config.READY_DATA_DIR / config.DAILY_MARKET_SERIES_NAME
    panel_path = ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME
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
    assert "realized_egarch_vol" not in stored.columns

    for column in ["usd_vol", "cpi_trajectory"]:
        assert np.allclose(stored[column], recomputed[column], atol=1e-12, rtol=1e-12)

    month_sizes = stored.groupby("Date")["AssetID"].transform("count").to_numpy()
    max_rank_step = 1.0 / (month_sizes - 1)

    normalized_columns = [
        "egarch_vol",
        "downside_dev",
        "max_drawdown",
        "volume",
        "atr_pct_20",
        "beta_to_egx30",
        "price_to_sma20",
        "rsi_14",
        "distance_to_3m_high",
        "realized_vol",
        "realized_downside_dev",
        "realized_max_drawdown",
        "realized_risk",
    ]
    for column in normalized_columns:
        diffs = np.abs(stored[column].to_numpy() - recomputed[column].to_numpy())
        assert np.all(
            diffs <= (max_rank_step + 1e-12)
        ), f"{column} drift exceeded one monthly rank step after CSV roundtrip"

    rank_diffs = np.abs(stored["realized_rank"].to_numpy() - recomputed["realized_rank"].to_numpy())
    assert np.all(rank_diffs <= 2.0)


def test_current_outputs_support_framework_comparison_from_common_start(built_outputs: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    _, panel = built_outputs

    from src.training.panel_utils import build_framework_batches

    one_month_batches = build_framework_batches(panel, framework_id="pit_1m_shared_mlp", split_name="train")
    three_month_batches = build_framework_batches(panel, framework_id="pit_3m_flat_shared_mlp", split_name="train")

    assert one_month_batches[0].date == config.TRAIN_START
    assert three_month_batches[0].date == config.TRAIN_START
    assert one_month_batches[0].state_months == ("2010-12",)
    assert three_month_batches[0].state_months == ("2010-10", "2010-11", "2010-12")
