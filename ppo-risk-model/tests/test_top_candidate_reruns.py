from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src import config
from src.training import promote_best_model, tail_diagnostics, top_candidate_reruns


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
    assert "outputs" in captured["panel_path"]
    assert "generated" in captured["panel_path"]
    assert "feature_profiles" in captured["panel_path"]
    assert captured["panel_path"].endswith("price_to_sma14\\monthly_asset_panel.csv")
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


def test_tail_diagnostic_report_ranks_by_validation_high_risk_overlap(tmp_path: Path) -> None:
    artifact_root = tmp_path / "refined50"
    candidates = ("drop_distance_to_3m_high", "monthly_only_rows_v1")
    seeds = (42,)
    for candidate_id in candidates:
        setup_dir = artifact_root / tail_diagnostics.setup_dir_name(candidate_id, 42)
        setup_dir.mkdir(parents=True)
        if candidate_id == "drop_distance_to_3m_high":
            predicted = {"A": 0.10, "B": 0.90, "C": 0.80, "D": 0.20}
        else:
            predicted = {"A": 0.10, "B": 0.20, "C": 0.80, "D": 0.90}
        frame = pd.DataFrame(
            {
                "Date": ["2023-01"] * 4 + ["2025-10"] * 4,
                "Split": ["validation"] * 4 + ["test"] * 4,
                "AssetID": ["A", "B", "C", "D"] * 2,
                "AssetName": ["A", "B", "C", "D"] * 2,
                "AssetGroup": ["Equity"] * 8,
                "realized_risk": [0.10, 0.20, 0.80, 0.90] * 2,
            }
        )
        frame["PredictedRisk"] = frame["AssetID"].map(predicted).astype(float)
        frame["realized_rank"] = frame.groupby("Date")["realized_risk"].rank(method="average", ascending=True)
        frame["PredictedRank"] = frame.groupby("Date")["PredictedRisk"].rank(method="average", ascending=True)
        frame.to_csv(setup_dir / "ranked_predictions.csv", index=False)

    grouped, payload = tail_diagnostics.build_tail_diagnostic_report(
        candidates=candidates,
        seeds=seeds,
        artifact_root=artifact_root,
        output_dir=tmp_path / "tail",
    )

    assert grouped.iloc[0]["CandidateID"] == "monthly_only_rows_v1"
    assert grouped.iloc[0]["ValidationMeanHighRiskTop25Overlap"] == pytest.approx(1.0)
    assert payload["monthly_only_tail_decision"]["label"] == "promote_monthly_only_rows_v1_for_tail_confirmation"
    assert (tmp_path / "tail" / tail_diagnostics.SUMMARY_FILE_NAME).exists()


def test_promote_best_model_overwrites_destination_and_writes_manifest(tmp_path: Path) -> None:
    source = tmp_path / "source_artifact"
    destination = tmp_path / "best_model"
    source.mkdir()
    destination.mkdir()
    (destination / "stale_file.txt").write_text("remove me", encoding="utf-8")

    for file_name in promote_best_model.REQUIRED_FILES:
        path = source / file_name
        if file_name.endswith(".json"):
            payload = {
                "SetupID": "TAIL-REFINED50-DOWNSIDE_TAIL_RATIO_3M-S42",
                "Seed": 42,
                "ArtifactsDir": str(source),
                "ReportedCheckpoint": str(source / "best_model.zip"),
                "artifacts_dir": str(source),
                "best_model_path": str(source / "best_model.zip"),
                "final_model_path": str(source / "final_model.zip"),
                "reported_checkpoint": str(source / "best_model.zip"),
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
        else:
            path.write_text("artifact", encoding="utf-8")

    promoted = promote_best_model.promote_best_model(
        source_artifact_dir=source,
        destination_dir=destination,
        model_id="downside_tail_ratio_3m_refined50",
        framework_id="pit_3m_flat_context",
        feature_profile_id="full_current_v1",
        additive_feature_id="downside_tail_ratio_3m",
        input_feature_set_id="shadow_add_downside_tail_ratio_3m",
        tuned_ppo_id="refined50",
        selection_rule="tail_aware_validation_high_risk_overlap_with_reward_spearman_guardrails",
    )

    assert promoted == destination
    assert not (destination / "stale_file.txt").exists()
    assert (destination / "best_model.zip").exists()
    manifest = json.loads((destination / promote_best_model.MANIFEST_FILE_NAME).read_text(encoding="utf-8"))
    assert manifest["model_id"] == "downside_tail_ratio_3m_refined50"
    assert manifest["seed"] == 42
    assert manifest["destination_dir"].endswith("best_model")
    readme = (destination / "README.md").read_text(encoding="utf-8")
    assert "overwritten on every best-model promotion" in readme

    summary = json.loads((destination / "setup_summary.json").read_text(encoding="utf-8"))
    metadata = json.loads((destination / "setup_metadata.json").read_text(encoding="utf-8"))
    assert summary["ArtifactsDir"] == str(destination.resolve())
    assert summary["ReportedCheckpoint"] == str((destination / "best_model.zip").resolve())
    assert metadata["artifacts_dir"] == str(destination.resolve())
    assert metadata["reported_checkpoint"] == str((destination / "best_model.zip").resolve())
