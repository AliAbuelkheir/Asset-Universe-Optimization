"""Validate the canonical or feature-profile daily and monthly datasets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_output_dir(
    input_dir: str | Path | None = None,
    expect_feature_profile_id: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    resolved_dir = Path(input_dir) if input_dir is not None else ROOT / config.READY_DATA_DIR
    daily_path = resolved_dir / config.DAILY_MARKET_SERIES_NAME
    panel_path = resolved_dir / config.MONTHLY_PANEL_NAME

    assert_true(daily_path.exists(), f"Missing daily market series: {daily_path}")
    assert_true(panel_path.exists(), f"Missing monthly panel: {panel_path}")

    if expect_feature_profile_id is not None:
        metadata_path = resolved_dir / "feature_profile_metadata.json"
        assert_true(metadata_path.exists(), f"Missing feature profile metadata: {metadata_path}")
        with metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)
        actual_profile_id = str(metadata.get("feature_profile_id", ""))
        assert_true(
            actual_profile_id == expect_feature_profile_id,
            "Feature profile metadata does not match the expected profile id. "
            f"Expected {expect_feature_profile_id} but found {actual_profile_id or '<missing>'}.",
        )

    daily = pd.read_csv(daily_path)
    panel = pd.read_csv(panel_path)

    assert_true(
        list(daily.columns) == config.DAILY_MARKET_COLUMNS,
        "Daily market series columns do not match the canonical contract.",
    )
    assert_true(
        list(panel.columns)
        == config.PANEL_METADATA_COLUMNS + config.MODEL_FEATURE_COLUMNS + config.TARGET_COLUMNS,
        "Monthly panel columns do not match the canonical contract.",
    )
    assert_true(
        not daily.duplicated(subset=["Date", "AssetID"]).any(),
        "Daily market series contains duplicate (Date, AssetID) rows.",
    )
    assert_true(
        not panel.duplicated(subset=["Date", "AssetID"]).any(),
        "Monthly panel contains duplicate (Date, AssetID) rows.",
    )
    assert_true(
        panel["Date"].min() == config.PANEL_STATE_START,
        f"Monthly panel should start at {config.PANEL_STATE_START}.",
    )
    assert_true(
        panel["Date"].max() <= config.TEST_END,
        f"Monthly panel should not extend past {config.TEST_END}.",
    )
    assert_true(
        panel[config.MODEL_FEATURE_COLUMNS].notna().all().all(),
        "Monthly panel contains missing model features.",
    )
    assert_true(
        panel[config.TARGET_COLUMNS].notna().all().all(),
        "Monthly panel contains missing target fields.",
    )

    numeric_daily_columns = [
        "QuotedValue",
        "OpenQuotedValue",
        "HighQuotedValue",
        "LowQuotedValue",
        "PriceForReturn",
        "OpenPriceForRange",
        "HighPriceForRange",
        "LowPriceForRange",
        "Volume",
        "ChangePctRaw",
        "ReturnFromPrice",
        "IsObserved",
    ]
    for column in numeric_daily_columns:
        assert_true(
            pd.api.types.is_numeric_dtype(daily[column]),
            f"{column} should be numeric in the daily market series.",
        )

    numeric_panel_columns = config.MODEL_FEATURE_COLUMNS + config.TARGET_COLUMNS
    for column in numeric_panel_columns:
        assert_true(
            pd.api.types.is_numeric_dtype(panel[column]),
            f"{column} should be numeric in the monthly panel.",
        )

    monthly_counts = panel.groupby("Date")["AssetID"].nunique()
    assert_true(
        (monthly_counts >= config.MIN_ASSETS_PER_MONTH).all(),
        "A month with fewer than the minimum asset count made it into the final panel.",
    )

    normalized_feature_columns = [
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
    for column in normalized_feature_columns:
        assert_true(
            panel[column].between(0.0, 1.0).all(),
            f"{column} must stay inside [0, 1].",
        )

    observed = daily.loc[daily["IsObserved"] == 1].copy()
    synthetic = daily.loc[daily["IsObserved"] == 0].copy()
    synthetic_ohlc_columns = [
        "OpenQuotedValue",
        "HighQuotedValue",
        "LowQuotedValue",
        "OpenPriceForRange",
        "HighPriceForRange",
        "LowPriceForRange",
    ]
    for column in synthetic_ohlc_columns:
        assert_true(
            synthetic[column].isna().all(),
            f"{column} should stay NaN on synthetic forward-filled rows.",
        )

    observed_range = observed.dropna(subset=["PriceForReturn", "HighPriceForRange", "LowPriceForRange"]).copy()
    assert_true(
        (observed_range["HighPriceForRange"] >= observed_range["PriceForReturn"]).all(),
        "Observed rows have HighPriceForRange below PriceForReturn.",
    )
    assert_true(
        (observed_range["LowPriceForRange"] <= observed_range["PriceForReturn"]).all(),
        "Observed rows have LowPriceForRange above PriceForReturn.",
    )
    open_available = observed_range["OpenPriceForRange"].notna()
    assert_true(
        (
            observed_range.loc[open_available, "HighPriceForRange"]
            >= observed_range.loc[open_available, "OpenPriceForRange"]
        ).all(),
        "Observed rows have HighPriceForRange below OpenPriceForRange.",
    )
    assert_true(
        (
            observed_range.loc[open_available, "LowPriceForRange"]
            <= observed_range.loc[open_available, "OpenPriceForRange"]
        ).all(),
        "Observed rows have LowPriceForRange above OpenPriceForRange.",
    )

    print("Daily rows:", f"{len(daily):,}")
    print("Monthly panel rows:", f"{len(panel):,}")
    print("Panel month range:", panel["Date"].min(), "to", panel["Date"].max())
    print("Minimum monthly asset count:", int(monthly_counts.min()))
    print("Maximum monthly asset count:", int(monthly_counts.max()))
    return daily, panel


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a canonical or feature-profile dataset directory.")
    parser.add_argument(
        "--input-dir",
        default=str(ROOT / config.READY_DATA_DIR),
        help="Directory that contains daily_market_series.csv and monthly_asset_panel.csv.",
    )
    parser.add_argument(
        "--expect-feature-profile-id",
        default=None,
        help="Optional feature_profile_id that must match feature_profile_metadata.json in the input directory.",
    )
    return parser


def main(argv: list[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    parser = _build_cli_parser()
    args = parser.parse_args(argv)
    return validate_output_dir(
        input_dir=args.input_dir,
        expect_feature_profile_id=args.expect_feature_profile_id,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
