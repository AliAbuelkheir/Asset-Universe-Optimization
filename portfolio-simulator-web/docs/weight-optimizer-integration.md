# Weight Optimizer Integration Evidence

These are historical simulation diagnostics only. They compare realized returns after a decision month and should not be read as proof of guaranteed future outperformance.

## Integration Status

- Deployment package: `model-artifacts/deployment`.
- Active simulator mode after integration: `external_model`.
- External optimizer runs once per decision month:
  - `optimizedPortfolio`: external optimizer weights on the selected risk bucket.
- Visible benchmarks:
  - `assignedRiskBucket`: selected bucket equal weight.
  - `mvoFullUniverse`: classical full-universe MVO with trailing historical data.
  - `egx30`: EGX30 context benchmark.

## Verified Contract

| Check | Status |
|---|---|
| Raw OHLCV request construction from `daily_market_series.csv` | Passed |
| Dynamic asset counts `N=3`, `N=5`, `N=10` | Passed |
| Selected-bucket inference | Passed |
| Long-only weights | Passed |
| Sum-to-one weights | Passed |
| Tier caps respected | Passed in deployment checks |
| JSON round trip | Passed in deployment checks |

Important caveat: when selected-bucket deployment `N` differs from the training count (`low=10`, `medium=12`, `high=16`), the optimizer package may fall back to identity VecNormalize observation normalization. The simplified public API keeps the report focused on displayed historical diagnostics, so advanced optimizer diagnostics are not returned to the client.

## Probe: 2024-01, 6-Month Horizon

| Risk level | Portfolio | Assets | Cumulative return | Annualized volatility | Sharpe | Max drawdown |
|---|---:|---:|---:|---:|---:|---:|
| Low | External weights after risk filter | 11 | 33.15% | 26.88% | 2.29 | -7.21% |
| Low | Selected bucket equal weight | 11 | 28.79% | 31.15% | 1.78 | -9.31% |
| Low | Full-universe MVO | 36 | Re-run required | Re-run required | Re-run required | Re-run required |
| Low | EGX30 | 1 | 11.54% | 31.31% | 0.83 | -15.59% |
| Medium | External weights after risk filter | 22 | 3.55% | 55.15% | 0.37 | -31.33% |
| Medium | Selected bucket equal weight | 22 | 15.82% | 50.93% | 0.80 | -25.10% |
| Medium | Full-universe MVO | 36 | Re-run required | Re-run required | Re-run required | Re-run required |
| Medium | EGX30 | 1 | 11.54% | 31.31% | 0.83 | -15.59% |
| High | External weights after risk filter | 11 | 35.15% | 46.85% | 1.51 | -20.17% |
| High | Selected bucket equal weight | 11 | 21.59% | 37.89% | 1.21 | -18.42% |
| High | Full-universe MVO | 36 | Re-run required | Re-run required | Re-run required | Re-run required |
| High | EGX30 | 1 | 11.54% | 31.31% | 0.83 | -15.59% |

The MVO rows must be re-generated after the full-universe MVO benchmark change before quoting figures.

## Honest Interpretation

- Low-risk 2024-01 is a historical example where filtering before external weighting produced a higher realized diagnostic than the selected equal-weight row.
- Medium-risk 2024-01 is not supportive for the selected optimizer; the equal-weight selected bucket was better in this probe.
- High-risk 2024-01 shows higher upside from selected optimization, with higher drawdown than selected equal weight.
- The full-universe MVO row is now the classical optimizer benchmark next to filtered equal weight and EGX30.
