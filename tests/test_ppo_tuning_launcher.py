from __future__ import annotations

import json

from src import config
from src.training import confirm_ppo_tuning, tune_ppo


class DummyTrial:
    def suggest_float(self, name: str, low: float, high: float, log: bool = False) -> float:
        assert low < high
        if name == "learning_rate":
            assert log is True
        return low

    def suggest_categorical(self, name: str, choices: list[int] | list[float]) -> int | float:
        assert choices
        return choices[0]


def test_tuning_plan_defaults_to_locked_feature_phase_backbone(tmp_path) -> None:
    plan = tune_ppo.TuningPlan(output_root=str(tmp_path), storage_path=str(tmp_path / "study.sqlite3"))

    assert plan.framework_id == config.FEATURE_PHASE_BASE_FRAMEWORK_ID
    assert plan.seed == 42
    assert plan.storage_url().startswith("sqlite:///")

    plan_path = tune_ppo.write_launch_plan(plan)
    with plan_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["study_name"] == tune_ppo.DEFAULT_STUDY_NAME
    assert payload["framework_id"] == config.FEATURE_PHASE_BASE_FRAMEWORK_ID
    assert payload["storage_url"] == plan.storage_url()


def test_sample_ppo_params_keeps_gamma_and_gae_out_of_first_search_space() -> None:
    params = tune_ppo.sample_ppo_params(DummyTrial())

    assert params["learning_rate"] == 1e-5
    assert params["n_steps"] == 128
    assert params["batch_size"] == 128
    assert "gamma" not in params
    assert "gae_lambda" not in params


def test_refined_search_space_uses_compatible_batch_sizes() -> None:
    params = tune_ppo.sample_ppo_params(DummyTrial(), search_space=tune_ppo.SEARCH_SPACE_REFINED)

    assert params["learning_rate"] == 2e-4
    assert params["n_steps"] == 256
    assert params["batch_size"] == 128
    assert params["n_epochs"] == 5
    assert "gamma" not in params
    assert "gae_lambda" not in params


def test_refined_search_space_uses_static_rollout_batch_distribution() -> None:
    assert tune_ppo._parse_rollout_batch_combo("512_512") == (512, 512)


def test_fixed_confirmation_runner_preserves_trial75_params() -> None:
    params = confirm_ppo_tuning.candidate_params("trial75")
    run = confirm_ppo_tuning.FixedRun(run_id="trial75", params=params, seed=7, total_timesteps=1)

    assert run.setup_id() == "PPO-CONFIRM-TRIAL75-S7"
    assert params["learning_rate"] == 0.00038063905891585874
    assert params["n_steps"] == 256
    assert params["batch_size"] == 256
    assert params["n_epochs"] == 5
    assert run.gamma == 1.0
    assert run.gae_lambda == 1.0
