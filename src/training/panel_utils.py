"""Shared helpers for framework-phase monthly state loading and batch assembly."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src import config
from src.training.experiment_profiles import get_comparison_protocol, get_objective_profile, protocol_split_windows
from src.training.frameworks import FrameworkSpec, get_framework_spec


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SplitWindow:
    name: str
    start: str
    end: str


@dataclass(frozen=True)
class DecisionBatch:
    date: str
    split: str
    framework_id: str
    state_months: tuple[str, ...]
    asset_ids: tuple[str, ...]
    asset_names: tuple[str, ...]
    asset_groups: tuple[str, ...]
    features: np.ndarray
    daily_strip: np.ndarray | None
    daily_mask: np.ndarray | None
    targets: np.ndarray

    @property
    def active_asset_count(self) -> int:
        return len(self.asset_ids)


def get_default_panel_path() -> Path:
    return ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME


def get_default_daily_path() -> Path:
    return ROOT / config.READY_DATA_DIR / config.DAILY_MARKET_SERIES_NAME


def expected_panel_columns(feature_columns: list[str] | tuple[str, ...] | None = None) -> list[str]:
    resolved_features = list(config.MODEL_FEATURE_COLUMNS if feature_columns is None else feature_columns)
    return config.PANEL_METADATA_COLUMNS + resolved_features + config.TARGET_COLUMNS


def expected_daily_columns() -> list[str]:
    return config.DAILY_MARKET_COLUMNS


def load_monthly_panel(
    panel_path: str | Path | None = None,
    feature_columns: list[str] | tuple[str, ...] | None = None,
    allow_extra_columns: bool = False,
) -> pd.DataFrame:
    resolved_path = Path(panel_path) if panel_path is not None else get_default_panel_path()
    panel = pd.read_csv(resolved_path)
    expected = expected_panel_columns(feature_columns=feature_columns)
    actual_columns = list(panel.columns)
    if allow_extra_columns:
        missing = [column for column in expected if column not in actual_columns]
        if missing:
            raise ValueError(
                "Monthly panel columns do not match the requested contract. "
                f"Missing required columns: {missing}. Found {actual_columns}."
            )
    elif actual_columns != expected:
        raise ValueError(
            "Monthly panel columns do not match the canonical contract. "
            f"Expected {expected} but found {actual_columns}."
        )
    return panel.sort_values(["Date", "AssetID"]).reset_index(drop=True)


def load_canonical_monthly_panel(panel_path: str | Path | None = None) -> pd.DataFrame:
    return load_monthly_panel(panel_path=panel_path, feature_columns=config.MODEL_FEATURE_COLUMNS, allow_extra_columns=False)


def load_canonical_daily_market_series(daily_path: str | Path | None = None) -> pd.DataFrame:
    resolved_path = Path(daily_path) if daily_path is not None else get_default_daily_path()
    daily = pd.read_csv(resolved_path)
    expected = expected_daily_columns()
    if list(daily.columns) != expected:
        raise ValueError(
            "Daily market columns do not match the canonical contract. "
            f"Expected {expected} but found {list(daily.columns)}."
        )
    return daily.sort_values(["Date", "AssetID"]).reset_index(drop=True)


def decision_split_name_for_month(
    month_label: str,
    comparison_protocol_id: str = config.DEFAULT_COMPARISON_PROTOCOL_ID,
) -> str:
    for window in protocol_split_windows(comparison_protocol_id):
        if window.start <= month_label <= window.end:
            return window.name
    raise ValueError(f"Decision month {month_label} does not belong to any configured split.")


def split_name_for_month(
    month_label: str,
    comparison_protocol_id: str = config.DEFAULT_COMPARISON_PROTOCOL_ID,
) -> str:
    return decision_split_name_for_month(month_label, comparison_protocol_id=comparison_protocol_id)


def decision_months_for_split(
    split_name: str,
    comparison_protocol_id: str = config.DEFAULT_COMPARISON_PROTOCOL_ID,
) -> tuple[str, ...]:
    for window in protocol_split_windows(comparison_protocol_id):
        if window.name == split_name:
            periods = pd.period_range(start=window.start, end=window.end, freq="M")
            return tuple(period.strftime(config.DATE_FORMAT_MONTHLY) for period in periods)
    raise ValueError(f"Unknown split requested: {split_name}")


def stacked_feature_column_names(
    framework: FrameworkSpec,
    feature_columns: list[str] | tuple[str, ...] | None = None,
) -> list[str]:
    resolved_feature_columns = list(config.MODEL_FEATURE_COLUMNS if feature_columns is None else feature_columns)
    columns: list[str] = []
    for lag in range(framework.lookback_months, 0, -1):
        columns.extend(f"{feature}__lag{lag}" for feature in resolved_feature_columns)
    return columns


def state_months_for_decision(decision_month: str, lookback_months: int) -> tuple[str, ...]:
    decision_period = pd.Period(decision_month, freq="M")
    return tuple(
        (decision_period - lag).strftime(config.DATE_FORMAT_MONTHLY)
        for lag in range(lookback_months, 0, -1)
    )


def build_daily_strip_lookup(
    daily_market_series: pd.DataFrame,
    strip_length: int,
) -> dict[tuple[str, str], tuple[np.ndarray, np.ndarray]]:
    observed = daily_market_series.copy()
    observed["IsObserved"] = pd.to_numeric(observed["IsObserved"], errors="coerce").fillna(0).astype(int)
    observed = observed.loc[observed["IsObserved"] == 1].copy()
    observed["Date"] = pd.to_datetime(observed["Date"])
    observed["Month"] = observed["Date"].dt.to_period("M").astype(str)

    lookup: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] = {}
    for (asset_id, month_label), group in observed.groupby(["AssetID", "Month"], sort=False):
        ordered = group.sort_values("Date").reset_index(drop=True)
        if len(ordered) > strip_length:
            raise ValueError(
                f"Observed daily rows for {(asset_id, month_label)} exceed configured strip length {strip_length}."
            )

        close = pd.to_numeric(ordered["PriceForReturn"], errors="coerce")
        first_close = float(close.iloc[0]) if not close.empty else float("nan")
        if pd.isna(first_close) or first_close <= 0:
            continue

        close_rel = (close / first_close) - 1.0
        daily_return = pd.to_numeric(ordered["ReturnFromPrice"], errors="coerce").fillna(0.0)
        volume = pd.to_numeric(ordered["Volume"], errors="coerce")
        log_volume = np.log1p(volume.fillna(0.0))
        volume_observed = volume.notna().astype(float)

        values = np.column_stack(
            [
                close_rel.to_numpy(dtype=np.float32),
                daily_return.to_numpy(dtype=np.float32),
                log_volume.to_numpy(dtype=np.float32),
                volume_observed.to_numpy(dtype=np.float32),
            ]
        )
        day_count = values.shape[0]
        strip = np.zeros((strip_length, config.DAILY_STRIP_CHANNELS), dtype=np.float32)
        mask = np.zeros((strip_length,), dtype=np.float32)
        strip[:day_count, :] = values
        mask[:day_count] = 1.0
        lookup[(str(asset_id), month_label)] = (strip, mask)
    return lookup


def build_framework_batches(
    panel: pd.DataFrame,
    framework_id: str,
    split_name: str,
    daily_market_series: pd.DataFrame | None = None,
    comparison_protocol_id: str = config.DEFAULT_COMPARISON_PROTOCOL_ID,
    feature_columns: list[str] | tuple[str, ...] | None = None,
    objective_profile_id: str = config.DEFAULT_OBJECTIVE_PROFILE_ID,
) -> list[DecisionBatch]:
    framework = get_framework_spec(framework_id)
    resolved_feature_columns = list(config.MODEL_FEATURE_COLUMNS if feature_columns is None else feature_columns)
    objective_profile = get_objective_profile(objective_profile_id)
    batches: list[DecisionBatch] = []
    daily_lookup: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] | None = None
    if framework.uses_daily_strip:
        daily_source = daily_market_series if daily_market_series is not None else load_canonical_daily_market_series()
        daily_lookup = build_daily_strip_lookup(daily_source, strip_length=framework.daily_strip_length)

    for decision_month in decision_months_for_split(split_name, comparison_protocol_id=comparison_protocol_id):
        decision_frame = panel.loc[
            panel["Date"] == decision_month,
            config.PANEL_METADATA_COLUMNS + config.TARGET_COLUMNS,
        ].copy()
        if decision_frame.empty:
            continue

        merged = decision_frame
        state_months = state_months_for_decision(decision_month, framework.lookback_months)
        for offset, state_month in enumerate(state_months):
            lag = framework.lookback_months - offset
            state_frame = panel.loc[
                panel["Date"] == state_month,
                ["AssetID"] + resolved_feature_columns,
            ].copy()
            if state_frame.empty:
                merged = merged.iloc[0:0].copy()
                break

            renamed = state_frame.rename(
                columns={
                    feature: f"{feature}__lag{lag}"
                    for feature in resolved_feature_columns
                }
            )
            merged = merged.merge(renamed, on="AssetID", how="inner")
            if merged.empty:
                break

        if len(merged) < config.MIN_ASSETS_PER_MONTH:
            continue

        merged = merged.sort_values("AssetID").reset_index(drop=True)
        daily_strip_array: np.ndarray | None = None
        daily_mask_array: np.ndarray | None = None
        if framework.uses_daily_strip:
            assert daily_lookup is not None
            state_month = state_months[-1]
            kept_rows: list[int] = []
            strips: list[np.ndarray] = []
            masks: list[np.ndarray] = []
            for row_index, asset_id in enumerate(merged["AssetID"].astype(str)):
                strip_and_mask = daily_lookup.get((asset_id, state_month))
                if strip_and_mask is None:
                    continue
                strip, day_mask = strip_and_mask
                kept_rows.append(row_index)
                strips.append(strip)
                masks.append(day_mask)

            if len(kept_rows) < config.MIN_ASSETS_PER_MONTH:
                continue
            merged = merged.iloc[kept_rows].reset_index(drop=True)
            daily_strip_array = np.stack(strips).astype(np.float32)
            daily_mask_array = np.stack(masks).astype(np.float32)

        stacked_columns = stacked_feature_column_names(framework, feature_columns=resolved_feature_columns)
        realized_risk = objective_profile.compute_realized_risk(merged)
        batches.append(
            DecisionBatch(
                date=decision_month,
                split=split_name,
                framework_id=framework.framework_id,
                state_months=state_months,
                asset_ids=tuple(merged["AssetID"].astype(str)),
                asset_names=tuple(merged["AssetName"].astype(str)),
                asset_groups=tuple(merged["AssetGroup"].astype(str)),
                features=merged[stacked_columns].to_numpy(dtype=np.float32),
                daily_strip=daily_strip_array,
                daily_mask=daily_mask_array,
                targets=realized_risk.to_numpy(dtype=np.float32),
            )
        )

    if not batches:
        raise ValueError(f"No decision batches were found for split {split_name} and framework {framework_id}.")
    return batches
