"""Fixed-config PPO confirmation runs for tuning candidates."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config
from src.training.train import SetupConfig, train_setup


DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / "generated" / "runs" / "ppo_tuning" / "confirmations"
DEFAULT_PANEL_PATH = ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME
DEFAULT_DAILY_PATH = ROOT / config.READY_DATA_DIR / config.DAILY_MARKET_SERIES_NAME

TUNED_CANDIDATES: dict[str, dict[str, float | int]] = {
    "trial75": {
        "learning_rate": 0.00038063905891585874,
        "n_steps": 256,
        "batch_size": 256,
        "n_epochs": 5,
        "clip_range": 0.22585671531571716,
        "ent_coef": 0.005342404415844881,
        "vf_coef": 0.9964247493812112,
        "max_grad_norm": 0.3,
    },
    "trial11": {
        "learning_rate": 0.00045512661571830743,
        "n_steps": 512,
        "batch_size": 128,
        "n_epochs": 20,
        "clip_range": 0.17531493778149573,
        "ent_coef": 0.0037017722546991397,
        "vf_coef": 0.9736515663927596,
        "max_grad_norm": 0.5,
    },
    "refined50": {
        "learning_rate": 0.00024935310281972535,
        "n_steps": 256,
        "batch_size": 256,
        "n_epochs": 10,
        "clip_range": 0.2990122587129351,
        "ent_coef": 0.0023477909057284673,
        "vf_coef": 0.9023537822799527,
        "max_grad_norm": 0.3,
    },
}

GAMMA_GAE_PAIRS: dict[str, tuple[float, float]] = {
    "gamma099_gae095": (0.99, 0.95),
    "gamma0995_gae097": (0.995, 0.97),
    "gamma100_gae095": (1.0, 0.95),
}


@dataclass(frozen=True)
class FixedRun:
    run_id: str
    params: dict[str, float | int]
    seed: int
    total_timesteps: int = 32768
    gamma: float = 1.0
    gae_lambda: float = 1.0
    output_root: str = str(DEFAULT_OUTPUT_ROOT)
    panel_path: str = str(DEFAULT_PANEL_PATH)
    daily_path: str = str(DEFAULT_DAILY_PATH)

    def setup_id(self) -> str:
        return f"PPO-CONFIRM-{self.run_id.upper()}-S{self.seed}"


def run_fixed_config(run: FixedRun) -> Path:
    setup = SetupConfig(
        setup_id=run.setup_id(),
        framework_id=config.FEATURE_PHASE_BASE_FRAMEWORK_ID,
        total_timesteps=run.total_timesteps,
        study_phase=config.FEATURE_PHASE_NAME,
        base_framework_id=config.FEATURE_PHASE_BASE_FRAMEWORK_ID,
        feature_profile_id=config.DEFAULT_FEATURE_PROFILE_ID,
        comparison_protocol_id=config.DEFAULT_COMPARISON_PROTOCOL_ID,
        objective_profile_id=config.DEFAULT_OBJECTIVE_PROFILE_ID,
        reward_profile_id=config.DEFAULT_REWARD_PROFILE_ID,
        training_method_id=config.DEFAULT_TRAINING_METHOD_ID,
        input_feature_set_id=config.DEFAULT_INPUT_FEATURE_SET_ID,
        seed=run.seed,
        gamma=run.gamma,
        gae_lambda=run.gae_lambda,
        notes=f"ppo_tuning_fixed_config_{run.run_id}",
        **run.params,
    )
    return train_setup(
        panel_path=run.panel_path,
        daily_path=run.daily_path,
        setup=setup,
        output_root=Path(run.output_root) / run.run_id,
    )


def _load_summary(setup_dir: Path) -> dict[str, Any]:
    with (setup_dir / "setup_summary.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _print_summary(summary: dict[str, Any]) -> None:
    print(
        json.dumps(
            {
                "SetupID": summary["SetupID"],
                "ValidationMeanReward": summary["ValidationMeanReward"],
                "ValidationMeanSpearman": summary["ValidationMeanSpearman"],
                "ValidationMeanMSE": summary["ValidationMeanMSE"],
                "TestMeanReward": summary["TestMeanReward"],
                "TestMeanSpearman": summary["TestMeanSpearman"],
                "Gamma": summary["Gamma"],
                "GaeLambda": summary["GaeLambda"],
                "ArtifactsDir": summary["ArtifactsDir"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def candidate_params(candidate: str) -> dict[str, float | int]:
    try:
        return dict(TUNED_CANDIDATES[candidate])
    except KeyError as exc:
        raise ValueError(f"Unknown candidate: {candidate}") from exc


def run_candidate_confirmations(
    candidates: list[str],
    seeds: list[int],
    total_timesteps: int,
    output_root: str,
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for candidate in candidates:
        for seed in seeds:
            setup_dir = run_fixed_config(
                FixedRun(
                    run_id=candidate,
                    params=candidate_params(candidate),
                    seed=seed,
                    total_timesteps=total_timesteps,
                    output_root=output_root,
                )
            )
            summary = _load_summary(setup_dir)
            _print_summary(summary)
            summaries.append(summary)
    return summaries


def run_gamma_gae_checks(
    champion: str,
    seed: int,
    total_timesteps: int,
    output_root: str,
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    base_params = candidate_params(champion)
    for pair_id, (gamma, gae_lambda) in GAMMA_GAE_PAIRS.items():
        setup_dir = run_fixed_config(
            FixedRun(
                run_id=f"{champion}_{pair_id}",
                params=base_params,
                seed=seed,
                total_timesteps=total_timesteps,
                gamma=gamma,
                gae_lambda=gae_lambda,
                output_root=output_root,
            )
        )
        summary = _load_summary(setup_dir)
        _print_summary(summary)
        summaries.append(summary)
    return summaries


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run fixed PPO tuning confirmations.")
    parser.add_argument("--mode", choices=["confirm", "gamma-gae"], default="confirm")
    parser.add_argument("--candidates", nargs="+", default=["trial75", "trial11"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[7, 13])
    parser.add_argument("--champion", default="trial75")
    parser.add_argument("--total-timesteps", type=int, default=32768)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if args.mode == "confirm":
        run_candidate_confirmations(
            candidates=args.candidates,
            seeds=args.seeds,
            total_timesteps=args.total_timesteps,
            output_root=args.output_root,
        )
        return
    run_gamma_gae_checks(
        champion=args.champion,
        seed=args.seeds[0],
        total_timesteps=args.total_timesteps,
        output_root=args.output_root,
    )


if __name__ == "__main__":
    main()
