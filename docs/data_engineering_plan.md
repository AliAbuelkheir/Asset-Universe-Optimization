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
- Keep `Date`, `Price`, `Vol.`, and `Change %`.
- Drop `Open`, `High`, and `Low`.
- Parse `Vol.` into numeric `Volume`.
- Parse `Change %` into numeric `ChangePctRaw`.
- Treat `ChangePctRaw` as QA/reference only.
- Compute authoritative returns from cleaned prices.
- Concatenate and deduplicate `USD_1.csv` and `USD_2.csv`.
- Clean CPI from `CPI.csv` by removing the leading blank row and trailing notes.
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
- `PriceForReturn`
- `Volume`
- `ChangePctRaw`
- `ReturnFromPrice`
- `IsObserved`

Rules:

- `PriceForReturn` equals cleaned price for normal price series.
- `PriceForReturn` is a fixed-maturity price proxy for `MoneyMarket` and
  `Bonds`.
- EGX Sunday-Thursday alignment is used.
- Forward-fill is limited to 5 trading days.
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
- `usd_vol`
- `cpi_trajectory`
- `realized_egarch_vol`
- `realized_downside_dev`
- `realized_max_drawdown`
- `realized_risk`
- `realized_rank`

## Feature And Target Logic

- Features for month `t` use the trailing 3 full months ending at `t-1`.
- Targets for month `t` use realized daily returns inside month `t`.
- Asset-level raw features are:
  `egarch_vol`, `downside_dev`, `max_drawdown`, `volume`
- Macro features are:
  `usd_vol`, `cpi_trajectory`
- `egarch_vol` and `realized_egarch_vol` are built with strict month-level
  walk-forward EGARCH, so month `m` may only use returns available by the end
  of month `m`.
- `volume` is the trailing observed trading volume over the configured
  lookback window (`WINDOW_MONTHS`, currently 3 months), built from daily
  `Volume` and defaulted to `0` when the window contains no vendor volume.
- Asset-level features are normalized cross-sectionally within month only.
- Macro features repeat across all active assets in the same month.
- Realized component columns are ranked within month and combined into
  `realized_risk`.
- Months with fewer than 3 valid assets are dropped.

## Availability And Leakage Rules

- Missing rows mean the asset is unavailable.
- A row is valid only if the asset has real history in each required trailing
  feature month and the realized month.
- Global preprocessing must not use future months when preparing earlier rows.
- Train, validation, and test ranges remain chronological.

## Acceptance Criteria

- `monthly_asset_panel.csv` starts at `2010-11`.
- No rows exist before an asset's real availability date.
- Metadata never needs to enter the model input tensor.
- Grouping by `Date` directly yields the runtime monthly batches.
