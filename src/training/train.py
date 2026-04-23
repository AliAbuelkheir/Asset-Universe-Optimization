"""Train a framework- or feature-phase PPO monthly ranking model and export artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
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
from src.feature_profiles import FeatureProfile, get_feature_profile
from src.input_feature_sets import get_input_feature_set
from src.training.callbacks import ValidationEvaluationCallback
from src.training.evaluate import evaluate_model_splits, load_ppo_checkpoint, write_evaluation_artifacts
from src.training.experiment_profiles import (
    ComparisonProtocol,
    ObjectiveProfile,
    RewardProfile,
    TrainingMethod,
    get_comparison_protocol,
    get_objective_profile,
    get_reward_profile,
    get_training_method,
)
from src.training.frameworks import FrameworkSpec, get_runtime_framework_spec
from src.training.panel_utils import load_monthly_panel
from src.training.policy import MaskedActorCriticPolicy
from src.training.results_store import EXPERIMENT_ROOT, SUMMARY_FILE_NAME


@dataclass(frozen=True)
class SetupConfig:
    setup_id: str
    framework_id: str
    total_timesteps: int
    study_phase: str = config.FRAMEWORK_PHASE_NAME
    base_framework_id: str = ""
    feature_profile_id: str = config.DEFAULT_FEATURE_PROFILE_ID
    change_type: str = "none"
    changed_feature: str = ""
    variant_id: str = ""
    notes: str = ""
    feature_profile_parameters: dict[str, Any] = field(default_factory=dict)
    comparison_protocol_id: str = config.DEFAULT_COMPARISON_PROTOCOL_ID
    objective_profile_id: str = config.DEFAULT_OBJECTIVE_PROFILE_ID
    reward_profile_id: str = config.DEFAULT_REWARD_PROFILE_ID
    training_method_id: str = config.DEFAULT_TRAINING_METHOD_ID
    input_feature_set_id: str = config.DEFAULT_INPUT_FEATURE_SET_ID
    checkpoint_provenance: str = ""
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


def _profile_params_json(profile: FeatureProfile, setup: SetupConfig) -> str:
    parameters = profile.parameter_values() | setup.feature_profile_parameters
    return json.dumps(parameters, sort_keys=True)


def _reported_checkpoint_path(
    final_model_path: Path,
    best_model_path: Path,
    checkpoint_provenance: str,
) -> Path:
    if checkpoint_provenance == "best_inner_validation" and best_model_path.exists():
        return best_model_path
    return final_model_path


def _to_summary_row(
    setup: SetupConfig,
    framework: FrameworkSpec,
    feature_profile: FeatureProfile,
    comparison_protocol: ComparisonProtocol,
    objective_profile: ObjectiveProfile,
    reward_profile: RewardProfile,
    training_method: TrainingMethod,
    feature_columns: tuple[str, ...],
    split_summary: pd.DataFrame,
    predictions: pd.DataFrame,
    setup_output_dir: Path,
    reported_checkpoint: Path,
) -> dict[str, Any]:
    checkpoint_split = comparison_protocol.checkpoint_selection_split_name
    comparison_split = comparison_protocol.comparison_split_name
    return {
        "SetupID": setup.setup_id,
        "TimestampUTC": _timestamp_utc(),
        "StudyPhase": setup.study_phase,
        "Trainer": "ppo_monthly_ranking",
        "ActionDistribution": config.ACTION_DISTRIBUTION_NAME,
        "PolicySemanticsVersion": config.POLICY_SEMANTICS_VERSION,
        "BaseFrameworkID": setup.base_framework_id,
        "FrameworkID": framework.framework_id,
        "FeatureProfileID": feature_profile.feature_profile_id,
        "ChangeType": setup.change_type,
        "ChangedFeature": setup.changed_feature,
        "VariantID": setup.variant_id,
        "FeatureProfileParameters": _profile_params_json(feature_profile, setup),
        "ComparisonProtocolID": comparison_protocol.comparison_protocol_id,
        "ObjectiveProfileID": objective_profile.objective_profile_id,
        "RewardProfileID": reward_profile.reward_profile_id,
        "TrainingMethodID": training_method.training_method_id,
        "InputFeatureSetID": setup.input_feature_set_id,
        "CheckpointProvenance": setup.checkpoint_provenance,
        "CheckpointSelectionSplit": checkpoint_split,
        "ComparisonSplit": comparison_split,
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
        "DailyFusionMode": framework.daily_fusion_mode,
        "DailyPathScope": framework.daily_path_scope,
        "DailyChannelNames": ",".join(framework.daily_channel_names),
        "FeatureColumns": ",".join(feature_columns),
        "RewardFormula": reward_profile.formula_label(),
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
        "TrainRows": _split_prediction_count(predictions, comparison_protocol.training_split_name),
        "ValidationRows": _split_prediction_count(predictions, comparison_split),
        "TestRows": _split_prediction_count(predictions, "test"),
        "TrainMonths": _split_month_count(predictions, comparison_protocol.training_split_name),
        "ValidationMonths": _split_month_count(predictions, comparison_split),
        "TestMonths": _split_month_count(predictions, "test"),
        "TrainMeanReward": _metric(split_summary, comparison_protocol.training_split_name, "mean_reward"),
        "ValidationMeanReward": _metric(split_summary, comparison_split, "mean_reward"),
        "TestMeanReward": _metric(split_summary, "test", "mean_reward"),
        "TrainMeanSpearman": _metric(split_summary, comparison_protocol.training_split_name, "mean_spearman"),
        "ValidationMeanSpearman": _metric(split_summary, comparison_split, "mean_spearman"),
        "TestMeanSpearman": _metric(split_summary, "test", "mean_spearman"),
        "TrainMeanMSE": _metric(split_summary, comparison_protocol.training_split_name, "mean_mse"),
        "ValidationMeanMSE": _metric(split_summary, comparison_split, "mean_mse"),
        "TestMeanMSE": _metric(split_summary, "test", "mean_mse"),
        "InnerValidationRows": _split_prediction_count(predictions, checkpoint_split),
        "InnerValidationMonths": _split_month_count(predictions, checkpoint_split),
        "InnerValidationMeanReward": _metric(split_summary, checkpoint_split, "mean_reward"),
        "InnerValidationMeanSpearman": _metric(split_summary, checkpoint_split, "mean_spearman"),
        "InnerValidationMeanMSE": _metric(split_summary, checkpoint_split, "mean_mse"),
        "ReportedCheckpoint": str(reported_checkpoint.resolve()),
        "ArtifactsDir": str(setup_output_dir.resolve()),
        "Notes": setup.notes,
    }


def append_setup_summary(summary_root: Path, summary_row: dict[str, Any]) -> None:
    summary_root.mkdir(parents=True, exist_ok=True)
    summary_path = summary_root / SUMMARY_FILE_NAME
    summary_frame = pd.DataFrame([summary_row])
    if summary_path.exists():
        existing = pd.read_csv(summary_path)
        summary_frame = pd.concat([existing, summary_frame], ignore_index=True)
    summary_frame.to_csv(summary_path, index=False)


def train_setup(
    panel_path: str | Path | None,
    daily_path: str | Path | None,
    setup: SetupConfig,
    output_root: str | Path | None = None,
) -> Path:
    input_feature_set = get_input_feature_set(setup.input_feature_set_id)
    feature_columns = tuple(input_feature_set.feature_columns)
    panel = load_monthly_panel(
        panel_path,
        feature_columns=feature_columns,
        allow_extra_columns=feature_columns != tuple(config.MODEL_FEATURE_COLUMNS),
    )
    framework = get_runtime_framework_spec(setup.framework_id, feature_count=len(feature_columns))
    feature_profile = get_feature_profile(setup.feature_profile_id)
    comparison_protocol = get_comparison_protocol(setup.comparison_protocol_id)
    objective_profile = get_objective_profile(setup.objective_profile_id)
    reward_profile = get_reward_profile(setup.reward_profile_id)
    training_method = get_training_method(setup.training_method_id)
    base_framework_id = setup.base_framework_id or (
        config.FEATURE_PHASE_BASE_FRAMEWORK_ID if setup.study_phase == config.FEATURE_PHASE_NAME else framework.framework_id
    )
    checkpoint_provenance = setup.checkpoint_provenance or (
        "best_inner_validation"
        if comparison_protocol.checkpoint_selection_split_name == "inner_validation"
        else "final"
    )
    setup = SetupConfig(
        **(asdict(setup) | {"base_framework_id": base_framework_id, "checkpoint_provenance": checkpoint_provenance}),
    )

    if setup.study_phase == config.FEATURE_PHASE_NAME:
        if framework.framework_id != config.FEATURE_PHASE_BASE_FRAMEWORK_ID:
            raise ValueError(
                f"Feature comparison runs must use {config.FEATURE_PHASE_BASE_FRAMEWORK_ID}, not {framework.framework_id}."
            )
        if framework.uses_daily_strip:
            raise ValueError("Feature comparison runs must stay on the monthly-only backbone.")
        if panel_path is None and feature_profile.feature_profile_id != config.DEFAULT_FEATURE_PROFILE_ID:
            raise ValueError("Non-base feature profiles require an explicit panel_path.")

    setup_output_dir = Path(output_root) / setup.setup_id if output_root is not None else EXPERIMENT_ROOT / setup.setup_id
    setup_output_dir.mkdir(parents=True, exist_ok=True)

    train_env = AssetRiskEnv(
        panel_path=panel_path,
        daily_path=daily_path,
        split_name=comparison_protocol.training_split_name,
        framework_id=setup.framework_id,
        sampling_mode=training_method.sampling_mode,
        comparison_protocol_id=comparison_protocol.comparison_protocol_id,
        objective_profile_id=objective_profile.objective_profile_id,
        reward_profile_id=reward_profile.reward_profile_id,
        feature_columns=feature_columns,
    )
    validation_callback = ValidationEvaluationCallback(
        panel_path=panel_path,
        daily_path=daily_path,
        output_dir=setup_output_dir,
        framework_id=setup.framework_id,
        eval_frequency=setup.eval_frequency,
        comparison_protocol_id=comparison_protocol.comparison_protocol_id,
        objective_profile_id=objective_profile.objective_profile_id,
        reward_profile_id=reward_profile.reward_profile_id,
        feature_columns=feature_columns,
        selection_split_name=comparison_protocol.checkpoint_selection_split_name,
        comparison_split_name=comparison_protocol.comparison_split_name,
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
            "daily_fusion_mode": framework.daily_fusion_mode,
            "daily_path_scope": framework.daily_path_scope,
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
    reported_checkpoint = _reported_checkpoint_path(final_model_path, best_model_path, setup.checkpoint_provenance)
    reporting_model = load_ppo_checkpoint(reported_checkpoint)

    split_names = [comparison_protocol.training_split_name]
    if comparison_protocol.has_split(comparison_protocol.checkpoint_selection_split_name):
        split_names.append(comparison_protocol.checkpoint_selection_split_name)
    if comparison_protocol.comparison_split_name not in split_names:
        split_names.append(comparison_protocol.comparison_split_name)
    if "test" not in split_names:
        split_names.append("test")

    predictions, monthly_metrics, split_summary = evaluate_model_splits(
        model=reporting_model,
        panel_path=panel_path,
        daily_path=daily_path,
        framework_id=setup.framework_id,
        split_names=split_names,
        comparison_protocol_id=comparison_protocol.comparison_protocol_id,
        objective_profile_id=objective_profile.objective_profile_id,
        reward_profile_id=reward_profile.reward_profile_id,
        feature_columns=feature_columns,
    )

    setup_metadata = {
        "setup": asdict(setup),
        "study_phase": setup.study_phase,
        "trainer": "ppo_monthly_ranking",
        "action_distribution": config.ACTION_DISTRIBUTION_NAME,
        "policy_semantics_version": config.POLICY_SEMANTICS_VERSION,
        "comparison_protocol_id": comparison_protocol.comparison_protocol_id,
        "comparison_protocol": {
            "description": comparison_protocol.description,
            "training_split_name": comparison_protocol.training_split_name,
            "checkpoint_selection_split_name": comparison_protocol.checkpoint_selection_split_name,
            "comparison_split_name": comparison_protocol.comparison_split_name,
            "split_windows": [asdict(window) for window in comparison_protocol.split_windows],
        },
        "objective_profile_id": objective_profile.objective_profile_id,
        "objective_profile": {
            "description": objective_profile.description,
            "weights": objective_profile.weight_map(),
        },
        "reward_profile_id": reward_profile.reward_profile_id,
        "reward_profile": {
            "description": reward_profile.description,
            "formula": reward_profile.formula_label(),
            "spearman_weight": reward_profile.spearman_weight,
            "mse_weight": reward_profile.mse_weight,
        },
        "training_method_id": training_method.training_method_id,
        "training_method": {
            "description": training_method.description,
            "sampling_mode": training_method.sampling_mode,
        },
        "input_feature_set_id": setup.input_feature_set_id,
        "input_feature_columns": list(feature_columns),
        "checkpoint_provenance": setup.checkpoint_provenance,
        "base_framework_id": setup.base_framework_id,
        "framework_id": framework.framework_id,
        "feature_profile_id": feature_profile.feature_profile_id,
        "change_type": setup.change_type,
        "changed_feature": setup.changed_feature,
        "variant_id": setup.variant_id,
        "feature_profile": {
            "description": feature_profile.description,
            "parameters": feature_profile.parameter_values() | setup.feature_profile_parameters,
        },
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
            "daily_fusion_mode": framework.daily_fusion_mode,
            "daily_path_scope": framework.daily_path_scope,
            "daily_channel_names": list(framework.daily_channel_names),
        },
        "policy_class": "MaskedActorCriticPolicy",
        "panel_path": str(
            (
                Path(panel_path)
                if panel_path is not None
                else ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME
            ).resolve()
        ),
        "daily_path": str(
            (
                Path(daily_path)
                if daily_path is not None
                else ROOT / config.READY_DATA_DIR / config.DAILY_MARKET_SERIES_NAME
            ).resolve()
        ),
        "artifacts_dir": str(setup_output_dir.resolve()),
        "best_model_path": str(best_model_path.resolve()),
        "final_model_path": str(final_model_path.resolve()),
        "reported_checkpoint": str(reported_checkpoint.resolve()),
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
        feature_profile=feature_profile,
        comparison_protocol=comparison_protocol,
        objective_profile=objective_profile,
        reward_profile=reward_profile,
        training_method=training_method,
        feature_columns=feature_columns,
        split_summary=split_summary,
        predictions=predictions,
        setup_output_dir=setup_output_dir,
        reported_checkpoint=reported_checkpoint,
    )
    append_setup_summary(setup_output_dir.parent, summary_row)
    with (setup_output_dir / "setup_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary_row, handle, indent=2, sort_keys=True)
    return setup_output_dir


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a monthly PPO ranking model for the framework or feature phase.")
    parser.add_argument("--setup-id", required=True, help="Unique identifier for this experiment run.")
    parser.add_argument("--framework-id", required=True, help="Framework identifier from the active registry.")
    parser.add_argument(
        "--panel-path",
        default=str(ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME),
        help="Monthly state panel path.",
    )
    parser.add_argument(
        "--daily-path",
        default=str(ROOT / config.READY_DATA_DIR / config.DAILY_MARKET_SERIES_NAME),
        help="Daily market series path.",
    )
    parser.add_argument("--total-timesteps", type=int, required=True, help="Total PPO timesteps.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument(
        "--study-phase",
        default=config.FRAMEWORK_PHASE_NAME,
        choices=[config.FRAMEWORK_PHASE_NAME, config.FEATURE_PHASE_NAME],
        help="Experiment phase label for metadata and summary rows.",
    )
    parser.add_argument(
        "--base-framework-id",
        default="",
        help="Locked backbone framework for the run. Feature-phase runs default to pit_3m_flat_context.",
    )
    parser.add_argument(
        "--feature-profile-id",
        default=config.DEFAULT_FEATURE_PROFILE_ID,
        help="Feature profile identifier used to build the input panel.",
    )
    parser.add_argument(
        "--comparison-protocol-id",
        default=config.DEFAULT_COMPARISON_PROTOCOL_ID,
        help="Comparison protocol identifier.",
    )
    parser.add_argument(
        "--objective-profile-id",
        default=config.DEFAULT_OBJECTIVE_PROFILE_ID,
        help="Objective profile identifier.",
    )
    parser.add_argument(
        "--reward-profile-id",
        default=config.DEFAULT_REWARD_PROFILE_ID,
        help="Reward profile identifier.",
    )
    parser.add_argument(
        "--training-method-id",
        default=config.DEFAULT_TRAINING_METHOD_ID,
        help="Training sampling method identifier.",
    )
    parser.add_argument(
        "--input-feature-set-id",
        default=config.DEFAULT_INPUT_FEATURE_SET_ID,
        help="Input feature set identifier.",
    )
    parser.add_argument("--change-type", default="none", help="Experiment change type, e.g. drop_feature or alter_feature.")
    parser.add_argument("--changed-feature", default="", help="Canonical feature name affected by this run.")
    parser.add_argument("--variant-id", default="", help="Variant identifier inside the feature family.")
    parser.add_argument("--notes", default="", help="Optional free-form run note recorded in metadata.")
    return parser


def main() -> None:
    parser = _build_cli_parser()
    args = parser.parse_args()
    setup = SetupConfig(
        setup_id=args.setup_id,
        framework_id=args.framework_id,
        total_timesteps=args.total_timesteps,
        study_phase=args.study_phase,
        base_framework_id=args.base_framework_id,
        feature_profile_id=args.feature_profile_id,
        comparison_protocol_id=args.comparison_protocol_id,
        objective_profile_id=args.objective_profile_id,
        reward_profile_id=args.reward_profile_id,
        training_method_id=args.training_method_id,
        input_feature_set_id=args.input_feature_set_id,
        change_type=args.change_type,
        changed_feature=args.changed_feature,
        variant_id=args.variant_id,
        notes=args.notes,
        seed=args.seed,
    )
    output_dir = train_setup(panel_path=args.panel_path, daily_path=args.daily_path, setup=setup)
    print(f"Training complete: {output_dir}")


if __name__ == "__main__":
    main()
