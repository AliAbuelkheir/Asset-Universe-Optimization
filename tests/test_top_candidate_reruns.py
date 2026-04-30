from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src import config
from src.training import top_candidate_reruns


def test_refined50_top_candidate_runner_preserves_tuned_params(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured = {}

    def fake_train_setup(panel_path, daily_path, setup, output_root):
        captured["panel_path"] = str(panel_path)
        captured["daily_path"] = str(daily_path)
        captured["setup"] = setup
        setup_dir = Path(output_root) / setup.setup_id
        setup_dir.mkdir(parents=True)
        summary = {
            "SetupID": setup.setup_id,
            "Seed": setup.seed,
            "FeatureProfileID": setup.feature_profile_id,
            "InputFeatureSetID": setup.input_feature_set_id,
            "CheckpointProvenance": "best_inner_validation",
            "ValidationMeanReward": 0.7,
            "ValidationMeanSpearman": 0.6,
            "ValidationMeanMSE": 0.05,
            "TestMeanReward": 0.8,
            "TestMeanSpearman": 0.7,
            "TestMeanMSE": 0.04,
            "LearningRate": setup.learning_rate,
            "NSteps": setup.n_steps,
            "BatchSize": setup.batch_size,
            "NEpochs": setup.n_epochs,
            "Gamma": setup.gamma,
            "GaeLambda": setup.gae_lambda,
            "ClipRange": setup.clip_range,
            "EntCoef": setup.ent_coef,
            "VfCoef": setup.vf_coef,
            "MaxGradNorm": setup.max_grad_norm,
            "ReportedCheckpoint": str(setup_dir / "best_model.zip"),
            "ArtifactsDir": str(setup_dir),
        }
        (setup_dir / "setup_summary.json").write_text(json.dumps(summary), encoding="utf-8")
        return setup_dir

    monkeypatch.setattr(top_candidate_reruns, "train_setup", fake_train_setup)
    candidate = top_candidate_reruns.top_candidate_by_id("price_to_sma14")

    row = top_candidate_reruns.run_top_candidate(
        candidate=candidate,
        seed=7,
        tuned_candidate="refined50",
        total_timesteps=32768,
        output_root=tmp_path,
    )

    setup = captured["setup"]
    assert setup.setup_id == "TOP-REFINED50-PRICE_TO_SMA14-S7"
    assert setup.framework_id == config.FEATURE_PHASE_BASE_FRAMEWORK_ID
    assert setup.feature_profile_id == "price_to_sma14"
    assert setup.changed_feature == "price_to_sma20"
    assert captured["panel_path"].endswith("outputs\\feature_profiles\\price_to_sma14\\monthly_asset_panel.csv")
    assert setup.learning_rate == pytest.approx(0.00024935310281972535)
    assert setup.n_steps == 256
    assert setup.batch_size == 256
    assert setup.n_epochs == 10
    assert setup.clip_range == pytest.approx(0.2990122587129351)
    assert setup.ent_coef == pytest.approx(0.0023477909057284673)
    assert setup.vf_coef == pytest.approx(0.9023537822799527)
    assert setup.max_grad_norm == pytest.approx(0.3)
    assert setup.gamma == pytest.approx(1.0)
    assert setup.gae_lambda == pytest.approx(1.0)
    assert row["CandidateID"] == "price_to_sma14"
    assert row["ValidationMeanReward"] == pytest.approx(0.7)
    assert row["TestMeanSpearman"] == pytest.approx(0.7)


def test_top_candidate_matrix_writes_summary_and_uses_validation_only_for_selection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    rewards = {
        ("full_current_v1", 42): (0.70, 0.60, 0.80, 0.70),
        ("full_current_v1", 7): (0.70, 0.60, 0.80, 0.70),
        ("monthly_only_rows_v1", 42): (0.68, 0.58, 0.90, 0.85),
        ("monthly_only_rows_v1", 7): (0.68, 0.58, 0.90, 0.85),
    }

    def fake_run_top_candidate(candidate, seed, tuned_candidate, total_timesteps, output_root):
        val_reward, val_spearman, test_reward, test_spearman = rewards[(candidate.candidate_id, seed)]
        return {
            "CandidateID": candidate.candidate_id,
            "TunedCandidate": tuned_candidate,
            "SetupID": candidate.setup_id(tuned_candidate, seed),
            "Seed": seed,
            "FeatureProfileID": candidate.feature_profile_id,
            "InputFeatureSetID": candidate.input_feature_set_id,
            "CheckpointProvenance": "best_inner_validation",
            "ValidationMeanReward": val_reward,
            "ValidationMeanSpearman": val_spearman,
            "ValidationMeanMSE": 0.05,
            "TestMeanReward": test_reward,
            "TestMeanSpearman": test_spearman,
            "TestMeanMSE": 0.04,
            "LearningRate": 0.00024935310281972535,
            "NSteps": 256,
            "BatchSize": 256,
            "NEpochs": 10,
            "Gamma": 1.0,
            "GaeLambda": 1.0,
            "ClipRange": 0.2990122587129351,
            "EntCoef": 0.0023477909057284673,
            "VfCoef": 0.9023537822799527,
            "MaxGradNorm": 0.3,
            "ReportedCheckpoint": "best_model.zip",
            "ArtifactsDir": "artifacts",
        }

    monkeypatch.setattr(top_candidate_reruns, "run_top_candidate", fake_run_top_candidate)

    summary = top_candidate_reruns.run_top_candidate_matrix(
        candidate_ids=["full_current_v1", "monthly_only_rows_v1"],
        seeds=[42, 7],
        output_root=tmp_path,
    )
    selection = json.loads((tmp_path / top_candidate_reruns.SELECTION_FILE_NAME).read_text(encoding="utf-8"))

    assert len(summary) == 4
    assert (tmp_path / top_candidate_reruns.SUMMARY_FILE_NAME).exists()
    assert selection["winner"]["CandidateID"] == "full_current_v1"
    assert selection["winner"]["mean_test_reward"] == pytest.approx(0.8)
    assert "test metrics reporting only" in selection["selection_rule"]


def test_top_candidate_selection_uses_spearman_as_validation_tiebreaker() -> None:
    summary = pd.DataFrame(
        [
            {"CandidateID": "a", "Seed": 1, "ValidationMeanReward": 0.7, "ValidationMeanSpearman": 0.55, "TestMeanReward": 0.9, "TestMeanSpearman": 0.9},
            {"CandidateID": "b", "Seed": 1, "ValidationMeanReward": 0.7, "ValidationMeanSpearman": 0.56, "TestMeanReward": 0.1, "TestMeanSpearman": 0.1},
        ]
    )

    selection = top_candidate_reruns.select_winning_candidate(summary)

    assert selection["winner"]["CandidateID"] == "b"
