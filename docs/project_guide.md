# Project Guide

## Objective

This repository builds a variable-universe, month-level PPO agent that predicts
asset `realized_risk` scores and derives monthly risk rankings from those
scores.

The completed modeling order was:

1. optimize the framework
2. optimize the feature set
3. tune PPO hyperparameters
4. rerun top candidates with the tuned PPO setup

The active work is now evaluation and reporting design for the thesis.

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

## Framework Summary

Decision month `t` is assembled from prior monthly state rows.

Monthly-only framework conclusion:

- `pit_3m_flat_context` is the locked winner for feature work.
- `1M` alone beat `3M` alone.
- `3M + context` beat `1M + context`.
- pooled context hurt the `1M` backbone.
- pooled context clearly helped the `3M` backbone.

Daily-input conclusion:

- daily-strip additions did not improve the monthly-only system and are
  excluded from the feature phase.
- shared daily CNN, shared daily flat, and actor-only daily additions all
  stayed below the locked monthly-only winner and below the bounded `1M` base
  on validation ranking quality.

For the full framework methodology and tested-framework record, see
[framework_phase.md](/C:/Ali/CS/Bachelor%20thesis/docs/framework_phase.md).

## Current Best Model

Authoritative current-best record:

- model id = `drop_distance_to_3m_high_refined50`
- framework = `pit_3m_flat_context`
- feature profile = `drop_distance_to_3m_high`
- tuned PPO candidate = `refined50`
- comparison protocol = `repaired_inner12_outer26_v1`
- objective profile = `risk_v1_equal_333`
- reward profile = `reward_v1_rank70_mse30`
- training method = `ordered_cycle`
- input feature set = `canonical_11`
- checkpoint provenance = `best_inner_validation`
- artifact root = `outputs/top_candidate_reruns/refined50/`

Selection rule:

- choose the highest three-seed validation mean reward
- use validation Spearman as the tie-breaker
- use test metrics only for reporting

Three-seed metrics:

- validation reward = `0.7012`
- validation Spearman = `0.5954`
- test reward = `0.7449`
- test Spearman = `0.6565`

Important comparison note:

- `monthly_only_rows_v1` had stronger test means, but lost on validation
  selection and remains reporting-only evidence.
- Canonical defaults remain `full_current_v1`; current-best metadata is kept
  separate from canonical data/profile defaults.

## Active PPO Implementation

Current active modules:

- `src/data_processing/build_model_dataset.py`
- `src/data_processing/validate_model_dataset.py`
- `src/environment/asset_risk_env.py`
- `src/training/frameworks.py`
- `src/training/policy.py`
- `src/training/train.py`
- `src/training/evaluate.py`
- `src/feature_profiles.py`

Locked PPO config during framework and feature comparison:

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

Current tuned PPO candidate:

- id = `refined50`
- `learning_rate = 0.00024935310281972535`
- `n_steps = 256`
- `batch_size = 256`
- `n_epochs = 10`
- `gamma = 1.0`
- `gae_lambda = 1.0`
- `clip_range = 0.2990122587129351`
- `ent_coef = 0.0023477909057284673`
- `vf_coef = 0.9023537822799527`
- `max_grad_norm = 0.3`

Policy behavior:

- one shared scorer is applied across all active asset rows
- PPO uses a bounded masked sigmoid-squashed Gaussian, so sampled risk scores
  are already valid `[0, 1]` actions before the environment backstop clip
- padded rows are masked out of action sampling, log-probability, entropy, and
  PPO loss
- the critic remains pooled and mask-aware

## PPO Environment And Reward

- One PPO episode equals one decision month.
- Training cycles through train decision months in chronological order.
- Validation and test evaluate decision months in chronological order.
- Standard monthly frameworks emit a padded observation dict with:
  `features` shape `(max_assets, input_dim)` and `mask` shape `(max_assets,)`.
- Daily-input frameworks additionally emit `daily_strip` and `daily_mask`, but
  those paths are not active in the feature phase.
- The action is one bounded continuous risk score per padded asset slot in
  `[0, 1]`.
- Rankings are derived by sorting predicted scores from low to high.

Month-level reward:

`0.7 * SpearmanRankCorr(predicted, realized) + 0.3 * (1 - MSE)`

## Future Inference Contract

The future web application is not active repo scope yet, but the serving
boundary should be planned around these stages:

1. `rank_assets(month) -> ranked universe`
2. `bucket_ranked_assets(ranked_universe, risk_tolerance) -> selected universe`
3. `allocate_assets(selected_universe, optional constraints) -> weights`

Current inference output before investor bucketing is redesigned:

- active month
- active assets
- predicted risk scores
- predicted risk ranks
- realized risk fields only when evaluating historical months

Future web input:

- `month`
- `risk_tolerance`

Future web output after selection logic is reopened:

- selected asset universe for the requested tolerance and month
- ranked-risk metadata used to justify the selection
- optional allocation weights and simulated earnings from a separate external
  model or REST adapter

Training, inference, investor-facing selection, and allocation must remain
separate modules. The web app should call inference services instead of reusing
CLI-only training code.

## Feature-Phase Support

The feature phase now uses explicit feature profiles instead of manual code
edits.

- base feature profile: `full_current_v1`
- current-best feature profile after tuned reruns: `drop_distance_to_3m_high`
- leave-one-out ablations keep the same 11-column model interface and
  neutralize one feature to `0.5`
- altered feature profiles are written to
  `outputs/feature_profiles/<feature_profile_id>/` unless a different output
  directory is explicitly requested

For the active feature-phase plan and experiment matrix, see
[feature_phase.md](/C:/Ali/CS/Bachelor%20thesis/docs/feature_phase.md).

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
  initialization, masking, split integrity, checkpoint selection, artifact
  writing, and feature-phase metadata paths

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
