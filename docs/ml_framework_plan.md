# ML Framework Plan

## Objective

Build a shared monthly risk scorer that consumes the canonical monthly asset
panel and outputs one risk score per active asset at each month.

The primary use case is cross-sectional monthly ranking from lower to higher
predicted risk. Investor-tier selection logic remains out of scope.

## Canonical Input Contract

The model reads `data/ready/monthly_asset_panel.csv`.

Canonical feature columns:

- `egarch_vol`
- `downside_dev`
- `max_drawdown`
- `volume`
- `usd_vol`
- `cpi_trajectory`

Columns retained for grouping/alignment but excluded from model input:

- `Date`
- `AssetID`
- `AssetName`
- `AssetGroup`
- `realized_egarch_vol`
- `realized_downside_dev`
- `realized_max_drawdown`
- `realized_risk`
- `realized_rank`

## Shared Scorer Design

- One scorer is shared across all asset rows.
- The model must not allocate one slot per named asset.
- Asset identifiers must never be embedded into the model input.
- The canonical stored dataset remains long rather than wide so the universe can
  grow or shrink without changing the schema.

## Runtime Batch Construction

For month `t`:

1. filter `monthly_asset_panel.csv` where `Date == t`
2. drop rows missing required model features
3. remove metadata and target columns
4. feed the remaining feature matrix to the scorer
5. join predictions back to metadata outside the model

This preserves the variable-size monthly batch design without leaking asset
identity into the model tensor.

## RL Framing

One environment step equals one month.

At month `t`:

1. score all active asset rows for the month
2. sort predictions from low to high risk
3. align them with month `t` realized targets
4. compute one reward for the full month

## Training And Evaluation Behavior

- Warm-up months are used only to initialize rolling windows.
- Training starts at `2010-11`.
- Validation covers `2023-01` to `2025-02`.
- Test covers `2025-03` to `2026-02`.
- Months with fewer than 3 available assets are skipped.

Evaluation outputs should focus on:

- monthly Spearman rank correlation
- monthly MSE
- aggregate reward over each split
- exported month-level ranked predictions

## Acceptance Criteria

- The scorer consumes only the canonical feature columns.
- The scorer can score any asset that matches the feature schema.
- Reward is computed at the month level only.
- Predictions can be grouped and sorted by month using model-hidden metadata.
