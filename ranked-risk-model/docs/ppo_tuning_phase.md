# PPO Tuning Phase

Status: closed.

This file records the PPO tuning decision. Current model details and thesis
evaluation live in [project_guide.md](/C:/Ali/CS/Bachelor%20thesis/docs/project_guide.md).

## Purpose

After the framework and feature phases, PPO hyperparameters were tuned while
holding the active framework fixed:

- framework: `pit_3m_flat_context`
- training method: `ordered_cycle`
- reward: `0.7 * SpearmanRankCorr(predicted, realized) + 0.3 * (1 - MSE)`
- action distribution: `masked_sigmoid_gaussian`
- policy semantics: `bounded_v2`

The tuning target was validation reward first, with validation Spearman as the
guardrail.

## Starting Baseline

The locked pre-tuning PPO configuration was:

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

## Locked Tuned Config

The selected tuned PPO candidate is `refined50`.

| Parameter | Value |
| --- | ---: |
| `learning_rate` | `0.00024935310281972535` |
| `n_steps` | `256` |
| `batch_size` | `256` |
| `n_epochs` | `10` |
| `gamma` | `1.0` |
| `gae_lambda` | `1.0` |
| `clip_range` | `0.2990122587129351` |
| `ent_coef` | `0.0023477909057284673` |
| `vf_coef` | `0.9023537822799527` |
| `max_grad_norm` | `0.3` |

Gamma and GAE stayed at `1.0` because each PPO episode is one decision month;
sensitivity checks did not justify changing them.

## Decision Evidence

| Step | Winning setup | Validation reward | Validation Spearman | Decision |
| --- | --- | ---: | ---: | --- |
| Full Optuna screen | `trial75` | `0.7036` | `0.5997` | seed-42 winner |
| Refined Optuna screen | `refined50` | `0.7056` | `0.6017` | refined winner |
| Three-seed confirmation | `refined50` | `0.7008` | `0.5950` | locked tuned config |

The tuned setup was then reused for final top-candidate reruns and tail-aware
candidate reruns. Test metrics were kept for reporting only, not selection.

## Final Current-Best Update

After PPO tuning, the initial tuned top-candidate rerun selected
`drop_distance_to_3m_high`. A later tail-aware additive candidate screen
promoted `downside_tail_ratio_3m` while keeping the same `refined50` PPO
configuration.

Current best:

- model id: `downside_tail_ratio_3m_refined50`
- framework: `pit_3m_flat_context`
- tuned PPO candidate: `refined50`
- additive feature: `downside_tail_ratio_3m`

Three-seed current-best metrics:

| Split | Reward | Spearman | High-risk top-25% overlap |
| --- | ---: | ---: | ---: |
| validation | `0.7081` | `0.6047` | `0.4772` |
| test | `0.7515` | `0.6652` | `0.4949` |

This update changed current-best metadata and promoted artifacts only; it did
not reopen PPO tuning.
