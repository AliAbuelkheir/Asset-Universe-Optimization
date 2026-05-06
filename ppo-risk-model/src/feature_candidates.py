"""Registry for shadow feature candidates used before PPO tuning."""

from __future__ import annotations

from dataclasses import dataclass

from src.input_feature_sets import additive_candidate_input_feature_set, register_input_feature_set


@dataclass(frozen=True)
class ShadowFeatureCandidate:
    candidate_id: str
    description: str
    candidate_type: str
    replacement_feature: str | None
    source_profile_id: str | None
    candidate_set_id: str
    input_feature_set_id: str
    feature_column: str
    is_macro: bool = False


@dataclass(frozen=True)
class ShadowCandidateShortlistEntry:
    candidate_id: str
    execution_priority: int
    primary_screen_type: str
    contingent_replacement_feature: str | None
    reason: str


REPLACEMENT_CANDIDATES: tuple[ShadowFeatureCandidate, ...] = (
    ShadowFeatureCandidate(
        candidate_id="distance_to_1m_high",
        description="Replace `distance_to_3m_high` with distance to the most recent 1-month high.",
        candidate_type="replacement",
        replacement_feature="distance_to_3m_high",
        source_profile_id="distance_to_1m_high",
        candidate_set_id="distance_to_1m_high",
        input_feature_set_id="canonical_11",
        feature_column="distance_to_3m_high",
    ),
    ShadowFeatureCandidate(
        candidate_id="price_to_sma14",
        description="Replace `price_to_sma20` with price versus SMA(14).",
        candidate_type="replacement",
        replacement_feature="price_to_sma20",
        source_profile_id="price_to_sma14",
        candidate_set_id="price_to_sma14",
        input_feature_set_id="canonical_11",
        feature_column="price_to_sma20",
    ),
    ShadowFeatureCandidate(
        candidate_id="max_drawdown_1m",
        description="Replace `max_drawdown` with a 1-month max drawdown.",
        candidate_type="replacement",
        replacement_feature="max_drawdown",
        source_profile_id="max_drawdown_1m",
        candidate_set_id="max_drawdown_1m",
        input_feature_set_id="canonical_11",
        feature_column="max_drawdown",
    ),
    ShadowFeatureCandidate(
        candidate_id="usd_vol_1m",
        description="Replace `usd_vol` with the most recent 1-month USD volatility.",
        candidate_type="replacement",
        replacement_feature="usd_vol",
        source_profile_id="usd_vol_1m",
        candidate_set_id="usd_vol_1m",
        input_feature_set_id="canonical_11",
        feature_column="usd_vol",
        is_macro=True,
    ),
    ShadowFeatureCandidate(
        candidate_id="downside_beta_to_egx30",
        description="Replace `beta_to_egx30` with downside-only beta to EGX30.",
        candidate_type="replacement",
        replacement_feature="beta_to_egx30",
        source_profile_id="downside_beta_to_egx30",
        candidate_set_id="downside_beta_to_egx30",
        input_feature_set_id="canonical_11",
        feature_column="beta_to_egx30",
    ),
    ShadowFeatureCandidate(
        candidate_id="beta_to_egx30_1m",
        description="Replace `beta_to_egx30` with the most recent 1-month beta.",
        candidate_type="replacement",
        replacement_feature="beta_to_egx30",
        source_profile_id="beta_to_egx30_1m",
        candidate_set_id="beta_to_egx30_1m",
        input_feature_set_id="canonical_11",
        feature_column="beta_to_egx30",
    ),
)


_ADDITIVE_CANDIDATE_SPECS = (
    ("distance_to_1m_low", "Add distance to the most recent 1-month low.", False),
    ("range_position_3m", "Add trailing 3-month range position.", False),
    ("drawdown_recovery_3m", "Add trailing 3-month drawdown recovery ratio.", False),
    ("realized_skew_3m", "Add trailing 3-month realized return skewness.", False),
    ("realized_kurtosis_3m", "Add trailing 3-month realized return kurtosis.", False),
    ("illiquidity_1m", "Add 1-month Amihud-style illiquidity.", False),
    ("volume_spike_1m_vs_3m", "Add a 1-month versus 3-month volume spike ratio.", False),
    ("usd_return_1m", "Add 1-month compounded USD return.", True),
    ("cpi_acceleration_3m", "Add a 3-month CPI acceleration signal.", True),
    ("sortino_3m", "Add trailing 3-month Sortino ratio with a zero hurdle.", False),
    ("sortino_1m", "Add trailing 1-month Sortino ratio with a zero hurdle.", False),
    ("calmar_3m", "Add trailing 3-month Calmar ratio.", False),
    ("calmar_1m", "Add trailing 1-month Calmar ratio.", False),
    ("expected_shortfall_95_3m", "Add trailing 3-month expected shortfall at the 95% tail.", False),
    ("drawdown_duration_3m", "Add trailing 3-month drawdown duration.", False),
    ("worst_return_1m", "Add the worst observed daily return from the most recent month.", False),
    ("max_abs_return_1m", "Add the maximum absolute observed daily return from the most recent month.", False),
    ("vol_of_vol_3m", "Add volatility-of-volatility across trailing monthly realized volatility summaries.", False),
    ("downside_tail_ratio_3m", "Add the ratio of downside tail magnitude to total absolute return magnitude over trailing 3 months.", False),
    ("worst_return_3m", "Add the worst observed daily return over the trailing 3-month window.", False),
    ("max_abs_return_3m", "Add the maximum absolute observed daily return over the trailing 3-month window.", False),
)


ADDITIVE_CANDIDATES: tuple[ShadowFeatureCandidate, ...] = tuple(
    ShadowFeatureCandidate(
        candidate_id=candidate_id,
        description=description,
        candidate_type="additive",
        replacement_feature=None,
        source_profile_id=None,
        candidate_set_id=f"shadow_add_{candidate_id}",
        input_feature_set_id=f"shadow_add_{candidate_id}",
        feature_column=candidate_id,
        is_macro=is_macro,
    )
    for candidate_id, description, is_macro in _ADDITIVE_CANDIDATE_SPECS
)


for candidate in ADDITIVE_CANDIDATES:
    register_input_feature_set(additive_candidate_input_feature_set(candidate.candidate_id))


SHADOW_FEATURE_CANDIDATES: tuple[ShadowFeatureCandidate, ...] = REPLACEMENT_CANDIDATES + ADDITIVE_CANDIDATES
SHADOW_FEATURE_CANDIDATE_LOOKUP = {candidate.candidate_id: candidate for candidate in SHADOW_FEATURE_CANDIDATES}

APPROVED_RATIO_AND_TAIL_SHORTLIST: tuple[ShadowCandidateShortlistEntry, ...] = (
    ShadowCandidateShortlistEntry(
        candidate_id="sortino_3m",
        execution_priority=1,
        primary_screen_type="additive",
        contingent_replacement_feature="downside_dev",
        reason="Directly tests a downside-adjusted return ratio over the full trailing 3-month window.",
    ),
    ShadowCandidateShortlistEntry(
        candidate_id="sortino_1m",
        execution_priority=2,
        primary_screen_type="additive",
        contingent_replacement_feature="downside_dev",
        reason="Tests whether the most recent 1-month downside-adjusted signal is sharper than the 3-month version.",
    ),
    ShadowCandidateShortlistEntry(
        candidate_id="calmar_3m",
        execution_priority=3,
        primary_screen_type="additive",
        contingent_replacement_feature="max_drawdown",
        reason="Tests a drawdown-aware ratio over the same 3-month horizon as the current risk features.",
    ),
    ShadowCandidateShortlistEntry(
        candidate_id="calmar_1m",
        execution_priority=4,
        primary_screen_type="additive",
        contingent_replacement_feature="max_drawdown",
        reason="Tests whether a shorter drawdown-aware ratio moves rankings more than the 3-month variant.",
    ),
    ShadowCandidateShortlistEntry(
        candidate_id="expected_shortfall_95_3m",
        execution_priority=5,
        primary_screen_type="additive",
        contingent_replacement_feature=None,
        reason="Adds a tail-loss feature that is more contrastive than variance-only risk summaries.",
    ),
    ShadowCandidateShortlistEntry(
        candidate_id="drawdown_duration_3m",
        execution_priority=6,
        primary_screen_type="additive",
        contingent_replacement_feature=None,
        reason="Adds underwater persistence to complement max-drawdown depth alone.",
    ),
    ShadowCandidateShortlistEntry(
        candidate_id="worst_return_1m",
        execution_priority=7,
        primary_screen_type="additive",
        contingent_replacement_feature=None,
        reason="Targets sudden one-month downside shocks like the October 2025 misses.",
    ),
    ShadowCandidateShortlistEntry(
        candidate_id="max_abs_return_1m",
        execution_priority=8,
        primary_screen_type="additive",
        contingent_replacement_feature=None,
        reason="Targets abrupt recent daily-return shocks regardless of sign.",
    ),
    ShadowCandidateShortlistEntry(
        candidate_id="vol_of_vol_3m",
        execution_priority=9,
        primary_screen_type="additive",
        contingent_replacement_feature=None,
        reason="Captures instability in monthly realized volatility over the policy lookback.",
    ),
    ShadowCandidateShortlistEntry(
        candidate_id="downside_tail_ratio_3m",
        execution_priority=10,
        primary_screen_type="additive",
        contingent_replacement_feature=None,
        reason="Measures how much of recent movement is concentrated in downside tail days.",
    ),
    ShadowCandidateShortlistEntry(
        candidate_id="worst_return_3m",
        execution_priority=11,
        primary_screen_type="additive",
        contingent_replacement_feature=None,
        reason="Captures trailing downside jumps across the full framework lookback.",
    ),
    ShadowCandidateShortlistEntry(
        candidate_id="max_abs_return_3m",
        execution_priority=12,
        primary_screen_type="additive",
        contingent_replacement_feature=None,
        reason="Captures trailing absolute jump risk across the full framework lookback.",
    ),
)
APPROVED_RATIO_AND_TAIL_SHORTLIST_BY_ID = {
    entry.candidate_id: entry for entry in APPROVED_RATIO_AND_TAIL_SHORTLIST
}


def get_shadow_candidate(candidate_id: str) -> ShadowFeatureCandidate:
    try:
        return SHADOW_FEATURE_CANDIDATE_LOOKUP[candidate_id]
    except KeyError as exc:
        raise ValueError(f"Unknown shadow candidate: {candidate_id}") from exc


def get_ratio_tail_shortlist_entry(candidate_id: str) -> ShadowCandidateShortlistEntry | None:
    return APPROVED_RATIO_AND_TAIL_SHORTLIST_BY_ID.get(candidate_id)


def ratio_tail_shortlist_candidate_ids() -> tuple[str, ...]:
    return tuple(entry.candidate_id for entry in APPROVED_RATIO_AND_TAIL_SHORTLIST)


def shadow_candidate_ids() -> tuple[str, ...]:
    return tuple(candidate.candidate_id for candidate in SHADOW_FEATURE_CANDIDATES)
