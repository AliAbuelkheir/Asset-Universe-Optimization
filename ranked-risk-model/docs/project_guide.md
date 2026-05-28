# Project Guide

## Objective

This repository supports a thesis on AI/ML-based investor-suitable
asset-universe selection before allocation. The current implementation uses a
variable-universe, month-level PPO agent that predicts asset `realized_risk`
scores and derives monthly risk-tolerance buckets from those scores.

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

- model id = `downside_tail_ratio_3m_refined50`
- framework = `pit_3m_flat_context`
- base feature profile = `full_current_v1`
- additive tail feature = `downside_tail_ratio_3m`
- tuned PPO candidate = `refined50`
- comparison protocol = `repaired_inner12_outer26_v1`
- objective profile = `risk_v1_equal_333`
- reward profile = `reward_v1_rank70_mse30`
- training method = `ordered_cycle`
- input feature set = `shadow_add_downside_tail_ratio_3m`
- checkpoint provenance = `best_inner_validation`
- artifact root = `outputs/generated/runs/tail_candidates/refined50/`
- canonical promoted artifact = `outputs/best_model/`

Selection rule:

- choose the strongest three-seed validation high-risk-overlap improvement
- require validation reward and Spearman guardrails versus the previous current
  best
- use test metrics only for reporting

Three-seed metrics:

- validation reward = `0.7081`
- validation Spearman = `0.6047`
- validation high-risk top-25% overlap = `0.4772`
- test reward = `0.7515`
- test Spearman = `0.6652`
- test high-risk top-25% overlap = `0.4949`

Important comparison note:

- `monthly_only_rows_v1` remains useful reporting evidence for the October
  2025 stress case, but `downside_tail_ratio_3m` is the stronger validation
  tail-plus-rank candidate.
- Canonical defaults remain `full_current_v1`; current-best metadata is kept
  separate from canonical data/profile defaults.
- `outputs/best_model/` is overwritten on every promotion. Other generated
  runs and reports live under ignored `outputs/generated/`.

## Active PPO Implementation

Current active modules:

- `src/data_processing/build_model_dataset.py`
- `src/data_processing/validate_model_dataset.py`
- `src/environment/asset_risk_env.py`
- `src/training/frameworks.py`
- `src/training/policy.py`
- `src/training/train.py`
- `src/training/evaluate.py`
- `src/training/portfolio_evaluation.py`
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

## Thesis Evaluation: Risk-Tolerance Bucket Evaluation

The thesis-facing downstream benchmark is an equal-weight simulation over
investor risk-tolerance buckets formed from the promoted model predictions. Its
purpose is to test whether the model can construct asset universes that match
different investor objectives before any final allocation model is applied. It
is not a full portfolio optimizer and should not be described as one.

Investor group objectives:

| Investor group | Selection objective | Thesis interpretation |
| --- | --- | --- |
| Conservative / low risk | Prioritize realized-risk reduction; returns are secondary. | The selected universe should have materially lower realized risk than the full active universe. |
| Balanced / medium risk | Balance risk containment with return participation. | The selected universe should sit between conservative and aggressive objectives and can overlap both sides. |
| Aggressive / high risk | Tolerate higher realized risk to access higher return opportunity. | The selected universe may have higher realized risk and should be interpreted through a risk-return tradeoff, not as guaranteed return prediction. |

Command:

```powershell
.\.venv\Scripts\python.exe -m src.training.portfolio_evaluation
```

Inputs:

- `outputs/best_model/ranked_predictions.csv`
- `data/ready/daily_market_series.csv`

Procedure:

1. compound each asset's authoritative daily `ReturnFromPrice` into monthly
   realized returns
2. join monthly returns to promoted model predictions by `(Date, AssetID)`
3. form equal-weight monthly portfolios from predicted-risk percentile bands
4. report risk separation by investor group and return behavior as economic
   diagnostics

The evaluator compares several bucket methods by default. All methods use
predicted rank-percentile bands, so bucket sizes adapt to the active universe in
each month instead of hardcoding a number of assets.

Candidate bucket methods:

| Method | Low-risk band | Medium-risk band | High-risk band | How it works |
| --- | --- | --- | --- | --- |
| `overlap_40_50` | `0.00` to `0.40` | `0.25` to `0.75` | `0.60` to `1.00` | Keeps the original thesis idea: low and high are broad 40% tails, while medium overlaps both sides. Assets near the 25-40% and 60-75% boundaries can serve two investor profiles. |
| `tercile_no_overlap` | `0.00` to `0.33` | `0.33` to `0.67` | `0.67` to `1.00` | Splits the ranked universe into three roughly equal-width groups. This is simple to explain but does not allow assets to be shared across risk-tolerance buckets. |
| `wide_overlap_50_60` | `0.00` to `0.50` | `0.20` to `0.80` | `0.50` to `1.00` | Uses very inclusive investor universes. Low and high each receive about half the active universe, so separation is intentionally softer. |
| `tail_30_overlap` | `0.00` to `0.30` | `0.20` to `0.80` | `0.70` to `1.00` | Reserves low and high for the clearest 30% tails and sends most assets to the medium bucket. This makes conservative/aggressive buckets selective while keeping ambiguous assets in the balanced universe. |

The bucket overlap is intentional. Real investor universes do not need to be
mutually exclusive: a stable asset can suit conservative and balanced
investors, while an upper-middle-risk asset can suit balanced and aggressive
investors.

The current recommended method is `tail_30_overlap`, selected because it gives
the largest high-minus-low realized-risk spread while keeping realized risk
monotonic across all test months. It also deliberately keeps fewer assets in the
extreme buckets and more assets in the medium bucket. This matches the thesis
framing that conservative investors should receive the clearest low-risk
universe, aggressive investors should receive the clearest high-risk/high-return
opportunity universe, and balanced investors should receive a broader
risk-return tradeoff universe.

Benchmark context:

- full universe equal weight is the neutral investable benchmark
- repeated random rank assignments show what bucket behavior looks like without
  model ordering
- realized-risk oracle buckets are non-investable and used only as an upper
  diagnostic bound

Current promoted-model test-window risk result for `tail_30_overlap`, `2025-03`
to `2026-01`:

| Bucket | Mean realized risk | Investor interpretation |
| --- | ---: | --- |
| Full universe | `0.500` | neutral reference |
| Low-risk bucket | `0.239` | conservative universe; materially below full universe risk |
| Medium-risk bucket | `0.536` | balanced universe; middle/high realized-risk participation |
| High-risk bucket | `0.688` | aggressive universe; materially above full universe risk |

Current promoted-model test-window return diagnostics for `tail_30_overlap`,
`2025-03` to `2026-01`:

| Bucket | Cumulative return | Mean monthly return | Monthly volatility | Max drawdown |
| --- | ---: | ---: | ---: | ---: |
| Full universe | `49.59%` | `3.75%` | `1.84%` | `0.00%` |
| Low-risk bucket | `29.91%` | `2.43%` | `1.93%` | `-1.92%` |
| Medium-risk bucket | `50.17%` | `3.79%` | `2.08%` | `0.00%` |
| High-risk bucket | `86.24%` | `5.92%` | `4.71%` | `-3.97%` |

Bucket-method comparison on the test split:

| Method | Monthly monotonicity | Low risk | Medium risk | High risk | High-low spread | Mean assets low/medium/high |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `tail_30_overlap` | `11/11` | `0.239` | `0.536` | `0.688` | `0.449` | `11 / 22 / 11` |
| `tercile_no_overlap` | `10/11` | `0.257` | `0.559` | `0.683` | `0.426` | `12 / 12 / 12` |
| `overlap_40_50` | `11/11` | `0.304` | `0.549` | `0.660` | `0.356` | `15 / 18 / 15` |
| `wide_overlap_50_60` | `11/11` | `0.341` | `0.536` | `0.659` | `0.317` | `18 / 22 / 18` |

Validation robustness check for `tail_30_overlap`, `2023-01` to `2025-02`:

| Bucket | Mean realized risk | Delta versus full universe | Mean assets |
| --- | ---: | ---: | ---: |
| Full universe | `0.500` | `0.000` | `36` |
| Low-risk bucket | `0.278` | `-0.222` | `11` |
| Medium-risk bucket | `0.538` | `0.038` | `22` |
| High-risk bucket | `0.671` | `0.171` | `11` |

On validation, mean realized risk is still ordered low < medium < high, and
monthly monotonicity holds in `24/26` months. The two exceptions are `2023-04`
and `2023-12`, where the high-risk bucket remains above low-risk but falls
slightly below the medium bucket. This supports using `tail_30_overlap` while
also giving a defensible limitation to discuss in the thesis.

Thesis-safe claims:

- the method constructs risk-tolerance-oriented asset universes before
  allocation
- the low-risk bucket materially reduces realized risk versus the full active
  universe in the current evaluation
- the high-risk bucket shows higher realized risk and higher cumulative return
  in the current short test window, which is consistent with a risk-return
  tradeoff

Thesis-unsafe claims:

- the PPO model optimizes expected return
- the method proves improved final portfolio optimization returns
- the current model directly solves investor-tier allocation weights

The high-risk bucket earned the highest cumulative return in the current short
test window, while also carrying the highest realized risk and higher volatility.
This supports the thesis framing of risk-tolerance-dependent universe
construction. It is not proof that the PPO policy predicts returns. Return,
Sharpe, Sortino, and drawdown values remain economic diagnostics unless a future
objective explicitly trains for return-aware utility by investor group.

Generated files live under:

- `outputs/generated/reports/portfolio_evaluation/`

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
