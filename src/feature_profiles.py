"""Feature-profile registry for the feature-comparison phase."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from src import config


CANONICAL_FEATURE_COLUMNS = tuple(config.MODEL_FEATURE_COLUMNS)
FULL_CURRENT_V1_FEATURE_PROFILE_ID = "full_current_v1"


@dataclass(frozen=True)
class FeatureProfile:
    feature_profile_id: str
    description: str
    change_type: str = "baseline"
    changed_feature: str = ""
    variant_id: str = ""
    active_features: tuple[str, ...] = CANONICAL_FEATURE_COLUMNS
    neutral_fill_value: float = 0.5
    row_feature_window_months: int = config.WINDOW_MONTHS
    technical_min_periods_mode: str = "full"
    egarch_mode: str = "aggregate_mean_3m"
    downside_mode: str = "standard"
    downside_window_months: int = config.WINDOW_MONTHS
    downside_ewm_alpha: float = 0.10
    max_drawdown_window_months: int = config.WINDOW_MONTHS
    volume_mode: str = "sum"
    volume_window_months: int = config.WINDOW_MONTHS
    atr_period: int = config.ATR_PERIOD
    beta_mode: str = "standard"
    beta_window_months: int = config.WINDOW_MONTHS
    ma_mode: str = "sma"
    ma_period: int = config.SMA_PERIOD
    rsi_period: int = config.RSI_PERIOD
    distance_high_window_months: int = config.WINDOW_MONTHS
    usd_mode: str = "volatility"
    usd_window_months: int = config.WINDOW_MONTHS
    cpi_mode: str = "trajectory"
    cpi_window_months: int = config.WINDOW_MONTHS

    def parameter_values(self) -> dict[str, Any]:
        fields = asdict(self)
        fields.pop("feature_profile_id")
        fields.pop("description")
        fields["active_features"] = list(self.active_features)
        return fields


BASE_FEATURE_PROFILE = FeatureProfile(
    feature_profile_id=FULL_CURRENT_V1_FEATURE_PROFILE_ID,
    description="Current full 11-feature monthly panel.",
)


DISTANCE_REMOVED_BASELINE_PROFILE = replace(
    BASE_FEATURE_PROFILE,
    feature_profile_id="full_current_v2_no_distance_to_3m_high",
    description="Promoted live baseline that neutralizes distance_to_3m_high while preserving the canonical 11-column panel schema.",
    active_features=tuple(feature for feature in CANONICAL_FEATURE_COLUMNS if feature != "distance_to_3m_high"),
)


def _drop_profile(feature_name: str) -> FeatureProfile:
    return replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id=f"drop_{feature_name}",
        description=f"Leave-one-out ablation that neutralizes {feature_name}.",
        change_type="drop_feature",
        changed_feature=feature_name,
        variant_id=f"drop_{feature_name}",
        active_features=tuple(feature for feature in CANONICAL_FEATURE_COLUMNS if feature != feature_name),
    )


FEATURE_PROFILE_REGISTRY: dict[str, FeatureProfile] = {
    BASE_FEATURE_PROFILE.feature_profile_id: BASE_FEATURE_PROFILE,
    DISTANCE_REMOVED_BASELINE_PROFILE.feature_profile_id: DISTANCE_REMOVED_BASELINE_PROFILE,
    "drop_egarch_vol": _drop_profile("egarch_vol"),
    "drop_downside_dev": _drop_profile("downside_dev"),
    "drop_max_drawdown": _drop_profile("max_drawdown"),
    "drop_volume": _drop_profile("volume"),
    "drop_atr_pct_20": _drop_profile("atr_pct_20"),
    "drop_beta_to_egx30": _drop_profile("beta_to_egx30"),
    "drop_price_to_sma20": _drop_profile("price_to_sma20"),
    "drop_rsi_14": _drop_profile("rsi_14"),
    "drop_distance_to_3m_high": _drop_profile("distance_to_3m_high"),
    "drop_usd_vol": _drop_profile("usd_vol"),
    "drop_cpi_trajectory": _drop_profile("cpi_trajectory"),
    "egarch_last_3m": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="egarch_last_3m",
        description="Use the last walk-forward EGARCH observation in the trailing 3-month window.",
        change_type="alter_feature",
        changed_feature="egarch_vol",
        variant_id="egarch_last_3m",
        egarch_mode="last_value_3m",
    ),
    "realized_vol_3m_proxy": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="realized_vol_3m_proxy",
        description="Replace EGARCH with trailing 3-month realized volatility.",
        change_type="alter_feature",
        changed_feature="egarch_vol",
        variant_id="realized_vol_3m_proxy",
        egarch_mode="realized_vol_proxy",
    ),
    "downside_dev_1m": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="downside_dev_1m",
        description="Use downside deviation from the most recent month only.",
        change_type="alter_feature",
        changed_feature="downside_dev",
        variant_id="downside_dev_1m",
        downside_window_months=1,
    ),
    "downside_dev_ewm_3m": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="downside_dev_ewm_3m",
        description="Use exponentially weighted downside deviation over the trailing 3 months.",
        change_type="alter_feature",
        changed_feature="downside_dev",
        variant_id="downside_dev_ewm_3m",
        downside_mode="ewm",
    ),
    "max_drawdown_1m": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="max_drawdown_1m",
        description="Use max drawdown from the most recent month only.",
        change_type="alter_feature",
        changed_feature="max_drawdown",
        variant_id="max_drawdown_1m",
        max_drawdown_window_months=1,
    ),
    "max_drawdown_2m": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="max_drawdown_2m",
        description="Use max drawdown over the most recent 2 months.",
        change_type="alter_feature",
        changed_feature="max_drawdown",
        variant_id="max_drawdown_2m",
        max_drawdown_window_months=2,
    ),
    "volume_1m_sum": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="volume_1m_sum",
        description="Use summed raw volume from the most recent month only.",
        change_type="alter_feature",
        changed_feature="volume",
        variant_id="volume_1m_sum",
        volume_window_months=1,
    ),
    "volume_3m_mean_log": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="volume_3m_mean_log",
        description="Use mean log volume over the trailing 3 months.",
        change_type="alter_feature",
        changed_feature="volume",
        variant_id="volume_3m_mean_log",
        volume_mode="mean_log",
    ),
    "atr_pct_14": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="atr_pct_14",
        description="Use ATR percentage with a 14-day ATR window.",
        change_type="alter_feature",
        changed_feature="atr_pct_20",
        variant_id="atr_pct_14",
        atr_period=14,
    ),
    "atr_pct_21": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="atr_pct_21",
        description="Use ATR percentage with a 21-day ATR window.",
        change_type="alter_feature",
        changed_feature="atr_pct_20",
        variant_id="atr_pct_21",
        atr_period=21,
    ),
    "beta_to_egx30_1m": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="beta_to_egx30_1m",
        description="Use beta to EGX30 from the most recent month only.",
        change_type="alter_feature",
        changed_feature="beta_to_egx30",
        variant_id="beta_to_egx30_1m",
        beta_window_months=1,
    ),
    "downside_beta_to_egx30": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="downside_beta_to_egx30",
        description="Use beta to EGX30 on downside benchmark days only.",
        change_type="alter_feature",
        changed_feature="beta_to_egx30",
        variant_id="downside_beta_to_egx30",
        beta_mode="downside",
    ),
    "price_to_sma14": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="price_to_sma14",
        description="Use price to SMA with a 14-day SMA.",
        change_type="alter_feature",
        changed_feature="price_to_sma20",
        variant_id="price_to_sma14",
        ma_period=14,
    ),
    "price_to_sma21": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="price_to_sma21",
        description="Use price to SMA with a 21-day SMA.",
        change_type="alter_feature",
        changed_feature="price_to_sma20",
        variant_id="price_to_sma21",
        ma_period=21,
    ),
    "price_to_ema20": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="price_to_ema20",
        description="Use price to EMA with a 20-day EMA.",
        change_type="alter_feature",
        changed_feature="price_to_sma20",
        variant_id="price_to_ema20",
        ma_mode="ema",
    ),
    "rsi_7": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="rsi_7",
        description="Use Wilder RSI with a 7-day period.",
        change_type="alter_feature",
        changed_feature="rsi_14",
        variant_id="rsi_7",
        rsi_period=7,
    ),
    "rsi_21": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="rsi_21",
        description="Use Wilder RSI with a 21-day period.",
        change_type="alter_feature",
        changed_feature="rsi_14",
        variant_id="rsi_21",
        rsi_period=21,
    ),
    "distance_to_1m_high": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="distance_to_1m_high",
        description="Use distance to the most recent 1-month high.",
        change_type="alter_feature",
        changed_feature="distance_to_3m_high",
        variant_id="distance_to_1m_high",
        distance_high_window_months=1,
    ),
    "distance_to_2m_high": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="distance_to_2m_high",
        description="Use distance to the most recent 2-month high.",
        change_type="alter_feature",
        changed_feature="distance_to_3m_high",
        variant_id="distance_to_2m_high",
        distance_high_window_months=2,
    ),
    "usd_vol_1m": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="usd_vol_1m",
        description="Use USD realized volatility from the most recent month only.",
        change_type="alter_feature",
        changed_feature="usd_vol",
        variant_id="usd_vol_1m",
        usd_window_months=1,
    ),
    "usd_return_trajectory_3m": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="usd_return_trajectory_3m",
        description="Use compounded USD return trajectory over the trailing 3 months.",
        change_type="alter_feature",
        changed_feature="usd_vol",
        variant_id="usd_return_trajectory_3m",
        usd_mode="return_trajectory",
    ),
    "cpi_last_mom": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="cpi_last_mom",
        description="Use the most recent CPI month-on-month change only.",
        change_type="alter_feature",
        changed_feature="cpi_trajectory",
        variant_id="cpi_last_mom",
        cpi_mode="last_mom",
        cpi_window_months=1,
    ),
    "cpi_trajectory_2m": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="cpi_trajectory_2m",
        description="Use compounded CPI trajectory over the most recent 2 months.",
        change_type="alter_feature",
        changed_feature="cpi_trajectory",
        variant_id="cpi_trajectory_2m",
        cpi_window_months=2,
    ),
    "monthly_only_rows_v1": replace(
        BASE_FEATURE_PROFILE,
        feature_profile_id="monthly_only_rows_v1",
        description="Experiment profile where each panel row uses only that row month; the 3-month PPO framework stacks three independent monthly rows.",
        change_type="alter_row_semantics",
        changed_feature="all_row_features",
        variant_id="monthly_only_rows_v1",
        row_feature_window_months=1,
        technical_min_periods_mode="available",
        egarch_mode="realized_vol_proxy",
        downside_window_months=1,
        max_drawdown_window_months=1,
        volume_window_months=1,
        beta_window_months=1,
        distance_high_window_months=1,
        usd_window_months=1,
        cpi_mode="last_mom",
        cpi_window_months=1,
    ),
}


def get_feature_profile(feature_profile_id: str) -> FeatureProfile:
    try:
        return FEATURE_PROFILE_REGISTRY[feature_profile_id]
    except KeyError as exc:
        raise ValueError(f"Unknown feature_profile_id: {feature_profile_id}") from exc


def feature_profile_ids() -> tuple[str, ...]:
    return tuple(FEATURE_PROFILE_REGISTRY)
