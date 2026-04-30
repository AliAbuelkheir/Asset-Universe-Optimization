# PPO Tuning Phase

## Purpose

This document is reserved for PPO hyperparameter work after the feature phase
is locked.

Current status:

- refined Optuna continuation and seed confirmations completed
- locked PPO tuning champion is `refined50`
- final tuned top-candidate rerun selected `drop_distance_to_3m_high`

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

Prepared full-run launcher:

```powershell
python -m src.training.tune_ppo
```

This command is a dry run only. It writes the launch plan under
`outputs/ppo_tuning/` and does not start trials.

When the feature set is locked and PPO tuning is explicitly opened, launch the
full Optuna run with:

```powershell
.\.venv\Scripts\python.exe -m src.training.tune_ppo --execute --n-trials 80 --total-timesteps 32768
```

Equivalent Windows launcher:

```powershell
.\scripts\run_ppo_tuning_full.bat
```

The default study uses `pit_3m_flat_context`, the active feature profile,
screening seed `42`, SQLite Optuna storage, and writes trial artifacts under
`outputs/ppo_tuning/ppo_full_run_after_feature_lock/`.

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
| 2026-04-29 | optuna_full_ordered_baseline | `PPO-OPTUNA-PPO_FULL_RUN_ORDERED_BASELINE-T0075-S42` | 0.7036 | 0.5997 | seed-42 winner | 80 trials: 77 complete, 3 failed unstable configs. Best params: `learning_rate=3.806e-4`, `n_steps=256`, `batch_size=256`, `n_epochs=5`, `clip_range=0.2259`, `ent_coef=0.00534`, `vf_coef=0.9964`, `max_grad_norm=0.3`. Beats ordered baseline `0.6814 / 0.5718`; confirm with seeds `7` and `13` before final lock. |
| 2026-04-29 | confirmation | `trial75`, `trial11` | 0.7001, 0.6983 | 0.5939, 0.5965 | trial75 provisional | Three-seed means over seeds `42`, `7`, and `13`. `trial75` keeps the reward lead; `trial11` has stronger Spearman but lower reward by more than the 0.001 tie band. |
| 2026-04-29 | refined_optuna | `PPO-OPTUNA-PPO_REFINED_ORDERED_BASELINE_V2-T0050-S42` | 0.7056 | 0.6017 | refined winner | Clean refined study: 102 trials recorded, 101 complete, 1 interrupted trial marked failed. Best params: `learning_rate=2.494e-4`, `n_steps=256`, `batch_size=256`, `n_epochs=10`, `clip_range=0.2990`, `ent_coef=0.00235`, `vf_coef=0.9024`, `max_grad_norm=0.3`. |
| 2026-04-29 | refined_confirmation | `refined50` | 0.7008 | 0.5950 | locked tuned config | Three-seed means beat `trial75` on validation reward and Spearman. Informational three-seed test means: reward `0.7406`, Spearman `0.6505`. |
| 2026-04-29 | gamma_gae_sensitivity | `refined50_gamma099_gae095`, `refined50_gamma0995_gae097`, `refined50_gamma100_gae095` | 0.7056 | 0.6017 | keep fixed | Seed-42 checks exactly matched `refined50`, consistent with the one-month episode design. Keep `gamma=1.0` and `gae_lambda=1.0`. |

## Final Top-Candidate Rerun

After PPO tuning, the top candidate matrix was rerun with `refined50` across
seeds `42`, `7`, and `13`.

Winner:

- `drop_distance_to_3m_high`

Three-seed means:

- validation reward = `0.7012`
- validation Spearman = `0.5954`
- test reward = `0.7449`
- test Spearman = `0.6565`

Selection used validation metrics only; test metrics are reporting evidence.
