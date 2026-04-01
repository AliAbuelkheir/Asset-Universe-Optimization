# Data Engineering Plan

## Objective

Build the smallest practical data pipeline that produces:

1. one canonical cleaned daily market reference
2. one canonical model-ready monthly panel

The pipeline must support a variable asset universe without pre-listing
leakage and without maintaining a redundant family of intermediate CSVs.

## Entry Points

Primary builder:

- `src/data_processing/build_model_dataset.py`

Optional validator:

- `src/data_processing/validate_model_dataset.py`

The earlier multi-file `clean/returns/features/targets` split is no longer the
active contract.

## Raw Data Rules

- `rawData/` must stay canonical and deduplicated.
- Preserve true asset start dates.
- Do not create synthetic pre-listing history.
- Keep `Date`, `Price`, `Open`, `High`, `Low`, `Vol.`, and `Change %`.
- Parse OHLC numerics into floats.
- Parse `Vol.` into numeric `Volume`.
- Parse `Change %` into numeric `ChangePctRaw`.
- Treat `ChangePctRaw` as QA/reference only.
- Compute authoritative returns from cleaned prices after any required yield
  conversion.
- Concatenate and deduplicate `USD_1.csv` and `USD_2.csv`.
- Clean CPI from `CPI.csv` by removing the leading blank row and trailing
  notes.
- Treat benchmark series as canonical market proxies when direct fund-level
  histories are not modeled separately:
  `EGX30` for ETFs and mutual funds tied to Egyptian equities, and `Gold` for
  gold exposure in all forms.

## Canonical Outputs

Reference daily file:

- `data/ready/daily_market_series.csv`

Model-facing file:

- `data/ready/monthly_asset_panel.csv`

No other CSV family should be treated as canonical by default.

## Daily Market Series Contract

Required columns:

- `Date`
- `AssetID`
- `AssetName`
- `AssetGroup`
- `QuotedValue`
- `OpenQuotedValue`
- `HighQuotedValue`
- `LowQuotedValue`
- `PriceForReturn`
- `OpenPriceForRange`
- `HighPriceForRange`
- `LowPriceForRange`
- `Volume`
- `ChangePctRaw`
- `ReturnFromPrice`
- `IsObserved`

Rules:

- `QuotedValue` is the cleaned vendor close quote.
- `OpenQuotedValue`, `HighQuotedValue`, and `LowQuotedValue` are cleaned vendor
  OHLC audit fields.
- `PriceForReturn` equals cleaned price for normal price series.
- `PriceForReturn` is a fixed-maturity price proxy for `MoneyMarket` and
  `Bonds`.
- `OpenPriceForRange`, `HighPriceForRange`, and `LowPriceForRange` are stored
  in the same price space as `PriceForReturn`.
- EGX Sunday-Thursday alignment is used.
- Forward-fill is limited to `QuotedValue` and `PriceForReturn`, for up to 5
  trading days.
- OHLC audit fields, price-range fields, `Volume`, and `ChangePctRaw` are not
  forward-filled.
- `Volume` is preserved in the cleaned daily market series.
- `ReturnFromPrice` is the authoritative return field.

## Monthly Panel Contract

The final model-facing storage shape is long format with one row per active
`(Date, AssetID)` month.

Required columns:

- `Date`
- `AssetID`
- `AssetName`
- `AssetGroup`
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
- `realized_vol`
- `realized_downside_dev`
- `realized_max_drawdown`
- `realized_risk`
- `realized_rank`

## Feature And Target Logic

- Features for month `t` use the trailing 3 full months ending at `t-1`.
- Targets for month `t` use realized daily returns inside month `t`.
- Asset-level raw features are:
  `egarch_vol`, `downside_dev`, `max_drawdown`, `volume`, `atr_pct_20`,
  `beta_to_egx30`, `price_to_sma20`, `rsi_14`, `distance_to_3m_high`
- Macro features are:
  `usd_vol`, `cpi_trajectory`
- `egarch_vol` is built with strict month-level walk-forward EGARCH, so month
  `m` may only use returns available by the end of month `m`.
- `volume` is the trailing observed trading volume over the configured lookback
  window (`WINDOW_MONTHS`, currently 3 months), built from daily `Volume` and
  defaulted to `0` when the window contains no vendor volume.
- `atr_pct_20` is the trailing 20-observation average true range ending in
  month `t-1`, divided by the last observed close in `t-1`.
- `beta_to_egx30` is the trailing-window beta of the asset to aligned EGX30
  returns over the same three-month feature window.
- `price_to_sma20` is the last observed close in `t-1` divided by the trailing
  20 observed closes ending in `t-1`, minus 1.
- `rsi_14` is the 14-period Wilder RSI evaluated at the last observed close in
  `t-1`.
- `distance_to_3m_high` is the last observed close in `t-1` divided by the max
  observed `HighPriceForRange` over the trailing 3 full months ending in `t-1`,
  minus 1.
- Asset-level features are normalized cross-sectionally within month only.
- Macro features repeat across all active assets in the same month.
- Realized target components are:
  `realized_vol`, `realized_downside_dev`, `realized_max_drawdown`
- `realized_vol` is plain annualized volatility computed directly from month `t`
  daily returns.
- Realized target components are ranked within month and combined into
  `realized_risk`.
- Months with fewer than 3 valid assets are dropped.

## Availability And Leakage Rules

- Missing rows mean the asset is unavailable.
- A row is valid only if the asset has real history in each required trailing
  feature month and the realized month.
- Month `t` feature values must only use data available through the end of
  month `t-1`.
- Month `t` targets must only use realized returns from month `t`.
- Global preprocessing must not use future months when preparing earlier rows.
- Train, validation, and test ranges remain chronological.

## Acceptance Criteria

- `monthly_asset_panel.csv` starts at `2010-11`.
- No rows exist before an asset's real availability date.
- Metadata never needs to enter the model input tensor.
- Grouping by `Date` directly yields the runtime monthly batches.
