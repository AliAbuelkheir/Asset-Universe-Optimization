"""Evaluate PPO checkpoints against the canonical monthly panel."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from stable_baselines3 import PPO

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config
from src.environment.asset_risk_env import AssetRiskEnv
from src.training.metrics import PREDICTION_COLUMN, add_prediction_ranks, evaluate_prediction_frame
from src.training.policy import MaskedActorCriticPolicy


def evaluate_model_split(
    model: PPO,
    panel_path: str | Path | None,
    daily_path: str | Path | None,
    framework_id: str,
    split_name: str,
) -> pd.DataFrame:
    env = AssetRiskEnv(
        panel_path=panel_path,
        daily_path=daily_path,
        split_name=split_name,
        framework_id=framework_id,
        sampling_mode="ordered",
    )
    prediction_rows: list[dict[str, Any]] = []
    observation, _ = env.reset(options={"restart_sequence": True})
    for batch_index in range(env.batch_count):
        actions, _ = model.predict(observation, deterministic=True)
        _, _, _, _, info = env.step(actions)
        for asset_id, asset_name, asset_group, realized_risk, predicted_risk in zip(
            info["AssetIDs"],
            info["AssetNames"],
            info["AssetGroups"],
            info["RealizedRisk"],
            info["PredictedRisk"],
        ):
            prediction_rows.append(
                {
                    "Date": info["Date"],
                    "Split": info["Split"],
                    "AssetID": asset_id,
                    "AssetName": asset_name,
                    "AssetGroup": asset_group,
                    "realized_risk": float(realized_risk),
                    PREDICTION_COLUMN: float(predicted_risk),
                }
            )
        if batch_index < env.batch_count - 1:
            observation, _ = env.reset()
    predictions = pd.DataFrame.from_records(prediction_rows)
    predictions["realized_rank"] = predictions.groupby("Date")["realized_risk"].rank(method="average", ascending=True)
    return predictions


def evaluate_model_splits(
    model: PPO,
    panel_path: str | Path | None,
    daily_path: str | Path | None,
    framework_id: str,
    split_names: Iterable[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prediction_frames = [
        evaluate_model_split(
            model=model,
            panel_path=panel_path,
            daily_path=daily_path,
            framework_id=framework_id,
            split_name=split_name,
        )
        for split_name in split_names
    ]
    predictions = pd.concat(prediction_frames, ignore_index=True)
    predictions = add_prediction_ranks(predictions, score_column=PREDICTION_COLUMN)
    monthly_metrics, split_summary = evaluate_prediction_frame(predictions, score_column=PREDICTION_COLUMN)
    return predictions, monthly_metrics, split_summary


def write_evaluation_artifacts(
    output_dir: str | Path,
    predictions: pd.DataFrame,
    monthly_metrics: pd.DataFrame,
    split_summary: pd.DataFrame,
    setup_metadata: dict[str, Any],
) -> Path:
    resolved_output_dir = Path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    predictions.to_csv(resolved_output_dir / "ranked_predictions.csv", index=False)
    monthly_metrics.to_csv(resolved_output_dir / "monthly_metrics.csv", index=False)
    split_summary.to_csv(resolved_output_dir / "split_summary.csv", index=False)
    with (resolved_output_dir / "setup_metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(setup_metadata, handle, indent=2, sort_keys=True)
    return resolved_output_dir


def load_ppo_checkpoint(checkpoint_path: str | Path) -> PPO:
    resolved_path = Path(checkpoint_path)
    load_path = resolved_path
    if resolved_path.suffix == ".zip" and resolved_path.exists():
        load_path = resolved_path.with_suffix("")
    return PPO.load(str(load_path), custom_objects={"policy_class": MaskedActorCriticPolicy})


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate a PPO checkpoint against the canonical monthly panel.")
    parser.add_argument("--checkpoint-path", required=True, help="Saved PPO checkpoint (`best_model.zip` or `final_model.zip`).")
    parser.add_argument(
        "--panel-path",
        default=str(ROOT / config.READY_DATA_DIR / config.MONTHLY_PANEL_NAME),
        help="Canonical monthly panel path.",
    )
    parser.add_argument(
        "--split-name",
        default="all",
        choices=["all", "train", "validation", "test"],
        help="Which split to score.",
    )
    parser.add_argument("--framework-id", required=True, help="Framework identifier used by the checkpoint.")
    parser.add_argument("--output-dir", required=True, help="Directory where evaluation artifacts should be written.")
    return parser


def main() -> None:
    parser = _build_cli_parser()
    args = parser.parse_args()

    split_names = ["train", "validation", "test"] if args.split_name == "all" else [args.split_name]
    model = load_ppo_checkpoint(args.checkpoint_path)
    predictions, monthly_metrics, split_summary = evaluate_model_splits(
        model=model,
        panel_path=args.panel_path,
        daily_path=None,
        framework_id=args.framework_id,
        split_names=split_names,
    )
    setup_metadata = {
        "checkpoint_path": str(Path(args.checkpoint_path).resolve()),
        "panel_path": str(Path(args.panel_path).resolve()),
        "framework_id": args.framework_id,
        "split_name": args.split_name,
    }
    write_evaluation_artifacts(
        output_dir=args.output_dir,
        predictions=predictions,
        monthly_metrics=monthly_metrics,
        split_summary=split_summary,
        setup_metadata=setup_metadata,
    )

    print("Evaluation complete")
    print(split_summary.to_string(index=False))


if __name__ == "__main__":
    main()
