"""Train a PPO monthly-panel risk scorer and export RL evaluation artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from stable_baselines3 import PPO

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config
from src.environment.asset_risk_env import AssetRiskEnv
from src.training.callbacks import ValidationEvaluationCallback
from src.training.evaluate import evaluate_model_splits, write_evaluation_artifacts
from src.training.panel_utils import load_canonical_monthly_panel, split_panel_by_date
from src.training.policy import MaskedActorCriticPolicy


EXPERIMENT_ROOT = ROOT / "outputs" / "experiments"
SUMMARY_FILE_NAME = "setup_results.csv"


@dataclass(frozen=True)
class SetupConfig:
    setup_id: str
    total_timesteps: int
    learning_rate: float = 3e-4
    n_steps: int = 256
    batch_size: int = 256
    n_epochs: int = 10
    gamma: float = 1.0
    gae_lambda: float = 1.0
    clip_range: float = 0.2
    ent_coef: float = 0.01
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    eval_frequency: int = 1024
    seed: int = 42


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _metric(split_summary: pd.DataFrame, split_name: str, column: str) -> float | int | None:
    split_lookup = {row["split"]: row for row in split_summary.to_dict(orient="records")}
    row = split_lookup.get(split_name)
    if row is None:
        return None
    value = row[column]
    return float(value) if isinstance(value, (int, float)) else value


def _to_summary_row(
    setup: SetupConfig,
    split_summary: pd.DataFrame,
    setup_output_dir: Path,
    train_frame: pd.DataFrame,
    validation_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    reported_checkpoint: Path,
) -> dict[str, Any]:
    return {
        "SetupID": setup.setup_id,
        "TimestampUTC": _timestamp_utc(),
        "Framework": "ppo_monthly_ranking",
        "PolicyClass": "MaskedActorCriticPolicy",
        "InputView": "monthly_asset_panel",
        "FeatureColumns": ",".join(config.MODEL_FEATURE_COLUMNS),
        "RewardFormula": "0.7*spearman + 0.3*(1-mse)",
        "TotalTimesteps": int(setup.total_timesteps),
        "EvalFrequency": int(setup.eval_frequency),
        "LearningRate": float(setup.learning_rate),
        "NSteps": int(setup.n_steps),
        "BatchSize": int(setup.batch_size),
        "NEpochs": int(setup.n_epochs),
        "Gamma": float(setup.gamma),
        "GaeLambda": float(setup.gae_lambda),
        "ClipRange": float(setup.clip_range),
        "EntCoef": float(setup.ent_coef),
        "VfCoef": float(setup.vf_coef),
        "MaxGradNorm": float(setup.max_grad_norm),
        "Seed": int(setup.seed),
        "TrainRows": int(len(train_frame)),
        "ValidationRows": int(len(validation_frame)),
        "TestRows": int(len(test_frame)),
        "TrainMonths": int(train_frame["Date"].nunique()),
        "ValidationMonths": int(validation_frame["Date"].nunique()),
        "TestMonths": int(test_frame["Date"].nunique()),
        "TrainMeanReward": _metric(split_summary, "train", "mean_reward"),
        "ValidationMeanReward": _metric(split_summary, "validation", "mean_reward"),
        "TestMeanReward": _metric(split_summary, "test", "mean_reward"),
        "TrainMeanSpearman": _metric(split_summary, "train", "mean_spearman"),
        "ValidationMeanSpearman": _metric(split_summary, "validation", "mean_spearman"),
        "TestMeanSpearman": _metric(split_summary, "test", "mean_spearman"),
        "TrainMeanMSE": _metric(split_summary, "train", "mean_mse"),
        "ValidationMeanMSE": _metric(split_summary, "validation", "mean_mse"),
        "TestMeanMSE": _metric(split_summary, "test", "mean_mse"),
        "ReportedCheckpoint": str(reported_checkpoint.resolve()),
        "ArtifactsDir": str(setup_output_dir.resolve()),
    }


def append_setup_summary(summary_root: Path, summary_row: dict[str, Any]) -> None:
    summary_root.mkdir(parents=True, exist_ok=True)
    summary_path = summary_root / SUMMARY_FILE_NAME
    summary_frame = pd.DataFrame([summary_row])
    if summary_path.exists():
        existing = pd.read_csv(summary_path)
        if "Framework" in existing.columns:
            existing = existing.loc[existing["Framework"] == "ppo_monthly_ranking"].copy()
        summary_frame = pd.concat([existing, summary_frame], ignore_index=True)
    summary_frame.to_csv(summary_path, index=False)


def train_setup(
    panel_path: str | Path | None,
    setup: SetupConfig,
    output_root: str | Path | None = None,
) -> Path:
    panel = load_canonical_monthly_panel(panel_path)
    split_frames = split_panel_by_date(panel)
    train_frame = split_frames["train"]
    validation_frame = split_frames["validation"]
    test_frame = split_frames["test"]

    setup_output_dir = Path(output_root) / setup.setup_id if output_root is not None else EXPERIMENT_ROOT / setup.setup_id
    setup_output_dir.mkdir(parents=True, exist_ok=True)

    train_env = AssetRiskEnv(panel_path=panel_path, split_name="train", sampling_mode="random")
    validation_callback = ValidationEvaluationCallback(
        panel_path=panel_path,
        output_dir=setup_output_dir,
        eval_frequency=setup.eval_frequency,
    )

    model = PPO(
        policy=MaskedActorCriticPolicy,
        env=train_env,
        learning_rate=setup.learning_rate,
        n_steps=setup.n_steps,
        batch_size=setup.batch_size,
        n_epochs=setup.n_epochs,
        gamma=setup.gamma,
        gae_lambda=setup.gae_lambda,
        clip_range=setup.clip_range,
        ent_coef=setup.ent_coef,
        vf_coef=setup.vf_coef,
        max_grad_norm=setup.max_grad_norm,
        seed=setup.seed,
        verbose=0,
    )
    model.learn(total_timesteps=setup.total_timesteps, callback=validation_callback, progress_bar=False)

    final_model_path = setup_output_dir / "final_model.zip"
    model.save(final_model_path)

    training_metrics = validation_callback.training_metrics_frame()
    if training_metrics.empty:
        validation_callback.evaluate_now(timesteps=int(model.num_timesteps))
        training_metrics = validation_callback.training_metrics_frame()
    training_metrics.to_csv(setup_output_dir / "training_metrics.csv", index=False)

    best_model_path = validation_callback.best_model_path if validation_callback.best_model_path.exists() else final_model_path
    reporting_model = PPO.load(best_model_path)
    predictions, monthly_metrics, split_summary = evaluate_model_splits(
        model=reporting_model,
        panel_path=panel_path,
        split_names=("train", "validation", "test"),
    )

    setup_metadata = {
        "setup": asdict(setup),
        "framework": "ppo_monthly_ranking",
        "policy_class": "MaskedActorCriticPolicy",
        "panel_path": str((Path(panel_path) if panel_path is not None else ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME).resolve()),
        "artifacts_dir": str(setup_output_dir.resolve()),
        "best_model_path": str(best_model_path.resolve()),
        "final_model_path": str(final_model_path.resolve()),
        "reported_checkpoint": str(best_model_path.resolve()),
        "validation_selection_metric": "mean_reward",
        "train_rows": int(len(train_frame)),
        "validation_rows": int(len(validation_frame)),
        "test_rows": int(len(test_frame)),
        "train_months": int(train_frame["Date"].nunique()),
        "validation_months": int(validation_frame["Date"].nunique()),
        "test_months": int(test_frame["Date"].nunique()),
    }
    write_evaluation_artifacts(
        output_dir=setup_output_dir,
        predictions=predictions,
        monthly_metrics=monthly_metrics,
        split_summary=split_summary,
        setup_metadata=setup_metadata,
    )

    summary_row = _to_summary_row(
        setup=setup,
        split_summary=split_summary,
        setup_output_dir=setup_output_dir,
        train_frame=train_frame,
        validation_frame=validation_frame,
        test_frame=test_frame,
        reported_checkpoint=best_model_path,
    )
    append_setup_summary(setup_output_dir.parent, summary_row)
    with (setup_output_dir / "setup_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary_row, handle, indent=2, sort_keys=True)
    return setup_output_dir


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a PPO monthly-panel risk scorer and export evaluation artifacts.")
    parser.add_argument("--setup-id", required=True, help="Unique identifier for this PPO experiment.")
    parser.add_argument(
        "--panel-path",
        default=str(ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME),
        help="Canonical monthly panel path.",
    )
    parser.add_argument("--total-timesteps", type=int, required=True, help="Total PPO timesteps.")
    parser.add_argument("--learning-rate", type=float, default=3e-4, help="PPO learning rate.")
    parser.add_argument("--n-steps", type=int, default=256, help="PPO rollout length.")
    parser.add_argument("--batch-size", type=int, default=256, help="PPO minibatch size.")
    parser.add_argument("--n-epochs", type=int, default=10, help="PPO optimization epochs per update.")
    parser.add_argument("--gamma", type=float, default=1.0, help="Discount factor.")
    parser.add_argument("--gae-lambda", type=float, default=1.0, help="GAE lambda.")
    parser.add_argument("--clip-range", type=float, default=0.2, help="PPO clip range.")
    parser.add_argument("--ent-coef", type=float, default=0.01, help="Entropy coefficient.")
    parser.add_argument("--vf-coef", type=float, default=0.5, help="Value loss coefficient.")
    parser.add_argument("--max-grad-norm", type=float, default=0.5, help="Gradient clipping norm.")
    parser.add_argument("--eval-frequency", type=int, default=1024, help="How often to run ordered validation evaluation.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument(
        "--output-root",
        default=str(EXPERIMENT_ROOT),
        help="Root directory where experiment artifacts should be written.",
    )
    return parser


def main() -> None:
    parser = _build_cli_parser()
    args = parser.parse_args()
    setup = SetupConfig(
        setup_id=args.setup_id,
        total_timesteps=args.total_timesteps,
        learning_rate=args.learning_rate,
        n_steps=args.n_steps,
        batch_size=args.batch_size,
        n_epochs=args.n_epochs,
        gamma=args.gamma,
        gae_lambda=args.gae_lambda,
        clip_range=args.clip_range,
        ent_coef=args.ent_coef,
        vf_coef=args.vf_coef,
        max_grad_norm=args.max_grad_norm,
        eval_frequency=args.eval_frequency,
        seed=args.seed,
    )
    output_dir = train_setup(panel_path=args.panel_path, setup=setup, output_root=args.output_root)
    print(f"Training complete: {output_dir}")


if __name__ == "__main__":
    main()
