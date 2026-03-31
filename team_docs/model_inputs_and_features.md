# Model Inputs And Features

This file lists the raw inputs, cleaned fields, engineered features, and the
exact columns the model uses versus the columns it ignores.

## Raw Input Sources

Scored market series:

- `MoneyMarket.csv`
- `Bonds.csv`
- `EGX30.csv`
- `REIT.csv`
- `Gold.csv`
- all stock CSVs referenced by `Stocks_Starting_Years.csv`

Benchmark interpretation:

- `EGX30` is used as the benchmark representation for ETFs and mutual funds
  tied to Egyptian equity exposure.
- `Gold` is used as the benchmark representation for gold exposure in all
  forms, including gold funds and similar products.

Macro inputs:

- `USD_1.csv`
- `USD_2.csv`
- `CPI.csv`

Metadata input:

- `Stocks_Starting_Years.csv`

## Cleaned Daily Fields

Stored in:

- [daily_market_series.csv](/C:/Ali/CS/Bachelor%20thesis/data/ready/daily_market_series.csv)

Columns:

- `Date`
- `AssetID`
- `AssetName`
- `AssetGroup`
- `QuotedValue`
- `PriceForReturn`
- `Volume`
- `ChangePctRaw`
- `ReturnFromPrice`
- `IsObserved`

Meaning:

- `QuotedValue` is the cleaned vendor quote
- `PriceForReturn` is the series used for return calculation
- `Volume` is the cleaned daily turnover field used to derive the monthly
  `volume` model feature
- `ChangePctRaw` is vendor raw change and is not authoritative
- `ReturnFromPrice` is the authoritative return

## Engineered Monthly Feature Columns

Stored in:

- [monthly_asset_panel.csv](/C:/Ali/CS/Bachelor%20thesis/data/ready/monthly_asset_panel.csv)

### Model Input Columns

These are the only columns fed into the scorer:

- `egarch_vol`
- `downside_dev`
- `max_drawdown`
- `volume`
- `usd_vol`
- `cpi_trajectory`

### Feature Definitions

- `egarch_vol`
  asset-level volatility feature built from strict walk-forward EGARCH month
  summaries over the trailing 3 full months ending at `t-1`
- `downside_dev`
  asset-level downside deviation over the trailing 3 full months ending at
  `t-1`
- `max_drawdown`
  asset-level maximum drawdown over the trailing 3 full months ending at `t-1`
- `volume`
  asset-level trailing observed trading volume over the configured lookback
  window (`WINDOW_MONTHS`, currently 3 full months ending at `t-1`), built
  from daily `Volume` and defaulted to `0` when no vendor volume exists in the
  window
- `usd_vol`
  macro USD/EGP volatility built from USD daily returns over the trailing
  3 full months ending at `t-1`
- `cpi_trajectory`
  macro CPI movement over the trailing 3 full months ending at `t-1`

## Columns Present But Not Used As Model Inputs

Metadata columns:

- `Date`
- `AssetID`
- `AssetName`
- `AssetGroup`

Target columns:

- `realized_egarch_vol`
- `realized_downside_dev`
- `realized_max_drawdown`
- `realized_risk`
- `realized_rank`

These stay in the dataset for:

- grouping by month
- aligning predictions back to assets
- computing reward
- inspecting evaluation results

## Current Target Construction

For month `t`, targets are built from realized daily returns inside month `t`.

Realized columns:

- `realized_egarch_vol`
- `realized_downside_dev`
- `realized_max_drawdown`

`realized_egarch_vol` uses the month `t` walk-forward EGARCH summary only, so
it does not see months after `t`.

Final target:

- `realized_risk`

Auxiliary ranking column:

- `realized_rank`

## Runtime Batch Logic

For month `t`:

1. filter all rows where `Date == t`
2. drop metadata and target columns
3. score every active asset row with one shared scorer
4. join predictions back to `AssetID`
5. rank assets from low to high predicted risk

Output for each month:

- one predicted risk score per active asset
- one ranked monthly list of assets by predicted risk

Reward:

`0.7 * SpearmanRankCorr(predicted, realized) + 0.3 * (1 - MSE)`

Rules:

- reward uses only active assets in that month
- months with fewer than 3 active assets are skipped
- asset identity never enters the model input tensor

## Current Runtime View

For a given month `t`, the runtime model input is effectively:

```text
[egarch_vol, downside_dev, max_drawdown, volume, usd_vol, cpi_trajectory]
```

for every active asset row in that month.

The model never sees:

- asset name
- asset id
- asset group
- realized target columns

## Important Notes

- daily `Volume` is preserved in the cleaned daily data and is rolled into the
  monthly `volume` model feature.
- `ChangePctRaw` is preserved only as a QA/reference field.
- `ReturnFromPrice` is the return source used for feature and target
  engineering.
- the monthly panel is long format because the active universe changes by month.
