# Integration Guide — Egyptian Tier-Based Portfolio Allocator

**Package**: `egtportfolio` v0.1.0
**Models**: PPO with set-based architecture, 3 tiers (low / medium / high)
**Purpose**: Given a list of assets and recent OHLCV history, return a recommended monthly portfolio allocation.

---

## TL;DR — 30 seconds to first prediction

```python
import json
from egtportfolio import load_model, predict, request_from_dict

with open('examples/sample_input_raw_ohlcv.json') as f:
    request = request_from_dict(json.load(f))

bundle = load_model(tier='low', n_assets=len(request.asset_data))
result = predict(request, model_bundle=bundle)

for w in result.asset_weights:
    print(f'{w.asset}: {w.weight:.1%}')
```

---

## 1. Model artifact files and loader code

### Files in the package
- `models/ppo_<tier>_seed42_setbased.zip` — PPO policy weights (3 tiers)
- `models/vecnorm_<tier>_seed42_setbased.pkl` — VecNormalize observation statistics
- `egtportfolio/feature_extractor_setbased.py` — `SetBasedFeatureExtractor` class (required to load `.zip`)
- `egtportfolio/policy_setbased.py` — `SetBasedActorCriticPolicy` class (required to load `.zip`)
- `egtportfolio/env_min.py` — `PortfolioEnvMin` providing observation construction and the `_masked_softmax` weight projection

### Loader
```python
from egtportfolio import load_model

bundle = load_model(
    tier='low',          # 'low' | 'medium' | 'high'
    n_assets=5,          # number of assets in your deployment universe
    model_dir=None,      # optional override; defaults to <package>/../models/
)
```

`bundle.model` is a `stable_baselines3.PPO` instance. `bundle.vecnormalize` is a `VecNormalize` wrapping a minimal env. Both are cached per-call so reuse `bundle` for multiple `predict()` calls.

### Internals (FYI)
The loader handles a SB3 quirk where `PPO.load(env=...)` strictly checks observation/action spaces. When deployment N differs from training N, the loader silently falls back to a manual state-dict load with `strict=False` and skips any shape-mismatched parameters. In practice, all set-based parameters (Conv1D, per-asset MLP, scalar log_std) are size-agnostic, so nothing is actually skipped.

---

## 2. Python and package versions

| Package | Version | Required for |
|---|---|---|
| Python | 3.11 - 3.13 (tested on 3.13.3) | All |
| torch | ≥ 2.6.0, < 3.0 | PPO inference |
| stable-baselines3 | ≥ 2.5.0, < 3.0 | PPO API |
| gymnasium | ≥ 1.0.0, < 2.0 | env API |
| pandas | ≥ 2.2, < 4.0 | data loading |
| numpy | ≥ 1.24, < 3.0 | math |
| openpyxl | ≥ 3.1, < 4.0 | reading bundled macro Excel files |

Install with:
```bash
pip install -r deployment/requirements.txt
```

CPU inference is sufficient (each `predict()` call is < 100ms on a modern laptop CPU). GPU is supported automatically if PyTorch was installed with CUDA.

---

## 3. Required input schema

The input is an `InferenceRequest` (Python dataclass or equivalent JSON dict):

```python
{
    "tier": "low",                         # required: 'low' | 'medium' | 'high'
    "target_month": "2025-08",             # required: 'YYYY-MM'
    "input_kind": "raw_ohlcv",             # optional: 'raw_ohlcv' | 'precomputed_features' | null (auto-detect)
    "asset_data": [                        # required: list of AssetTimeSeries
        {
            "asset": "Gold",                 # required: string identifier (any name)
            "dates": ["2024-11-01", ...],    # required: ISO YYYY-MM-DD, daily
            "close": [3000.0, ...],          # required
            "open":  [2995.0, ...],          # optional, falls back to close
            "high":  [3015.0, ...],          # optional, falls back to close
            "low":   [2990.0, ...],          # optional, falls back to close
            "volume": [100000, ...]          # optional
        },
        ...
    ],
    "egx30_ohlcv": {                       # optional but recommended: EGX30 daily prices for rolling_beta_60
        "asset": "EGX30",
        "dates": [...],
        "close": [...]
    },
    "constraints_override": {              # optional: override the tier's defaults
        "max_weight": 0.40,
        "min_weight": 0.02
    }
}
```

**Critical**: `asset_data` for each asset must contain **≥ 123 trading days** before `target_month` starts:
- 63 days for the model's lookback window
- 60 days for the longest rolling feature (rolling_vol_60, rolling_sharpe_60, rolling_beta_60, max_drawdown_60)

If you provide fewer days, `predict()` raises `ValueError` with a clear message.

**Risk group → tier**: the developer picks `tier` based on the risk profile they want to expose to the user:
- `low` → bond + gold + defensive equity tier (max 30% per asset)
- `medium` → balanced tier with EGX30 + Gold + ~10 equities (max 20% per asset)
- `high` → cyclical / growth tier with 16 high-vol equities + Gold + EGX30 (max 15% per asset)

---

## 4. What the model expects: raw vs pre-computed

The package accepts **both** input forms:

### A) Raw OHLCV (recommended for most integrators)
Pass each asset's daily OHLCV in `asset_data`. The package will internally:
1. Compute the 18 technical features (returns, volatility, Sharpe, RSI, MACD, Bollinger, ADX, CCI, beta-vs-EGX30, max drawdown, daily range, price-to-SMA)
2. Attach 4 macro features (inflation × 2, interest rates × 2) from bundled Excel data
3. Cross-sectionally z-score per day
4. Build the (lookback=63, N_assets, 22+1) observation tensor
5. Run `model.predict()` and apply the Dirichlet-mean weight projection

Set `input_kind` to `"raw_ohlcv"` or leave it `null` to auto-detect.

### B) Pre-computed feature CSV
If you have the 18 features already (same shape as `low_risk_dataset_final.csv`), pass a CSV path as `asset_data` and set `input_kind` to `"precomputed_features"`. The CSV must have columns `Date, Asset, is_active, Close` plus the 18 RL feature names listed in `egtportfolio.features.RL_FEATURE_NAMES`.

### Internal flow
```
asset_data (raw OHLCV)
    ↓ compute_features_for_universe()
features per asset (18 cols)
    ↓ + macro broadcast (4 cols)
feature tensor (T, N, 22)
    ↓ cross_sectional_zscore()
normalized tensor (T, N, 22)
    ↓ + weight channel
observation tensor (T, N, 23)
    ↓ model.predict()
action logits (N,)
    ↓ _masked_softmax()
final weights (N,) — sum to 1.0, each in [min_weight, max_weight]
```

---

## 5. Output weight schema and ordering

```python
{
    "tier": "low",
    "target_month": "2025-08",
    "decision_date": "2025-07-31",        # last trading day before target_month
    "lookback_window": 63,                # how many days of history were used
    "asset_weights": [                    # SORTED by weight DESCENDING
        {"asset": "Eastern_Tobacco", "weight": 0.245},
        {"asset": "Gold",             "weight": 0.198},
        ...
    ],
    "cash_position": 0.0,                 # always 0 (long-only, fully invested)
    "sum_check": 1.0000003,               # sanity check, should be ≈ 1.0 (float error)
    "constraints_applied": {              # what min/max/etc. were enforced
        "max_weight": 0.30,
        "min_weight": 0.0,
        "dirichlet_prior": 0.2,
        "long_only": true,
        "leverage": false,
        "sum_to_one": true
    },
    "model_version": "setbased_seed42",
    "package_version": "0.1.0"
}
```

**Asset ordering**: the output's `asset_weights` list is **sorted by weight descending**. The asset names returned match exactly what the developer passed in (we do not impose alphabetical or any other canonical order — the developer's labels are preserved).

If you need to JOIN the output back to your portfolio data, use the `asset` field as the join key, not list position.

---

## 6. Constraints

| Constraint | Default | Override? | Notes |
|---|---|---|---|
| **Long-only** (no shorting) | ✅ enforced | NO — architectural | The Dirichlet-mean projection always produces `weight ≥ 0`. The model cannot output short positions. |
| **Min weight floor** | LOW: 0.0, MED: 0.01, HIGH: 0.01 | ✅ via `constraints_override.min_weight` | If you set 0.02, every active asset gets at least 2%. |
| **Max weight cap** | LOW: 0.30, MED: 0.20, HIGH: 0.15 | ✅ via `constraints_override.max_weight` | Forces diversification. Setting > 1.0 effectively disables the cap. |
| **Weights sum to 1.0** | ✅ enforced | NO — architectural | After min/max enforcement, weights are re-normalized so `sum_check ≈ 1.0`. |
| **No leverage** | ✅ enforced | NO — architectural | Because `sum_check = 1.0`, total exposure is exactly 100% of NAV. |
| **No cash position** | `cash_position: 0.0` | NO — architectural | All 100% of NAV is allocated across the input universe. If you want a cash buffer, scale the output weights by `(1 - cash_pct)` on your side. |

### How to inject a cash position from your side
The package always returns weights summing to 1.0 across the input assets — there's no separate "cash" output. If your application needs a cash position, post-process:

```python
result = predict(request, model_bundle=bundle)
cash_pct = 0.10  # 10% cash
for w in result.asset_weights:
    w.weight *= (1 - cash_pct)
# Cash weight: cash_pct
```

---

## 7. Rebalance and forward holding-period assumption

- **Training**: daily resolution (each PPO step = 1 trading day)
- **Deployment**: **monthly** (the model produces one set of weights for the entire target month)

### Recommended call pattern
- Call `predict()` **once per month**, on the **last trading day of the previous month**
- Use `target_month='YYYY-MM'` to specify the month the weights apply to
- The returned `asset_weights` are intended to be held for the full target month
- The model was specifically trained to be evaluated this way — daily rebalancing inflates turnover by ~3× without improving Sharpe

### What happens within the month
The package does NOT simulate weight drift. The returned weights are the **target** allocation at the start of the month. In production:
- Day 1 of target_month: allocate exactly per the returned weights (after your platform's slippage and TC)
- Days 2-N of target_month: weights drift naturally with prices (you do nothing)
- Last day of target_month: call `predict()` again with `target_month=next_month` for the next rebalance

### Forward-looking horizon
The model is optimized for **1-month forward Sharpe ratio** with mean-variance regularization. It does not target longer or shorter holding periods. Holding weights for > 1 month without rebalance degrades performance roughly linearly.

---

## 8. Sample input and expected output

Two examples are provided in `examples/`:

- `examples/sample_input_raw_ohlcv.json` — 5 assets, 195 trading days, target month 2025-08, raw OHLCV format. The 5 assets are `Gold`, `TBills`, `Eastern_Tobacco`, `Commercial_Int_Bank`, `Edita_Food` (a subset of the LOW universe).
- `examples/expected_output.json` — the expected `InferenceResponse` for that input. **Run `python examples/run_example.py` to regenerate or verify.**

### Running the example
```bash
cd deployment/
python examples/run_example.py
```

Expected output (truncated):
```
Loaded request: tier=low, target=2025-08, n_assets=5
Loaded low set-based model (max_weight=0.3, min_weight=0.0, dirichlet_prior=0.2)

Decision date: 2025-07-31
Target month:  2025-08
Sum check:     1.000000

  Asset                       Weight
  -----------------------------------
  Eastern_Tobacco              30.0%  #########
  TBills                       30.0%  #########
  Gold                         15.4%  ####
  Commercial_Int_Bank          14.2%  ####
  Edita_Food                   10.4%  ###

Max weight delta vs expected: 0.00e+00
  OK — reproducible within 1e-3 tolerance
```

### Round-trip JSON
```python
import json
from egtportfolio import predict, request_from_dict

# Receive JSON from your HTTP layer
request_json = '{"tier": "low", "target_month": "2025-08", "asset_data": [...]}'
request = request_from_dict(json.loads(request_json))

# Predict
result = predict(request)

# Send result back as JSON
result_json = json.dumps(result.to_dict())
```

---

## Error handling

The package raises:
- `ValueError` — input validation (bad tier, dates length mismatch, < 123 days of history)
- `FileNotFoundError` — missing model files or bundled macro Excel files
- `RuntimeError` — torch / SB3 issues (rare; usually a version mismatch)

The package does NOT silently produce zero or garbage weights. If your input is malformed, you'll get an explicit error.

---

## Out-of-distribution warning

The set-based architecture is N-invariant, but the **policy learned patterns specific to Egyptian market dynamics 2010-2023**. If you call it with assets from a different market (e.g., US stocks) or completely different asset classes (e.g., crypto), the weights may be unreasonable. The package will run without errors but the output is not guaranteed to be sensible.

Recommended usage:
- ✅ Subset of the original training universe (e.g., 5 of LOW's 10 assets)
- ✅ New Egyptian stocks similar in volatility to the training universe
- ⚠️ Assets from other emerging markets with similar characteristics
- ❌ Crypto, US large-caps, or any asset class wildly outside training distribution

---

## Refresh procedure

The bundled macro data in `data/` covers training period (2010-2026). To use the package beyond 2026:

1. Download fresh `Inflations Historical.xlsx` and `Monthly Interest Rates Historical.xlsx` from the Central Bank of Egypt
2. Drop them into `deployment/data/` (overwrite the bundled copies)
3. Verify with `python -c "from egtportfolio.macro import latest_macro_date; print(latest_macro_date(Path('deployment/data')))"`

The model weights themselves do not need to change. The macro features are aligned monthly at inference time.

---

## Support

- `egtportfolio.__version__` for the package version
- `bundle.model.policy` for full PyTorch model inspection
- Model training reference: `src/train.py` in the source repo (see `docs/19_architecture_walkthrough.md` for full architecture details)
