# Framework Phase

## Purpose

This is the active framework-phase document.

Use it to track:

- framework comparison methodology
- the tested framework set
- the locked framework conclusion
- the framework-to-feature handoff

Machine-readable source:

- `outputs/experiments/setup_results.csv`
- use rows filtered to:
  `StudyPhase = framework_selection` and
  `PolicySemanticsVersion = bounded_v2`

## Methodology

Comparison rules:

- compare frameworks on the same decision months
- require a full framework lookback for each active asset
- keep the final test window locked while iterating
- use outer validation to choose the winning framework
- record native metrics for reference, but use the common anchor comparison for
  promotion decisions:
  `risk_v1_equal_333 + reward_v1_rank70_mse30`
- use anchor outer-validation reward as the primary metric
- use anchor outer-validation Spearman as the secondary metric
- screen on seed `42` first
- expand to seeds `7` and `13` only after a seed-42 result is promotable

Framework input rules:

- monthly frameworks use prior monthly state rows only
- daily-input variants may read only observed rows from
  `data/ready/daily_market_series.csv`
- daily-input variants may read only the observed `t-1` month strip
- synthetic forward-filled rows must not enter policy input

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
- action distribution: `masked_sigmoid_gaussian`
- policy semantics version: `bounded_v2`

Month-level reward:

`0.7 * SpearmanRankCorr(predicted, realized) + 0.3 * (1 - MSE)`

## Tested Frameworks

| FrameworkID | Monthly Backbone | Extra Input Or Fusion | Actor Context | Tested Seeds | Outcome |
| --- | --- | --- | --- | --- | --- |
| `pit_1m_shared_mlp` | month `t-1` | none | none | `42, 7, 13` | Strong monthly baseline, but not the final winner |
| `pit_1m_context` | month `t-1` | none | pooled month context | `42` | Rejected: context hurt the `1M` backbone |
| `pit_3m_flat_shared_mlp` | months `t-3:t-1` flattened | none | none | `42` | Rejected: `3M` alone stayed below the `1M` base |
| `pit_3m_flat_context` | months `t-3:t-1` flattened | none | pooled month context | `42, 7, 13` | Locked winner for the next phase |
| `pit_1m_dailystrip_shared_cnn` | month `t-1` | observed `t-1` daily strip via shared CNN pool | none | `42` | Rejected: daily strip hurt ranking quality |
| `pit_1m_context_t1_dailyflat` | month `t-1` | observed `t-1` daily strip via flat concat | pooled month context | `42` | Rejected: daily flat plus context collapsed badly |
| `pit_1m_t1_dailyflat` | month `t-1` | observed `t-1` daily strip via flat concat | none | `42` | Rejected: removing context did not rescue daily flat |
| `pit_1m_t1_daily_actor_cnn` | month `t-1` | actor-only observed `t-1` daily strip via CNN pool | none | `42` | Rejected: actor-only CNN stayed below the `1M` base |
| `pit_1m_t1_daily_actor_flat` | month `t-1` | actor-only observed `t-1` daily strip via flat concat | none | `42` | Rejected: best actor-only daily variant, but still below the `1M` base |
| `pit_3m_flat_context_t1_dailyflat` | months `t-3:t-1` flattened | observed `t-1` daily strip via flat concat | pooled month context | `42, 7, 13` | Rejected: daily flat stayed far below the monthly winner |
| `pit_3m_flat_context_t1_daily_actor_cnn` | months `t-3:t-1` flattened | actor-only observed `t-1` daily strip via CNN pool | pooled month context | `42` | Rejected: stronger than the flat daily port, but still below the locked monthly winner on both promotion metrics |
| `pit_3m_flat_t1_dailyflat` | months `t-3:t-1` flattened | observed `t-1` daily strip via flat concat | none | `42` | Rejected: weakest tracked daily-input result |

Not run in the active phase:

- `pit_3m_flat_context_t1_daily_actor_flat`
- `pit_3m_flat_attention`

## Key Comparisons

### Monthly-Only Rerun

The fresh monthly-only rerun used the same bounded PPO setup and seed `42`.

| FrameworkID | Validation Reward | Validation Spearman | Interpretation |
| --- | --- | --- | --- |
| `pit_1m_shared_mlp` | `0.6710` | `0.5608` | `1M` without context stayed stronger than `3M` without context |
| `pit_1m_context` | `0.6664` | `0.5503` | Adding pooled context hurt the `1M` backbone |
| `pit_3m_flat_shared_mlp` | `0.6618` | `0.5438` | `3M` alone stayed below the `1M` base |
| `pit_3m_flat_context` | `0.6845` | `0.5761` | `3M + context` finished as the strongest monthly-only framework |

### Daily-Input Comparison

Best recorded validation result for each tested daily-input path:

| FrameworkID | Validation Reward | Validation Spearman | Interpretation |
| --- | --- | --- | --- |
| `pit_1m_dailystrip_shared_cnn` | `0.6472` | `0.5248` | Better than flat daily variants, but still below the monthly baselines |
| `pit_1m_context_t1_dailyflat` | `0.5327` | `0.3614` | Pooled context plus raw daily flat was clearly weak |
| `pit_1m_t1_dailyflat` | `0.5419` | `0.3759` | Removing context did not fix raw daily flat |
| `pit_1m_t1_daily_actor_cnn` | `0.5926` | `0.4474` | Actor-only CNN still stayed below the bounded `1M` base |
| `pit_1m_t1_daily_actor_flat` | `0.6161` | `0.4805` | Best actor-only daily screen, still not promotable |
| `pit_3m_flat_context_t1_dailyflat` | `0.5572` | `0.3962` | Daily flat plus the winning `3M` backbone failed materially |
| `pit_3m_flat_context_t1_daily_actor_cnn` | `0.6650` | `0.5486` | Strongest `3M` daily follow-up, but still below the locked monthly winner on both promotion metrics |
| `pit_3m_flat_t1_dailyflat` | `0.4110` | `0.1894` | Worst tracked daily-input result |

## Decision Conclusion

Locked winner:

- `pit_3m_flat_context`

Conclusion:

- `1M` alone beat `3M` alone.
- `3M + context` beat `1M + context`.
- pooled context hurt the `1M` backbone.
- pooled context clearly helped the `3M` backbone.
- daily-strip and daily-flat additions did not improve the monthly-only system.
- actor-only daily additions also failed the promotion gate.
- the direct `3M + context + actor-only daily CNN` screen also failed the
  seed-42 gate versus the locked winner.

Compact daily-input comparison:

- shared daily CNN, shared daily flat, and actor-only daily additions all
  stayed below the locked monthly-only winner and below the bounded `1M` base
  on validation ranking quality.
- the strongest tested `3M` daily follow-up was
  `pit_3m_flat_context_t1_daily_actor_cnn`, but it still finished below
  `pit_3m_flat_context` on both validation reward and validation Spearman.

Multi-seed winner note:

- `pit_3m_flat_context` mean validation reward across seeds `42, 7, 13`:
  `0.6818`
- `pit_3m_flat_context` mean validation Spearman across seeds `42, 7, 13`:
  `0.5720`
- `pit_1m_shared_mlp` mean validation reward across seeds `42, 7, 13`:
  `0.6690`
- `pit_1m_shared_mlp` mean validation Spearman across seeds `42, 7, 13`:
  `0.5579`

## Handoff To Feature Work

The framework phase is closed enough to proceed with feature work.

Feature-phase rules inherited from this conclusion:

- keep `pit_3m_flat_context` fixed
- keep the bounded PPO config fixed
- keep the reward and masking semantics fixed
- keep daily-input frameworks out of scope for the feature phase

## Comparison Protocol Audit

These rows document runs executed under the repaired comparison protocol and report both native and anchor-rescored outer-validation metrics.

| Date | SetupID | FrameworkID | ComparisonProtocolID | CheckpointProvenance | ObjectiveProfileID | RewardProfileID | TrainingMethodID | Native Validation Reward | Native Validation Spearman | Anchor Validation Reward | Anchor Validation Spearman | Prediction Similarity To Baseline | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V1_RANK70_MSE30-RANDOM_IID-S42 | pit_3m_flat_context | repaired_inner12_outer26_v1 | best_inner_validation | risk_v1_equal_333 | reward_v1_rank70_mse30 | random_iid | 0.6875 | 0.5803 | 0.6875 | 0.5803 | baseline | incumbent anchor |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V2_DOWNSIDE_050-REWARD_V1_RANK70_MSE30-RANDOM_IID-S42 | pit_3m_flat_context | repaired_inner12_outer26_v1 | best_inner_validation | risk_v2_downside_050 | reward_v1_rank70_mse30 | random_iid | 0.6828 | 0.5749 | 0.6859 | 0.5783 | P=0.9998; S=0.9998; MAD=0.0024 | stop: weak sensitivity |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V3_TAIL_040-REWARD_V1_RANK70_MSE30-RANDOM_IID-S42 | pit_3m_flat_context | repaired_inner12_outer26_v1 | best_inner_validation | risk_v3_tail_040 | reward_v1_rank70_mse30 | random_iid | 0.6777 | 0.5672 | 0.6865 | 0.5788 | P=0.9999; S=0.9999; MAD=0.0005 | stop: weak sensitivity |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V2_RANK85_MSE15-RANDOM_IID-S42 | pit_3m_flat_context | repaired_inner12_outer26_v1 | best_inner_validation | risk_v1_equal_333 | reward_v2_rank85_mse15 | random_iid | 0.6336 | 0.5799 | 0.6875 | 0.5802 | P=0.9999; S=0.9999; MAD=0.0007 | stop: weak sensitivity |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V1_RANK70_MSE30-ORDERED_CYCLE-S42 | pit_3m_flat_context | repaired_inner12_outer26_v1 | best_inner_validation | risk_v1_equal_333 | reward_v1_rank70_mse30 | ordered_cycle | 0.6814 | 0.5718 | 0.6816 | 0.5720 | P=0.9954; S=0.9948; MAD=0.0026 | screened |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V1_RANK70_MSE30-BLOCK_RANDOM_6M-S42 | pit_3m_flat_context | repaired_inner12_outer26_v1 | best_inner_validation | risk_v1_equal_333 | reward_v1_rank70_mse30 | block_random_6m | 0.6823 | 0.5732 | 0.6824 | 0.5734 | P=0.9952; S=0.9945; MAD=0.0040 | screened |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V7_DOWNSIDE_DRAWDOWN_5050-REWARD_V1_RANK70_MSE30-RANDOM_IID-S42 | pit_3m_flat_context | repaired_inner12_outer26_v1 | best_inner_validation | risk_v7_downside_drawdown_5050 | reward_v1_rank70_mse30 | random_iid | 0.6561 | 0.5397 | 0.6844 | 0.5764 | P=0.9988; S=0.9987; MAD=0.0044 | stop: weak sensitivity |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V5_DOWNSIDE_ONLY-REWARD_V1_RANK70_MSE30-RANDOM_IID-S42 | pit_3m_flat_context | repaired_inner12_outer26_v1 | best_inner_validation | risk_v5_downside_only | reward_v1_rank70_mse30 | random_iid | 0.6732 | 0.5666 | 0.6855 | 0.5775 | P=0.9996; S=0.9995; MAD=0.0045 | stop: weak sensitivity |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V6_DRAWDOWN_ONLY-REWARD_V1_RANK70_MSE30-RANDOM_IID-S42 | pit_3m_flat_context | repaired_inner12_outer26_v1 | best_inner_validation | risk_v6_drawdown_only | reward_v1_rank70_mse30 | random_iid | 0.6126 | 0.4810 | 0.6849 | 0.5770 | P=0.9979; S=0.9977; MAD=0.0041 | screened |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V4_VOL_ONLY-REWARD_V1_RANK70_MSE30-RANDOM_IID-S42 | pit_3m_flat_context | repaired_inner12_outer26_v1 | best_inner_validation | risk_v4_vol_only | reward_v1_rank70_mse30 | random_iid | 0.6786 | 0.5743 | 0.6875 | 0.5805 | P=0.9994; S=0.9993; MAD=0.0037 | stop: weak sensitivity |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V3_RANK100_MSE00-RANDOM_IID-S42 | pit_3m_flat_context | repaired_inner12_outer26_v1 | best_inner_validation | risk_v1_equal_333 | reward_v3_rank100_mse00 | random_iid | 0.5831 | 0.5831 | 0.6897 | 0.5833 | P=0.9999; S=0.9998; MAD=0.0009 | promotable on anchor |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V1_RANK70_MSE30-RANDOM_IID-S7 | pit_3m_flat_context | repaired_inner12_outer26_v1 | best_inner_validation | risk_v1_equal_333 | reward_v1_rank70_mse30 | random_iid | 0.6725 | 0.5591 | 0.6725 | 0.5591 | baseline | incumbent anchor |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V1_RANK70_MSE30-RANDOM_IID-S13 | pit_3m_flat_context | repaired_inner12_outer26_v1 | best_inner_validation | risk_v1_equal_333 | reward_v1_rank70_mse30 | random_iid | 0.6841 | 0.5753 | 0.6841 | 0.5753 | baseline | incumbent anchor |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V3_RANK100_MSE00-RANDOM_IID-S7 | pit_3m_flat_context | repaired_inner12_outer26_v1 | best_inner_validation | risk_v1_equal_333 | reward_v3_rank100_mse00 | random_iid | 0.5583 | 0.5583 | 0.6716 | 0.5583 | P=0.9997; S=0.9996; MAD=0.0035 | stop: weak sensitivity |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V3_RANK100_MSE00-RANDOM_IID-S13 | pit_3m_flat_context | repaired_inner12_outer26_v1 | best_inner_validation | risk_v1_equal_333 | reward_v3_rank100_mse00 | random_iid | 0.5739 | 0.5739 | 0.6832 | 0.5740 | P=0.9995; S=0.9994; MAD=0.0013 | stop: weak sensitivity |
## Objective Audit

These rows track realized-risk target variants and reward-profile variants under native scoring and the fixed anchor rescoring rule.

| Date | SetupID | FrameworkID | ObjectiveProfileID | RewardProfileID | TrainingMethodID | Native Validation Reward | Native Validation Spearman | Anchor Validation Reward | Anchor Validation Spearman | Prediction Similarity To Baseline | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V1_RANK70_MSE30-RANDOM_IID-S42 | pit_3m_flat_context | risk_v1_equal_333 | reward_v1_rank70_mse30 | random_iid | 0.6875 | 0.5803 | 0.6875 | 0.5803 | baseline | incumbent anchor |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V2_DOWNSIDE_050-REWARD_V1_RANK70_MSE30-RANDOM_IID-S42 | pit_3m_flat_context | risk_v2_downside_050 | reward_v1_rank70_mse30 | random_iid | 0.6828 | 0.5749 | 0.6859 | 0.5783 | P=0.9998; S=0.9998; MAD=0.0024 | stop: weak sensitivity |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V3_TAIL_040-REWARD_V1_RANK70_MSE30-RANDOM_IID-S42 | pit_3m_flat_context | risk_v3_tail_040 | reward_v1_rank70_mse30 | random_iid | 0.6777 | 0.5672 | 0.6865 | 0.5788 | P=0.9999; S=0.9999; MAD=0.0005 | stop: weak sensitivity |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V2_RANK85_MSE15-RANDOM_IID-S42 | pit_3m_flat_context | risk_v1_equal_333 | reward_v2_rank85_mse15 | random_iid | 0.6336 | 0.5799 | 0.6875 | 0.5802 | P=0.9999; S=0.9999; MAD=0.0007 | stop: weak sensitivity |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V7_DOWNSIDE_DRAWDOWN_5050-REWARD_V1_RANK70_MSE30-RANDOM_IID-S42 | pit_3m_flat_context | risk_v7_downside_drawdown_5050 | reward_v1_rank70_mse30 | random_iid | 0.6561 | 0.5397 | 0.6844 | 0.5764 | P=0.9988; S=0.9987; MAD=0.0044 | stop: weak sensitivity |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V5_DOWNSIDE_ONLY-REWARD_V1_RANK70_MSE30-RANDOM_IID-S42 | pit_3m_flat_context | risk_v5_downside_only | reward_v1_rank70_mse30 | random_iid | 0.6732 | 0.5666 | 0.6855 | 0.5775 | P=0.9996; S=0.9995; MAD=0.0045 | stop: weak sensitivity |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V6_DRAWDOWN_ONLY-REWARD_V1_RANK70_MSE30-RANDOM_IID-S42 | pit_3m_flat_context | risk_v6_drawdown_only | reward_v1_rank70_mse30 | random_iid | 0.6126 | 0.4810 | 0.6849 | 0.5770 | P=0.9979; S=0.9977; MAD=0.0041 | screened |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V4_VOL_ONLY-REWARD_V1_RANK70_MSE30-RANDOM_IID-S42 | pit_3m_flat_context | risk_v4_vol_only | reward_v1_rank70_mse30 | random_iid | 0.6786 | 0.5743 | 0.6875 | 0.5805 | P=0.9994; S=0.9993; MAD=0.0037 | stop: weak sensitivity |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V3_RANK100_MSE00-RANDOM_IID-S42 | pit_3m_flat_context | risk_v1_equal_333 | reward_v3_rank100_mse00 | random_iid | 0.5831 | 0.5831 | 0.6897 | 0.5833 | P=0.9999; S=0.9998; MAD=0.0009 | promotable on anchor |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V1_RANK70_MSE30-RANDOM_IID-S7 | pit_3m_flat_context | risk_v1_equal_333 | reward_v1_rank70_mse30 | random_iid | 0.6725 | 0.5591 | 0.6725 | 0.5591 | baseline | incumbent anchor |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V1_RANK70_MSE30-RANDOM_IID-S13 | pit_3m_flat_context | risk_v1_equal_333 | reward_v1_rank70_mse30 | random_iid | 0.6841 | 0.5753 | 0.6841 | 0.5753 | baseline | incumbent anchor |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V3_RANK100_MSE00-RANDOM_IID-S7 | pit_3m_flat_context | risk_v1_equal_333 | reward_v3_rank100_mse00 | random_iid | 0.5583 | 0.5583 | 0.6716 | 0.5583 | P=0.9997; S=0.9996; MAD=0.0035 | stop: weak sensitivity |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V3_RANK100_MSE00-RANDOM_IID-S13 | pit_3m_flat_context | risk_v1_equal_333 | reward_v3_rank100_mse00 | random_iid | 0.5739 | 0.5739 | 0.6832 | 0.5740 | P=0.9995; S=0.9994; MAD=0.0013 | stop: weak sensitivity |
## Training Method Screens

These rows track train-sampling-method comparisons while keeping validation and test ordered and reporting anchor-rescored validation metrics.

| Date | SetupID | FrameworkID | ObjectiveProfileID | RewardProfileID | TrainingMethodID | Native Validation Reward | Native Validation Spearman | Anchor Validation Reward | Anchor Validation Spearman | Prediction Similarity To Baseline | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V1_RANK70_MSE30-RANDOM_IID-S42 | pit_3m_flat_context | risk_v1_equal_333 | reward_v1_rank70_mse30 | random_iid | 0.6875 | 0.5803 | 0.6875 | 0.5803 | baseline | incumbent anchor |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V1_RANK70_MSE30-ORDERED_CYCLE-S42 | pit_3m_flat_context | risk_v1_equal_333 | reward_v1_rank70_mse30 | ordered_cycle | 0.6814 | 0.5718 | 0.6816 | 0.5720 | P=0.9954; S=0.9948; MAD=0.0026 | screened |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V1_RANK70_MSE30-BLOCK_RANDOM_6M-S42 | pit_3m_flat_context | risk_v1_equal_333 | reward_v1_rank70_mse30 | block_random_6m | 0.6823 | 0.5732 | 0.6824 | 0.5734 | P=0.9952; S=0.9945; MAD=0.0040 | screened |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V1_RANK70_MSE30-RANDOM_IID-S7 | pit_3m_flat_context | risk_v1_equal_333 | reward_v1_rank70_mse30 | random_iid | 0.6725 | 0.5591 | 0.6725 | 0.5591 | baseline | incumbent anchor |
| 2026-04-22 | FW-RELK-PIT_3M_FLAT_CONTEXT-RISK_V1_EQUAL_333-REWARD_V1_RANK70_MSE30-RANDOM_IID-S13 | pit_3m_flat_context | risk_v1_equal_333 | reward_v1_rank70_mse30 | random_iid | 0.6841 | 0.5753 | 0.6841 | 0.5753 | baseline | incumbent anchor |
