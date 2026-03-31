# AGENTS.md

## Project Summary

This repository is a bachelor thesis project for a variable-universe,
monthly-batched RL asset risk scorer over the Egyptian market.

The active system is:

- one shared scorer applied to every asset available in a month
- one canonical long monthly panel with one row per `(Date, AssetID)`
- one month-level reward computed after scoring the full active universe
- monthly ranking quality as the primary evaluation target

Deferred from the active scope:

- investor-tier asset selection logic
- pairwise correlation features
- test-driven development workflow

## Current Direction

The immediate priority is data engineering that makes the model ingestible as
quickly as possible.

The canonical pipeline direction is now:

1. clean and standardize the raw market files
2. derive authoritative returns from cleaned prices
3. build the final monthly asset panel directly
4. train and evaluate from that one panel

If wording conflicts across repository markdown files, `AGENTS.md` wins.

## Repository Communication Layout

- `docs/` contains internal implementation plans
- `team_docs/` contains team-facing status and architecture files
- `thesis/` stays unchanged; only the rendered PDF is copied into `team_docs/`
- `diagrams/` stays unchanged
- `external_docs/` is no longer part of the active repository structure

## Asset Universe

Base scored asset classes:

1. `MoneyMarket` - 91-day T-bills
2. `Bonds` - 5-year government bonds
3. `EGX30` - Egyptian equities index
4. `REIT` - real estate index
5. `Gold` - 24K gold in EGP

Benchmark interpretation:

- `EGX30` is the benchmark representation for Egyptian equity-market exposure,
  including ETFs and mutual funds that track or proxy the equity market.
- `Gold` is the benchmark representation for gold exposure in all practical
  forms, including gold funds and other gold-linked products.

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
- Keep `Date`, `Price`, `Vol.`, and `Change %`.
- Drop `Open`, `High`, and `Low`.
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

Optional validation script:

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

## Daily Market Series Contract

`data/ready/daily_market_series.csv` is the cleaned reference file for daily
market data.

Required columns:

- `Date`
- `AssetID`
- `AssetName`
- `AssetGroup`
- `QuotedValue`
- `PriceForReturn`
- `Volume`
- `ChangePctRaw`
- `ReturnFromPrice`
- `IsObserved`

Rules:

- `QuotedValue` stores the vendor `Price` field after numeric parsing.
- `PriceForReturn` is the value actually used for return calculation.
- For `MoneyMarket` and `Bonds`, `PriceForReturn` is a price proxy derived from
  the quoted yield.
- `ChangePctRaw` is a QA/reference field only.
- `ReturnFromPrice` is the authoritative return series.
- EGX Sunday-Thursday calendar alignment is used.
- Forward-fill is allowed only for small gaps, up to 5 trading days.
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
- `usd_vol`
- `cpi_trajectory`

Target columns:

- `realized_egarch_vol`
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
- `egarch_vol` and `realized_egarch_vol` use strict month-level walk-forward
  EGARCH summaries. For any month `m`, the EGARCH fit may only use data
  available through the end of month `m`.
- `volume` is built from observed daily `Volume` over the same trailing feature
  window defined by `WINDOW_MONTHS` and defaults to `0` when no vendor volume
  exists in that window.
- Bonds and money market series are quoted as yields and must be converted to a
  fixed-maturity price proxy before returns are computed.
- Asset-level feature normalization is cross-sectional within month only.
- Macro features stay repeated per month and are not cross-sectionally
  normalized.
- Realized risk is built from within-month ranked realized components.
- Pairwise cross-asset correlation features are removed from the active plan.

## Month-Level Batching And Reward

One environment step equals one month.

At step `t`:

1. load all rows for month `t` from `monthly_asset_panel.csv`
2. build the model tensor from feature columns only
3. apply one shared scorer across the active asset rows
4. output one risk score per available asset
5. sort predictions from low to high predicted risk
6. compare against month `t` realized targets
7. compute one reward for the whole month

Reward:

`0.7 * SpearmanRankCorr(predicted, realized) + 0.3 * (1 - MSE)`

Reward rules:

- compute reward only across active assets in that month
- skip months with fewer than 3 assets
- keep identifiers only for grouping and alignment

## Data Splits

- Warm-up: Aug 2010 to Oct 2010
- Training: Nov 2010 to Dec 2022
- Validation: Jan 2023 to Feb 2025
- Test: Mar 2025 to Feb 2026

Do not introduce temporal leakage across these ranges.

## Source Of Truth

- `AGENTS.md` is the canonical repository specification
- `README.md` is the short overview
- `docs/data_engineering_plan.md` expands the internal data pipeline design
- `docs/ml_framework_plan.md` expands the model design
- `docs/month_level_batching_and_reward.md` expands month-level scoring logic
- `team_docs/` is the team-facing communication hub
- `src/config.py` holds implementation constants but is not more authoritative
  than `AGENTS.md`

## Working Guidance

- Prefer the documented variable-universe monthly-panel design over any earlier
  fixed-universe assumption.
- Keep outputs chronological.
- Keep `rawData/` canonical and deduplicated.
- Avoid reintroducing older architecture ideas such as two-level orchestrators,
  fixed per-asset model slots, or rule-labeled supervised targets.
- Avoid reintroducing TDD/test-suite workflow language into repository docs.
