"""Training callbacks for PPO monthly-panel experiments."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

from src.training.evaluate import evaluate_model_splits


class ValidationEvaluationCallback(BaseCallback):
    """Periodically evaluate PPO on the ordered validation split."""

    def __init__(
        self,
        panel_path: str | Path | None,
        output_dir: str | Path,
        eval_frequency: int,
        verbose: int = 0,
    ) -> None:
        super().__init__(verbose=verbose)
        self.panel_path = panel_path
        self.output_dir = Path(output_dir)
        self.eval_frequency = int(eval_frequency)
        self.history: list[dict[str, Any]] = []
        self.best_mean_reward = float("-inf")
        self.best_summary: dict[str, Any] | None = None
        self.best_model_path = self.output_dir / "best_model.zip"

    def _record_validation_metrics(self, timesteps: int) -> dict[str, Any]:
        if not isinstance(self.model, PPO):
            raise TypeError("ValidationEvaluationCallback expects a PPO model.")

        _, _, split_summary = evaluate_model_splits(
            model=self.model,
            panel_path=self.panel_path,
            split_names=("validation",),
        )
        summary = split_summary.iloc[0].to_dict()
        record = {
            "timesteps": int(timesteps),
            "split": "validation",
            "months": int(summary["months"]),
            "mean_active_assets": float(summary["mean_active_assets"]),
            "mean_spearman": float(summary["mean_spearman"]),
            "mean_mse": float(summary["mean_mse"]),
            "mean_reward": float(summary["mean_reward"]),
            "total_reward": float(summary["total_reward"]),
        }
        self.history.append(record)
        if record["mean_reward"] > self.best_mean_reward:
            self.best_mean_reward = record["mean_reward"]
            self.best_summary = record
            self.best_model_path.parent.mkdir(parents=True, exist_ok=True)
            self.model.save(self.best_model_path)
        return record

    def evaluate_now(self, timesteps: int | None = None) -> dict[str, Any]:
        effective_timesteps = int(self.num_timesteps if timesteps is None else timesteps)
        return self._record_validation_metrics(effective_timesteps)

    def training_metrics_frame(self) -> pd.DataFrame:
        return pd.DataFrame.from_records(self.history)

    def _on_step(self) -> bool:
        if self.eval_frequency <= 0:
            return True
        if self.num_timesteps % self.eval_frequency == 0:
            self._record_validation_metrics(self.num_timesteps)
        return True

    def _on_training_end(self) -> None:
        if not self.history or self.history[-1]["timesteps"] != int(self.num_timesteps):
            self._record_validation_metrics(int(self.num_timesteps))
