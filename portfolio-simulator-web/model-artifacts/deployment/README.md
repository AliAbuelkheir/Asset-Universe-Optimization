# Egyptian Portfolio Allocator — Deployment Package

PPO-based monthly portfolio allocation across 3 risk tiers for the Egyptian market. **Dynamic n_assets**: each tier's model accepts any subset of its training universe (or any superset, with the OOD caveat noted in `INTEGRATION_GUIDE.md`).

## Quickstart

```bash
pip install -r requirements.txt
python examples/run_example.py
```

Expected output: a table of 5 assets with weights summing to ~1.0.

## Folder structure

```
deployment/
├── README.md                   ← you are here
├── INTEGRATION_GUIDE.md        ← full developer manual (8 sections)
├── requirements.txt
│
├── models/                     ← trained PPO models (1 per tier)
├── data/                       ← bundled macro Excel files
├── egtportfolio/               ← the Python package
└── examples/                   ← sample input + expected output + runnable demo
```

## Three-line summary for the integrator

1. **Input**: tier + target month + list of asset OHLCV time series
2. **Output**: monthly weights summing to 1.0 (long-only, capped per tier)
3. **Cadence**: call once per month, on the last trading day before the target month

Read `INTEGRATION_GUIDE.md` for everything else.
