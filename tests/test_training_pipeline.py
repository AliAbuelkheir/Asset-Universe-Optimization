from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from stable_baselines3 import PPO

from src import config
from src.environment.asset_risk_env import AssetRiskEnv
from src.training import evaluate, train
from src.training.policy import MaskedActorCriticPolicy


def make_panel() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    month_assets = {
        "2010-11": ["A", "B", "C", "D"],
        "2010-12": ["A", "B", "C"],
        "2023-01": ["A", "B", "C"],
        "2023-02": ["A", "B", "C"],
        "2025-03": ["A", "B", "C"],
    }
    ordered_months = list(month_assets.keys())
    for month_index, date in enumerate(ordered_months, start=1):
        assets = month_assets[date]
        for asset_index, asset_id in enumerate(assets, start=1):
            base = 0.05 * month_index
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
                    "usd_vol": min(0.2 + base, 0.99),
                    "cpi_trajectory": min(0.03 + base, 0.99),
                    "realized_vol": (asset_index - 1) / max(len(assets) - 1, 1),
                    "realized_downside_dev": (asset_index - 1) / max(len(assets) - 1, 1),
                    "realized_max_drawdown": (asset_index - 1) / max(len(assets) - 1, 1),
                    "realized_risk": (asset_index - 1) / max(len(assets) - 1, 1),
                    "realized_rank": float(asset_index),
                }
            )
    return pd.DataFrame(rows)[config.PANEL_METADATA_COLUMNS + config.MODEL_FEATURE_COLUMNS + config.TARGET_COLUMNS]


def make_policy_model(env: AssetRiskEnv) -> PPO:
    return PPO(
        MaskedActorCriticPolicy,
        env,
        n_steps=4,
        batch_size=4,
        n_epochs=1,
        gamma=1.0,
        gae_lambda=1.0,
        verbose=0,
        seed=42,
    )


def test_masked_policy_initializes_and_action_space_is_finite(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    make_panel().to_csv(panel_path, index=False)

    env = AssetRiskEnv(panel_path=panel_path, split_name="train")
    model = make_policy_model(env)

    assert env.action_space.shape == (4,)
    assert env.action_space.low.tolist() == [0.0, 0.0, 0.0, 0.0]
    assert env.action_space.high.tolist() == [1.0, 1.0, 1.0, 1.0]
    assert isinstance(model.policy, MaskedActorCriticPolicy)


def test_asset_risk_env_uses_single_step_episodes_and_split_specific_reset_modes(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    make_panel().to_csv(panel_path, index=False)

    train_env = AssetRiskEnv(panel_path=panel_path, split_name="train")
    validation_env = AssetRiskEnv(panel_path=panel_path, split_name="validation")

    observation, info = train_env.reset(seed=123)
    assert observation["features"].shape == (4, len(config.MODEL_FEATURE_COLUMNS))
    assert info["Split"] == "train"
    action = np.array([0.0, 0.5, 1.0, 0.25], dtype=np.float32)
    _, reward, terminated, truncated, step_info = train_env.step(action)
    assert terminated is True
    assert truncated is False
    assert step_info["Split"] == "train"
    assert isinstance(reward, float)

    ordered_dates: list[str] = []
    for index in range(validation_env.batch_count):
        _, reset_info = validation_env.reset(options={"restart_sequence": index == 0})
        ordered_dates.append(reset_info["Date"])
        validation_env.step(np.array([0.1, 0.2, 0.3, 0.0], dtype=np.float32))
    assert ordered_dates == ["2023-01", "2023-02"]


def test_masked_policy_is_row_order_invariant_and_ignores_padded_rows(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    make_panel().to_csv(panel_path, index=False)
    env = AssetRiskEnv(panel_path=panel_path, split_name="train")
    model = make_policy_model(env)

    obs = {
        "features": np.array(
            [
                [0.11] * len(config.MODEL_FEATURE_COLUMNS),
                [0.22] * len(config.MODEL_FEATURE_COLUMNS),
                [0.33] * len(config.MODEL_FEATURE_COLUMNS),
                [0.99] * len(config.MODEL_FEATURE_COLUMNS),
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
    padded_variant["features"][3] = np.array([0.01] * len(config.MODEL_FEATURE_COLUMNS), dtype=np.float32)

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
    assert np.allclose(entropy_a.detach().cpu().numpy(), entropy_b.detach().cpu().numpy())


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

    env = LoggingAssetRiskEnv(panel_path=panel_path, split_name="train", sampling_mode="random")
    model = make_policy_model(env)
    model.learn(total_timesteps=8, progress_bar=False)

    assert env.reset_splits
    assert set(env.reset_splits) == {"train"}


def test_evaluate_model_splits_and_write_artifacts(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    output_dir = tmp_path / "eval_outputs"
    make_panel().to_csv(panel_path, index=False)

    env = AssetRiskEnv(panel_path=panel_path, split_name="train")
    model = make_policy_model(env)
    model.learn(total_timesteps=8, progress_bar=False)

    predictions, monthly_metrics, split_summary = evaluate.evaluate_model_splits(
        model=model,
        panel_path=panel_path,
        split_names=("validation", "test"),
    )
    evaluate.write_evaluation_artifacts(
        output_dir=output_dir,
        predictions=predictions,
        monthly_metrics=monthly_metrics,
        split_summary=split_summary,
        setup_metadata={"source": "test"},
    )

    assert set(predictions["Split"]) == {"validation", "test"}
    assert (output_dir / "ranked_predictions.csv").exists()
    assert (output_dir / "monthly_metrics.csv").exists()
    assert (output_dir / "split_summary.csv").exists()
    assert (output_dir / "setup_metadata.json").exists()


def test_train_setup_writes_rl_artifacts_and_metadata(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.csv"
    output_root = tmp_path / "outputs"
    make_panel().to_csv(panel_path, index=False)

    setup = train.SetupConfig(
        setup_id="TEST-PPO-001",
        total_timesteps=8,
        learning_rate=3e-4,
        n_steps=4,
        batch_size=4,
        n_epochs=1,
        gamma=1.0,
        gae_lambda=1.0,
        clip_range=0.2,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        eval_frequency=4,
        seed=42,
    )
    artifact_dir = train.train_setup(panel_path=panel_path, setup=setup, output_root=output_root)

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
    assert set(setup_results["Framework"]) == {"ppo_monthly_ranking"}
    assert "ModelType" not in setup_results.columns
    assert setup_results.iloc[0]["ReportedCheckpoint"].endswith("best_model.zip")

    split_summary = pd.read_csv(artifact_dir / "split_summary.csv")
    assert set(split_summary["split"]) == {"train", "validation", "test"}

    metadata = pd.read_json(artifact_dir / "setup_metadata.json", typ="series")
    assert metadata["validation_selection_metric"] == "mean_reward"
    assert str(metadata["reported_checkpoint"]).endswith("best_model.zip")

    reloaded_model = evaluate.load_ppo_checkpoint(artifact_dir / "best_model.zip")
    assert isinstance(reloaded_model, PPO)
