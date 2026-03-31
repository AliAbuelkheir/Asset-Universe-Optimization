"""Validate the canonical daily market series and monthly asset panel."""

from __future__ import annotations

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


def main() -> None:
    ready_dir = ROOT / config.READY_DATA_DIR
    daily_path = ready_dir / config.DAILY_MARKET_SERIES_NAME
    panel_path = ready_dir / config.MONTHLY_PANEL_NAME

    assert_true(daily_path.exists(), f"Missing daily market series: {daily_path}")
    assert_true(panel_path.exists(), f"Missing monthly panel: {panel_path}")

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
        panel["Date"].min() == config.TRAIN_START,
        f"Monthly panel should start at {config.TRAIN_START}.",
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
        pd.api.types.is_numeric_dtype(panel["volume"]),
        "volume should be numeric in the monthly panel.",
    )
    assert_true(
        panel["realized_risk"].between(0.0, 1.0).all(),
        "realized_risk must stay inside [0, 1].",
    )

    monthly_counts = panel.groupby("Date")["AssetID"].nunique()
    assert_true(
        (monthly_counts >= config.MIN_ASSETS_PER_MONTH).all(),
        "A month with fewer than the minimum asset count made it into the final panel.",
    )
    assert_true(
        pd.api.types.is_numeric_dtype(daily["Volume"]),
        "Volume should be numeric in the daily market series.",
    )
    assert_true(
        pd.api.types.is_numeric_dtype(daily["ChangePctRaw"]),
        "ChangePctRaw should be numeric in the daily market series.",
    )
    assert_true(
        pd.api.types.is_numeric_dtype(daily["ReturnFromPrice"]),
        "ReturnFromPrice should be numeric in the daily market series.",
    )

    print("Daily rows:", f"{len(daily):,}")
    print("Monthly panel rows:", f"{len(panel):,}")
    print("Panel month range:", panel["Date"].min(), "to", panel["Date"].max())
    print("Minimum monthly asset count:", int(monthly_counts.min()))
    print("Maximum monthly asset count:", int(monthly_counts.max()))


if __name__ == "__main__":
    main()
