"""Optuna-ready PPO tuning launcher.

This module is intentionally inert unless called with ``--execute``. It exists
so the PPO tuning phase can start from one command after the feature set is
locked, without changing training code at that point.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config
from src.training.train import SetupConfig, train_setup


DEFAULT_STUDY_NAME = "ppo_full_run_after_feature_lock"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / "generated" / "runs" / "ppo_tuning"
DEFAULT_STORAGE_PATH = DEFAULT_OUTPUT_ROOT / "optuna_studies.sqlite3"
SEARCH_SPACE_BROAD = "broad"
SEARCH_SPACE_REFINED = "refined"


@dataclass(frozen=True)
class TuningPlan:
    study_name: str = DEFAULT_STUDY_NAME
    n_trials: int = 80
    total_timesteps: int = 32768
    framework_id: str = config.FEATURE_PHASE_BASE_FRAMEWORK_ID
    feature_profile_id: str = config.DEFAULT_FEATURE_PROFILE_ID
    input_feature_set_id: str = config.DEFAULT_INPUT_FEATURE_SET_ID
    comparison_protocol_id: str = config.DEFAULT_COMPARISON_PROTOCOL_ID
    objective_profile_id: str = config.DEFAULT_OBJECTIVE_PROFILE_ID
    reward_profile_id: str = config.DEFAULT_REWARD_PROFILE_ID
    training_method_id: str = config.DEFAULT_TRAINING_METHOD_ID
    seed: int = 42
    panel_path: str = str(ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME)
    daily_path: str = str(ROOT / config.READY_DATA_DIR / config.DAILY_MARKET_SERIES_NAME)
    output_root: str = str(DEFAULT_OUTPUT_ROOT)
    storage_path: str = str(DEFAULT_STORAGE_PATH)
    search_space: str = SEARCH_SPACE_BROAD

    def storage_url(self) -> str:
        return f"sqlite:///{Path(self.storage_path).resolve().as_posix()}"


def _timestamp_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _trial_setup_id(study_name: str, trial_number: int, seed: int) -> str:
    return f"PPO-OPTUNA-{study_name.upper()}-T{trial_number:04d}-S{seed}"


def _compatible_batch_sizes(n_steps: int) -> list[int]:
    return [batch_size for batch_size in [128, 256, 512] if n_steps % batch_size == 0]


def _parse_rollout_batch_combo(combo: str) -> tuple[int, int]:
    n_steps_text, batch_size_text = combo.split("_", maxsplit=1)
    return int(n_steps_text), int(batch_size_text)


def sample_ppo_params(trial: Any, search_space: str = SEARCH_SPACE_BROAD) -> dict[str, float | int]:
    """Sample a PPO tuning space.

    ``gamma`` and ``gae_lambda`` stay fixed at 1.0 because this environment has
    one month-level reward per episode; they are deliberately left out of the
    automated tuning spaces.
    """

    if search_space == SEARCH_SPACE_REFINED:
        n_steps, batch_size = _parse_rollout_batch_combo(
            str(trial.suggest_categorical("rollout_batch", ["256_128", "256_256", "512_128", "512_256", "512_512"]))
        )
        return {
            "learning_rate": trial.suggest_float("learning_rate", 2e-4, 5e-4, log=True),
            "n_steps": n_steps,
            "batch_size": batch_size,
            "n_epochs": trial.suggest_categorical("n_epochs", [5, 10]),
            "clip_range": trial.suggest_float("clip_range", 0.18, 0.30),
            "ent_coef": trial.suggest_float("ent_coef", 0.002, 0.02, log=True),
            "vf_coef": trial.suggest_float("vf_coef", 0.60, 1.00),
            "max_grad_norm": trial.suggest_categorical("max_grad_norm", [0.3, 0.5]),
        }
    if search_space != SEARCH_SPACE_BROAD:
        raise ValueError(f"Unknown search_space: {search_space}")
    return {
        "learning_rate": trial.suggest_float("learning_rate", 1e-5, 5e-4, log=True),
        "n_steps": trial.suggest_categorical("n_steps", [128, 256, 512, 1024]),
        "batch_size": trial.suggest_categorical("batch_size", [128, 256, 512]),
        "n_epochs": trial.suggest_categorical("n_epochs", [5, 10, 15, 20]),
        "clip_range": trial.suggest_float("clip_range", 0.10, 0.30),
        "ent_coef": trial.suggest_float("ent_coef", 1e-4, 5e-2, log=True),
        "vf_coef": trial.suggest_float("vf_coef", 0.20, 1.00),
        "max_grad_norm": trial.suggest_categorical("max_grad_norm", [0.3, 0.5, 0.7, 1.0]),
    }


def _summary_metric(setup_dir: Path, metric_name: str) -> float:
    summary_path = setup_dir / "setup_summary.json"
    with summary_path.open("r", encoding="utf-8") as handle:
        summary = json.load(handle)
    value = summary.get(metric_name)
    if value is None:
        raise ValueError(f"Missing metric {metric_name} in {summary_path}")
    return float(value)


def objective_for_plan(plan: TuningPlan):
    def objective(trial: Any) -> float:
        params = sample_ppo_params(trial, search_space=plan.search_space)
        trial_output_root = Path(plan.output_root) / plan.study_name
        setup = SetupConfig(
            setup_id=_trial_setup_id(plan.study_name, int(trial.number), plan.seed),
            framework_id=plan.framework_id,
            total_timesteps=plan.total_timesteps,
            study_phase=config.FEATURE_PHASE_NAME,
            base_framework_id=plan.framework_id,
            feature_profile_id=plan.feature_profile_id,
            comparison_protocol_id=plan.comparison_protocol_id,
            objective_profile_id=plan.objective_profile_id,
            reward_profile_id=plan.reward_profile_id,
            training_method_id=plan.training_method_id,
            input_feature_set_id=plan.input_feature_set_id,
            seed=plan.seed,
            notes=f"optuna_ppo_{plan.search_space}_ordered_baseline",
            **params,
        )
        setup_dir = train_setup(
            panel_path=plan.panel_path,
            daily_path=plan.daily_path,
            setup=setup,
            output_root=trial_output_root,
        )
        validation_reward = _summary_metric(setup_dir, "ValidationMeanReward")
        trial.set_user_attr("ValidationMeanSpearman", _summary_metric(setup_dir, "ValidationMeanSpearman"))
        trial.set_user_attr("ValidationMeanMSE", _summary_metric(setup_dir, "ValidationMeanMSE"))
        trial.set_user_attr("ArtifactsDir", str(setup_dir.resolve()))
        return validation_reward

    return objective


def write_launch_plan(plan: TuningPlan) -> Path:
    output_root = Path(plan.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    plan_path = output_root / f"{plan.study_name}_launch_plan.json"
    with plan_path.open("w", encoding="utf-8") as handle:
        json.dump(asdict(plan) | {"storage_url": plan.storage_url()}, handle, indent=2, sort_keys=True)
    return plan_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare or execute Optuna PPO tuning after feature lock.")
    parser.add_argument("--execute", action="store_true", help="Actually start Optuna trials. Omit for dry-run setup only.")
    parser.add_argument("--study-name", default=DEFAULT_STUDY_NAME)
    parser.add_argument("--n-trials", type=int, default=80)
    parser.add_argument("--total-timesteps", type=int, default=32768)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--framework-id", default=config.FEATURE_PHASE_BASE_FRAMEWORK_ID)
    parser.add_argument("--feature-profile-id", default=config.DEFAULT_FEATURE_PROFILE_ID)
    parser.add_argument("--input-feature-set-id", default=config.DEFAULT_INPUT_FEATURE_SET_ID)
    parser.add_argument("--panel-path", default=str(ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME))
    parser.add_argument("--daily-path", default=str(ROOT / config.READY_DATA_DIR / config.DAILY_MARKET_SERIES_NAME))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--storage-path", default=str(DEFAULT_STORAGE_PATH))
    parser.add_argument(
        "--search-space",
        choices=[SEARCH_SPACE_BROAD, SEARCH_SPACE_REFINED],
        default=SEARCH_SPACE_BROAD,
        help="Optuna PPO parameter space.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    plan = TuningPlan(
        study_name=args.study_name,
        n_trials=args.n_trials,
        total_timesteps=args.total_timesteps,
        framework_id=args.framework_id,
        feature_profile_id=args.feature_profile_id,
        input_feature_set_id=args.input_feature_set_id,
        seed=args.seed,
        panel_path=args.panel_path,
        daily_path=args.daily_path,
        output_root=args.output_root,
        storage_path=args.storage_path,
        search_space=args.search_space,
    )
    plan_path = write_launch_plan(plan)
    print(f"PPO tuning launch plan written: {plan_path}")
    print("Dry run only. Add --execute to start trials.") if not args.execute else None
    if not args.execute:
        return

    import optuna

    study = optuna.create_study(
        study_name=plan.study_name,
        storage=plan.storage_url(),
        direction="maximize",
        load_if_exists=True,
    )
    print(f"Starting Optuna study {plan.study_name} at {_timestamp_label()}")
    study.optimize(objective_for_plan(plan), n_trials=plan.n_trials, catch=(Exception,))
    print(f"Best validation reward: {study.best_value:.6f}")
    print(f"Best params: {study.best_params}")


if __name__ == "__main__":
    main()
