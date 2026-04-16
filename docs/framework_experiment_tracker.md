# Framework Experiment Tracker

## Purpose

This is the framework-only working sheet for the active PPO framework study.

Use it to:

- keep one archived note of the older PPO sweep
- keep one archived note of the pre-fix clipped-Gaussian framework runs
- track the current bounded-action framework leaderboard
- record the exact runs used to select the framework
- document the framework handoff into the feature phase

Machine-readable source:

- `outputs/experiments/setup_results.csv`
- current active framework runs are the rows filtered to:
  `StudyPhase = framework_selection` and
  `PolicySemanticsVersion = bounded_v2`

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
not directly comparable to the current canonical framework-phase runs.

## Archived Pre-Fix Framework Note

The first canonical framework study used the older unclipped-Gaussian action
path. Those runs are kept in `outputs/experiments/` for reference only.

Why they are archived:

- PPO sampled from an unbounded Gaussian
- SB3 clipped actions before `env.step()`
- rollout-buffer actions and log-probabilities still reflected the unclipped
  samples

After the bounded-action fix, the framework conclusion changed enough to
require a full rerun of the tracked framework set.

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
- action distribution: `masked_sigmoid_gaussian`
- policy semantics version: `bounded_v2`

## Framework Leaderboard

Selection rule:

- primary metric: mean validation reward across fixed seeds
- secondary tie-breaker: mean validation Spearman
- third tie-breaker: lower validation reward standard deviation
- promotion rule: beat the base by at least `0.01`, or stay within `0.005`
  while improving validation Spearman

| FrameworkID | Seeds | Mean Validation Reward | Validation Reward Std | Mean Validation Spearman | Mean Test Reward | Mean Test Spearman | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `pit_3m_flat_context` | `42, 7, 13` | `0.6818` | `0.0070` | `0.5720` | `0.7065` | `0.6066` | Selected winner after the bounded-action fix |
| `pit_1m_shared_mlp` | `42, 7, 13` | `0.6690` | `0.0052` | `0.5579` | `0.6950` | `0.5948` | Rejected after rerun: no longer the strongest validation framework |
| `pit_1m_context` | `42` | `0.6674` | `n/a` | `0.5518` | `0.7005` | `0.5985` | Rejected: pooled context alone still stayed below both the base and the winner on validation |
| `pit_3m_flat_shared_mlp` | `42` | `0.6618` | `n/a` | `0.5438` | `0.6890` | `0.5820` | Rejected: flat 3-month stack remained weaker than the context version and below the base |
| `pit_1m_dailystrip_shared_cnn` | `42` | `0.6472` | `n/a` | `0.5248` | `0.6757` | `0.5652` | Rejected: prior-month daily strip plus CNN still hurt ranking quality materially |

## Framework Coverage Status

- all five enabled framework candidates have now been executed under the active
  bounded-action semantics
- `pit_3m_flat_attention` remains a disabled stretch candidate and has no
  recorded run artifacts in the active phase

## Framework Winner Handoff

Locked framework winner:

- `FrameworkID`: `pit_3m_flat_context`
- representative run: [FW-STACK3M-CONTEXT-BOUNDED-S13](/C:/Ali/CS/Bachelor%20thesis/outputs/experiments/FW-STACK3M-CONTEXT-BOUNDED-S13)
- validation reward: `0.6870`
- test reward: `0.7033`
- validation Spearman: `0.5791`
- test Spearman: `0.6017`
- reported checkpoint: `best_model.zip`

Why the winner changed:

- the bounded-action fix removed the old clipped-Gaussian mismatch
- after rerunning the tracked framework set, the `3M + pooled context`
  framework beat the `1M` base by `0.0129` on mean validation reward
- it also improved mean validation Spearman by `0.0141`

This is the starting point for the next phase, which is feature optimization.

Boundary notes for interpretation:

- the current canonical panel ends at `2026-01`, and the active test split is
  aligned to that boundary, so test evaluation covers `11` months from
  `2025-03` through `2026-01`
- missing panel months `2011-02` to `2011-04` are expected from source
  coverage and the minimum active-asset rule; they are not treated as
  implementation bugs
- `ChangePctRaw` mismatches are QA-only and do not change the model path;
  `ReturnFromPrice` remains the authoritative series

## Recorded Framework Runs

| SetupID | FrameworkID | Seed | Validation Reward | Test Reward | Validation Spearman | Test Spearman | Validation MSE | Test MSE | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `FW-BASE-1M-BOUNDED-S42` | `pit_1m_shared_mlp` | `42` | `0.6710` | `0.7080` | `0.5608` | `0.6134` | `0.0716` | `0.0710` | Base rerun after the bounded-action fix |
| `FW-BASE-1M-BOUNDED-S7` | `pit_1m_shared_mlp` | `7` | `0.6630` | `0.6763` | `0.5495` | `0.5682` | `0.0720` | `0.0715` | Lower seed run confirms the bounded base still has variance |
| `FW-BASE-1M-BOUNDED-S13` | `pit_1m_shared_mlp` | `13` | `0.6728` | `0.7005` | `0.5633` | `0.6027` | `0.0718` | `0.0712` | Best bounded base seed, but not the winning framework |
| `FW-1M-CONTEXT-BOUNDED-S42` | `pit_1m_context` | `42` | `0.6674` | `0.7005` | `0.5518` | `0.5985` | `0.0628` | `0.0615` | Lower MSE than the bounded base, but validation ranking still weaker |
| `FW-1M-DAILYSTRIP-CNN-BOUNDED-S42` | `pit_1m_dailystrip_shared_cnn` | `42` | `0.6472` | `0.6757` | `0.5248` | `0.5652` | `0.0672` | `0.0666` | Observed daily strip plus CNN remained below every main monthly candidate |
| `FW-STACK3M-BOUNDED-S42` | `pit_3m_flat_shared_mlp` | `42` | `0.6618` | `0.6890` | `0.5438` | `0.5820` | `0.0628` | `0.0613` | Flat 3-month stack alone did not beat the bounded 1-month base |
| `FW-STACK3M-CONTEXT-BOUNDED-S42` | `pit_3m_flat_context` | `42` | `0.6845` | `0.7116` | `0.5761` | `0.6140` | `0.0625` | `0.0607` | Strong rerun that already beat the bounded base on both reward and Spearman |
| `FW-STACK3M-CONTEXT-BOUNDED-S7` | `pit_3m_flat_context` | `7` | `0.6739` | `0.7048` | `0.5607` | `0.6041` | `0.0621` | `0.0603` | Lower seed still stayed above the bounded base on validation reward |
| `FW-STACK3M-CONTEXT-BOUNDED-S13` | `pit_3m_flat_context` | `13` | `0.6870` | `0.7033` | `0.5791` | `0.6017` | `0.0611` | `0.0598` | Best validation run inside the winning framework |

## Pending Next Phase

The framework phase is complete enough to move on.

Next active phase:

1. keep `pit_3m_flat_context` fixed
2. design and test feature additions or feature replacements one at a time
3. keep the PPO config locked while feature work is in progress
4. return to broader PPO tuning only after the feature set is locked

Final framework-side conclusion:

- the bounded-action fix changed the framework winner
- the active feature-phase base is now `pit_3m_flat_context`
- the daily-strip CNN should not be carried into the feature phase

## How To Update This Sheet

After each real framework-phase run:

1. append the run to `outputs/experiments/setup_results.csv`
2. update the leaderboard and recorded runs table using
   `PolicySemanticsVersion = bounded_v2`
3. update the winner handoff section only if the selected framework changes
4. keep the two archived notes unchanged
5. keep feature-phase and tuning-phase runs in their own trackers instead of
   appending them here
