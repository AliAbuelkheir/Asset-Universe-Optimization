# PPO Tuning Phase

## Purpose

This document is reserved for PPO hyperparameter work after the feature phase
is locked.

Current status:

- not active yet

## Entry Conditions

Do not start this phase until all of the following are true:

- the framework is locked
- the feature set is locked
- the active backbone is still `pit_3m_flat_context`
- the active feature profile is promoted from the feature phase

## Locked Starting Point

This is the PPO baseline that tuning must compare against:

- framework: `pit_3m_flat_context`
- reward: `0.7 * SpearmanRankCorr(predicted, realized) + 0.3 * (1 - MSE)`
- action distribution: `masked_sigmoid_gaussian`
- policy semantics version: `bounded_v2`
- learning rate: `1e-4`
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

## Methodology

Tuning rules:

- tune PPO only after feature work is closed
- keep the framework fixed while tuning PPO
- keep the feature profile fixed while tuning PPO
- validation reward is the primary metric
- validation Spearman is the secondary metric
- seed `42` is the screening seed
- seeds `7` and `13` are used only after a seed-42 tuning result beats the
  locked baseline on both validation reward and validation Spearman
- change one parameter family at a time before testing interactions

Suggested tuning order:

1. optimizer scale: `learning_rate`
2. rollout geometry: `n_steps`, `batch_size`
3. PPO update intensity: `n_epochs`, `clip_range`
4. exploration and value balance: `ent_coef`, `vf_coef`
5. stabilization: `max_grad_norm`
6. only revisit `gamma` and `gae_lambda` if there is a clear reason

Naming rules:

- baseline confirmation: `PPO-BASE-LOCKED-S<SEED>`
- tuning screen: `PPO-TUNE-<FAMILY>-<VARIANT>-S42`
- confirmation: same setup family with seeds `7` and `13`

## Planned Parameter Families

| Family | Current Value | Candidate Variants | Status | Notes |
| --- | --- | --- | --- | --- |
| `learning_rate` | `1e-4` | `5e-5`, `2e-4`, `3e-4` | blocked | Open only after features lock |
| `n_steps_batch_size` | `256 / 256` | `512 / 256`, `512 / 512`, `1024 / 256` | blocked | Keep episode semantics unchanged |
| `n_epochs` | `10` | `5`, `15` | blocked | Test only after rollout geometry is stable |
| `clip_range` | `0.2` | `0.1`, `0.15`, `0.25` | blocked | Compare with unchanged reward and masking |
| `ent_coef` | `0.01` | `0.0`, `0.005`, `0.02` | blocked | Watch ranking stability |
| `vf_coef` | `0.5` | `0.25`, `0.75`, `1.0` | blocked | Keep critic monthly-only |
| `max_grad_norm` | `0.5` | `0.3`, `1.0` | blocked | Stabilization pass only |
| `gamma_gae` | `1.0 / 1.0` | `0.99 / 0.95`, `0.995 / 0.97` | blocked | Lowest-priority family |

## Decision Log

| Date | Family | SetupID | Validation Reward | Validation Spearman | Decision | Notes |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |
