# Project Guide

## Objective

This repository builds a variable-universe, month-level PPO agent that predicts
asset `realized_risk` scores and derives monthly risk rankings from those
scores.

The active path is:

1. clean and standardize raw market files
2. derive authoritative daily returns from cleaned prices
3. build the canonical monthly asset panel
4. train and evaluate a PPO agent on month-level batches

## Canonical Data Contract

Canonical outputs:

- `data/ready/daily_market_series.csv`
- `data/ready/monthly_asset_panel.csv`

`daily_market_series.csv` is the cleaned daily reference file. It preserves:

- `Date`, `AssetID`, `AssetName`, `AssetGroup`
- parsed vendor close and OHLC fields
- `PriceForReturn` and range-price fields
- `Volume`
- `ChangePctRaw`
- `ReturnFromPrice`
- `IsObserved`

`monthly_asset_panel.csv` is the only model-facing dataset. One row is one
active `(Date, AssetID)` month.

Metadata columns:

- `Date`
- `AssetID`
- `AssetName`
- `AssetGroup`

Feature columns:

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

## Feature, Target, And Leakage Rules

- Features for month `t` use the trailing 3 full months ending at `t-1`.
- Targets for month `t` use realized daily returns inside month `t`.
- `MoneyMarket` and `Bonds` are converted from quoted yields into price proxies
  before return and range calculations.
- Asset-level features are normalized cross-sectionally within month only.
- Macro features repeat within month and are not cross-sectionally normalized.
- Missing rows mean the asset is unavailable; pre-listing history must not be
  imputed.
- Month `t` features must use data available only through the end of `t-1`.
- Future asset edits, future benchmark edits, and future macro edits must not
  change earlier panel rows.

## PPO Environment And Reward

- One PPO episode equals one month.
- Training samples one train month at random per episode.
- Validation and test evaluate months in chronological order.
- The observation is a padded dict:
  `features` with shape `(max_assets, 11)` and `mask` with shape
  `(max_assets,)`.
- The action is one bounded continuous risk score per padded asset slot in
  `[0, 1]`.
- Rankings are derived by sorting predicted scores from low to high.

Month-level reward:

`0.7 * SpearmanRankCorr(predicted, realized) + 0.3 * (1 - MSE)`

Rules:

- compute reward only across active assets in that month
- padded rows must not affect reward, log-probability, entropy, or PPO loss
- skip months with fewer than 3 assets
- `AssetID` is for alignment only and never enters the policy input

## Active PPO Implementation

Current active modules:

- `src/data_processing/build_model_dataset.py`
- `src/data_processing/validate_model_dataset.py`
- `src/environment/asset_risk_env.py`
- `src/training/policy.py`
- `src/training/train.py`
- `src/training/evaluate.py`

Current policy architecture:

- shared row encoder: `11 -> 64 -> 64` with ReLU
- actor head: `64 -> 32 -> 1`
- critic input: masked mean pool + masked max pool + normalized active count
- critic head: `129 -> 64 -> 1`
- masked diagonal Gaussian action distribution

Split ranges:

- warm-up: `2010-08` to `2010-10`
- train: `2010-11` to `2022-12`
- validation: `2023-01` to `2025-02`
- test: `2025-03` to `2026-02`

Validation mean reward is the checkpoint-selection metric. Test metrics are
reported only after the validation-selected checkpoint is fixed.

## Validation And Testing

Validation in the ML sense:

- train = the model learns
- validation = checkpoint selection and experiment comparison
- test = final unseen evaluation

Testing in the software sense is used to make sure:

1. the data engineering part is correct and calculations are performed
   correctly
2. no data leakage whatsoever is happening in the calculations

Repository checks:

- `src/data_processing/validate_model_dataset.py` is the fast contract
  validator
- `tests/test_data_engineering_pipeline.py` is the stronger correctness and
  leakage suite
- `tests/test_training_pipeline.py` protects PPO initialization, masking,
  split integrity, checkpoint selection, and artifact writing
