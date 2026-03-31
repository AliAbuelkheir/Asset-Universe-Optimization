# Architecture And Pipeline

This file is the shortest end-to-end explanation of the current architecture
and what is implemented from `rawData/` to the model-ready monthly batches.

## 0. Current Architecture

The repository currently follows a variable-universe monthly risk-scoring
design.

- One shared scorer is applied to every active asset row in a month.
- The stored model-facing dataset is a long monthly panel, not a fixed-width
  asset matrix.
- One RL step equals one month.
- Reward is computed only after scoring the full active universe for that month.
- The current output is a comparable monthly risk score and ranking across the
  available assets.

Important scope boundaries:

- investor-tier selection logic is not implemented yet
- downstream allocation is not implemented yet
- pairwise correlation features are out of scope
- bucketing/grouping after scoring is still an open design layer, not part of
  the current data pipeline

## 1. Raw Inputs

The builder reads canonical raw files from `rawData/`.

Scored asset series:

- base assets:
  `MoneyMarket.csv`, `Bonds.csv`, `EGX30.csv`, `REIT.csv`, `Gold.csv`
- EGX30 constituent stocks:
  all stock CSVs listed in `Stocks_Starting_Years.csv`

Benchmark usage:

- `EGX30` is the benchmark proxy for Egyptian equity exposure, including ETFs
  and mutual funds built around the local equity market.
- `Gold` is the benchmark proxy for gold exposure in all forms, including gold
  funds and other gold-linked vehicles.

Macro series:

- `USD_1.csv`
- `USD_2.csv`
- `CPI.csv`

Metadata source:

- `Stocks_Starting_Years.csv`

## 2. Main Implemented Builder

Implemented entrypoint:

- [build_model_dataset.py](/C:/Ali/CS/Bachelor%20thesis/src/data_processing/build_model_dataset.py)

Optional checker:

- [validate_model_dataset.py](/C:/Ali/CS/Bachelor%20thesis/src/data_processing/validate_model_dataset.py)

Build command:

```powershell
.\.venv\Scripts\python.exe src\data_processing\build_model_dataset.py
```

## 3. What The Builder Does

For every market CSV:

1. read `Date`, `Price`, `Vol.`, and `Change %`
2. parse `Price` into numeric `QuotedValue`
3. parse `Vol.` into numeric `Volume`
4. parse `Change %` into numeric `ChangePctRaw`
5. reverse to chronological order
6. drop duplicate dates

Special handling:

- `MoneyMarket` and `Bonds` are treated as yield series, so the quoted values
  are converted into `PriceForReturn` before returns are calculated.
- `USD_1.csv` and `USD_2.csv` are concatenated and deduplicated into one USD
  time series.
- `CPI.csv` is cleaned by removing the leading blank row and trailing note rows.

Gap handling:

- the trading calendar is EGX Sunday-Thursday
- `PriceForReturn` is forward-filled only for small gaps, up to 5 trading days
- `Volume` and `ChangePctRaw` are not forward-filled
- pre-listing history is never created

## 4. Daily Output

Implemented output:

- [daily_market_series.csv](/C:/Ali/CS/Bachelor%20thesis/data/ready/daily_market_series.csv)

This is the cleaned daily reference table.

Important columns:

- `QuotedValue`:
  cleaned vendor price/yield quote
- `PriceForReturn`:
  the value actually used for return calculation
- `Volume`:
  cleaned numeric market volume
- `ChangePctRaw`:
  vendor raw change percentage kept only for QA/reference
- `ReturnFromPrice`:
  the authoritative return series
- `IsObserved`:
  `1` for observed rows, `0` for EGX-calendar synthetic forward-filled rows

## 5. Monthly Feature/Target Build

Implemented output:

- [monthly_asset_panel.csv](/C:/Ali/CS/Bachelor%20thesis/data/ready/monthly_asset_panel.csv)

This is the only canonical model-facing dataset.

For decision month `t`:

- features use the trailing 3 full months ending at `t-1`
- targets use realized daily returns inside month `t`

Asset-level features:

- `egarch_vol`
- `downside_dev`
- `max_drawdown`
- `volume`

Macro features:

- `usd_vol`
- `cpi_trajectory`

Targets:

- `realized_egarch_vol`
- `realized_downside_dev`
- `realized_max_drawdown`
- `realized_risk`
- `realized_rank`

`volume` is built from observed daily `Volume` over the configured trailing
lookback window. With the current settings that means the prior 3 full months
ending at `t-1`. If an asset has no vendor volume in that window, the raw
volume feature defaults to `0` before monthly cross-sectional ranking.

`egarch_vol` and `realized_egarch_vol` are built with strict month-level
walk-forward EGARCH. For any month `m`, the EGARCH fit may only use returns
available through the end of month `m`, which removes the earlier full-history
leakage.

## 6. What The Model Actually Reads

The model does not read raw files directly.

It reads one month at a time from `monthly_asset_panel.csv`.

At month `t`:

1. filter rows where `Date == t`
2. keep metadata only for grouping/alignment
3. remove metadata and target columns from the model input
4. feed only feature columns into the scorer
5. score all active assets for that month
6. compare predictions against `realized_risk`
7. compute one month-level reward

## 7. Iteration Logic

One environment step equals one month.

That means the runtime loop is:

1. load month `t`
2. score all active assets in month `t`
3. rank them by predicted risk
4. compute reward for month `t`
5. move to month `t+1`

This is why the data is stored in long format instead of a fixed asset-column
matrix.

## 8. Bucketing And Grouping Status

The bucketing/grouping mechanism is not finalized yet.

What is already fixed:

- the model batch unit is one month
- the active asset universe can change by month
- metadata stays outside the model input and is used for grouping and reward
- reward is computed at the month level after full-batch scoring

Open design questions:

- how investor-facing buckets should be defined after risk scores are produced
- whether bucketing should be threshold-based, rank-based, or relative to the
  active universe
- whether group outputs should be stable across months or adaptive by month
- how bucketing should behave when the active universe is very small

Current recommendation:

- keep bucketing out of the v1 training/data pipeline
- finish reliable monthly scores and rankings first
- add bucketing as a layer on top of scored/ranked outputs later
