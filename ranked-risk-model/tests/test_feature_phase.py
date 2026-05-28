from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src import config
from src.data_processing import validate_model_dataset as dataset_validator
from src.feature_profiles import get_feature_profile
from src.training import feature_phase, train


def write_minimal_output_dir(output_dir: Path, feature_profile_id: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    daily_rows = []
    for asset_id, base_price in (("A", 100.0), ("B", 110.0), ("C", 120.0)):
        daily_rows.append(
            {
                "Date": "2010-10-03",
                "AssetID": asset_id,
                "AssetName": f"Asset {asset_id}",
                "AssetGroup": "Equity",
                "QuotedValue": base_price,
                "OpenQuotedValue": base_price - 1.0,
                "HighQuotedValue": base_price + 2.0,
                "LowQuotedValue": base_price - 2.0,
                "PriceForReturn": base_price,
                "OpenPriceForRange": base_price - 1.0,
                "HighPriceForRange": base_price + 2.0,
                "LowPriceForRange": base_price - 2.0,
                "Volume": 1000.0,
                "ChangePctRaw": 0.0,
                "ReturnFromPrice": 0.0,
                "IsObserved": 1,
            }
        )
    pd.DataFrame(daily_rows)[config.DAILY_MARKET_COLUMNS].to_csv(
        output_dir / config.DAILY_MARKET_SERIES_NAME,
        index=False,
    )

    panel_rows = []
    for rank, asset_id in enumerate(("A", "B", "C"), start=1):
        base = (rank - 1) / 2.0
        row = {
            "Date": config.PANEL_STATE_START,
            "AssetID": asset_id,
            "AssetName": f"Asset {asset_id}",
            "AssetGroup": "Equity",
        }
        for column in config.MODEL_FEATURE_COLUMNS:
            row[column] = base
        row["realized_vol"] = base
        row["realized_downside_dev"] = base
        row["realized_max_drawdown"] = base
        row["realized_risk"] = base
        row["realized_rank"] = float(rank)
        panel_rows.append(row)
    pd.DataFrame(panel_rows)[config.PANEL_METADATA_COLUMNS + config.MODEL_FEATURE_COLUMNS + config.TARGET_COLUMNS].to_csv(
        output_dir / config.MONTHLY_PANEL_NAME,
        index=False,
    )

    (output_dir / "feature_profile_metadata.json").write_text(
        json.dumps({"feature_profile_id": feature_profile_id}),
        encoding="utf-8",
    )


def feature_phase_row(
    setup_id: str,
    timestamp_utc: str,
    validation_reward: float,
    validation_spearman: float,
    feature_profile_id: str = config.DEFAULT_FEATURE_PROFILE_ID,
    change_type: str = "baseline",
    changed_feature: str = "",
    variant_id: str = "base",
) -> dict[str, object]:
    return {
        "SetupID": setup_id,
        "TimestampUTC": timestamp_utc,
        "StudyPhase": config.FEATURE_PHASE_NAME,
        "FrameworkID": config.FEATURE_PHASE_BASE_FRAMEWORK_ID,
        "PolicySemanticsVersion": config.POLICY_SEMANTICS_VERSION,
        "FeatureProfileID": feature_profile_id,
        "ChangeType": change_type,
        "ChangedFeature": changed_feature,
        "VariantID": variant_id,
        "ValidationMeanReward": validation_reward,
        "ValidationMeanSpearman": validation_spearman,
    }


def write_feature_phase_summary(output_root: Path, rows: list[dict[str, object]]) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    summary_path = output_root / train.SUMMARY_FILE_NAME
    pd.DataFrame(rows).to_csv(summary_path, index=False)
    return summary_path


def test_feature_phase_registry_matches_tracker_order_and_profiles() -> None:
    assert [family.feature_name for family in feature_phase.FEATURE_FAMILIES] == [
        "egarch_vol",
        "downside_dev",
        "max_drawdown",
        "volume",
        "atr_pct_20",
        "beta_to_egx30",
        "price_to_sma20",
        "rsi_14",
        "distance_to_3m_high",
        "usd_vol",
        "cpi_trajectory",
    ]
    assert [family.drop_profile_id for family in feature_phase.FEATURE_FAMILIES] == [
        "drop_egarch_vol",
        "drop_downside_dev",
        "drop_max_drawdown",
        "drop_volume",
        "drop_atr_pct_20",
        "drop_beta_to_egx30",
        "drop_price_to_sma20",
        "drop_rsi_14",
        "drop_distance_to_3m_high",
        "drop_usd_vol",
        "drop_cpi_trajectory",
    ]
    assert config.FEATURE_PHASE_TOTAL_TIMESTEPS == 8192

    for profile_id in feature_phase.feature_phase_profile_ids():
        get_feature_profile(profile_id)


def test_validate_output_dir_supports_non_base_feature_profile_and_metadata(tmp_path: Path) -> None:
    output_dir = tmp_path / "drop_rsi_14"
    write_minimal_output_dir(output_dir, feature_profile_id="drop_rsi_14")

    daily, panel = dataset_validator.validate_output_dir(
        input_dir=output_dir,
        expect_feature_profile_id="drop_rsi_14",
    )
    assert len(daily) == 3
    assert len(panel) == 3

    cli_daily, cli_panel = dataset_validator.main(
        ["--input-dir", str(output_dir), "--expect-feature-profile-id", "drop_rsi_14"]
    )
    assert len(cli_daily) == len(daily)
    assert len(cli_panel) == len(panel)


def test_validate_output_dir_rejects_mismatched_feature_profile_metadata(tmp_path: Path) -> None:
    output_dir = tmp_path / "drop_rsi_14"
    write_minimal_output_dir(output_dir, feature_profile_id="drop_rsi_14")

    with pytest.raises(AssertionError, match="does not match the expected profile id"):
        dataset_validator.validate_output_dir(
            input_dir=output_dir,
            expect_feature_profile_id="drop_volume",
        )


def test_plan_frame_opens_override_shortlist_stage2_and_blocks_other_valuable_features(tmp_path: Path) -> None:
    output_root = tmp_path / "experiments"
    write_feature_phase_summary(
        output_root,
        [
            feature_phase_row(
                setup_id=feature_phase.baseline_setup_id(42),
                timestamp_utc="2026-04-20T10:00:00+00:00",
                validation_reward=0.6800,
                validation_spearman=0.5700,
            ),
            feature_phase_row(
                setup_id=feature_phase.drop_setup_id("price_to_sma20"),
                timestamp_utc="2026-04-20T10:30:00+00:00",
                validation_reward=0.6790,
                validation_spearman=0.5690,
                feature_profile_id="drop_price_to_sma20",
                change_type="drop_feature",
                changed_feature="price_to_sma20",
                variant_id="drop_price_to_sma20",
            ),
            feature_phase_row(
                setup_id=feature_phase.drop_setup_id("volume"),
                timestamp_utc="2026-04-20T11:00:00+00:00",
                validation_reward=0.6700,
                validation_spearman=0.5600,
                feature_profile_id="drop_volume",
                change_type="drop_feature",
                changed_feature="volume",
                variant_id="drop_volume",
            ),
        ],
    )

    frame = feature_phase.plan_frame(output_root=output_root)

    baseline_row = frame.loc[frame["setup_id"] == feature_phase.baseline_setup_id(42)].iloc[0]
    assert baseline_row["status"] == "completed"

    stage1_row = frame.loc[frame["setup_id"] == feature_phase.drop_setup_id("price_to_sma20")].iloc[0]
    assert stage1_row["status"] == "completed"
    assert feature_phase.stage1_decision(
        feature_phase.load_feature_phase_results(output_root=output_root),
        "price_to_sma20",
    ) == "provisionally valuable"

    override_stage2 = frame.loc[
        frame["setup_id"] == feature_phase.variant_setup_id("price_to_sma20", "price_to_sma14", seed=42)
    ].iloc[0]
    assert override_stage2["status"] == "pending"
    assert override_stage2["dependency_status"] == "ready"

    blocked_stage2 = frame.loc[
        frame["setup_id"] == feature_phase.variant_setup_id("volume", "volume_1m_sum", seed=42)
    ].iloc[0]
    assert blocked_stage2["dependency_status"] == "blocked: not approved for stage2 wave"


def test_first_wave_is_complete_only_when_baseline_and_all_stage1_runs_exist(tmp_path: Path) -> None:
    output_root = tmp_path / "experiments"
    partial_rows = [
        feature_phase_row(feature_phase.baseline_setup_id(42), "2026-04-21T08:00:00+00:00", 0.6800, 0.5700),
        feature_phase_row(
            feature_phase.drop_setup_id("rsi_14"),
            "2026-04-21T08:30:00+00:00",
            0.6810,
            0.5600,
            feature_profile_id="drop_rsi_14",
            change_type="drop_feature",
            changed_feature="rsi_14",
            variant_id="drop_rsi_14",
        ),
    ]
    write_feature_phase_summary(output_root, partial_rows)
    partial_results = feature_phase.load_feature_phase_results(output_root=output_root)
    assert not feature_phase.first_wave_is_complete(partial_results)

    complete_rows = [feature_phase_row(feature_phase.baseline_setup_id(42), "2026-04-21T08:00:00+00:00", 0.6800, 0.5700)]
    for index, family in enumerate(feature_phase.FEATURE_FAMILIES, start=1):
        complete_rows.append(
            feature_phase_row(
                feature_phase.drop_setup_id(family.feature_name),
                f"2026-04-21T08:{index:02d}:00+00:00",
                0.6700,
                0.5600,
                feature_profile_id=family.drop_profile_id,
                change_type="drop_feature",
                changed_feature=family.feature_name,
                variant_id=family.drop_profile_id,
            )
        )
    write_feature_phase_summary(output_root, complete_rows)
    complete_results = feature_phase.load_feature_phase_results(output_root=output_root)
    assert feature_phase.first_wave_is_complete(complete_results)


def test_provisional_feature_set_shows_baseline_only_before_ablation(tmp_path: Path) -> None:
    output_root = tmp_path / "experiments"
    write_feature_phase_summary(
        output_root,
        [feature_phase_row(feature_phase.baseline_setup_id(42), "2026-04-21T08:00:00+00:00", 0.6800, 0.5700)],
    )

    rows = feature_phase.provisional_feature_set_rows(feature_phase.load_feature_phase_results(output_root=output_root))

    assert len(rows) == len(config.MODEL_FEATURE_COLUMNS)
    assert all(row["Current Status"] == "baseline only" for row in rows)
    assert all(row["Next Action"] == "await screen" for row in rows)
    assert all(row["Evidence SetupIDs"] == feature_phase.baseline_setup_id(42) for row in rows)


def test_provisional_feature_set_reflects_stage1_decision_and_evidence(tmp_path: Path) -> None:
    output_root = tmp_path / "experiments"
    write_feature_phase_summary(
        output_root,
        [
            feature_phase_row(feature_phase.baseline_setup_id(42), "2026-04-21T08:00:00+00:00", 0.6800, 0.5700),
            feature_phase_row(
                feature_phase.drop_setup_id("rsi_14"),
                "2026-04-21T08:30:00+00:00",
                0.6810,
                0.5600,
                feature_profile_id="drop_rsi_14",
                change_type="drop_feature",
                changed_feature="rsi_14",
                variant_id="drop_rsi_14",
            ),
        ],
    )

    rows = feature_phase.provisional_feature_set_rows(feature_phase.load_feature_phase_results(output_root=output_root))
    rsi_row = next(row for row in rows if row["Feature"] == "rsi_14")

    assert rsi_row["Current Status"] == "candidate for redesign"
    assert rsi_row["Evidence SetupIDs"] == "FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-RSI_14-S42"
    assert rsi_row["Next Action"] == "open redesign variants"


def test_provisional_feature_set_opens_redesign_for_override_shortlist_family(tmp_path: Path) -> None:
    output_root = tmp_path / "experiments"
    write_feature_phase_summary(
        output_root,
        [
            feature_phase_row(feature_phase.baseline_setup_id(42), "2026-04-21T08:00:00+00:00", 0.6800, 0.5700),
            feature_phase_row(
                feature_phase.drop_setup_id("price_to_sma20"),
                "2026-04-21T08:30:00+00:00",
                0.6790,
                0.5690,
                feature_profile_id="drop_price_to_sma20",
                change_type="drop_feature",
                changed_feature="price_to_sma20",
                variant_id="drop_price_to_sma20",
            ),
        ],
    )

    rows = feature_phase.provisional_feature_set_rows(feature_phase.load_feature_phase_results(output_root=output_root))
    price_row = next(row for row in rows if row["Feature"] == "price_to_sma20")

    assert price_row["Current Status"] == "provisionally valuable"
    assert price_row["Evidence SetupIDs"] == "FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-PRICE_TO_SMA20-S42"
    assert price_row["Next Action"] == "open redesign variants"


def test_run_stage1_blocks_explicit_multi_seed_without_named_feature() -> None:
    with pytest.raises(ValueError, match="require an explicit --feature selection"):
        feature_phase.run_stage1(seeds=[42, 7, 13], dry_run=True)


def test_run_stage1_allows_named_multi_seed_confirmation_and_auto_creates_missing_baselines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_results = pd.DataFrame(
        [
            feature_phase_row(
                setup_id=feature_phase.baseline_setup_id(42),
                timestamp_utc="2026-04-22T10:00:00+00:00",
                validation_reward=0.6800,
                validation_spearman=0.5700,
            ),
        ]
    )
    executed: list[str] = []
    comparison_writes: list[str] = []

    def fake_load_feature_phase_results(*args: object, **kwargs: object) -> pd.DataFrame:
        return current_results.copy()

    def fake_execute(feature_run: feature_phase.FeaturePhaseRun, **kwargs: object) -> Path:
        nonlocal current_results
        executed.append(feature_run.setup_id)
        reward = 0.6800
        spearman = 0.5700
        if feature_run.setup_id == feature_phase.drop_setup_id("distance_to_3m_high", seed=42):
            reward = 0.6840
            spearman = 0.5740
        elif feature_run.setup_id == feature_phase.baseline_setup_id(7):
            reward = 0.6750
            spearman = 0.5650
        elif feature_run.setup_id == feature_phase.drop_setup_id("distance_to_3m_high", seed=7):
            reward = 0.6790
            spearman = 0.5690
        elif feature_run.setup_id == feature_phase.baseline_setup_id(13):
            reward = 0.6850
            spearman = 0.5750
        elif feature_run.setup_id == feature_phase.drop_setup_id("distance_to_3m_high", seed=13):
            reward = 0.6890
            spearman = 0.5790

        current_results = pd.concat(
            [
                current_results,
                pd.DataFrame(
                    [
                        feature_phase_row(
                            setup_id=feature_run.setup_id,
                            timestamp_utc=f"2026-04-22T10:{10 + len(executed):02d}:00+00:00",
                            validation_reward=reward,
                            validation_spearman=spearman,
                            feature_profile_id=feature_run.feature_profile_id,
                            change_type=feature_run.change_type,
                            changed_feature=feature_run.changed_feature,
                            variant_id=feature_run.variant_id,
                        )
                    ]
                ),
            ],
            ignore_index=True,
        )
        return tmp_path / feature_run.setup_id

    def fake_write_drop_multi_seed_comparison(feature_name: str, **kwargs: object) -> Path:
        comparison_writes.append(feature_name)
        return tmp_path / "multi_seed_comparison.json"

    monkeypatch.setattr(feature_phase, "load_feature_phase_results", fake_load_feature_phase_results)
    monkeypatch.setattr(feature_phase, "execute_feature_phase_run", fake_execute)
    monkeypatch.setattr(feature_phase, "write_drop_multi_seed_comparison", fake_write_drop_multi_seed_comparison)

    feature_phase.run_stage1(
        feature_names=["distance_to_3m_high"],
        seeds=[42, 7, 13],
        output_root=tmp_path / "experiments",
    )

    assert executed == [
        feature_phase.drop_setup_id("distance_to_3m_high", seed=42),
        feature_phase.baseline_setup_id(7),
        feature_phase.drop_setup_id("distance_to_3m_high", seed=7),
        feature_phase.baseline_setup_id(13),
        feature_phase.drop_setup_id("distance_to_3m_high", seed=13),
    ]
    assert comparison_writes == ["distance_to_3m_high"]


def test_run_stage1_requires_seed42_drop_win_before_opening_promoted_seeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_results = pd.DataFrame(
        [
            feature_phase_row(
                setup_id=feature_phase.baseline_setup_id(42),
                timestamp_utc="2026-04-22T10:00:00+00:00",
                validation_reward=0.6800,
                validation_spearman=0.5700,
            ),
        ]
    )
    executed: list[str] = []

    def fake_load_feature_phase_results(*args: object, **kwargs: object) -> pd.DataFrame:
        return current_results.copy()

    def fake_execute(feature_run: feature_phase.FeaturePhaseRun, **kwargs: object) -> Path:
        nonlocal current_results
        executed.append(feature_run.setup_id)
        current_results = pd.concat(
            [
                current_results,
                pd.DataFrame(
                    [
                        feature_phase_row(
                            setup_id=feature_run.setup_id,
                            timestamp_utc="2026-04-22T10:10:00+00:00",
                            validation_reward=0.6790,
                            validation_spearman=0.5690,
                            feature_profile_id=feature_run.feature_profile_id,
                            change_type=feature_run.change_type,
                            changed_feature=feature_run.changed_feature,
                            variant_id=feature_run.variant_id,
                        )
                    ]
                ),
            ],
            ignore_index=True,
        )
        return tmp_path / feature_run.setup_id

    monkeypatch.setattr(feature_phase, "load_feature_phase_results", fake_load_feature_phase_results)
    monkeypatch.setattr(feature_phase, "execute_feature_phase_run", fake_execute)

    feature_phase.run_stage1(
        feature_names=["distance_to_3m_high"],
        seeds=[42, 7, 13],
        output_root=tmp_path / "experiments",
    )

    assert executed == [feature_phase.drop_setup_id("distance_to_3m_high", seed=42)]


def test_run_stage2_auto_creates_missing_promotion_baselines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    current_results = pd.DataFrame(
        [
            feature_phase_row(
                setup_id=feature_phase.baseline_setup_id(42),
                timestamp_utc="2026-04-20T10:00:00+00:00",
                validation_reward=0.6800,
                validation_spearman=0.5700,
            ),
            feature_phase_row(
                setup_id=feature_phase.drop_setup_id("rsi_14"),
                timestamp_utc="2026-04-20T10:30:00+00:00",
                validation_reward=0.6810,
                validation_spearman=0.5600,
                feature_profile_id="drop_rsi_14",
                change_type="drop_feature",
                changed_feature="rsi_14",
                variant_id="drop_rsi_14",
            ),
        ]
    )
    executed: list[str] = []
    summaries: list[tuple[str, str]] = []

    def fake_load_feature_phase_results(*args: object, **kwargs: object) -> pd.DataFrame:
        return current_results.copy()

    def fake_execute(feature_run: feature_phase.FeaturePhaseRun, **kwargs: object) -> Path:
        nonlocal current_results
        executed.append(feature_run.setup_id)
        reward = 0.6800
        spearman = 0.5700
        if feature_run.setup_id.startswith("FT-VAR-"):
            reward = 0.6900
            spearman = 0.5800
        elif feature_run.setup_id.endswith("-S7"):
            reward = 0.6750
            spearman = 0.5650
        elif feature_run.setup_id.endswith("-S13"):
            reward = 0.6850
            spearman = 0.5750

        current_results = pd.concat(
            [
                current_results,
                pd.DataFrame(
                    [
                        feature_phase_row(
                            setup_id=feature_run.setup_id,
                            timestamp_utc=f"2026-04-20T12:0{len(executed)}:00+00:00",
                            validation_reward=reward,
                            validation_spearman=spearman,
                            feature_profile_id=feature_run.feature_profile_id,
                            change_type=feature_run.change_type,
                            changed_feature=feature_run.changed_feature,
                            variant_id=feature_run.variant_id,
                        )
                    ]
                ),
            ],
            ignore_index=True,
        )
        return tmp_path / feature_run.setup_id

    def fake_write_multi_seed_comparison(feature_name: str, variant_id: str, **kwargs: object) -> Path:
        summaries.append((feature_name, variant_id))
        return tmp_path / "multi_seed_comparison.json"

    monkeypatch.setattr(feature_phase, "load_feature_phase_results", fake_load_feature_phase_results)
    monkeypatch.setattr(feature_phase, "execute_feature_phase_run", fake_execute)
    monkeypatch.setattr(feature_phase, "write_multi_seed_comparison", fake_write_multi_seed_comparison)

    feature_phase.run_stage2(
        feature_names=["rsi_14"],
        variant_ids=["rsi_7"],
        output_root=tmp_path / "experiments",
    )

    assert executed == [
        feature_phase.variant_setup_id("rsi_14", "rsi_7", seed=42),
        feature_phase.baseline_setup_id(7),
        feature_phase.variant_setup_id("rsi_14", "rsi_7", seed=7),
        feature_phase.baseline_setup_id(13),
        feature_phase.variant_setup_id("rsi_14", "rsi_7", seed=13),
    ]
    assert summaries == [("rsi_14", "rsi_7")]


def test_run_stage2_explicit_seed_42_only_keeps_execution_at_screening_seed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_results = pd.DataFrame(
        [
            feature_phase_row(
                setup_id=feature_phase.baseline_setup_id(42),
                timestamp_utc="2026-04-20T10:00:00+00:00",
                validation_reward=0.6800,
                validation_spearman=0.5700,
            ),
            feature_phase_row(
                setup_id=feature_phase.drop_setup_id("price_to_sma20"),
                timestamp_utc="2026-04-20T10:30:00+00:00",
                validation_reward=0.6790,
                validation_spearman=0.5690,
                feature_profile_id="drop_price_to_sma20",
                change_type="drop_feature",
                changed_feature="price_to_sma20",
                variant_id="drop_price_to_sma20",
            ),
        ]
    )
    executed: list[str] = []

    def fake_load_feature_phase_results(*args: object, **kwargs: object) -> pd.DataFrame:
        return current_results.copy()

    def fake_execute(feature_run: feature_phase.FeaturePhaseRun, **kwargs: object) -> Path:
        nonlocal current_results
        executed.append(feature_run.setup_id)
        current_results = pd.concat(
            [
                current_results,
                pd.DataFrame(
                    [
                        feature_phase_row(
                            setup_id=feature_run.setup_id,
                            timestamp_utc="2026-04-20T11:00:00+00:00",
                            validation_reward=0.6900,
                            validation_spearman=0.5800,
                            feature_profile_id=feature_run.feature_profile_id,
                            change_type=feature_run.change_type,
                            changed_feature=feature_run.changed_feature,
                            variant_id=feature_run.variant_id,
                        )
                    ]
                ),
            ],
            ignore_index=True,
        )
        return tmp_path / feature_run.setup_id

    monkeypatch.setattr(feature_phase, "load_feature_phase_results", fake_load_feature_phase_results)
    monkeypatch.setattr(feature_phase, "execute_feature_phase_run", fake_execute)

    feature_phase.run_stage2(
        feature_names=["price_to_sma20"],
        variant_ids=["price_to_sma14"],
        seeds=[42],
        output_root=tmp_path / "experiments",
    )

    assert feature_phase.stage1_decision(current_results, "price_to_sma20") == "provisionally valuable"
    assert executed == [feature_phase.variant_setup_id("price_to_sma20", "price_to_sma14", seed=42)]


def test_run_stage2_accepts_override_family_without_relabeling_stage1(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_results = pd.DataFrame(
        [
            feature_phase_row(
                setup_id=feature_phase.baseline_setup_id(42),
                timestamp_utc="2026-04-20T10:00:00+00:00",
                validation_reward=0.6800,
                validation_spearman=0.5700,
            ),
            feature_phase_row(
                setup_id=feature_phase.drop_setup_id("usd_vol"),
                timestamp_utc="2026-04-20T10:30:00+00:00",
                validation_reward=0.6792,
                validation_spearman=0.5691,
                feature_profile_id="drop_usd_vol",
                change_type="drop_feature",
                changed_feature="usd_vol",
                variant_id="drop_usd_vol",
            ),
        ]
    )
    executed: list[str] = []

    def fake_load_feature_phase_results(*args: object, **kwargs: object) -> pd.DataFrame:
        return current_results.copy()

    def fake_execute(feature_run: feature_phase.FeaturePhaseRun, **kwargs: object) -> Path:
        nonlocal current_results
        executed.append(feature_run.setup_id)
        current_results = pd.concat(
            [
                current_results,
                pd.DataFrame(
                    [
                        feature_phase_row(
                            setup_id=feature_run.setup_id,
                            timestamp_utc="2026-04-20T11:00:00+00:00",
                            validation_reward=0.6785,
                            validation_spearman=0.5680,
                            feature_profile_id=feature_run.feature_profile_id,
                            change_type=feature_run.change_type,
                            changed_feature=feature_run.changed_feature,
                            variant_id=feature_run.variant_id,
                        )
                    ]
                ),
            ],
            ignore_index=True,
        )
        return tmp_path / feature_run.setup_id

    monkeypatch.setattr(feature_phase, "load_feature_phase_results", fake_load_feature_phase_results)
    monkeypatch.setattr(feature_phase, "execute_feature_phase_run", fake_execute)

    feature_phase.run_stage2(
        feature_names=["usd_vol"],
        variant_ids=["usd_vol_1m"],
        seeds=[42],
        output_root=tmp_path / "experiments",
    )

    assert feature_phase.stage1_decision(current_results, "usd_vol") == "provisionally valuable"
    assert executed == [feature_phase.variant_setup_id("usd_vol", "usd_vol_1m", seed=42)]


def test_variant_confirmation_requires_beating_matching_baseline_on_all_seeds(tmp_path: Path) -> None:
    output_root = tmp_path / "experiments"
    write_feature_phase_summary(
        output_root,
        [
            feature_phase_row(
                feature_phase.baseline_setup_id(42),
                "2026-04-20T10:00:00+00:00",
                0.6800,
                0.5700,
            ),
            feature_phase_row(
                feature_phase.drop_setup_id("distance_to_3m_high"),
                "2026-04-20T10:10:00+00:00",
                0.6810,
                0.5710,
                feature_profile_id="drop_distance_to_3m_high",
                change_type="drop_feature",
                changed_feature="distance_to_3m_high",
                variant_id="drop_distance_to_3m_high",
            ),
            feature_phase_row(
                feature_phase.variant_setup_id("distance_to_3m_high", "distance_to_1m_high", seed=42),
                "2026-04-20T10:20:00+00:00",
                0.6900,
                0.5800,
                feature_profile_id="distance_to_1m_high",
                change_type="alter_feature",
                changed_feature="distance_to_3m_high",
                variant_id="distance_to_1m_high",
            ),
            feature_phase_row(
                feature_phase.variant_setup_id("distance_to_3m_high", "distance_to_2m_high", seed=42),
                "2026-04-20T10:30:00+00:00",
                0.6790,
                0.5690,
                feature_profile_id="distance_to_2m_high",
                change_type="alter_feature",
                changed_feature="distance_to_3m_high",
                variant_id="distance_to_2m_high",
            ),
            feature_phase_row(
                feature_phase.baseline_setup_id(7),
                "2026-04-20T10:40:00+00:00",
                0.6750,
                0.5650,
            ),
            feature_phase_row(
                feature_phase.variant_setup_id("distance_to_3m_high", "distance_to_1m_high", seed=7),
                "2026-04-20T10:50:00+00:00",
                0.6710,
                0.5560,
                feature_profile_id="distance_to_1m_high",
                change_type="alter_feature",
                changed_feature="distance_to_3m_high",
                variant_id="distance_to_1m_high",
            ),
            feature_phase_row(
                feature_phase.baseline_setup_id(13),
                "2026-04-20T11:00:00+00:00",
                0.6850,
                0.5750,
            ),
            feature_phase_row(
                feature_phase.variant_setup_id("distance_to_3m_high", "distance_to_1m_high", seed=13),
                "2026-04-20T11:10:00+00:00",
                0.6890,
                0.5810,
                feature_profile_id="distance_to_1m_high",
                change_type="alter_feature",
                changed_feature="distance_to_3m_high",
                variant_id="distance_to_1m_high",
            ),
        ],
    )

    results = feature_phase.load_feature_phase_results(output_root=output_root)
    assert feature_phase.selected_family_variant_id(
        results,
        feature_phase.get_feature_family("distance_to_3m_high"),
    ) == "distance_to_1m_high"
    assert not feature_phase.variant_is_confirmed(results, "distance_to_3m_high", "distance_to_1m_high")

    comparison_path = feature_phase.write_multi_seed_comparison(
        feature_name="distance_to_3m_high",
        variant_id="distance_to_1m_high",
        output_root=output_root,
    )
    payload = json.loads(comparison_path.read_text(encoding="utf-8"))

    assert payload["winner_confirmed"] is False
    assert payload["rows_by_seed"][1]["seed"] == 7
    assert payload["rows_by_seed"][1]["beats_baseline_on_both"] is False


def test_stage1_drop_confirmation_decisions_distinguish_confirmed_and_rejected(tmp_path: Path) -> None:
    confirmed_output_root = tmp_path / "confirmed"
    write_feature_phase_summary(
        confirmed_output_root,
        [
            feature_phase_row(feature_phase.baseline_setup_id(42), "2026-04-22T10:00:00+00:00", 0.6800, 0.5700),
            feature_phase_row(
                feature_phase.drop_setup_id("distance_to_3m_high", seed=42),
                "2026-04-22T10:10:00+00:00",
                0.6840,
                0.5740,
                feature_profile_id="drop_distance_to_3m_high",
                change_type="drop_feature",
                changed_feature="distance_to_3m_high",
                variant_id="drop_distance_to_3m_high",
            ),
            feature_phase_row(feature_phase.baseline_setup_id(7), "2026-04-22T10:20:00+00:00", 0.6750, 0.5650),
            feature_phase_row(
                feature_phase.drop_setup_id("distance_to_3m_high", seed=7),
                "2026-04-22T10:30:00+00:00",
                0.6790,
                0.5690,
                feature_profile_id="drop_distance_to_3m_high",
                change_type="drop_feature",
                changed_feature="distance_to_3m_high",
                variant_id="drop_distance_to_3m_high",
            ),
            feature_phase_row(feature_phase.baseline_setup_id(13), "2026-04-22T10:40:00+00:00", 0.6850, 0.5750),
            feature_phase_row(
                feature_phase.drop_setup_id("distance_to_3m_high", seed=13),
                "2026-04-22T10:50:00+00:00",
                0.6890,
                0.5790,
                feature_profile_id="drop_distance_to_3m_high",
                change_type="drop_feature",
                changed_feature="distance_to_3m_high",
                variant_id="drop_distance_to_3m_high",
            ),
        ],
    )
    confirmed_results = feature_phase.load_feature_phase_results(output_root=confirmed_output_root)
    assert feature_phase.stage1_decision(confirmed_results, "distance_to_3m_high") == "removal confirmed"
    assert feature_phase.feature_matrix_status(confirmed_results, feature_phase.get_feature_family("distance_to_3m_high")) == "removal confirmed"

    rejected_output_root = tmp_path / "rejected"
    write_feature_phase_summary(
        rejected_output_root,
        [
            feature_phase_row(feature_phase.baseline_setup_id(42), "2026-04-22T10:00:00+00:00", 0.6800, 0.5700),
            feature_phase_row(
                feature_phase.drop_setup_id("distance_to_3m_high", seed=42),
                "2026-04-22T10:10:00+00:00",
                0.6840,
                0.5740,
                feature_profile_id="drop_distance_to_3m_high",
                change_type="drop_feature",
                changed_feature="distance_to_3m_high",
                variant_id="drop_distance_to_3m_high",
            ),
            feature_phase_row(feature_phase.baseline_setup_id(7), "2026-04-22T10:20:00+00:00", 0.6750, 0.5650),
            feature_phase_row(
                feature_phase.drop_setup_id("distance_to_3m_high", seed=7),
                "2026-04-22T10:30:00+00:00",
                0.6710,
                0.5610,
                feature_profile_id="drop_distance_to_3m_high",
                change_type="drop_feature",
                changed_feature="distance_to_3m_high",
                variant_id="drop_distance_to_3m_high",
            ),
        ],
    )
    rejected_results = feature_phase.load_feature_phase_results(output_root=rejected_output_root)
    assert feature_phase.stage1_decision(rejected_results, "distance_to_3m_high") == "removal rejected"


def test_write_drop_multi_seed_comparison_records_confirmation_payload(tmp_path: Path) -> None:
    output_root = tmp_path / "experiments"
    write_feature_phase_summary(
        output_root,
        [
            feature_phase_row(feature_phase.baseline_setup_id(42), "2026-04-22T10:00:00+00:00", 0.6800, 0.5700),
            feature_phase_row(
                feature_phase.drop_setup_id("distance_to_3m_high", seed=42),
                "2026-04-22T10:10:00+00:00",
                0.6840,
                0.5740,
                feature_profile_id="drop_distance_to_3m_high",
                change_type="drop_feature",
                changed_feature="distance_to_3m_high",
                variant_id="drop_distance_to_3m_high",
            ),
            feature_phase_row(feature_phase.baseline_setup_id(7), "2026-04-22T10:20:00+00:00", 0.6750, 0.5650),
            feature_phase_row(
                feature_phase.drop_setup_id("distance_to_3m_high", seed=7),
                "2026-04-22T10:30:00+00:00",
                0.6790,
                0.5690,
                feature_profile_id="drop_distance_to_3m_high",
                change_type="drop_feature",
                changed_feature="distance_to_3m_high",
                variant_id="drop_distance_to_3m_high",
            ),
            feature_phase_row(feature_phase.baseline_setup_id(13), "2026-04-22T10:40:00+00:00", 0.6850, 0.5750),
            feature_phase_row(
                feature_phase.drop_setup_id("distance_to_3m_high", seed=13),
                "2026-04-22T10:50:00+00:00",
                0.6890,
                0.5790,
                feature_profile_id="drop_distance_to_3m_high",
                change_type="drop_feature",
                changed_feature="distance_to_3m_high",
                variant_id="drop_distance_to_3m_high",
            ),
        ],
    )

    comparison_path = feature_phase.write_drop_multi_seed_comparison(
        feature_name="distance_to_3m_high",
        output_root=output_root,
    )
    payload = json.loads(comparison_path.read_text(encoding="utf-8"))

    assert payload["winner_confirmed"] is True
    assert payload["promoted_baseline_profile_id"] == "full_current_v2_no_distance_to_3m_high"
    assert payload["rows_by_seed"][2]["drop_setup_id"] == "FT-ABL-DROP-DISTANCE_TO_3M_HIGH-S13"


def test_sync_feature_phase_doc_rewrites_status_tables_and_decision_log(tmp_path: Path) -> None:
    output_root = tmp_path / "experiments"
    write_feature_phase_summary(
        output_root,
        [
            feature_phase_row(feature_phase.baseline_setup_id(42), "2026-04-20T10:00:00+00:00", 0.6800, 0.5700),
            feature_phase_row(feature_phase.baseline_setup_id(7), "2026-04-20T10:05:00+00:00", 0.6750, 0.5650),
            feature_phase_row(feature_phase.baseline_setup_id(13), "2026-04-20T10:10:00+00:00", 0.6850, 0.5750),
            feature_phase_row(
                feature_phase.drop_setup_id("rsi_14"),
                "2026-04-20T10:30:00+00:00",
                0.6810,
                0.5600,
                feature_profile_id="drop_rsi_14",
                change_type="drop_feature",
                changed_feature="rsi_14",
                variant_id="drop_rsi_14",
            ),
            feature_phase_row(
                feature_phase.variant_setup_id("rsi_14", "rsi_7", seed=42),
                "2026-04-20T11:00:00+00:00",
                0.6900,
                0.5800,
                feature_profile_id="rsi_7",
                change_type="alter_feature",
                changed_feature="rsi_14",
                variant_id="rsi_7",
            ),
            feature_phase_row(
                feature_phase.variant_setup_id("rsi_14", "rsi_7", seed=7),
                "2026-04-20T11:10:00+00:00",
                0.6850,
                0.5750,
                feature_profile_id="rsi_7",
                change_type="alter_feature",
                changed_feature="rsi_14",
                variant_id="rsi_7",
            ),
            feature_phase_row(
                feature_phase.variant_setup_id("rsi_14", "rsi_7", seed=13),
                "2026-04-20T11:20:00+00:00",
                0.6950,
                0.5850,
                feature_profile_id="rsi_7",
                change_type="alter_feature",
                changed_feature="rsi_14",
                variant_id="rsi_7",
            ),
            feature_phase_row(
                feature_phase.variant_setup_id("rsi_14", "rsi_21", seed=42),
                "2026-04-20T11:30:00+00:00",
                0.6750,
                0.5650,
                feature_profile_id="rsi_21",
                change_type="alter_feature",
                changed_feature="rsi_14",
                variant_id="rsi_21",
            ),
        ],
    )
    doc_path = tmp_path / "feature_phase.md"

    feature_phase.sync_feature_phase_doc(output_root=output_root, doc_path=doc_path)
    rendered = doc_path.read_text(encoding="utf-8")

    assert "### Approved Exploratory Redesign Shortlist" in rendered
    assert "| `FT-BASE-3M-CONTEXT-S42` | `pit_3m_flat_context` | `full_current_v1` | completed | Seed-42 anchor |" in rendered
    assert "| `rsi_14` | Wilder `RSI(14)` | drop `rsi_14` | `rsi_7`, `rsi_21` | winner confirmed |" in rendered
    assert "`FT-VAR-RSI_14-RSI_7-S13`" in rendered
    assert "Selected family winner; confirmed across seeds 42, 7, and 13." in rendered
    assert "## Run Results" in rendered
    assert "| Date | SetupID | FeatureProfileID | Seed | Validation Reward | Validation Spearman | Decision | Notes |" in rendered
    assert "## Current Provisional Feature Set" in rendered
    assert "| `rsi_14` | winner confirmed | FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-RSI_14-S42 |" in rendered


def test_sync_feature_phase_doc_keeps_mixed_multi_seed_result_as_winner_promoted(tmp_path: Path) -> None:
    output_root = tmp_path / "experiments"
    write_feature_phase_summary(
        output_root,
        [
            feature_phase_row(feature_phase.baseline_setup_id(42), "2026-04-20T10:00:00+00:00", 0.6800, 0.5700),
            feature_phase_row(
                feature_phase.drop_setup_id("distance_to_3m_high"),
                "2026-04-20T10:10:00+00:00",
                0.6810,
                0.5710,
                feature_profile_id="drop_distance_to_3m_high",
                change_type="drop_feature",
                changed_feature="distance_to_3m_high",
                variant_id="drop_distance_to_3m_high",
            ),
            feature_phase_row(
                feature_phase.variant_setup_id("distance_to_3m_high", "distance_to_1m_high", seed=42),
                "2026-04-20T10:20:00+00:00",
                0.6900,
                0.5800,
                feature_profile_id="distance_to_1m_high",
                change_type="alter_feature",
                changed_feature="distance_to_3m_high",
                variant_id="distance_to_1m_high",
            ),
            feature_phase_row(
                feature_phase.variant_setup_id("distance_to_3m_high", "distance_to_2m_high", seed=42),
                "2026-04-20T10:30:00+00:00",
                0.6790,
                0.5690,
                feature_profile_id="distance_to_2m_high",
                change_type="alter_feature",
                changed_feature="distance_to_3m_high",
                variant_id="distance_to_2m_high",
            ),
            feature_phase_row(feature_phase.baseline_setup_id(7), "2026-04-20T10:40:00+00:00", 0.6750, 0.5650),
            feature_phase_row(
                feature_phase.variant_setup_id("distance_to_3m_high", "distance_to_1m_high", seed=7),
                "2026-04-20T10:50:00+00:00",
                0.6710,
                0.5560,
                feature_profile_id="distance_to_1m_high",
                change_type="alter_feature",
                changed_feature="distance_to_3m_high",
                variant_id="distance_to_1m_high",
            ),
            feature_phase_row(feature_phase.baseline_setup_id(13), "2026-04-20T11:00:00+00:00", 0.6850, 0.5750),
            feature_phase_row(
                feature_phase.variant_setup_id("distance_to_3m_high", "distance_to_1m_high", seed=13),
                "2026-04-20T11:10:00+00:00",
                0.6890,
                0.5810,
                feature_profile_id="distance_to_1m_high",
                change_type="alter_feature",
                changed_feature="distance_to_3m_high",
                variant_id="distance_to_1m_high",
            ),
        ],
    )
    doc_path = tmp_path / "feature_phase.md"

    feature_phase.sync_feature_phase_doc(output_root=output_root, doc_path=doc_path)
    rendered = doc_path.read_text(encoding="utf-8")

    assert "| `distance_to_3m_high` | last close versus trailing `3M` high | drop `distance_to_3m_high` | `distance_to_1m_high`, `distance_to_2m_high` | winner promoted |" in rendered
    assert "multi-seed comparison is recorded but not confirmed across all promoted seeds" in rendered
    assert "| `distance_to_3m_high` | winner promoted | FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-DISTANCE_TO_3M_HIGH-S42 |" in rendered


def test_sync_feature_phase_doc_switches_locked_baseline_after_confirmed_distance_removal(tmp_path: Path) -> None:
    output_root = tmp_path / "experiments"
    write_feature_phase_summary(
        output_root,
        [
            feature_phase_row(feature_phase.baseline_setup_id(42), "2026-04-22T10:00:00+00:00", 0.6800, 0.5700),
            feature_phase_row(
                feature_phase.drop_setup_id("distance_to_3m_high", seed=42),
                "2026-04-22T10:10:00+00:00",
                0.6840,
                0.5740,
                feature_profile_id="drop_distance_to_3m_high",
                change_type="drop_feature",
                changed_feature="distance_to_3m_high",
                variant_id="drop_distance_to_3m_high",
            ),
            feature_phase_row(feature_phase.baseline_setup_id(7), "2026-04-22T10:20:00+00:00", 0.6750, 0.5650),
            feature_phase_row(
                feature_phase.drop_setup_id("distance_to_3m_high", seed=7),
                "2026-04-22T10:30:00+00:00",
                0.6790,
                0.5690,
                feature_profile_id="drop_distance_to_3m_high",
                change_type="drop_feature",
                changed_feature="distance_to_3m_high",
                variant_id="drop_distance_to_3m_high",
            ),
            feature_phase_row(feature_phase.baseline_setup_id(13), "2026-04-22T10:40:00+00:00", 0.6850, 0.5750),
            feature_phase_row(
                feature_phase.drop_setup_id("distance_to_3m_high", seed=13),
                "2026-04-22T10:50:00+00:00",
                0.6890,
                0.5790,
                feature_profile_id="drop_distance_to_3m_high",
                change_type="drop_feature",
                changed_feature="distance_to_3m_high",
                variant_id="drop_distance_to_3m_high",
            ),
        ],
    )
    doc_path = tmp_path / "feature_phase.md"

    feature_phase.sync_feature_phase_doc(output_root=output_root, doc_path=doc_path)
    rendered = doc_path.read_text(encoding="utf-8")

    assert "### Stage 1 Multi-Seed Removal Confirmation" in rendered
    assert "| `distance_to_3m_high` | passed | 7, 13 | removal confirmed | Locked baseline relocked to `full_current_v2_no_distance_to_3m_high`;" in rendered
    assert "- `full_current_v2_no_distance_to_3m_high`" in rendered
    assert "- `distance_to_3m_high`" not in rendered.split("Locked feature set:")[1].split("Locked comparison rules:")[0]
    assert "neutralized to `0.5`" in rendered
    assert "| `distance_to_3m_high` | last close versus trailing `3M` high | drop `distance_to_3m_high` | `distance_to_1m_high`, `distance_to_2m_high` | removal confirmed |" in rendered
    assert "| `distance_to_3m_high` | removed from baseline | FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-DISTANCE_TO_3M_HIGH-S42 |" in rendered
    assert "| `FT-BASE-3M-CONTEXT-S42` | `pit_3m_flat_context` | `full_current_v1` | completed | Seed-42 anchor |" in rendered


def test_sync_feature_phase_doc_keeps_full_current_v1_when_distance_removal_fails_confirmation(tmp_path: Path) -> None:
    output_root = tmp_path / "experiments"
    write_feature_phase_summary(
        output_root,
        [
            feature_phase_row(feature_phase.baseline_setup_id(42), "2026-04-22T10:00:00+00:00", 0.6800, 0.5700),
            feature_phase_row(
                feature_phase.drop_setup_id("distance_to_3m_high", seed=42),
                "2026-04-22T10:10:00+00:00",
                0.6840,
                0.5740,
                feature_profile_id="drop_distance_to_3m_high",
                change_type="drop_feature",
                changed_feature="distance_to_3m_high",
                variant_id="drop_distance_to_3m_high",
            ),
            feature_phase_row(feature_phase.baseline_setup_id(7), "2026-04-22T10:20:00+00:00", 0.6750, 0.5650),
            feature_phase_row(
                feature_phase.drop_setup_id("distance_to_3m_high", seed=7),
                "2026-04-22T10:30:00+00:00",
                0.6710,
                0.5610,
                feature_profile_id="drop_distance_to_3m_high",
                change_type="drop_feature",
                changed_feature="distance_to_3m_high",
                variant_id="drop_distance_to_3m_high",
            ),
        ],
    )
    doc_path = tmp_path / "feature_phase.md"

    feature_phase.sync_feature_phase_doc(output_root=output_root, doc_path=doc_path)
    rendered = doc_path.read_text(encoding="utf-8")

    assert "| `distance_to_3m_high` | passed | 7 | removal rejected | Keep `full_current_v1` as the live baseline; no replacement testing opens in this wave. |" in rendered
    assert "- `full_current_v1`" in rendered
    assert "| `distance_to_3m_high` | last close versus trailing `3M` high | drop `distance_to_3m_high` | `distance_to_1m_high`, `distance_to_2m_high` | removal rejected |" in rendered
    assert "| `distance_to_3m_high` | removal rejected | FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-DISTANCE_TO_3M_HIGH-S42 |" in rendered


def test_sync_feature_phase_doc_renders_shortlist_and_override_board_actions(tmp_path: Path) -> None:
    output_root = tmp_path / "experiments"
    write_feature_phase_summary(
        output_root,
        [
            feature_phase_row(feature_phase.baseline_setup_id(42), "2026-04-20T10:00:00+00:00", 0.6800, 0.5700),
            feature_phase_row(
                feature_phase.drop_setup_id("distance_to_3m_high"),
                "2026-04-20T10:10:00+00:00",
                0.6810,
                0.5710,
                feature_profile_id="drop_distance_to_3m_high",
                change_type="drop_feature",
                changed_feature="distance_to_3m_high",
                variant_id="drop_distance_to_3m_high",
            ),
            feature_phase_row(
                feature_phase.drop_setup_id("price_to_sma20"),
                "2026-04-20T10:20:00+00:00",
                0.6790,
                0.5690,
                feature_profile_id="drop_price_to_sma20",
                change_type="drop_feature",
                changed_feature="price_to_sma20",
                variant_id="drop_price_to_sma20",
            ),
            feature_phase_row(
                feature_phase.drop_setup_id("max_drawdown"),
                "2026-04-20T10:30:00+00:00",
                0.6791,
                0.5692,
                feature_profile_id="drop_max_drawdown",
                change_type="drop_feature",
                changed_feature="max_drawdown",
                variant_id="drop_max_drawdown",
            ),
            feature_phase_row(
                feature_phase.drop_setup_id("usd_vol"),
                "2026-04-20T10:40:00+00:00",
                0.6793,
                0.5691,
                feature_profile_id="drop_usd_vol",
                change_type="drop_feature",
                changed_feature="usd_vol",
                variant_id="drop_usd_vol",
            ),
        ],
    )
    doc_path = tmp_path / "feature_phase.md"

    feature_phase.sync_feature_phase_doc(output_root=output_root, doc_path=doc_path)
    rendered = doc_path.read_text(encoding="utf-8")

    assert "### Approved Exploratory Redesign Shortlist" in rendered
    assert "| `distance_to_3m_high` | Raw Stage 1 candidate for redesign at seed 42. | `distance_to_1m_high`, `distance_to_2m_high` | 1 |" in rendered
    assert "| `price_to_sma20` | Exploratory redesign override for this one-wave Stage 2 shortlist. | `price_to_sma14`, `price_to_sma21`, `price_to_ema20` | 2 |" in rendered
    assert "| `max_drawdown` | trailing `3M` max drawdown | drop `max_drawdown` | `max_drawdown_1m`, `max_drawdown_2m` | provisionally valuable |" in rendered
    assert "| `price_to_sma20` | last close versus `SMA(20)` | drop `price_to_sma20` | `price_to_sma14`, `price_to_sma21`, `price_to_ema20` | provisionally valuable |" in rendered
    assert "| `usd_vol` | trailing `3M` USD realized volatility | drop `usd_vol` | `usd_vol_1m`, `usd_return_trajectory_3m` | provisionally valuable |" in rendered
    assert "| `distance_to_3m_high` | candidate for redesign | FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-DISTANCE_TO_3M_HIGH-S42 |" in rendered
    assert "| `price_to_sma20` | provisionally valuable | FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-PRICE_TO_SMA20-S42 |" in rendered
    assert "open redesign variants |" in rendered


def test_sync_feature_phase_doc_renders_shadow_candidate_sections(tmp_path: Path) -> None:
    output_root = tmp_path / "experiments"
    write_feature_phase_summary(
        output_root,
        [
            feature_phase_row(feature_phase.baseline_setup_id(42), "2026-04-21T10:00:00+00:00", 0.6800, 0.5700),
            feature_phase_row(
                feature_phase.variant_setup_id("distance_to_3m_high", "distance_to_1m_high", seed=42),
                "2026-04-21T10:10:00+00:00",
                0.6900,
                0.5800,
                feature_profile_id="distance_to_1m_high",
                change_type="alter_feature",
                changed_feature="distance_to_3m_high",
                variant_id="distance_to_1m_high",
            ),
            {
                "SetupID": feature_phase.shadow_baseline_setup_id(42),
                "TimestampUTC": "2026-04-22T10:00:00+00:00",
                "StudyPhase": config.FEATURE_PHASE_NAME,
                "FrameworkID": config.FEATURE_PHASE_BASE_FRAMEWORK_ID,
                "PolicySemanticsVersion": config.POLICY_SEMANTICS_VERSION,
                "FeatureProfileID": config.DEFAULT_FEATURE_PROFILE_ID,
                "ChangeType": "baseline",
                "ChangedFeature": "",
                "VariantID": "canonical_11",
                "InputFeatureSetID": "canonical_11",
                "Notes": feature_phase.SHADOW_BASELINE_NOTE,
                "ValidationMeanReward": 0.6800,
                "ValidationMeanSpearman": 0.5700,
            },
            {
                "SetupID": feature_phase.shadow_replacement_setup_id("distance_to_1m_high", 42),
                "TimestampUTC": "2026-04-22T10:10:00+00:00",
                "StudyPhase": config.FEATURE_PHASE_NAME,
                "FrameworkID": config.FEATURE_PHASE_BASE_FRAMEWORK_ID,
                "PolicySemanticsVersion": config.POLICY_SEMANTICS_VERSION,
                "FeatureProfileID": "distance_to_1m_high",
                "ChangeType": "alter_feature",
                "ChangedFeature": "distance_to_3m_high",
                "VariantID": "distance_to_1m_high",
                "InputFeatureSetID": "canonical_11",
                "Notes": feature_phase.SHADOW_REPLACEMENT_NOTE,
                "ValidationMeanReward": 0.6900,
                "ValidationMeanSpearman": 0.5800,
            },
        ],
    )
    candidate_audit_path = tmp_path / "standalone_candidate_audit.csv"
    pd.DataFrame(
        [
            {
                "CandidateID": "sortino_3m",
                "CandidateType": "additive",
                "ReplacementFeature": "",
                "CandidateSetID": "shadow_add_sortino_3m",
                "InputFeatureSetID": "shadow_add_sortino_3m",
                "StandaloneMeanSpearman": 0.1234,
                "OuterValidationMonths": 26,
                "EligibleForRLScreen": True,
                "RLScreenOrder": 1,
                "RLScreenReason": "approved_shortlist",
                "FeatureColumn": "sortino_3m",
            }
        ]
    ).to_csv(candidate_audit_path, index=False)
    doc_path = tmp_path / "feature_phase.md"

    feature_phase.sync_feature_phase_doc(
        output_root=output_root,
        doc_path=doc_path,
        candidate_audit_path=candidate_audit_path,
    )
    rendered = doc_path.read_text(encoding="utf-8")

    assert "## Approved Ratio And Tail Shortlist" in rendered
    assert "## Shadow Candidate Registry" in rendered
    assert "## Standalone Candidate Audit" in rendered
    assert "## RL Candidate Screens" in rendered
    assert "## Canonical Promotion Decisions" in rendered
    assert (
        "| `sortino_3m` | additive | replacement for `downside_dev` after additive confirmation | 1 | "
        "Directly tests a downside-adjusted return ratio over the full trailing 3-month window. |"
    ) in rendered
    assert "| `sortino_3m` | additive |  | `shadow_add_sortino_3m` | 0.1234 | 26 | approved shortlist | 1 |" in rendered
    assert "`FT-SHADOW-REP-DISTANCE_TO_1M_HIGH-S42`" in rendered
    assert "Beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics; awaiting seed 7 and 13 confirmation for this isolated replacement screen." in rendered


def test_canonical_promotion_decisions_explain_contingent_ratio_follow_up_when_unrun() -> None:
    rows = feature_phase.canonical_promotion_decision_rows(pd.DataFrame())
    sortino_row = next(row for row in rows if row["Candidate"] == "sortino_3m")
    distance_row = next(row for row in rows if row["Candidate"] == "distance_to_1m_low")

    assert sortino_row["Decision"] == "planned"
    assert "contingent replacement follow-up against `downside_dev` open" in sortino_row["Notes"]
    assert distance_row["Decision"] == "planned"
    assert distance_row["Notes"] == "Await standalone audit and RL screen."


def test_execute_feature_phase_run_orders_build_validate_train_and_sync(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    call_order: list[str] = []
    profile_paths = feature_phase.FeatureProfilePaths(
        output_dir=tmp_path / "profile",
        daily_path=tmp_path / "profile" / config.DAILY_MARKET_SERIES_NAME,
        panel_path=tmp_path / "profile" / config.MONTHLY_PANEL_NAME,
        metadata_path=tmp_path / "profile" / "feature_profile_metadata.json",
    )

    def fake_ensure_outputs(*args: object, **kwargs: object) -> feature_phase.FeatureProfilePaths:
        call_order.append("build")
        return profile_paths

    def fake_validate_output_dir(*args: object, **kwargs: object) -> tuple[pd.DataFrame, pd.DataFrame]:
        call_order.append("validate")
        return pd.DataFrame(), pd.DataFrame()

    def fake_train_setup(*args: object, **kwargs: object) -> Path:
        call_order.append("train")
        return tmp_path / "artifacts"

    def fake_sync(*args: object, **kwargs: object) -> Path:
        call_order.append("sync")
        return tmp_path / "feature_phase.md"

    monkeypatch.setattr(feature_phase, "load_feature_phase_results", lambda *args, **kwargs: pd.DataFrame())
    monkeypatch.setattr(feature_phase, "ensure_feature_profile_outputs", fake_ensure_outputs)
    monkeypatch.setattr(dataset_validator, "validate_output_dir", fake_validate_output_dir)
    monkeypatch.setattr(train, "train_setup", fake_train_setup)
    monkeypatch.setattr(feature_phase, "sync_feature_phase_doc", fake_sync)

    feature_phase.execute_feature_phase_run(
        feature_phase.stage2_run(feature_phase.get_feature_family("price_to_sma20"), "price_to_sma14"),
        output_root=tmp_path / "experiments",
    )

    assert call_order == ["build", "validate", "train", "sync"]
