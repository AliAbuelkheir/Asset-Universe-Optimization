"""Shared monthly-panel helpers for the RL training and evaluation path."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src import config


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SplitWindow:
    name: str
    start: str
    end: str


@dataclass(frozen=True)
class MonthlyBatch:
    date: str
    split: str
    asset_ids: tuple[str, ...]
    asset_names: tuple[str, ...]
    asset_groups: tuple[str, ...]
    features: np.ndarray
    targets: np.ndarray

    @property
    def active_asset_count(self) -> int:
        return len(self.asset_ids)


SPLIT_WINDOWS = (
    SplitWindow("train", config.TRAIN_START, config.TRAIN_END),
    SplitWindow("validation", config.VAL_START, config.VAL_END),
    SplitWindow("test", config.TEST_START, config.TEST_END),
)


def get_default_panel_path() -> Path:
    return ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME


def expected_panel_columns() -> list[str]:
    return config.PANEL_METADATA_COLUMNS + config.MODEL_FEATURE_COLUMNS + config.TARGET_COLUMNS


def load_canonical_monthly_panel(panel_path: str | Path | None = None) -> pd.DataFrame:
    resolved_path = Path(panel_path) if panel_path is not None else get_default_panel_path()
    panel = pd.read_csv(resolved_path)
    expected = expected_panel_columns()
    if list(panel.columns) != expected:
        raise ValueError(
            "Monthly panel columns do not match the canonical contract. "
            f"Expected {expected} but found {list(panel.columns)}."
        )
    return panel.sort_values(["Date", "AssetID"]).reset_index(drop=True)


def split_name_for_month(month_label: str) -> str:
    for window in SPLIT_WINDOWS:
        if window.start <= month_label <= window.end:
            return window.name
    raise ValueError(f"Month {month_label} does not belong to any configured split.")


def split_panel_by_date(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    split_frames: dict[str, pd.DataFrame] = {}
    for window in SPLIT_WINDOWS:
        mask = (panel["Date"] >= window.start) & (panel["Date"] <= window.end)
        split_frames[window.name] = panel.loc[mask].copy().reset_index(drop=True)
    return split_frames


def build_monthly_batches(panel: pd.DataFrame, split_name: str | None = None) -> list[MonthlyBatch]:
    working_panel = panel
    if split_name is not None:
        if split_name not in {window.name for window in SPLIT_WINDOWS}:
            raise ValueError(f"Unknown split requested: {split_name}")
        working_panel = split_panel_by_date(panel)[split_name]

    batches: list[MonthlyBatch] = []
    for date, month_frame in working_panel.groupby("Date", sort=True):
        frame = month_frame.sort_values("AssetID").reset_index(drop=True)
        batches.append(
            MonthlyBatch(
                date=str(date),
                split=split_name_for_month(str(date)),
                asset_ids=tuple(frame["AssetID"].astype(str)),
                asset_names=tuple(frame["AssetName"].astype(str)),
                asset_groups=tuple(frame["AssetGroup"].astype(str)),
                features=frame[config.MODEL_FEATURE_COLUMNS].to_numpy(dtype=np.float32),
                targets=frame["realized_risk"].to_numpy(dtype=np.float32),
            )
        )

    if split_name is not None and not batches:
        raise ValueError(f"No monthly batches were found for split {split_name}.")
    return batches
