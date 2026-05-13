# Weight Optimizer Integration Evidence

These are historical simulation diagnostics only. They compare realized returns after a decision month and should not be read as proof of guaranteed future outperformance.

## Integration Status

- Deployment package: `model-artifacts/deployment`.
- Active simulator mode after integration: `external_model`.
- Optimizer runs twice per simulation:
  - `optimizedPortfolio`: optimizer on the PPO-selected risk bucket.
  - `optimizedRawUniverse`: optimizer on the full active raw universe for the same month and tier.
- Existing benchmarks remain:
  - `assignedRiskBucket`: selected bucket equal weight.
  - `allEqualWeight`: full active universe equal weight.
  - `egx30`: EGX30 context benchmark.

## Verified Contract

| Check | Status |
|---|---|
| Raw OHLCV request construction from `daily_market_series.csv` | Passed |
| Dynamic asset counts `N=3`, `N=5`, `N=10` | Passed |
| Selected-bucket and full-universe inference | Passed |
| Long-only weights | Passed |
| Sum-to-one weights | Passed |
| Tier caps respected | Passed in deployment tests |
| JSON round trip | Passed in deployment tests |

Important caveat: when deployment `N` differs from the training count (`low=10`, `medium=12`, `high=16`), the optimizer package may fall back to identity VecNormalize observation normalization. The simplified public API keeps the report focused on displayed historical diagnostics, so advanced optimizer diagnostics are not returned to the client.

## Probe: 2024-01, 6-Month Horizon

| Risk level | Portfolio | Assets | Cumulative return | Annualized volatility | Sharpe | Max drawdown |
|---|---:|---:|---:|---:|---:|---:|
| Low | Optimizer after risk filter | 11 | 33.15% | 26.88% | 2.29 | -7.21% |
| Low | Selected bucket equal weight | 11 | 28.79% | 31.15% | 1.78 | -9.31% |
| Low | Optimizer on raw universe | 36 | 20.96% | 37.45% | 1.18 | -17.04% |
| Low | Full universe equal weight | 36 | 20.13% | 39.78% | 1.10 | -18.94% |
| Low | EGX30 | 1 | 11.54% | 31.31% | 0.83 | -15.59% |
| Medium | Optimizer after risk filter | 22 | 3.55% | 55.15% | 0.37 | -31.33% |
| Medium | Selected bucket equal weight | 22 | 15.82% | 50.93% | 0.80 | -25.10% |
| Medium | Optimizer on raw universe | 36 | 21.92% | 56.69% | 0.94 | -25.63% |
| Medium | Full universe equal weight | 36 | 20.13% | 39.78% | 1.10 | -18.94% |
| Medium | EGX30 | 1 | 11.54% | 31.31% | 0.83 | -15.59% |
| High | Optimizer after risk filter | 11 | 35.15% | 46.85% | 1.51 | -20.17% |
| High | Selected bucket equal weight | 11 | 21.59% | 37.89% | 1.21 | -18.42% |
| High | Optimizer on raw universe | 36 | 28.86% | 46.20% | 1.30 | -18.92% |
| High | Full universe equal weight | 36 | 20.13% | 39.78% | 1.10 | -18.94% |
| High | EGX30 | 1 | 11.54% | 31.31% | 0.83 | -15.59% |

## Honest Interpretation

- Low-risk 2024-01 is strong evidence that filtering before optimization can improve the realized diagnostic versus optimizing the raw universe.
- Medium-risk 2024-01 is not supportive for the selected optimizer; the equal-weight selected bucket was better in this probe.
- High-risk 2024-01 shows higher upside from selected optimization, with higher drawdown than selected equal weight.
- The raw-universe optimizer is useful as an experimental benchmark next to equal weights and EGX30, but it should carry the dynamic-N and possible tier-universe distribution caveat.
