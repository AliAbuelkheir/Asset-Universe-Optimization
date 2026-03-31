# RL Asset Risk Scoring

This repository is a bachelor thesis project for a variable-universe,
month-level RL asset risk scorer over the Egyptian market.

The canonical direction is now:

- one shared scorer applied to every active asset row in a month
- one canonical long monthly panel with one row per `(Date, AssetID)`
- one month-level reward after the full active universe is scored
- one daily cleaned market reference that preserves volume and raw change data
- one monthly model input set that now includes rolling asset volume

## Canonical Docs

- Canonical repository contract:
  [AGENTS.md](/C:/Ali/CS/Bachelor%20thesis/AGENTS.md)
- Internal data engineering plan:
  [docs/data_engineering_plan.md](/C:/Ali/CS/Bachelor%20thesis/docs/data_engineering_plan.md)
- Internal ML framework plan:
  [docs/ml_framework_plan.md](/C:/Ali/CS/Bachelor%20thesis/docs/ml_framework_plan.md)
- Internal month batching and reward plan:
  [docs/month_level_batching_and_reward.md](/C:/Ali/CS/Bachelor%20thesis/docs/month_level_batching_and_reward.md)
- Team-facing communication hub:
  [team_docs/README.md](/C:/Ali/CS/Bachelor%20thesis/team_docs/README.md)

If wording conflicts across repository markdown files, `AGENTS.md` is the
source of truth.

## High-Level Structure

```text
rawData/                 Canonical raw market data
data/ready/              Cleaned daily market series and monthly asset panel
docs/                    Internal implementation plans
team_docs/               Team-facing updates, RL model notes, papers, thesis PDF
src/
  data_processing/       Dataset builder and validator
  environment/           RL environment placeholder
  training/              Training and evaluation placeholders
  config.py              Shared implementation constants
diagrams/                Preserved diagram assets
thesis/                  Thesis source and rendered PDF
outputs/                 Models, rankings, metrics, and plots
```

## Active Pipeline

Build the canonical datasets with:

```powershell
.\.venv\Scripts\python.exe src\data_processing\build_model_dataset.py
.\.venv\Scripts\python.exe src\data_processing\validate_model_dataset.py
```

Primary outputs:

- `data/ready/daily_market_series.csv`
- `data/ready/monthly_asset_panel.csv`

## Current Focus

- finish the monthly asset panel for model ingestion
- preserve volume and raw vendor change data in the cleaned daily series
- expose trailing-window asset volume as a model feature
- derive authoritative returns from cleaned prices
- keep batching and reward strictly month-level
- keep metadata available for grouping while excluding it from model inputs
