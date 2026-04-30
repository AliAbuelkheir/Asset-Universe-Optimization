"""Run final tuned PPO reruns for top feature candidates."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config
from src.training.confirm_ppo_tuning import candidate_params
from src.training.train import SetupConfig, train_setup


DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / "top_candidate_reruns" / "refined50"
DEFAULT_PANEL_PATH = ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME
DEFAULT_DAILY_PATH = ROOT / config.READY_DATA_DIR / config.DAILY_MARKET_SERIES_NAME
DEFAULT_CANDIDATE = "refined50"
DEFAULT_SEEDS = [42, 7, 13]
DEFAULT_TOTAL_TIMESTEPS = 32768
SUMMARY_FILE_NAME = "top_candidate_summary.csv"
SELECTION_FILE_NAME = "top_candidate_selection.json"


@dataclass(frozen=True)
class TopCandidate:
    candidate_id: str
    feature_profile_id: str
    panel_path: str
    input_feature_set_id: str = config.DEFAULT_INPUT_FEATURE_SET_ID
    change_type: str = "none"
    changed_feature: str = ""
    variant_id: str = ""
    description: str = ""

    def setup_id(self, tuned_candidate: str, seed: int) -> str:
        return f"TOP-{tuned_candidate.upper()}-{self.candidate_id.upper()}-S{seed}"


TOP_CANDIDATES: tuple[TopCandidate, ...] = (
    TopCandidate(
        candidate_id="full_current_v1",
        feature_profile_id="full_current_v1",
        panel_path=str(DEFAULT_PANEL_PATH),
        change_type="baseline",
        variant_id="base",
        description="Live canonical 11-feature baseline.",
    ),
    TopCandidate(
        candidate_id="monthly_only_rows_v1",
        feature_profile_id="monthly_only_rows_v1",
        panel_path=str(ROOT / config.FEATURE_PROFILE_OUTPUT_DIR / "monthly_only_rows_v1" / config.MONTHLY_PANEL_NAME),
        change_type="alter_row_semantics",
        changed_feature="all_row_features",
        variant_id="monthly_only_rows_v1",
        description="Monthly-only row semantics challenger.",
    ),
    TopCandidate(
        candidate_id="drop_distance_to_3m_high",
        feature_profile_id="drop_distance_to_3m_high",
        panel_path=str(ROOT / config.FEATURE_PROFILE_OUTPUT_DIR / "drop_distance_to_3m_high" / config.MONTHLY_PANEL_NAME),
        change_type="drop_feature",
        changed_feature="distance_to_3m_high",
        variant_id="drop_distance_to_3m_high",
        description="Strongest prior validation-style drop challenger.",
    ),
    TopCandidate(
        candidate_id="distance_to_1m_high",
        feature_profile_id="distance_to_1m_high",
        panel_path=str(ROOT / config.FEATURE_PROFILE_OUTPUT_DIR / "distance_to_1m_high" / config.MONTHLY_PANEL_NAME),
        change_type="alter_feature",
        changed_feature="distance_to_3m_high",
        variant_id="distance_to_1m_high",
        description="Best distance-family redesign.",
    ),
    TopCandidate(
        candidate_id="price_to_sma14",
        feature_profile_id="price_to_sma14",
        panel_path=str(ROOT / config.FEATURE_PROFILE_OUTPUT_DIR / "price_to_sma14" / config.MONTHLY_PANEL_NAME),
        change_type="alter_feature",
        changed_feature="price_to_sma20",
        variant_id="price_to_sma14",
        description="Best moving-average redesign.",
    ),
    TopCandidate(
        candidate_id="max_drawdown_1m",
        feature_profile_id="max_drawdown_1m",
        panel_path=str(ROOT / config.FEATURE_PROFILE_OUTPUT_DIR / "max_drawdown_1m" / config.MONTHLY_PANEL_NAME),
        change_type="alter_feature",
        changed_feature="max_drawdown",
        variant_id="max_drawdown_1m",
        description="Best max-drawdown redesign.",
    ),
    TopCandidate(
        candidate_id="usd_vol_1m",
        feature_profile_id="usd_vol_1m",
        panel_path=str(ROOT / config.FEATURE_PROFILE_OUTPUT_DIR / "usd_vol_1m" / config.MONTHLY_PANEL_NAME),
        change_type="alter_feature",
        changed_feature="usd_vol",
        variant_id="usd_vol_1m",
        description="Best USD-volatility redesign.",
    ),
)


def top_candidate_by_id(candidate_id: str) -> TopCandidate:
    for candidate in TOP_CANDIDATES:
        if candidate.candidate_id == candidate_id:
            return candidate
    raise ValueError(f"Unknown top candidate: {candidate_id}")


def _load_summary(setup_dir: Path) -> dict[str, Any]:
    with (setup_dir / "setup_summary.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _summary_row(candidate: TopCandidate, tuned_candidate: str, summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "CandidateID": candidate.candidate_id,
        "TunedCandidate": tuned_candidate,
        "SetupID": summary["SetupID"],
        "Seed": int(summary["Seed"]),
        "FeatureProfileID": summary["FeatureProfileID"],
        "InputFeatureSetID": summary["InputFeatureSetID"],
        "CheckpointProvenance": summary["CheckpointProvenance"],
        "ValidationMeanReward": float(summary["ValidationMeanReward"]),
        "ValidationMeanSpearman": float(summary["ValidationMeanSpearman"]),
        "ValidationMeanMSE": float(summary["ValidationMeanMSE"]),
        "TestMeanReward": float(summary["TestMeanReward"]),
        "TestMeanSpearman": float(summary["TestMeanSpearman"]),
        "TestMeanMSE": float(summary["TestMeanMSE"]),
        "LearningRate": float(summary["LearningRate"]),
        "NSteps": int(summary["NSteps"]),
        "BatchSize": int(summary["BatchSize"]),
        "NEpochs": int(summary["NEpochs"]),
        "Gamma": float(summary["Gamma"]),
        "GaeLambda": float(summary["GaeLambda"]),
        "ClipRange": float(summary["ClipRange"]),
        "EntCoef": float(summary["EntCoef"]),
        "VfCoef": float(summary["VfCoef"]),
        "MaxGradNorm": float(summary["MaxGradNorm"]),
        "ReportedCheckpoint": summary["ReportedCheckpoint"],
        "ArtifactsDir": summary["ArtifactsDir"],
    }


def select_winning_candidate(summary_frame: pd.DataFrame) -> dict[str, Any]:
    if summary_frame.empty:
        raise ValueError("Cannot select a winning top candidate from an empty summary.")
    required = {"CandidateID", "ValidationMeanReward", "ValidationMeanSpearman", "TestMeanReward", "TestMeanSpearman"}
    missing = required.difference(summary_frame.columns)
    if missing:
        raise ValueError(f"Top candidate summary is missing required columns: {sorted(missing)}")

    grouped = (
        summary_frame.groupby("CandidateID", sort=False)
        .agg(
            seeds=("Seed", "count"),
            mean_validation_reward=("ValidationMeanReward", "mean"),
            mean_validation_spearman=("ValidationMeanSpearman", "mean"),
            mean_test_reward=("TestMeanReward", "mean"),
            mean_test_spearman=("TestMeanSpearman", "mean"),
        )
        .reset_index()
        .sort_values(
            ["mean_validation_reward", "mean_validation_spearman", "CandidateID"],
            ascending=[False, False, True],
        )
    )
    winner = grouped.iloc[0].to_dict()
    return {
        "selection_rule": "max three-seed validation mean reward; validation Spearman tie-breaker; test metrics reporting only",
        "winner": winner,
        "candidates": grouped.to_dict(orient="records"),
    }


def run_top_candidate(
    candidate: TopCandidate,
    seed: int,
    tuned_candidate: str,
    total_timesteps: int,
    output_root: Path,
) -> dict[str, Any]:
    params = candidate_params(tuned_candidate)
    setup = SetupConfig(
        setup_id=candidate.setup_id(tuned_candidate, seed),
        framework_id=config.FEATURE_PHASE_BASE_FRAMEWORK_ID,
        total_timesteps=total_timesteps,
        study_phase=config.FEATURE_PHASE_NAME,
        base_framework_id=config.FEATURE_PHASE_BASE_FRAMEWORK_ID,
        feature_profile_id=candidate.feature_profile_id,
        comparison_protocol_id=config.DEFAULT_COMPARISON_PROTOCOL_ID,
        objective_profile_id=config.DEFAULT_OBJECTIVE_PROFILE_ID,
        reward_profile_id=config.DEFAULT_REWARD_PROFILE_ID,
        training_method_id=config.DEFAULT_TRAINING_METHOD_ID,
        input_feature_set_id=candidate.input_feature_set_id,
        change_type=candidate.change_type,
        changed_feature=candidate.changed_feature,
        variant_id=candidate.variant_id,
        seed=seed,
        gamma=1.0,
        gae_lambda=1.0,
        notes=f"top_candidate_rerun_{tuned_candidate}_{candidate.candidate_id}: {candidate.description}",
        **params,
    )
    setup_dir = train_setup(
        panel_path=candidate.panel_path,
        daily_path=DEFAULT_DAILY_PATH,
        setup=setup,
        output_root=output_root,
    )
    return _summary_row(candidate, tuned_candidate, _load_summary(setup_dir))


def run_top_candidate_matrix(
    candidate_ids: list[str] | None = None,
    seeds: list[int] | None = None,
    tuned_candidate: str = DEFAULT_CANDIDATE,
    total_timesteps: int = DEFAULT_TOTAL_TIMESTEPS,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
) -> pd.DataFrame:
    resolved_output_root = Path(output_root)
    resolved_output_root.mkdir(parents=True, exist_ok=True)
    selected_candidates = (
        list(TOP_CANDIDATES) if candidate_ids is None else [top_candidate_by_id(candidate_id) for candidate_id in candidate_ids]
    )
    selected_seeds = DEFAULT_SEEDS if seeds is None else seeds

    rows: list[dict[str, Any]] = []
    for candidate in selected_candidates:
        for seed in selected_seeds:
            rows.append(
                run_top_candidate(
                    candidate=candidate,
                    seed=seed,
                    tuned_candidate=tuned_candidate,
                    total_timesteps=total_timesteps,
                    output_root=resolved_output_root,
                )
            )

    summary_frame = pd.DataFrame(rows)
    summary_path = resolved_output_root / SUMMARY_FILE_NAME
    summary_frame.to_csv(summary_path, index=False)
    selection = select_winning_candidate(summary_frame)
    with (resolved_output_root / SELECTION_FILE_NAME).open("w", encoding="utf-8") as handle:
        json.dump(selection, handle, indent=2, sort_keys=True)
    return summary_frame


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run refined PPO reruns for top feature candidates.")
    parser.add_argument("--candidates", nargs="+", default=None, help="Candidate IDs to run. Defaults to all top candidates.")
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--tuned-candidate", default=DEFAULT_CANDIDATE)
    parser.add_argument("--total-timesteps", type=int, default=DEFAULT_TOTAL_TIMESTEPS)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--list-candidates", action="store_true", help="Print candidate registry and exit.")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if args.list_candidates:
        print(json.dumps([asdict(candidate) for candidate in TOP_CANDIDATES], indent=2, sort_keys=True))
        return
    summary = run_top_candidate_matrix(
        candidate_ids=args.candidates,
        seeds=args.seeds,
        tuned_candidate=args.tuned_candidate,
        total_timesteps=args.total_timesteps,
        output_root=args.output_root,
    )
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
