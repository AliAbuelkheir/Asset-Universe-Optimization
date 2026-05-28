"""Tail-aware diagnostics for saved ranked-risk experiment artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config
from src.training.metrics import PREDICTION_COLUMN, evaluate_prediction_frame


DEFAULT_REFINED50_ROOT = ROOT / "outputs" / "generated" / "runs" / "top_candidates" / "refined50"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "generated" / "reports" / "tail_diagnostics"
DEFAULT_CANDIDATES = (
    "drop_distance_to_3m_high",
    "full_current_v1",
    "monthly_only_rows_v1",
    "distance_to_1m_high",
    "max_drawdown_1m",
    "usd_vol_1m",
)
DEFAULT_SEEDS = (42, 7, 13)
OCTOBER_STRESS_MONTH = "2025-10"
SUMMARY_FILE_NAME = "refined50_tail_comparison.csv"
SELECTION_FILE_NAME = "refined50_tail_selection.json"


@dataclass(frozen=True)
class CandidateArtifact:
    candidate_id: str
    seed: int
    artifact_dir: Path


def setup_dir_name(candidate_id: str, seed: int) -> str:
    return f"TOP-REFINED50-{candidate_id.upper()}-S{seed}"


def artifact_for(candidate_id: str, seed: int, artifact_root: Path = DEFAULT_REFINED50_ROOT) -> CandidateArtifact:
    return CandidateArtifact(
        candidate_id=candidate_id,
        seed=seed,
        artifact_dir=artifact_root / setup_dir_name(candidate_id, seed),
    )


def load_ranked_predictions(artifact: CandidateArtifact) -> pd.DataFrame:
    path = artifact.artifact_dir / "ranked_predictions.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing ranked predictions: {path}")
    return pd.read_csv(path)


def _split_row(split_summary: pd.DataFrame, split: str) -> dict[str, Any]:
    rows = split_summary.loc[split_summary["split"].astype(str).eq(split)]
    if rows.empty:
        return {}
    return rows.iloc[0].to_dict()


def _month_metric(monthly_metrics: pd.DataFrame, split: str, date: str, column: str) -> float | None:
    rows = monthly_metrics.loc[
        monthly_metrics["split"].astype(str).eq(split)
        & monthly_metrics["date"].astype(str).eq(date)
    ]
    if rows.empty or column not in rows:
        return None
    value = rows.iloc[0][column]
    return None if pd.isna(value) else float(value)


def summarize_artifact(artifact: CandidateArtifact) -> dict[str, Any]:
    predictions = load_ranked_predictions(artifact)
    monthly_metrics, split_summary = evaluate_prediction_frame(
        predictions,
        score_column=PREDICTION_COLUMN,
        reward_profile=config.DEFAULT_REWARD_PROFILE_ID,
    )
    validation = _split_row(split_summary, "validation")
    test = _split_row(split_summary, "test")
    return {
        "CandidateID": artifact.candidate_id,
        "Seed": artifact.seed,
        "ArtifactsDir": str(artifact.artifact_dir.resolve()),
        "ValidationMeanReward": validation.get("mean_reward"),
        "ValidationMeanSpearman": validation.get("mean_spearman"),
        "ValidationMeanHighRiskTop25Overlap": validation.get("mean_high_risk_top25_overlap"),
        "ValidationWorstHighRiskTop25Overlap": validation.get("worst_high_risk_top25_overlap"),
        "TestMeanReward": test.get("mean_reward"),
        "TestMeanSpearman": test.get("mean_spearman"),
        "TestMeanHighRiskTop25Overlap": test.get("mean_high_risk_top25_overlap"),
        "TestWorstHighRiskTop25Overlap": test.get("worst_high_risk_top25_overlap"),
        "October2025HighRiskTop25Overlap": _month_metric(
            monthly_metrics,
            split="test",
            date=OCTOBER_STRESS_MONTH,
            column="high_risk_top25_overlap",
        ),
        "October2025Spearman": _month_metric(
            monthly_metrics,
            split="test",
            date=OCTOBER_STRESS_MONTH,
            column="spearman",
        ),
        "October2025Reward": _month_metric(
            monthly_metrics,
            split="test",
            date=OCTOBER_STRESS_MONTH,
            column="reward",
        ),
    }


def candidate_mean_summary(rows: pd.DataFrame) -> pd.DataFrame:
    numeric_columns = [
        "ValidationMeanReward",
        "ValidationMeanSpearman",
        "ValidationMeanHighRiskTop25Overlap",
        "ValidationWorstHighRiskTop25Overlap",
        "TestMeanReward",
        "TestMeanSpearman",
        "TestMeanHighRiskTop25Overlap",
        "TestWorstHighRiskTop25Overlap",
        "October2025HighRiskTop25Overlap",
        "October2025Spearman",
        "October2025Reward",
    ]
    grouped = (
        rows.groupby("CandidateID", sort=False)
        .agg(
            Seeds=("Seed", "count"),
            **{column: (column, "mean") for column in numeric_columns},
        )
        .reset_index()
    )
    return grouped.sort_values(
        [
            "ValidationMeanHighRiskTop25Overlap",
            "ValidationMeanSpearman",
            "ValidationMeanReward",
            "CandidateID",
        ],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)


def monthly_only_tail_decision(grouped: pd.DataFrame) -> dict[str, Any]:
    current_rows = grouped.loc[grouped["CandidateID"].eq("drop_distance_to_3m_high")]
    challenger_rows = grouped.loc[grouped["CandidateID"].eq("monthly_only_rows_v1")]
    if current_rows.empty or challenger_rows.empty:
        return {
            "label": "incomplete",
            "reason": "Expected both drop_distance_to_3m_high and monthly_only_rows_v1 in the diagnostic set.",
        }
    current = current_rows.iloc[0]
    challenger = challenger_rows.iloc[0]
    overlap_delta = float(challenger["ValidationMeanHighRiskTop25Overlap"] - current["ValidationMeanHighRiskTop25Overlap"])
    spearman_delta = float(challenger["ValidationMeanSpearman"] - current["ValidationMeanSpearman"])
    promoted = bool(overlap_delta > 0.0 and spearman_delta >= -0.01)
    return {
        "label": "promote_monthly_only_rows_v1_for_tail_confirmation" if promoted else "keep_current_best_for_now",
        "rule": "Promote only if validation high-risk top-25% overlap improves and validation Spearman loses no more than 0.01.",
        "validation_high_risk_overlap_delta": overlap_delta,
        "validation_spearman_delta": spearman_delta,
    }


def build_tail_diagnostic_report(
    candidates: tuple[str, ...] = DEFAULT_CANDIDATES,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    artifact_root: str | Path = DEFAULT_REFINED50_ROOT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    root = Path(artifact_root)
    rows = [
        summarize_artifact(artifact_for(candidate_id, seed, artifact_root=root))
        for candidate_id in candidates
        for seed in seeds
    ]
    row_frame = pd.DataFrame(rows)
    grouped = candidate_mean_summary(row_frame)
    decision = monthly_only_tail_decision(grouped)
    payload = {
        "selection_note": "Diagnostics only. Current-best metadata is unchanged.",
        "ranking_rule": "Sort by validation high-risk top-25% overlap, then validation Spearman, then validation reward.",
        "monthly_only_tail_decision": decision,
        "candidate_means": grouped.to_dict(orient="records"),
        "seed_rows": row_frame.to_dict(orient="records"),
    }

    resolved_output_dir = Path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    grouped.to_csv(resolved_output_dir / SUMMARY_FILE_NAME, index=False)
    with (resolved_output_dir / SELECTION_FILE_NAME).open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    return grouped, payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Re-score saved refined50 artifacts with tail-aware diagnostics.")
    parser.add_argument("--artifact-root", default=str(DEFAULT_REFINED50_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--candidates", nargs="+", default=list(DEFAULT_CANDIDATES))
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    grouped, payload = build_tail_diagnostic_report(
        candidates=tuple(args.candidates),
        seeds=tuple(args.seeds),
        artifact_root=args.artifact_root,
        output_dir=args.output_dir,
    )
    print(grouped.to_string(index=False))
    print(json.dumps(payload["monthly_only_tail_decision"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
