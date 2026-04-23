# AGENTS.md

## Project Summary

This repository is a bachelor thesis project for a variable-universe,
month-level RL asset risk scorer over the Egyptian market.

The active repository phase is now:

1. optimize the **framework**
2. then optimize the **feature set**
3. only after that optimize **PPO hyperparameters**

The active RL system is:

- one canonical long monthly state panel with one row per `(Date, AssetID)`
- one PPO policy that scores every active asset available in a decision month
- one month-level reward computed after the full active universe is scored
- monthly ranking quality against `realized_risk` as the primary evaluation
  target

Deferred from the active scope:

- investor-tier asset selection logic
- pairwise correlation features
- any non-RL trainer as an active repository path
- recurrent PPO
- transformer-first architectures

## Current Direction

The immediate priority is framework selection on top of the canonical monthly
state panel.

The active order of work is:

1. keep the data engineering pipeline correct and leakage-free
2. compare how monthly state rows are fed into PPO
3. lock one framework
4. then optimize features
5. only then tune PPO hyperparameters more broadly

If wording conflicts across repository markdown files, `AGENTS.md` wins.

## Repository Communication Layout

- `docs/` is the single documentation hub
- `thesis/` stays unchanged and remains the home of the thesis source and PDF
- `docs/diagrams/` stores diagram assets

## Asset Universe

Base scored asset classes:

1. `MoneyMarket` - 91-day T-bills
2. `Bonds` - 5-year government bonds
3. `EGX30` - Egyptian equities index
4. `REIT` - real estate index
5. `Gold` - 24K gold in EGP

Benchmark interpretation:

- `EGX30` is the benchmark representation for Egyptian equity-market exposure.
- `Gold` is the benchmark representation for gold exposure.

Equity expansion:

- EGX30 constituent stock CSVs live directly under `rawData/`
- stock rows begin only when real history exists
- absence of a row means the asset is unavailable for that month

Macro inputs:

- `USD` from `rawData/USD_1.csv` and `rawData/USD_2.csv`
- CPI from `rawData/CPI.csv`

## Raw Data Contract

- Source format is investing.com-style CSV for market series.
- Market CSVs are reverse chronological and use `MM/DD/YYYY`.
- Keep `Date`, `Price`, `Open`, `High`, `Low`, `Vol.`, and `Change %`.
- Parse comma-formatted numerics into floats.
- Parse `Vol.` into numeric volume using `K/M/B` suffixes.
- Parse `Change %` into numeric `ChangePctRaw`, but do not treat it as the
  authoritative return series.
- Compute authoritative returns from cleaned prices after any required yield
  conversion.
- `USD_1.csv` and `USD_2.csv` must be concatenated and deduplicated.
- CPI is monthly and requires special handling because it contains a leading
  blank row and trailing note rows.
- `rawData/` should stay canonical and deduplicated.

## Data Engineering Entry Points

Primary build script:

1. `src/data_processing/build_model_dataset.py`

Fast validation script:

2. `src/data_processing/validate_model_dataset.py`

## Canonical Outputs

Canonical cleaned daily reference:

- `data/ready/daily_market_series.csv`

Canonical model-ready monthly state panel:

- `data/ready/monthly_asset_panel.csv`

Only `data/ready/` should hold canonical generated datasets.

## Daily Market Series Contract

`data/ready/daily_market_series.csv` is the cleaned daily reference file for
market data.

Required columns:

- `Date`
- `AssetID`
- `AssetName`
- `AssetGroup`
- `QuotedValue`
- `OpenQuotedValue`
- `HighQuotedValue`
- `LowQuotedValue`
- `PriceForReturn`
- `OpenPriceForRange`
- `HighPriceForRange`
- `LowPriceForRange`
- `Volume`
- `ChangePctRaw`
- `ReturnFromPrice`
- `IsObserved`

Rules:

- `QuotedValue` stores the vendor `Price` field after numeric parsing.
- `PriceForReturn` is the value actually used for return calculation.
- For `MoneyMarket` and `Bonds`, `PriceForReturn` and the range-price fields are
  price proxies derived from quoted yields.
- `ChangePctRaw` is a QA/reference field only.
- `ReturnFromPrice` is the authoritative return series.
- EGX Sunday-Thursday calendar alignment is used.
- Forward-fill is allowed only for `QuotedValue` and `PriceForReturn`, up to 5
  trading days.
- OHLC audit fields, range-price fields, `Volume`, and `ChangePctRaw` must stay
  missing on synthetic forward-filled rows.
- Pre-listing history must not be imputed.

## Monthly State Panel Contract

`data/ready/monthly_asset_panel.csv` is the only canonical model-facing file.

One row represents one active point-in-time `(Date, AssetID)` monthly state.

Metadata columns:

- `Date`
- `AssetID`
- `AssetName`
- `AssetGroup`

Model feature columns:

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

Target columns:

- `realized_vol`
- `realized_downside_dev`
- `realized_max_drawdown`
- `realized_risk`
- `realized_rank`

Rules:

- The canonical storage shape is long, not wide.
- Asset identity must never enter the model input tensor.
- Monthly state rows use data available through the end of that same month.
- Targets in the same row are the realized targets inside that same month.
- Do not create rows for pre-listing months.
- Macro features repeat across all active assets in the same month.
- Months with fewer than 3 active assets are skipped from the final panel.

## Feature And Target Rules

- Time resolution is monthly.
- Monthly state features for month `m` use the trailing 3 full months ending at
  `m`.
- Targets for month `m` use realized daily returns inside month `m`.
- Daily returns are used for asset-level feature and target construction.
- `egarch_vol` uses strict month-level walk-forward EGARCH summaries.
- `volume` is built from observed daily `Volume` over the same trailing feature
  window and defaults to `0` when no vendor volume exists in that window.
- `atr_pct_20` is the trailing 20-observation average true range ending in
  month `m`, divided by the last observed close in month `m`.
- `beta_to_egx30` is computed over the same trailing 3-month feature window.
- `price_to_sma20`, `rsi_14`, and `distance_to_3m_high` are evaluated at the
  last observed close in month `m`.
- Bonds and money market series are quoted as yields and must be converted to a
  fixed-maturity price proxy before return and range-derived features are
  computed.
- Asset-level feature normalization is cross-sectional within month only.
- Macro features stay repeated per month and are not cross-sectionally
  normalized.
- `realized_risk` is built from within-month ranked `realized_vol`,
  `realized_downside_dev`, and `realized_max_drawdown`.

## Framework Optimization Phase

Decision month `t` is built from prior monthly state rows only.

Active framework candidates:

1. `pit_1m_shared_mlp`
- input per asset: month `t-1`
- actor context mode: `none`

2. `pit_1m_context`
- input per asset: month `t-1`
- actor context mode: pooled month context
- evaluated and rejected before the feature phase

3. `pit_1m_dailystrip_shared_cnn`
- input per asset: month `t-1` monthly row plus an observed prior-month daily
  strip
- daily strip channels: `close_rel`, `ReturnFromPrice`, `log1p(Volume)`,
  `volume_observed`
- daily strip length: `23` observed trading days max, zero-padded with a day
  mask
- actor context mode: `none`
- evaluated and rejected before the feature phase

4. `pit_1m_context_t1_dailyflat`
- input per asset: month `t-1` monthly row plus the observed prior-month daily
  price path from `t-1`
- daily strip channels: `close_rel`, `ReturnFromPrice`, `log1p(Volume)`,
  `volume_observed`
- daily fusion mode: direct flat concatenation of the zero-padded `(23, 4)`
  strip plus the day mask into the shared scorer MLP
- actor context mode: pooled month context
- evaluated and rejected before the feature phase

5. `pit_1m_t1_dailyflat`
- input per asset: month `t-1` monthly row plus the observed prior-month daily
  price path from `t-1`
- daily strip channels: `close_rel`, `ReturnFromPrice`, `log1p(Volume)`,
  `volume_observed`
- daily fusion mode: direct flat concatenation of the zero-padded `(23, 4)`
  strip plus the day mask into the shared scorer MLP
- actor context mode: `none`
- screened and rejected before the feature phase

6. `pit_3m_flat_shared_mlp`
- input per asset: months `t-3`, `t-2`, `t-1` concatenated
- actor context mode: `none`

7. `pit_3m_flat_context`
- input per asset: months `t-3`, `t-2`, `t-1` concatenated
- actor context mode: pooled month context

8. `pit_3m_flat_context_t1_dailyflat`
- input per asset: months `t-3`, `t-2`, `t-1` concatenated plus the observed
  prior-month daily price path from `t-1`
- daily strip channels: `close_rel`, `ReturnFromPrice`, `log1p(Volume)`,
  `volume_observed`
- daily fusion mode: direct flat concatenation of the zero-padded `(23, 4)`
  strip plus the day mask into the shared scorer MLP
- actor context mode: pooled month context
- evaluated and rejected before the feature phase

9. `pit_3m_flat_t1_dailyflat`
- input per asset: months `t-3`, `t-2`, `t-1` concatenated plus the observed
  prior-month daily price path from `t-1`
- daily strip channels: `close_rel`, `ReturnFromPrice`, `log1p(Volume)`,
  `volume_observed`
- daily fusion mode: direct flat concatenation of the zero-padded `(23, 4)`
  strip plus the day mask into the shared scorer MLP
- actor context mode: `none`
- screened and rejected before the feature phase

Conditional stretch candidate:

10. `pit_3m_flat_attention`
- do not activate unless a context model clearly beats the base

Comparison rules:

- require a full lookback for every active asset
- compare frameworks on the same decision months
- common train decision start is `2011-01`
- use validation only to select the winning framework
- daily-input candidates may read `data/ready/daily_market_series.csv`, but
  only from observed rows in state month `t-1`; synthetic forward-filled rows
  must not enter the policy input

Locked PPO config for this phase:

- `learning_rate = 1e-4`
- `n_steps = 256`
- `batch_size = 256`
- `n_epochs = 10`
- `gamma = 1.0`
- `gae_lambda = 1.0`
- `clip_range = 0.2`
- `ent_coef = 0.01`
- `vf_coef = 0.5`
- `max_grad_norm = 0.5`
- `eval_frequency = 512`

## Month-Level RL Contract

One PPO episode equals one decision month.

At decision month `t`:

1. choose the configured prior state rows needed by the framework
2. build one policy tensor from feature columns only
3. apply one shared scorer across the active asset rows
4. output one risk score per available asset
5. sort predictions from low to high predicted risk
6. compare against decision month `t` realized targets
7. compute one reward for the whole month

Reward:

`0.7 * SpearmanRankCorr(predicted, realized) + 0.3 * (1 - MSE)`

Rules:

- training samples random decision months from the train split
- validation and test evaluate decision months in chronological order
- compute reward only across active assets in that month
- padded rows must not contribute to log-probability, entropy, PPO loss, or
  reward

## Data Splits

Daily history warm-up:

- starts at `2010-08`

Monthly state panel:

- starts at `2010-10`

Decision splits:

- Training: `2011-01` to `2022-12`
- Validation: `2023-01` to `2025-02`
- Test: `2025-03` to `2026-01`

Do not introduce temporal leakage across these ranges.

## Testing And Leakage Policy

Testing is used to make sure:

1. the data engineering part is correct and calculations are performed
   correctly
2. no data leakage whatsoever is happening in the calculations

Repository rules:

- `validate_model_dataset.py` is the fast schema and contract check
- `tests/test_data_engineering_pipeline.py` is the stronger correctness and
  leakage suite for parsing, feature construction, target construction, and
  monthly state timing
- `tests/test_training_pipeline.py` protects the PPO path, framework batch
  assembly, masking behavior, split integrity, checkpoint selection, and
  artifact writing

## Source Of Truth

- `AGENTS.md` is the canonical repository specification
- `README.md` is the short overview
- `docs/README.md` is the documentation hub
- `docs/framework_phase.md` is the framework-phase methodology, tested-set,
  and conclusion document
- `docs/feature_phase.md` is the feature-phase methodology, matrix, and
  decision document
- `docs/ppo_tuning_phase.md` is the PPO tuning methodology and sweep tracker
- `docs/project_guide.md` is the compact technical guide for the data
  contract, PPO setup, and leakage rules
- `docs/papers.md` is the paper tracker
- `src/config.py` holds implementation constants but is not more authoritative
  than `AGENTS.md`

## Working Guidance

- Prefer the documented point-in-time monthly-state design over the old baked
  decision-month panel.
- Keep generated canonical datasets under `data/ready/` only.
- Do not reintroduce non-RL trainer paths.
- Do not reintroduce direct asset identity into the policy input.
- Do not weaken the leakage test expectations for convenience.
- Keep the active docs compact and update the relevant phase document whenever
  a real run is completed.
