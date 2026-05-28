"""Registry, orchestration, planning, and doc sync for the feature phase."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config
from src.feature_candidates import (
    APPROVED_RATIO_AND_TAIL_SHORTLIST,
    SHADOW_FEATURE_CANDIDATES,
    get_ratio_tail_shortlist_entry,
    get_shadow_candidate,
)
from src.data_processing import build_model_dataset as dataset_builder
from src.data_processing import validate_model_dataset as dataset_validator
from src.feature_profiles import get_feature_profile
from src.training import train
from src.training.results_store import (
    load_setup_results,
    metric_value,
    resolve_output_root,
    resolve_summary_path,
    result_row_for_setup,
    string_series as _string_series,
)


FEATURE_PHASE_DOC_PATH = ROOT / "docs" / "feature_phase.md"
FEATURE_CANDIDATE_AUDIT_PATH = ROOT / config.FEATURE_CANDIDATE_OUTPUT_DIR / "standalone_candidate_audit.csv"
SCREENING_SEED = 42
PROMOTION_SEEDS = (7, 13)
BASELINE_SEEDS = (SCREENING_SEED,) + PROMOTION_SEEDS
EXPLORATORY_STAGE2_FAMILY_ORDER = (
    "distance_to_3m_high",
    "price_to_sma20",
    "max_drawdown",
    "usd_vol",
)
EXPLORATORY_STAGE2_PRIORITY = {
    feature_name: index
    for index, feature_name in enumerate(EXPLORATORY_STAGE2_FAMILY_ORDER, start=1)
}
SHADOW_BASELINE_PREFIX = "FT-SHADOW-BASE-"
SHADOW_REPLACEMENT_PREFIX = "FT-SHADOW-REP-"
SHADOW_ADDITIVE_PREFIX = "FT-SHADOW-ADD-"
SHADOW_BASELINE_NOTE = "shadow_baseline"
SHADOW_REPLACEMENT_NOTE = "shadow_replacement_screen"
SHADOW_ADDITIVE_NOTE = "shadow_additive_screen"
SHADOW_SCREEN_NOTES = {SHADOW_REPLACEMENT_NOTE, SHADOW_ADDITIVE_NOTE}
SHADOW_NOTES = {SHADOW_BASELINE_NOTE} | SHADOW_SCREEN_NOTES


@dataclass(frozen=True)
class FeatureFamily:
    feature_name: str
    current_definition: str
    drop_profile_id: str
    stage2_variant_ids: tuple[str, ...]


@dataclass(frozen=True)
class FeatureProfilePaths:
    output_dir: Path
    daily_path: Path
    panel_path: Path
    metadata_path: Path


@dataclass(frozen=True)
class FeaturePhaseRun:
    stage: str
    feature_name: str
    feature_profile_id: str
    setup_id: str
    seed: int
    change_type: str
    changed_feature: str
    variant_id: str
    notes: str = ""


@dataclass(frozen=True)
class PlanRow:
    stage: str
    feature_name: str
    seed: int
    feature_profile_id: str
    setup_id: str
    status: str
    dependency_status: str


FEATURE_FAMILIES: tuple[FeatureFamily, ...] = (
    FeatureFamily(
        feature_name="egarch_vol",
        current_definition="walk-forward EGARCH aggregated across trailing `3M`",
        drop_profile_id="drop_egarch_vol",
        stage2_variant_ids=("egarch_last_3m", "realized_vol_3m_proxy"),
    ),
    FeatureFamily(
        feature_name="downside_dev",
        current_definition="trailing `3M` downside deviation",
        drop_profile_id="drop_downside_dev",
        stage2_variant_ids=("downside_dev_1m", "downside_dev_ewm_3m"),
    ),
    FeatureFamily(
        feature_name="max_drawdown",
        current_definition="trailing `3M` max drawdown",
        drop_profile_id="drop_max_drawdown",
        stage2_variant_ids=("max_drawdown_1m", "max_drawdown_2m"),
    ),
    FeatureFamily(
        feature_name="volume",
        current_definition="trailing `3M` summed raw volume",
        drop_profile_id="drop_volume",
        stage2_variant_ids=("volume_1m_sum", "volume_3m_mean_log"),
    ),
    FeatureFamily(
        feature_name="atr_pct_20",
        current_definition="`ATR(20) / last_close`",
        drop_profile_id="drop_atr_pct_20",
        stage2_variant_ids=("atr_pct_14", "atr_pct_21"),
    ),
    FeatureFamily(
        feature_name="beta_to_egx30",
        current_definition="trailing `3M` beta to `EGX30`",
        drop_profile_id="drop_beta_to_egx30",
        stage2_variant_ids=("beta_to_egx30_1m", "downside_beta_to_egx30"),
    ),
    FeatureFamily(
        feature_name="price_to_sma20",
        current_definition="last close versus `SMA(20)`",
        drop_profile_id="drop_price_to_sma20",
        stage2_variant_ids=("price_to_sma14", "price_to_sma21", "price_to_ema20"),
    ),
    FeatureFamily(
        feature_name="rsi_14",
        current_definition="Wilder `RSI(14)`",
        drop_profile_id="drop_rsi_14",
        stage2_variant_ids=("rsi_7", "rsi_21"),
    ),
    FeatureFamily(
        feature_name="distance_to_3m_high",
        current_definition="last close versus trailing `3M` high",
        drop_profile_id="drop_distance_to_3m_high",
        stage2_variant_ids=("distance_to_1m_high", "distance_to_2m_high"),
    ),
    FeatureFamily(
        feature_name="usd_vol",
        current_definition="trailing `3M` USD realized volatility",
        drop_profile_id="drop_usd_vol",
        stage2_variant_ids=("usd_vol_1m", "usd_return_trajectory_3m"),
    ),
    FeatureFamily(
        feature_name="cpi_trajectory",
        current_definition="compounded CPI trajectory over trailing `3M`",
        drop_profile_id="drop_cpi_trajectory",
        stage2_variant_ids=("cpi_last_mom", "cpi_trajectory_2m"),
    ),
)


FEATURE_FAMILY_LOOKUP = {family.feature_name: family for family in FEATURE_FAMILIES}
REMOVAL_CONFIRMATION_BASELINES = {
    "distance_to_3m_high": "full_current_v2_no_distance_to_3m_high",
}


def shadow_baseline_setup_id(seed: int) -> str:
    return f"FT-SHADOW-BASE-CANONICAL-S{seed}"


def shadow_replacement_setup_id(candidate_id: str, seed: int) -> str:
    return f"FT-SHADOW-REP-{candidate_id.upper()}-S{seed}"


def shadow_additive_setup_id(candidate_id: str, seed: int) -> str:
    return f"FT-SHADOW-ADD-{candidate_id.upper()}-S{seed}"


def _is_shadow_baseline_setup_id(setup_id: str) -> bool:
    return setup_id.startswith(SHADOW_BASELINE_PREFIX)


def _is_shadow_candidate_setup_id(setup_id: str) -> bool:
    return setup_id.startswith(SHADOW_REPLACEMENT_PREFIX) or setup_id.startswith(SHADOW_ADDITIVE_PREFIX)


def _row_setup_id(row: pd.Series) -> str:
    value = row.get("SetupID", "")
    return "" if pd.isna(value) else str(value)


def _row_note(row: pd.Series) -> str:
    value = row.get("Notes", "")
    return "" if pd.isna(value) else str(value)


def _is_shadow_baseline_row(row: pd.Series) -> bool:
    setup_id = _row_setup_id(row)
    note = _row_note(row)
    return _is_shadow_baseline_setup_id(setup_id) or note == SHADOW_BASELINE_NOTE


def _is_shadow_candidate_row(row: pd.Series) -> bool:
    setup_id = _row_setup_id(row)
    note = _row_note(row)
    return _is_shadow_candidate_setup_id(setup_id) or note in SHADOW_SCREEN_NOTES


def _shadow_lane_results_from_results(results: pd.DataFrame) -> pd.DataFrame:
    if results.empty:
        return results
    shadow_mask = results.apply(lambda row: _is_shadow_baseline_row(row) or _is_shadow_candidate_row(row), axis=1)
    return results.loc[shadow_mask].copy().reset_index(drop=True)


def baseline_setup_id(seed: int) -> str:
    return f"FT-BASE-3M-CONTEXT-S{seed}"


def drop_setup_id(feature_name: str, seed: int = SCREENING_SEED) -> str:
    return f"FT-ABL-DROP-{feature_name.upper()}-S{seed}"


def variant_setup_id(feature_name: str, variant_id: str, seed: int = SCREENING_SEED) -> str:
    return f"FT-VAR-{feature_name.upper()}-{variant_id.upper()}-S{seed}"


def baseline_run(seed: int) -> FeaturePhaseRun:
    return FeaturePhaseRun(
        stage="stage0",
        feature_name="baseline",
        feature_profile_id=config.DEFAULT_FEATURE_PROFILE_ID,
        setup_id=baseline_setup_id(seed),
        seed=seed,
        change_type="baseline",
        changed_feature="",
        variant_id="base",
        notes=f"Seed-{seed} anchor",
    )


def stage1_run(family: FeatureFamily, seed: int = SCREENING_SEED) -> FeaturePhaseRun:
    return FeaturePhaseRun(
        stage="stage1",
        feature_name=family.feature_name,
        feature_profile_id=family.drop_profile_id,
        setup_id=drop_setup_id(family.feature_name, seed=seed),
        seed=seed,
        change_type="drop_feature",
        changed_feature=family.feature_name,
        variant_id=family.drop_profile_id,
        notes=f"Leave-one-out drop of {family.feature_name}",
    )


def stage2_run(family: FeatureFamily, variant_id: str, seed: int = SCREENING_SEED) -> FeaturePhaseRun:
    return FeaturePhaseRun(
        stage="stage2",
        feature_name=family.feature_name,
        feature_profile_id=variant_id,
        setup_id=variant_setup_id(family.feature_name, variant_id, seed=seed),
        seed=seed,
        change_type="alter_feature",
        changed_feature=family.feature_name,
        variant_id=variant_id,
        notes=f"Feature variant screen for {family.feature_name}: {variant_id}",
    )


def get_feature_family(feature_name: str) -> FeatureFamily:
    try:
        return FEATURE_FAMILY_LOOKUP[feature_name]
    except KeyError as exc:
        raise ValueError(f"Unknown feature family: {feature_name}") from exc


def feature_phase_profile_ids() -> tuple[str, ...]:
    ordered_ids = [config.DEFAULT_FEATURE_PROFILE_ID]
    for family in FEATURE_FAMILIES:
        ordered_ids.append(family.drop_profile_id)
        ordered_ids.extend(family.stage2_variant_ids)
    return tuple(ordered_ids)


def load_feature_phase_results(
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
) -> pd.DataFrame:
    results = load_setup_results(output_root=output_root, summary_path=summary_path)
    if results.empty:
        return results

    required_filters = (
        results["StudyPhase"].eq(config.FEATURE_PHASE_NAME)
        & results["FrameworkID"].eq(config.FEATURE_PHASE_BASE_FRAMEWORK_ID)
        & results["PolicySemanticsVersion"].eq(config.POLICY_SEMANTICS_VERSION)
    )
    return results.loc[required_filters].copy().reset_index(drop=True)


def load_shadow_feature_phase_results(
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
) -> pd.DataFrame:
    results = load_feature_phase_results(output_root=output_root, summary_path=summary_path)
    if results.empty:
        return results
    setup_ids = _string_series(results, "SetupID")
    notes = _string_series(results, "Notes")
    shadow_mask = setup_ids.apply(lambda setup_id: _is_shadow_baseline_setup_id(setup_id) or _is_shadow_candidate_setup_id(setup_id))
    shadow_mask |= notes.isin(SHADOW_NOTES)
    return results.loc[shadow_mask].copy().reset_index(drop=True)


def seed_value_from_setup_id(setup_id: str) -> int | None:
    if "-S" not in setup_id:
        return None
    suffix = setup_id.rsplit("-S", maxsplit=1)[-1]
    try:
        return int(suffix)
    except ValueError:
        return None


def run_status(results: pd.DataFrame, setup_id: str) -> str:
    return "completed" if result_row_for_setup(results, setup_id) is not None else "pending"


def raw_stage1_decision(results: pd.DataFrame, feature_name: str) -> str | None:
    baseline = result_row_for_setup(results, baseline_setup_id(SCREENING_SEED))
    drop_row = result_row_for_setup(results, drop_setup_id(feature_name, seed=SCREENING_SEED))
    baseline_reward = metric_value(baseline, "ValidationMeanReward")
    baseline_spearman = metric_value(baseline, "ValidationMeanSpearman")
    drop_reward = metric_value(drop_row, "ValidationMeanReward")
    drop_spearman = metric_value(drop_row, "ValidationMeanSpearman")
    if None in (baseline_reward, baseline_spearman, drop_reward, drop_spearman):
        return None
    if drop_reward < baseline_reward and drop_spearman < baseline_spearman:
        return "provisionally valuable"
    return "candidate for redesign"


def drop_feature_beats_baseline_for_seed(results: pd.DataFrame, feature_name: str, seed: int) -> bool:
    baseline = result_row_for_setup(results, baseline_setup_id(seed))
    drop_row = result_row_for_setup(results, drop_setup_id(feature_name, seed=seed))
    baseline_reward = metric_value(baseline, "ValidationMeanReward")
    baseline_spearman = metric_value(baseline, "ValidationMeanSpearman")
    drop_reward = metric_value(drop_row, "ValidationMeanReward")
    drop_spearman = metric_value(drop_row, "ValidationMeanSpearman")
    if None in (baseline_reward, baseline_spearman, drop_reward, drop_spearman):
        return False
    return drop_reward > baseline_reward and drop_spearman > baseline_spearman


def drop_feature_is_seed42_winner(results: pd.DataFrame, feature_name: str) -> bool:
    return drop_feature_beats_baseline_for_seed(results, feature_name, SCREENING_SEED)


def drop_feature_is_confirmed(results: pd.DataFrame, feature_name: str) -> bool:
    required_setups = [baseline_setup_id(seed) for seed in BASELINE_SEEDS]
    required_setups.extend(drop_setup_id(feature_name, seed=seed) for seed in BASELINE_SEEDS)
    if not all(result_row_for_setup(results, setup_id) is not None for setup_id in required_setups):
        return False
    return all(drop_feature_beats_baseline_for_seed(results, feature_name, seed) for seed in BASELINE_SEEDS)


def drop_feature_has_failed_confirmation(results: pd.DataFrame, feature_name: str) -> bool:
    if not drop_feature_is_seed42_winner(results, feature_name):
        return False
    promotion_rows = [result_row_for_setup(results, drop_setup_id(feature_name, seed=seed)) for seed in PROMOTION_SEEDS]
    if not any(row is not None for row in promotion_rows):
        return False
    for seed in PROMOTION_SEEDS:
        baseline = result_row_for_setup(results, baseline_setup_id(seed))
        drop_row = result_row_for_setup(results, drop_setup_id(feature_name, seed=seed))
        if baseline is None or drop_row is None:
            continue
        if not drop_feature_beats_baseline_for_seed(results, feature_name, seed):
            return True
    return False


def has_drop_confirmation_lane(results: pd.DataFrame, feature_name: str) -> bool:
    return any(result_row_for_setup(results, drop_setup_id(feature_name, seed=seed)) is not None for seed in PROMOTION_SEEDS)


def live_feature_profile_id(results: pd.DataFrame) -> str:
    for feature_name, promoted_profile_id in REMOVAL_CONFIRMATION_BASELINES.items():
        if drop_feature_is_confirmed(results, feature_name):
            return promoted_profile_id
    return config.DEFAULT_FEATURE_PROFILE_ID


def live_feature_profile(results: pd.DataFrame):
    return get_feature_profile(live_feature_profile_id(results))


def baseline_feature_profile_id_for_seed(results: pd.DataFrame, seed: int) -> str:
    row = result_row_for_setup(results, baseline_setup_id(seed))
    if row is not None:
        feature_profile_id = row.get("FeatureProfileID", "")
        if not pd.isna(feature_profile_id) and str(feature_profile_id):
            return str(feature_profile_id)
    return live_feature_profile_id(results)


def shadow_candidate_setup_id(candidate_id: str, seed: int) -> str:
    candidate = get_shadow_candidate(candidate_id)
    if candidate.candidate_type == "replacement":
        return shadow_replacement_setup_id(candidate_id, seed)
    return shadow_additive_setup_id(candidate_id, seed)


def shadow_baseline_row_for_seed(results: pd.DataFrame, seed: int) -> pd.Series | None:
    return result_row_for_setup(results, shadow_baseline_setup_id(seed))


def shadow_candidate_row_for_seed(results: pd.DataFrame, candidate_id: str, seed: int) -> pd.Series | None:
    return result_row_for_setup(results, shadow_candidate_setup_id(candidate_id, seed))


def shadow_candidate_beats_baseline_for_seed(results: pd.DataFrame, candidate_id: str, seed: int) -> bool:
    baseline = shadow_baseline_row_for_seed(results, seed)
    candidate_row = shadow_candidate_row_for_seed(results, candidate_id, seed)
    baseline_reward = metric_value(baseline, "ValidationMeanReward")
    baseline_spearman = metric_value(baseline, "ValidationMeanSpearman")
    candidate_reward = metric_value(candidate_row, "ValidationMeanReward")
    candidate_spearman = metric_value(candidate_row, "ValidationMeanSpearman")
    if None in (baseline_reward, baseline_spearman, candidate_reward, candidate_spearman):
        return False
    return candidate_reward > baseline_reward and candidate_spearman > baseline_spearman


def shadow_candidate_is_seed42_winner(results: pd.DataFrame, candidate_id: str) -> bool:
    return shadow_candidate_beats_baseline_for_seed(results, candidate_id, SCREENING_SEED)


def shadow_candidate_is_confirmed(results: pd.DataFrame, candidate_id: str) -> bool:
    required_setup_ids = [shadow_baseline_setup_id(seed) for seed in BASELINE_SEEDS]
    required_setup_ids.extend(shadow_candidate_setup_id(candidate_id, seed) for seed in BASELINE_SEEDS)
    if not all(result_row_for_setup(results, setup_id) is not None for setup_id in required_setup_ids):
        return False
    return all(shadow_candidate_beats_baseline_for_seed(results, candidate_id, seed) for seed in BASELINE_SEEDS)


def shadow_candidate_has_failed_confirmation(results: pd.DataFrame, candidate_id: str) -> bool:
    if not shadow_candidate_is_seed42_winner(results, candidate_id):
        return False
    promotion_rows = [shadow_candidate_row_for_seed(results, candidate_id, seed) for seed in PROMOTION_SEEDS]
    if not any(row is not None for row in promotion_rows):
        return False
    for seed in PROMOTION_SEEDS:
        baseline = shadow_baseline_row_for_seed(results, seed)
        candidate_row = shadow_candidate_row_for_seed(results, candidate_id, seed)
        if baseline is None or candidate_row is None:
            continue
        if not shadow_candidate_beats_baseline_for_seed(results, candidate_id, seed):
            return True
    return False


def is_exploratory_stage2_family(feature_name: str) -> bool:
    return feature_name in EXPLORATORY_STAGE2_PRIORITY


def stage1_decision(results: pd.DataFrame, feature_name: str) -> str | None:
    raw_decision = raw_stage1_decision(results, feature_name)
    if feature_name not in REMOVAL_CONFIRMATION_BASELINES:
        return raw_decision
    if drop_feature_is_confirmed(results, feature_name):
        return "removal confirmed"
    if drop_feature_has_failed_confirmation(results, feature_name):
        return "removal rejected"
    if has_drop_confirmation_lane(results, feature_name) and drop_feature_is_seed42_winner(results, feature_name):
        return "removal promoted"
    return raw_decision


def variant_is_promotable(results: pd.DataFrame, feature_name: str, variant_id: str) -> bool:
    baseline = result_row_for_setup(results, baseline_setup_id(SCREENING_SEED))
    variant_row = result_row_for_setup(results, variant_setup_id(feature_name, variant_id, seed=SCREENING_SEED))
    baseline_reward = metric_value(baseline, "ValidationMeanReward")
    baseline_spearman = metric_value(baseline, "ValidationMeanSpearman")
    variant_reward = metric_value(variant_row, "ValidationMeanReward")
    variant_spearman = metric_value(variant_row, "ValidationMeanSpearman")
    if None in (baseline_reward, baseline_spearman, variant_reward, variant_spearman):
        return False
    return variant_reward > baseline_reward and variant_spearman > baseline_spearman


def variant_beats_baseline_for_seed(results: pd.DataFrame, feature_name: str, variant_id: str, seed: int) -> bool:
    baseline = result_row_for_setup(results, baseline_setup_id(seed))
    variant_row = result_row_for_setup(results, variant_setup_id(feature_name, variant_id, seed=seed))
    baseline_reward = metric_value(baseline, "ValidationMeanReward")
    baseline_spearman = metric_value(baseline, "ValidationMeanSpearman")
    variant_reward = metric_value(variant_row, "ValidationMeanReward")
    variant_spearman = metric_value(variant_row, "ValidationMeanSpearman")
    if None in (baseline_reward, baseline_spearman, variant_reward, variant_spearman):
        return False
    return variant_reward > baseline_reward and variant_spearman > baseline_spearman


def family_stage2_screen_complete(
    results: pd.DataFrame,
    family: FeatureFamily,
    variant_ids: tuple[str, ...] | None = None,
) -> bool:
    variants = family.stage2_variant_ids if variant_ids is None else variant_ids
    return all(
        result_row_for_setup(results, variant_setup_id(family.feature_name, variant_id, seed=SCREENING_SEED)) is not None
        for variant_id in variants
    )


def family_has_any_stage2_screen(
    results: pd.DataFrame,
    family: FeatureFamily,
    variant_ids: tuple[str, ...] | None = None,
) -> bool:
    variants = family.stage2_variant_ids if variant_ids is None else variant_ids
    return any(
        result_row_for_setup(results, variant_setup_id(family.feature_name, variant_id, seed=SCREENING_SEED)) is not None
        for variant_id in variants
    )


def stage2_is_eligible(results: pd.DataFrame, family: FeatureFamily) -> bool:
    decision = raw_stage1_decision(results, family.feature_name)
    if decision is None:
        return False
    return decision == "candidate for redesign" or is_exploratory_stage2_family(family.feature_name)


def selected_family_variant_id(
    results: pd.DataFrame,
    family: FeatureFamily,
    variant_ids: tuple[str, ...] | None = None,
    require_complete_screen: bool = True,
) -> str | None:
    variants = family.stage2_variant_ids if variant_ids is None else variant_ids
    if require_complete_screen and not family_stage2_screen_complete(results, family, variant_ids=variants):
        return None

    ranked_candidates: list[tuple[str, float, float, int]] = []
    for tracker_index, variant_id in enumerate(variants):
        if not variant_is_promotable(results, family.feature_name, variant_id):
            continue
        row = result_row_for_setup(results, variant_setup_id(family.feature_name, variant_id, seed=SCREENING_SEED))
        reward = metric_value(row, "ValidationMeanReward")
        spearman = metric_value(row, "ValidationMeanSpearman")
        if reward is None or spearman is None:
            continue
        ranked_candidates.append((variant_id, reward, spearman, tracker_index))

    if not ranked_candidates:
        return None

    ranked_candidates.sort(key=lambda item: (-item[1], -item[2], item[3]))
    return ranked_candidates[0][0]


def variant_is_confirmed(results: pd.DataFrame, feature_name: str, variant_id: str) -> bool:
    family = get_feature_family(feature_name)
    if selected_family_variant_id(results, family) != variant_id:
        return False
    required_setups = [baseline_setup_id(seed) for seed in BASELINE_SEEDS]
    required_setups.extend(variant_setup_id(feature_name, variant_id, seed=seed) for seed in BASELINE_SEEDS)
    if not all(result_row_for_setup(results, setup_id) is not None for setup_id in required_setups):
        return False
    return all(
        variant_beats_baseline_for_seed(results, feature_name, variant_id, seed)
        for seed in BASELINE_SEEDS
    )


def any_promoted_variant(results: pd.DataFrame) -> bool:
    return any(
        selected_family_variant_id(results, family) is not None
        for family in FEATURE_FAMILIES
    )


def feature_matrix_status(results: pd.DataFrame, family: FeatureFamily) -> str:
    decision = stage1_decision(results, family.feature_name)
    if decision is None:
        return "planned"
    if decision in {"removal promoted", "removal confirmed", "removal rejected"}:
        return decision

    selected_variant_id = selected_family_variant_id(results, family)
    if selected_variant_id is not None and variant_is_confirmed(results, family.feature_name, selected_variant_id):
        return "winner confirmed"
    if selected_variant_id is not None:
        return "winner promoted"
    if family_has_any_stage2_screen(results, family):
        return "redesign screened"
    return decision


def baseline_dependency_status(results: pd.DataFrame, seed: int) -> str:
    setup_id = baseline_setup_id(seed)
    if result_row_for_setup(results, setup_id) is not None:
        return "completed"
    if seed == SCREENING_SEED:
        return "ready"
    if any_promoted_variant(results):
        return "ready"
    return "waits for stage2 promotion"


def stage1_dependency_status(results: pd.DataFrame, family: FeatureFamily, seed: int = SCREENING_SEED) -> str:
    setup_id = drop_setup_id(family.feature_name, seed=seed)
    if result_row_for_setup(results, setup_id) is not None:
        return "completed"
    if result_row_for_setup(results, baseline_setup_id(SCREENING_SEED)) is not None:
        return "ready"
    return f"requires {baseline_setup_id(SCREENING_SEED)}"


def stage2_dependency_status(results: pd.DataFrame, family: FeatureFamily, variant_id: str, seed: int) -> str:
    setup_id = variant_setup_id(family.feature_name, variant_id, seed=seed)
    if result_row_for_setup(results, setup_id) is not None:
        return "completed"

    if seed == SCREENING_SEED:
        decision = stage1_decision(results, family.feature_name)
        if decision is None:
            return f"requires {drop_setup_id(family.feature_name, seed=SCREENING_SEED)}"
        if not stage2_is_eligible(results, family):
            return "blocked: not approved for stage2 wave"
        return "ready"

    selected_variant_id = selected_family_variant_id(results, family)
    screen_setup_id = variant_setup_id(family.feature_name, variant_id, seed=SCREENING_SEED)
    if result_row_for_setup(results, screen_setup_id) is None:
        return f"requires {screen_setup_id}"
    if not family_stage2_screen_complete(results, family):
        return "waits for remaining seed-42 family screens"
    if selected_variant_id != variant_id:
        return "blocked: not selected family winner"

    if not variant_is_promotable(results, family.feature_name, variant_id):
        screen_setup_id = variant_setup_id(family.feature_name, variant_id, seed=SCREENING_SEED)
        return "blocked: seed-42 screen not promotable"

    baseline_setup = baseline_setup_id(seed)
    if result_row_for_setup(results, baseline_setup) is None:
        return f"requires {baseline_setup}"
    return "ready"


def build_plan_rows(
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
) -> list[PlanRow]:
    results = load_feature_phase_results(output_root=output_root, summary_path=summary_path)
    rows: list[PlanRow] = []

    for seed in BASELINE_SEEDS:
        rows.append(
            PlanRow(
                stage="stage0",
                feature_name="baseline",
                seed=seed,
                feature_profile_id=baseline_feature_profile_id_for_seed(results, seed),
                setup_id=baseline_setup_id(seed),
                status=run_status(results, baseline_setup_id(seed)),
                dependency_status=baseline_dependency_status(results, seed),
            )
        )

    for family in FEATURE_FAMILIES:
        stage1_setup = drop_setup_id(family.feature_name, seed=SCREENING_SEED)
        rows.append(
            PlanRow(
                stage="stage1",
                feature_name=family.feature_name,
                seed=SCREENING_SEED,
                feature_profile_id=family.drop_profile_id,
                setup_id=stage1_setup,
                status=run_status(results, stage1_setup),
                dependency_status=stage1_dependency_status(results, family),
            )
        )
        for variant_id in family.stage2_variant_ids:
            for seed in BASELINE_SEEDS:
                stage2_setup = variant_setup_id(family.feature_name, variant_id, seed=seed)
                rows.append(
                    PlanRow(
                        stage="stage2",
                        feature_name=family.feature_name,
                        seed=seed,
                        feature_profile_id=variant_id,
                        setup_id=stage2_setup,
                        status=run_status(results, stage2_setup),
                        dependency_status=stage2_dependency_status(results, family, variant_id, seed),
                    )
                )
    return rows


def plan_frame(
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
) -> pd.DataFrame:
    rows = build_plan_rows(output_root=output_root, summary_path=summary_path)
    if not rows:
        return pd.DataFrame(columns=["stage", "feature_name", "seed", "feature_profile_id", "setup_id", "status", "dependency_status"])
    return pd.DataFrame.from_records(asdict(row) for row in rows)


def print_plan(
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
) -> pd.DataFrame:
    frame = plan_frame(output_root=output_root, summary_path=summary_path)
    if frame.empty:
        print("No feature-phase plan rows were generated.")
        return frame

    for stage in ("stage0", "stage1", "stage2"):
        stage_frame = frame.loc[frame["stage"] == stage, ["setup_id", "seed", "feature_name", "feature_profile_id", "status", "dependency_status"]]
        print(stage.upper())
        print(stage_frame.to_string(index=False))
        print()
    return frame


def resolve_feature_profile_paths(feature_profile_id: str) -> FeatureProfilePaths:
    get_feature_profile(feature_profile_id)
    output_dir = dataset_builder.resolve_output_dir(feature_profile_id)
    return FeatureProfilePaths(
        output_dir=output_dir,
        daily_path=output_dir / config.DAILY_MARKET_SERIES_NAME,
        panel_path=output_dir / config.MONTHLY_PANEL_NAME,
        metadata_path=output_dir / "feature_profile_metadata.json",
    )


def _metadata_profile_id(metadata_path: Path) -> str | None:
    if not metadata_path.exists():
        return None
    with metadata_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    feature_profile_id = payload.get("feature_profile_id")
    return str(feature_profile_id) if feature_profile_id is not None else None


def ensure_feature_profile_outputs(
    feature_profile_id: str,
    force_rebuild: bool = False,
) -> FeatureProfilePaths:
    paths = resolve_feature_profile_paths(feature_profile_id)
    cache_ready = (
        paths.daily_path.exists()
        and paths.panel_path.exists()
        and paths.metadata_path.exists()
        and _metadata_profile_id(paths.metadata_path) == feature_profile_id
    )
    if not force_rebuild and cache_ready:
        return paths
    dataset_builder.build_outputs(feature_profile_id=feature_profile_id)
    return paths


def execute_feature_phase_run(
    feature_run: FeaturePhaseRun,
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
    doc_path: str | Path | None = None,
    candidate_audit_path: str | Path | None = None,
    force_rerun: bool = False,
    force_rebuild_panels: bool = False,
) -> Path:
    resolved_output_root = resolve_output_root(output_root)
    existing_results = load_feature_phase_results(output_root=resolved_output_root, summary_path=summary_path)
    existing_row = result_row_for_setup(existing_results, feature_run.setup_id)
    if existing_row is not None and not force_rerun:
        artifact_dir = resolved_output_root / feature_run.setup_id
    else:
        profile_paths = ensure_feature_profile_outputs(
            feature_run.feature_profile_id,
            force_rebuild=(force_rerun or force_rebuild_panels),
        )
        dataset_validator.validate_output_dir(
            input_dir=profile_paths.output_dir,
            expect_feature_profile_id=feature_run.feature_profile_id,
        )
        setup = train.SetupConfig(
            setup_id=feature_run.setup_id,
            framework_id=config.FEATURE_PHASE_BASE_FRAMEWORK_ID,
            total_timesteps=config.FEATURE_PHASE_TOTAL_TIMESTEPS,
            study_phase=config.FEATURE_PHASE_NAME,
            base_framework_id=config.FEATURE_PHASE_BASE_FRAMEWORK_ID,
            feature_profile_id=feature_run.feature_profile_id,
            change_type=feature_run.change_type,
            changed_feature=feature_run.changed_feature,
            variant_id=feature_run.variant_id,
            notes=feature_run.notes,
            seed=feature_run.seed,
        )
        artifact_dir = train.train_setup(
            panel_path=profile_paths.panel_path,
            daily_path=profile_paths.daily_path,
            setup=setup,
            output_root=resolved_output_root,
        )

    sync_feature_phase_doc(
        output_root=resolved_output_root,
        summary_path=summary_path,
        doc_path=doc_path,
        candidate_audit_path=candidate_audit_path,
    )
    return artifact_dir


def multi_seed_comparison_path(
    feature_name: str,
    variant_id: str,
    output_root: str | Path | None = None,
) -> Path:
    resolved_output_root = resolve_output_root(output_root)
    return resolved_output_root / variant_setup_id(feature_name, variant_id, seed=SCREENING_SEED) / "multi_seed_comparison.json"


def drop_multi_seed_comparison_path(
    feature_name: str,
    output_root: str | Path | None = None,
) -> Path:
    resolved_output_root = resolve_output_root(output_root)
    return resolved_output_root / drop_setup_id(feature_name, seed=SCREENING_SEED) / "multi_seed_comparison.json"


def write_multi_seed_comparison(
    feature_name: str,
    variant_id: str,
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
) -> Path:
    results = load_feature_phase_results(output_root=output_root, summary_path=summary_path)
    required_setups = [baseline_setup_id(seed) for seed in BASELINE_SEEDS]
    required_setups.extend(variant_setup_id(feature_name, variant_id, seed=seed) for seed in BASELINE_SEEDS)
    missing = [setup_id for setup_id in required_setups if result_row_for_setup(results, setup_id) is None]
    if missing:
        raise ValueError(
            f"Variant {variant_id} for {feature_name} is missing required multi-seed comparison inputs: {missing}."
        )

    rows_by_seed: list[dict[str, Any]] = []
    for seed in BASELINE_SEEDS:
        baseline_row = result_row_for_setup(results, baseline_setup_id(seed))
        variant_row = result_row_for_setup(results, variant_setup_id(feature_name, variant_id, seed=seed))
        rows_by_seed.append(
            {
                "seed": seed,
                "baseline_setup_id": baseline_setup_id(seed),
                "variant_setup_id": variant_setup_id(feature_name, variant_id, seed=seed),
                "baseline_validation_reward": metric_value(baseline_row, "ValidationMeanReward"),
                "baseline_validation_spearman": metric_value(baseline_row, "ValidationMeanSpearman"),
                "variant_validation_reward": metric_value(variant_row, "ValidationMeanReward"),
                "variant_validation_spearman": metric_value(variant_row, "ValidationMeanSpearman"),
                "beats_baseline_on_both": variant_beats_baseline_for_seed(results, feature_name, variant_id, seed),
            }
        )

    winner_confirmed = variant_is_confirmed(results, feature_name, variant_id)
    comparison_payload = {
        "feature_name": feature_name,
        "variant_id": variant_id,
        "framework_id": config.FEATURE_PHASE_BASE_FRAMEWORK_ID,
        "seeds": list(BASELINE_SEEDS),
        "rows_by_seed": rows_by_seed,
        "mean_baseline_validation_reward": float(
            sum(row["baseline_validation_reward"] or 0.0 for row in rows_by_seed) / len(rows_by_seed)
        ),
        "mean_baseline_validation_spearman": float(
            sum(row["baseline_validation_spearman"] or 0.0 for row in rows_by_seed) / len(rows_by_seed)
        ),
        "mean_variant_validation_reward": float(
            sum(row["variant_validation_reward"] or 0.0 for row in rows_by_seed) / len(rows_by_seed)
        ),
        "mean_variant_validation_spearman": float(
            sum(row["variant_validation_spearman"] or 0.0 for row in rows_by_seed) / len(rows_by_seed)
        ),
        "winner_confirmed": winner_confirmed,
    }

    output_path = multi_seed_comparison_path(feature_name, variant_id, output_root=output_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(comparison_payload, handle, indent=2, sort_keys=True)
    return output_path


def write_drop_multi_seed_comparison(
    feature_name: str,
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
) -> Path:
    results = load_feature_phase_results(output_root=output_root, summary_path=summary_path)
    required_setups = [baseline_setup_id(seed) for seed in BASELINE_SEEDS]
    required_setups.extend(drop_setup_id(feature_name, seed=seed) for seed in BASELINE_SEEDS)
    missing = [setup_id for setup_id in required_setups if result_row_for_setup(results, setup_id) is None]
    if missing:
        raise ValueError(f"Drop confirmation for {feature_name} is missing required multi-seed comparison inputs: {missing}.")

    rows_by_seed: list[dict[str, Any]] = []
    for seed in BASELINE_SEEDS:
        baseline_row = result_row_for_setup(results, baseline_setup_id(seed))
        drop_row = result_row_for_setup(results, drop_setup_id(feature_name, seed=seed))
        rows_by_seed.append(
            {
                "seed": seed,
                "baseline_setup_id": baseline_setup_id(seed),
                "drop_setup_id": drop_setup_id(feature_name, seed=seed),
                "baseline_validation_reward": metric_value(baseline_row, "ValidationMeanReward"),
                "baseline_validation_spearman": metric_value(baseline_row, "ValidationMeanSpearman"),
                "drop_validation_reward": metric_value(drop_row, "ValidationMeanReward"),
                "drop_validation_spearman": metric_value(drop_row, "ValidationMeanSpearman"),
                "beats_baseline_on_both": drop_feature_beats_baseline_for_seed(results, feature_name, seed),
            }
        )

    comparison_payload = {
        "feature_name": feature_name,
        "comparison_type": "drop_feature",
        "framework_id": config.FEATURE_PHASE_BASE_FRAMEWORK_ID,
        "seeds": list(BASELINE_SEEDS),
        "rows_by_seed": rows_by_seed,
        "mean_baseline_validation_reward": float(
            sum(row["baseline_validation_reward"] or 0.0 for row in rows_by_seed) / len(rows_by_seed)
        ),
        "mean_baseline_validation_spearman": float(
            sum(row["baseline_validation_spearman"] or 0.0 for row in rows_by_seed) / len(rows_by_seed)
        ),
        "mean_drop_validation_reward": float(
            sum(row["drop_validation_reward"] or 0.0 for row in rows_by_seed) / len(rows_by_seed)
        ),
        "mean_drop_validation_spearman": float(
            sum(row["drop_validation_spearman"] or 0.0 for row in rows_by_seed) / len(rows_by_seed)
        ),
        "winner_confirmed": drop_feature_is_confirmed(results, feature_name),
        "promoted_baseline_profile_id": REMOVAL_CONFIRMATION_BASELINES.get(feature_name, ""),
    }

    output_path = drop_multi_seed_comparison_path(feature_name, output_root=output_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(comparison_payload, handle, indent=2, sort_keys=True)
    return output_path


def _format_metric(value: float | None) -> str:
    return "" if value is None else f"{value:.4f}"


def _date_from_timestamp(timestamp: Any) -> str:
    if pd.isna(timestamp):
        return ""
    text = str(timestamp)
    return text.split("T", maxsplit=1)[0]


def _stage_for_result(row: pd.Series) -> str:
    setup_id = str(row.get("SetupID", ""))
    if _is_shadow_baseline_setup_id(setup_id):
        return "shadow_baseline"
    if _is_shadow_candidate_setup_id(setup_id):
        return "shadow_screen"
    if setup_id.startswith("FT-BASE-"):
        return "stage0"
    if setup_id.startswith("FT-ABL-"):
        return "stage1"
    if setup_id.startswith("FT-VAR-"):
        return "stage2"
    return ""


def _feature_for_result(row: pd.Series) -> str:
    stage = _stage_for_result(row)
    if stage in {"stage0", "shadow_baseline"}:
        return "baseline"
    feature_name = row.get("ChangedFeature", "")
    return "" if pd.isna(feature_name) else str(feature_name)


def decision_label_for_result(results: pd.DataFrame, row: pd.Series) -> str:
    stage = _stage_for_result(row)
    feature_name = _feature_for_result(row)
    if stage == "shadow_baseline":
        return "shadow baseline completed"
    if stage == "shadow_screen":
        candidate_id = _candidate_id_for_result(row)
        if candidate_id is None:
            return "completed"
        if shadow_candidate_is_confirmed(results, candidate_id):
            return "winner confirmed"
        if shadow_candidate_has_failed_confirmation(results, candidate_id):
            return "screened candidate"
        if shadow_candidate_is_seed42_winner(results, candidate_id):
            return "winner promoted"
        return "screened candidate"
    if stage == "stage0":
        return "baseline anchor completed"
    if stage == "stage1":
        return stage1_decision(results, feature_name) or "stage1 completed"
    if stage == "stage2":
        variant_id = str(row.get("VariantID", ""))
        family = get_feature_family(feature_name)
        if selected_family_variant_id(results, family) == variant_id:
            if variant_is_confirmed(results, feature_name, variant_id):
                return "winner confirmed"
            return "winner promoted"
        if family_has_any_stage2_screen(results, family):
            return "redesign screened"
        if variant_is_confirmed(results, feature_name, variant_id):
            return "winner confirmed"
        return "redesign screened"
    return "completed"


def decision_note_for_result(results: pd.DataFrame, row: pd.Series) -> str:
    stage = _stage_for_result(row)
    if stage == "shadow_baseline":
        seed = seed_value_from_setup_id(_row_setup_id(row))
        return f"Seed-{seed} canonical shadow baseline anchor." if seed is not None else "Canonical shadow baseline anchor."
    if stage == "shadow_screen":
        candidate_id = _candidate_id_for_result(row)
        if candidate_id is None:
            return ""
        candidate = get_shadow_candidate(candidate_id)
        shortlist_entry = get_ratio_tail_shortlist_entry(candidate_id)
        screen_kind = "additive" if candidate.candidate_type == "additive" else "replacement"
        follow_up_suffix = ""
        if shortlist_entry and shortlist_entry.contingent_replacement_feature:
            follow_up_suffix = (
                f" Contingent replacement follow-up against `{shortlist_entry.contingent_replacement_feature}` "
                "opens only after additive confirmation."
            )
        if shadow_candidate_is_confirmed(results, candidate_id):
            return (
                f"Confirmed isolated {screen_kind} winner against the seed-matched canonical shadow baseline across "
                f"seeds 42, 7, and 13.{follow_up_suffix}"
            )
        if shadow_candidate_has_failed_confirmation(results, candidate_id):
            return (
                f"Beat the seed-42 canonical shadow baseline but failed multi-seed confirmation as an isolated "
                f"{screen_kind} screen against the seed-matched shadow baselines.{follow_up_suffix}"
            )
        if shadow_candidate_is_seed42_winner(results, candidate_id):
            return (
                f"Beat `{shadow_baseline_setup_id(SCREENING_SEED)}` on both outer-validation metrics; awaiting seed "
                f"7 and 13 confirmation for this isolated {screen_kind} screen.{follow_up_suffix}"
            )
        return (
            f"Did not beat `{shadow_baseline_setup_id(SCREENING_SEED)}` on both outer-validation metrics in this "
            f"isolated {screen_kind} screen.{follow_up_suffix}"
        )
    if stage == "stage0":
        seed = seed_value_from_setup_id(str(row.get("SetupID", "")))
        return f"Seed-{seed} anchor." if seed is not None else "Baseline anchor."
    if stage == "stage1":
        feature_name = _feature_for_result(row)
        decision = stage1_decision(results, feature_name)
        if decision == "removal confirmed":
            promoted_profile_id = REMOVAL_CONFIRMATION_BASELINES[feature_name]
            return (
                f"Removal beat the seed-matched baselines across seeds 42, 7, and 13; live baseline relocked to "
                f"`{promoted_profile_id}`."
            )
        if decision == "removal rejected":
            return (
                f"Removal beat `{baseline_setup_id(SCREENING_SEED)}` at seed 42 but failed promoted-seed confirmation; "
                f"live baseline stays `{config.DEFAULT_FEATURE_PROFILE_ID}`."
            )
        if decision == "removal promoted":
            promoted_seeds = [
                str(seed)
                for seed in PROMOTION_SEEDS
                if result_row_for_setup(results, drop_setup_id(feature_name, seed=seed)) is not None
            ]
            if promoted_seeds:
                return (
                    f"Removal beat `{baseline_setup_id(SCREENING_SEED)}` and promoted seeds "
                    f"{', '.join(promoted_seeds)} are recorded; awaiting full confirmation."
                )
            return f"Removal beat `{baseline_setup_id(SCREENING_SEED)}` and is awaiting promoted-seed confirmation."
        return f"Compared against `{baseline_setup_id(SCREENING_SEED)}`."
    if stage == "stage2":
        feature_name = _feature_for_result(row)
        variant_id = str(row.get("VariantID", ""))
        family = get_feature_family(feature_name)
        selected_variant_id = selected_family_variant_id(results, family)
        if selected_variant_id == variant_id:
            if variant_is_confirmed(results, feature_name, variant_id):
                return "Selected family winner; confirmed across seeds 42, 7, and 13."
            if all(
                result_row_for_setup(results, variant_setup_id(feature_name, variant_id, seed=seed)) is not None
                for seed in PROMOTION_SEEDS
            ):
                return "Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds."
            return f"Selected family winner after the seed-42 redesign screen. Beat `{baseline_setup_id(SCREENING_SEED)}` on validation reward and Spearman."
        if variant_is_promotable(results, feature_name, variant_id):
            if selected_variant_id is not None:
                return f"Beat `{baseline_setup_id(SCREENING_SEED)}` on both validation metrics but ranked below `{selected_variant_id}` in the family screen."
            return f"Beat `{baseline_setup_id(SCREENING_SEED)}` on both validation metrics; family screening is still in progress."
        if family_stage2_screen_complete(results, family):
            return f"Did not beat `{baseline_setup_id(SCREENING_SEED)}` on both validation metrics."
        return f"Screened against `{baseline_setup_id(SCREENING_SEED)}`; family screening is still in progress."
    return ""


def decision_log_rows(results: pd.DataFrame) -> list[dict[str, str]]:
    if results.empty:
        return []

    ordered = results.copy()
    if "TimestampUTC" in ordered.columns:
        ordered = ordered.sort_values(["TimestampUTC", "SetupID"], kind="stable")
    else:
        ordered = ordered.sort_values(["SetupID"], kind="stable")

    rows: list[dict[str, str]] = []
    for _, row in ordered.iterrows():
        rows.append(
            {
                "Date": _date_from_timestamp(row.get("TimestampUTC", "")),
                "Feature": _feature_for_result(row),
                "Stage": _stage_for_result(row),
                "SetupID": str(row.get("SetupID", "")),
                "Validation Reward": _format_metric(metric_value(row, "ValidationMeanReward")),
                "Validation Spearman": _format_metric(metric_value(row, "ValidationMeanSpearman")),
                "Decision": decision_label_for_result(results, row),
                "Notes": decision_note_for_result(results, row),
            }
        )
    return rows


def run_results_rows(results: pd.DataFrame) -> list[dict[str, str]]:
    if results.empty:
        return []

    ordered = results.copy()
    if "TimestampUTC" in ordered.columns:
        ordered = ordered.sort_values(["TimestampUTC", "SetupID"], kind="stable")
    else:
        ordered = ordered.sort_values(["SetupID"], kind="stable")

    rows: list[dict[str, str]] = []
    for _, row in ordered.iterrows():
        rows.append(
            {
                "Date": _date_from_timestamp(row.get("TimestampUTC", "")),
                "SetupID": str(row.get("SetupID", "")),
                "FeatureProfileID": str(row.get("FeatureProfileID", "")),
                "Seed": "" if seed_value_from_setup_id(str(row.get("SetupID", ""))) is None else str(seed_value_from_setup_id(str(row.get("SetupID", "")))),
                "Validation Reward": _format_metric(metric_value(row, "ValidationMeanReward")),
                "Validation Spearman": _format_metric(metric_value(row, "ValidationMeanSpearman")),
                "Decision": decision_label_for_result(results, row),
                "Notes": decision_note_for_result(results, row),
            }
        )
    return rows


def first_wave_expected_setup_ids() -> tuple[str, ...]:
    return (baseline_setup_id(SCREENING_SEED),) + tuple(
        drop_setup_id(family.feature_name, seed=SCREENING_SEED)
        for family in FEATURE_FAMILIES
    )


def first_wave_is_complete(results: pd.DataFrame) -> bool:
    return all(result_row_for_setup(results, setup_id) is not None for setup_id in first_wave_expected_setup_ids())


def exploratory_redesign_shortlist_rows(results: pd.DataFrame) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for feature_name in EXPLORATORY_STAGE2_FAMILY_ORDER:
        family = get_feature_family(feature_name)
        selected_variant_id = selected_family_variant_id(results, family)
        if selected_variant_id is not None and variant_is_confirmed(results, family.feature_name, selected_variant_id):
            reason = f"Seed-42 redesign screen complete; `{selected_variant_id}` is confirmed across seeds 42, 7, and 13."
        elif selected_variant_id is not None:
            reason = f"Seed-42 redesign screen complete; `{selected_variant_id}` is the selected family winner."
        elif family_stage2_screen_complete(results, family):
            reason = "Seed-42 redesign screen complete; no approved variant beat the baseline on both validation metrics."
        elif family_has_any_stage2_screen(results, family):
            reason = "Seed-42 redesign screening is in progress for this approved family."
        elif stage1_decision(results, family.feature_name) == "candidate for redesign":
            reason = "Raw Stage 1 candidate for redesign at seed 42."
        else:
            reason = "Exploratory redesign override for this one-wave Stage 2 shortlist."

        rows.append(
            {
                "Feature": family.feature_name,
                "Reason": reason,
                "Allowed Variants": ", ".join(f"`{variant_id}`" for variant_id in family.stage2_variant_ids),
                "Execution Priority": str(EXPLORATORY_STAGE2_PRIORITY[family.feature_name]),
            }
        )
    return rows


def multi_seed_removal_confirmation_rows(results: pd.DataFrame) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for feature_name, promoted_profile_id in REMOVAL_CONFIRMATION_BASELINES.items():
        raw_decision = raw_stage1_decision(results, feature_name)
        if raw_decision is None:
            gate_status = "planned"
        elif drop_feature_is_seed42_winner(results, feature_name):
            gate_status = "passed"
        else:
            gate_status = "failed"

        promoted_seeds = [
            str(seed)
            for seed in PROMOTION_SEEDS
            if result_row_for_setup(results, drop_setup_id(feature_name, seed=seed)) is not None
        ]
        promoted_seed_text = ", ".join(promoted_seeds) if promoted_seeds else "-"

        if drop_feature_is_confirmed(results, feature_name):
            result = "removal confirmed"
            canonical_outcome = (
                f"Locked baseline relocked to `{promoted_profile_id}`; `{feature_name}` is neutralized to `0.5` in the live panel."
            )
        elif drop_feature_has_failed_confirmation(results, feature_name):
            result = "removal rejected"
            canonical_outcome = (
                f"Keep `{config.DEFAULT_FEATURE_PROFILE_ID}` as the live baseline; no replacement testing opens in this wave."
            )
        elif has_drop_confirmation_lane(results, feature_name):
            result = "removal promoted"
            canonical_outcome = "Await promoted-seed confirmation before relocking the live baseline."
        else:
            result = "planned"
            canonical_outcome = f"Current live baseline stays `{live_feature_profile_id(results)}` until multi-seed confirmation exists."

        rows.append(
            {
                "Feature": feature_name,
                "Seed-42 Gate": gate_status,
                "Promoted Seeds": promoted_seed_text,
                "Result": result,
                "Canonical Outcome": canonical_outcome,
            }
        )
    return rows


def provisional_feature_set_rows(results: pd.DataFrame) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    baseline_exists = result_row_for_setup(results, baseline_setup_id(SCREENING_SEED)) is not None

    for family in FEATURE_FAMILIES:
        drop_setup = drop_setup_id(family.feature_name, seed=SCREENING_SEED)
        drop_exists = result_row_for_setup(results, drop_setup) is not None
        stage1_label = stage1_decision(results, family.feature_name)
        matrix_status = feature_matrix_status(results, family)

        if not baseline_exists:
            current_status = "await baseline"
            evidence_setup_ids = ""
            interpretation = "Baseline anchor has not been recorded yet."
            next_action = "await baseline"
        elif not drop_exists:
            current_status = "baseline only"
            evidence_setup_ids = baseline_setup_id(SCREENING_SEED)
            interpretation = f"Baseline anchor is recorded; `{family.feature_name}` has not been screened yet."
            next_action = "await screen"
        elif matrix_status == "winner confirmed":
            current_status = "winner confirmed"
            evidence_setup_ids = f"{baseline_setup_id(SCREENING_SEED)}, {drop_setup}"
            interpretation = f"A redesign variant for `{family.feature_name}` has been confirmed across the promoted seeds."
            next_action = "hold"
        elif matrix_status == "removal confirmed":
            current_status = "removed from baseline"
            evidence_setup_ids = f"{baseline_setup_id(SCREENING_SEED)}, {drop_setup}"
            interpretation = (
                f"Dropping `{family.feature_name}` beat the seed-matched baselines across seeds 42, 7, and 13, "
                "so the live baseline now neutralizes it to `0.5`."
            )
            next_action = "hold"
        elif matrix_status == "removal rejected":
            current_status = "removal rejected"
            evidence_setup_ids = f"{baseline_setup_id(SCREENING_SEED)}, {drop_setup}"
            interpretation = (
                f"Dropping `{family.feature_name}` won at seed 42 but failed promoted-seed confirmation, so the live baseline stays unchanged."
            )
            next_action = "hold"
        elif matrix_status == "removal promoted":
            current_status = "removal promoted"
            evidence_setup_ids = f"{baseline_setup_id(SCREENING_SEED)}, {drop_setup}"
            interpretation = f"Dropping `{family.feature_name}` beat the seed-42 baseline and is awaiting promoted-seed confirmation."
            next_action = "await confirmation"
        elif matrix_status == "winner promoted":
            current_status = "winner promoted"
            evidence_setup_ids = f"{baseline_setup_id(SCREENING_SEED)}, {drop_setup}"
            interpretation = f"A redesign variant for `{family.feature_name}` beat the baseline at seed 42."
            next_action = "hold"
        elif matrix_status == "redesign screened":
            current_status = "redesign screened"
            evidence_setup_ids = f"{baseline_setup_id(SCREENING_SEED)}, {drop_setup}"
            if family_stage2_screen_complete(results, family):
                interpretation = f"Redesign variants for `{family.feature_name}` have been screened."
            else:
                interpretation = f"Redesign variants for `{family.feature_name}` are being screened at seed 42."
            next_action = "hold"
        elif stage1_label == "provisionally valuable":
            current_status = "provisionally valuable"
            evidence_setup_ids = f"{baseline_setup_id(SCREENING_SEED)}, {drop_setup}"
            if is_exploratory_stage2_family(family.feature_name):
                interpretation = f"Dropping `{family.feature_name}` hurt both validation metrics, but this family is on the exploratory Stage 2 shortlist."
                next_action = "open redesign variants"
            else:
                interpretation = f"Dropping `{family.feature_name}` hurt both validation metrics."
                next_action = "hold"
        else:
            current_status = "candidate for redesign"
            evidence_setup_ids = f"{baseline_setup_id(SCREENING_SEED)}, {drop_setup}"
            interpretation = f"Dropping `{family.feature_name}` was mixed or improved at least one validation metric."
            next_action = "open redesign variants"

        rows.append(
            {
                "Feature": family.feature_name,
                "Current Status": current_status,
                "Evidence SetupIDs": evidence_setup_ids,
                "Current Interpretation": interpretation,
                "Next Action": next_action,
            }
        )
    return rows


def shadow_candidate_registry_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for candidate in SHADOW_FEATURE_CANDIDATES:
        rows.append(
            {
                "Candidate": candidate.candidate_id,
                "Type": candidate.candidate_type,
                "Replacement Family": candidate.replacement_feature or "",
                "Candidate Set ID": candidate.candidate_set_id,
                "InputFeatureSetID": candidate.input_feature_set_id,
                "Description": candidate.description,
            }
        )
    return rows


def approved_ratio_and_tail_shortlist_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for entry in APPROVED_RATIO_AND_TAIL_SHORTLIST:
        follow_up = (
            f"replacement for `{entry.contingent_replacement_feature}` after additive confirmation"
            if entry.contingent_replacement_feature
            else "none"
        )
        rows.append(
            {
                "Candidate": entry.candidate_id,
                "Primary Screen": entry.primary_screen_type,
                "Contingent Replacement Follow-Up": follow_up,
                "RL Screen Order": str(entry.execution_priority),
                "Reason": entry.reason,
            }
        )
    return rows


def load_standalone_candidate_audit(candidate_audit_path: str | Path | None = None) -> pd.DataFrame:
    resolved_path = Path(candidate_audit_path) if candidate_audit_path is not None else FEATURE_CANDIDATE_AUDIT_PATH
    if not resolved_path.exists():
        return pd.DataFrame()
    return pd.read_csv(resolved_path)


def standalone_candidate_audit_rows(candidate_audit_path: str | Path | None = None) -> list[dict[str, str]]:
    audit = load_standalone_candidate_audit(candidate_audit_path=candidate_audit_path)
    if audit.empty:
        return []
    ordered = audit.sort_values(["StandaloneMeanSpearman", "CandidateID"], ascending=[False, True], kind="stable")
    rows: list[dict[str, str]] = []
    for _, row in ordered.iterrows():
        rl_reason = "" if pd.isna(row.get("RLScreenReason", "")) else str(row.get("RLScreenReason", ""))
        if rl_reason == "approved_shortlist":
            eligibility = "approved shortlist"
        elif bool(row.get("EligibleForRLScreen", False)):
            eligibility = "top-6 screen"
        else:
            eligibility = "below cut"
        rows.append(
            {
                "Candidate": str(row.get("CandidateID", "")),
                "Type": str(row.get("CandidateType", "")),
                "Replacement Family": "" if pd.isna(row.get("ReplacementFeature", "")) else str(row.get("ReplacementFeature", "")),
                "Candidate Set ID": str(row.get("CandidateSetID", "")),
                "Standalone Mean Spearman": _format_metric(row.get("StandaloneMeanSpearman")),
                "Outer Validation Months": "" if pd.isna(row.get("OuterValidationMonths", "")) else str(int(row.get("OuterValidationMonths", 0))),
                "RL Screen Eligibility": eligibility,
                "RL Screen Order": "" if pd.isna(row.get("RLScreenOrder", "")) else str(int(row.get("RLScreenOrder", 0))),
            }
        )
    return rows


def _candidate_id_for_result(row: pd.Series) -> str | None:
    if not _is_shadow_candidate_row(row):
        return None
    feature_profile_id = "" if pd.isna(row.get("FeatureProfileID", "")) else str(row.get("FeatureProfileID", ""))
    input_feature_set_id = "" if pd.isna(row.get("InputFeatureSetID", "")) else str(row.get("InputFeatureSetID", ""))
    for candidate in SHADOW_FEATURE_CANDIDATES:
        if candidate.source_profile_id and candidate.source_profile_id == feature_profile_id:
            return candidate.candidate_id
        if candidate.input_feature_set_id == input_feature_set_id and candidate.candidate_type == "additive":
            return candidate.candidate_id
    return None


def rl_candidate_screen_rows(results: pd.DataFrame) -> list[dict[str, str]]:
    shadow_lane_results = _shadow_lane_results_from_results(results)
    if shadow_lane_results.empty:
        return []
    ordered = shadow_lane_results.loc[shadow_lane_results.apply(_is_shadow_candidate_row, axis=1)].copy()
    if ordered.empty:
        return []
    if "TimestampUTC" in ordered.columns:
        ordered = ordered.sort_values(["TimestampUTC", "SetupID"], kind="stable")
    rows: list[dict[str, str]] = []
    for _, row in ordered.iterrows():
        candidate_id = _candidate_id_for_result(row)
        if candidate_id is None:
            continue
        candidate = get_shadow_candidate(candidate_id)
        rows.append(
            {
                "Date": _date_from_timestamp(row.get("TimestampUTC", "")),
                "Candidate": candidate_id,
                "Type": candidate.candidate_type,
                "SetupID": str(row.get("SetupID", "")),
                "InputFeatureSetID": str(row.get("InputFeatureSetID", "")),
                "Validation Reward": _format_metric(metric_value(row, "ValidationMeanReward")),
                "Validation Spearman": _format_metric(metric_value(row, "ValidationMeanSpearman")),
                "Decision": decision_label_for_result(shadow_lane_results, row),
            }
        )
    return rows


def canonical_promotion_decision_rows(results: pd.DataFrame) -> list[dict[str, str]]:
    shadow_results = _shadow_lane_results_from_results(results)
    rows: list[dict[str, str]] = []
    for candidate in SHADOW_FEATURE_CANDIDATES:
        shortlist_entry = get_ratio_tail_shortlist_entry(candidate.candidate_id)
        matching_rows = shadow_results.loc[
            shadow_results.apply(lambda row: _candidate_id_for_result(row) == candidate.candidate_id, axis=1)
        ] if not shadow_results.empty else pd.DataFrame()
        if matching_rows.empty:
            decision = "planned"
            if shortlist_entry and shortlist_entry.contingent_replacement_feature:
                notes = (
                    "Await additive RL screen. Only after additive confirmation may the contingent replacement "
                    f"follow-up against `{shortlist_entry.contingent_replacement_feature}` open."
                )
            else:
                notes = "Await standalone audit and RL screen."
        else:
            ordered = matching_rows.sort_values(["TimestampUTC", "SetupID"], kind="stable") if "TimestampUTC" in matching_rows.columns else matching_rows
            latest = ordered.iloc[-1]
            decision = decision_label_for_result(shadow_results, latest)
            notes = decision_note_for_result(shadow_results, latest)
        rows.append(
            {
                "Candidate": candidate.candidate_id,
                "Type": candidate.candidate_type,
                "Canonical Target": candidate.replacement_feature or f"add `{candidate.candidate_id}`",
                "Decision": decision,
                "Notes": notes,
            }
        )
    return rows


def render_feature_phase_doc(
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
    candidate_audit_path: str | Path | None = None,
) -> str:
    results = load_feature_phase_results(output_root=output_root, summary_path=summary_path)
    locked_profile = live_feature_profile(results)
    locked_feature_profile_id = locked_profile.feature_profile_id

    lines: list[str] = [
        "# Feature Phase",
        "",
        "## Purpose",
        "",
        "This is the active feature-phase planning and tracking document.",
        "",
        "Use it to track:",
        "",
        "- the locked backbone for feature work",
        "- the feature-comparison methodology",
        "- the experiment matrix for feature ablations and redesigns",
        "- final keep, drop, and alter decisions",
        "",
        "## Locked Baseline",
        "",
        "Active backbone:",
        "",
        f"- `{config.FEATURE_PHASE_BASE_FRAMEWORK_ID}`",
        "",
        "Active feature profile:",
        "",
        f"- `{locked_feature_profile_id}`",
        "",
        "Locked feature set:",
        "",
    ]
    lines.extend(f"- `{feature_name}`" for feature_name in locked_profile.active_features)
    if locked_feature_profile_id != config.DEFAULT_FEATURE_PROFILE_ID:
        lines.extend(
            [
                "",
                f"- canonical panel schema remains the same; `distance_to_3m_high` is neutralized to `{locked_profile.neutral_fill_value}`",
            ]
        )
    lines.extend(
        [
            "",
            "Locked comparison rules:",
            "",
            f"- monthly-only framework stays fixed at `{config.FEATURE_PHASE_BASE_FRAMEWORK_ID}`",
            "- daily-input variants are out of scope",
            "- validation reward is the primary metric",
            "- validation Spearman is the secondary metric",
            "- seed `42` is the screening seed",
            "- seeds `7` and `13` are used only after a feature edit beats the full",
            "  feature baseline on both validation reward and validation Spearman",
            "",
            "## Methodology",
            "",
            "Stage order:",
            "",
            "1. establish the baseline anchor",
            "2. run leave-one-out value tests on seed `42`",
            "3. open redesign variants only for weak or ambiguous features",
            "4. expand only confirmed winners to seeds `7` and `13`",
            "",
            "Metadata that must be written for feature-phase runs:",
            "",
            f"- `StudyPhase = {config.FEATURE_PHASE_NAME}`",
            f"- `BaseFrameworkID = {config.FEATURE_PHASE_BASE_FRAMEWORK_ID}`",
            "- `FeatureProfileID`",
            "- `ChangeType`",
            "- `ChangedFeature`",
            "- `VariantID`",
            "",
            "Naming rules:",
            "",
            "- baseline anchor: `FT-BASE-3M-CONTEXT-S<SEED>`",
            "- leave-one-out ablation: `FT-ABL-DROP-<FEATURE>-S42`",
            "- feature variant screen: `FT-VAR-<FEATURE>-<VARIANT>-S42`",
            "",
            "Decision rules:",
            "",
            "- if dropping a feature lowers both validation reward and validation Spearman,",
            "  label it `provisionally valuable`",
            "- if dropping a feature is mixed or improves either validation metric, label it",
            "  `candidate for redesign`",
            "- a Stage 1 removal-confirmation lane may expand a drop run to seeds `7` and `13`",
            "  only after the seed-42 drop beats the baseline on both validation metrics",
            "- only a stage-2 feature variant that beats the full-feature baseline on both",
            "  validation reward and validation Spearman may expand to seeds `7` and `13`",
            "- do not combine multiple winning feature edits in the same wave",
            "",
            "### Approved Exploratory Redesign Shortlist",
            "",
            "| Feature | Reason | Allowed Variants | Execution Priority |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in exploratory_redesign_shortlist_rows(results):
        lines.append(
            f"| `{row['Feature']}` | {row['Reason']} | {row['Allowed Variants']} | {row['Execution Priority']} |"
        )

    lines.extend(
        [
            "",
            "### Stage 1 Multi-Seed Removal Confirmation",
            "",
            "| Feature | Seed-42 Gate | Promoted Seeds | Result | Canonical Outcome |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in multi_seed_removal_confirmation_rows(results):
        lines.append(
            f"| `{row['Feature']}` | {row['Seed-42 Gate']} | {row['Promoted Seeds']} | {row['Result']} | {row['Canonical Outcome']} |"
        )

    lines.extend(
        [
            "",
            "## Experiment Matrix",
            "",
            "### Stage 0: Baseline Anchors",
            "",
            "| SetupPattern | Backbone | FeatureProfileID | Status | Notes |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for seed in BASELINE_SEEDS:
        lines.append(
            f"| `{baseline_setup_id(seed)}` | `{config.FEATURE_PHASE_BASE_FRAMEWORK_ID}` | "
            f"`{baseline_feature_profile_id_for_seed(results, seed)}` | {run_status(results, baseline_setup_id(seed)).replace('pending', 'planned')} | "
            f"Seed-{seed} anchor |"
        )

    lines.extend(
        [
            "",
            "### Stage 1 And Stage 2 Matrix",
            "",
            "| Feature | Current Definition | Stage 1 Test | Stage 2 Allowed Variants | Status |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for family in FEATURE_FAMILIES:
        stage2_variants = ", ".join(f"`{variant_id}`" for variant_id in family.stage2_variant_ids)
        lines.append(
            f"| `{family.feature_name}` | {family.current_definition} | drop `{family.feature_name}` | "
            f"{stage2_variants} | {feature_matrix_status(results, family)} |"
        )

    lines.extend(
        [
            "",
            "## Decision Log",
            "",
            "| Date | Feature | Stage | SetupID | Validation Reward | Validation Spearman | Decision | Notes |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )

    log_rows = decision_log_rows(results)
    if log_rows:
        for row in log_rows:
            lines.append(
                f"| {row['Date']} | {row['Feature']} | {row['Stage']} | `{row['SetupID']}` | "
                f"{row['Validation Reward']} | {row['Validation Spearman']} | {row['Decision']} | {row['Notes']} |"
            )
    else:
        lines.extend(
            [
                "|  |  |  |  |  |  |  |  |",
                "|  |  |  |  |  |  |  |  |",
                "|  |  |  |  |  |  |  |  |",
            ]
        )

    lines.extend(
        [
            "",
            "## Run Results",
            "",
            "| Date | SetupID | FeatureProfileID | Seed | Validation Reward | Validation Spearman | Decision | Notes |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    completed_runs = run_results_rows(results)
    if completed_runs:
        for row in completed_runs:
            lines.append(
                f"| {row['Date']} | `{row['SetupID']}` | `{row['FeatureProfileID']}` | {row['Seed']} | "
                f"{row['Validation Reward']} | {row['Validation Spearman']} | {row['Decision']} | {row['Notes']} |"
            )
    else:
        lines.append("|  |  |  |  |  |  |  |  |")

    lines.extend(
        [
            "",
            "## Current Provisional Feature Set",
            "",
            "| Feature | Current Status | Evidence SetupIDs | Current Interpretation | Next Action |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in provisional_feature_set_rows(results):
        lines.append(
            f"| `{row['Feature']}` | {row['Current Status']} | {row['Evidence SetupIDs']} | "
            f"{row['Current Interpretation']} | {row['Next Action']} |"
        )

    lines.extend(
        [
            "",
            "## Approved Ratio And Tail Shortlist",
            "",
            "| Candidate | Primary Screen | Contingent Replacement Follow-Up | RL Screen Order | Reason |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in approved_ratio_and_tail_shortlist_rows():
        lines.append(
            f"| `{row['Candidate']}` | {row['Primary Screen']} | {row['Contingent Replacement Follow-Up']} | "
            f"{row['RL Screen Order']} | {row['Reason']} |"
        )

    lines.extend(
        [
            "",
            "## Shadow Candidate Registry",
            "",
            "| Candidate | Type | Replacement Family | Candidate Set ID | InputFeatureSetID | Description |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in shadow_candidate_registry_rows():
        lines.append(
            f"| `{row['Candidate']}` | {row['Type']} | {row['Replacement Family']} | "
            f"`{row['Candidate Set ID']}` | `{row['InputFeatureSetID']}` | {row['Description']} |"
        )

    lines.extend(
        [
            "",
            "## Standalone Candidate Audit",
            "",
            "| Candidate | Type | Replacement Family | Candidate Set ID | Standalone Mean Spearman | Outer Validation Months | RL Screen Eligibility | RL Screen Order |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    standalone_rows = standalone_candidate_audit_rows(candidate_audit_path=candidate_audit_path)
    if standalone_rows:
        for row in standalone_rows:
            lines.append(
                f"| `{row['Candidate']}` | {row['Type']} | {row['Replacement Family']} | "
                f"`{row['Candidate Set ID']}` | {row['Standalone Mean Spearman']} | {row['Outer Validation Months']} | "
                f"{row['RL Screen Eligibility']} | {row['RL Screen Order']} |"
            )
    else:
        lines.append("|  |  |  |  |  |  |  |  |")

    lines.extend(
        [
            "",
            "## RL Candidate Screens",
            "",
            "| Date | Candidate | Type | SetupID | InputFeatureSetID | Validation Reward | Validation Spearman | Decision |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    candidate_screen_rows = rl_candidate_screen_rows(results)
    if candidate_screen_rows:
        for row in candidate_screen_rows:
            lines.append(
                f"| {row['Date']} | `{row['Candidate']}` | {row['Type']} | `{row['SetupID']}` | "
                f"`{row['InputFeatureSetID']}` | {row['Validation Reward']} | {row['Validation Spearman']} | {row['Decision']} |"
            )
    else:
        lines.append("|  |  |  |  |  |  |  |  |")

    lines.extend(
        [
            "",
            "## Canonical Promotion Decisions",
            "",
            "| Candidate | Type | Canonical Target | Decision | Notes |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in canonical_promotion_decision_rows(results):
        lines.append(
            f"| `{row['Candidate']}` | {row['Type']} | {row['Canonical Target']} | {row['Decision']} | {row['Notes']} |"
        )

    return "\n".join(lines) + "\n"


def sync_feature_phase_doc(
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
    doc_path: str | Path | None = None,
    candidate_audit_path: str | Path | None = None,
) -> Path:
    resolved_doc_path = Path(doc_path) if doc_path is not None else FEATURE_PHASE_DOC_PATH
    rendered = render_feature_phase_doc(
        output_root=output_root,
        summary_path=summary_path,
        candidate_audit_path=candidate_audit_path,
    )
    resolved_doc_path.write_text(rendered, encoding="utf-8")
    return resolved_doc_path


def _validate_baseline_seeds(seeds: list[int] | None) -> tuple[int, ...]:
    if seeds is None:
        return (SCREENING_SEED,)
    invalid = [seed for seed in seeds if seed not in BASELINE_SEEDS]
    if invalid:
        raise ValueError(f"Unsupported baseline seeds: {invalid}. Expected a subset of {BASELINE_SEEDS}.")
    return tuple(seeds)


def _validate_stage1_seeds(feature_names: list[str] | None, seeds: list[int] | None) -> tuple[int, ...]:
    if seeds is None:
        return (SCREENING_SEED,)

    requested_seeds = tuple(seeds)
    if requested_seeds == (SCREENING_SEED,):
        return requested_seeds

    if feature_names is None:
        raise ValueError("Stage 1 seeds 7 and 13 require an explicit --feature selection.")
    if len(_selected_families(feature_names)) != 1:
        raise ValueError("Stage 1 seeds 7 and 13 require exactly one --feature selection.")
    if requested_seeds != BASELINE_SEEDS:
        raise ValueError(f"Stage 1 multi-seed confirmation expects exactly seeds {BASELINE_SEEDS}.")
    return requested_seeds


def _selected_families(feature_names: list[str] | None) -> list[FeatureFamily]:
    if not feature_names:
        return list(FEATURE_FAMILIES)
    requested = set(feature_names)
    unknown = requested.difference(FEATURE_FAMILY_LOOKUP)
    if unknown:
        raise ValueError(f"Unknown feature families requested: {sorted(unknown)}")
    ordered_families: list[FeatureFamily] = []
    seen: set[str] = set()
    for feature_name in feature_names:
        if feature_name in seen:
            continue
        ordered_families.append(FEATURE_FAMILY_LOOKUP[feature_name])
        seen.add(feature_name)
    return ordered_families


def _selected_variants(family: FeatureFamily, variant_ids: list[str] | None) -> tuple[str, ...]:
    if variant_ids is None:
        return family.stage2_variant_ids
    invalid = [variant_id for variant_id in variant_ids if variant_id not in family.stage2_variant_ids]
    if invalid:
        raise ValueError(
            f"Variants {invalid} are not registered for feature {family.feature_name}. "
            f"Expected a subset of {family.stage2_variant_ids}."
        )
    return tuple(variant_ids)


def run_stage0(
    seeds: list[int] | None = None,
    dry_run: bool = False,
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
    doc_path: str | Path | None = None,
    candidate_audit_path: str | Path | None = None,
    force_rerun: bool = False,
    force_rebuild_panels: bool = False,
) -> list[str]:
    selected_seeds = _validate_baseline_seeds(seeds)
    runs = [baseline_run(seed) for seed in selected_seeds]
    if dry_run:
        for feature_run in runs:
            print(feature_run.setup_id)
        return [feature_run.setup_id for feature_run in runs]

    executed: list[str] = []
    for feature_run in runs:
        execute_feature_phase_run(
            feature_run,
            output_root=output_root,
            summary_path=summary_path,
            doc_path=doc_path,
            candidate_audit_path=candidate_audit_path,
            force_rerun=force_rerun,
            force_rebuild_panels=force_rebuild_panels,
        )
        executed.append(feature_run.setup_id)
    return executed


def run_stage1(
    feature_names: list[str] | None = None,
    seeds: list[int] | None = None,
    dry_run: bool = False,
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
    doc_path: str | Path | None = None,
    candidate_audit_path: str | Path | None = None,
    force_rerun: bool = False,
    force_rebuild_panels: bool = False,
) -> list[str]:
    families = _selected_families(feature_names)
    requested_seeds = _validate_stage1_seeds(feature_names, seeds)
    baseline = baseline_run(SCREENING_SEED)
    results = load_feature_phase_results(output_root=output_root, summary_path=summary_path)
    if result_row_for_setup(results, baseline.setup_id) is None or force_rerun:
        if dry_run:
            print(baseline.setup_id)
        else:
            execute_feature_phase_run(
                baseline,
                output_root=output_root,
                summary_path=summary_path,
                doc_path=doc_path,
                candidate_audit_path=candidate_audit_path,
                force_rerun=force_rerun,
                force_rebuild_panels=force_rebuild_panels,
            )
            results = load_feature_phase_results(output_root=output_root, summary_path=summary_path)

    runs = [stage1_run(family, seed=SCREENING_SEED) for family in families]
    if dry_run:
        for feature_run in runs:
            print(feature_run.setup_id)
        if requested_seeds != (SCREENING_SEED,) and len(families) == 1 and drop_feature_is_seed42_winner(results, families[0].feature_name):
            for seed in PROMOTION_SEEDS:
                print(baseline_setup_id(seed))
                print(drop_setup_id(families[0].feature_name, seed=seed))
        return [feature_run.setup_id for feature_run in runs]

    executed: list[str] = []
    for feature_run in runs:
        execute_feature_phase_run(
            feature_run,
            output_root=output_root,
            summary_path=summary_path,
            doc_path=doc_path,
            candidate_audit_path=candidate_audit_path,
            force_rerun=force_rerun,
            force_rebuild_panels=force_rebuild_panels,
        )
        executed.append(feature_run.setup_id)
        results = load_feature_phase_results(output_root=output_root, summary_path=summary_path)

    if requested_seeds == (SCREENING_SEED,) or len(families) != 1:
        return executed

    family = families[0]
    if not drop_feature_is_seed42_winner(results, family.feature_name):
        return executed

    for seed in PROMOTION_SEEDS:
        anchor_run = baseline_run(seed)
        if result_row_for_setup(results, anchor_run.setup_id) is None or force_rerun:
            execute_feature_phase_run(
                anchor_run,
                output_root=output_root,
                summary_path=summary_path,
                doc_path=doc_path,
                candidate_audit_path=candidate_audit_path,
                force_rerun=force_rerun,
                force_rebuild_panels=force_rebuild_panels,
            )
            executed.append(anchor_run.setup_id)
            results = load_feature_phase_results(output_root=output_root, summary_path=summary_path)

        promoted_drop_run = stage1_run(family, seed=seed)
        execute_feature_phase_run(
            promoted_drop_run,
            output_root=output_root,
            summary_path=summary_path,
            doc_path=doc_path,
            candidate_audit_path=candidate_audit_path,
            force_rerun=force_rerun,
            force_rebuild_panels=force_rebuild_panels,
        )
        executed.append(promoted_drop_run.setup_id)
        results = load_feature_phase_results(output_root=output_root, summary_path=summary_path)

    write_drop_multi_seed_comparison(
        feature_name=family.feature_name,
        output_root=output_root,
        summary_path=summary_path,
    )
    return executed


def run_stage2(
    feature_names: list[str] | None = None,
    variant_ids: list[str] | None = None,
    seeds: list[int] | None = None,
    dry_run: bool = False,
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
    doc_path: str | Path | None = None,
    candidate_audit_path: str | Path | None = None,
    force_rerun: bool = False,
    force_rebuild_panels: bool = False,
) -> list[str]:
    requested_seeds = tuple(seeds) if seeds is not None else (SCREENING_SEED,)
    if SCREENING_SEED not in requested_seeds:
        raise ValueError("Stage 2 runs must include seed 42 for screening.")
    invalid_seeds = [seed for seed in requested_seeds if seed not in BASELINE_SEEDS]
    if invalid_seeds:
        raise ValueError(f"Unsupported stage-2 seeds: {invalid_seeds}. Expected a subset of {BASELINE_SEEDS}.")

    families = _selected_families(feature_names)
    if variant_ids is not None and len(families) != 1:
        raise ValueError("--variant requires exactly one --feature selection.")

    results = load_feature_phase_results(output_root=output_root, summary_path=summary_path)
    baseline = baseline_run(SCREENING_SEED)
    if result_row_for_setup(results, baseline.setup_id) is None:
        if dry_run:
            print(baseline.setup_id)
        else:
            execute_feature_phase_run(
                baseline,
                output_root=output_root,
                summary_path=summary_path,
                doc_path=doc_path,
                candidate_audit_path=candidate_audit_path,
                force_rerun=force_rerun,
                force_rebuild_panels=force_rebuild_panels,
            )
            results = load_feature_phase_results(output_root=output_root, summary_path=summary_path)

    eligible_families: list[FeatureFamily] = []
    for family in families:
        decision = stage1_decision(results, family.feature_name)
        if stage2_is_eligible(results, family):
            eligible_families.append(family)
        elif feature_names is not None:
            raise ValueError(f"Feature {family.feature_name} is not eligible for stage 2. Current stage-1 decision: {decision}.")

    executed: list[str] = []
    for family in eligible_families:
        selected_variants = _selected_variants(family, variant_ids)
        for variant_id in selected_variants:
            screening_run = stage2_run(family, variant_id, seed=SCREENING_SEED)
            if dry_run:
                print(screening_run.setup_id)
                continue

            execute_feature_phase_run(
                screening_run,
                output_root=output_root,
                summary_path=summary_path,
                doc_path=doc_path,
                candidate_audit_path=candidate_audit_path,
                force_rerun=force_rerun,
                force_rebuild_panels=force_rebuild_panels,
            )
            executed.append(screening_run.setup_id)

            results = load_feature_phase_results(output_root=output_root, summary_path=summary_path)
        if dry_run:
            continue

        selected_variant_id = selected_family_variant_id(
            results,
            family,
            variant_ids=selected_variants,
            require_complete_screen=True,
        )
        if selected_variant_id is None:
            continue

        promotion_seeds = PROMOTION_SEEDS if seeds is None else tuple(
            seed for seed in requested_seeds if seed != SCREENING_SEED
        )
        if not promotion_seeds:
            continue

        for seed in promotion_seeds:
            anchor_run = baseline_run(seed)
            if result_row_for_setup(results, anchor_run.setup_id) is None or force_rerun:
                execute_feature_phase_run(
                    anchor_run,
                    output_root=output_root,
                    summary_path=summary_path,
                    doc_path=doc_path,
                    candidate_audit_path=candidate_audit_path,
                    force_rerun=force_rerun,
                    force_rebuild_panels=force_rebuild_panels,
                )
                executed.append(anchor_run.setup_id)
                results = load_feature_phase_results(output_root=output_root, summary_path=summary_path)

            promoted_variant_run = stage2_run(family, selected_variant_id, seed=seed)
            execute_feature_phase_run(
                promoted_variant_run,
                output_root=output_root,
                summary_path=summary_path,
                doc_path=doc_path,
                candidate_audit_path=candidate_audit_path,
                force_rerun=force_rerun,
                force_rebuild_panels=force_rebuild_panels,
            )
            executed.append(promoted_variant_run.setup_id)
            results = load_feature_phase_results(output_root=output_root, summary_path=summary_path)

        write_multi_seed_comparison(
            feature_name=family.feature_name,
            variant_id=selected_variant_id,
            output_root=output_root,
            summary_path=summary_path,
        )
    return executed


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan, run, and sync the feature phase.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Print the current feature-phase execution plan.")
    plan_parser.add_argument("--output-root", default=None, help="Experiment root directory. Defaults to outputs/generated/runs/experiments.")
    plan_parser.add_argument("--summary-path", default=None, help="Optional explicit path to setup_results.csv.")

    run_parser = subparsers.add_parser("run", help="Run a feature-phase stage.")
    run_parser.add_argument("--stage", required=True, choices=["stage0", "stage1", "stage2"], help="Feature-phase stage to execute.")
    run_parser.add_argument("--feature", nargs="+", default=None, help="Optional feature family name(s) to restrict the run.")
    run_parser.add_argument("--variant", nargs="+", default=None, help="Optional variant id(s) for stage 2.")
    run_parser.add_argument("--seeds", nargs="+", type=int, default=None, help="Optional seed list.")
    run_parser.add_argument("--dry-run", action="store_true", help="Print the planned setup ids without executing them.")
    run_parser.add_argument("--force-rerun", action="store_true", help="Rerun completed setups and rebuild profile panels.")
    run_parser.add_argument("--force-rebuild-panels", action="store_true", help="Rebuild feature-profile panels before training.")
    run_parser.add_argument("--output-root", default=None, help="Experiment root directory. Defaults to outputs/generated/runs/experiments.")
    run_parser.add_argument("--summary-path", default=None, help="Optional explicit path to setup_results.csv.")
    run_parser.add_argument("--doc-path", default=None, help="Optional explicit path to docs/feature_phase.md.")
    run_parser.add_argument("--candidate-audit-path", default=None, help="Optional explicit path to standalone candidate audit CSV.")

    sync_parser = subparsers.add_parser("sync-docs", help="Rewrite docs/feature_phase.md from feature-phase results.")
    sync_parser.add_argument("--output-root", default=None, help="Experiment root directory. Defaults to outputs/generated/runs/experiments.")
    sync_parser.add_argument("--summary-path", default=None, help="Optional explicit path to setup_results.csv.")
    sync_parser.add_argument("--doc-path", default=None, help="Optional explicit path to docs/feature_phase.md.")
    sync_parser.add_argument("--candidate-audit-path", default=None, help="Optional explicit path to standalone candidate audit CSV.")
    return parser


def main(argv: list[str] | None = None) -> Any:
    parser = _build_cli_parser()
    args = parser.parse_args(argv)

    if args.command == "plan":
        return print_plan(output_root=args.output_root, summary_path=args.summary_path)

    if args.command == "sync-docs":
        path = sync_feature_phase_doc(
            output_root=args.output_root,
            summary_path=args.summary_path,
            doc_path=args.doc_path,
            candidate_audit_path=args.candidate_audit_path,
        )
        print(f"Synced {path}")
        return path

    if args.command == "run":
        common_kwargs = {
            "dry_run": args.dry_run,
            "output_root": args.output_root,
            "summary_path": args.summary_path,
            "doc_path": args.doc_path,
            "candidate_audit_path": args.candidate_audit_path,
            "force_rerun": args.force_rerun,
            "force_rebuild_panels": args.force_rebuild_panels,
        }
        if args.stage == "stage0":
            return run_stage0(seeds=args.seeds, **common_kwargs)
        if args.stage == "stage1":
            return run_stage1(feature_names=args.feature, seeds=args.seeds, **common_kwargs)
        return run_stage2(feature_names=args.feature, variant_ids=args.variant, seeds=args.seeds, **common_kwargs)

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main(sys.argv[1:])
