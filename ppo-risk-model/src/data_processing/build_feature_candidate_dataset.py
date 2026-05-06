"""Build shadow feature-candidate outputs without changing the canonical panel."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config
from src.data_processing import build_model_dataset as builder
from src.feature_candidates import (
    APPROVED_RATIO_AND_TAIL_SHORTLIST,
    SHADOW_FEATURE_CANDIDATES,
    ShadowFeatureCandidate,
    get_shadow_candidate,
)


RATIO_CANDIDATE_IDS = {"sortino_3m", "sortino_1m", "calmar_3m", "calmar_1m"}
RATIO_CLIP_BOUNDS = (-10.0, 10.0)
RATIO_EPSILON = 1e-6


def resolve_output_dir(candidate_set_id: str, output_dir: str | Path | None = None) -> Path:
    if output_dir is not None:
        return Path(output_dir)
    return ROOT / config.FEATURE_CANDIDATE_OUTPUT_DIR / candidate_set_id


def _candidate_outputs_ready(candidate: ShadowFeatureCandidate, resolved_output_dir: Path) -> bool:
    daily_output = resolved_output_dir / config.DAILY_MARKET_SERIES_NAME
    panel_output = resolved_output_dir / config.MONTHLY_PANEL_NAME
    metadata_output = resolved_output_dir / "feature_candidate_metadata.json"
    if not daily_output.exists() or not panel_output.exists() or not metadata_output.exists():
        return False
    try:
        metadata = json.loads(metadata_output.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return str(metadata.get("candidate_id", "")) == candidate.candidate_id


def _compute_distance_to_low(last_close: float, low_prices: pd.Series) -> float:
    clean_lows = low_prices.replace([np.inf, -np.inf], np.nan).dropna()
    if clean_lows.empty or pd.isna(last_close):
        return float("nan")
    window_low = float(clean_lows.min())
    if window_low <= 0:
        return float("nan")
    return float((last_close / window_low) - 1.0)


def _compute_range_position(last_close: float, high_prices: pd.Series, low_prices: pd.Series) -> float:
    highs = high_prices.replace([np.inf, -np.inf], np.nan).dropna()
    lows = low_prices.replace([np.inf, -np.inf], np.nan).dropna()
    if highs.empty or lows.empty or pd.isna(last_close):
        return float("nan")
    window_high = float(highs.max())
    window_low = float(lows.min())
    if window_high <= window_low:
        return float("nan")
    return float((last_close - window_low) / (window_high - window_low))


def _compute_drawdown_recovery(returns: pd.Series) -> float:
    clean = returns.replace([np.inf, -np.inf], np.nan).dropna().astype(float)
    if clean.empty:
        return float("nan")
    growth = (1.0 + clean.clip(lower=-0.999999)).cumprod()
    peak = growth.cummax()
    drawdown = (growth / peak) - 1.0
    trough_index = int(drawdown.argmin())
    trough_growth = float(growth.iloc[trough_index])
    prior_peak = float(peak.iloc[trough_index])
    final_growth = float(growth.iloc[-1])
    drawdown_depth = max(prior_peak - trough_growth, 1e-12)
    return float((final_growth - trough_growth) / drawdown_depth)


def _compute_realized_skew(returns: pd.Series) -> float:
    clean = returns.replace([np.inf, -np.inf], np.nan).dropna().astype(float)
    if len(clean) < 3:
        return float("nan")
    return float(clean.skew())


def _compute_realized_kurtosis(returns: pd.Series) -> float:
    clean = returns.replace([np.inf, -np.inf], np.nan).dropna().astype(float)
    if len(clean) < 4:
        return float("nan")
    return float(clean.kurt())


def _compute_illiquidity_1m(observed_frame: pd.DataFrame) -> float:
    clean = observed_frame[["ReturnFromPrice", "Volume"]].replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return 0.0
    denom = clean["Volume"].clip(lower=1.0)
    return float((clean["ReturnFromPrice"].abs() / denom).mean())


def _compute_volume_spike_1m_vs_3m(frame: pd.DataFrame, month: pd.Period) -> float:
    trailing_months = builder.trailing_months(month, config.WINDOW_MONTHS)
    observed = frame.loc[frame["IsObserved"] == 1].copy()
    observed = observed.loc[observed["Month"].isin(trailing_months)]
    if observed.empty:
        return 0.0
    monthly_volume = observed.groupby("Month")["Volume"].sum(min_count=1)
    if monthly_volume.empty or monthly_volume.isna().all():
        return 0.0
    recent = float(monthly_volume.get(month, np.nan))
    trailing_mean = float(monthly_volume.mean())
    if np.isnan(recent) or trailing_mean <= 0:
        return 0.0
    return float((recent / trailing_mean) - 1.0)


def _compute_usd_return_1m(usd_daily: pd.DataFrame, month: pd.Period) -> float:
    returns = usd_daily.loc[usd_daily["Month"] == month, "ReturnFromPrice"].dropna()
    return builder.compute_compounded_return(returns) if not returns.empty else float("nan")


def _compute_cpi_acceleration_3m(cpi_monthly: pd.DataFrame, month: pd.Period) -> float:
    lookup = cpi_monthly.set_index("Month")["HeadlineMoM"]
    window = lookup.reindex(builder.trailing_months(month, config.WINDOW_MONTHS))
    if window.isna().any():
        return float("nan")
    return float(window.iloc[-1] - window.iloc[:2].mean())


def _clean_return_series(returns: pd.Series) -> pd.Series:
    return returns.replace([np.inf, -np.inf], np.nan).dropna().astype(float)


def _sanitize_ratio_candidate_value(value: float) -> float:
    if not np.isfinite(value):
        return float("nan")
    lower, upper = RATIO_CLIP_BOUNDS
    return float(np.clip(value, lower, upper))


def _compute_sortino_ratio(returns: pd.Series) -> float:
    clean = _clean_return_series(returns)
    if clean.empty:
        return float("nan")
    compounded_return = builder.compute_compounded_return(clean)
    downside_deviation = builder.compute_downside_deviation(clean)
    if pd.isna(compounded_return) or pd.isna(downside_deviation):
        return float("nan")
    return float(compounded_return / max(float(downside_deviation), RATIO_EPSILON))


def _compute_calmar_ratio(returns: pd.Series) -> float:
    clean = _clean_return_series(returns)
    if clean.empty:
        return float("nan")
    compounded_return = builder.compute_compounded_return(clean)
    max_drawdown = builder.compute_max_drawdown(clean)
    if pd.isna(compounded_return) or pd.isna(max_drawdown):
        return float("nan")
    return float(compounded_return / max(float(max_drawdown), RATIO_EPSILON))


def _compute_expected_shortfall_95(returns: pd.Series) -> float:
    clean = _clean_return_series(returns)
    if clean.empty:
        return float("nan")
    tail_count = max(1, int(np.ceil(len(clean) * 0.05)))
    tail_slice = clean.nsmallest(tail_count)
    return float(tail_slice.mean())


def _compute_drawdown_duration(returns: pd.Series) -> float:
    clean = _clean_return_series(returns)
    if clean.empty:
        return float("nan")
    growth = (1.0 + clean.clip(lower=-0.999999)).cumprod()
    below_peak = growth < growth.cummax()
    longest_run = 0
    current_run = 0
    for is_below_peak in below_peak.tolist():
        if is_below_peak:
            current_run += 1
            longest_run = max(longest_run, current_run)
        else:
            current_run = 0
    return float(longest_run)


def _compute_worst_return(returns: pd.Series) -> float:
    clean = _clean_return_series(returns)
    if clean.empty:
        return float("nan")
    return float(clean.min())


def _compute_max_abs_return(returns: pd.Series) -> float:
    clean = _clean_return_series(returns)
    if clean.empty:
        return float("nan")
    return float(clean.abs().max())


def _compute_vol_of_vol_3m(frame: pd.DataFrame, months: tuple[pd.Period, ...]) -> float:
    monthly_vols: list[float] = []
    for month in months:
        returns = _clean_return_series(frame.loc[frame["Month"] == month, "ReturnFromPrice"])
        if len(returns) < 2:
            continue
        monthly_vols.append(float(returns.std(ddof=0)))
    if len(monthly_vols) < 2:
        return float("nan")
    return float(np.std(monthly_vols, ddof=0))


def _compute_downside_tail_ratio(returns: pd.Series) -> float:
    clean = _clean_return_series(returns)
    if clean.empty:
        return float("nan")
    downside = clean.loc[clean < 0.0].abs()
    denominator = float(clean.abs().sum())
    if denominator <= 0.0:
        return 0.0
    if downside.empty:
        return 0.0
    tail_count = max(1, int(np.ceil(len(downside) * 0.25)))
    return float(downside.nlargest(tail_count).sum() / denominator)


def apply_rl_screen_shortlist_override(
    audit: pd.DataFrame,
    shortlist=APPROVED_RATIO_AND_TAIL_SHORTLIST,
) -> pd.DataFrame:
    overridden = audit.copy()
    overridden["EligibleForRLScreen"] = False
    overridden["RLScreenOrder"] = pd.Series([pd.NA] * len(overridden), dtype="Int64")
    overridden["RLScreenReason"] = "below_cut"
    for entry in shortlist:
        match_index = overridden.index[overridden["CandidateID"].astype(str) == entry.candidate_id]
        if match_index.empty:
            continue
        overridden.loc[match_index, "EligibleForRLScreen"] = True
        overridden.loc[match_index, "RLScreenOrder"] = pd.Series(
            [entry.execution_priority] * len(match_index),
            index=match_index,
            dtype="Int64",
        )
        overridden.loc[match_index, "RLScreenReason"] = "approved_shortlist"
    return overridden


def build_additive_candidate_panel(
    candidate: ShadowFeatureCandidate,
    output_dir: str | Path | None = None,
) -> tuple[Path, Path]:
    if candidate.candidate_type != "additive":
        raise ValueError(f"Candidate {candidate.candidate_id} is not additive.")

    raw_dir = ROOT / config.RAW_DATA_DIR
    stock_specs = builder.build_stock_specs(raw_dir)
    scoring_specs = builder.SCORING_ASSETS + stock_specs
    daily_frames: dict[str, pd.DataFrame] = {}
    export_frames: list[pd.DataFrame] = []
    qa_rows: list[dict[str, float | int | str]] = []

    for spec in scoring_specs:
        prepared, qa = builder.prepare_asset_series(raw_dir, spec)
        daily_frames[spec.asset_id] = prepared
        export_frames.append(prepared)
        qa_rows.append(qa)

    usd_daily, usd_qa = builder.prepare_usd_series(raw_dir)
    export_frames.append(usd_daily)
    qa_rows.append(usd_qa)
    cpi_monthly = builder.load_cpi_series(raw_dir)

    canonical_panel = pd.read_csv(ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME)
    candidate_rows: list[dict[str, object]] = []
    canonical_months = {pd.Period(date, freq="M") for date in canonical_panel["Date"].unique()}

    for asset_id, frame in daily_frames.items():
        observed_months = set(frame.loc[frame["IsObserved"] == 1, "Month"].unique())
        for month in sorted(canonical_months):
            required_feature_months = builder.trailing_months(month, config.WINDOW_MONTHS)
            if not all(required_month in observed_months for required_month in required_feature_months):
                continue
            month_label = month.strftime(config.DATE_FORMAT_MONTHLY)
            if canonical_panel.loc[
                (canonical_panel["Date"] == month_label) & (canonical_panel["AssetID"] == asset_id)
            ].empty:
                continue

            feature_window = frame.loc[frame["Month"].isin(required_feature_months)].copy()
            observed_feature_window = feature_window.loc[feature_window["IsObserved"] == 1].copy()
            observed_closes = observed_feature_window["PriceForReturn"].dropna()
            last_close = float(observed_closes.iloc[-1]) if not observed_closes.empty else float("nan")
            candidate_value = float("nan")
            if candidate.candidate_id == "distance_to_1m_low":
                one_month = observed_feature_window.loc[observed_feature_window["Month"] == month]
                candidate_value = _compute_distance_to_low(last_close, one_month["LowPriceForRange"])
            elif candidate.candidate_id == "range_position_3m":
                candidate_value = _compute_range_position(
                    last_close,
                    observed_feature_window["HighPriceForRange"],
                    observed_feature_window["LowPriceForRange"],
                )
            elif candidate.candidate_id == "drawdown_recovery_3m":
                candidate_value = _compute_drawdown_recovery(feature_window["ReturnFromPrice"])
            elif candidate.candidate_id == "realized_skew_3m":
                candidate_value = _compute_realized_skew(feature_window["ReturnFromPrice"])
            elif candidate.candidate_id == "realized_kurtosis_3m":
                candidate_value = _compute_realized_kurtosis(feature_window["ReturnFromPrice"])
            elif candidate.candidate_id == "illiquidity_1m":
                one_month = observed_feature_window.loc[observed_feature_window["Month"] == month]
                candidate_value = _compute_illiquidity_1m(one_month)
            elif candidate.candidate_id == "volume_spike_1m_vs_3m":
                candidate_value = _compute_volume_spike_1m_vs_3m(frame, month)
            elif candidate.candidate_id == "usd_return_1m":
                candidate_value = _compute_usd_return_1m(usd_daily, month)
            elif candidate.candidate_id == "cpi_acceleration_3m":
                candidate_value = _compute_cpi_acceleration_3m(cpi_monthly, month)
            elif candidate.candidate_id == "sortino_3m":
                candidate_value = _compute_sortino_ratio(feature_window["ReturnFromPrice"])
            elif candidate.candidate_id == "sortino_1m":
                one_month_returns = frame.loc[frame["Month"] == month, "ReturnFromPrice"]
                candidate_value = _compute_sortino_ratio(one_month_returns)
            elif candidate.candidate_id == "calmar_3m":
                candidate_value = _compute_calmar_ratio(feature_window["ReturnFromPrice"])
            elif candidate.candidate_id == "calmar_1m":
                one_month_returns = frame.loc[frame["Month"] == month, "ReturnFromPrice"]
                candidate_value = _compute_calmar_ratio(one_month_returns)
            elif candidate.candidate_id == "expected_shortfall_95_3m":
                candidate_value = _compute_expected_shortfall_95(feature_window["ReturnFromPrice"])
            elif candidate.candidate_id == "drawdown_duration_3m":
                candidate_value = _compute_drawdown_duration(observed_feature_window["ReturnFromPrice"])
            elif candidate.candidate_id == "worst_return_1m":
                one_month_returns = observed_feature_window.loc[observed_feature_window["Month"] == month, "ReturnFromPrice"]
                candidate_value = _compute_worst_return(one_month_returns)
            elif candidate.candidate_id == "max_abs_return_1m":
                one_month_returns = observed_feature_window.loc[observed_feature_window["Month"] == month, "ReturnFromPrice"]
                candidate_value = _compute_max_abs_return(one_month_returns)
            elif candidate.candidate_id == "vol_of_vol_3m":
                candidate_value = _compute_vol_of_vol_3m(observed_feature_window, required_feature_months)
            elif candidate.candidate_id == "downside_tail_ratio_3m":
                candidate_value = _compute_downside_tail_ratio(observed_feature_window["ReturnFromPrice"])
            elif candidate.candidate_id == "worst_return_3m":
                candidate_value = _compute_worst_return(observed_feature_window["ReturnFromPrice"])
            elif candidate.candidate_id == "max_abs_return_3m":
                candidate_value = _compute_max_abs_return(observed_feature_window["ReturnFromPrice"])
            else:
                raise ValueError(f"Unsupported additive candidate: {candidate.candidate_id}")

            if candidate.candidate_id in RATIO_CANDIDATE_IDS:
                candidate_value = _sanitize_ratio_candidate_value(candidate_value)

            candidate_rows.append(
                {
                    "Date": month_label,
                    "AssetID": asset_id,
                    candidate.candidate_id: candidate_value,
                }
            )

    candidate_frame = pd.DataFrame(candidate_rows)
    merged = canonical_panel.merge(candidate_frame, on=["Date", "AssetID"], how="left")
    if candidate.is_macro:
        if merged[candidate.candidate_id].isna().any():
            raise RuntimeError(f"Macro candidate {candidate.candidate_id} has missing values after merge.")
    else:
        normalized_values = []
        for _, month_frame in merged.groupby("Date", sort=True):
            ranked = builder.rank_to_unit_interval(month_frame[candidate.candidate_id])
            month_copy = month_frame.copy()
            # Keep shadow additive panels complete by falling back to a neutral
            # cross-sectional value when the raw candidate cannot be formed for
            # an asset-month.
            month_copy[candidate.candidate_id] = ranked.fillna(0.5)
            normalized_values.append(month_copy)
        merged = pd.concat(normalized_values, ignore_index=True)
        if merged[candidate.candidate_id].isna().any():
            raise RuntimeError(f"Asset-level candidate {candidate.candidate_id} has missing values after normalization.")

    ordered_columns = config.PANEL_METADATA_COLUMNS + config.MODEL_FEATURE_COLUMNS + [candidate.candidate_id] + config.TARGET_COLUMNS
    merged = merged[ordered_columns].sort_values(["Date", "AssetID"]).reset_index(drop=True)

    resolved_output_dir = resolve_output_dir(candidate.candidate_set_id, output_dir=output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    daily_market_series = builder.format_daily_market_series(export_frames)
    daily_output = resolved_output_dir / config.DAILY_MARKET_SERIES_NAME
    panel_output = resolved_output_dir / config.MONTHLY_PANEL_NAME
    metadata_output = resolved_output_dir / "feature_candidate_metadata.json"
    daily_market_series.to_csv(daily_output, index=False)
    merged.to_csv(panel_output, index=False)
    with metadata_output.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "candidate_id": candidate.candidate_id,
                "candidate_type": candidate.candidate_type,
                "candidate_set_id": candidate.candidate_set_id,
                "input_feature_set_id": candidate.input_feature_set_id,
                "feature_column": candidate.feature_column,
                "description": candidate.description,
                "is_macro": candidate.is_macro,
            },
            handle,
            indent=2,
            sort_keys=True,
        )
    builder.print_qa_summary(qa_rows)
    return daily_output, panel_output


def build_candidate_outputs(
    candidate_id: str,
    output_dir: str | Path | None = None,
) -> tuple[Path, Path]:
    candidate = get_shadow_candidate(candidate_id)
    resolved_output_dir = resolve_output_dir(candidate.candidate_set_id, output_dir=output_dir)
    if _candidate_outputs_ready(candidate, resolved_output_dir):
        return (
            resolved_output_dir / config.DAILY_MARKET_SERIES_NAME,
            resolved_output_dir / config.MONTHLY_PANEL_NAME,
        )

    if candidate.candidate_type == "replacement":
        daily_output, panel_output = builder.build_outputs(
            feature_profile_id=str(candidate.source_profile_id),
            output_dir=resolved_output_dir,
        )
        with (resolved_output_dir / "feature_candidate_metadata.json").open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "candidate_id": candidate.candidate_id,
                    "candidate_type": candidate.candidate_type,
                    "replacement_feature": candidate.replacement_feature,
                    "source_profile_id": candidate.source_profile_id,
                    "candidate_set_id": candidate.candidate_set_id,
                    "input_feature_set_id": candidate.input_feature_set_id,
                    "feature_column": candidate.feature_column,
                    "description": candidate.description,
                    "is_macro": candidate.is_macro,
                },
                handle,
                indent=2,
                sort_keys=True,
            )
        return daily_output, panel_output
    return build_additive_candidate_panel(candidate, output_dir=resolved_output_dir)


def standalone_candidate_audit(
    output_root: str | Path | None = None,
    candidates: tuple[ShadowFeatureCandidate, ...] = SHADOW_FEATURE_CANDIDATES,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for candidate in candidates:
        _, panel_path = build_candidate_outputs(candidate.candidate_id, output_dir=resolve_output_dir(candidate.candidate_set_id, output_dir=output_root))
        panel = pd.read_csv(panel_path)
        outer_validation = panel.loc[(panel["Date"] >= config.VAL_START) & (panel["Date"] <= config.VAL_END)].copy()
        monthly_spearman: list[float] = []
        for _, month_frame in outer_validation.groupby("Date", sort=True):
            statistic = spearmanr(
                month_frame[candidate.feature_column].to_numpy(dtype=float),
                month_frame["realized_risk"].to_numpy(dtype=float),
            ).statistic
            if np.isnan(statistic):
                statistic = 0.0
            monthly_spearman.append(float(statistic))

        rows.append(
            {
                "CandidateID": candidate.candidate_id,
                "CandidateType": candidate.candidate_type,
                "ReplacementFeature": candidate.replacement_feature or "",
                "CandidateSetID": candidate.candidate_set_id,
                "InputFeatureSetID": candidate.input_feature_set_id,
                "StandaloneMeanSpearman": float(np.mean(monthly_spearman)) if monthly_spearman else float("nan"),
                "OuterValidationMonths": int(len(monthly_spearman)),
                "FeatureColumn": candidate.feature_column,
            }
        )

    audit = pd.DataFrame(rows).sort_values(["StandaloneMeanSpearman", "CandidateID"], ascending=[False, True]).reset_index(drop=True)
    audit["AuditRank"] = range(1, len(audit) + 1)
    audit = apply_rl_screen_shortlist_override(audit)

    audit_root = Path(output_root) if output_root is not None else ROOT / config.FEATURE_CANDIDATE_OUTPUT_DIR
    audit_root.mkdir(parents=True, exist_ok=True)
    audit.to_csv(audit_root / "standalone_candidate_audit.csv", index=False)
    return audit


def top_positive_shadow_candidates(
    audit: pd.DataFrame,
    limit: int = 6,
) -> list[str]:
    if "EligibleForRLScreen" in audit.columns:
        eligible_mask = audit["EligibleForRLScreen"].fillna(False).astype(bool)
        ordered = audit.loc[eligible_mask].copy()
        if "RLScreenOrder" in ordered.columns:
            ordered = ordered.sort_values(["RLScreenOrder", "CandidateID"], ascending=[True, True], kind="stable")
        return ordered.head(limit)["CandidateID"].astype(str).tolist()

    positive = audit.loc[pd.to_numeric(audit["StandaloneMeanSpearman"], errors="coerce") > 0.0]
    return positive.head(limit)["CandidateID"].astype(str).tolist()


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build shadow candidate outputs and standalone audits.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build a single candidate output directory.")
    build_parser.add_argument("--candidate-id", required=True, help="Shadow candidate identifier.")
    build_parser.add_argument("--output-dir", default=None, help="Optional explicit output directory.")

    audit_parser = subparsers.add_parser("audit", help="Build all candidate outputs and write the standalone audit CSV.")
    audit_parser.add_argument("--output-root", default=None, help="Optional root for candidate outputs and audit CSV.")
    return parser


def main(argv: list[str] | None = None) -> pd.DataFrame | tuple[Path, Path]:
    parser = _build_cli_parser()
    args = parser.parse_args(argv)
    if args.command == "build":
        return build_candidate_outputs(candidate_id=args.candidate_id, output_dir=args.output_dir)
    audit = standalone_candidate_audit(output_root=args.output_root)
    print(audit.to_string(index=False))
    return audit


if __name__ == "__main__":
    main(sys.argv[1:])
