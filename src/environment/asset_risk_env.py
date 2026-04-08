"""Gymnasium environment for month-level RL risk scoring over the canonical panel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from src import config
from src.training.metrics import compute_month_metrics
from src.training.panel_utils import MonthlyBatch, build_monthly_batches, load_canonical_monthly_panel


class AssetRiskEnv(gym.Env):
    """Single-month episode environment over the canonical monthly panel.

    Training uses random month sampling from the train split. Validation and
    test use deterministic ordered month traversal via repeated resets.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        panel_path: str | Path | None = None,
        split_name: str = "train",
        sampling_mode: str | None = None,
    ) -> None:
        super().__init__()
        self.panel = load_canonical_monthly_panel(panel_path)
        self.max_assets = int(self.panel.groupby("Date")["AssetID"].nunique().max())
        self.feature_count = len(config.MODEL_FEATURE_COLUMNS)
        self.observation_space = spaces.Dict(
            {
                "features": spaces.Box(
                    low=0.0,
                    high=1.0,
                    shape=(self.max_assets, self.feature_count),
                    dtype=np.float32,
                ),
                "mask": spaces.Box(low=0.0, high=1.0, shape=(self.max_assets,), dtype=np.float32),
            }
        )
        self.action_space = spaces.Box(low=0.0, high=1.0, shape=(self.max_assets,), dtype=np.float32)

        self._split_name = split_name
        self._sampling_mode = sampling_mode or self._default_sampling_mode(split_name)
        self._batches = build_monthly_batches(self.panel, split_name=split_name)
        self._current_batch: MonthlyBatch | None = None
        self._ordered_cursor = 0

    @staticmethod
    def _default_sampling_mode(split_name: str) -> str:
        return "random" if split_name == "train" else "ordered"

    @property
    def batch_count(self) -> int:
        return len(self._batches)

    @property
    def split_name(self) -> str:
        return self._split_name

    def available_dates(self) -> list[str]:
        return [batch.date for batch in self._batches]

    def _select_batch(self, restart_sequence: bool = False) -> MonthlyBatch:
        if self._sampling_mode == "random":
            index = int(self.np_random.integers(len(self._batches)))
            return self._batches[index]

        if restart_sequence:
            self._ordered_cursor = 0
        batch = self._batches[self._ordered_cursor]
        self._ordered_cursor = (self._ordered_cursor + 1) % len(self._batches)
        return batch

    def _zero_observation(self) -> dict[str, np.ndarray]:
        return {
            "features": np.zeros((self.max_assets, self.feature_count), dtype=np.float32),
            "mask": np.zeros((self.max_assets,), dtype=np.float32),
        }

    def _observation_from_batch(self, batch: MonthlyBatch) -> dict[str, np.ndarray]:
        features = np.zeros((self.max_assets, self.feature_count), dtype=np.float32)
        mask = np.zeros((self.max_assets,), dtype=np.float32)
        active_count = batch.active_asset_count
        features[:active_count, :] = batch.features
        mask[:active_count] = 1.0
        return {"features": features, "mask": mask}

    def _info_from_batch(self, batch: MonthlyBatch) -> dict[str, Any]:
        return {
            "Date": batch.date,
            "Split": batch.split,
            "SamplingMode": self._sampling_mode,
            "ActiveAssetCount": batch.active_asset_count,
            "AssetIDs": list(batch.asset_ids),
            "AssetNames": list(batch.asset_names),
            "AssetGroups": list(batch.asset_groups),
        }

    def set_split(self, split_name: str, sampling_mode: str | None = None) -> None:
        self._split_name = split_name
        self._sampling_mode = sampling_mode or self._default_sampling_mode(split_name)
        self._batches = build_monthly_batches(self.panel, split_name=split_name)
        self._ordered_cursor = 0
        self._current_batch = None

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
        super().reset(seed=seed)
        options = options or {}

        requested_split = options.get("split_name")
        requested_sampling = options.get("sampling_mode")
        if requested_split is not None or requested_sampling is not None:
            next_split = str(requested_split) if requested_split is not None else self._split_name
            next_sampling = str(requested_sampling) if requested_sampling is not None else self._sampling_mode
            self.set_split(next_split, sampling_mode=next_sampling)

        restart_sequence = bool(options.get("restart_sequence", False))
        self._current_batch = self._select_batch(restart_sequence=restart_sequence)
        return self._observation_from_batch(self._current_batch), self._info_from_batch(self._current_batch)

    def step(
        self,
        action: np.ndarray,
    ) -> tuple[dict[str, np.ndarray], float, bool, bool, dict[str, Any]]:
        if self._current_batch is None:
            raise RuntimeError("reset() must be called before step().")

        batch = self._current_batch
        action_values = np.asarray(action, dtype=np.float32).reshape(-1)
        if action_values.shape[0] != self.max_assets:
            raise ValueError(f"Expected action shape ({self.max_assets},) but received {action_values.shape}.")

        clipped_actions = np.clip(action_values, 0.0, 1.0)
        active_scores = clipped_actions[: batch.active_asset_count]
        metrics = compute_month_metrics(active_scores, batch.targets, batch.date)
        info = self._info_from_batch(batch) | {
            "Spearman": metrics.spearman,
            "MSE": metrics.mse,
            "Reward": metrics.reward,
            "PredictedRisk": active_scores.tolist(),
            "RealizedRisk": batch.targets.tolist(),
        }
        self._current_batch = None
        return self._zero_observation(), metrics.reward, True, False, info
