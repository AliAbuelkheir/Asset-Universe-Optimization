# Feature Phase

## Purpose

This is the active feature-phase planning and tracking document.

Use it to track:

- the locked backbone for feature work
- the feature-comparison methodology
- the experiment matrix for feature ablations and redesigns
- final keep, drop, and alter decisions

## Locked Baseline

Active backbone:

- `pit_3m_flat_context`

Active feature profile:

- `full_current_v1`

Locked feature set:

- `egarch_vol`
- `downside_dev`
- `max_drawdown`
- `volume`
- `atr_pct_20`
- `beta_to_egx30`
- `price_to_sma20`
- `rsi_14`
- `distance_to_3m_high`
- `usd_vol`
- `cpi_trajectory`

Locked comparison rules:

- monthly-only framework stays fixed at `pit_3m_flat_context`
- daily-input variants are out of scope
- validation reward is the primary metric
- validation Spearman is the secondary metric
- seed `42` is the screening seed
- seeds `7` and `13` are used only after a feature edit beats the full
  feature baseline on both validation reward and validation Spearman

## Methodology

Stage order:

1. establish the baseline anchor
2. run leave-one-out value tests on seed `42`
3. open redesign variants only for weak or ambiguous features
4. expand only confirmed winners to seeds `7` and `13`

Metadata that must be written for feature-phase runs:

- `StudyPhase = feature_comparison`
- `BaseFrameworkID = pit_3m_flat_context`
- `FeatureProfileID`
- `ChangeType`
- `ChangedFeature`
- `VariantID`

Naming rules:

- baseline anchor: `FT-BASE-3M-CONTEXT-S<SEED>`
- leave-one-out ablation: `FT-ABL-DROP-<FEATURE>-S42`
- feature variant screen: `FT-VAR-<FEATURE>-<VARIANT>-S42`

Decision rules:

- if dropping a feature lowers both validation reward and validation Spearman,
  label it `provisionally valuable`
- if dropping a feature is mixed or improves either validation metric, label it
  `candidate for redesign`
- a Stage 1 removal-confirmation lane may expand a drop run to seeds `7` and `13`
  only after the seed-42 drop beats the baseline on both validation metrics
- only a stage-2 feature variant that beats the full-feature baseline on both
  validation reward and validation Spearman may expand to seeds `7` and `13`
- do not combine multiple winning feature edits in the same wave

### Approved Exploratory Redesign Shortlist

| Feature | Reason | Allowed Variants | Execution Priority |
| --- | --- | --- | --- |
| `distance_to_3m_high` | Seed-42 redesign screen complete; `distance_to_1m_high` is the selected family winner. | `distance_to_1m_high`, `distance_to_2m_high` | 1 |
| `price_to_sma20` | Seed-42 redesign screen complete; `price_to_sma14` is the selected family winner. | `price_to_sma14`, `price_to_sma21`, `price_to_ema20` | 2 |
| `max_drawdown` | Seed-42 redesign screen complete; `max_drawdown_1m` is the selected family winner. | `max_drawdown_1m`, `max_drawdown_2m` | 3 |
| `usd_vol` | Seed-42 redesign screen complete; `usd_vol_1m` is the selected family winner. | `usd_vol_1m`, `usd_return_trajectory_3m` | 4 |

### Stage 1 Multi-Seed Removal Confirmation

| Feature | Seed-42 Gate | Promoted Seeds | Result | Canonical Outcome |
| --- | --- | --- | --- | --- |
| `distance_to_3m_high` | passed | 7, 13 | removal rejected | Keep `full_current_v1` as the live baseline; no replacement testing opens in this wave. |

## Experiment Matrix

### Stage 0: Baseline Anchors

| SetupPattern | Backbone | FeatureProfileID | Status | Notes |
| --- | --- | --- | --- | --- |
| `FT-BASE-3M-CONTEXT-S42` | `pit_3m_flat_context` | `full_current_v1` | completed | Seed-42 anchor |
| `FT-BASE-3M-CONTEXT-S7` | `pit_3m_flat_context` | `full_current_v1` | completed | Seed-7 anchor |
| `FT-BASE-3M-CONTEXT-S13` | `pit_3m_flat_context` | `full_current_v1` | completed | Seed-13 anchor |

### Stage 1 And Stage 2 Matrix

| Feature | Current Definition | Stage 1 Test | Stage 2 Allowed Variants | Status |
| --- | --- | --- | --- | --- |
| `egarch_vol` | walk-forward EGARCH aggregated across trailing `3M` | drop `egarch_vol` | `egarch_last_3m`, `realized_vol_3m_proxy` | provisionally valuable |
| `downside_dev` | trailing `3M` downside deviation | drop `downside_dev` | `downside_dev_1m`, `downside_dev_ewm_3m` | provisionally valuable |
| `max_drawdown` | trailing `3M` max drawdown | drop `max_drawdown` | `max_drawdown_1m`, `max_drawdown_2m` | winner promoted |
| `volume` | trailing `3M` summed raw volume | drop `volume` | `volume_1m_sum`, `volume_3m_mean_log` | provisionally valuable |
| `atr_pct_20` | `ATR(20) / last_close` | drop `atr_pct_20` | `atr_pct_14`, `atr_pct_21` | provisionally valuable |
| `beta_to_egx30` | trailing `3M` beta to `EGX30` | drop `beta_to_egx30` | `beta_to_egx30_1m`, `downside_beta_to_egx30` | provisionally valuable |
| `price_to_sma20` | last close versus `SMA(20)` | drop `price_to_sma20` | `price_to_sma14`, `price_to_sma21`, `price_to_ema20` | winner promoted |
| `rsi_14` | Wilder `RSI(14)` | drop `rsi_14` | `rsi_7`, `rsi_21` | provisionally valuable |
| `distance_to_3m_high` | last close versus trailing `3M` high | drop `distance_to_3m_high` | `distance_to_1m_high`, `distance_to_2m_high` | removal rejected |
| `usd_vol` | trailing `3M` USD realized volatility | drop `usd_vol` | `usd_vol_1m`, `usd_return_trajectory_3m` | winner promoted |
| `cpi_trajectory` | compounded CPI trajectory over trailing `3M` | drop `cpi_trajectory` | `cpi_last_mom`, `cpi_trajectory_2m` | provisionally valuable |

## Decision Log

| Date | Feature | Stage | SetupID | Validation Reward | Validation Spearman | Decision | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-20 | baseline | stage0 | `FT-BASE-3M-CONTEXT-S42` | 0.6845 | 0.5761 | baseline anchor completed | Seed-42 anchor. |
| 2026-04-20 | egarch_vol | stage1 | `FT-ABL-DROP-EGARCH_VOL-S42` | 0.6738 | 0.5609 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | downside_dev | stage1 | `FT-ABL-DROP-DOWNSIDE_DEV-S42` | 0.6821 | 0.5730 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | max_drawdown | stage1 | `FT-ABL-DROP-MAX_DRAWDOWN-S42` | 0.6836 | 0.5747 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | volume | stage1 | `FT-ABL-DROP-VOLUME-S42` | 0.6786 | 0.5676 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | atr_pct_20 | stage1 | `FT-ABL-DROP-ATR_PCT_20-S42` | 0.6624 | 0.5449 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | beta_to_egx30 | stage1 | `FT-ABL-DROP-BETA_TO_EGX30-S42` | 0.6791 | 0.5685 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | price_to_sma20 | stage1 | `FT-ABL-DROP-PRICE_TO_SMA20-S42` | 0.6841 | 0.5754 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | rsi_14 | stage1 | `FT-ABL-DROP-RSI_14-S42` | 0.6760 | 0.5641 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | distance_to_3m_high | stage1 | `FT-ABL-DROP-DISTANCE_TO_3M_HIGH-S42` | 0.6877 | 0.5805 | removal rejected | Removal beat `FT-BASE-3M-CONTEXT-S42` at seed 42 but failed promoted-seed confirmation; live baseline stays `full_current_v1`. |
| 2026-04-20 | usd_vol | stage1 | `FT-ABL-DROP-USD_VOL-S42` | 0.6833 | 0.5741 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | cpi_trajectory | stage1 | `FT-ABL-DROP-CPI_TRAJECTORY-S42` | 0.6822 | 0.5727 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-21 | distance_to_3m_high | stage2 | `FT-VAR-DISTANCE_TO_3M_HIGH-DISTANCE_TO_1M_HIGH-S42` | 0.6870 | 0.5797 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | distance_to_3m_high | stage2 | `FT-VAR-DISTANCE_TO_3M_HIGH-DISTANCE_TO_2M_HIGH-S42` | 0.6835 | 0.5747 | redesign screened | Did not beat `FT-BASE-3M-CONTEXT-S42` on both validation metrics. |
| 2026-04-21 | price_to_sma20 | stage2 | `FT-VAR-PRICE_TO_SMA20-PRICE_TO_SMA14-S42` | 0.6847 | 0.5763 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | price_to_sma20 | stage2 | `FT-VAR-PRICE_TO_SMA20-PRICE_TO_SMA21-S42` | 0.6838 | 0.5751 | redesign screened | Did not beat `FT-BASE-3M-CONTEXT-S42` on both validation metrics. |
| 2026-04-21 | price_to_sma20 | stage2 | `FT-VAR-PRICE_TO_SMA20-PRICE_TO_EMA20-S42` | 0.6818 | 0.5723 | redesign screened | Did not beat `FT-BASE-3M-CONTEXT-S42` on both validation metrics. |
| 2026-04-21 | max_drawdown | stage2 | `FT-VAR-MAX_DRAWDOWN-MAX_DRAWDOWN_1M-S42` | 0.6865 | 0.5788 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | max_drawdown | stage2 | `FT-VAR-MAX_DRAWDOWN-MAX_DRAWDOWN_2M-S42` | 0.6831 | 0.5742 | redesign screened | Did not beat `FT-BASE-3M-CONTEXT-S42` on both validation metrics. |
| 2026-04-21 | usd_vol | stage2 | `FT-VAR-USD_VOL-USD_VOL_1M-S42` | 0.6851 | 0.5770 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | usd_vol | stage2 | `FT-VAR-USD_VOL-USD_RETURN_TRAJECTORY_3M-S42` | 0.6840 | 0.5753 | redesign screened | Did not beat `FT-BASE-3M-CONTEXT-S42` on both validation metrics. |
| 2026-04-21 | baseline | stage0 | `FT-BASE-3M-CONTEXT-S7` | 0.6730 | 0.5596 | baseline anchor completed | Seed-7 anchor. |
| 2026-04-21 | distance_to_3m_high | stage2 | `FT-VAR-DISTANCE_TO_3M_HIGH-DISTANCE_TO_1M_HIGH-S7` | 0.6710 | 0.5567 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | baseline | stage0 | `FT-BASE-3M-CONTEXT-S13` | 0.6882 | 0.5808 | baseline anchor completed | Seed-13 anchor. |
| 2026-04-21 | distance_to_3m_high | stage2 | `FT-VAR-DISTANCE_TO_3M_HIGH-DISTANCE_TO_1M_HIGH-S13` | 0.6890 | 0.5819 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | price_to_sma20 | stage2 | `FT-VAR-PRICE_TO_SMA20-PRICE_TO_SMA14-S7` | 0.6732 | 0.5598 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | price_to_sma20 | stage2 | `FT-VAR-PRICE_TO_SMA20-PRICE_TO_SMA14-S13` | 0.6872 | 0.5795 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | max_drawdown | stage2 | `FT-VAR-MAX_DRAWDOWN-MAX_DRAWDOWN_1M-S7` | 0.6728 | 0.5593 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | max_drawdown | stage2 | `FT-VAR-MAX_DRAWDOWN-MAX_DRAWDOWN_1M-S13` | 0.6859 | 0.5775 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | usd_vol | stage2 | `FT-VAR-USD_VOL-USD_VOL_1M-S7` | 0.6709 | 0.5567 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | usd_vol | stage2 | `FT-VAR-USD_VOL-USD_VOL_1M-S13` | 0.6870 | 0.5791 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-22 | baseline | shadow_baseline | `FT-SHADOW-BASE-CANONICAL-S42` | 0.6875 | 0.5803 | shadow baseline completed | Seed-42 canonical shadow baseline anchor. |
| 2026-04-22 | max_drawdown | shadow_screen | `FT-SHADOW-REP-MAX_DRAWDOWN_1M-S42` | 0.6837 | 0.5754 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated replacement screen. |
| 2026-04-22 | beta_to_egx30 | shadow_screen | `FT-SHADOW-REP-BETA_TO_EGX30_1M-S42` | 0.6838 | 0.5752 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated replacement screen. |
| 2026-04-22 | beta_to_egx30 | shadow_screen | `FT-SHADOW-REP-DOWNSIDE_BETA_TO_EGX30-S42` | 0.6851 | 0.5771 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated replacement screen. |
| 2026-04-22 | distance_to_1m_low | shadow_screen | `FT-SHADOW-ADD-DISTANCE_TO_1M_LOW-S42` | 0.6798 | 0.5692 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. |
| 2026-04-22 | illiquidity_1m | shadow_screen | `FT-SHADOW-ADD-ILLIQUIDITY_1M-S42` | 0.6640 | 0.5469 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. |
| 2026-04-22 | realized_skew_3m | shadow_screen | `FT-SHADOW-ADD-REALIZED_SKEW_3M-S42` | 0.6719 | 0.5581 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. |
| 2026-04-22 | sortino_3m | shadow_screen | `FT-SHADOW-ADD-SORTINO_3M-S42` | 0.6704 | 0.5561 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. Contingent replacement follow-up against `downside_dev` opens only after additive confirmation. |
| 2026-04-22 | sortino_1m | shadow_screen | `FT-SHADOW-ADD-SORTINO_1M-S42` | 0.6687 | 0.5536 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. Contingent replacement follow-up against `downside_dev` opens only after additive confirmation. |
| 2026-04-22 | calmar_3m | shadow_screen | `FT-SHADOW-ADD-CALMAR_3M-S42` | 0.6715 | 0.5577 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. Contingent replacement follow-up against `max_drawdown` opens only after additive confirmation. |
| 2026-04-22 | calmar_1m | shadow_screen | `FT-SHADOW-ADD-CALMAR_1M-S42` | 0.6697 | 0.5550 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. Contingent replacement follow-up against `max_drawdown` opens only after additive confirmation. |
| 2026-04-22 | expected_shortfall_95_3m | shadow_screen | `FT-SHADOW-ADD-EXPECTED_SHORTFALL_95_3M-S42` | 0.6662 | 0.5497 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. |
| 2026-04-22 | drawdown_duration_3m | shadow_screen | `FT-SHADOW-ADD-DRAWDOWN_DURATION_3M-S42` | 0.6626 | 0.5451 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. |
| 2026-04-22 | distance_to_3m_high | stage1 | `FT-ABL-DROP-DISTANCE_TO_3M_HIGH-S7` | 0.6716 | 0.5576 | removal rejected | Removal beat `FT-BASE-3M-CONTEXT-S42` at seed 42 but failed promoted-seed confirmation; live baseline stays `full_current_v1`. |
| 2026-04-22 | distance_to_3m_high | stage1 | `FT-ABL-DROP-DISTANCE_TO_3M_HIGH-S13` | 0.6896 | 0.5830 | removal rejected | Removal beat `FT-BASE-3M-CONTEXT-S42` at seed 42 but failed promoted-seed confirmation; live baseline stays `full_current_v1`. |

## Run Results

| Date | SetupID | FeatureProfileID | Seed | Validation Reward | Validation Spearman | Decision | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-20 | `FT-BASE-3M-CONTEXT-S42` | `full_current_v1` | 42 | 0.6845 | 0.5761 | baseline anchor completed | Seed-42 anchor. |
| 2026-04-20 | `FT-ABL-DROP-EGARCH_VOL-S42` | `drop_egarch_vol` | 42 | 0.6738 | 0.5609 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | `FT-ABL-DROP-DOWNSIDE_DEV-S42` | `drop_downside_dev` | 42 | 0.6821 | 0.5730 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | `FT-ABL-DROP-MAX_DRAWDOWN-S42` | `drop_max_drawdown` | 42 | 0.6836 | 0.5747 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | `FT-ABL-DROP-VOLUME-S42` | `drop_volume` | 42 | 0.6786 | 0.5676 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | `FT-ABL-DROP-ATR_PCT_20-S42` | `drop_atr_pct_20` | 42 | 0.6624 | 0.5449 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | `FT-ABL-DROP-BETA_TO_EGX30-S42` | `drop_beta_to_egx30` | 42 | 0.6791 | 0.5685 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | `FT-ABL-DROP-PRICE_TO_SMA20-S42` | `drop_price_to_sma20` | 42 | 0.6841 | 0.5754 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | `FT-ABL-DROP-RSI_14-S42` | `drop_rsi_14` | 42 | 0.6760 | 0.5641 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | `FT-ABL-DROP-DISTANCE_TO_3M_HIGH-S42` | `drop_distance_to_3m_high` | 42 | 0.6877 | 0.5805 | removal rejected | Removal beat `FT-BASE-3M-CONTEXT-S42` at seed 42 but failed promoted-seed confirmation; live baseline stays `full_current_v1`. |
| 2026-04-20 | `FT-ABL-DROP-USD_VOL-S42` | `drop_usd_vol` | 42 | 0.6833 | 0.5741 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-20 | `FT-ABL-DROP-CPI_TRAJECTORY-S42` | `drop_cpi_trajectory` | 42 | 0.6822 | 0.5727 | provisionally valuable | Compared against `FT-BASE-3M-CONTEXT-S42`. |
| 2026-04-21 | `FT-VAR-DISTANCE_TO_3M_HIGH-DISTANCE_TO_1M_HIGH-S42` | `distance_to_1m_high` | 42 | 0.6870 | 0.5797 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | `FT-VAR-DISTANCE_TO_3M_HIGH-DISTANCE_TO_2M_HIGH-S42` | `distance_to_2m_high` | 42 | 0.6835 | 0.5747 | redesign screened | Did not beat `FT-BASE-3M-CONTEXT-S42` on both validation metrics. |
| 2026-04-21 | `FT-VAR-PRICE_TO_SMA20-PRICE_TO_SMA14-S42` | `price_to_sma14` | 42 | 0.6847 | 0.5763 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | `FT-VAR-PRICE_TO_SMA20-PRICE_TO_SMA21-S42` | `price_to_sma21` | 42 | 0.6838 | 0.5751 | redesign screened | Did not beat `FT-BASE-3M-CONTEXT-S42` on both validation metrics. |
| 2026-04-21 | `FT-VAR-PRICE_TO_SMA20-PRICE_TO_EMA20-S42` | `price_to_ema20` | 42 | 0.6818 | 0.5723 | redesign screened | Did not beat `FT-BASE-3M-CONTEXT-S42` on both validation metrics. |
| 2026-04-21 | `FT-VAR-MAX_DRAWDOWN-MAX_DRAWDOWN_1M-S42` | `max_drawdown_1m` | 42 | 0.6865 | 0.5788 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | `FT-VAR-MAX_DRAWDOWN-MAX_DRAWDOWN_2M-S42` | `max_drawdown_2m` | 42 | 0.6831 | 0.5742 | redesign screened | Did not beat `FT-BASE-3M-CONTEXT-S42` on both validation metrics. |
| 2026-04-21 | `FT-VAR-USD_VOL-USD_VOL_1M-S42` | `usd_vol_1m` | 42 | 0.6851 | 0.5770 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | `FT-VAR-USD_VOL-USD_RETURN_TRAJECTORY_3M-S42` | `usd_return_trajectory_3m` | 42 | 0.6840 | 0.5753 | redesign screened | Did not beat `FT-BASE-3M-CONTEXT-S42` on both validation metrics. |
| 2026-04-21 | `FT-BASE-3M-CONTEXT-S7` | `full_current_v1` | 7 | 0.6730 | 0.5596 | baseline anchor completed | Seed-7 anchor. |
| 2026-04-21 | `FT-VAR-DISTANCE_TO_3M_HIGH-DISTANCE_TO_1M_HIGH-S7` | `distance_to_1m_high` | 7 | 0.6710 | 0.5567 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | `FT-BASE-3M-CONTEXT-S13` | `full_current_v1` | 13 | 0.6882 | 0.5808 | baseline anchor completed | Seed-13 anchor. |
| 2026-04-21 | `FT-VAR-DISTANCE_TO_3M_HIGH-DISTANCE_TO_1M_HIGH-S13` | `distance_to_1m_high` | 13 | 0.6890 | 0.5819 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | `FT-VAR-PRICE_TO_SMA20-PRICE_TO_SMA14-S7` | `price_to_sma14` | 7 | 0.6732 | 0.5598 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | `FT-VAR-PRICE_TO_SMA20-PRICE_TO_SMA14-S13` | `price_to_sma14` | 13 | 0.6872 | 0.5795 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | `FT-VAR-MAX_DRAWDOWN-MAX_DRAWDOWN_1M-S7` | `max_drawdown_1m` | 7 | 0.6728 | 0.5593 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | `FT-VAR-MAX_DRAWDOWN-MAX_DRAWDOWN_1M-S13` | `max_drawdown_1m` | 13 | 0.6859 | 0.5775 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | `FT-VAR-USD_VOL-USD_VOL_1M-S7` | `usd_vol_1m` | 7 | 0.6709 | 0.5567 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-21 | `FT-VAR-USD_VOL-USD_VOL_1M-S13` | `usd_vol_1m` | 13 | 0.6870 | 0.5791 | winner promoted | Selected family winner from seed 42; multi-seed comparison is recorded but not confirmed across all promoted seeds. |
| 2026-04-22 | `FT-SHADOW-BASE-CANONICAL-S42` | `full_current_v1` | 42 | 0.6875 | 0.5803 | shadow baseline completed | Seed-42 canonical shadow baseline anchor. |
| 2026-04-22 | `FT-SHADOW-REP-MAX_DRAWDOWN_1M-S42` | `max_drawdown_1m` | 42 | 0.6837 | 0.5754 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated replacement screen. |
| 2026-04-22 | `FT-SHADOW-REP-BETA_TO_EGX30_1M-S42` | `beta_to_egx30_1m` | 42 | 0.6838 | 0.5752 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated replacement screen. |
| 2026-04-22 | `FT-SHADOW-REP-DOWNSIDE_BETA_TO_EGX30-S42` | `downside_beta_to_egx30` | 42 | 0.6851 | 0.5771 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated replacement screen. |
| 2026-04-22 | `FT-SHADOW-ADD-DISTANCE_TO_1M_LOW-S42` | `full_current_v1` | 42 | 0.6798 | 0.5692 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. |
| 2026-04-22 | `FT-SHADOW-ADD-ILLIQUIDITY_1M-S42` | `full_current_v1` | 42 | 0.6640 | 0.5469 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. |
| 2026-04-22 | `FT-SHADOW-ADD-REALIZED_SKEW_3M-S42` | `full_current_v1` | 42 | 0.6719 | 0.5581 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. |
| 2026-04-22 | `FT-SHADOW-ADD-SORTINO_3M-S42` | `full_current_v1` | 42 | 0.6704 | 0.5561 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. Contingent replacement follow-up against `downside_dev` opens only after additive confirmation. |
| 2026-04-22 | `FT-SHADOW-ADD-SORTINO_1M-S42` | `full_current_v1` | 42 | 0.6687 | 0.5536 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. Contingent replacement follow-up against `downside_dev` opens only after additive confirmation. |
| 2026-04-22 | `FT-SHADOW-ADD-CALMAR_3M-S42` | `full_current_v1` | 42 | 0.6715 | 0.5577 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. Contingent replacement follow-up against `max_drawdown` opens only after additive confirmation. |
| 2026-04-22 | `FT-SHADOW-ADD-CALMAR_1M-S42` | `full_current_v1` | 42 | 0.6697 | 0.5550 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. Contingent replacement follow-up against `max_drawdown` opens only after additive confirmation. |
| 2026-04-22 | `FT-SHADOW-ADD-EXPECTED_SHORTFALL_95_3M-S42` | `full_current_v1` | 42 | 0.6662 | 0.5497 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. |
| 2026-04-22 | `FT-SHADOW-ADD-DRAWDOWN_DURATION_3M-S42` | `full_current_v1` | 42 | 0.6626 | 0.5451 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. |
| 2026-04-22 | `FT-ABL-DROP-DISTANCE_TO_3M_HIGH-S7` | `drop_distance_to_3m_high` | 7 | 0.6716 | 0.5576 | removal rejected | Removal beat `FT-BASE-3M-CONTEXT-S42` at seed 42 but failed promoted-seed confirmation; live baseline stays `full_current_v1`. |
| 2026-04-22 | `FT-ABL-DROP-DISTANCE_TO_3M_HIGH-S13` | `drop_distance_to_3m_high` | 13 | 0.6896 | 0.5830 | removal rejected | Removal beat `FT-BASE-3M-CONTEXT-S42` at seed 42 but failed promoted-seed confirmation; live baseline stays `full_current_v1`. |

## Current Provisional Feature Set

| Feature | Current Status | Evidence SetupIDs | Current Interpretation | Next Action |
| --- | --- | --- | --- | --- |
| `egarch_vol` | provisionally valuable | FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-EGARCH_VOL-S42 | Dropping `egarch_vol` hurt both validation metrics. | hold |
| `downside_dev` | provisionally valuable | FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-DOWNSIDE_DEV-S42 | Dropping `downside_dev` hurt both validation metrics. | hold |
| `max_drawdown` | winner promoted | FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-MAX_DRAWDOWN-S42 | A redesign variant for `max_drawdown` beat the baseline at seed 42. | hold |
| `volume` | provisionally valuable | FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-VOLUME-S42 | Dropping `volume` hurt both validation metrics. | hold |
| `atr_pct_20` | provisionally valuable | FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-ATR_PCT_20-S42 | Dropping `atr_pct_20` hurt both validation metrics. | hold |
| `beta_to_egx30` | provisionally valuable | FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-BETA_TO_EGX30-S42 | Dropping `beta_to_egx30` hurt both validation metrics. | hold |
| `price_to_sma20` | winner promoted | FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-PRICE_TO_SMA20-S42 | A redesign variant for `price_to_sma20` beat the baseline at seed 42. | hold |
| `rsi_14` | provisionally valuable | FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-RSI_14-S42 | Dropping `rsi_14` hurt both validation metrics. | hold |
| `distance_to_3m_high` | removal rejected | FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-DISTANCE_TO_3M_HIGH-S42 | Dropping `distance_to_3m_high` won at seed 42 but failed promoted-seed confirmation, so the live baseline stays unchanged. | hold |
| `usd_vol` | winner promoted | FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-USD_VOL-S42 | A redesign variant for `usd_vol` beat the baseline at seed 42. | hold |
| `cpi_trajectory` | provisionally valuable | FT-BASE-3M-CONTEXT-S42, FT-ABL-DROP-CPI_TRAJECTORY-S42 | Dropping `cpi_trajectory` hurt both validation metrics. | hold |

## Approved Ratio And Tail Shortlist

| Candidate | Primary Screen | Contingent Replacement Follow-Up | RL Screen Order | Reason |
| --- | --- | --- | --- | --- |
| `sortino_3m` | additive | replacement for `downside_dev` after additive confirmation | 1 | Directly tests a downside-adjusted return ratio over the full trailing 3-month window. |
| `sortino_1m` | additive | replacement for `downside_dev` after additive confirmation | 2 | Tests whether the most recent 1-month downside-adjusted signal is sharper than the 3-month version. |
| `calmar_3m` | additive | replacement for `max_drawdown` after additive confirmation | 3 | Tests a drawdown-aware ratio over the same 3-month horizon as the current risk features. |
| `calmar_1m` | additive | replacement for `max_drawdown` after additive confirmation | 4 | Tests whether a shorter drawdown-aware ratio moves rankings more than the 3-month variant. |
| `expected_shortfall_95_3m` | additive | none | 5 | Adds a tail-loss feature that is more contrastive than variance-only risk summaries. |
| `drawdown_duration_3m` | additive | none | 6 | Adds underwater persistence to complement max-drawdown depth alone. |

## Shadow Candidate Registry

| Candidate | Type | Replacement Family | Candidate Set ID | InputFeatureSetID | Description |
| --- | --- | --- | --- | --- | --- |
| `distance_to_1m_high` | replacement | distance_to_3m_high | `distance_to_1m_high` | `canonical_11` | Replace `distance_to_3m_high` with distance to the most recent 1-month high. |
| `price_to_sma14` | replacement | price_to_sma20 | `price_to_sma14` | `canonical_11` | Replace `price_to_sma20` with price versus SMA(14). |
| `max_drawdown_1m` | replacement | max_drawdown | `max_drawdown_1m` | `canonical_11` | Replace `max_drawdown` with a 1-month max drawdown. |
| `usd_vol_1m` | replacement | usd_vol | `usd_vol_1m` | `canonical_11` | Replace `usd_vol` with the most recent 1-month USD volatility. |
| `downside_beta_to_egx30` | replacement | beta_to_egx30 | `downside_beta_to_egx30` | `canonical_11` | Replace `beta_to_egx30` with downside-only beta to EGX30. |
| `beta_to_egx30_1m` | replacement | beta_to_egx30 | `beta_to_egx30_1m` | `canonical_11` | Replace `beta_to_egx30` with the most recent 1-month beta. |
| `distance_to_1m_low` | additive |  | `shadow_add_distance_to_1m_low` | `shadow_add_distance_to_1m_low` | Add distance to the most recent 1-month low. |
| `range_position_3m` | additive |  | `shadow_add_range_position_3m` | `shadow_add_range_position_3m` | Add trailing 3-month range position. |
| `drawdown_recovery_3m` | additive |  | `shadow_add_drawdown_recovery_3m` | `shadow_add_drawdown_recovery_3m` | Add trailing 3-month drawdown recovery ratio. |
| `realized_skew_3m` | additive |  | `shadow_add_realized_skew_3m` | `shadow_add_realized_skew_3m` | Add trailing 3-month realized return skewness. |
| `realized_kurtosis_3m` | additive |  | `shadow_add_realized_kurtosis_3m` | `shadow_add_realized_kurtosis_3m` | Add trailing 3-month realized return kurtosis. |
| `illiquidity_1m` | additive |  | `shadow_add_illiquidity_1m` | `shadow_add_illiquidity_1m` | Add 1-month Amihud-style illiquidity. |
| `volume_spike_1m_vs_3m` | additive |  | `shadow_add_volume_spike_1m_vs_3m` | `shadow_add_volume_spike_1m_vs_3m` | Add a 1-month versus 3-month volume spike ratio. |
| `usd_return_1m` | additive |  | `shadow_add_usd_return_1m` | `shadow_add_usd_return_1m` | Add 1-month compounded USD return. |
| `cpi_acceleration_3m` | additive |  | `shadow_add_cpi_acceleration_3m` | `shadow_add_cpi_acceleration_3m` | Add a 3-month CPI acceleration signal. |
| `sortino_3m` | additive |  | `shadow_add_sortino_3m` | `shadow_add_sortino_3m` | Add trailing 3-month Sortino ratio with a zero hurdle. |
| `sortino_1m` | additive |  | `shadow_add_sortino_1m` | `shadow_add_sortino_1m` | Add trailing 1-month Sortino ratio with a zero hurdle. |
| `calmar_3m` | additive |  | `shadow_add_calmar_3m` | `shadow_add_calmar_3m` | Add trailing 3-month Calmar ratio. |
| `calmar_1m` | additive |  | `shadow_add_calmar_1m` | `shadow_add_calmar_1m` | Add trailing 1-month Calmar ratio. |
| `expected_shortfall_95_3m` | additive |  | `shadow_add_expected_shortfall_95_3m` | `shadow_add_expected_shortfall_95_3m` | Add trailing 3-month expected shortfall at the 95% tail. |
| `drawdown_duration_3m` | additive |  | `shadow_add_drawdown_duration_3m` | `shadow_add_drawdown_duration_3m` | Add trailing 3-month drawdown duration. |

## Standalone Candidate Audit

| Candidate | Type | Replacement Family | Candidate Set ID | Standalone Mean Spearman | Outer Validation Months | RL Screen Eligibility | RL Screen Order |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `max_drawdown_1m` | replacement | max_drawdown | `max_drawdown_1m` | 0.8760 | 26 | below cut |  |
| `beta_to_egx30_1m` | replacement | beta_to_egx30 | `beta_to_egx30_1m` | 0.5741 | 26 | below cut |  |
| `downside_beta_to_egx30` | replacement | beta_to_egx30 | `downside_beta_to_egx30` | 0.4386 | 26 | below cut |  |
| `distance_to_1m_low` | additive |  | `shadow_add_distance_to_1m_low` | 0.3159 | 26 | below cut |  |
| `illiquidity_1m` | additive |  | `shadow_add_illiquidity_1m` | 0.1827 | 26 | below cut |  |
| `realized_skew_3m` | additive |  | `shadow_add_realized_skew_3m` | 0.1689 | 26 | below cut |  |
| `calmar_3m` | additive |  | `shadow_add_calmar_3m` | 0.1205 | 26 | approved shortlist | 3 |
| `sortino_3m` | additive |  | `shadow_add_sortino_3m` | 0.1159 | 26 | approved shortlist | 1 |
| `volume_spike_1m_vs_3m` | additive |  | `shadow_add_volume_spike_1m_vs_3m` | 0.0651 | 26 | below cut |  |
| `cpi_acceleration_3m` | additive |  | `shadow_add_cpi_acceleration_3m` | 0.0000 | 26 | below cut |  |
| `usd_return_1m` | additive |  | `shadow_add_usd_return_1m` | 0.0000 | 26 | below cut |  |
| `usd_vol_1m` | replacement | usd_vol | `usd_vol_1m` | 0.0000 | 26 | below cut |  |
| `range_position_3m` | additive |  | `shadow_add_range_position_3m` | -0.0755 | 26 | below cut |  |
| `drawdown_duration_3m` | additive |  | `shadow_add_drawdown_duration_3m` | -0.0915 | 26 | approved shortlist | 6 |
| `drawdown_recovery_3m` | additive |  | `shadow_add_drawdown_recovery_3m` | -0.1034 | 26 | below cut |  |
| `sortino_1m` | additive |  | `shadow_add_sortino_1m` | -0.1089 | 26 | approved shortlist | 2 |
| `realized_kurtosis_3m` | additive |  | `shadow_add_realized_kurtosis_3m` | -0.1091 | 26 | below cut |  |
| `calmar_1m` | additive |  | `shadow_add_calmar_1m` | -0.1176 | 26 | approved shortlist | 4 |
| `price_to_sma14` | replacement | price_to_sma20 | `price_to_sma14` | -0.1274 | 26 | below cut |  |
| `distance_to_1m_high` | replacement | distance_to_3m_high | `distance_to_1m_high` | -0.6642 | 26 | below cut |  |
| `expected_shortfall_95_3m` | additive |  | `shadow_add_expected_shortfall_95_3m` | -0.6849 | 26 | approved shortlist | 5 |

## RL Candidate Screens

| Date | Candidate | Type | SetupID | InputFeatureSetID | Validation Reward | Validation Spearman | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-22 | `max_drawdown_1m` | replacement | `FT-SHADOW-REP-MAX_DRAWDOWN_1M-S42` | `canonical_11` | 0.6837 | 0.5754 | screened candidate |
| 2026-04-22 | `beta_to_egx30_1m` | replacement | `FT-SHADOW-REP-BETA_TO_EGX30_1M-S42` | `canonical_11` | 0.6838 | 0.5752 | screened candidate |
| 2026-04-22 | `downside_beta_to_egx30` | replacement | `FT-SHADOW-REP-DOWNSIDE_BETA_TO_EGX30-S42` | `canonical_11` | 0.6851 | 0.5771 | screened candidate |
| 2026-04-22 | `distance_to_1m_low` | additive | `FT-SHADOW-ADD-DISTANCE_TO_1M_LOW-S42` | `shadow_add_distance_to_1m_low` | 0.6798 | 0.5692 | screened candidate |
| 2026-04-22 | `illiquidity_1m` | additive | `FT-SHADOW-ADD-ILLIQUIDITY_1M-S42` | `shadow_add_illiquidity_1m` | 0.6640 | 0.5469 | screened candidate |
| 2026-04-22 | `realized_skew_3m` | additive | `FT-SHADOW-ADD-REALIZED_SKEW_3M-S42` | `shadow_add_realized_skew_3m` | 0.6719 | 0.5581 | screened candidate |
| 2026-04-22 | `sortino_3m` | additive | `FT-SHADOW-ADD-SORTINO_3M-S42` | `shadow_add_sortino_3m` | 0.6704 | 0.5561 | screened candidate |
| 2026-04-22 | `sortino_1m` | additive | `FT-SHADOW-ADD-SORTINO_1M-S42` | `shadow_add_sortino_1m` | 0.6687 | 0.5536 | screened candidate |
| 2026-04-22 | `calmar_3m` | additive | `FT-SHADOW-ADD-CALMAR_3M-S42` | `shadow_add_calmar_3m` | 0.6715 | 0.5577 | screened candidate |
| 2026-04-22 | `calmar_1m` | additive | `FT-SHADOW-ADD-CALMAR_1M-S42` | `shadow_add_calmar_1m` | 0.6697 | 0.5550 | screened candidate |
| 2026-04-22 | `expected_shortfall_95_3m` | additive | `FT-SHADOW-ADD-EXPECTED_SHORTFALL_95_3M-S42` | `shadow_add_expected_shortfall_95_3m` | 0.6662 | 0.5497 | screened candidate |
| 2026-04-22 | `drawdown_duration_3m` | additive | `FT-SHADOW-ADD-DRAWDOWN_DURATION_3M-S42` | `shadow_add_drawdown_duration_3m` | 0.6626 | 0.5451 | screened candidate |

## Canonical Promotion Decisions

| Candidate | Type | Canonical Target | Decision | Notes |
| --- | --- | --- | --- | --- |
| `distance_to_1m_high` | replacement | distance_to_3m_high | planned | Await standalone audit and RL screen. |
| `price_to_sma14` | replacement | price_to_sma20 | planned | Await standalone audit and RL screen. |
| `max_drawdown_1m` | replacement | max_drawdown | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated replacement screen. |
| `usd_vol_1m` | replacement | usd_vol | planned | Await standalone audit and RL screen. |
| `downside_beta_to_egx30` | replacement | beta_to_egx30 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated replacement screen. |
| `beta_to_egx30_1m` | replacement | beta_to_egx30 | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated replacement screen. |
| `distance_to_1m_low` | additive | add `distance_to_1m_low` | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. |
| `range_position_3m` | additive | add `range_position_3m` | planned | Await standalone audit and RL screen. |
| `drawdown_recovery_3m` | additive | add `drawdown_recovery_3m` | planned | Await standalone audit and RL screen. |
| `realized_skew_3m` | additive | add `realized_skew_3m` | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. |
| `realized_kurtosis_3m` | additive | add `realized_kurtosis_3m` | planned | Await standalone audit and RL screen. |
| `illiquidity_1m` | additive | add `illiquidity_1m` | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. |
| `volume_spike_1m_vs_3m` | additive | add `volume_spike_1m_vs_3m` | planned | Await standalone audit and RL screen. |
| `usd_return_1m` | additive | add `usd_return_1m` | planned | Await standalone audit and RL screen. |
| `cpi_acceleration_3m` | additive | add `cpi_acceleration_3m` | planned | Await standalone audit and RL screen. |
| `sortino_3m` | additive | add `sortino_3m` | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. Contingent replacement follow-up against `downside_dev` opens only after additive confirmation. |
| `sortino_1m` | additive | add `sortino_1m` | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. Contingent replacement follow-up against `downside_dev` opens only after additive confirmation. |
| `calmar_3m` | additive | add `calmar_3m` | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. Contingent replacement follow-up against `max_drawdown` opens only after additive confirmation. |
| `calmar_1m` | additive | add `calmar_1m` | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. Contingent replacement follow-up against `max_drawdown` opens only after additive confirmation. |
| `expected_shortfall_95_3m` | additive | add `expected_shortfall_95_3m` | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. |
| `drawdown_duration_3m` | additive | add `drawdown_duration_3m` | screened candidate | Did not beat `FT-SHADOW-BASE-CANONICAL-S42` on both outer-validation metrics in this isolated additive screen. |
