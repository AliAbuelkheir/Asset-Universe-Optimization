"""Shared experiment-result path and summary helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_ROOT = ROOT / "outputs" / "generated" / "runs" / "experiments"
SUMMARY_FILE_NAME = "setup_results.csv"


def resolve_output_root(output_root: str | Path | None = None) -> Path:
    return Path(output_root) if output_root is not None else EXPERIMENT_ROOT


def resolve_summary_path(
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
) -> Path:
    if summary_path is not None:
        return Path(summary_path)
    return resolve_output_root(output_root) / SUMMARY_FILE_NAME


def string_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series("", index=frame.index, dtype="object")
    return frame[column].fillna("").astype(str)


def load_setup_results(
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
) -> pd.DataFrame:
    resolved_summary_path = resolve_summary_path(output_root=output_root, summary_path=summary_path)
    if not resolved_summary_path.exists():
        return pd.DataFrame()

    results = pd.read_csv(resolved_summary_path)
    if results.empty:
        return results

    ordered = results.copy()
    ordered["__row_order__"] = range(len(ordered))
    sort_columns = ["__row_order__"]
    if "TimestampUTC" in ordered.columns:
        ordered["TimestampUTC"] = ordered["TimestampUTC"].astype(str)
        sort_columns = ["TimestampUTC", "__row_order__"]
    ordered = ordered.sort_values(sort_columns, kind="stable")
    ordered = ordered.drop_duplicates(subset=["SetupID"], keep="last")
    return ordered.drop(columns="__row_order__").reset_index(drop=True)


def result_row_for_setup(results: pd.DataFrame, setup_id: str) -> pd.Series | None:
    if results.empty or "SetupID" not in results.columns:
        return None
    matches = results.loc[string_series(results, "SetupID").eq(setup_id)]
    if matches.empty:
        return None
    return matches.iloc[-1]


def metric_value(row: pd.Series | None, column: str) -> float | None:
    if row is None or column not in row.index:
        return None
    value = pd.to_numeric(pd.Series([row[column]]), errors="coerce").iloc[0]
    if pd.isna(value):
        return None
    return float(value)
