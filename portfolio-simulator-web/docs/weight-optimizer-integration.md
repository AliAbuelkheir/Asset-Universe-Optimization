# Weight Optimizer Integration Evidence

These are historical simulation diagnostics only. They compare realized returns after a decision month and should not be read as proof of guaranteed future outperformance.

## Integration Status

- Deployment package: `model-artifacts/deployment`.
- Active simulator mode after integration: `external_model`.
- External optimizer runs once per decision month:
  - `optimizedPortfolio`: profile optimizer weights on the selected/filtered universe.
  - `optimizerFullUniverse`: profile optimizer weights on the full reportable universe.
- Visible benchmarks:
  - `mvoFilteredUniverse`: classical MVO on the selected/filtered universe.
  - `mvoFullUniverse`: classical MVO on the full reportable universe.
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
| Low | Profile optimizer portfolio | 11 | 33.15% | 26.88% | 2.29 | -7.21% |
| Low | Full-universe optimizer benchmark | 36 | Re-run required | Re-run required | Re-run required | Re-run required |
| Low | Profile MVO benchmark | 11 | Re-run required | Re-run required | Re-run required | Re-run required |
| Low | Full-universe MVO benchmark | 36 | Re-run required | Re-run required | Re-run required | Re-run required |
| Low | EGX30 | 1 | 11.54% | 31.31% | 0.83 | -15.59% |
| Medium | Profile optimizer portfolio | 22 | 3.55% | 55.15% | 0.37 | -31.33% |
| Medium | Full-universe optimizer benchmark | 36 | Re-run required | Re-run required | Re-run required | Re-run required |
| Medium | Profile MVO benchmark | 22 | Re-run required | Re-run required | Re-run required | Re-run required |
| Medium | Full-universe MVO benchmark | 36 | Re-run required | Re-run required | Re-run required | Re-run required |
| Medium | EGX30 | 1 | 11.54% | 31.31% | 0.83 | -15.59% |
| High | Profile optimizer portfolio | 11 | 35.15% | 46.85% | 1.51 | -20.17% |
| High | Full-universe optimizer benchmark | 36 | Re-run required | Re-run required | Re-run required | Re-run required |
| High | Profile MVO benchmark | 11 | Re-run required | Re-run required | Re-run required | Re-run required |
| High | Full-universe MVO benchmark | 36 | Re-run required | Re-run required | Re-run required | Re-run required |
| High | EGX30 | 1 | 11.54% | 31.31% | 0.83 | -15.59% |

The full-universe optimizer and MVO rows must be re-generated after the benchmark-set change before quoting figures.

## Honest Interpretation

- Low-risk 2024-01 is a historical example where profile filtering before optimizer weighting produced a higher realized diagnostic than EGX30 in the prior probe.
- Medium-risk 2024-01 is not supportive for the selected optimizer in the prior probe, so do not quote it as general outperformance.
- High-risk 2024-01 shows higher upside from selected optimization, with higher drawdown than the lower-risk examples.
- The visible report now separates allocator and universe: profile optimizer, full-universe optimizer, profile MVO, full-universe MVO, and EGX30.
