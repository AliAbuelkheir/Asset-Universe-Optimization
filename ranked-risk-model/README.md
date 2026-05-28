# RL Asset Risk Scoring

This repository implements a variable-universe, month-level RL asset risk
scorer over the Egyptian market.

The active system is built around:

- one canonical long monthly panel with one row per `(Date, AssetID)`
- one shared PPO policy that scores every active asset row in a month
- one month-level reward after the full active universe is scored
- one cleaned daily reference file that preserves price, OHLC, volume, and raw
  vendor change data

## Active Pipeline

1. clean and standardize raw market files
2. derive authoritative returns from cleaned prices
3. build the canonical monthly panel directly
4. train and evaluate the PPO agent from that panel
5. compare top candidates with the tuned PPO setup

Current project phase:

- evaluation and reporting design for the thesis
- future investor-facing selection and web serving are deferred

## Current Implementation Status

Implemented now:

- `src/data_processing/build_model_dataset.py` builds the canonical daily and
  monthly datasets
- `src/data_processing/validate_model_dataset.py` checks the generated outputs
  against the repository contract
- `src/environment/asset_risk_env.py` exposes single-month RL episodes over the
  canonical monthly panel
- `src/training/policy.py` defines the masked shared-scorer PPO policy
- `src/training/train.py` trains PPO and exports experiment artifacts
- `src/training/evaluate.py` evaluates PPO checkpoints on ordered monthly
  batches
- `src/training/tune_ppo.py` runs PPO hyperparameter searches
- `src/training/top_candidate_reruns.py` reruns top feature/model candidates
  with the selected tuned PPO parameters
- `src/training/promote_best_model.py` overwrites `outputs/best_model/` with
  the promoted current-best artifact
- `src/training/portfolio_evaluation.py` runs the thesis risk-bucket
  evaluation and bucket-method comparison
- `tests/test_data_engineering_pipeline.py` covers feature correctness and
  leakage prevention
- `tests/test_training_pipeline.py` covers PPO initialization, masking, split
  integrity, evaluation, and artifact writing

Current best model:

- `downside_tail_ratio_3m + refined50`
- framework: `pit_3m_flat_context`
- selected by three-seed validation high-risk overlap improvement with
  validation reward and Spearman guardrails
- canonical defaults remain `full_current_v1`

The authoritative current-best record is in
[docs/project_guide.md](docs/project_guide.md).

## Canonical Outputs

- `data/ready/daily_market_series.csv`
- `data/ready/monthly_asset_panel.csv`
- `outputs/best_model/`

The monthly panel keeps metadata for grouping and alignment while feeding only
the canonical feature columns into the policy.

`outputs/best_model/` is the only repo-visible model artifact directory and is
overwritten on every best-model promotion. All other generated runs, candidate
datasets, and reports belong under ignored `outputs/generated/`.

Current model features:

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

Current-best additive feature:

- `downside_tail_ratio_3m`

Current realized targets:

- `realized_vol`
- `realized_downside_dev`
- `realized_max_drawdown`
- `realized_risk`
- `realized_rank`

## Build And Validate

```powershell
.\.venv\Scripts\python.exe src\data_processing\build_model_dataset.py
.\.venv\Scripts\python.exe src\data_processing\validate_model_dataset.py
.\.venv\Scripts\python.exe -m pytest tests
```

## Train And Evaluate PPO

```powershell
.\.venv\Scripts\python.exe src\training\train.py --setup-id PPO-CANONICAL --framework-id pit_3m_flat_context --study-phase feature_comparison --total-timesteps 4096
.\.venv\Scripts\python.exe src\training\evaluate.py --checkpoint-path outputs\generated\runs\experiments\PPO-CANONICAL\best_model.zip --framework-id pit_3m_flat_context --output-dir outputs\generated\runs\experiments\PPO-CANONICAL\reevaluation --split-name all
```

## Top Candidate Reruns

```powershell
.\.venv\Scripts\python.exe -m src.training.top_candidate_reruns --tuned-candidate refined50 --seeds 42 7 13 --total-timesteps 32768
```

## Thesis Portfolio Evaluation

```powershell
.\.venv\Scripts\python.exe -m src.training.portfolio_evaluation
```

This generates an equal-weight downstream simulation comparing the full active
universe with candidate low-, medium-, and high-risk bucket methods under
`outputs/generated/reports/portfolio_evaluation/`.

## Testing Policy

- `validate_model_dataset.py` is the fast contract validator for generated CSVs.
- The pytest suite is the stronger gate for feature correctness, target
  correctness, split integrity, and leakage prevention.
- Data-engineering tests must protect against any future leakage from later
  months, benchmark edits, or macro revisions.
- Training tests must protect against mask leakage, split misuse, and accidental
  reintroduction of non-RL training paths.
- Investor-facing selection and future web/API serving must stay outside the
  PPO training path.

## Documentation

- [AGENTS.md](AGENTS.md) is the main repository contract
- [docs/README.md](docs/README.md) is the documentation index
- [docs/framework_phase.md](docs/framework_phase.md)
  tracks framework methodology, tested frameworks, and the locked framework
  conclusion
- [docs/feature_phase.md](docs/feature_phase.md)
  tracks feature-phase planning, ablations, and feature decisions
- [docs/ppo_tuning_phase.md](docs/ppo_tuning_phase.md)
  tracks PPO tuning methodology and parameter sweeps after the feature phase
- [docs/project_guide.md](docs/project_guide.md)
  is the compact technical guide for the data contract, PPO setup, and
  leakage rules
- [docs/papers.md](docs/papers.md)
  is the literature tracker

If wording conflicts across markdown files, `AGENTS.md` is the source of truth.
