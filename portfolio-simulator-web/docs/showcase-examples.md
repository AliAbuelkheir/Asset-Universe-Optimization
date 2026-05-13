# Showcase Examples

Use these examples when demonstrating how the asset-universe filtration step changes the simulation output.

These are historical diagnostics only. They should be presented as examples of how the risk-bucket filter behaved in the validation/test data, not as proof of guaranteed future improvement.

## Recommended Primary Demo

| Risk level | Month | Duration | Why this is the best first demo |
| --- | --- | --- | --- |
| Low | `2024-01` | `3 months` | Best balanced low-risk example. The selected bucket return is `24.84%` versus `15.09%` for all active assets, with lower volatility `33.49%` versus `53.62%` and lower drawdown `-0.97%` versus `-11.56%`. |

## Good Examples By Risk Level

| Risk level | Month | Duration | Use this when | Caveat |
| --- | --- | --- | --- | --- |
| Low | `2024-01` | `3 months` | You want the cleanest low-risk filtration story: better return, lower volatility, and lower drawdown versus all active assets. | Short window, so keep wording as a historical example. |
| Low | `2024-01` | `6 months` | You want a slightly longer low-risk example with the same overall message. Return is `28.79%` versus `20.13%`, volatility is `31.15%` versus `39.78%`, and drawdown is `-9.31%` versus `-18.94%`. | Less visually sharp than the 3-month version. |
| Low | `2025-06` | `6 months` | You want a test-split example. Return is `27.88%` versus `24.35%`, with lower forward volatility `4.37%` versus `7.86%`. | Forward drawdown is `0%` for both selected and all-active universes, so it is weaker for drawdown separation. |
| Medium | `2023-07` | `6 months` | You want a medium-bucket example where the central filter still has a readable return edge. Return is `34.56%` versus `28.70%`. | Forward volatility and drawdown are slightly worse than all active assets, so frame it as central-bucket filtering, not risk minimization. |
| Medium | `2023-07` | `12 months` | You want a longer medium-bucket return-supporting example. Return is `59.54%` versus `54.61%`. | Same caveat: this is not a pure lower-risk example. |
| High | `2024-10` | `Max available` | You want the clearest high-risk contrast. Return is `107.26%` versus `60.63%`, while volatility and drawdown are higher, which fits the high-risk bucket story. | Present as upside-for-risk behavior, not as a recommended safer portfolio. |
| High | `2024-05` | `12 months` | You want a strong high-risk upside example. Return is `97.82%` versus `53.33%`. | High bucket has higher volatility; that is expected and should be explained. |

## Presentation Guidance

- Start with `Low / 2024-01 / 3 months`.
- Use the component-risk diagnostics first: volatility, downside deviation, and max drawdown.
- Use the cumulative return chart as supporting evidence, not the headline.
- For the high bucket, emphasize that the filter is identifying a higher-risk universe with higher historical upside in these examples.
- Avoid saying the filter guarantees improvement. Use language like "historical diagnostic," "observed comparison," and "selected bucket versus all active assets."
