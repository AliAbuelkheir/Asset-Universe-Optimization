# Feature Phase

Status: closed.

This file records the feature-comparison and tail-candidate decisions. Current
model details and thesis evaluation live in
[project_guide.md](/C:/Ali/CS/Bachelor%20thesis/docs/project_guide.md).

## Purpose

The feature phase tested whether the canonical monthly feature profile should
be changed after the framework was locked to `pit_3m_flat_context`.

Selection rules:

- keep the framework fixed
- use validation reward as the primary metric
- use validation Spearman as the guardrail
- screen with seed `42`
- confirm promoted candidates with seeds `7` and `13`
- use test only for reporting

## Locked Baseline

Canonical default profile:

- `full_current_v1`

Canonical model-facing features:

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

Current-best metadata is separate from the canonical defaults. The current best
adds `downside_tail_ratio_3m` through the input feature set
`shadow_add_downside_tail_ratio_3m`.

## Main Findings

The original feature phase did not promote a canonical replacement profile.
Several one-feature drops and redesigns were useful diagnostics, but the
canonical profile stayed `full_current_v1`.

Important outcomes:

| Candidate or profile | Outcome | Reason |
| --- | --- | --- |
| `drop_distance_to_3m_high` | not canonical | won some screens but failed the earlier promoted-seed feature confirmation |
| `monthly_only_rows_v1` | rejected | improved held-out test average but lost on validation reward/Spearman |
| replacement features such as `max_drawdown_1m`, `price_to_sma14`, `usd_vol_1m` | not canonical | did not beat the canonical shadow baseline under the isolated screen |
| additive ratio/tail features | reopened after PPO tuning | used to investigate high-risk-overlap weakness |

## Row-Semantics Experiment

`monthly_only_rows_v1` tested whether rows should represent only the current
month instead of the canonical trailing 3-month row definition.

Three-seed means:

| Profile | Validation reward | Validation Spearman | Test reward | Test Spearman | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| `full_current_v1` | `0.6819` | `0.5722` | `0.7078` | `0.6085` | keep |
| `monthly_only_rows_v1` | `0.6794` | `0.5687` | `0.7224` | `0.6291` | reject |

The test improvement was treated as reporting evidence only because selection
uses validation.

## Tail-Aware Additive Update

After PPO tuning, a tail-aware candidate screen was run under the locked
`refined50` PPO setup. The goal was to improve high-risk identification without
reopening framework or PPO tuning.

Selected additive feature:

- `downside_tail_ratio_3m`

Interpretation:

- measures how much recent absolute movement came from downside tail returns
- complements volatility, downside deviation, and drawdown features
- is financially defensible for high-risk bucket separation

Three-seed current-best metrics:

| Split | Reward | Spearman | High-risk top-25% overlap |
| --- | ---: | ---: | ---: |
| validation | `0.7081` | `0.6047` | `0.4772` |
| test | `0.7515` | `0.6652` | `0.4949` |

## Final Decision

Use this distinction consistently:

- canonical default profile: `full_current_v1`
- current-best input feature set: `shadow_add_downside_tail_ratio_3m`
- current-best additive feature: `downside_tail_ratio_3m`

Do not reopen feature search unless the thesis evaluation shows that the
current model fails risk separation or high-risk detection.
