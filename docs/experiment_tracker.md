# Experiment Tracker

## Purpose

This is the active working sheet for the framework-first PPO study.

Use it to:

- keep one archived note of the legacy PPO sweep
- track the active framework leaderboard
- record the exact runs used to select the framework
- lock the feature-phase starting point

Machine-readable source:

- `outputs/experiments/setup_results.csv`

Per-run artifacts:

- `outputs/experiments/<SetupID>/`

## Archived Legacy Reset Note

The earlier PPO sweep was reset and removed from the active experiment phase.

Legacy best result kept for context only:

- `SetupID`: `PPO-LR-1E4-20260408`
- validation reward: `0.6906`
- test reward: `0.7115`
- validation Spearman: `0.5884`
- test Spearman: `0.6179`

This legacy result was produced under the old baked decision-month panel and is
not directly comparable to the current framework-phase runs.

## Locked Framework-Phase PPO Config

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
- common train decision start: `2011-01`

## Framework Leaderboard

Selection rule:

- primary metric: mean validation reward across fixed seeds
- secondary tie-breaker: mean validation Spearman
- third tie-breaker: lower validation reward standard deviation
- promotion rule: beat the base by at least `0.01`, or stay within `0.005`
  while improving validation Spearman

| FrameworkID | Seeds | Mean Validation Reward | Validation Reward Std | Mean Validation Spearman | Mean Test Reward | Mean Test Spearman | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `pit_1m_shared_mlp` | `42, 7, 13` | `0.6772` | `0.0053` | `0.5689` | `0.7031` | `0.6056` | Selected winner |
| `pit_1m_context` | `42` | `0.6498` | `n/a` | `0.5243` | `0.6835` | `0.5716` | Rejected: context alone hurt both reward and ranking quality |
| `pit_1m_dailystrip_shared_cnn` | `42` | `0.6093` | `n/a` | `0.4747` | `0.5928` | `0.4508` | Rejected: prior-month daily strip plus CNN materially hurt reward and ranking quality |
| `pit_3m_flat_context` | `42, 7, 13` | `0.6793` | `0.0033` | `0.5639` | `0.7045` | `0.5986` | Not promoted: reward stayed within the `0.005` tie band but validation Spearman was worse than the base |
| `pit_3m_flat_shared_mlp` | `42` | `0.6735` | `n/a` | `0.5638` | `0.7104` | `0.6161` | Rejected after the first run |

## Feature-Phase Starting Point

Locked framework winner:

- `FrameworkID`: `pit_1m_shared_mlp`
- representative run: [FW-BASE-1M-S42](/C:/Ali/CS/Bachelor%20thesis/outputs/experiments/FW-BASE-1M-S42)
- validation reward: `0.6823`
- test reward: `0.7145`
- validation Spearman: `0.5765`
- test Spearman: `0.6222`
- reported checkpoint: `best_model.zip`

This is the starting point for the next phase, which is feature optimization.

Boundary notes for interpretation:

- the current canonical panel ends at `2026-01`, and the active test split is
  now explicitly aligned to that boundary, so test evaluation covers `11`
  months from `2025-03` through `2026-01`
- missing panel months `2011-02` to `2011-04` are expected from source
  coverage and the minimum active-asset rule; they are not currently treated as
  implementation bugs
- `ChangePctRaw` mismatches are QA-only and do not change the model path;
  `ReturnFromPrice` remains the authoritative series

## Recorded Framework Runs

| SetupID | FrameworkID | Seed | Validation Reward | Test Reward | Validation Spearman | Test Spearman | Validation MSE | Test MSE | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `FW-BASE-1M-S42` | `pit_1m_shared_mlp` | `42` | `0.6823` | `0.7145` | `0.5765` | `0.6222` | `0.0708` | `0.0701` | Best single run inside the winning framework |
| `FW-BASE-1M-S7` | `pit_1m_shared_mlp` | `7` | `0.6718` | `0.6889` | `0.5610` | `0.5853` | `0.0699` | `0.0692` | Lower seed run confirms variance exists |
| `FW-BASE-1M-S13` | `pit_1m_shared_mlp` | `13` | `0.6775` | `0.7057` | `0.5692` | `0.6092` | `0.0699` | `0.0691` | Mid-range seed run |
| `FW-1M-CONTEXT-S42` | `pit_1m_context` | `42` | `0.6498` | `0.6835` | `0.5243` | `0.5716` | `0.0572` | `0.0553` | Isolated context ablation. Lower MSE, but substantially worse ranking and reward than the base |
| `FW-1M-DAILYSTRIP-CNN-S42` | `pit_1m_dailystrip_shared_cnn` | `42` | `0.6093` | `0.5928` | `0.4747` | `0.4508` | `0.0765` | `0.0758` | Added an observed prior-month daily strip with a small shared CNN. This materially underperformed the base and was not promoted |
| `FW-STACK3M-S42` | `pit_3m_flat_shared_mlp` | `42` | `0.6735` | `0.7104` | `0.5638` | `0.6161` | `0.0705` | `0.0698` | Flat 3-month stack underperformed the 1-month base |
| `FW-STACK3M-CONTEXT-S42` | `pit_3m_flat_context` | `42` | `0.6824` | `0.7127` | `0.5696` | `0.6115` | `0.0544` | `0.0509` | Reward tied the base, but validation Spearman stayed lower |
| `FW-STACK3M-CONTEXT-S7` | `pit_3m_flat_context` | `7` | `0.6758` | `0.7055` | `0.5583` | `0.5993` | `0.0502` | `0.0465` | Confirmed lower MSE but weaker ranking quality |
| `FW-STACK3M-CONTEXT-S13` | `pit_3m_flat_context` | `13` | `0.6796` | `0.6951` | `0.5638` | `0.5849` | `0.0501` | `0.0477` | Stayed close on reward, still below the base on Spearman |

## Pending Next Phase

The framework phase is complete enough to move on.

Next active phase:

1. keep `pit_1m_shared_mlp` fixed
2. design and test feature additions or feature replacements one at a time
3. keep the PPO config locked while feature work is in progress
4. return to broader PPO tuning only after the feature set is locked

Final framework-side conclusion:

- the added daily-strip CNN did not improve over the base and should not be
  carried into the feature phase

## How To Update This Sheet

After each real feature-phase run:

1. append the run to `outputs/experiments/setup_results.csv`
2. add the run to the recorded runs table
3. update the winner section only if the active framework or feature-phase base changes
4. keep the legacy reset note unchanged
