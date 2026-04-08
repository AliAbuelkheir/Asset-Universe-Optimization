# Experiment Tracker

## Purpose

This is the main working sheet for model iteration.

Use it to:

- record every PPO experiment that was actually run
- compare validation and test performance across runs
- track which checkpoint was selected
- list the next experiments to run

Machine-readable source:

- `outputs/experiments/setup_results.csv`

Per-run artifacts:

- `outputs/experiments/<SetupID>/`

## Active Objective

- framework: PPO monthly ranking
- policy: `MaskedActorCriticPolicy`
- input view: `monthly_asset_panel`
- target: `realized_risk`
- reward:
  `0.7 * SpearmanRankCorr(predicted, realized) + 0.3 * (1 - MSE)`

Fixed split ranges:

- train: `2010-11` to `2022-12`
- validation: `2023-01` to `2025-02`
- test: `2025-03` to `2026-02`

Checkpoint selection rule:

- choose the checkpoint with the best validation mean reward
- report final train/validation/test metrics from that checkpoint

## Recorded Runs

| SetupID | Date | Timesteps | LR | N Steps | Batch | Epochs | Ent Coef | Validation Reward | Test Reward | Validation Spearman | Test Spearman | Validation MSE | Test MSE | Reported Checkpoint | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PPO-CANONICAL-20260408 | 2026-04-08 | 4096 | 0.0003 | 256 | 256 | 10 | 0.01 | 0.6778 | 0.7051 | 0.5700 | 0.6086 | 0.0706 | 0.0696 | `best_model.zip` | First persistent PPO run after the RL-only refactor. Validation peak occurred at 1024 timesteps. |
| PPO-EVAL-512-20260408 | 2026-04-08 | 4096 | 0.0003 | 256 | 256 | 10 | 0.01 | 0.6851 | 0.7034 | 0.5809 | 0.6066 | 0.0718 | 0.0709 | `best_model.zip` | Same PPO setup as canonical, but validation checked every 512 timesteps. Best checkpoint was found at 512 timesteps. |
| PPO-SEED-7-20260408 | 2026-04-08 | 4096 | 0.0003 | 256 | 256 | 10 | 0.01 | 0.6602 | 0.6883 | 0.5381 | 0.5772 | 0.0548 | 0.0525 | `best_model.zip` | Alternate seed run. Validation improved steadily through 4096 timesteps, but finished below the current best validation reward. |
| PPO-SEED-13-20260408 | 2026-04-08 | 4096 | 0.0003 | 256 | 256 | 10 | 0.01 | 0.6692 | 0.6870 | 0.5577 | 0.5828 | 0.0708 | 0.0698 | `best_model.zip` | Second alternate seed run. Best validation checkpoint was again early at 1024 timesteps, confirming seed sensitivity. |
| PPO-LR-1E4-20260408 | 2026-04-08 | 4096 | 0.0001 | 256 | 256 | 10 | 0.01 | 0.6906 | 0.7115 | 0.5884 | 0.6179 | 0.0709 | 0.0699 | `best_model.zip` | Lower learning-rate run. Best validation checkpoint moved later to 2048 timesteps and became the strongest result so far. |
| PPO-ENT-000-20260408 | 2026-04-08 | 4096 | 0.0003 | 256 | 256 | 10 | 0.00 | 0.6775 | 0.7053 | 0.5695 | 0.6088 | 0.0706 | 0.0696 | `best_model.zip` | Entropy-free run. It behaved similarly to the canonical setup and did not improve validation reward. |
| PPO-NSTEPS-512-20260408 | 2026-04-08 | 4096 | 0.0003 | 512 | 256 | 10 | 0.01 | 0.6671 | 0.7070 | 0.5504 | 0.6065 | 0.0607 | 0.0585 | `best_model.zip` | Longer-rollout run. It reduced MSE substantially, but ranking quality fell and validation reward stayed below the current best. |

## Current Best Run

Current best recorded setup:

- `SetupID`: `PPO-LR-1E4-20260408`
- artifact directory:
  [outputs/experiments/PPO-LR-1E4-20260408](/C:/Ali/CS/Bachelor%20thesis/outputs/experiments/PPO-LR-1E4-20260408)
- validation mean reward: `0.6906`
- test mean reward: `0.7115`
- validation mean Spearman: `0.5884`
- test mean Spearman: `0.6179`

Important files:

- [setup_summary.json](/C:/Ali/CS/Bachelor%20thesis/outputs/experiments/PPO-LR-1E4-20260408/setup_summary.json)
- [training_metrics.csv](/C:/Ali/CS/Bachelor%20thesis/outputs/experiments/PPO-LR-1E4-20260408/training_metrics.csv)
- [split_summary.csv](/C:/Ali/CS/Bachelor%20thesis/outputs/experiments/PPO-LR-1E4-20260408/split_summary.csv)
- [monthly_metrics.csv](/C:/Ali/CS/Bachelor%20thesis/outputs/experiments/PPO-LR-1E4-20260408/monthly_metrics.csv)
- [ranked_predictions.csv](/C:/Ali/CS/Bachelor%20thesis/outputs/experiments/PPO-LR-1E4-20260408/ranked_predictions.csv)

Training-curve note for this run:

- validation mean reward at `1024` timesteps: `0.6836`
- validation mean reward at `2048` timesteps: `0.6906`
- validation mean reward at `3072` timesteps: `0.6846`
- validation mean reward at `4096` timesteps: `0.6809`

That means the saved `best_model.zip` is the 2048-timestep checkpoint, not the
final model.

## Latest Sweep Findings

- Lowering `learning_rate` from `3e-4` to `1e-4` produced the best validation and test reward so far.
- Checking validation every `512` timesteps helped checkpoint selection, but did not beat the lower-learning-rate run by itself.
- Seed variance is meaningful. Validation reward ranged from `0.6602` to `0.6851` across the canonical-style runs, so single-run conclusions are weak.
- Setting `ent_coef=0.0` was effectively neutral relative to the canonical setup and did not improve validation reward.
- Increasing `n_steps` to `512` improved MSE, but hurt Spearman enough that the combined reward fell.

## Pending Experiments

### Priority 1: PPO Stabilization

| Status | Experiment | Change | Why |
| --- | --- | --- | --- |
| pending | PPO-LR-1E4-EVAL-512 | Combine `learning_rate=1e-4` with `eval_frequency=512` | Check whether the current best setup peaks between 1024-step validation checks. |
| pending | PPO-LR-1E4-SEED-7 | Repeat the current best setup with seed `7` | Measure whether the learning-rate improvement is robust across randomness. |
| pending | PPO-LR-1E4-SEED-13 | Repeat the current best setup with seed `13` | Estimate variance for the current best setup instead of the older canonical one. |
| pending | PPO-LR-1E4-LONGER-16384 | Increase total timesteps from 4096 to 16384 on the current best setup | Check whether the lower-learning-rate run continues improving with a larger budget. |

### Priority 2: Hyperparameter Sweeps

| Status | Experiment | Change | Why |
| --- | --- | --- | --- |
| pending | PPO-ENT-002 | Set `ent_coef=0.02` | Test a slightly stronger exploration term. |
| pending | PPO-LR-1E3 | Set `learning_rate=1e-3` | Test whether faster learning improves early validation peaks. |
| pending | PPO-LR-1E4-NSTEPS-512 | Combine `learning_rate=1e-4` with `n_steps=512` | Check whether the best learning rate recovers ranking quality under longer rollouts. |

### Priority 3: Model And Feature Improvements

| Status | Experiment | Change | Why |
| --- | --- | --- | --- |
| pending | PPO-WIDER-ACTOR | Increase row encoder or actor width | Test whether the current policy is capacity-limited. |
| pending | PPO-FEAT-PRICE-LOW | Add one new scale-free price feature such as distance to 3m low | Improve ranking signal without violating the canonical data rules. |
| pending | PPO-FEAT-MOM | Add benchmark-relative momentum style feature | Test whether trend information improves risk ordering. |

## How To Update This Sheet

After each real run:

1. add one row to `outputs/experiments/setup_results.csv`
2. copy the headline metrics into the `Recorded Runs` table
3. update `Current Best Run` if validation mean reward improved
4. move completed ideas from `Pending Experiments` into `Recorded Runs`
5. add any new follow-up runs suggested by the results
