# Framework Phase

Status: closed.

This file records the framework-selection decision. Current model details and
thesis evaluation live in
[project_guide.md](/C:/Ali/CS/Bachelor%20thesis/docs/project_guide.md).

## Purpose

The framework phase compared how monthly state rows should be fed into PPO
before feature tuning. The final selection used validation metrics only, with
test results reserved for reporting.

Rules used during comparison:

- compare frameworks on the same decision months
- require a full lookback for every active asset
- use prior monthly state rows only for decision month `t`
- keep daily-input candidates restricted to observed rows from prior month
  `t-1`
- keep synthetic forward-filled daily rows out of policy input

## Locked PPO Setup During Framework Selection

| Parameter | Value |
| --- | ---: |
| `learning_rate` | `1e-4` |
| `n_steps` | `256` |
| `batch_size` | `256` |
| `n_epochs` | `10` |
| `gamma` | `1.0` |
| `gae_lambda` | `1.0` |
| `clip_range` | `0.2` |
| `ent_coef` | `0.01` |
| `vf_coef` | `0.5` |
| `max_grad_norm` | `0.5` |
| `eval_frequency` | `512` |

Reward:

`0.7 * SpearmanRankCorr(predicted, realized) + 0.3 * (1 - MSE)`

## Tested Framework Groups

Monthly-only candidates:

| Framework | State input | Actor context | Outcome |
| --- | --- | --- | --- |
| `pit_1m_shared_mlp` | month `t-1` | none | strong baseline, not winner |
| `pit_1m_context` | month `t-1` | pooled context | rejected; context hurt 1M backbone |
| `pit_3m_flat_shared_mlp` | months `t-3:t-1` | none | rejected; 3M alone was weak |
| `pit_3m_flat_context` | months `t-3:t-1` | pooled context | locked winner |

Daily-input candidates:

| Framework family | Daily input | Outcome |
| --- | --- | --- |
| shared daily CNN | observed prior-month strip | rejected |
| daily flat concat | observed prior-month strip | rejected |
| actor-only daily CNN/flat | daily path affects actor only | rejected |
| `3M + context + daily` variants | monthly winner plus daily input | rejected |

## Key Validation Results

Monthly-only seed-42 rerun:

| Framework | Validation reward | Validation Spearman |
| --- | ---: | ---: |
| `pit_1m_shared_mlp` | `0.6710` | `0.5608` |
| `pit_1m_context` | `0.6664` | `0.5503` |
| `pit_3m_flat_shared_mlp` | `0.6618` | `0.5438` |
| `pit_3m_flat_context` | `0.6845` | `0.5761` |

Best daily-input checks:

| Framework | Validation reward | Validation Spearman | Interpretation |
| --- | ---: | ---: | --- |
| `pit_1m_dailystrip_shared_cnn` | `0.6472` | `0.5248` | best shared CNN daily screen, below monthly winner |
| `pit_1m_t1_daily_actor_flat` | `0.6161` | `0.4805` | best actor-only 1M daily screen, below monthly winner |
| `pit_3m_flat_context_t1_daily_actor_cnn` | `0.6650` | `0.5486` | strongest 3M daily follow-up, still below monthly winner |
| `pit_3m_flat_context_t1_dailyflat` | `0.5572` | `0.3962` | rejected |

Multi-seed monthly comparison:

| Framework | Mean validation reward | Mean validation Spearman |
| --- | ---: | ---: |
| `pit_3m_flat_context` | `0.6818` | `0.5720` |
| `pit_1m_shared_mlp` | `0.6690` | `0.5579` |

## Final Decision

Locked framework:

- `pit_3m_flat_context`

Reason:

- `3M + pooled context` produced the strongest validation ranking quality
- context helped the 3-month backbone but hurt the 1-month backbone
- daily-input paths did not improve the monthly-only system
- actor-only daily paths also failed the promotion gate

Framework search is closed. Future work should not reopen daily-input,
attention, recurrent, transformer, or non-RL trainers unless thesis scope is
explicitly changed.
