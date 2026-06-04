# Defense Script

Use this file as the reusable slide-by-slide speaking script template.

## Slide 4 - Why Risk-Tolerance Universe Selection Matters

**Talk track**

In the Egyptian investment context, many retail investors are highly sensitive to instability because of inflation, currency fluctuations, and broader economic uncertainty. That often pushes investors toward assets they see as more stable, such as gold, bank certificates, or foreign currency exposure.

This thesis explores a risk-first portfolio construction approach that starts by aligning asset exposure with investor risk tolerance under changing market conditions. Instead of optimizing mainly for maximum return, the system focuses first on controlling portfolio risk, reducing excessive exposure to unstable assets, and evaluating historical behavior through simulation diagnostics.

For medium- and high-risk investors, this does not mean removing return-seeking exposure. It means allowing greater participation in higher-risk assets when that fits the investor profile, while still keeping the selection logic centered on risk behavior first.

**Transition**
This leads to the next question: how similar ideas were handled in the literature before my proposed solution.

## Slide 8.1 - AI/ML Preselection Context

**Talk track**

In the literature, AI and machine learning are often used before portfolio optimization as a filtering step. The model helps decide which stocks should enter the portfolio construction stage.

The important distinction is that these AI and machine learning preselection papers usually filter stocks based on expected price, expected return, or profitability. After that, the selected candidates are passed to a portfolio optimizer.

Risk metrics such as Sharpe ratio, volatility, drawdown, or robustness usually appear after the preselection step, during weight allocation, portfolio optimization, or evaluation. So risk is often used to judge or optimize the final portfolio, not as the direct target of the AI preselection model.

**Transition**
There is one important exception in the reviewed literature, and that is the DEA-style preselection line.

## Slide 8.2 - DEA Preselection Papers

**Talk track**

The main exception is the DEA-style preselection paper. DEA is not AI or machine learning in the same predictive sense. It is an efficiency-screening method, and it can include risk-return measures as part of the screening process.

However, this still falls under efficiency-based filtering. The goal is to identify efficient assets based on risk-return behavior, not to learn an investor-risk-tolerance ranking.

It is also not the same market setting as my thesis, because my work uses an Egyptian mixed-asset universe rather than the setting used in that paper.
