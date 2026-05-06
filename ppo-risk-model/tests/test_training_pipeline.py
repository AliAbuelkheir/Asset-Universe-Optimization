from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch as th
from stable_baselines3 import PPO
from torch import nn

from src import config
from src.environment.asset_risk_env import AssetRiskEnv
from src.feature_candidates import get_shadow_candidate
from src.input_feature_sets import get_input_feature_set
from src.training import evaluate, train
from src.training import framework_phase
from src.training.experiment_profiles import get_objective_profile, get_reward_profile
from src.training.frameworks import enabled_framework_ids, get_framework_spec
from src.training.metrics import apply_objective_profile, compute_month_metrics, evaluate_prediction_frame, tail_overlap_details
from src.training.panel_utils import build_framework_batches
from src.training.policy import MaskedActorCriticPolicy


def make_panel() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    months = [
        "2010-10",
        "2010-11",
        "2010-12",
        "2011-01",
        "2011-02",
        "2022-10",
        "2022-11",
        "2022-12",
        "2023-01",
        "2023-02",
        "2024-12",
        "2025-01",
        "2025-02",
        "2025-03",
    ]
    month_assets = {month: ["A", "B", "C", "D"] for month in months}

    for month_index, date in enumerate(months, start=1):
        assets = month_assets[date]
        for asset_index, asset_id in enumerate(assets, start=1):
            base = min(0.03 * month_index, 0.70)
            rows.append(
                {
                    "Date": date,
                    "AssetID": asset_id,
                    "AssetName": f"Asset {asset_id}",
                    "AssetGroup": "Equity",
                    "egarch_vol": min(base + (asset_index * 0.01), 0.99),
                    "downside_dev": min(base + (asset_index * 0.02), 0.99),
                    "max_drawdown": min(base + (asset_index * 0.03), 0.99),
                    "volume": min(base + (asset_index * 0.04), 0.99),
                    "atr_pct_20": min(base + (asset_index * 0.05), 0.99),
                    "beta_to_egx30": min(base + (asset_index * 0.06), 0.99),
                    "price_to_sma20": min(base + (asset_index * 0.07), 0.99),
                    "rsi_14": min(base + (asset_index * 0.08), 0.99),
                    "distance_to_3m_high": min(base + (asset_index * 0.09), 0.99),
                    "usd_vol": min(0.15 + base, 0.99),
                    "cpi_trajectory": min(0.02 + base, 0.99),
                    "realized_vol": (asset_index - 1) / max(len(assets) - 1, 1),
                    "realized_downside_dev": (asset_index - 1) / max(len(assets) - 1, 1),
                    "realized_max_drawdown": (asset_index - 1) / max(len(assets) - 1, 1),
                    "realized_risk": (asset_index - 1) / max(len(assets) - 1, 1),
                    "realized_rank": float(asset_index),
                }
            )
    return pd.DataFrame(rows)[config.PANEL_METADATA_COLUMNS + config.MODEL_FEATURE_COLUMNS + config.TARGET_COLUMNS]


def make_daily_market_series(panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for month_index, date in enumerate(sorted(panel["Date"].unique()), start=1):
        month_period = pd.Period(date, freq="M")
        month_start = month_period.to_timestamp()
        month_assets = panel.loc[panel["Date"] == date, ["AssetID", "AssetName", "AssetGroup"]].drop_duplicates()
        for asset_index, row in enumerate(month_assets.itertuples(index=False), start=1):
            base_price = 100.0 + (month_index * 10.0) + asset_index
            observed_dates = [month_start + pd.Timedelta(days=offset) for offset in range(3)]
            observed_prices = [base_price, base_price * 1.10, base_price * 1.21]
            observed_returns = [np.nan, 0.10, 0.10]
            observed_volumes = [1000.0 + asset_index, np.nan, 3000.0 + asset_index]

            for day_idx, observed_date in enumerate(observed_dates):
                rows.append(
                    {
                        "Date": observed_date.strftime(config.DATE_FORMAT_DAILY),
                        "AssetID": row.AssetID,
                        "AssetName": row.AssetName,
                        "AssetGroup": row.AssetGroup,
                        "QuotedValue": observed_prices[day_idx],
                        "OpenQuotedValue": observed_prices[day_idx],
                        "HighQuotedValue": observed_prices[day_idx],
                        "LowQuotedValue": observed_prices[day_idx],
                        "PriceForReturn": observed_prices[day_idx],
                        "OpenPriceForRange": observed_prices[day_idx],
                        "HighPriceForRange": observed_prices[day_idx],
                        "LowPriceForRange": observed_prices[day_idx],
                        "Volume": observed_volumes[day_idx],
                        "ChangePctRaw": observed_returns[day_idx],
                        "ReturnFromPrice": observed_returns[day_idx],
                        "IsObserved": 1,
                    }
                )

            synthetic_date = month_start + pd.Timedelta(days=5)
            rows.append(
                {
                    "Date": synthetic_date.strftime(config.DATE_FORMAT_DAILY),
                    "AssetID": row.AssetID,
                    "AssetName": row.AssetName,
                    "AssetGroup": row.AssetGroup,
                    "QuotedValue": observed_prices[-1] * 5.0,
                    "OpenQuotedValue": observed_prices[-1] * 5.0,
                    "HighQuotedValue": observed_prices[-1] * 5.0,
                    "LowQuotedValue": observed_prices[-1] * 5.0,
                    "PriceForReturn": observed_prices[-1] * 5.0,
                    "OpenPriceForRange": observed_prices[-1] * 5.0,
                    "HighPriceForRange": observed_prices[-1] * 5.0,
                    "LowPriceForRange": observed_prices[-1] * 5.0,
                    "Volume": 999999.0,
                    "ChangePctRaw": 4.0,
                    "ReturnFromPrice": 4.0,
                    "IsObserved": 0,
                }
            )
    return pd.DataFrame(rows)[config.DAILY_MARKET_COLUMNS]


def make_policy_model(env: AssetRiskEnv) -> PPO:
    framework = get_framework_spec(env.framework_id)
    return PPO(
        MaskedActorCriticPolicy,
        env,
        n_steps=4,
        batch_size=4,
        n_epochs=1,
        gamma=1.0,
        gae_lambda=1.0,
        learning_rate=1e-4,
        ent_coef=0.01,
        verbose=0,
        seed=42,
        policy_kwargs={
            "row_encoder_dims": framework.row_encoder_dims,
            "actor_hidden_dims": framework.actor_hidden_dims,
            "actor_context_mode": framework.actor_context_mode,
            "daily_fusion_mode": framework.daily_fusion_mode,
            "daily_path_scope": framework.daily_path_scope,
        },
    )


def make_panel_with_distinct_targets() -> pd.DataFrame:
    panel = make_panel().copy()
    realized_vol = {"A": 0.05, "B": 0.35, "C": 0.75, "D": 0.95}
    realized_downside = {"A": 0.05, "B": 0.85, "C": 0.25, "D": 0.95}
    realized_drawdown = {"A": 0.15, "B": 0.45, "C": 0.95, "D": 0.75}
    panel["realized_vol"] = panel["AssetID"].map(realized_vol).astype(float)
    panel["realized_downside_dev"] = panel["AssetID"].map(realized_downside).astype(float)
    panel["realized_max_drawdown"] = panel["AssetID"].map(realized_drawdown).astype(float)
    return apply_objective_profile(panel, config.DEFAULT_OBJECTIVE_PROFILE_ID)


def make_validation_predictions(
    panel: pd.DataFrame,
    predicted_scores: dict[str, float],
    months: tuple[str, ...] = ("2023-01", "2023-02"),
) -> pd.DataFrame:
    predictions = panel.loc[
        panel["Date"].isin(months),
        ["Date", "AssetID", "AssetName", "AssetGroup", "realized_risk"],
    ].copy()
    predictions["Split"] = "validation"
    predictions["PredictedRisk"] = predictions["AssetID"].map(predicted_scores).astype(float)
    return predictions


def write_framework_artifacts(
    artifact_dir: Path,
    panel_path: Path,
    predictions: pd.DataFrame,
    reward_profile_id: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    monthly_metrics, split_summary = evaluate_prediction_frame(predictions, reward_profile=reward_profile_id)
    evaluate.write_evaluation_artifacts(
        output_dir=artifact_dir,
        predictions=predictions,
        monthly_metrics=monthly_metrics,
        split_summary=split_summary,
        setup_metadata={"panel_path": str(panel_path)},
    )
    return monthly_metrics, split_summary


def clone_observation(observation: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        key: value.copy() if isinstance(value, np.ndarray) else value
        for key, value in observation.items()
    }


def force_actor_head_to_use_daily_signal(policy: MaskedActorCriticPolicy) -> None:
    actor_linears = [module for module in policy.actor_hidden if isinstance(module, nn.Linear)]
    with th.no_grad():
        for linear in actor_linears:
            linear.weight.zero_()
            linear.bias.zero_()
        actor_linears[0].weight[0, policy.row_dim] = 1.0
        for linear in actor_linears[1:]:
            linear.weight[0, 0] = 1.0
        policy.actor_output.weight.zero_()
        policy.actor_output.bias.zero_()
        policy.actor_output.weight[0, 0] = 1.0


def force_cnn_daily_encoder_positive(policy: MaskedActorCriticPolicy) -> None:
    if policy.daily_conv_layers is None:
        raise AssertionError("Expected CNN daily fusion layers to be initialized.")
    with th.no_grad():
        for module in policy.daily_conv_layers:
            if isinstance(module, nn.Conv1d):
                module.weight.fill_(1.0)
                module.bias.zero_()


def test_framework_registry_exposes_active_frameworks() -> None:
    assert enabled_framework_ids() == (
        "pit_1m_shared_mlp",
        "pit_1m_context",
        "pit_1m_dailystrip_shared_cnn",
        "pit_1m_context_t1_dailyflat",
        "pit_1m_t1_dailyflat",
        "pit_1m_t1_daily_actor_cnn",
        "pit_1m_t1_daily_actor_flat",
        "pit_3m_flat_shared_mlp",
        "pit_3m_flat_context",
        "pit_3m_flat_context_t1_dailyflat",
        "pit_3m_flat_t1_dailyflat",
        "pit_3m_flat_context_t1_daily_actor_cnn",
        "pit_3m_flat_context_t1_daily_actor_flat",
    )


@pytest.mark.parametrize(
    ("framework_id", "expected_fusion_mode"),
    (
        ("pit_1m_t1_daily_actor_cnn", "cnn_pool"),
        ("pit_1m_t1_daily_actor_flat", "flat_concat"),
        ("pit_3m_flat_context_t1_daily_actor_cnn", "cnn_pool"),
        ("pit_3m_flat_context_t1_daily_actor_flat", "flat_concat"),
    ),
)
def test_actor_only_framework_specs_expose_daily_path_scope_and_fusion_mode(
    framework_id: str,
    expected_fusion_mode: str,
) -> None:
    framework = get_framework_spec(framework_id)

    assert framework.uses_daily_strip
    assert framework.daily_path_scope == "actor_only"
    assert framework.daily_fusion_mode == expected_fusion_mode


def test_masked_policy_initializes_and_action_space_is_finite(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    make_panel().to_csv(panel_path, index=False)

    env = AssetRiskEnv(panel_path=panel_path, split_name="train", framework_id="pit_1m_shared_mlp")
    model = make_policy_model(env)

    assert env.action_space.shape == (4,)
    assert env.action_space.low.tolist() == [0.0, 0.0, 0.0, 0.0]
    assert env.action_space.high.tolist() == [1.0, 1.0, 1.0, 1.0]
    assert env.observation_space["features"].shape == (4, 11)
    assert isinstance(model.policy, MaskedActorCriticPolicy)


def test_asset_risk_env_uses_framework_specific_observation_shapes_and_state_months(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    daily_path = tmp_path / "daily.csv"
    panel = make_panel()
    panel.to_csv(panel_path, index=False)
    make_daily_market_series(panel).to_csv(daily_path, index=False)

    one_month_env = AssetRiskEnv(
        panel_path=panel_path,
        split_name="train",
        framework_id="pit_1m_shared_mlp",
        sampling_mode="ordered",
    )
    observation, info = one_month_env.reset(options={"restart_sequence": True})
    assert observation["features"].shape == (4, 11)
    assert info["Date"] == "2011-01"
    assert info["StateMonths"] == ["2010-12"]

    three_month_env = AssetRiskEnv(
        panel_path=panel_path,
        split_name="train",
        framework_id="pit_3m_flat_shared_mlp",
        sampling_mode="ordered",
    )
    stacked_observation, stacked_info = three_month_env.reset(options={"restart_sequence": True})
    assert stacked_observation["features"].shape == (4, 33)
    assert stacked_info["Date"] == "2011-01"
    assert stacked_info["StateMonths"] == ["2010-10", "2010-11", "2010-12"]

    daily_flat_env = AssetRiskEnv(
        panel_path=panel_path,
        daily_path=daily_path,
        split_name="train",
        framework_id="pit_3m_flat_context_t1_dailyflat",
        sampling_mode="ordered",
    )
    daily_observation, daily_info = daily_flat_env.reset(options={"restart_sequence": True})
    assert daily_observation["features"].shape == (4, 33)
    assert daily_observation["daily_strip"].shape == (4, config.MAX_MONTHLY_OBS, config.DAILY_STRIP_CHANNELS)
    assert daily_observation["daily_mask"].shape == (4, config.MAX_MONTHLY_OBS)
    assert daily_info["Date"] == "2011-01"
    assert daily_info["StateMonths"] == ["2010-10", "2010-11", "2010-12"]


def test_build_framework_batches_attach_daily_strip_from_prior_month_only(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    daily_path = tmp_path / "daily.csv"
    panel = make_panel()
    daily = make_daily_market_series(panel)
    panel.to_csv(panel_path, index=False)
    daily.to_csv(daily_path, index=False)

    batches = build_framework_batches(
        panel,
        framework_id="pit_1m_dailystrip_shared_cnn",
        split_name="train",
        daily_market_series=daily,
    )
    first_batch = batches[0]

    assert first_batch.date == "2011-01"
    assert first_batch.state_months == ("2010-12",)
    assert first_batch.daily_strip is not None
    assert first_batch.daily_mask is not None
    assert first_batch.daily_strip.shape == (4, config.MAX_MONTHLY_OBS, config.DAILY_STRIP_CHANNELS)
    assert first_batch.daily_mask.shape == (4, config.MAX_MONTHLY_OBS)

    expected_strip = np.array(
        [
            [0.0, 0.0, np.log1p(1001.0), 1.0],
            [0.10, 0.10, 0.0, 0.0],
            [0.21, 0.10, np.log1p(3001.0), 1.0],
        ],
        dtype=np.float32,
    )
    assert np.allclose(first_batch.daily_strip[0, :3], expected_strip, atol=1e-6)
    assert np.allclose(first_batch.daily_mask[0, :3], np.ones(3, dtype=np.float32))
    assert np.allclose(first_batch.daily_mask[0, 3:], np.zeros(config.MAX_MONTHLY_OBS - 3, dtype=np.float32))
    assert np.allclose(first_batch.daily_strip[0, 3:], 0.0)


def test_environment_observation_space_contains_emitted_observations(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    panel = make_panel()
    panel.loc[panel["Date"] == "2010-12", "cpi_trajectory"] = -0.01
    panel.to_csv(panel_path, index=False)

    env = AssetRiskEnv(
        panel_path=panel_path,
        split_name="train",
        framework_id="pit_1m_shared_mlp",
        sampling_mode="ordered",
    )
    observation, _ = env.reset(options={"restart_sequence": True})

    assert env.observation_space.contains(observation)


def test_daily_strip_environment_emits_expected_keys_and_shapes(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    daily_path = tmp_path / "daily.csv"
    panel = make_panel()
    daily = make_daily_market_series(panel)
    panel.to_csv(panel_path, index=False)
    daily.to_csv(daily_path, index=False)

    env = AssetRiskEnv(
        panel_path=panel_path,
        daily_path=daily_path,
        split_name="train",
        framework_id="pit_1m_dailystrip_shared_cnn",
        sampling_mode="ordered",
    )
    observation, info = env.reset(options={"restart_sequence": True})

    assert observation["features"].shape == (4, 11)
    assert observation["daily_strip"].shape == (4, config.MAX_MONTHLY_OBS, config.DAILY_STRIP_CHANNELS)
    assert observation["daily_mask"].shape == (4, config.MAX_MONTHLY_OBS)
    assert info["Date"] == "2011-01"
    assert env.observation_space.contains(observation)


def test_daily_flat_environment_emits_expected_keys_and_shapes(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    daily_path = tmp_path / "daily.csv"
    panel = make_panel()
    daily = make_daily_market_series(panel)
    panel.to_csv(panel_path, index=False)
    daily.to_csv(daily_path, index=False)

    env = AssetRiskEnv(
        panel_path=panel_path,
        daily_path=daily_path,
        split_name="train",
        framework_id="pit_3m_flat_context_t1_dailyflat",
        sampling_mode="ordered",
    )
    observation, info = env.reset(options={"restart_sequence": True})

    assert observation["features"].shape == (4, 33)
    assert observation["daily_strip"].shape == (4, config.MAX_MONTHLY_OBS, config.DAILY_STRIP_CHANNELS)
    assert observation["daily_mask"].shape == (4, config.MAX_MONTHLY_OBS)
    assert info["Date"] == "2011-01"
    assert info["StateMonths"] == ["2010-10", "2010-11", "2010-12"]
    assert env.observation_space.contains(observation)


def test_1m_daily_flat_environment_emits_expected_keys_and_shapes(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    daily_path = tmp_path / "daily.csv"
    panel = make_panel()
    daily = make_daily_market_series(panel)
    panel.to_csv(panel_path, index=False)
    daily.to_csv(daily_path, index=False)

    env = AssetRiskEnv(
        panel_path=panel_path,
        daily_path=daily_path,
        split_name="train",
        framework_id="pit_1m_context_t1_dailyflat",
        sampling_mode="ordered",
    )
    observation, info = env.reset(options={"restart_sequence": True})

    assert observation["features"].shape == (4, 11)
    assert observation["daily_strip"].shape == (4, config.MAX_MONTHLY_OBS, config.DAILY_STRIP_CHANNELS)
    assert observation["daily_mask"].shape == (4, config.MAX_MONTHLY_OBS)
    assert info["Date"] == "2011-01"
    assert info["StateMonths"] == ["2010-12"]
    assert env.observation_space.contains(observation)


def test_1m_daily_flat_no_context_environment_emits_expected_keys_and_shapes(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    daily_path = tmp_path / "daily.csv"
    panel = make_panel()
    daily = make_daily_market_series(panel)
    panel.to_csv(panel_path, index=False)
    daily.to_csv(daily_path, index=False)

    env = AssetRiskEnv(
        panel_path=panel_path,
        daily_path=daily_path,
        split_name="train",
        framework_id="pit_1m_t1_dailyflat",
        sampling_mode="ordered",
    )
    observation, info = env.reset(options={"restart_sequence": True})

    assert observation["features"].shape == (4, 11)
    assert observation["daily_strip"].shape == (4, config.MAX_MONTHLY_OBS, config.DAILY_STRIP_CHANNELS)
    assert observation["daily_mask"].shape == (4, config.MAX_MONTHLY_OBS)
    assert info["Date"] == "2011-01"
    assert info["StateMonths"] == ["2010-12"]
    assert env.observation_space.contains(observation)


@pytest.mark.parametrize(
    ("framework_id", "expected_feature_dim", "expected_state_months"),
    (
        ("pit_1m_t1_daily_actor_cnn", 11, ["2010-12"]),
        ("pit_1m_t1_daily_actor_flat", 11, ["2010-12"]),
        ("pit_3m_flat_context_t1_daily_actor_cnn", 33, ["2010-10", "2010-11", "2010-12"]),
        ("pit_3m_flat_context_t1_daily_actor_flat", 33, ["2010-10", "2010-11", "2010-12"]),
    ),
)
def test_actor_only_daily_environments_emit_expected_keys_and_shapes(
    tmp_path: Path,
    framework_id: str,
    expected_feature_dim: int,
    expected_state_months: list[str],
) -> None:
    panel_path = tmp_path / "panel.csv"
    daily_path = tmp_path / "daily.csv"
    panel = make_panel()
    daily = make_daily_market_series(panel)
    panel.to_csv(panel_path, index=False)
    daily.to_csv(daily_path, index=False)

    env = AssetRiskEnv(
        panel_path=panel_path,
        daily_path=daily_path,
        split_name="train",
        framework_id=framework_id,
        sampling_mode="ordered",
    )
    observation, info = env.reset(options={"restart_sequence": True})

    assert observation["features"].shape == (4, expected_feature_dim)
    assert observation["daily_strip"].shape == (4, config.MAX_MONTHLY_OBS, config.DAILY_STRIP_CHANNELS)
    assert observation["daily_mask"].shape == (4, config.MAX_MONTHLY_OBS)
    assert info["Date"] == "2011-01"
    assert info["StateMonths"] == expected_state_months
    assert env.observation_space.contains(observation)


def test_build_framework_batches_stack_prior_month_rows_only(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    panel = make_panel()
    panel.to_csv(panel_path, index=False)

    batches = build_framework_batches(panel, framework_id="pit_3m_flat_shared_mlp", split_name="train")
    first_batch = batches[0]
    asset_a = panel.loc[panel["AssetID"] == "A"].set_index("Date")
    expected = np.concatenate(
        [
            asset_a.loc["2010-10", config.MODEL_FEATURE_COLUMNS].to_numpy(dtype=np.float32),
            asset_a.loc["2010-11", config.MODEL_FEATURE_COLUMNS].to_numpy(dtype=np.float32),
            asset_a.loc["2010-12", config.MODEL_FEATURE_COLUMNS].to_numpy(dtype=np.float32),
        ]
    )

    assert first_batch.date == config.TRAIN_START
    assert first_batch.features.shape == (4, 33)
    assert np.allclose(first_batch.features[0], expected)


def test_3m_context_keeps_33_features_and_uses_first_train_prior_rows_for_monthly_only_profile() -> None:
    panel = make_panel()
    monthly_only_panel = panel.copy()
    for month_index, date in enumerate(sorted(monthly_only_panel["Date"].unique()), start=1):
        month_mask = monthly_only_panel["Date"] == date
        monthly_only_panel.loc[month_mask, config.MODEL_FEATURE_COLUMNS] = month_index / 100.0

    batches = build_framework_batches(monthly_only_panel, framework_id="pit_3m_flat_context", split_name="train")
    first_batch = batches[0]
    expected = np.concatenate(
        [
            np.full(len(config.MODEL_FEATURE_COLUMNS), 0.01, dtype=np.float32),
            np.full(len(config.MODEL_FEATURE_COLUMNS), 0.02, dtype=np.float32),
            np.full(len(config.MODEL_FEATURE_COLUMNS), 0.03, dtype=np.float32),
        ]
    )

    assert first_batch.date == "2011-01"
    assert first_batch.state_months == ("2010-10", "2010-11", "2010-12")
    assert first_batch.features.shape == (4, 33)
    assert np.allclose(first_batch.features[0], expected)


def test_daily_flat_framework_keeps_the_same_decision_months_as_3m_context(tmp_path: Path) -> None:
    panel = make_panel()
    daily = make_daily_market_series(panel)

    context_batches = build_framework_batches(panel, framework_id="pit_3m_flat_context", split_name="train")
    daily_flat_batches = build_framework_batches(
        panel,
        framework_id="pit_3m_flat_context_t1_dailyflat",
        split_name="train",
        daily_market_series=daily,
    )

    assert [batch.date for batch in daily_flat_batches] == [batch.date for batch in context_batches]

    first_batch = daily_flat_batches[0]
    assert first_batch.state_months == ("2010-10", "2010-11", "2010-12")
    assert first_batch.daily_strip is not None
    assert first_batch.daily_mask is not None


def test_1m_daily_flat_framework_keeps_the_same_decision_months_as_1m_context(tmp_path: Path) -> None:
    panel = make_panel()
    daily = make_daily_market_series(panel)

    context_batches = build_framework_batches(panel, framework_id="pit_1m_context", split_name="train")
    daily_flat_batches = build_framework_batches(
        panel,
        framework_id="pit_1m_context_t1_dailyflat",
        split_name="train",
        daily_market_series=daily,
    )

    assert [batch.date for batch in daily_flat_batches] == [batch.date for batch in context_batches]

    first_batch = daily_flat_batches[0]
    assert first_batch.state_months == ("2010-12",)
    assert first_batch.features.shape == (4, 11)
    assert first_batch.daily_strip is not None
    assert first_batch.daily_mask is not None


def test_1m_daily_flat_no_context_framework_keeps_the_same_decision_months_as_1m_base(tmp_path: Path) -> None:
    panel = make_panel()
    daily = make_daily_market_series(panel)

    base_batches = build_framework_batches(panel, framework_id="pit_1m_shared_mlp", split_name="train")
    daily_flat_batches = build_framework_batches(
        panel,
        framework_id="pit_1m_t1_dailyflat",
        split_name="train",
        daily_market_series=daily,
    )

    assert [batch.date for batch in daily_flat_batches] == [batch.date for batch in base_batches]

    first_batch = daily_flat_batches[0]
    assert first_batch.state_months == ("2010-12",)
    assert first_batch.features.shape == (4, 11)
    assert first_batch.daily_strip is not None
    assert first_batch.daily_mask is not None


def test_3m_daily_flat_no_context_framework_keeps_the_same_decision_months_as_3m_base(tmp_path: Path) -> None:
    panel = make_panel()
    daily = make_daily_market_series(panel)

    base_batches = build_framework_batches(panel, framework_id="pit_3m_flat_shared_mlp", split_name="train")
    daily_flat_batches = build_framework_batches(
        panel,
        framework_id="pit_3m_flat_t1_dailyflat",
        split_name="train",
        daily_market_series=daily,
    )

    assert [batch.date for batch in daily_flat_batches] == [batch.date for batch in base_batches]

    first_batch = daily_flat_batches[0]
    assert first_batch.state_months == ("2010-10", "2010-11", "2010-12")
    assert first_batch.features.shape == (4, 33)
    assert first_batch.daily_strip is not None
    assert first_batch.daily_mask is not None


@pytest.mark.parametrize(
    ("framework_id", "backbone_framework_id", "expected_state_months"),
    (
        ("pit_1m_t1_daily_actor_cnn", "pit_1m_shared_mlp", ("2010-12",)),
        ("pit_1m_t1_daily_actor_flat", "pit_1m_shared_mlp", ("2010-12",)),
        ("pit_3m_flat_context_t1_daily_actor_cnn", "pit_3m_flat_context", ("2010-10", "2010-11", "2010-12")),
        ("pit_3m_flat_context_t1_daily_actor_flat", "pit_3m_flat_context", ("2010-10", "2010-11", "2010-12")),
    ),
)
def test_actor_only_daily_frameworks_keep_backbone_decision_months_and_state_months(
    tmp_path: Path,
    framework_id: str,
    backbone_framework_id: str,
    expected_state_months: tuple[str, ...],
) -> None:
    panel = make_panel()
    daily = make_daily_market_series(panel)

    backbone_batches = build_framework_batches(panel, framework_id=backbone_framework_id, split_name="train")
    actor_only_batches = build_framework_batches(
        panel,
        framework_id=framework_id,
        split_name="train",
        daily_market_series=daily,
    )

    assert [batch.date for batch in actor_only_batches] == [batch.date for batch in backbone_batches]

    first_batch = actor_only_batches[0]
    assert first_batch.state_months == expected_state_months
    assert first_batch.daily_strip is not None
    assert first_batch.daily_mask is not None

def test_masked_policy_is_row_order_invariant_and_ignores_padded_rows(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    make_panel().to_csv(panel_path, index=False)
    env = AssetRiskEnv(panel_path=panel_path, split_name="train", framework_id="pit_3m_flat_context")
    model = make_policy_model(env)

    obs = {
        "features": np.array(
            [
                [0.11] * env.feature_count,
                [0.22] * env.feature_count,
                [0.33] * env.feature_count,
                [0.99] * env.feature_count,
            ],
            dtype=np.float32,
        ),
        "mask": np.array([1.0, 1.0, 1.0, 0.0], dtype=np.float32),
    }
    swapped = {
        "features": obs["features"][[2, 0, 1, 3]],
        "mask": obs["mask"][[2, 0, 1, 3]],
    }
    padded_variant = {
        "features": obs["features"].copy(),
        "mask": obs["mask"].copy(),
    }
    padded_variant["features"][3] = np.array([0.01] * env.feature_count, dtype=np.float32)

    actions, _ = model.predict(obs, deterministic=True)
    swapped_actions, _ = model.predict(swapped, deterministic=True)
    padded_actions, _ = model.predict(padded_variant, deterministic=True)

    assert np.allclose(actions[:3], swapped_actions[[1, 2, 0]][:3])
    assert np.allclose(actions[:3], padded_actions[:3])
    assert padded_actions[3] == 0.0

    obs_tensor, _ = model.policy.obs_to_tensor(obs)
    padded_tensor, _ = model.policy.obs_to_tensor(padded_variant)
    action_tensor = model.policy.get_distribution(obs_tensor).mode()
    values_a, log_prob_a, entropy_a = model.policy.evaluate_actions(obs_tensor, action_tensor)
    values_b, log_prob_b, entropy_b = model.policy.evaluate_actions(padded_tensor, action_tensor)

    assert np.allclose(values_a.detach().cpu().numpy(), values_b.detach().cpu().numpy())
    assert np.allclose(log_prob_a.detach().cpu().numpy(), log_prob_b.detach().cpu().numpy())
    assert entropy_a is None
    assert entropy_b is None


def test_masked_policy_samples_and_predicts_within_action_bounds(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    make_panel().to_csv(panel_path, index=False)

    env = AssetRiskEnv(panel_path=panel_path, split_name="train", framework_id="pit_1m_shared_mlp")
    model = make_policy_model(env)
    observation, _ = env.reset(seed=42)

    actions, _ = model.predict(observation, deterministic=False)
    deterministic_actions, _ = model.predict(observation, deterministic=True)

    assert np.all(actions >= 0.0)
    assert np.all(actions <= 1.0)
    assert np.all(deterministic_actions >= 0.0)
    assert np.all(deterministic_actions <= 1.0)


def test_masked_policy_log_prob_is_finite_near_action_boundaries(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    make_panel().to_csv(panel_path, index=False)

    env = AssetRiskEnv(panel_path=panel_path, split_name="train", framework_id="pit_1m_shared_mlp")
    model = make_policy_model(env)
    observation, _ = env.reset(seed=42)
    obs_tensor, _ = model.policy.obs_to_tensor(observation)
    near_boundary_actions = th.tensor([[1e-6, 0.25, 0.999999, 0.0]], dtype=th.float32)

    _, log_prob, entropy = model.policy.evaluate_actions(obs_tensor, near_boundary_actions)

    assert th.isfinite(log_prob).all()
    assert entropy is None


def test_daily_strip_policy_predict_and_evaluate_actions(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    daily_path = tmp_path / "daily.csv"
    panel = make_panel()
    daily = make_daily_market_series(panel)
    panel.to_csv(panel_path, index=False)
    daily.to_csv(daily_path, index=False)

    env = AssetRiskEnv(
        panel_path=panel_path,
        daily_path=daily_path,
        split_name="train",
        framework_id="pit_1m_dailystrip_shared_cnn",
        sampling_mode="ordered",
    )
    model = make_policy_model(env)
    observation, _ = env.reset(options={"restart_sequence": True})

    actions, _ = model.predict(observation, deterministic=True)
    assert actions.shape == (4,)

    obs_tensor, _ = model.policy.obs_to_tensor(observation)
    action_tensor = model.policy.get_distribution(obs_tensor).mode()
    values, log_prob, entropy = model.policy.evaluate_actions(obs_tensor, action_tensor)

    assert values.shape == (1, 1)
    assert log_prob.shape == (1,)
    assert entropy is None


def test_daily_flat_policy_predicts_without_conv_layers_and_ignores_masked_days(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    daily_path = tmp_path / "daily.csv"
    panel = make_panel()
    daily = make_daily_market_series(panel)
    panel.to_csv(panel_path, index=False)
    daily.to_csv(daily_path, index=False)

    env = AssetRiskEnv(
        panel_path=panel_path,
        daily_path=daily_path,
        split_name="train",
        framework_id="pit_3m_flat_context_t1_dailyflat",
        sampling_mode="ordered",
    )
    model = make_policy_model(env)
    observation, _ = env.reset(options={"restart_sequence": True})

    assert not any(isinstance(module, nn.Conv1d) for module in model.policy.modules())

    padded_variant = {
        key: value.copy() if isinstance(value, np.ndarray) else value
        for key, value in observation.items()
    }
    padded_variant["daily_strip"][0, 3:, :] = 999.0

    actions, _ = model.predict(observation, deterministic=True)
    padded_actions, _ = model.predict(padded_variant, deterministic=True)

    assert np.allclose(actions, padded_actions)

    obs_tensor, _ = model.policy.obs_to_tensor(observation)
    action_tensor = model.policy.get_distribution(obs_tensor).mode()
    values, log_prob, entropy = model.policy.evaluate_actions(obs_tensor, action_tensor)

    assert values.shape == (1, 1)
    assert log_prob.shape == (1,)
    assert entropy is None


@pytest.mark.parametrize(
    "framework_id",
    (
        "pit_1m_t1_daily_actor_cnn",
        "pit_1m_t1_daily_actor_flat",
        "pit_3m_flat_context_t1_daily_actor_cnn",
        "pit_3m_flat_context_t1_daily_actor_flat",
    ),
)
def test_actor_only_daily_policy_changes_actor_outputs_without_changing_critic_values(
    tmp_path: Path,
    framework_id: str,
) -> None:
    panel_path = tmp_path / "panel.csv"
    daily_path = tmp_path / "daily.csv"
    panel = make_panel()
    daily = make_daily_market_series(panel)
    panel.to_csv(panel_path, index=False)
    daily.to_csv(daily_path, index=False)

    env = AssetRiskEnv(
        panel_path=panel_path,
        daily_path=daily_path,
        split_name="train",
        framework_id=framework_id,
        sampling_mode="ordered",
    )
    model = make_policy_model(env)
    if "cnn" in framework_id:
        force_cnn_daily_encoder_positive(model.policy)
    force_actor_head_to_use_daily_signal(model.policy)

    observation, _ = env.reset(options={"restart_sequence": True})
    changed_observation = clone_observation(observation)
    assert changed_observation["daily_mask"][0, 0] == 1.0
    changed_observation["daily_strip"][0, 0, 0] = 5.0

    obs_tensor, _ = model.policy.obs_to_tensor(observation)
    changed_tensor, _ = model.policy.obs_to_tensor(changed_observation)

    actor_rows_a, critic_rows_a, mask_a = model.policy._encode_rows(obs_tensor)
    actor_rows_b, critic_rows_b, mask_b = model.policy._encode_rows(changed_tensor)
    summary_a = model.policy._pooled_summary(critic_rows_a, mask_a)
    summary_b = model.policy._pooled_summary(critic_rows_b, mask_b)
    means_a = model.policy._actor_means(actor_rows_a, mask_a, summary_a)
    means_b = model.policy._actor_means(actor_rows_b, mask_b, summary_b)
    values_a = model.policy._critic_values(summary_a)
    values_b = model.policy._critic_values(summary_b)

    assert np.array_equal(mask_a.detach().cpu().numpy(), mask_b.detach().cpu().numpy())
    assert not np.allclose(actor_rows_a.detach().cpu().numpy(), actor_rows_b.detach().cpu().numpy())
    assert np.allclose(critic_rows_a.detach().cpu().numpy(), critic_rows_b.detach().cpu().numpy())
    assert np.allclose(summary_a.detach().cpu().numpy(), summary_b.detach().cpu().numpy())
    assert not np.allclose(means_a.detach().cpu().numpy(), means_b.detach().cpu().numpy())
    assert np.allclose(values_a.detach().cpu().numpy(), values_b.detach().cpu().numpy())


@pytest.mark.parametrize(
    "framework_id",
    (
        "pit_1m_t1_daily_actor_cnn",
        "pit_1m_t1_daily_actor_flat",
    ),
)
def test_actor_only_daily_policy_ignores_masked_day_values(
    tmp_path: Path,
    framework_id: str,
) -> None:
    panel_path = tmp_path / "panel.csv"
    daily_path = tmp_path / "daily.csv"
    panel = make_panel()
    daily = make_daily_market_series(panel)
    panel.to_csv(panel_path, index=False)
    daily.to_csv(daily_path, index=False)

    env = AssetRiskEnv(
        panel_path=panel_path,
        daily_path=daily_path,
        split_name="train",
        framework_id=framework_id,
        sampling_mode="ordered",
    )
    model = make_policy_model(env)
    if "cnn" in framework_id:
        force_cnn_daily_encoder_positive(model.policy)
    force_actor_head_to_use_daily_signal(model.policy)

    observation, _ = env.reset(options={"restart_sequence": True})
    padded_variant = clone_observation(observation)
    padded_variant["daily_strip"][0, 3:, :] = 999.0

    actions, _ = model.predict(observation, deterministic=True)
    padded_actions, _ = model.predict(padded_variant, deterministic=True)

    obs_tensor, _ = model.policy.obs_to_tensor(observation)
    padded_tensor, _ = model.policy.obs_to_tensor(padded_variant)
    actor_rows_a, critic_rows_a, mask_a = model.policy._encode_rows(obs_tensor)
    actor_rows_b, critic_rows_b, mask_b = model.policy._encode_rows(padded_tensor)
    summary_a = model.policy._pooled_summary(critic_rows_a, mask_a)
    summary_b = model.policy._pooled_summary(critic_rows_b, mask_b)
    values_a = model.policy._critic_values(summary_a)
    values_b = model.policy._critic_values(summary_b)

    assert np.array_equal(mask_a.detach().cpu().numpy(), mask_b.detach().cpu().numpy())
    assert np.allclose(actor_rows_a.detach().cpu().numpy(), actor_rows_b.detach().cpu().numpy())
    assert np.allclose(critic_rows_a.detach().cpu().numpy(), critic_rows_b.detach().cpu().numpy())
    assert np.allclose(actions, padded_actions)
    assert np.allclose(values_a.detach().cpu().numpy(), values_b.detach().cpu().numpy())


def test_learn_only_uses_train_split(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    make_panel().to_csv(panel_path, index=False)

    class LoggingAssetRiskEnv(AssetRiskEnv):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self.reset_splits: list[str] = []

        def reset(self, *args, **kwargs):  # type: ignore[override]
            observation, info = super().reset(*args, **kwargs)
            self.reset_splits.append(info["Split"])
            return observation, info

    env = LoggingAssetRiskEnv(
        panel_path=panel_path,
        split_name="train",
        framework_id="pit_1m_shared_mlp",
        sampling_mode="random",
    )
    model = make_policy_model(env)
    model.learn(total_timesteps=8, progress_bar=False)

    assert env.reset_splits
    assert set(env.reset_splits) == {"train"}
    assert np.all(model.rollout_buffer.actions >= 0.0)
    assert np.all(model.rollout_buffer.actions <= 1.0)


def test_evaluate_model_splits_and_write_artifacts(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    output_dir = tmp_path / "eval_outputs"
    make_panel().to_csv(panel_path, index=False)

    env = AssetRiskEnv(panel_path=panel_path, split_name="train", framework_id="pit_1m_shared_mlp")
    model = make_policy_model(env)
    model.learn(total_timesteps=8, progress_bar=False)

    predictions, monthly_metrics, split_summary = evaluate.evaluate_model_splits(
        model=model,
        panel_path=panel_path,
        daily_path=None,
        framework_id="pit_1m_shared_mlp",
        split_names=("validation", "test"),
    )
    evaluate.write_evaluation_artifacts(
        output_dir=output_dir,
        predictions=predictions,
        monthly_metrics=monthly_metrics,
        split_summary=split_summary,
        setup_metadata={"source": "test", "framework_id": "pit_1m_shared_mlp"},
    )

    assert set(predictions["Split"]) == {"validation", "test"}
    assert (output_dir / "ranked_predictions.csv").exists()
    assert (output_dir / "monthly_metrics.csv").exists()
    assert (output_dir / "split_summary.csv").exists()
    assert (output_dir / "setup_metadata.json").exists()


def test_train_setup_writes_framework_phase_artifacts_and_metadata(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    output_root = tmp_path / "outputs"
    make_panel().to_csv(panel_path, index=False)

    setup = train.SetupConfig(
        setup_id="FW-BASE-1M-S42",
        framework_id="pit_1m_shared_mlp",
        total_timesteps=8,
        seed=42,
    )
    artifact_dir = train.train_setup(panel_path=panel_path, daily_path=None, setup=setup, output_root=output_root)

    assert (artifact_dir / "best_model.zip").exists()
    assert (artifact_dir / "final_model.zip").exists()
    assert (artifact_dir / "ranked_predictions.csv").exists()
    assert (artifact_dir / "monthly_metrics.csv").exists()
    assert (artifact_dir / "split_summary.csv").exists()
    assert (artifact_dir / "training_metrics.csv").exists()
    assert (artifact_dir / "setup_metadata.json").exists()
    assert (artifact_dir / "setup_summary.json").exists()
    assert (output_root / train.SUMMARY_FILE_NAME).exists()

    setup_results = pd.read_csv(output_root / train.SUMMARY_FILE_NAME)
    assert set(setup_results["StudyPhase"]) == {config.FRAMEWORK_PHASE_NAME}
    assert set(setup_results["FrameworkID"]) == {"pit_1m_shared_mlp"}
    assert set(setup_results["ActionDistribution"]) == {config.ACTION_DISTRIBUTION_NAME}
    assert set(setup_results["PolicySemanticsVersion"]) == {config.POLICY_SEMANTICS_VERSION}
    assert set(setup_results["FeatureProfileID"]) == {config.DEFAULT_FEATURE_PROFILE_ID}
    assert float(setup_results.iloc[0]["LearningRate"]) == config.FRAMEWORK_PPO_LEARNING_RATE
    assert int(setup_results.iloc[0]["EvalFrequency"]) == config.FRAMEWORK_PPO_EVAL_FREQUENCY
    assert setup_results.iloc[0]["DailyPathScope"] == "none"
    assert setup_results.iloc[0]["ReportedCheckpoint"].endswith("best_model.zip")

    metadata = pd.read_json(artifact_dir / "setup_metadata.json", typ="series")
    assert metadata["study_phase"] == config.FRAMEWORK_PHASE_NAME
    assert metadata["action_distribution"] == config.ACTION_DISTRIBUTION_NAME
    assert metadata["policy_semantics_version"] == config.POLICY_SEMANTICS_VERSION
    assert metadata["framework_id"] == "pit_1m_shared_mlp"
    assert metadata["feature_profile_id"] == config.DEFAULT_FEATURE_PROFILE_ID
    assert metadata["common_decision_start"] == config.TRAIN_START
    assert metadata["panel_state_start"] == config.PANEL_STATE_START
    assert metadata["framework_spec"]["daily_path_scope"] == "none"

    reloaded_model = evaluate.load_ppo_checkpoint(artifact_dir / "best_model.zip")
    assert isinstance(reloaded_model, PPO)


def test_train_setup_supports_daily_strip_framework(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    daily_path = tmp_path / "daily.csv"
    output_root = tmp_path / "outputs"
    panel = make_panel()
    daily = make_daily_market_series(panel)
    panel.to_csv(panel_path, index=False)
    daily.to_csv(daily_path, index=False)

    setup = train.SetupConfig(
        setup_id="FW-1M-DAILYSTRIP-CNN-S42",
        framework_id="pit_1m_dailystrip_shared_cnn",
        total_timesteps=8,
        seed=42,
    )
    artifact_dir = train.train_setup(panel_path=panel_path, daily_path=daily_path, setup=setup, output_root=output_root)

    assert (artifact_dir / "best_model.zip").exists()
    assert (artifact_dir / "final_model.zip").exists()
    assert (artifact_dir / "ranked_predictions.csv").exists()
    assert (artifact_dir / "monthly_metrics.csv").exists()
    assert (artifact_dir / "split_summary.csv").exists()

    setup_results = pd.read_csv(output_root / train.SUMMARY_FILE_NAME)
    row = setup_results.iloc[0]
    assert row["FrameworkID"] == "pit_1m_dailystrip_shared_cnn"
    assert bool(row["UsesDailyStrip"])
    assert int(row["DailyStripChannels"]) == config.DAILY_STRIP_CHANNELS
    assert int(row["DailyStripLength"]) == config.MAX_MONTHLY_OBS
    assert row["ActionDistribution"] == config.ACTION_DISTRIBUTION_NAME
    assert row["PolicySemanticsVersion"] == config.POLICY_SEMANTICS_VERSION
    assert row["DailyFusionMode"] == "cnn_pool"
    assert row["DailyPathScope"] == "shared"
    assert row["DailyChannelNames"] == ",".join(config.DAILY_STRIP_CHANNEL_NAMES)


def test_train_setup_supports_daily_flat_framework(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    daily_path = tmp_path / "daily.csv"
    output_root = tmp_path / "outputs"
    panel = make_panel()
    daily = make_daily_market_series(panel)
    panel.to_csv(panel_path, index=False)
    daily.to_csv(daily_path, index=False)

    setup = train.SetupConfig(
        setup_id="FW-STACK3M-CONTEXT-T1-DAILYFLAT-S42",
        framework_id="pit_3m_flat_context_t1_dailyflat",
        total_timesteps=8,
        seed=42,
    )
    artifact_dir = train.train_setup(panel_path=panel_path, daily_path=daily_path, setup=setup, output_root=output_root)

    assert (artifact_dir / "best_model.zip").exists()
    assert (artifact_dir / "final_model.zip").exists()
    assert (artifact_dir / "ranked_predictions.csv").exists()
    assert (artifact_dir / "monthly_metrics.csv").exists()
    assert (artifact_dir / "split_summary.csv").exists()

    setup_results = pd.read_csv(output_root / train.SUMMARY_FILE_NAME)
    row = setup_results.iloc[0]
    assert row["FrameworkID"] == "pit_3m_flat_context_t1_dailyflat"
    assert int(row["MonthlyFeatureDim"]) == len(config.MODEL_FEATURE_COLUMNS) * 3
    assert int(row["InputDim"]) == (len(config.MODEL_FEATURE_COLUMNS) * 3) + (config.MAX_MONTHLY_OBS * config.DAILY_STRIP_CHANNELS) + config.MAX_MONTHLY_OBS
    assert bool(row["UsesDailyStrip"])
    assert int(row["DailyStripChannels"]) == config.DAILY_STRIP_CHANNELS
    assert int(row["DailyStripLength"]) == config.MAX_MONTHLY_OBS
    assert row["DailyFusionMode"] == "flat_concat"
    assert row["DailyPathScope"] == "shared"
    assert row["DailyChannelNames"] == ",".join(config.DAILY_STRIP_CHANNEL_NAMES)


def test_train_setup_supports_1m_context_daily_flat_framework(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    daily_path = tmp_path / "daily.csv"
    output_root = tmp_path / "outputs"
    panel = make_panel()
    daily = make_daily_market_series(panel)
    panel.to_csv(panel_path, index=False)
    daily.to_csv(daily_path, index=False)

    setup = train.SetupConfig(
        setup_id="FW-1M-CONTEXT-T1-DAILYFLAT-S42",
        framework_id="pit_1m_context_t1_dailyflat",
        total_timesteps=8,
        seed=42,
    )
    artifact_dir = train.train_setup(panel_path=panel_path, daily_path=daily_path, setup=setup, output_root=output_root)

    assert (artifact_dir / "best_model.zip").exists()
    assert (artifact_dir / "final_model.zip").exists()
    assert (artifact_dir / "ranked_predictions.csv").exists()
    assert (artifact_dir / "monthly_metrics.csv").exists()
    assert (artifact_dir / "split_summary.csv").exists()

    setup_results = pd.read_csv(output_root / train.SUMMARY_FILE_NAME)
    row = setup_results.iloc[0]
    assert row["FrameworkID"] == "pit_1m_context_t1_dailyflat"
    assert int(row["MonthlyFeatureDim"]) == len(config.MODEL_FEATURE_COLUMNS)
    assert int(row["InputDim"]) == len(config.MODEL_FEATURE_COLUMNS) + (config.MAX_MONTHLY_OBS * config.DAILY_STRIP_CHANNELS) + config.MAX_MONTHLY_OBS
    assert bool(row["UsesDailyStrip"])
    assert int(row["DailyStripChannels"]) == config.DAILY_STRIP_CHANNELS
    assert int(row["DailyStripLength"]) == config.MAX_MONTHLY_OBS
    assert row["DailyFusionMode"] == "flat_concat"
    assert row["DailyPathScope"] == "shared"
    assert row["DailyChannelNames"] == ",".join(config.DAILY_STRIP_CHANNEL_NAMES)


def test_train_setup_supports_1m_daily_flat_no_context_framework(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    daily_path = tmp_path / "daily.csv"
    output_root = tmp_path / "outputs"
    panel = make_panel()
    daily = make_daily_market_series(panel)
    panel.to_csv(panel_path, index=False)
    daily.to_csv(daily_path, index=False)

    setup = train.SetupConfig(
        setup_id="FW-1M-T1-DAILYFLAT-S42",
        framework_id="pit_1m_t1_dailyflat",
        total_timesteps=8,
        seed=42,
    )
    artifact_dir = train.train_setup(panel_path=panel_path, daily_path=daily_path, setup=setup, output_root=output_root)

    assert (artifact_dir / "best_model.zip").exists()
    assert (artifact_dir / "final_model.zip").exists()
    assert (artifact_dir / "ranked_predictions.csv").exists()
    assert (artifact_dir / "monthly_metrics.csv").exists()
    assert (artifact_dir / "split_summary.csv").exists()

    setup_results = pd.read_csv(output_root / train.SUMMARY_FILE_NAME)
    row = setup_results.iloc[0]
    assert row["FrameworkID"] == "pit_1m_t1_dailyflat"
    assert int(row["MonthlyFeatureDim"]) == len(config.MODEL_FEATURE_COLUMNS)
    assert int(row["InputDim"]) == len(config.MODEL_FEATURE_COLUMNS) + (config.MAX_MONTHLY_OBS * config.DAILY_STRIP_CHANNELS) + config.MAX_MONTHLY_OBS
    assert bool(row["UsesDailyStrip"])
    assert int(row["DailyStripChannels"]) == config.DAILY_STRIP_CHANNELS
    assert int(row["DailyStripLength"]) == config.MAX_MONTHLY_OBS
    assert row["DailyFusionMode"] == "flat_concat"
    assert row["DailyPathScope"] == "shared"
    assert row["DailyChannelNames"] == ",".join(config.DAILY_STRIP_CHANNEL_NAMES)


def test_train_setup_supports_3m_daily_flat_no_context_framework(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    daily_path = tmp_path / "daily.csv"
    output_root = tmp_path / "outputs"
    panel = make_panel()
    daily = make_daily_market_series(panel)
    panel.to_csv(panel_path, index=False)
    daily.to_csv(daily_path, index=False)

    setup = train.SetupConfig(
        setup_id="FW-STACK3M-T1-DAILYFLAT-S42",
        framework_id="pit_3m_flat_t1_dailyflat",
        total_timesteps=8,
        seed=42,
    )
    artifact_dir = train.train_setup(panel_path=panel_path, daily_path=daily_path, setup=setup, output_root=output_root)

    assert (artifact_dir / "best_model.zip").exists()
    assert (artifact_dir / "final_model.zip").exists()
    assert (artifact_dir / "ranked_predictions.csv").exists()
    assert (artifact_dir / "monthly_metrics.csv").exists()
    assert (artifact_dir / "split_summary.csv").exists()

    setup_results = pd.read_csv(output_root / train.SUMMARY_FILE_NAME)
    row = setup_results.iloc[0]
    assert row["FrameworkID"] == "pit_3m_flat_t1_dailyflat"
    assert int(row["MonthlyFeatureDim"]) == len(config.MODEL_FEATURE_COLUMNS) * 3
    assert int(row["InputDim"]) == (len(config.MODEL_FEATURE_COLUMNS) * 3) + (config.MAX_MONTHLY_OBS * config.DAILY_STRIP_CHANNELS) + config.MAX_MONTHLY_OBS
    assert bool(row["UsesDailyStrip"])
    assert int(row["DailyStripChannels"]) == config.DAILY_STRIP_CHANNELS
    assert int(row["DailyStripLength"]) == config.MAX_MONTHLY_OBS
    assert row["DailyFusionMode"] == "flat_concat"
    assert row["DailyPathScope"] == "shared"
    assert row["DailyChannelNames"] == ",".join(config.DAILY_STRIP_CHANNEL_NAMES)


@pytest.mark.parametrize(
    ("setup_id", "framework_id", "expected_monthly_feature_dim", "expected_input_dim", "expected_fusion_mode"),
    (
        (
            "FW-1M-T1-DAILY-ACTOR-CNN-S42",
            "pit_1m_t1_daily_actor_cnn",
            len(config.MODEL_FEATURE_COLUMNS),
            len(config.MODEL_FEATURE_COLUMNS),
            "cnn_pool",
        ),
        (
            "FW-1M-T1-DAILY-ACTOR-FLAT-S42",
            "pit_1m_t1_daily_actor_flat",
            len(config.MODEL_FEATURE_COLUMNS),
            len(config.MODEL_FEATURE_COLUMNS) + (config.MAX_MONTHLY_OBS * config.DAILY_STRIP_CHANNELS) + config.MAX_MONTHLY_OBS,
            "flat_concat",
        ),
        (
            "FW-3M-CONTEXT-T1-DAILY-ACTOR-CNN-S42",
            "pit_3m_flat_context_t1_daily_actor_cnn",
            len(config.MODEL_FEATURE_COLUMNS) * 3,
            len(config.MODEL_FEATURE_COLUMNS) * 3,
            "cnn_pool",
        ),
        (
            "FW-3M-CONTEXT-T1-DAILY-ACTOR-FLAT-S42",
            "pit_3m_flat_context_t1_daily_actor_flat",
            len(config.MODEL_FEATURE_COLUMNS) * 3,
            (len(config.MODEL_FEATURE_COLUMNS) * 3) + (config.MAX_MONTHLY_OBS * config.DAILY_STRIP_CHANNELS) + config.MAX_MONTHLY_OBS,
            "flat_concat",
        ),
    ),
)
def test_train_setup_supports_actor_only_daily_frameworks(
    tmp_path: Path,
    setup_id: str,
    framework_id: str,
    expected_monthly_feature_dim: int,
    expected_input_dim: int,
    expected_fusion_mode: str,
) -> None:
    panel_path = tmp_path / "panel.csv"
    daily_path = tmp_path / "daily.csv"
    output_root = tmp_path / "outputs"
    panel = make_panel()
    daily = make_daily_market_series(panel)
    panel.to_csv(panel_path, index=False)
    daily.to_csv(daily_path, index=False)

    setup = train.SetupConfig(
        setup_id=setup_id,
        framework_id=framework_id,
        total_timesteps=8,
        seed=42,
    )
    artifact_dir = train.train_setup(panel_path=panel_path, daily_path=daily_path, setup=setup, output_root=output_root)

    assert (artifact_dir / "best_model.zip").exists()
    assert (artifact_dir / "final_model.zip").exists()
    assert (artifact_dir / "ranked_predictions.csv").exists()
    assert (artifact_dir / "monthly_metrics.csv").exists()
    assert (artifact_dir / "split_summary.csv").exists()

    setup_results = pd.read_csv(output_root / train.SUMMARY_FILE_NAME)
    row = setup_results.iloc[0]
    assert row["FrameworkID"] == framework_id
    assert int(row["MonthlyFeatureDim"]) == expected_monthly_feature_dim
    assert int(row["InputDim"]) == expected_input_dim
    assert bool(row["UsesDailyStrip"])
    assert int(row["DailyStripChannels"]) == config.DAILY_STRIP_CHANNELS
    assert int(row["DailyStripLength"]) == config.MAX_MONTHLY_OBS
    assert row["DailyFusionMode"] == expected_fusion_mode
    assert row["DailyPathScope"] == "actor_only"
    assert row["DailyChannelNames"] == ",".join(config.DAILY_STRIP_CHANNEL_NAMES)

    metadata = pd.read_json(artifact_dir / "setup_metadata.json", typ="series")
    assert metadata["framework_id"] == framework_id
    assert metadata["framework_spec"]["daily_path_scope"] == "actor_only"
    assert metadata["framework_spec"]["daily_fusion_mode"] == expected_fusion_mode
    assert metadata["framework_spec"]["uses_daily_strip"] is True


@pytest.mark.parametrize(
    ("setup_id", "feature_profile_id", "change_type", "changed_feature", "variant_id"),
    (
        ("FT-BASE-3M-CONTEXT-S42", config.DEFAULT_FEATURE_PROFILE_ID, "baseline", "", "base"),
        ("FT-ABL-DROP-RSI_14-S42", "drop_rsi_14", "drop_feature", "rsi_14", "drop_rsi_14"),
        ("FT-VAR-ATR_PCT_20-ATR_PCT_14-S42", "atr_pct_14", "alter_feature", "atr_pct_20", "atr_pct_14"),
    ),
)
def test_train_setup_supports_feature_phase_metadata_and_smoke_runs(
    tmp_path: Path,
    setup_id: str,
    feature_profile_id: str,
    change_type: str,
    changed_feature: str,
    variant_id: str,
) -> None:
    panel_path = tmp_path / "panel.csv"
    output_root = tmp_path / "outputs"
    make_panel().to_csv(panel_path, index=False)

    setup = train.SetupConfig(
        setup_id=setup_id,
        framework_id=config.FEATURE_PHASE_BASE_FRAMEWORK_ID,
        total_timesteps=8,
        study_phase=config.FEATURE_PHASE_NAME,
        base_framework_id=config.FEATURE_PHASE_BASE_FRAMEWORK_ID,
        feature_profile_id=feature_profile_id,
        change_type=change_type,
        changed_feature=changed_feature,
        variant_id=variant_id,
        seed=42,
    )
    artifact_dir = train.train_setup(panel_path=panel_path, daily_path=None, setup=setup, output_root=output_root)

    assert (artifact_dir / "best_model.zip").exists()
    assert (artifact_dir / "setup_metadata.json").exists()
    assert (output_root / train.SUMMARY_FILE_NAME).exists()

    setup_results = pd.read_csv(output_root / train.SUMMARY_FILE_NAME)
    row = setup_results.iloc[0]
    assert row["StudyPhase"] == config.FEATURE_PHASE_NAME
    assert row["FrameworkID"] == config.FEATURE_PHASE_BASE_FRAMEWORK_ID
    assert row["BaseFrameworkID"] == config.FEATURE_PHASE_BASE_FRAMEWORK_ID
    assert row["FeatureProfileID"] == feature_profile_id
    assert row["ChangeType"] == change_type
    actual_changed_feature = "" if pd.isna(row["ChangedFeature"]) else row["ChangedFeature"]
    assert actual_changed_feature == changed_feature
    assert row["VariantID"] == variant_id

    metadata = pd.read_json(artifact_dir / "setup_metadata.json", typ="series")
    assert metadata["study_phase"] == config.FEATURE_PHASE_NAME
    assert metadata["framework_id"] == config.FEATURE_PHASE_BASE_FRAMEWORK_ID
    assert metadata["base_framework_id"] == config.FEATURE_PHASE_BASE_FRAMEWORK_ID
    assert metadata["feature_profile_id"] == feature_profile_id
    assert metadata["change_type"] == change_type
    assert metadata["changed_feature"] == changed_feature
    assert metadata["variant_id"] == variant_id
    if feature_profile_id == "atr_pct_14":
        assert metadata["feature_profile"]["parameters"]["atr_period"] == 14


def test_train_setup_rejects_feature_phase_runs_on_non_winner_backbones(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    output_root = tmp_path / "outputs"
    make_panel().to_csv(panel_path, index=False)

    setup = train.SetupConfig(
        setup_id="FT-BAD-1M-S42",
        framework_id="pit_1m_shared_mlp",
        total_timesteps=8,
        study_phase=config.FEATURE_PHASE_NAME,
        base_framework_id=config.FEATURE_PHASE_BASE_FRAMEWORK_ID,
        feature_profile_id=config.DEFAULT_FEATURE_PROFILE_ID,
        change_type="baseline",
        variant_id="base",
        seed=42,
    )

    with pytest.raises(ValueError, match="Feature comparison runs must use"):
        train.train_setup(panel_path=panel_path, daily_path=None, setup=setup, output_root=output_root)


def test_repaired_protocol_uses_inner_validation_and_outer_validation_in_artifacts(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    output_root = tmp_path / "outputs"
    make_panel().to_csv(panel_path, index=False)

    setup = train.SetupConfig(
        setup_id="FW-RELOCK-3M-S42",
        framework_id="pit_1m_shared_mlp",
        total_timesteps=8,
        seed=42,
    )
    artifact_dir = train.train_setup(panel_path=panel_path, daily_path=None, setup=setup, output_root=output_root)

    split_summary = pd.read_csv(artifact_dir / "split_summary.csv")
    assert set(split_summary["split"]) == {"train", "inner_validation", "validation", "test"}

    setup_results = pd.read_csv(output_root / train.SUMMARY_FILE_NAME)
    row = setup_results.iloc[0]
    assert row["ComparisonProtocolID"] == config.DEFAULT_COMPARISON_PROTOCOL_ID
    assert row["CheckpointProvenance"] == "best_inner_validation"
    assert int(row["InnerValidationMonths"]) == 2
    assert int(row["ValidationMonths"]) == 4
    assert row["TrainingMethodID"] == config.DEFAULT_TRAINING_METHOD_ID
    assert row["ObjectiveProfileID"] == config.DEFAULT_OBJECTIVE_PROFILE_ID
    assert row["RewardProfileID"] == config.DEFAULT_REWARD_PROFILE_ID
    assert row["InputFeatureSetID"] == config.DEFAULT_INPUT_FEATURE_SET_ID
    assert row["ReportedCheckpoint"].endswith("best_model.zip")

    metadata = pd.read_json(artifact_dir / "setup_metadata.json", typ="series")
    assert metadata["comparison_protocol_id"] == config.DEFAULT_COMPARISON_PROTOCOL_ID
    assert metadata["comparison_protocol"]["checkpoint_selection_split_name"] == "inner_validation"
    assert metadata["comparison_protocol"]["comparison_split_name"] == "validation"
    assert metadata["checkpoint_provenance"] == "best_inner_validation"


def test_environment_supports_ordered_cycle_sampling(tmp_path: Path) -> None:
    months = ["2010-10", "2010-11", "2010-12"] + [f"2011-{month:02d}" for month in range(1, 9)]
    rows: list[dict[str, object]] = []
    for month_index, date in enumerate(months, start=1):
        for asset_index, asset_id in enumerate(("A", "B", "C", "D"), start=1):
            base = min(0.02 * month_index, 0.90)
            rows.append(
                {
                    "Date": date,
                    "AssetID": asset_id,
                    "AssetName": f"Asset {asset_id}",
                    "AssetGroup": "Equity",
                    **{column: min(base + (asset_index * 0.01), 0.99) for column in config.MODEL_FEATURE_COLUMNS},
                    "realized_vol": (asset_index - 1) / 3.0,
                    "realized_downside_dev": (asset_index - 1) / 3.0,
                    "realized_max_drawdown": (asset_index - 1) / 3.0,
                    "realized_risk": (asset_index - 1) / 3.0,
                    "realized_rank": float(asset_index),
                }
            )
    panel = pd.DataFrame(rows)[config.PANEL_METADATA_COLUMNS + config.MODEL_FEATURE_COLUMNS + config.TARGET_COLUMNS]
    panel_path = tmp_path / "ordered_panel.csv"
    panel.to_csv(panel_path, index=False)

    ordered_env = AssetRiskEnv(
        panel_path=panel_path,
        split_name="train",
        framework_id="pit_1m_shared_mlp",
        sampling_mode="ordered_cycle",
    )
    first_observation, first_info = ordered_env.reset(options={"restart_sequence": True})
    second_observation, second_info = ordered_env.reset()
    assert first_observation["features"].shape == (4, 11)
    assert first_info["Date"] == "2011-01"
    assert second_info["Date"] == "2011-02"


def test_environment_block_random_6m_samples_contiguous_months(tmp_path: Path) -> None:
    months = ["2010-10", "2010-11", "2010-12"] + [f"2011-{month:02d}" for month in range(1, 9)]
    rows: list[dict[str, object]] = []
    for month_index, date in enumerate(months, start=1):
        for asset_index, asset_id in enumerate(("A", "B", "C", "D"), start=1):
            base = min(0.02 * month_index, 0.90)
            row = {
                "Date": date,
                "AssetID": asset_id,
                "AssetName": f"Asset {asset_id}",
                "AssetGroup": "Equity",
            }
            for column in config.MODEL_FEATURE_COLUMNS:
                row[column] = min(base + (asset_index * 0.01), 0.99)
            row["realized_vol"] = (asset_index - 1) / 3.0
            row["realized_downside_dev"] = (asset_index - 1) / 3.0
            row["realized_max_drawdown"] = (asset_index - 1) / 3.0
            row["realized_risk"] = (asset_index - 1) / 3.0
            row["realized_rank"] = float(asset_index)
            rows.append(row)
    panel = pd.DataFrame(rows)[config.PANEL_METADATA_COLUMNS + config.MODEL_FEATURE_COLUMNS + config.TARGET_COLUMNS]
    panel_path = tmp_path / "long_panel.csv"
    panel.to_csv(panel_path, index=False)

    env = AssetRiskEnv(panel_path=panel_path, split_name="train", framework_id="pit_1m_shared_mlp", sampling_mode="block_random_6m")
    seen_dates: list[str] = []
    observation, info = env.reset(seed=42, options={"restart_sequence": True})
    seen_dates.append(info["Date"])
    for _ in range(5):
        env.step(np.full(env.max_assets, 0.5, dtype=np.float32))
        observation, info = env.reset()
        seen_dates.append(info["Date"])
    expected_dates = pd.period_range(start=seen_dates[0], periods=6, freq="M").strftime(config.DATE_FORMAT_MONTHLY).tolist()
    assert seen_dates == expected_dates


def test_objective_and_reward_profiles_apply_expected_weights() -> None:
    panel = make_panel()
    objective = get_objective_profile("risk_v2_downside_050")
    adjusted = apply_objective_profile(panel, objective)
    first_row = adjusted.iloc[0]
    expected = (
        (0.25 * first_row["realized_vol"])
        + (0.50 * first_row["realized_downside_dev"])
        + (0.25 * first_row["realized_max_drawdown"])
    )
    assert first_row["realized_risk"] == pytest.approx(expected)

    reward = get_reward_profile("reward_v2_rank85_mse15")
    metrics = compute_month_metrics(
        predicted=np.array([0.0, 0.5, 1.0]),
        realized=np.array([0.0, 0.5, 1.0]),
        date="2023-01",
        reward_profile=reward,
    )
    assert metrics.spearman == pytest.approx(1.0)
    assert metrics.mse == pytest.approx(0.0)
    assert metrics.reward == pytest.approx(1.0)

    vol_only = get_objective_profile("risk_v4_vol_only")
    assert vol_only.weight_map() == {
        "realized_vol": pytest.approx(1.0),
        "realized_downside_dev": pytest.approx(0.0),
        "realized_max_drawdown": pytest.approx(0.0),
    }

    pure_rank_reward = get_reward_profile("reward_v3_rank100_mse00")
    pure_rank_metrics = compute_month_metrics(
        predicted=np.array([0.0, 0.3, 0.6, 0.9]),
        realized=np.array([0.0, 0.3, 0.6, 0.9]),
        date="2023-01",
        reward_profile=pure_rank_reward,
    )
    assert pure_rank_metrics.reward == pytest.approx(1.0)

    balanced_reward = get_reward_profile("reward_v4_rank50_mse50")
    balanced_metrics = compute_month_metrics(
        predicted=np.array([0.1, 0.4, 0.8]),
        realized=np.array([0.0, 0.5, 1.0]),
        date="2023-01",
        reward_profile=balanced_reward,
    )
    expected_mse = float(np.mean(np.square(np.array([0.1, 0.4, 0.8]) - np.array([0.0, 0.5, 1.0]))))
    assert balanced_metrics.spearman == pytest.approx(1.0)
    assert balanced_metrics.mse == pytest.approx(expected_mse)
    assert balanced_metrics.reward == pytest.approx((0.50 * 1.0) + (0.50 * (1.0 - expected_mse)))

    tail_reward = get_reward_profile("reward_v5_rank60_mse20_highoverlap20")
    tail_metrics = compute_month_metrics(
        predicted=np.array([0.1, 0.2, 0.8, 0.9]),
        realized=np.array([0.1, 0.2, 0.8, 0.9]),
        date="2023-01",
        reward_profile=tail_reward,
    )
    assert tail_metrics.high_risk_top25_overlap == pytest.approx(1.0)
    assert tail_metrics.reward == pytest.approx(
        (0.60 * tail_metrics.spearman)
        + (0.20 * (1.0 - tail_metrics.mse))
        + (0.20 * tail_metrics.high_risk_top25_overlap)
    )


def test_tail_overlap_metrics_report_exact_quarter_tail_sets() -> None:
    predictions = pd.DataFrame(
        {
            "Date": ["2023-01"] * 4,
            "Split": ["validation"] * 4,
            "AssetID": ["A", "B", "C", "D"],
            "PredictedRisk": [0.10, 0.90, 0.80, 0.20],
            "realized_risk": [0.10, 0.20, 0.80, 0.90],
        }
    )

    monthly_metrics, split_summary = evaluate_prediction_frame(predictions)
    details = tail_overlap_details(predictions)

    assert monthly_metrics.iloc[0]["high_risk_top25_overlap"] == pytest.approx(0.0)
    assert monthly_metrics.iloc[0]["low_risk_top25_overlap"] == pytest.approx(1.0)
    assert monthly_metrics.iloc[0]["high_risk_top25_missed"] == "D"
    assert monthly_metrics.iloc[0]["high_risk_top25_false_positives"] == "B"
    assert split_summary.iloc[0]["mean_high_risk_top25_overlap"] == pytest.approx(0.0)
    assert split_summary.iloc[0]["worst_high_risk_top25_overlap"] == pytest.approx(0.0)
    assert details["tail_count"] == 1


def test_framework_phase_can_rescore_candidate_under_anchor_without_mutating_predictions(tmp_path: Path) -> None:
    panel = make_panel_with_distinct_targets()
    panel_path = tmp_path / "panel.csv"
    panel.to_csv(panel_path, index=False)

    candidate_panel = apply_objective_profile(panel.copy(), "risk_v5_downside_only")
    candidate_predictions = make_validation_predictions(
        candidate_panel,
        predicted_scores={"A": 0.10, "B": 0.55, "C": 0.35, "D": 0.90},
    )
    artifact_dir = tmp_path / "candidate_artifacts"
    _, split_summary = write_framework_artifacts(
        artifact_dir=artifact_dir,
        panel_path=panel_path,
        predictions=candidate_predictions,
        reward_profile_id=config.DEFAULT_REWARD_PROFILE_ID,
    )
    row = pd.Series(
        {
            "ArtifactsDir": str(artifact_dir),
            "ComparisonSplit": "validation",
            "ValidationMeanReward": split_summary.loc[split_summary["split"] == "validation", "mean_reward"].iloc[0],
            "ValidationMeanSpearman": split_summary.loc[split_summary["split"] == "validation", "mean_spearman"].iloc[0],
            "ObjectiveProfileID": "risk_v5_downside_only",
            "RewardProfileID": config.DEFAULT_REWARD_PROFILE_ID,
        }
    )

    predictions_path = artifact_dir / "ranked_predictions.csv"
    before = predictions_path.read_bytes()
    rescored = framework_phase.anchor_rescored_metrics_for_setup(row)
    after = predictions_path.read_bytes()

    assert before == after
    assert rescored["validation_reward"] != pytest.approx(float(row["ValidationMeanReward"]))


def test_reward_profile_comparison_uses_anchor_metrics_for_promotion(tmp_path: Path) -> None:
    output_root = tmp_path / "experiments"
    output_root.mkdir(parents=True, exist_ok=True)
    panel = make_panel_with_distinct_targets()
    panel_path = tmp_path / "panel.csv"
    panel.to_csv(panel_path, index=False)

    predicted_scores = {"A": 0.10, "B": 0.35, "C": 0.70, "D": 0.95}
    baseline_predictions = make_validation_predictions(panel, predicted_scores=predicted_scores)
    candidate_predictions = baseline_predictions.copy()

    baseline_artifact_dir = output_root / "FW-RELK-BASE-S42"
    candidate_artifact_dir = output_root / "FW-RELK-REWARD-S42"
    _, baseline_summary = write_framework_artifacts(
        artifact_dir=baseline_artifact_dir,
        panel_path=panel_path,
        predictions=baseline_predictions,
        reward_profile_id=config.DEFAULT_REWARD_PROFILE_ID,
    )
    _, candidate_summary = write_framework_artifacts(
        artifact_dir=candidate_artifact_dir,
        panel_path=panel_path,
        predictions=candidate_predictions,
        reward_profile_id="reward_v2_rank85_mse15",
    )

    baseline_setup_id = framework_phase.relock_setup_id(
        framework_id="pit_3m_flat_context",
        objective_profile_id=config.DEFAULT_OBJECTIVE_PROFILE_ID,
        reward_profile_id=config.DEFAULT_REWARD_PROFILE_ID,
        training_method_id=config.DEFAULT_TRAINING_METHOD_ID,
        seed=42,
    )
    candidate_setup_id = framework_phase.relock_setup_id(
        framework_id="pit_3m_flat_context",
        objective_profile_id=config.DEFAULT_OBJECTIVE_PROFILE_ID,
        reward_profile_id="reward_v2_rank85_mse15",
        training_method_id=config.DEFAULT_TRAINING_METHOD_ID,
        seed=42,
    )
    baseline_reward = baseline_summary.loc[baseline_summary["split"] == "validation", "mean_reward"].iloc[0]
    baseline_spearman = baseline_summary.loc[baseline_summary["split"] == "validation", "mean_spearman"].iloc[0]
    candidate_reward = candidate_summary.loc[candidate_summary["split"] == "validation", "mean_reward"].iloc[0]
    pd.DataFrame(
        [
            {
                "SetupID": baseline_setup_id,
                "TimestampUTC": "2026-04-22T10:00:00+00:00",
                "StudyPhase": config.FRAMEWORK_PHASE_NAME,
                "PolicySemanticsVersion": config.POLICY_SEMANTICS_VERSION,
                "FrameworkID": "pit_3m_flat_context",
                "ComparisonProtocolID": config.DEFAULT_COMPARISON_PROTOCOL_ID,
                "CheckpointProvenance": "best_inner_validation",
                "ObjectiveProfileID": config.DEFAULT_OBJECTIVE_PROFILE_ID,
                "RewardProfileID": config.DEFAULT_REWARD_PROFILE_ID,
                "TrainingMethodID": config.DEFAULT_TRAINING_METHOD_ID,
                "Notes": framework_phase.PROTOCOL_BASELINE_NOTE,
                "ArtifactsDir": str(baseline_artifact_dir),
                "ValidationMeanReward": baseline_reward,
                "ValidationMeanSpearman": baseline_spearman,
            },
            {
                "SetupID": candidate_setup_id,
                "TimestampUTC": "2026-04-22T11:00:00+00:00",
                "StudyPhase": config.FRAMEWORK_PHASE_NAME,
                "PolicySemanticsVersion": config.POLICY_SEMANTICS_VERSION,
                "FrameworkID": "pit_3m_flat_context",
                "ComparisonProtocolID": config.DEFAULT_COMPARISON_PROTOCOL_ID,
                "CheckpointProvenance": "best_inner_validation",
                "ObjectiveProfileID": config.DEFAULT_OBJECTIVE_PROFILE_ID,
                "RewardProfileID": "reward_v2_rank85_mse15",
                "TrainingMethodID": config.DEFAULT_TRAINING_METHOD_ID,
                "Notes": framework_phase.REWARD_AUDIT_NOTE,
                "ArtifactsDir": str(candidate_artifact_dir),
                "ValidationMeanReward": candidate_reward,
                "ValidationMeanSpearman": baseline_spearman + 0.01,
            },
        ]
    ).to_csv(output_root / train.SUMMARY_FILE_NAME, index=False)

    comparison_path = framework_phase.write_outer_validation_comparison(
        baseline_setup_id=baseline_setup_id,
        candidate_setup_id=candidate_setup_id,
        output_root=output_root,
    )
    payload = json.loads(comparison_path.read_text(encoding="utf-8"))
    results = framework_phase.load_framework_phase_results(output_root=output_root)

    assert payload["candidate_validation_metrics"]["native_reward"] != pytest.approx(
        payload["candidate_validation_metrics"]["anchor_reward"]
    )
    assert payload["decision"]["label"] == "stop: weak sensitivity"
    assert framework_phase.beats_on_outer_validation(results, baseline_setup_id, candidate_setup_id) is False


def test_prediction_similarity_summary_reports_correlations_and_mad() -> None:
    baseline = pd.DataFrame(
        {
            "Date": ["2023-01", "2023-01", "2023-02", "2023-02"],
            "AssetID": ["A", "B", "A", "B"],
            "Split": ["validation", "validation", "validation", "validation"],
            "PredictedRisk": [0.10, 0.90, 0.20, 0.80],
        }
    )
    candidate = pd.DataFrame(
        {
            "Date": ["2023-01", "2023-01", "2023-02", "2023-02"],
            "AssetID": ["A", "B", "A", "B"],
            "Split": ["validation", "validation", "validation", "validation"],
            "PredictedRisk": [0.15, 0.85, 0.25, 0.75],
        }
    )

    summary = framework_phase.prediction_similarity_summary(baseline, candidate)

    assert summary["paired_rows"] == 4
    assert summary["paired_months"] == 2
    assert summary["pearson_correlation"] == pytest.approx(0.9997, abs=1e-4)
    assert summary["spearman_correlation"] == pytest.approx(1.0)
    assert summary["mean_absolute_difference"] == pytest.approx(0.05)


def test_train_setup_supports_shadow_additive_input_feature_set(tmp_path: Path) -> None:
    panel = make_panel().copy()
    candidate = get_shadow_candidate("distance_to_1m_low")
    panel[candidate.candidate_id] = panel["distance_to_3m_high"]
    panel_path = tmp_path / "shadow_panel.csv"
    output_root = tmp_path / "outputs"
    panel.to_csv(panel_path, index=False)

    input_feature_set = get_input_feature_set(candidate.input_feature_set_id)
    setup = train.SetupConfig(
        setup_id="FT-SHADOW-DISTANCE-LOW-S42",
        framework_id="pit_3m_flat_context",
        total_timesteps=8,
        input_feature_set_id=input_feature_set.input_feature_set_id,
        seed=42,
    )
    artifact_dir = train.train_setup(panel_path=panel_path, daily_path=None, setup=setup, output_root=output_root)

    assert (artifact_dir / "split_summary.csv").exists()
    setup_results = pd.read_csv(output_root / train.SUMMARY_FILE_NAME)
    row = setup_results.iloc[0]
    assert row["InputFeatureSetID"] == input_feature_set.input_feature_set_id
    assert row["FeatureColumns"].split(",")[-1] == candidate.candidate_id
    assert int(row["MonthlyFeatureDim"]) == len(input_feature_set.feature_columns) * 3


def test_framework_phase_doc_sync_renders_relock_sections(tmp_path: Path) -> None:
    output_root = tmp_path / "experiments"
    output_root.mkdir(parents=True, exist_ok=True)
    summary_path = output_root / train.SUMMARY_FILE_NAME
    candidate_artifact_dir = output_root / "FW-RELK-CANDIDATE-S42"
    candidate_artifact_dir.mkdir(parents=True, exist_ok=True)
    (candidate_artifact_dir / "outer_validation_comparison.json").write_text(
        json.dumps(
            {
                "baseline_setup_id": "FW-RELK-INCUMBENT-S42",
                "candidate_setup_id": "FW-RELK-CANDIDATE-S42",
                "candidate_validation_metrics": {
                    "native_reward": 0.6840,
                    "native_spearman": 0.5750,
                    "anchor_reward": 0.6830,
                    "anchor_spearman": 0.5740,
                },
                "prediction_similarity": {
                    "pearson_correlation": 0.9992,
                    "spearman_correlation": 0.9991,
                    "mean_absolute_difference": 0.0011,
                },
                "decision": {"label": "stop: weak sensitivity"},
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    baseline_setup_id = framework_phase.relock_setup_id(
        framework_id="pit_3m_flat_context",
        objective_profile_id=config.DEFAULT_OBJECTIVE_PROFILE_ID,
        reward_profile_id=config.DEFAULT_REWARD_PROFILE_ID,
        training_method_id=config.DEFAULT_TRAINING_METHOD_ID,
        seed=42,
    )
    pd.DataFrame(
        [
            {
                "SetupID": baseline_setup_id,
                "TimestampUTC": "2026-04-21T10:00:00+00:00",
                "StudyPhase": config.FRAMEWORK_PHASE_NAME,
                "PolicySemanticsVersion": config.POLICY_SEMANTICS_VERSION,
                "FrameworkID": "pit_3m_flat_context",
                "ComparisonProtocolID": config.DEFAULT_COMPARISON_PROTOCOL_ID,
                "CheckpointProvenance": "best_inner_validation",
                "ObjectiveProfileID": config.DEFAULT_OBJECTIVE_PROFILE_ID,
                "RewardProfileID": config.DEFAULT_REWARD_PROFILE_ID,
                "TrainingMethodID": config.DEFAULT_TRAINING_METHOD_ID,
                "Notes": framework_phase.PROTOCOL_BASELINE_NOTE,
                "ValidationMeanReward": 0.6850,
                "ValidationMeanSpearman": 0.5770,
            },
            {
                "SetupID": "FW-RELK-CANDIDATE-S42",
                "TimestampUTC": "2026-04-21T11:00:00+00:00",
                "StudyPhase": config.FRAMEWORK_PHASE_NAME,
                "PolicySemanticsVersion": config.POLICY_SEMANTICS_VERSION,
                "FrameworkID": "pit_3m_flat_context",
                "ComparisonProtocolID": config.DEFAULT_COMPARISON_PROTOCOL_ID,
                "CheckpointProvenance": "best_inner_validation",
                "ObjectiveProfileID": "risk_v5_downside_only",
                "RewardProfileID": config.DEFAULT_REWARD_PROFILE_ID,
                "TrainingMethodID": config.DEFAULT_TRAINING_METHOD_ID,
                "Notes": framework_phase.OBJECTIVE_AUDIT_NOTE,
                "ArtifactsDir": str(candidate_artifact_dir),
                "ValidationMeanReward": 0.6840,
                "ValidationMeanSpearman": 0.5750,
            },
            {
                "SetupID": "FW-OLD-PIT_1M_SHARED_MLP-S42",
                "TimestampUTC": "2026-04-20T10:00:00+00:00",
                "StudyPhase": config.FRAMEWORK_PHASE_NAME,
                "PolicySemanticsVersion": config.POLICY_SEMANTICS_VERSION,
                "FrameworkID": "pit_1m_shared_mlp",
                "CheckpointProvenance": "final",
                "ValidationMeanReward": 0.5000,
                "ValidationMeanSpearman": 0.4000,
            }
        ]
    ).to_csv(summary_path, index=False)
    doc_path = tmp_path / "framework_phase.md"
    doc_path.write_text("# Framework Phase\n", encoding="utf-8")

    framework_phase.sync_framework_phase_doc(output_root=output_root, doc_path=doc_path)
    rendered = doc_path.read_text(encoding="utf-8")

    assert "## Comparison Protocol Audit" in rendered
    assert "## Objective Audit" in rendered
    assert "## Training Method Screens" in rendered
    assert baseline_setup_id in rendered
    assert config.DEFAULT_COMPARISON_PROTOCOL_ID in rendered
    assert config.DEFAULT_TRAINING_METHOD_ID in rendered
    assert "Native Validation Reward" in rendered
    assert "Anchor Validation Reward" in rendered
    assert "Prediction Similarity To Baseline" in rendered
    assert "stop: weak sensitivity" in rendered
    assert "FW-OLD-PIT_1M_SHARED_MLP-S42" not in rendered
