# Showcase Examples

Use this file as two separate demo scripts after the full pipeline integration.

These are historical simulation diagnostics only. Present them as realized outcomes after the selected decision month, not as proof of guaranteed future outperformance.

## Version 1: Full Pipeline Showcase

Use this version when the point is: the selected-bucket external weights can be shown as one historical diagnostic next to the baselines.

Full pipeline means:

1. active asset universe
2. PPO risk-bucket filter
3. external weight optimizer on the filtered universe

The main row is `Profile optimizer portfolio`. It should be reviewed alongside:

- `Profile equal weights`
- `Full-universe optimizer benchmark`
- `Full-universe equal weights`
- `Profile MVO benchmark`
- `Full-universe MVO benchmark`
- `EGX30`

### Recommended Primary Demo

| Risk level | Month | Duration | Why this is the primary full-pipeline demo |
| --- | --- | --- | --- |
| Medium | `2023-06` | `Max available` (`32 months`) | Largest checked full-pipeline separation in the prior scan. Re-run this row after the MVO benchmark update before quoting exact full-universe MVO figures. |

Use `Low / 2024-01 / 6 months` if you need a shorter, cleaner live demo. Re-run the simulator before quoting exact full-universe MVO figures.

### Good Full-Pipeline Examples

| Risk level | Month | Duration | Use this when | Caveat |
| --- | --- | --- | --- | --- |
| Medium | `2023-06` | `Max available` (`32 months`) | You want the largest full-pipeline return gap from the prior scan. | Long historical-window example. Re-run before quoting exact MVO comparison figures. |
| Medium | `2023-06` | `12 months` | You want a shorter medium-risk full-pipeline example. | EGX30 is close on return in the prior scan, so do not frame this as uniformly lower risk. |
| Low | `2023-11` | `Max available` (`27 months`) | You want a low-risk full-pipeline example with higher realized return and lower drawdown than the filter-only row. Return is `195.22%` versus `172.88%`; drawdown is `-8.36%` versus `-10.57%`. | Long historical-window example. |
| Low | `2024-01` | `6 months` | You want a compact full-pipeline story. Return is `33.15%`, volatility is `26.88%`, and drawdown is `-7.21%` in the prior scan. | Short historical window. Re-run before quoting MVO figures. |
| Low | `2024-01` | `3 months` | You want the shortest compact full-pipeline demo. Return is `26.99%` versus `24.84%` for profile equal weights in the prior scan. | Three months is only a visual example, not a robust performance claim. |
| High | `2024-09` | `Max available` (`17 months`) | You want an aggressive full-pipeline example. | Volatility and drawdown are higher than the lower-risk baselines, which fits a high-risk story. |
| High | `2025-10` | `3 months` | You want a recent-window example where the external-weight row had the higher realized return. | Very short window; ratios are unstable. |

## Version 2: PPO Risk-Filter Showcase

Use this version when the point is: the PPO risk-bucket filter changes the selected asset universe before external weighting.

This isolates the filter. Compare `Profile equal weights` against `Full-universe equal weights`. Do not use this version to claim that the external weighting stage caused the result.

The previous showcase rows were rechecked and remain valid for this filter-only interpretation.

### Recommended Primary Demo

| Risk level | Month | Duration | Why this is the primary filter-only demo |
| --- | --- | --- | --- |
| Low | `2023-06` | `12 months` | Balanced low-risk filter example found in the checked rows. Profile equal-weight return is `85.07%` versus `53.24%` for full-universe equal weights, with lower volatility `28.21%` versus `30.46%` and lower drawdown `-6.79%` versus `-18.94%`. |

Use `Low / 2024-01 / 3 months` when you need the simplest short demo: return is `24.84%` versus `15.09%`, volatility is `33.49%` versus `53.62%`, and drawdown is `-0.97%` versus `-11.56%`.

### Good Filter-Only Examples By Risk Level

| Risk level | Month | Duration | Use this when | Caveat |
| --- | --- | --- | --- | --- |
| Low | `2023-06` | `12 months` | You want the largest balanced low-risk filter example: higher return, lower volatility, and lower drawdown versus full-universe equal weights. | Historical window. |
| Low | `2024-01` | `3 months` | You want a short low-risk filtration story. | Short window, so keep wording as a historical example. |
| Low | `2024-01` | `6 months` | You want the older low-risk demo with a slightly longer horizon. Return is `28.79%` versus `20.13%`, volatility is `31.15%` versus `39.78%`, and drawdown is `-9.31%` versus `-18.94%`. | Less sharp than the 3-month version. |
| Low | `2025-06` | `6 months` | You want a recent-window low-risk example. Return is `27.88%` versus `24.35%`, with lower volatility `4.37%` versus `7.86%`. | Drawdown is `0.00%` for both rows, so it is weak for drawdown separation. |
| Medium | `2023-05` | `Max available` (`33 months`) | You want the largest checked medium-bucket return gap. Return is `278.09%` versus `212.90%`. | Volatility and drawdown are worse than the full universe, so frame it as central-bucket filtering, not risk minimization. |
| Medium | `2023-09` | `6 months` | You want a medium-bucket example with a strong return edge and no observed drawdown. Return is `88.94%` versus `66.50%`. | Volatility is higher than the full-universe row. |
| Medium | `2023-07` | `6 months` | You want the older medium-bucket example. Return is `34.56%` versus `28.70%`. | EGX30 is higher in this short window, so use it only for filter-versus-full-universe discussion. |
| Medium | `2023-07` | `12 months` | You want a longer medium-bucket example. Return is `59.54%` versus `54.61%`. | Risk metrics are not better than the full universe. |
| High | `2024-10` | `Max available` (`16 months`) | You want the clearest high-risk filter contrast. Return is `107.26%` versus `60.63%`. | Higher volatility and drawdown are expected for a high-risk bucket. |
| High | `2024-05` | `12 months` | You want a strong high-risk upside example. Return is `97.82%` versus `53.33%`. | Volatility is higher, so present it as upside-for-risk behavior. |
| High | `2025-03` | `Max available` (`11 months`) | You want a recent-window high-risk example. Return is `77.21%` versus `49.59%` in the prior scan. | Full-universe equal weights have lower volatility and no drawdown in this window. |

## Presentation Guidance

- Use Version 1 for the live full-pipeline simulator story.
- Use Version 2 when defending the PPO risk-bucket filter itself.
- Do not mix the two claims: filter-only examples are not optimizer evidence, and full-pipeline examples should name the optimizer.
- For high-risk rows, emphasize that the filter is identifying a higher-risk universe with higher historical upside in these examples.
- Avoid saying the pipeline or filter guarantees improvement. Use language like "historical diagnostic," "observed comparison," and "selected bucket versus baseline."
