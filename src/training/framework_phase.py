"""Doc sync and comparison helpers for the framework-phase re-lock lane."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config
from src.training.experiment_profiles import blocked_bootstrap_mean_summary
from src.training.metrics import apply_objective_profile, evaluate_prediction_frame
from src.training.results_store import (
    EXPERIMENT_ROOT,
    load_setup_results,
    metric_value,
    resolve_output_root,
    resolve_summary_path,
    result_row_for_setup,
    string_series as _string_series,
)


FRAMEWORK_PHASE_DOC_PATH = ROOT / "docs" / "framework_phase.md"
RELOCK_SETUP_PREFIX = "FW-RELK-"
ANCHOR_OBJECTIVE_PROFILE_ID = config.DEFAULT_OBJECTIVE_PROFILE_ID
ANCHOR_REWARD_PROFILE_ID = config.DEFAULT_REWARD_PROFILE_ID
SENSITIVITY_STOP_CORRELATION = 0.998
PROTOCOL_BASELINE_NOTE = "protocol_baseline"
OBJECTIVE_AUDIT_NOTE = "objective_audit"
FRAMEWORK_RERUN_AFTER_OBJECTIVE_NOTE = "framework_rerun_after_objective"
REWARD_AUDIT_NOTE = "reward_audit"
TRAINING_METHOD_AUDIT_NOTE = "training_method_audit"
RELOCK_NOTES = {
    PROTOCOL_BASELINE_NOTE,
    OBJECTIVE_AUDIT_NOTE,
    FRAMEWORK_RERUN_AFTER_OBJECTIVE_NOTE,
    REWARD_AUDIT_NOTE,
    TRAINING_METHOD_AUDIT_NOTE,
}
OBJECTIVE_SECTION_NOTES = {
    PROTOCOL_BASELINE_NOTE,
    OBJECTIVE_AUDIT_NOTE,
    FRAMEWORK_RERUN_AFTER_OBJECTIVE_NOTE,
    REWARD_AUDIT_NOTE,
}
TRAINING_SECTION_NOTES = {
    PROTOCOL_BASELINE_NOTE,
    TRAINING_METHOD_AUDIT_NOTE,
}
DOC_COMPARISON_HEADERS = [
    "Date",
    "SetupID",
    "FrameworkID",
    "ObjectiveProfileID",
    "RewardProfileID",
    "TrainingMethodID",
    "Native Validation Reward",
    "Native Validation Spearman",
    "Anchor Validation Reward",
    "Anchor Validation Spearman",
    "Prediction Similarity To Baseline",
    "Decision",
]
def load_framework_phase_results(
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
) -> pd.DataFrame:
    results = load_setup_results(output_root=output_root, summary_path=summary_path)
    if results.empty:
        return results

    required_filters = (
        results["StudyPhase"].eq(config.FRAMEWORK_PHASE_NAME)
        & results["PolicySemanticsVersion"].eq(config.POLICY_SEMANTICS_VERSION)
        & _string_series(results, "ComparisonProtocolID").eq(config.DEFAULT_COMPARISON_PROTOCOL_ID)
        & (
            _string_series(results, "SetupID").str.startswith(RELOCK_SETUP_PREFIX)
            | _string_series(results, "Notes").isin(RELOCK_NOTES)
        )
    )
    return results.loc[required_filters].copy().reset_index(drop=True)


def _date_from_timestamp(timestamp: Any) -> str:
    if pd.isna(timestamp):
        return ""
    return str(timestamp).split("T", maxsplit=1)[0]


def _format_metric(value: Any) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return "" if pd.isna(numeric) else f"{float(numeric):.4f}"


def relock_setup_id(
    framework_id: str,
    objective_profile_id: str,
    reward_profile_id: str,
    training_method_id: str,
    seed: int,
) -> str:
    return (
        f"{RELOCK_SETUP_PREFIX}{framework_id.upper()}-"
        f"{objective_profile_id.upper()}-"
        f"{reward_profile_id.upper()}-"
        f"{training_method_id.upper()}-S{seed}"
    )
def _artifacts_dir(row: pd.Series | None) -> Path | None:
    if row is None or "ArtifactsDir" not in row.index:
        return None
    value = row.get("ArtifactsDir", "")
    if pd.isna(value):
        return None
    resolved = str(value).strip()
    return None if not resolved else Path(resolved)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}.")
    return payload


def comparison_payload_for_row(row: pd.Series | None) -> dict[str, Any] | None:
    artifacts_dir = _artifacts_dir(row)
    if artifacts_dir is None:
        return None
    comparison_path = artifacts_dir / "outer_validation_comparison.json"
    if not comparison_path.exists():
        return None
    return _load_json(comparison_path)


def _setup_metadata_for_row(row: pd.Series) -> dict[str, Any]:
    artifacts_dir = _artifacts_dir(row)
    if artifacts_dir is None:
        raise ValueError("Result row is missing ArtifactsDir, so setup metadata cannot be resolved.")
    metadata_path = artifacts_dir / "setup_metadata.json"
    if not metadata_path.exists():
        raise ValueError(f"Missing setup metadata: {metadata_path}")
    return _load_json(metadata_path)


def _predictions_for_row(row: pd.Series) -> pd.DataFrame:
    artifacts_dir = _artifacts_dir(row)
    if artifacts_dir is None:
        raise ValueError("Result row is missing ArtifactsDir, so predictions cannot be resolved.")
    predictions_path = artifacts_dir / "ranked_predictions.csv"
    if not predictions_path.exists():
        raise ValueError(f"Missing ranked predictions: {predictions_path}")
    return pd.read_csv(predictions_path)


def _anchor_target_frame(
    panel_path: str | Path,
    objective_profile_id: str = ANCHOR_OBJECTIVE_PROFILE_ID,
) -> pd.DataFrame:
    required_columns = ["Date", "AssetID", *config.TARGET_COMPONENT_COLUMNS]
    panel = pd.read_csv(panel_path, usecols=required_columns)
    adjusted = apply_objective_profile(panel, objective_profile=objective_profile_id)
    return adjusted[["Date", "AssetID", "realized_risk"]]


def rescore_predictions_against_anchor(
    predictions: pd.DataFrame,
    panel_path: str | Path,
    objective_profile_id: str = ANCHOR_OBJECTIVE_PROFILE_ID,
    reward_profile_id: str = ANCHOR_REWARD_PROFILE_ID,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    anchor_targets = _anchor_target_frame(panel_path=panel_path, objective_profile_id=objective_profile_id)
    rescored = predictions.drop(columns=["realized_risk", "realized_rank"], errors="ignore").merge(
        anchor_targets,
        on=["Date", "AssetID"],
        how="left",
        validate="many_to_one",
    )
    if rescored["realized_risk"].isna().any():
        missing = rescored.loc[rescored["realized_risk"].isna(), ["Date", "AssetID"]].drop_duplicates()
        raise ValueError(
            "Anchor rescoring could not resolve realized_risk for all prediction rows: "
            f"{missing.to_dict(orient='records')[:5]}"
        )
    monthly_metrics, split_summary = evaluate_prediction_frame(rescored, reward_profile=reward_profile_id)
    return rescored, monthly_metrics, split_summary


def _split_summary_value(split_summary: pd.DataFrame, split_name: str, column: str) -> float | None:
    if split_summary.empty or "split" not in split_summary.columns or column not in split_summary.columns:
        return None
    matches = split_summary.loc[split_summary["split"].astype(str).eq(str(split_name))]
    if matches.empty:
        return None
    value = pd.to_numeric(pd.Series([matches.iloc[-1][column]]), errors="coerce").iloc[0]
    return None if pd.isna(value) else float(value)


def anchor_rescored_metrics_for_setup(
    row: pd.Series,
    objective_profile_id: str = ANCHOR_OBJECTIVE_PROFILE_ID,
    reward_profile_id: str = ANCHOR_REWARD_PROFILE_ID,
) -> dict[str, Any]:
    metadata = _setup_metadata_for_row(row)
    panel_path = metadata.get("panel_path")
    if not panel_path:
        raise ValueError("Setup metadata is missing panel_path, so anchor rescoring cannot proceed.")
    predictions = _predictions_for_row(row)
    rescored_predictions, monthly_metrics, split_summary = rescore_predictions_against_anchor(
        predictions=predictions,
        panel_path=panel_path,
        objective_profile_id=objective_profile_id,
        reward_profile_id=reward_profile_id,
    )
    comparison_split = str(row.get("ComparisonSplit", "validation") or "validation")
    return {
        "comparison_split": comparison_split,
        "rescored_predictions": rescored_predictions,
        "monthly_metrics": monthly_metrics,
        "split_summary": split_summary,
        "validation_reward": _split_summary_value(split_summary, comparison_split, "mean_reward"),
        "validation_spearman": _split_summary_value(split_summary, comparison_split, "mean_spearman"),
        "test_reward": _split_summary_value(split_summary, "test", "mean_reward"),
        "test_spearman": _split_summary_value(split_summary, "test", "mean_spearman"),
    }


def prediction_similarity_summary(
    baseline_predictions: pd.DataFrame,
    candidate_predictions: pd.DataFrame,
    split_name: str = "validation",
) -> dict[str, Any]:
    baseline_subset = baseline_predictions.copy()
    candidate_subset = candidate_predictions.copy()
    if "Split" in baseline_subset.columns:
        baseline_subset = baseline_subset.loc[baseline_subset["Split"].astype(str).eq(split_name)]
    if "Split" in candidate_subset.columns:
        candidate_subset = candidate_subset.loc[candidate_subset["Split"].astype(str).eq(split_name)]
    baseline_subset = baseline_subset[["Date", "AssetID", "PredictedRisk"]].rename(
        columns={"PredictedRisk": "BaselinePredictedRisk"}
    )
    candidate_subset = candidate_subset[["Date", "AssetID", "PredictedRisk"]].rename(
        columns={"PredictedRisk": "CandidatePredictedRisk"}
    )
    merged = baseline_subset.merge(candidate_subset, on=["Date", "AssetID"], how="inner", validate="one_to_one")
    if merged.empty:
        return {
            "split": split_name,
            "paired_rows": 0,
            "paired_months": 0,
            "pearson_correlation": None,
            "spearman_correlation": None,
            "mean_absolute_difference": None,
        }

    pearson = merged["BaselinePredictedRisk"].corr(merged["CandidatePredictedRisk"], method="pearson")
    spearman = merged["BaselinePredictedRisk"].corr(merged["CandidatePredictedRisk"], method="spearman")
    mad = (merged["CandidatePredictedRisk"] - merged["BaselinePredictedRisk"]).abs().mean()
    return {
        "split": split_name,
        "paired_rows": int(len(merged)),
        "paired_months": int(merged["Date"].nunique()),
        "pearson_correlation": None if pd.isna(pearson) else float(pearson),
        "spearman_correlation": None if pd.isna(spearman) else float(spearman),
        "mean_absolute_difference": None if pd.isna(mad) else float(mad),
    }


def _decision_from_comparison_payload(
    baseline_anchor_reward: float | None,
    baseline_anchor_spearman: float | None,
    candidate_anchor_reward: float | None,
    candidate_anchor_spearman: float | None,
    similarity_summary: dict[str, Any],
) -> dict[str, Any]:
    promotable = (
        None not in (
            baseline_anchor_reward,
            baseline_anchor_spearman,
            candidate_anchor_reward,
            candidate_anchor_spearman,
        )
        and candidate_anchor_reward > baseline_anchor_reward
        and candidate_anchor_spearman > baseline_anchor_spearman
    )
    pearson = similarity_summary.get("pearson_correlation")
    spearman = similarity_summary.get("spearman_correlation")
    sensitivity_stop = (
        not promotable
        and pearson is not None
        and spearman is not None
        and float(pearson) > SENSITIVITY_STOP_CORRELATION
        and float(spearman) > SENSITIVITY_STOP_CORRELATION
    )
    if promotable:
        label = "promotable on anchor"
    elif sensitivity_stop:
        label = "stop: weak sensitivity"
    else:
        label = "screened"
    return {
        "promotable_on_anchor": bool(promotable),
        "sensitivity_stop": bool(sensitivity_stop),
        "label": label,
    }


def beats_on_outer_validation(results: pd.DataFrame, incumbent_setup_id: str, candidate_setup_id: str) -> bool:
    incumbent = result_row_for_setup(results, incumbent_setup_id)
    candidate = result_row_for_setup(results, candidate_setup_id)
    payload = comparison_payload_for_row(candidate)
    if payload is not None and str(payload.get("baseline_setup_id", "")) == incumbent_setup_id:
        baseline_metrics = payload.get("baseline_validation_metrics", {})
        candidate_metrics = payload.get("candidate_validation_metrics", {})
        baseline_reward = pd.to_numeric(pd.Series([baseline_metrics.get("anchor_reward")]), errors="coerce").iloc[0]
        baseline_spearman = pd.to_numeric(pd.Series([baseline_metrics.get("anchor_spearman")]), errors="coerce").iloc[0]
        candidate_reward = pd.to_numeric(pd.Series([candidate_metrics.get("anchor_reward")]), errors="coerce").iloc[0]
        candidate_spearman = pd.to_numeric(pd.Series([candidate_metrics.get("anchor_spearman")]), errors="coerce").iloc[0]
        if not any(pd.isna(value) for value in (baseline_reward, baseline_spearman, candidate_reward, candidate_spearman)):
            return bool(candidate_reward > baseline_reward and candidate_spearman > baseline_spearman)
    incumbent_reward = metric_value(incumbent, "ValidationMeanReward")
    incumbent_spearman = metric_value(incumbent, "ValidationMeanSpearman")
    candidate_reward = metric_value(candidate, "ValidationMeanReward")
    candidate_spearman = metric_value(candidate, "ValidationMeanSpearman")
    if None in (incumbent_reward, incumbent_spearman, candidate_reward, candidate_spearman):
        return False
    return candidate_reward > incumbent_reward and candidate_spearman > incumbent_spearman


def confirmed_on_all_seeds(
    results: pd.DataFrame,
    incumbent_by_seed: dict[int, str],
    candidate_by_seed: dict[int, str],
) -> bool:
    shared_seeds = sorted(set(incumbent_by_seed).intersection(candidate_by_seed))
    if not shared_seeds:
        return False
    return all(
        result_row_for_setup(results, incumbent_by_seed[seed]) is not None
        and result_row_for_setup(results, candidate_by_seed[seed]) is not None
        and beats_on_outer_validation(results, incumbent_by_seed[seed], candidate_by_seed[seed])
        for seed in shared_seeds
    )


def _format_similarity(similarity_summary: dict[str, Any] | None) -> str:
    if not similarity_summary:
        return ""
    pearson = pd.to_numeric(pd.Series([similarity_summary.get("pearson_correlation")]), errors="coerce").iloc[0]
    spearman = pd.to_numeric(pd.Series([similarity_summary.get("spearman_correlation")]), errors="coerce").iloc[0]
    mad = pd.to_numeric(pd.Series([similarity_summary.get("mean_absolute_difference")]), errors="coerce").iloc[0]
    if pd.isna(pearson) or pd.isna(spearman) or pd.isna(mad):
        return ""
    return f"P={float(pearson):.4f}; S={float(spearman):.4f}; MAD={float(mad):.4f}"


def _doc_comparison_row(row: pd.Series) -> dict[str, str]:
    payload = comparison_payload_for_row(row)
    native_reward = _format_metric(row.get("ValidationMeanReward", ""))
    native_spearman = _format_metric(row.get("ValidationMeanSpearman", ""))
    if payload is not None:
        candidate_metrics = payload.get("candidate_validation_metrics", {})
        anchor_reward = _format_metric(candidate_metrics.get("anchor_reward", ""))
        anchor_spearman = _format_metric(candidate_metrics.get("anchor_spearman", ""))
        similarity = _format_similarity(payload.get("prediction_similarity"))
        decision = str(payload.get("decision", {}).get("label", ""))
    else:
        anchor_reward = native_reward if str(row.get("ObjectiveProfileID", "")) == ANCHOR_OBJECTIVE_PROFILE_ID and str(row.get("RewardProfileID", "")) == ANCHOR_REWARD_PROFILE_ID else ""
        anchor_spearman = native_spearman if anchor_reward else ""
        similarity = "baseline" if str(row.get("Notes", "")) == PROTOCOL_BASELINE_NOTE else ""
        decision = "incumbent anchor" if str(row.get("Notes", "")) == PROTOCOL_BASELINE_NOTE else ""
    return {
        "Date": _date_from_timestamp(row.get("TimestampUTC", "")),
        "SetupID": "" if pd.isna(row.get("SetupID", "")) else str(row.get("SetupID", "")),
        "FrameworkID": "" if pd.isna(row.get("FrameworkID", "")) else str(row.get("FrameworkID", "")),
        "ObjectiveProfileID": "" if pd.isna(row.get("ObjectiveProfileID", "")) else str(row.get("ObjectiveProfileID", "")),
        "RewardProfileID": "" if pd.isna(row.get("RewardProfileID", "")) else str(row.get("RewardProfileID", "")),
        "TrainingMethodID": "" if pd.isna(row.get("TrainingMethodID", "")) else str(row.get("TrainingMethodID", "")),
        "Native Validation Reward": native_reward,
        "Native Validation Spearman": native_spearman,
        "Anchor Validation Reward": anchor_reward,
        "Anchor Validation Spearman": anchor_spearman,
        "Prediction Similarity To Baseline": similarity,
        "Decision": decision,
    }


def _comparison_rows_for_doc(results: pd.DataFrame) -> list[dict[str, str]]:
    if results.empty:
        return []
    ordered = results.sort_values(["TimestampUTC", "SetupID"], kind="stable") if "TimestampUTC" in results.columns else results
    return [_doc_comparison_row(row) for _, row in ordered.iterrows()]


def comparison_protocol_audit_rows(results: pd.DataFrame) -> list[dict[str, str]]:
    if results.empty:
        return []
    ordered = results.sort_values(["TimestampUTC", "SetupID"], kind="stable") if "TimestampUTC" in results.columns else results
    rows = _comparison_rows_for_doc(ordered)
    for rendered, (_, source_row) in zip(rows, ordered.iterrows(), strict=False):
        rendered["ComparisonProtocolID"] = "" if pd.isna(source_row.get("ComparisonProtocolID", "")) else str(source_row.get("ComparisonProtocolID", ""))
        rendered["CheckpointProvenance"] = "" if pd.isna(source_row.get("CheckpointProvenance", "")) else str(source_row.get("CheckpointProvenance", ""))
    return rows


def objective_audit_rows(results: pd.DataFrame) -> list[dict[str, str]]:
    filtered = results.loc[_string_series(results, "Notes").isin(OBJECTIVE_SECTION_NOTES)].copy()
    return _comparison_rows_for_doc(filtered)


def training_method_rows(results: pd.DataFrame) -> list[dict[str, str]]:
    filtered = results.loc[_string_series(results, "Notes").isin(TRAINING_SECTION_NOTES)].copy()
    return _comparison_rows_for_doc(filtered)


def _table_lines(headers: list[str], rows: list[dict[str, str]]) -> list[str]:
    lines = [
        f"| {' | '.join(headers)} |",
        f"| {' | '.join('---' for _ in headers)} |",
    ]
    if not rows:
        lines.append(f"| {' | '.join('' for _ in headers)} |")
        return lines
    for row in rows:
        values = [row.get(header, "") for header in headers]
        lines.append(f"| {' | '.join(values)} |")
    return lines


def _replace_or_append_section(existing_text: str, heading: str, section_lines: list[str]) -> str:
    start_marker = f"## {heading}"
    if start_marker not in existing_text:
        text = existing_text.rstrip() + "\n\n" + "\n".join(section_lines).rstrip() + "\n"
        return text

    start_index = existing_text.index(start_marker)
    next_heading_index = existing_text.find("\n## ", start_index + len(start_marker))
    end_index = len(existing_text) if next_heading_index == -1 else next_heading_index + 1
    replacement = "\n".join(section_lines).rstrip() + "\n"
    return existing_text[:start_index] + replacement + existing_text[end_index:]


def render_protocol_audit_section(results: pd.DataFrame) -> list[str]:
    rows = comparison_protocol_audit_rows(results)
    return [
        "## Comparison Protocol Audit",
        "",
        "These rows document runs executed under the repaired comparison protocol and report both native and anchor-rescored outer-validation metrics.",
        "",
        *(_table_lines(
            [
                "Date",
                "SetupID",
                "FrameworkID",
                "ComparisonProtocolID",
                "CheckpointProvenance",
                "ObjectiveProfileID",
                "RewardProfileID",
                "TrainingMethodID",
                "Native Validation Reward",
                "Native Validation Spearman",
                "Anchor Validation Reward",
                "Anchor Validation Spearman",
                "Prediction Similarity To Baseline",
                "Decision",
            ],
            rows,
        )),
    ]


def render_objective_audit_section(results: pd.DataFrame) -> list[str]:
    rows = objective_audit_rows(results)
    return [
        "## Objective Audit",
        "",
        "These rows track realized-risk target variants and reward-profile variants under native scoring and the fixed anchor rescoring rule.",
        "",
        *(_table_lines(DOC_COMPARISON_HEADERS, rows)),
    ]


def render_training_method_section(results: pd.DataFrame) -> list[str]:
    rows = training_method_rows(results)
    return [
        "## Training Method Screens",
        "",
        "These rows track train-sampling-method comparisons while keeping validation and test ordered and reporting anchor-rescored validation metrics.",
        "",
        *(_table_lines(DOC_COMPARISON_HEADERS, rows)),
    ]


def sync_framework_phase_doc(
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
    doc_path: str | Path | None = None,
) -> Path:
    results = load_framework_phase_results(output_root=output_root, summary_path=summary_path)
    resolved_doc_path = Path(doc_path) if doc_path is not None else FRAMEWORK_PHASE_DOC_PATH
    existing_text = resolved_doc_path.read_text(encoding="utf-8") if resolved_doc_path.exists() else "# Framework Phase\n"
    updated_text = existing_text
    updated_text = _replace_or_append_section(updated_text, "Comparison Protocol Audit", render_protocol_audit_section(results))
    updated_text = _replace_or_append_section(updated_text, "Objective Audit", render_objective_audit_section(results))
    updated_text = _replace_or_append_section(updated_text, "Training Method Screens", render_training_method_section(results))
    resolved_doc_path.write_text(updated_text, encoding="utf-8")
    return resolved_doc_path


def outer_validation_delta_summary(
    baseline_metrics: pd.DataFrame,
    candidate_metrics: pd.DataFrame,
    split_name: str = "validation",
) -> dict[str, Any]:
    baseline = baseline_metrics.loc[baseline_metrics["split"] == split_name, ["date", "reward", "spearman"]].rename(
        columns={"reward": "baseline_reward", "spearman": "baseline_spearman"}
    )
    candidate = candidate_metrics.loc[candidate_metrics["split"] == split_name, ["date", "reward", "spearman"]].rename(
        columns={"reward": "candidate_reward", "spearman": "candidate_spearman"}
    )
    merged = baseline.merge(candidate, on="date", how="inner").sort_values("date").reset_index(drop=True)
    merged["reward_delta"] = merged["candidate_reward"] - merged["baseline_reward"]
    merged["spearman_delta"] = merged["candidate_spearman"] - merged["baseline_spearman"]
    return {
        "paired_months": int(len(merged)),
        "rows": merged.to_dict(orient="records"),
        "reward_summary": blocked_bootstrap_mean_summary(merged["reward_delta"].tolist()),
        "spearman_summary": blocked_bootstrap_mean_summary(merged["spearman_delta"].tolist()),
    }


def _validation_metrics_payload(
    row: pd.Series,
    anchor_metrics: dict[str, Any],
) -> dict[str, float | None]:
    return {
        "native_reward": metric_value(row, "ValidationMeanReward"),
        "native_spearman": metric_value(row, "ValidationMeanSpearman"),
        "anchor_reward": anchor_metrics.get("validation_reward"),
        "anchor_spearman": anchor_metrics.get("validation_spearman"),
    }


def _test_metrics_payload(
    row: pd.Series,
    anchor_metrics: dict[str, Any],
) -> dict[str, float | None]:
    return {
        "native_reward": metric_value(row, "TestMeanReward"),
        "native_spearman": metric_value(row, "TestMeanSpearman"),
        "anchor_reward": anchor_metrics.get("test_reward"),
        "anchor_spearman": anchor_metrics.get("test_spearman"),
    }


def write_outer_validation_comparison(
    baseline_setup_id: str,
    candidate_setup_id: str,
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
) -> Path:
    results = load_framework_phase_results(output_root=output_root, summary_path=summary_path)
    baseline_row = results.loc[results["SetupID"] == baseline_setup_id]
    candidate_row = results.loc[results["SetupID"] == candidate_setup_id]
    if baseline_row.empty or candidate_row.empty:
        raise ValueError("Both baseline and candidate setups must exist before writing a comparison summary.")
    baseline_result = baseline_row.iloc[-1]
    candidate_result = candidate_row.iloc[-1]
    baseline_artifacts = Path(str(baseline_result["ArtifactsDir"]))
    candidate_artifacts = Path(str(candidate_result["ArtifactsDir"]))
    baseline_metrics = pd.read_csv(baseline_artifacts / "monthly_metrics.csv")
    candidate_metrics = pd.read_csv(candidate_artifacts / "monthly_metrics.csv")
    native_summary = outer_validation_delta_summary(baseline_metrics=baseline_metrics, candidate_metrics=candidate_metrics)
    baseline_anchor = anchor_rescored_metrics_for_setup(baseline_result)
    candidate_anchor = anchor_rescored_metrics_for_setup(candidate_result)
    anchor_summary = outer_validation_delta_summary(
        baseline_metrics=baseline_anchor["monthly_metrics"],
        candidate_metrics=candidate_anchor["monthly_metrics"],
    )
    similarity_summary = prediction_similarity_summary(
        baseline_predictions=_predictions_for_row(baseline_result),
        candidate_predictions=_predictions_for_row(candidate_result),
        split_name=str(candidate_anchor.get("comparison_split", "validation")),
    )
    decision = _decision_from_comparison_payload(
        baseline_anchor_reward=baseline_anchor.get("validation_reward"),
        baseline_anchor_spearman=baseline_anchor.get("validation_spearman"),
        candidate_anchor_reward=candidate_anchor.get("validation_reward"),
        candidate_anchor_spearman=candidate_anchor.get("validation_spearman"),
        similarity_summary=similarity_summary,
    )
    payload = {
        "baseline_setup_id": baseline_setup_id,
        "candidate_setup_id": candidate_setup_id,
        "comparison_split": str(candidate_anchor.get("comparison_split", "validation")),
        "anchor_profile": {
            "objective_profile_id": ANCHOR_OBJECTIVE_PROFILE_ID,
            "reward_profile_id": ANCHOR_REWARD_PROFILE_ID,
        },
        "baseline_validation_metrics": _validation_metrics_payload(baseline_result, baseline_anchor),
        "candidate_validation_metrics": _validation_metrics_payload(candidate_result, candidate_anchor),
        "baseline_test_metrics": _test_metrics_payload(baseline_result, baseline_anchor),
        "candidate_test_metrics": _test_metrics_payload(candidate_result, candidate_anchor),
        "prediction_similarity": similarity_summary,
        "decision": decision,
        "native_outer_validation": native_summary,
        "anchor_outer_validation": anchor_summary,
        # Preserve the original top-level keys for older readers that expect the native comparison shape.
        "paired_months": native_summary["paired_months"],
        "rows": native_summary["rows"],
        "reward_summary": native_summary["reward_summary"],
        "spearman_summary": native_summary["spearman_summary"],
    }
    output_path = candidate_artifacts / "outer_validation_comparison.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    return output_path


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync framework-phase tracker sections from experiment outputs.")
    parser.add_argument("--output-root", default=None, help="Experiment root directory. Defaults to outputs/experiments.")
    parser.add_argument("--summary-path", default=None, help="Optional explicit path to setup_results.csv.")
    parser.add_argument("--doc-path", default=None, help="Optional explicit path to docs/framework_phase.md.")
    return parser


def main(argv: list[str] | None = None) -> Path:
    parser = _build_cli_parser()
    args = parser.parse_args(argv)
    path = sync_framework_phase_doc(output_root=args.output_root, summary_path=args.summary_path, doc_path=args.doc_path)
    print(f"Synced {path}")
    return path


if __name__ == "__main__":
    main(sys.argv[1:])
