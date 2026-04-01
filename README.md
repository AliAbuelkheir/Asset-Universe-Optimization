# RL Asset Risk Scoring

This repository contains a bachelor thesis project for a variable-universe,
month-level RL asset risk scorer over the Egyptian market.

The active system is built around:

- one shared scorer applied to every active asset row in a month
- one canonical long monthly panel with one row per `(Date, AssetID)`
- one month-level reward after the full active universe is scored
- one cleaned daily reference file that preserves price, OHLC, volume, and raw
  vendor change data

## Current Pipeline

The practical pipeline is:

1. clean and standardize raw market files
2. derive authoritative returns from cleaned prices
3. build the canonical monthly panel directly
4. train and evaluate from that panel

The project is currently focused on making the data contract reliable and
model-ready before deeper modeling work.

## Canonical Outputs

- `data/ready/daily_market_series.csv`
- `data/ready/monthly_asset_panel.csv`

The monthly panel keeps metadata for grouping but feeds only feature columns
into the scorer.

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

Current targets:

- `realized_vol`
- `realized_downside_dev`
- `realized_max_drawdown`
- `realized_risk`
- `realized_rank`

## Repository Layout

- `rawData/` stores the canonical source market data
- `data/ready/` stores canonical generated datasets
- `src/` contains the data-processing and modeling code
- `docs/` is the single documentation hub for plans, architecture notes, and
  references
- `outputs/` stores generated artifacts such as metrics and plots
- `thesis/` contains thesis-related source material

## Build And Validate

```powershell
.\.venv\Scripts\python.exe src\data_processing\build_model_dataset.py
.\.venv\Scripts\python.exe src\data_processing\validate_model_dataset.py
.\.venv\Scripts\python.exe -m pytest tests\test_data_engineering_pipeline.py
```

## Documentation

- [AGENTS.md](/C:/Ali/CS/Bachelor%20thesis/AGENTS.md) is the main repository contract
- [docs/README.md](/C:/Ali/CS/Bachelor%20thesis/docs/README.md) is the documentation index

If wording conflicts across markdown files, `AGENTS.md` is the source of truth.
