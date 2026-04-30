"""Shared protocol, objective, reward, and training-method registries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from src import config


@dataclass(frozen=True)
class SplitWindow:
    name: str
    start: str
    end: str


@dataclass(frozen=True)
class ComparisonProtocol:
    comparison_protocol_id: str
    description: str
    split_windows: tuple[SplitWindow, ...]
    training_split_name: str = "train"
    comparison_split_name: str = "validation"
    checkpoint_selection_split_name: str = "inner_validation"

    def split_names(self) -> tuple[str, ...]:
        return tuple(window.name for window in self.split_windows)

    def has_split(self, split_name: str) -> bool:
        return any(window.name == split_name for window in self.split_windows)


@dataclass(frozen=True)
class ObjectiveProfile:
    objective_profile_id: str
    description: str
    realized_vol_weight: float
    realized_downside_weight: float
    realized_max_drawdown_weight: float

    def weight_map(self) -> dict[str, float]:
        return {
            "realized_vol": float(self.realized_vol_weight),
            "realized_downside_dev": float(self.realized_downside_weight),
            "realized_max_drawdown": float(self.realized_max_drawdown_weight),
        }

    def compute_realized_risk(self, frame: pd.DataFrame) -> pd.Series:
        return (
            (self.realized_vol_weight * frame["realized_vol"].astype(float))
            + (self.realized_downside_weight * frame["realized_downside_dev"].astype(float))
            + (self.realized_max_drawdown_weight * frame["realized_max_drawdown"].astype(float))
        )


@dataclass(frozen=True)
class RewardProfile:
    reward_profile_id: str
    description: str
    spearman_weight: float
    mse_weight: float

    def formula_label(self) -> str:
        return f"{self.spearman_weight:.2f}*spearman + {self.mse_weight:.2f}*(1-mse)"


@dataclass(frozen=True)
class TrainingMethod:
    training_method_id: str
    description: str
    sampling_mode: str


LEGACY_PROTOCOL = ComparisonProtocol(
    comparison_protocol_id=config.LEGACY_COMPARISON_PROTOCOL_ID,
    description="Legacy train/validation/test protocol without a separate inner-validation carveout.",
    split_windows=(
        SplitWindow("train", config.TRAIN_START, config.TRAIN_END),
        SplitWindow("validation", config.VAL_START, config.VAL_END),
        SplitWindow("test", config.TEST_START, config.TEST_END),
    ),
    training_split_name="train",
    comparison_split_name="validation",
    checkpoint_selection_split_name="validation",
)

REPAIRED_PROTOCOL = ComparisonProtocol(
    comparison_protocol_id=config.DEFAULT_COMPARISON_PROTOCOL_ID,
    description="Pre-PPO repaired protocol with 2022 carved out for inner validation and 2023-01 to 2025-02 retained for outer comparison.",
    split_windows=(
        SplitWindow("train", config.TRAIN_START, "2021-12"),
        SplitWindow("inner_validation", "2022-01", "2022-12"),
        SplitWindow("validation", config.VAL_START, config.VAL_END),
        SplitWindow("test", config.TEST_START, config.TEST_END),
    ),
    training_split_name="train",
    comparison_split_name="validation",
    checkpoint_selection_split_name="inner_validation",
)

COMPARISON_PROTOCOL_REGISTRY: dict[str, ComparisonProtocol] = {
    protocol.comparison_protocol_id: protocol
    for protocol in (LEGACY_PROTOCOL, REPAIRED_PROTOCOL)
}

OBJECTIVE_PROFILE_REGISTRY: dict[str, ObjectiveProfile] = {
    "risk_v1_equal_333": ObjectiveProfile(
        objective_profile_id="risk_v1_equal_333",
        description="Equal-weight realized risk target: 0.333 vol / 0.333 downside / 0.333 max drawdown.",
        realized_vol_weight=1 / 3,
        realized_downside_weight=1 / 3,
        realized_max_drawdown_weight=1 / 3,
    ),
    "risk_v2_downside_050": ObjectiveProfile(
        objective_profile_id="risk_v2_downside_050",
        description="Downside-heavy realized risk target: 0.25 vol / 0.50 downside / 0.25 max drawdown.",
        realized_vol_weight=0.25,
        realized_downside_weight=0.50,
        realized_max_drawdown_weight=0.25,
    ),
    "risk_v3_tail_040": ObjectiveProfile(
        objective_profile_id="risk_v3_tail_040",
        description="Tail-heavy realized risk target: 0.20 vol / 0.40 downside / 0.40 max drawdown.",
        realized_vol_weight=0.20,
        realized_downside_weight=0.40,
        realized_max_drawdown_weight=0.40,
    ),
    "risk_v4_vol_only": ObjectiveProfile(
        objective_profile_id="risk_v4_vol_only",
        description="Volatility-only realized risk target: 1.00 vol / 0.00 downside / 0.00 max drawdown.",
        realized_vol_weight=1.00,
        realized_downside_weight=0.00,
        realized_max_drawdown_weight=0.00,
    ),
    "risk_v5_downside_only": ObjectiveProfile(
        objective_profile_id="risk_v5_downside_only",
        description="Downside-only realized risk target: 0.00 vol / 1.00 downside / 0.00 max drawdown.",
        realized_vol_weight=0.00,
        realized_downside_weight=1.00,
        realized_max_drawdown_weight=0.00,
    ),
    "risk_v6_drawdown_only": ObjectiveProfile(
        objective_profile_id="risk_v6_drawdown_only",
        description="Drawdown-only realized risk target: 0.00 vol / 0.00 downside / 1.00 max drawdown.",
        realized_vol_weight=0.00,
        realized_downside_weight=0.00,
        realized_max_drawdown_weight=1.00,
    ),
    "risk_v7_downside_drawdown_5050": ObjectiveProfile(
        objective_profile_id="risk_v7_downside_drawdown_5050",
        description="Downside/drawdown realized risk target: 0.00 vol / 0.50 downside / 0.50 max drawdown.",
        realized_vol_weight=0.00,
        realized_downside_weight=0.50,
        realized_max_drawdown_weight=0.50,
    ),
}

REWARD_PROFILE_REGISTRY: dict[str, RewardProfile] = {
    "reward_v1_rank70_mse30": RewardProfile(
        reward_profile_id="reward_v1_rank70_mse30",
        description="Current reward mix: 70% Spearman / 30% (1 - MSE).",
        spearman_weight=0.70,
        mse_weight=0.30,
    ),
    "reward_v4_rank50_mse50": RewardProfile(
        reward_profile_id="reward_v4_rank50_mse50",
        description="Balanced reward mix: 50% Spearman / 50% (1 - MSE).",
        spearman_weight=0.50,
        mse_weight=0.50,
    ),
    "reward_v2_rank85_mse15": RewardProfile(
        reward_profile_id="reward_v2_rank85_mse15",
        description="Rank-heavier reward mix: 85% Spearman / 15% (1 - MSE).",
        spearman_weight=0.85,
        mse_weight=0.15,
    ),
    "reward_v3_rank100_mse00": RewardProfile(
        reward_profile_id="reward_v3_rank100_mse00",
        description="Pure ranking reward: 100% Spearman / 0% (1 - MSE).",
        spearman_weight=1.00,
        mse_weight=0.00,
    ),
}

TRAINING_METHOD_REGISTRY: dict[str, TrainingMethod] = {
    "random_iid": TrainingMethod(
        training_method_id="random_iid",
        description="Sample train months independently at random.",
        sampling_mode="random_iid",
    ),
    "ordered_cycle": TrainingMethod(
        training_method_id="ordered_cycle",
        description="Cycle through the train months in chronological order.",
        sampling_mode="ordered_cycle",
    ),
    "block_random_6m": TrainingMethod(
        training_method_id="block_random_6m",
        description="Sample a random contiguous 6-month block and cycle within that block.",
        sampling_mode="block_random_6m",
    ),
}


def get_comparison_protocol(comparison_protocol_id: str) -> ComparisonProtocol:
    try:
        return COMPARISON_PROTOCOL_REGISTRY[comparison_protocol_id]
    except KeyError as exc:
        raise ValueError(f"Unknown comparison_protocol_id: {comparison_protocol_id}") from exc


def get_objective_profile(objective_profile_id: str) -> ObjectiveProfile:
    try:
        return OBJECTIVE_PROFILE_REGISTRY[objective_profile_id]
    except KeyError as exc:
        raise ValueError(f"Unknown objective_profile_id: {objective_profile_id}") from exc


def get_reward_profile(reward_profile_id: str) -> RewardProfile:
    try:
        return REWARD_PROFILE_REGISTRY[reward_profile_id]
    except KeyError as exc:
        raise ValueError(f"Unknown reward_profile_id: {reward_profile_id}") from exc


def get_training_method(training_method_id: str) -> TrainingMethod:
    try:
        return TRAINING_METHOD_REGISTRY[training_method_id]
    except KeyError as exc:
        raise ValueError(f"Unknown training_method_id: {training_method_id}") from exc


def protocol_split_windows(comparison_protocol_id: str) -> tuple[SplitWindow, ...]:
    return get_comparison_protocol(comparison_protocol_id).split_windows


def blocked_bootstrap_mean_summary(
    deltas: Iterable[float],
    block_size: int = 3,
    bootstrap_samples: int = 1000,
    random_seed: int = 42,
) -> dict[str, float | int]:
    values = np.asarray(list(deltas), dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {
            "count": 0,
            "mean_delta": float("nan"),
            "median_delta": float("nan"),
            "ci_lower": float("nan"),
            "ci_upper": float("nan"),
        }

    block = max(1, min(int(block_size), values.size))
    rng = np.random.default_rng(random_seed)
    sampled_means: list[float] = []
    max_start = values.size - block
    draws = max(100, int(bootstrap_samples))
    for _ in range(draws):
        sampled_blocks: list[float] = []
        while len(sampled_blocks) < values.size:
            start = int(rng.integers(max_start + 1)) if max_start > 0 else 0
            sampled_blocks.extend(values[start : start + block].tolist())
        sampled_means.append(float(np.mean(sampled_blocks[: values.size])))

    return {
        "count": int(values.size),
        "mean_delta": float(np.mean(values)),
        "median_delta": float(np.median(values)),
        "ci_lower": float(np.quantile(sampled_means, 0.025)),
        "ci_upper": float(np.quantile(sampled_means, 0.975)),
    }
