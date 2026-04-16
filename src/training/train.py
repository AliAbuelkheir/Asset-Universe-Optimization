"""Train a framework-phase PPO monthly ranking model and export artifacts."""

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
from src.training.evaluate import evaluate_model_splits, load_ppo_checkpoint, write_evaluation_artifacts
from src.training.frameworks import FrameworkSpec, get_framework_spec
from src.training.panel_utils import load_canonical_monthly_panel
from src.training.policy import MaskedActorCriticPolicy


EXPERIMENT_ROOT = ROOT / "outputs" / "experiments"
SUMMARY_FILE_NAME = "setup_results.csv"


@dataclass(frozen=True)
class SetupConfig:
    setup_id: str
    framework_id: str
    total_timesteps: int
    seed: int = 42
    learning_rate: float = config.FRAMEWORK_PPO_LEARNING_RATE
    n_steps: int = config.FRAMEWORK_PPO_N_STEPS
    batch_size: int = config.FRAMEWORK_PPO_BATCH_SIZE
    n_epochs: int = config.FRAMEWORK_PPO_N_EPOCHS
    gamma: float = config.FRAMEWORK_PPO_GAMMA
    gae_lambda: float = config.FRAMEWORK_PPO_GAE_LAMBDA
    clip_range: float = config.FRAMEWORK_PPO_CLIP_RANGE
    ent_coef: float = config.FRAMEWORK_PPO_ENT_COEF
    vf_coef: float = config.FRAMEWORK_PPO_VF_COEF
    max_grad_norm: float = config.FRAMEWORK_PPO_MAX_GRAD_NORM
    eval_frequency: int = config.FRAMEWORK_PPO_EVAL_FREQUENCY


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _metric(split_summary: pd.DataFrame, split_name: str, column: str) -> float | int | None:
    split_lookup = {row["split"]: row for row in split_summary.to_dict(orient="records")}
    row = split_lookup.get(split_name)
    if row is None:
        return None
    value = row[column]
    return float(value) if isinstance(value, (int, float)) else value


def _split_prediction_count(predictions: pd.DataFrame, split_name: str) -> int:
    return int((predictions["Split"] == split_name).sum())


def _split_month_count(predictions: pd.DataFrame, split_name: str) -> int:
    return int(predictions.loc[predictions["Split"] == split_name, "Date"].nunique())


def _to_summary_row(
    setup: SetupConfig,
    framework: FrameworkSpec,
    split_summary: pd.DataFrame,
    predictions: pd.DataFrame,
    setup_output_dir: Path,
    reported_checkpoint: Path,
) -> dict[str, Any]:
    return {
        "SetupID": setup.setup_id,
        "TimestampUTC": _timestamp_utc(),
        "StudyPhase": config.FRAMEWORK_PHASE_NAME,
        "Trainer": "ppo_monthly_ranking",
        "ActionDistribution": config.ACTION_DISTRIBUTION_NAME,
        "PolicySemanticsVersion": config.POLICY_SEMANTICS_VERSION,
        "FrameworkID": framework.framework_id,
        "PolicyClass": "MaskedActorCriticPolicy",
        "InputView": framework.observation_mode,
        "MonthlyFeatureDim": int(framework.monthly_feature_dim),
        "InputDim": int(framework.input_dim),
        "LookbackMonths": int(framework.lookback_months),
        "StateAssemblyMode": framework.state_assembly_mode,
        "ActorContextMode": framework.actor_context_mode,
        "UsesDailyStrip": bool(framework.uses_daily_strip),
        "DailyStripChannels": int(framework.daily_strip_channels),
        "DailyStripLength": int(framework.daily_strip_length),
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
        "TrainRows": _split_prediction_count(predictions, "train"),
        "ValidationRows": _split_prediction_count(predictions, "validation"),
        "TestRows": _split_prediction_count(predictions, "test"),
        "TrainMonths": _split_month_count(predictions, "train"),
        "ValidationMonths": _split_month_count(predictions, "validation"),
        "TestMonths": _split_month_count(predictions, "test"),
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
        if "StudyPhase" in existing.columns:
            existing = existing.loc[existing["StudyPhase"] == config.FRAMEWORK_PHASE_NAME].copy()
        summary_frame = pd.concat([existing, summary_frame], ignore_index=True)
    summary_frame.to_csv(summary_path, index=False)


def train_setup(
    panel_path: str | Path | None,
    daily_path: str | Path | None,
    setup: SetupConfig,
    output_root: str | Path | None = None,
) -> Path:
    panel = load_canonical_monthly_panel(panel_path)
    framework = get_framework_spec(setup.framework_id)

    setup_output_dir = Path(output_root) / setup.setup_id if output_root is not None else EXPERIMENT_ROOT / setup.setup_id
    setup_output_dir.mkdir(parents=True, exist_ok=True)

    train_env = AssetRiskEnv(
        panel_path=panel_path,
        daily_path=daily_path,
        split_name="train",
        framework_id=setup.framework_id,
        sampling_mode="random",
    )
    validation_callback = ValidationEvaluationCallback(
        panel_path=panel_path,
        daily_path=daily_path,
        output_dir=setup_output_dir,
        framework_id=setup.framework_id,
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
        policy_kwargs={
            "row_encoder_dims": framework.row_encoder_dims,
            "actor_hidden_dims": framework.actor_hidden_dims,
            "actor_context_mode": framework.actor_context_mode,
        },
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
    reporting_model = load_ppo_checkpoint(best_model_path)
    predictions, monthly_metrics, split_summary = evaluate_model_splits(
        model=reporting_model,
        panel_path=panel_path,
        daily_path=daily_path,
        framework_id=setup.framework_id,
        split_names=("train", "validation", "test"),
    )

    setup_metadata = {
        "setup": asdict(setup),
        "study_phase": config.FRAMEWORK_PHASE_NAME,
        "trainer": "ppo_monthly_ranking",
        "action_distribution": config.ACTION_DISTRIBUTION_NAME,
        "policy_semantics_version": config.POLICY_SEMANTICS_VERSION,
        "framework_id": framework.framework_id,
        "framework_spec": {
            "observation_mode": framework.observation_mode,
            "monthly_feature_dim": framework.monthly_feature_dim,
            "lookback_months": framework.lookback_months,
            "state_assembly_mode": framework.state_assembly_mode,
            "actor_context_mode": framework.actor_context_mode,
            "input_dim": framework.input_dim,
            "row_encoder_dims": list(framework.row_encoder_dims),
            "actor_hidden_dims": list(framework.actor_hidden_dims),
            "uses_daily_strip": framework.uses_daily_strip,
            "daily_strip_channels": framework.daily_strip_channels,
            "daily_strip_length": framework.daily_strip_length,
        },
        "policy_class": "MaskedActorCriticPolicy",
        "panel_path": str((Path(panel_path) if panel_path is not None else ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME).resolve()),
        "daily_path": str((Path(daily_path) if daily_path is not None else ROOT / config.READY_DATA_DIR / config.DAILY_MARKET_SERIES_NAME).resolve()),
        "artifacts_dir": str(setup_output_dir.resolve()),
        "best_model_path": str(best_model_path.resolve()),
        "final_model_path": str(final_model_path.resolve()),
        "reported_checkpoint": str(best_model_path.resolve()),
        "validation_selection_metric": "mean_reward",
        "common_decision_start": config.TRAIN_START,
        "panel_state_start": config.PANEL_STATE_START,
        "fixed_ppo_config": {
            "learning_rate": setup.learning_rate,
            "n_steps": setup.n_steps,
            "batch_size": setup.batch_size,
            "n_epochs": setup.n_epochs,
            "gamma": setup.gamma,
            "gae_lambda": setup.gae_lambda,
            "clip_range": setup.clip_range,
            "ent_coef": setup.ent_coef,
            "vf_coef": setup.vf_coef,
            "max_grad_norm": setup.max_grad_norm,
            "eval_frequency": setup.eval_frequency,
        },
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
        framework=framework,
        split_summary=split_summary,
        predictions=predictions,
        setup_output_dir=setup_output_dir,
        reported_checkpoint=best_model_path,
    )
    append_setup_summary(setup_output_dir.parent, summary_row)
    with (setup_output_dir / "setup_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary_row, handle, indent=2, sort_keys=True)
    return setup_output_dir


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a framework-phase PPO monthly ranking model.")
    parser.add_argument("--setup-id", required=True, help="Unique identifier for this experiment run.")
    parser.add_argument("--framework-id", required=True, help="Framework identifier from the active registry.")
    parser.add_argument(
        "--panel-path",
        default=str(ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME),
        help="Canonical monthly state panel path.",
    )
    parser.add_argument("--total-timesteps", type=int, required=True, help="Total PPO timesteps.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    return parser


def main() -> None:
    parser = _build_cli_parser()
    args = parser.parse_args()
    setup = SetupConfig(
        setup_id=args.setup_id,
        framework_id=args.framework_id,
        total_timesteps=args.total_timesteps,
        seed=args.seed,
    )
    output_dir = train_setup(panel_path=args.panel_path, daily_path=None, setup=setup)
    print(f"Training complete: {output_dir}")


if __name__ == "__main__":
    main()
