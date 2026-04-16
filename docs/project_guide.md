# Project Guide

## Objective

This repository builds a variable-universe, month-level PPO agent that predicts
asset `realized_risk` scores and derives monthly risk rankings from those
scores.

The active phase is now:

1. optimize the framework
2. then optimize the feature set
3. only after that optimize PPO hyperparameters

## Canonical Data Contract

Canonical outputs:

- `data/ready/daily_market_series.csv`
- `data/ready/monthly_asset_panel.csv`

`daily_market_series.csv` is the cleaned daily reference file.

`monthly_asset_panel.csv` is the canonical point-in-time monthly state store.
One row is one active `(Date, AssetID)` month.

Current generated panel coverage:

- panel month range is currently `2010-10` to `2026-01`
- the configured test window is now `2025-03` to `2026-01`
- the current canonical panel therefore supports `11` test months:
  `2025-03` through `2026-01`
- February 2026 is intentionally excluded from the active test split

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

- Monthly state features for month `m` use the trailing 3 full months ending at
  `m`.
- Targets for month `m` use realized daily returns inside month `m`.
- `MoneyMarket` and `Bonds` are converted from quoted yields into price proxies
  before return and range calculations.
- Asset-level features are normalized cross-sectionally within month only.
- Macro features repeat within month and are not cross-sectionally normalized.
- Missing rows mean the asset is unavailable; pre-listing history must not be
  imputed.
- Month `m` rows must use data available only through the end of month `m`.
- Future asset edits, future benchmark edits, and future macro edits must not
  change earlier monthly state rows.

## Framework Optimization Phase

Decision month `t` is assembled from prior monthly state rows.

Current framework registry:

- `pit_1m_shared_mlp`: use month `t-1` only
- `pit_1m_context`: use month `t-1` plus pooled month context
- `pit_1m_dailystrip_shared_cnn`: use month `t-1` plus an observed daily strip
  from month `t-1`
- `pit_3m_flat_shared_mlp`: concatenate months `t-3`, `t-2`, `t-1`
- `pit_3m_flat_context`: same 3-month stack plus pooled month context

Conditional stretch candidate:

- `pit_3m_flat_attention`
- keep disabled unless the context model clearly beats the base

Comparison rules:

- require full lookback availability for every active asset
- compare all frameworks on the same decision months
- common train decision start is `2011-01`
- select frameworks on validation only

Daily-strip candidate details:

- the monthly branch stays the same as `pit_1m_shared_mlp`
- the extra daily branch reads only observed rows from
  `data/ready/daily_market_series.csv`
- it uses the prior state month `t-1`, not decision month `t`
- each asset gets a zero-padded `(23, 4)` strip with channels:
  `close_rel`, `ReturnFromPrice`, `log1p(Volume)`, and `volume_observed`
- synthetic forward-filled rows are excluded from the strip entirely
- the daily branch is a small shared 1D CNN, not a recurrent policy

Expected early coverage gap:

- `monthly_asset_panel.csv` has no rows for `2011-02`, `2011-03`, or `2011-04`
- this is expected from the Egyptian market disruption period plus the minimum
  active-asset rule
- under the full-lookback rule, the base `1M` framework then also loses
  decision month `2011-05`, and the `3M` frameworks lose through `2011-07`
- this should be treated as an expected data-availability boundary, not as a
  panel-construction bug

## Active PPO Implementation

Current active modules:

- `src/data_processing/build_model_dataset.py`
- `src/data_processing/validate_model_dataset.py`
- `src/environment/asset_risk_env.py`
- `src/training/frameworks.py`
- `src/training/policy.py`
- `src/training/train.py`
- `src/training/evaluate.py`

Locked PPO config for the framework phase:

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

Policy behavior:

- one shared scorer is applied across all active asset rows
- padded rows are masked out of action sampling, log-probability, entropy, and
  PPO loss
- the critic remains pooled and mask-aware

## PPO Environment And Reward

- One PPO episode equals one decision month.
- Training samples decision months at random from the train split.
- Validation and test evaluate decision months in chronological order.
- Standard monthly frameworks emit a padded observation dict with:
  `features` shape `(max_assets, input_dim)` and `mask` shape `(max_assets,)`.
- `pit_1m_dailystrip_shared_cnn` additionally emits:
  `daily_strip` shape `(max_assets, 23, 4)` and
  `daily_mask` shape `(max_assets, 23)`.
- The action is one bounded continuous risk score per padded asset slot in
  `[0, 1]`.
- Rankings are derived by sorting predicted scores from low to high.

Month-level reward:

`0.7 * SpearmanRankCorr(predicted, realized) + 0.3 * (1 - MSE)`

## Current Framework Outcome

The initial framework study has been implemented and executed.

What has been tested:

- `FW-BASE-1M-*` for `pit_1m_shared_mlp`
- `FW-1M-CONTEXT-S42` for `pit_1m_context`
- `FW-1M-DAILYSTRIP-CNN-S42` for `pit_1m_dailystrip_shared_cnn`
- `FW-STACK3M-S42` for `pit_3m_flat_shared_mlp`
- `FW-STACK3M-CONTEXT-*` for `pit_3m_flat_context`

Current selection:

- the 1-month base framework remains the winner for now
- the 1-month context ablation underperformed clearly and was rejected
- the 1-month daily-strip CNN underperformed materially and was rejected after
  the first run:
  validation reward `0.6093`, validation Spearman `0.4747`, test reward
  `0.5928`, test Spearman `0.4508`
- the 3-month context model stayed within the reward tie band but did not
  improve validation Spearman, so it was **not promoted**
- the attention stretch candidate remains disabled

See [experiment_tracker.md](/C:/Ali/CS/Bachelor%20thesis/docs/experiment_tracker.md) for the exact results.

## Validation And Testing

Validation in the ML sense:

- train = the model learns
- validation = framework selection and experiment comparison
- test = final unseen evaluation after the framework is locked

Testing in the software sense is used to make sure:

1. the data engineering part is correct and calculations are performed
   correctly
2. no data leakage whatsoever is happening in the calculations

Repository checks:

- `src/data_processing/validate_model_dataset.py` is the fast contract
  validator
- `tests/test_data_engineering_pipeline.py` is the stronger correctness and
  leakage suite
- `tests/test_training_pipeline.py` protects framework assembly, PPO
  initialization, masking, split integrity, checkpoint selection, and artifact
  writing

Return QA interpretation:

- `ChangePctRaw` is a vendor QA field only and is not the authoritative return
  series
- `ReturnFromPrice` is the authoritative series used by the pipeline
- large `ChangePctRaw` versus `ReturnFromPrice` differences are expected for
  `MoneyMarket` and `Bonds` because returns are computed from fixed-maturity
  price proxies derived from quoted yields
- the remaining notable mismatch assets are currently `HELI.CA`, `RMDA.CA`,
  `ADIB.CA`, and `Gold`; these look like source-side quote or corporate-action
  inconsistencies rather than a current parsing bug
