"""Promote one trained artifact directory into the canonical best-model output."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config


REQUIRED_FILES = (
    "best_model.zip",
    "final_model.zip",
    "setup_summary.json",
    "setup_metadata.json",
    "split_summary.csv",
    "monthly_metrics.csv",
    "ranked_predictions.csv",
)
OPTIONAL_FILES = ("training_metrics.csv",)
MANIFEST_FILE_NAME = "best_model_manifest.json"
README_FILE_NAME = "README.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _canonical_path(destination: Path, file_name: str) -> str:
    return str((destination / file_name).resolve())


def _rewrite_generated_output_paths(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _rewrite_generated_output_paths(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_rewrite_generated_output_paths(item) for item in value]
    if not isinstance(value, str):
        return value
    replacements = {
        "outputs\\feature_candidates": "outputs\\generated\\datasets\\feature_candidates",
        "outputs/feature_candidates": "outputs/generated/datasets/feature_candidates",
        "outputs\\feature_profiles": "outputs\\generated\\datasets\\feature_profiles",
        "outputs/feature_profiles": "outputs/generated/datasets/feature_profiles",
        "outputs\\tail_candidate_reruns": "outputs\\generated\\runs\\tail_candidates",
        "outputs/tail_candidate_reruns": "outputs/generated/runs/tail_candidates",
        "outputs\\top_candidate_reruns": "outputs\\generated\\runs\\top_candidates",
        "outputs/top_candidate_reruns": "outputs/generated/runs/top_candidates",
        "outputs\\tail_reward_reruns": "outputs\\generated\\runs\\tail_reward",
        "outputs/tail_reward_reruns": "outputs/generated/runs/tail_reward",
        "outputs\\ppo_tuning": "outputs\\generated\\runs\\ppo_tuning",
        "outputs/ppo_tuning": "outputs/generated/runs/ppo_tuning",
        "outputs\\experiments": "outputs\\generated\\runs\\experiments",
        "outputs/experiments": "outputs/generated/runs/experiments",
    }
    rewritten = value
    for old, new in replacements.items():
        rewritten = rewritten.replace(old, new)
    return rewritten


def _normalize_setup_metadata(destination: Path) -> None:
    path = destination / "setup_metadata.json"
    if not path.exists():
        return
    payload = _rewrite_generated_output_paths(_load_json(path))
    payload["artifacts_dir"] = str(destination.resolve())
    payload["best_model_path"] = _canonical_path(destination, "best_model.zip")
    payload["final_model_path"] = _canonical_path(destination, "final_model.zip")
    payload["reported_checkpoint"] = _canonical_path(destination, "best_model.zip")
    _write_json(path, payload)


def _normalize_setup_summary(destination: Path) -> None:
    path = destination / "setup_summary.json"
    if not path.exists():
        return
    payload = _rewrite_generated_output_paths(_load_json(path))
    payload["ArtifactsDir"] = str(destination.resolve())
    payload["ReportedCheckpoint"] = _canonical_path(destination, "best_model.zip")
    _write_json(path, payload)


def _read_summary_value(destination: Path, key: str) -> Any:
    summary_path = destination / "setup_summary.json"
    if not summary_path.exists():
        return None
    return _load_json(summary_path).get(key)


def _write_readme(destination: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "# Current Best Model",
        "",
        "This directory is overwritten on every best-model promotion.",
        "",
        f"- model id: `{manifest['model_id']}`",
        f"- framework: `{manifest['framework_id']}`",
        f"- feature profile: `{manifest['feature_profile_id']}`",
        f"- additive feature: `{manifest['additive_feature_id'] or 'none'}`",
        f"- input feature set: `{manifest['input_feature_set_id']}`",
        f"- tuned PPO candidate: `{manifest['tuned_ppo_id']}`",
        f"- seed: `{manifest['seed']}`",
        f"- selection rule: `{manifest['selection_rule']}`",
        f"- source artifact: `{manifest['source_artifact_dir']}`",
        f"- promoted at: `{manifest['promoted_at_utc']}`",
        "",
        "Canonical files:",
        "",
        "- `best_model.zip`",
        "- `final_model.zip`",
        "- `setup_summary.json`",
        "- `setup_metadata.json`",
        "- `split_summary.csv`",
        "- `monthly_metrics.csv`",
        "- `ranked_predictions.csv`",
        f"- `{MANIFEST_FILE_NAME}`",
        "",
        "All non-canonical generated runs belong under `outputs/generated/` and are ignored by git.",
        "",
    ]
    (destination / README_FILE_NAME).write_text("\n".join(lines), encoding="utf-8")


def promote_best_model(
    source_artifact_dir: str | Path,
    destination_dir: str | Path = ROOT / config.BEST_MODEL_OUTPUT_DIR,
    model_id: str = config.CURRENT_BEST_MODEL_ID,
    framework_id: str = config.CURRENT_BEST_FRAMEWORK_ID,
    feature_profile_id: str = config.CURRENT_BEST_FEATURE_PROFILE_ID,
    additive_feature_id: str = config.CURRENT_BEST_ADDITIVE_FEATURE_ID,
    input_feature_set_id: str = config.CURRENT_BEST_INPUT_FEATURE_SET_ID,
    tuned_ppo_id: str = config.CURRENT_BEST_TUNED_PPO_ID,
    selection_rule: str = config.CURRENT_BEST_SELECTION_RULE,
) -> Path:
    source = Path(source_artifact_dir)
    destination = Path(destination_dir)
    missing = [file_name for file_name in REQUIRED_FILES if not (source / file_name).exists()]
    if missing:
        raise FileNotFoundError(f"Cannot promote {source}: missing required files {missing}")

    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)

    for file_name in REQUIRED_FILES + OPTIONAL_FILES:
        source_file = source / file_name
        if source_file.exists():
            shutil.copy2(source_file, destination / file_name)

    _normalize_setup_metadata(destination)
    _normalize_setup_summary(destination)

    manifest = {
        "model_id": model_id,
        "framework_id": framework_id,
        "feature_profile_id": feature_profile_id,
        "additive_feature_id": additive_feature_id,
        "input_feature_set_id": input_feature_set_id,
        "tuned_ppo_id": tuned_ppo_id,
        "seed": _read_summary_value(destination, "Seed"),
        "setup_id": _read_summary_value(destination, "SetupID"),
        "selection_rule": selection_rule,
        "source_artifact_dir": _repo_relative(source),
        "destination_dir": _repo_relative(destination),
        "promoted_at_utc": _utc_now(),
    }
    _write_json(destination / MANIFEST_FILE_NAME, manifest)
    _write_readme(destination, manifest)
    return destination


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Overwrite outputs/best_model with one promoted artifact directory.")
    parser.add_argument("--source-artifact-dir", required=True)
    parser.add_argument("--destination-dir", default=str(ROOT / config.BEST_MODEL_OUTPUT_DIR))
    parser.add_argument("--model-id", default=config.CURRENT_BEST_MODEL_ID)
    parser.add_argument("--framework-id", default=config.CURRENT_BEST_FRAMEWORK_ID)
    parser.add_argument("--feature-profile-id", default=config.CURRENT_BEST_FEATURE_PROFILE_ID)
    parser.add_argument("--additive-feature-id", default=config.CURRENT_BEST_ADDITIVE_FEATURE_ID)
    parser.add_argument("--input-feature-set-id", default=config.CURRENT_BEST_INPUT_FEATURE_SET_ID)
    parser.add_argument("--tuned-ppo-id", default=config.CURRENT_BEST_TUNED_PPO_ID)
    parser.add_argument("--selection-rule", default=config.CURRENT_BEST_SELECTION_RULE)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    destination = promote_best_model(
        source_artifact_dir=args.source_artifact_dir,
        destination_dir=args.destination_dir,
        model_id=args.model_id,
        framework_id=args.framework_id,
        feature_profile_id=args.feature_profile_id,
        additive_feature_id=args.additive_feature_id,
        input_feature_set_id=args.input_feature_set_id,
        tuned_ppo_id=args.tuned_ppo_id,
        selection_rule=args.selection_rule,
    )
    print(f"Promoted best model to {destination}")


if __name__ == "__main__":
    main()
