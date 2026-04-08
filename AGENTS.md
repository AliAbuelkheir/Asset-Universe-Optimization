# AGENTS.md

## Project Summary

This repository is a bachelor thesis project for a variable-universe,
monthly-batched RL asset risk scorer over the Egyptian market.

The active system is:

- one shared PPO scorer applied to every asset available in a month
- one canonical long monthly panel with one row per `(Date, AssetID)`
- one month-level reward computed after scoring the full active universe
- monthly ranking quality against `realized_risk` as the primary evaluation
  target

Deferred from the active scope:

- investor-tier asset selection logic
- pairwise correlation features
- any non-RL trainer as an active repository path

## Current Direction

The immediate priority is a fully working RL path on top of the canonical
monthly panel.

The canonical pipeline direction is now:

1. clean and standardize the raw market files
2. derive authoritative returns from cleaned prices
3. build the final monthly asset panel directly
4. train and evaluate the PPO agent from that one panel

If wording conflicts across repository markdown files, `AGENTS.md` wins.

## Repository Communication Layout

- `docs/` is the single documentation hub for implementation plans,
  architecture notes, and team-facing reference material
- `thesis/` stays unchanged and remains the home of the thesis source and
  rendered PDF
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
- `rawData/` should stay canonical and deduplicated. Do not reintroduce
  duplicate stock folders, zip archives, or repeated exported variants.

## Data Engineering Entry Points

Primary build script:

1. `src/data_processing/build_model_dataset.py`

Fast validation script:

2. `src/data_processing/validate_model_dataset.py`

The earlier `clean.py`, `returns.py`, `features.py`, and `targets.py` split is
no longer the active pipeline contract.

## Canonical Outputs

Canonical cleaned daily reference:

- `data/ready/daily_market_series.csv`

Canonical model-ready monthly panel:

- `data/ready/monthly_asset_panel.csv`

No additional intermediate CSV family should be treated as the repository
contract by default.

Only `data/ready/` should hold canonical generated datasets. Do not keep
duplicate copies of those outputs elsewhere under `data/`.

## Daily Market Series Contract

`data/ready/daily_market_series.csv` is the cleaned reference file for daily
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
- `OpenQuotedValue`, `HighQuotedValue`, and `LowQuotedValue` store parsed vendor
  OHLC fields for QA and reproducibility.
- `PriceForReturn` is the value actually used for return calculation.
- `OpenPriceForRange`, `HighPriceForRange`, and `LowPriceForRange` are kept in
  the same price space as `PriceForReturn`.
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
- `Volume` is preserved and used to derive the monthly `volume` model feature.

## Monthly Panel Contract

`data/ready/monthly_asset_panel.csv` is the only canonical model-facing file.

One row represents one active `(Date, AssetID)` month.

Metadata columns kept for grouping and alignment:

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
- The runtime batch for month `t` is built by filtering rows where `Date == t`
  and then dropping metadata and target columns.
- Do not create rows for pre-listing months.
- Months with fewer than 3 active assets are skipped.
- Macro features repeat across all active assets in the same month.

## Feature And Target Rules

- Time resolution is monthly.
- Features for month `t` use the trailing 3 full months ending at `t-1`.
- Targets for month `t` use realized daily returns inside month `t`.
- Daily returns are used for asset-level feature and target construction.
- `egarch_vol` uses strict month-level walk-forward EGARCH summaries. For any
  month `m`, the EGARCH fit may only use data available through the end of
  month `m`.
- `volume` is built from observed daily `Volume` over the same trailing feature
  window defined by `WINDOW_MONTHS` and defaults to `0` when no vendor volume
  exists in that window.
- `atr_pct_20` is the trailing 20-observation average true range ending in
  month `t-1`, divided by the last observed close in `t-1`.
- `beta_to_egx30` is the covariance of aligned asset returns with aligned EGX30
  returns over the trailing 3 full months ending at `t-1`, divided by EGX30
  return variance over the same window.
- `price_to_sma20` is the last observed close in `t-1` divided by the trailing
  20 observed closes ending in `t-1`, minus 1.
- `rsi_14` is the 14-period Wilder RSI evaluated at the last observed close in
  `t-1`.
- `distance_to_3m_high` is the last observed close in `t-1` divided by the max
  observed `HighPriceForRange` over the trailing 3 full months ending at `t-1`,
  minus 1.
- Bonds and money market series are quoted as yields and must be converted to a
  fixed-maturity price proxy before returns and range-derived features are
  computed.
- Asset-level feature normalization is cross-sectional within month only.
- Macro features stay repeated per month and are not cross-sectionally
  normalized.
- `realized_vol` is plain annualized volatility computed directly from month `t`
  daily returns.
- `realized_risk` is built from within-month ranked `realized_vol`,
  `realized_downside_dev`, and `realized_max_drawdown`.
- Pairwise cross-asset correlation features are removed from the active plan.

## Month-Level RL Contract

One PPO episode equals one month.

At episode `t`:

1. load all rows for month `t` from `monthly_asset_panel.csv`
2. build the policy tensor from feature columns only
3. apply one shared scorer across the active asset rows
4. output one risk score per available asset
5. sort predictions from low to high predicted risk
6. compare against month `t` realized targets
7. compute one reward for the whole month

Reward:

`0.7 * SpearmanRankCorr(predicted, realized) + 0.3 * (1 - MSE)`

Rules:

- training samples random months from the train split
- validation and test evaluate months in chronological order
- compute reward only across active assets in that month
- skip months with fewer than 3 assets
- keep identifiers only for grouping and alignment
- padded rows must not contribute to log-probability, entropy, or reward

## Data Splits

- Warm-up: Aug 2010 to Oct 2010
- Training: Nov 2010 to Dec 2022
- Validation: Jan 2023 to Feb 2025
- Test: Mar 2025 to Feb 2026

Do not introduce temporal leakage across these ranges.

## Testing And Leakage Policy

Testing is used to make sure:

1. the data engineering part is correct and calculations are performed
   correctly
2. no data leakage whatsoever is happening in the calculations

Repository rules:

- `validate_model_dataset.py` is the fast schema and contract check for the
  canonical outputs
- `tests/test_data_engineering_pipeline.py` is the stronger correctness and
  leakage suite for parsing, feature construction, target construction, and
  month-level walk-forward logic
- `tests/test_training_pipeline.py` protects the PPO path, masking behavior,
  split integrity, checkpoint selection, and evaluation artifacts

## Source Of Truth

- `AGENTS.md` is the canonical repository specification
- `README.md` is the short overview
- `docs/README.md` is the documentation hub
- `docs/project_guide.md` expands the internal data pipeline design, PPO
  contract, month-level reward logic, and leakage rules
- `docs/experiment_tracker.md` is the main sheet for recorded runs and pending
  experiments
- `docs/papers.md` is the paper tracker
- `src/config.py` holds implementation constants but is not more authoritative
  than `AGENTS.md`

## Working Guidance

- Prefer the documented variable-universe monthly-panel design over any earlier
  fixed-universe assumption.
- Keep outputs chronological.
- Keep `rawData/` canonical and deduplicated.
- Keep generated canonical datasets under `data/ready/` only.
- Do not reintroduce non-RL trainer paths as active repo paths.
- Do not reintroduce direct asset identity into the policy input.
- Do not weaken the leakage test expectations for convenience.
