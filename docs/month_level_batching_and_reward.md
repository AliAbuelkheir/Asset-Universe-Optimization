# Month-Level Batching And Reward

## Core Rule

One RL step equals one month, not one asset row.

This remains required because the reward depends on ranking all active assets in
the same month, which cannot be computed correctly at the row level.

## Canonical Batch Source

Monthly batches are built from `data/ready/monthly_asset_panel.csv`.

For each month `t`:

1. select all rows where `Date == t`
2. keep metadata columns for grouping only
3. build the model tensor from feature columns only
4. score every active asset row in that month

Current feature columns:

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

Each month is therefore a variable-size batch because the number of active
assets changes through time.

## Prediction Flow

For month `t`:

1. input all active asset rows
2. output one predicted risk score per asset row
3. join predictions back to `AssetID`
4. sort assets by predicted score from low to high risk

This sorted list is the immediate product of the model in the current phase.

## Reward Flow

After all assets in month `t` are scored:

1. fetch the realized targets already stored in the month `t` panel rows
2. align by `AssetID`
3. compute Spearman rank correlation across the active asset set
4. compute MSE across the active asset set
5. combine them into one month-level reward

Reward formula:

`0.7 * SpearmanRankCorr(predicted, realized) + 0.3 * (1 - MSE)`

## Stored Realized Targets

The month-`t` realized target columns are:

- `realized_vol`
- `realized_downside_dev`
- `realized_max_drawdown`
- `realized_risk`
- `realized_rank`

`realized_risk` is built from within-month normalized:

- `realized_vol`
- `realized_downside_dev`
- `realized_max_drawdown`

This keeps the target fully realized and avoids model-based filtering inside the
target construction.

## Validity Rules

- Compute reward only for assets active in that month.
- Do not pad unavailable assets into the reward calculation.
- Skip months with fewer than 3 active assets.
- Keep `AssetID` for alignment and sorting, but exclude it from model input.

## Why This Fixes The RL Mismatch

The reward is fundamentally month-level because:

- the task is cross-sectional ranking within a month
- the model output is only meaningful once all assets for that month are scored
- the reward compares the whole monthly ordering against the realized ordering

This preserves the RL framing while matching the actual structure of the
prediction problem.
