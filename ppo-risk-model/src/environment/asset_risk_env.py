"""Gymnasium environment for month-level RL risk scoring."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from src import config
from src.training.frameworks import get_runtime_framework_spec
from src.training.metrics import compute_month_metrics
from src.training.panel_utils import (
    DecisionBatch,
    build_framework_batches,
    load_canonical_daily_market_series,
    load_monthly_panel,
)


class AssetRiskEnv(gym.Env):
    """Single-month episode environment over point-in-time monthly state rows."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        panel_path: str | Path | None = None,
        daily_path: str | Path | None = None,
        split_name: str = "train",
        framework_id: str = "pit_1m_shared_mlp",
        sampling_mode: str | None = None,
        comparison_protocol_id: str = config.DEFAULT_COMPARISON_PROTOCOL_ID,
        objective_profile_id: str = config.DEFAULT_OBJECTIVE_PROFILE_ID,
        reward_profile_id: str = config.DEFAULT_REWARD_PROFILE_ID,
        feature_columns: tuple[str, ...] | list[str] | None = None,
    ) -> None:
        super().__init__()
        self._feature_columns = tuple(config.MODEL_FEATURE_COLUMNS if feature_columns is None else feature_columns)
        self.panel = load_monthly_panel(
            panel_path,
            feature_columns=self._feature_columns,
            allow_extra_columns=tuple(self._feature_columns) != tuple(config.MODEL_FEATURE_COLUMNS),
        )
        self.framework = get_runtime_framework_spec(framework_id, feature_count=len(self._feature_columns))
        self.daily_market_series = (
            load_canonical_daily_market_series(daily_path) if self.framework.uses_daily_strip else None
        )
        self.max_assets = int(self.panel.groupby("Date")["AssetID"].nunique().max())
        self.feature_count = self.framework.monthly_feature_dim
        observation_spaces: dict[str, spaces.Space] = {
            "features": spaces.Box(
                low=-np.inf,
                high=np.inf,
                shape=(self.max_assets, self.feature_count),
                dtype=np.float32,
            ),
            "mask": spaces.Box(low=0.0, high=1.0, shape=(self.max_assets,), dtype=np.float32),
        }
        if self.framework.uses_daily_strip:
            observation_spaces["daily_strip"] = spaces.Box(
                low=-np.inf,
                high=np.inf,
                shape=(self.max_assets, self.framework.daily_strip_length, self.framework.daily_strip_channels),
                dtype=np.float32,
            )
            observation_spaces["daily_mask"] = spaces.Box(
                low=0.0,
                high=1.0,
                shape=(self.max_assets, self.framework.daily_strip_length),
                dtype=np.float32,
            )
        self.observation_space = spaces.Dict(observation_spaces)
        self.action_space = spaces.Box(low=0.0, high=1.0, shape=(self.max_assets,), dtype=np.float32)

        self._framework_id = framework_id
        self._split_name = split_name
        self._comparison_protocol_id = comparison_protocol_id
        self._objective_profile_id = objective_profile_id
        self._reward_profile_id = reward_profile_id
        self._sampling_mode = sampling_mode or self._default_sampling_mode(split_name)
        self._batches = build_framework_batches(
            self.panel,
            framework_id=framework_id,
            split_name=split_name,
            daily_market_series=self.daily_market_series,
            comparison_protocol_id=self._comparison_protocol_id,
            feature_columns=self._feature_columns,
            objective_profile_id=self._objective_profile_id,
        )
        self._current_batch: DecisionBatch | None = None
        self._ordered_cursor = 0
        self._block_cursor = 0
        self._active_block_indices: list[int] | None = None

    @staticmethod
    def _default_sampling_mode(split_name: str) -> str:
        return "ordered_cycle"

    @property
    def batch_count(self) -> int:
        return len(self._batches)

    @property
    def framework_id(self) -> str:
        return self._framework_id

    @property
    def split_name(self) -> str:
        return self._split_name

    def available_dates(self) -> list[str]:
        return [batch.date for batch in self._batches]

    def _select_batch(self, restart_sequence: bool = False) -> DecisionBatch:
        if self._sampling_mode in {"random", "random_iid"}:
            index = int(self.np_random.integers(len(self._batches)))
            return self._batches[index]

        if self._sampling_mode == "block_random_6m":
            if restart_sequence:
                self._active_block_indices = None
                self._block_cursor = 0
            if self._active_block_indices is None or self._block_cursor >= len(self._active_block_indices):
                block_length = min(6, len(self._batches))
                max_start = max(0, len(self._batches) - block_length)
                start = int(self.np_random.integers(max_start + 1)) if max_start > 0 else 0
                self._active_block_indices = list(range(start, start + block_length))
                self._block_cursor = 0
            batch = self._batches[self._active_block_indices[self._block_cursor]]
            self._block_cursor += 1
            return batch

        if restart_sequence:
            self._ordered_cursor = 0
        batch = self._batches[self._ordered_cursor]
        self._ordered_cursor = (self._ordered_cursor + 1) % len(self._batches)
        return batch

    def _zero_observation(self) -> dict[str, np.ndarray]:
        observation = {
            "features": np.zeros((self.max_assets, self.feature_count), dtype=np.float32),
            "mask": np.zeros((self.max_assets,), dtype=np.float32),
        }
        if self.framework.uses_daily_strip:
            observation["daily_strip"] = np.zeros(
                (self.max_assets, self.framework.daily_strip_length, self.framework.daily_strip_channels),
                dtype=np.float32,
            )
            observation["daily_mask"] = np.zeros((self.max_assets, self.framework.daily_strip_length), dtype=np.float32)
        return observation

    def _observation_from_batch(self, batch: DecisionBatch) -> dict[str, np.ndarray]:
        features = np.zeros((self.max_assets, self.feature_count), dtype=np.float32)
        mask = np.zeros((self.max_assets,), dtype=np.float32)
        active_count = batch.active_asset_count
        features[:active_count, :] = batch.features
        mask[:active_count] = 1.0
        observation = {"features": features, "mask": mask}
        if self.framework.uses_daily_strip:
            daily_strip = np.zeros(
                (self.max_assets, self.framework.daily_strip_length, self.framework.daily_strip_channels),
                dtype=np.float32,
            )
            daily_mask = np.zeros((self.max_assets, self.framework.daily_strip_length), dtype=np.float32)
            if batch.daily_strip is None or batch.daily_mask is None:
                raise ValueError("Daily-strip framework expected daily_strip and daily_mask batch tensors.")
            daily_strip[:active_count, :, :] = batch.daily_strip
            daily_mask[:active_count, :] = batch.daily_mask
            observation["daily_strip"] = daily_strip
            observation["daily_mask"] = daily_mask
        return observation

    def _info_from_batch(self, batch: DecisionBatch) -> dict[str, Any]:
        return {
            "Date": batch.date,
            "Split": batch.split,
            "FrameworkID": batch.framework_id,
            "StateMonths": list(batch.state_months),
            "SamplingMode": self._sampling_mode,
            "ComparisonProtocolID": self._comparison_protocol_id,
            "ObjectiveProfileID": self._objective_profile_id,
            "RewardProfileID": self._reward_profile_id,
            "ActiveAssetCount": batch.active_asset_count,
            "AssetIDs": list(batch.asset_ids),
            "AssetNames": list(batch.asset_names),
            "AssetGroups": list(batch.asset_groups),
        }

    def set_split(self, split_name: str, sampling_mode: str | None = None) -> None:
        self._split_name = split_name
        self._sampling_mode = sampling_mode or self._default_sampling_mode(split_name)
        self._batches = build_framework_batches(
            self.panel,
            framework_id=self._framework_id,
            split_name=split_name,
            daily_market_series=self.daily_market_series,
            comparison_protocol_id=self._comparison_protocol_id,
            feature_columns=self._feature_columns,
            objective_profile_id=self._objective_profile_id,
        )
        self._ordered_cursor = 0
        self._block_cursor = 0
        self._active_block_indices = None
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
        metrics = compute_month_metrics(
            active_scores,
            batch.targets,
            batch.date,
            reward_profile=self._reward_profile_id,
        )
        info = self._info_from_batch(batch) | {
            "Spearman": metrics.spearman,
            "MSE": metrics.mse,
            "HighRiskTop25Overlap": metrics.high_risk_top25_overlap,
            "LowRiskTop25Overlap": metrics.low_risk_top25_overlap,
            "Reward": metrics.reward,
            "PredictedRisk": active_scores.tolist(),
            "RealizedRisk": batch.targets.tolist(),
        }
        self._current_batch = None
        return self._zero_observation(), metrics.reward, True, False, info
