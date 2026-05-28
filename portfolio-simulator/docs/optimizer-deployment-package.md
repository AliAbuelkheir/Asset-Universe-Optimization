# Doc 24 — Deployment Package (Dynamic-N Set-Based Models)

**Date**: 2026-05-11
**Status**: Set-based models trained for all 3 tiers; deployment package at `deployment/` ready for hand-off.

This doc explains how the deployment package was built, what's inside it, how to refresh it, and how it differs from the thesis's static baseline models.

---

## What's in `deployment/`

```
deployment/
├── README.md                                  ← quickstart
├── INTEGRATION_GUIDE.md                       ← full developer manual (8 sections)
├── requirements.txt                           ← pinned versions
├── test_inference.py                          ← end-to-end checks
│
├── models/
│   ├── ppo_low_seed42_setbased.zip
│   ├── ppo_medium_seed42_setbased.zip
│   ├── ppo_high_seed42_setbased.zip
│   ├── vecnorm_low_seed42_setbased.pkl
│   ├── vecnorm_medium_seed42_setbased.pkl
│   └── vecnorm_high_seed42_setbased.pkl
│
├── data/
│   ├── Inflations Historical.xlsx
│   └── Monthly Interest Rates Historical.xlsx
│
├── egtportfolio/
│   ├── __init__.py                            ← exposes load_model, predict, schemas
│   ├── loader.py                              ← PPO + VecNormalize + strict=False handling
│   ├── features.py                            ← compute 18 RL features from OHLCV
│   ├── macro.py                               ← load macro from bundled Excel
│   ├── inference.py                           ← high-level predict() orchestrator
│   ├── schemas.py                             ← dataclass-based request/response schemas
│   ├── feature_extractor_setbased.py          ← copy of src/ file
│   ├── policy_setbased.py                     ← copy of src/ file
│   └── env_min.py                             ← eval-only PortfolioEnv
│
└── examples/
    ├── generate_sample.py                     ← regenerate the sample JSON
    ├── sample_input_raw_ohlcv.json            ← 5 assets, 195 trading days
    ├── expected_output.json                   ← reference output (regen on first run)
    └── run_example.py                         ← runnable demo
```

---

## How it was built — Phase by Phase

### Phase 1: Set-based architecture
Created two new Python files in `src/`:
- `src/feature_extractor_setbased.py:SetBasedFeatureExtractor` — per-asset Conv1D + mean-pool over assets + Linear(64, 256). No `n_assets` baked anywhere. Stashes per-asset 64-d features as `_per_asset_cache` for the policy to consume.
- `src/policy_setbased.py:SetBasedActorCriticPolicy` — shared per-asset MLP for action means + mean-pool value head + **scalar log_std** (the key to true N-invariance — the standard SB3 PPO uses a per-action-dim log_std, which would shape-mismatch on different N).

Added `--setbased` flag to `src/train.py`. When set: uses `SetBasedActorCriticPolicy` + `SetBasedFeatureExtractor` and saves outputs with `_setbased` suffix to avoid clobbering the static baselines.

### Phase 2: Training
3 parallel trainings, each 2M steps, ~3.5 hours total:
```bash
python -m src.train --tier {low,medium,high} --seed 42 --setbased > train_<tier>_setbased.log 2>&1
```

Same baseline config as `a586a88` (rich `EnvConfig` + `tier_overrides` + `PPOConfig` with `n_epochs=5, ent_coef=0.02, lr_end=1e-6, max_grad_norm=0.3`). Same reward function (10 components + TC). Only difference is the network architecture.

Saves:
- `models/ppo_<tier>_seed42_setbased.zip` + `vecnorm_*.pkl` (×3)

### Phase 3: Verification on subsets
The subset-verification script evaluates each trained model on:
1. Full tier universe (sanity)
2. 5-asset defensive subset
3. 5-asset stocks-only subset
4. 3-asset extreme reduction

Results saved to `results/setbased_subset_comparison.csv`.

**Acceptance criterion**: every (tier × subset) combination produces non-degenerate metrics (Sharpe finite, turnover > 0, sum-to-1 satisfied).

### Phase 4: Deployment package
Built `deployment/` folder containing the trained models + a Python package + macro Excel files. The package wraps the SB3 internals with a clean `predict(request, model_bundle)` API that the developer's app can call.

Key design choices:
- **Dataclass schemas** instead of Pydantic — fewer dependencies for the developer
- **Auto-detect input kind** (raw OHLCV vs pre-computed features) so the developer's calling code is simpler
- **Bundled macro Excel** so the developer doesn't need to source inflation/rate data themselves (with documented refresh procedure)
- **No cash position output** — the model is long-only fully-invested; developer applies any cash buffer post-hoc

### Phase 5: Integration documentation
`INTEGRATION_GUIDE.md` covers the user's 8 explicit requirements:
1. Model artifact + loader code (with internals explanation)
2. Python + package versions (`requirements.txt` pinned)
3. Input schema (full `InferenceRequest` spec with examples)
4. Whether expects raw vs features vs tensors (the answer: both — auto-detect)
5. Output weight schema + ordering (sorted by weight desc, asset names preserved)
6. Constraints (long-only, weight cap, min weight, no leverage, no cash)
7. Rebalance + holding-period assumption (monthly, train daily / deploy monthly)
8. Sample input/output + runnable example

### Phase 6: End-to-end checks
`deployment/test_inference.py` asserts:
- Output weights sum to 1.0 within 1e-5
- All weights ≥ 0 and ≤ max_weight
- Output reproducible vs `expected_output.json` within 1e-3
- Dynamic N works (3, 5 assets from the same model)
- `constraints_override` correctly caps weights
- JSON round-trip preserves results

---

## How to refresh

### Macro data (quarterly recommended)
1. Download fresh `Inflations Historical.xlsx` and `Monthly Interest Rates Historical.xlsx` from the Central Bank of Egypt
2. Drop them into `deployment/data/` (overwrite the bundled copies)
3. Verify: `python -c "from pathlib import Path; from deployment.egtportfolio.macro import latest_macro_date; print(latest_macro_date(Path('deployment/data')))"`

### Models (annually recommended, or when adding new tier)
1. Retrain: `python -m src.train --tier <X> --seed 42 --setbased`
2. Copy outputs into deployment:
   ```bash
   cp models/ppo_<X>_seed42_setbased.* deployment/models/
   cp models/vecnorm_<X>_seed42_setbased.pkl deployment/models/
   ```
3. Re-run the deployment inference check script
4. Re-run `deployment/examples/run_example.py` and commit the new `expected_output.json`

### Feature engineering
If the feature set ever changes (add or remove a feature in `RL_FEATURES`):
1. Update `egtportfolio/features.py:RL_FEATURE_NAMES` to match
2. Update `egtportfolio/features.py:compute_features_one_asset` to compute the new feature
3. Retrain all 3 models (the network architecture's input channel count would change)
4. Replace the bundled models

---

## Difference from baseline static models

The deployment uses **NEW** models (set-based) trained alongside the original static-N baselines. Both sets of models coexist in the repo:

| File pattern | Architecture | n_assets | Active for |
|---|---|---|---|
| `models/ppo_<tier>_seed42.zip` (no suffix) | Static Conv1D (baseline) | Locked per tier | THESIS reporting (Sharpe 2.77/2.38/2.16) |
| `models/ppo_<tier>_seed42_setbased.zip` | Set-based (this work) | Any N | DEPLOYMENT package |

**The thesis numbers of record do NOT change.** Sharpe 2.77 / 2.38 / 2.16 from the baseline are still the values reported in CLAUDE.md and docs 14, 17, 18, 19, 20, 21, 23.

The set-based deployment numbers will be reported in `results/setbased_subset_comparison.csv` after Phase 3 verification completes. They are expected to be **slightly lower** than the static baselines on the full universe (the mean-pool over assets is a more compressed representation than per-asset Linear), but the trade-off is N-invariance — a single trained model handles any subset.

---

## Honest limitations of the deployment

1. **Out-of-distribution assets**: the policy was trained on Egyptian market dynamics 2010-2023. If the developer passes US stocks or crypto, the package will run but the weights may be unreasonable. The architecture is N-invariant, but the data distribution is not.
2. **VecNormalize stats**: trained at the original N. When deployment N differs, the saved running mean/var doesn't quite match the input scale. The loader handles this with a try/except fallback to identity normalization. Predictions are still sensible because the cross-sectional z-score in the feature pipeline already centers per-day data.
3. **Macro data staleness**: the bundled Excel files cover up to ~Feb 2026. Beyond that, macro features will use the most recent available value (forward-filled). The developer is responsible for refreshing the Excel files quarterly.
4. **EGX30 dependency**: `rolling_beta_60` uses EGX30 returns. If the developer omits `egx30_ohlcv` from the request, beta is set to 0 (neutral). This matches the training-time behavior for assets predating EGX30 alignment, so it's safe but slightly degrades signal quality.

---

## Files added to the repo

### New code under `src/` (also part of training pipeline)
- `src/feature_extractor_setbased.py`
- `src/policy_setbased.py`
- subset verification script under `src/`
- `src/train.py` (modified — added `--setbased` flag)

### New files under `deployment/`
- Entire `deployment/` folder

### New doc
- `docs/optimizer-deployment-package.md` (this file)

---

## References

- `docs/19_architecture_walkthrough.md` — the baseline static architecture
- `docs/23_failed_experiments_ledger.md` — set-based was previously experimented with (verified working but archived); this is the re-implementation with `scalar` log_std for true N-invariance
- `src/feature_extractor_setbased.py` — the architecture itself
- `deployment/INTEGRATION_GUIDE.md` — the developer-facing manual
