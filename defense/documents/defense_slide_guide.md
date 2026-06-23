# Defense Slide Guide

> Source: `defense/slides/defense.pptx`. Regenerate with `$update-defense-docs` after the deck changes.
> This is a concise content guide, not a second script.

## Slide 1: Portfolio Optimization

**Main idea:** Introduce the thesis as risk-based asset-universe selection before portfolio allocation.

- Asset Universe Selection Based on Investor Profiles
- Presenter: Ali Abuelkheir
- Supervisor: Dr. Mervat Abuelkheir

## Slide 2: Roadmap

**Main idea:** Preview the presentation sequence.

- Problem Definition
- Literature Gap
- Proposed Solution
- Methodology & Experiments
- Results
- Conclusion
- Future Work

## Slide 3: Problem Definition

**Main idea:** Section divider introducing the portfolio-selection problem.

## Slide 4: The Fixed-Universe Assumption

**Main idea:** Portfolio optimization is constrained by the assets selected before weighting begins.

- Optimization often starts after assets are already chosen.
- A weak candidate universe limits even a strong optimizer.
- This thesis studies selection before allocation.

## Slide 5: Untitled Risk-Ranking Video

**Main idea:** Asset risk ranks change materially across months in the Egyptian market.

**Visual reminder:** The animation tracks each asset's realized-risk rank over time. Point out the monthly reshuffling and the average movement of about seven rank positions.

## Slide 6: Why Universe Selection Matters?

**Main idea:** Risk tolerance should define the candidate universe before return, diversification, and allocation decisions.

**Diagram reminder:** Explain the risk-first suitability flow from investor tolerance to a filtered universe and then to later portfolio-construction decisions.

## Slide 7: Scope and Asset Universe

**Main idea:** Define the mixed Egyptian investment universe used by the thesis.

- 91-day treasury bills
- 5-year government bonds
- Individual EGX30 equities
- EGX30 market benchmark
- EGX Real Estate index
- Egyptian 24-karat gold price

**Visual reminder:** Use the asset-class cards to distinguish investable assets from the EGX30 reference benchmark.

## Slide 8: Research Questions

**Main idea:** State the three questions evaluated by the thesis.

- RQ1: Can AI/ML support dynamic risk-based universe selection?
- RQ2: Do selected universes align with investor profiles?
- RQ3: How do selected universes compare with the full active universe?

## Slide 9: Literature Review

**Main idea:** Section divider introducing prior work and the research gap.

## Slide 10: Classical Allocation Context

**Main idea:** Classical methods optimize weights after assuming the investable universe is already defined.

- Classical methods focus on return-risk weight allocation.
- Markowitz (1952) and MVO assume a predefined universe.
- This thesis focuses on the step before weighting.

## Slide 11: AI/ML Preselection Context

**Main idea:** Existing AI/ML preselection usually filters for return or profitability, while risk is handled later.

- Existing work filters assets before optimization.
- Common signals include expected price, expected return, and profitability.
- Risk metrics usually appear during weighting or evaluation.

## Slide 12: DEA Preselection Paper

**Main idea:** Atta Mills and Anyomi provide a preselection precedent, but their DEA method targets efficiency rather than learned risk ranking.

- DEA screens assets before allocation.
- Standard deviation is one input among mainly performance-oriented inputs.
- The method is statistical rather than AI-based ranking.

## Slide 13: RL And Investor Personalization

**Main idea:** The thesis links RL and personalization by predicting risk first and then constructing profile-specific universes.

- Finance RL commonly targets trading or weights.
- Personalization commonly maps profiles to advice, products, or final portfolios.
- This thesis ranks risk first, then selects assets by profile.

## Slide 14: Proposed Solution

**Main idea:** Section divider introducing the proposed pipeline.

## Slide 15: Contribution In One View

**Main idea:** Present the complete thesis pipeline from raw data to historical evaluation.

**Diagram reminder:** Walk through four layers in order: data engineering, predicted-risk ranking, investor-profile universe selection, and historical evaluation.

## Slide 16: Methodology

**Main idea:** Section divider introducing the technical method.

## Slide 17: Chronological Split Design

**Main idea:** Separate model learning, checkpoint selection, configuration comparison, and final reporting chronologically.

**Diagram reminder:** Explain the timeline in order: training, inner validation, validation, and test. Emphasize that the test period is untouched until the promoted configuration is fixed.

## Slide 18: Raw Data Engineering

**Main idea:** Convert heterogeneous market and macro data into comparable model inputs.

- Date, price, OHLC fields, and volume
- T-bill and bond yields converted into price proxies
- USD/EGP and CPI as macro context

## Slide 19: Point-In-Time Monthly Panel

**Main idea:** Build one leakage-controlled row per active asset and month.

- Features use only information available up to that month.
- Assets are not backfilled before they existed.
- Asset identity remains metadata and is excluded from model inputs.

## Slide 20: Feature Families

**Main idea:** Group model inputs by the behavior they describe rather than presenting a long feature list.

**Diagram reminder:** Briefly cover risk behavior, liquidity, technical state, market sensitivity, and macro context.

## Slide 21: Realized Risk Target

**Main idea:** Define the monthly target as the equal-weight average of rank-normalized volatility, downside deviation, and maximum drawdown.

**Diagram reminder:** Stress that normalization is cross-sectional within each month, so every asset is compared only with assets active at that time.

## Slide 22: What Is Reinforcement Learning

**Main idea:** Give a simple explanation of state, action, reward, and policy updates.

**Diagram reminder:** Follow the loop in order: observe state, take action, receive reward, update policy.

## Slide 23: Why Reinforcement Learning

**Main idea:** Frame each month as one set-level ranking decision with delayed feedback.

- The available assets change from month to month.
- The model scores the complete monthly set, not isolated assets.
- Reward arrives after the entire universe is ranked.

**Diagram reminder:** Map state to the active universe, action to per-asset risk scores, and reward to agreement with the realized-risk ranking.

## Slide 24: Why PPO

**Main idea:** PPO provides controlled policy updates and a stable actor-critic learning structure.

- Clipping limits unstable policy jumps.
- Actor-critic structure stabilizes learning.
- The method supports month-level reward feedback.

## Slide 25: PPO Episode Format

**Main idea:** One PPO episode is one monthly universe-ranking decision.

**Diagram reminder:** Explain observation tensor plus mask, continuous per-asset scores, sorting into a predicted ranking, and one reward for the complete month.

## Slide 26: Variable Universe & Masking

**Main idea:** Padding creates a fixed tensor shape while masking prevents fake rows from affecting the model.

- Padding gives a consistent tensor shape.
- The mask separates real asset rows from padding rows.
- Padding does not affect actions, learning, or reward.

## Slide 27: Actor-Critic Architecture

**Main idea:** Show how the shared encoder, actor, and critic cooperate on a monthly set of assets.

**Diagram reminder:** The row encoder creates asset representations and pooled monthly context; the actor outputs risk scores; the critic estimates expected reward; the advantage drives PPO updates.

## Slide 28: Reward Definition

**Main idea:** Reward prioritizes rank agreement while retaining score-value discipline.

- 70% Spearman rank correlation
- 30% score error term based on MSE

**Diagram reminder:** Explain that Spearman evaluates ordering and the MSE term discourages collapsed, indistinguishable scores.

## Slide 29: Profile-Specific Asset Universes

**Main idea:** Convert predicted rank percentiles into overlapping investor-profile universes.

- Conservative: lowest 30% predicted-risk assets
- Balanced: 20% to 80% predicted-risk band
- Aggressive: highest 30% predicted-risk assets

## Slide 30: Experiments

**Main idea:** Section divider introducing model and mapping experiments.

## Slide 31: Framework Selection

**Main idea:** Compare temporal windows and context designs before fixing the final framework.

- One-month versus three-month feature windows
- With versus without pooled active-universe context
- Variants with more direct daily-price inputs

**Result reminder:** The three-month view with pooled active-universe context was promoted.

## Slide 32: Features and Reward Function

**Main idea:** Select features sequentially, then compare reward formulations after fixing the input framework.

- Drop-one ablations on the base feature set
- Multi-seed confirmation, redesigned families, and incremental additions
- Rank-dominant reward with secondary score discipline

## Slide 33: Hyper-parameters and Selection

**Main idea:** Tune PPO, confirm robustness across seeds, and then choose the profile mapping.

- Optuna trials using validation reward
- Three-seed confirmation before locking the model
- Comparison of alternative profile-universe mappings

## Slide 34: Evaluation Logic

**Main idea:** Evaluate both predictive ranking quality and the practical behavior of profile universes.

- Stage 1: Compare predicted ranks with realized-risk ranks.
- Stage 2: Compare profile universes with the full active universe.

**Diagram reminder:** Equal weighting is held constant in stage 2 so the comparison isolates universe selection.

## Slide 35: Results

**Main idea:** Section divider introducing test-period findings.

## Slide 36: Ranking Quality

**Main idea:** The promoted model shows meaningful test-period alignment with realized-risk ordering.

- Mean reward: 0.75
- Mean Spearman correlation: 0.67

**Chart reminder:** The scatter plot compares realized and predicted ranks; proximity to the diagonal indicates stronger agreement.

## Slide 37: Risk Separation

**Main idea:** The predicted profile universes separate realized risk in the intended monotonic order.

- Conservative mean realized risk: 23.9%
- Full-universe mean realized risk: 50.0%
- Balanced mean realized risk: 53.6%
- Aggressive mean realized risk: 68.8%
- Monotonic ordering held in 11 of 11 test months.

## Slide 38: Return Separation

**Main idea:** Return outcomes differ across the same profile universes, with higher aggressive returns accompanied by higher risk.

- Conservative cumulative return: 29.91%
- Full-universe cumulative return: 49.59%
- Balanced cumulative return: 50.17%
- Aggressive cumulative return: 86.24%

**Chart reminder:** Treat these as historical diagnostics under equal weighting, not forecasts or guarantees.

## Slide 39: Baseline Comparison

**Main idea:** Filtering changes the opportunity set relative to the full active universe under the same allocation rule.

- Baseline: full active universe without filtering
- Conservative universe reduced mean realized risk by 52.2%.
- Conservative universe had lower realized risk in every test month.
- Aggressive universe increased mean realized risk by 37.6%.
- Aggressive universe had 73.9% higher historical cumulative return.

## Slide 40: Conclusion & Limitations

**Main idea:** Section divider introducing conclusions, limitations, and direct answers to the research questions.

## Slide 41: Key Limitations

**Main idea:** Summarize the study's key boundaries and what the results do not establish.

**Diagram reminder:** Use the limitation callouts to distinguish historical evidence, market scope, risk-first selection, and the mock equal-weight allocation stage.

**Notes warning:** The current PowerPoint notes repeat the research-question answers used on slide 42; they do not contain a limitations script.

## Slide 42: Research Question Answers

**Main idea:** Answer all three research questions directly from the test evidence.

- RQ1: Yes; PPO supported dynamic risk-based universe selection.
- RQ2: Yes; the selected universes produced distinct profile-oriented risk behavior.
- RQ3: Filtering changed realized risk and return behavior relative to the full universe under equal weighting.

## Slide 43: Future Work

**Main idea:** Section divider introducing extensions beyond the thesis scope.

## Slide 44: Live Data and Forward Testing

**Main idea:** Extend the offline historical pipeline to live data, recurring feature construction, and forward monitoring.

**Diagram reminder:** Explain the future loop from market-data APIs through monthly features and selection to live monitoring.

## Slide 45: Return-Aware Suitability

**Main idea:** Add return information only after risk suitability has established acceptable boundaries.

- Risk suitability defines the boundaries.
- Return awareness adds context inside those boundaries.
- Exact integration requires further research.

## Slide 46: Key References

**Main idea:** Identify the core academic references and historical data sources supporting the thesis.

- Markowitz (1952) — Portfolio Selection
- Wang et al. (2020) — Deep-Learning Portfolio Preselection
- Ma et al. (2021) — Return Prediction and Portfolio Optimization
- Chaweewanchon & Chaysiri (2022) — Predictive Stock Selection
- Atta Mills & Anyomi (2022) — DEA-Based Portfolio Preselection
- Investing.com — historical market-series CSV data
- Egyptian Exchange (EGX) — macroeconomic data

## Slide 47: Q&A

**Main idea:** Invite examiner questions.

## Slide 48: Thank You

**Main idea:** Close the presentation.

## Slide 49: Asset Universe Selection Formulas

**Main idea:** Appendix reference for the percentile formulas used to form conservative, balanced, and aggressive universes.

**Diagram reminder:** Use only if asked to formalize how predicted ranks are mapped to profile-specific asset sets.
