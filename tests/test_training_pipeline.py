from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch as th
from stable_baselines3 import PPO

from src import config
from src.environment.asset_risk_env import AssetRiskEnv
from src.training import evaluate, train
from src.training.frameworks import enabled_framework_ids, get_framework_spec
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
        },
    )


def test_framework_registry_exposes_active_frameworks() -> None:
    assert enabled_framework_ids() == (
        "pit_1m_shared_mlp",
        "pit_1m_context",
        "pit_1m_dailystrip_shared_cnn",
        "pit_3m_flat_shared_mlp",
        "pit_3m_flat_context",
    )


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
    make_panel().to_csv(panel_path, index=False)

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
    assert float(setup_results.iloc[0]["LearningRate"]) == config.FRAMEWORK_PPO_LEARNING_RATE
    assert int(setup_results.iloc[0]["EvalFrequency"]) == config.FRAMEWORK_PPO_EVAL_FREQUENCY
    assert setup_results.iloc[0]["ReportedCheckpoint"].endswith("best_model.zip")

    metadata = pd.read_json(artifact_dir / "setup_metadata.json", typ="series")
    assert metadata["study_phase"] == config.FRAMEWORK_PHASE_NAME
    assert metadata["action_distribution"] == config.ACTION_DISTRIBUTION_NAME
    assert metadata["policy_semantics_version"] == config.POLICY_SEMANTICS_VERSION
    assert metadata["framework_id"] == "pit_1m_shared_mlp"
    assert metadata["common_decision_start"] == config.TRAIN_START
    assert metadata["panel_state_start"] == config.PANEL_STATE_START

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
