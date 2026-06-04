# Defense Topic-To-Slide Map

Status: working map for trial feedback
Goal: one subtopic is approximately one slide. Combine marked slides if timing is tight.

Each slide has a short `Talk focus` section. Expand these into the script later.

## Navigation

- [0. Opening](#0-opening)
- [1. Problem Statement](#1-problem-statement)
- [2. Literature Review](#2-literature-review)
- [3. Proposed Solution Overview](#3-proposed-solution-overview)
- [4. Methodology: Data And Risk Target](#4-methodology-data-and-risk-target)
- [5. Methodology: PPO Ranking Model](#5-methodology-ppo-ranking-model)
- [6. Experiments](#6-experiments)
- [7. Results](#7-results)
- [8. Conclusion](#8-conclusion)
- [9. Optional Future Work](#9-optional-future-work)
- [10. References](#10-references)
- [Appendix Candidates](#appendix-candidates)

## 0. Opening

Purpose: set the scope quickly and make it clear that the project is about risk-aware asset-universe selection before final portfolio allocation.

### Slide 1 - Title

Talk focus:
- Introduce Myself
- State the thesis title and  supervisor.
- Frame the work as a pre-allocation portfolio-management component: selecting an asset universe that matches investor risk tolerance.
- Clarify from the beginning that the system ranks assets by predicted risk behavior.

### Slide 2 - Talk Roadmap

Talk focus:
- Walk the audience through the defense structure: problem, literature gap, proposed solution, methodology, experiments, results, conclusion, and future work.

## 1. Problem Statement

Purpose: explain why the project exists and why asset-universe selection is a meaningful step before optimization.

### Slide 3 - The Fixed-Universe Assumption

Talk focus:
- Explain that many portfolio methods begin after the candidate assets have already been chosen.
- Argue that this leaves an important earlier decision untreated: which assets should even enter the allocation stage.
- Position the thesis as studying this earlier stage, not replacing classical portfolio allocation.

### Slide 4 - Why Risk-Tolerance Universe Selection Matters

Talk focus:
- Explain why conservative, balanced, and aggressive investors should not necessarily start from the same candidate universe.
- Connect the problem to changing market conditions: inflation, exchange-rate movement, equity volatility, and drawdowns can shift asset risk behavior over time.
- Emphasize that suitability is treated as risk behavior first, not only expected return.
- Add the Egyptian-market motivation: instability can make investors more risk-conscious and increase demand for stable assets.
- State that the selected universe should respond to changing market conditions rather than remain static.

### Slide 5 - Scope And Asset Universe

Talk focus:
- Define the Egyptian mixed-asset setting used in the project.
- Cover the included asset categories: 91-day treasury bills, 5-year government bonds, EGX30, EGX30 constituent stocks, REIT exposure, gold in EGP, USD/EGP, and CPI.
- Explain why this is more realistic than using equities only: the investor can compare defensive, growth, real-asset, and macro-sensitive exposures.
- Compare each asset category with its benchmark or market role using a compact **table**.

### Slide 6 - Research Questions

Talk focus:
- Present the three research questions as in the thesis contract.
- RQ1 asks whether AI/ML can support dynamic asset-universe selection using realized-risk ranking.
- RQ2 asks whether the selected universes align with conservative, balanced, and aggressive profiles.
- RQ3 asks how the selected universes compare against the full active universe under the same equal-weight diagnostic rule.

## 2. Literature Review

Purpose: keep the literature short and use it only to justify the project gap.

### Slide 7 - Classical Allocation Context

Talk focus:
- Briefly introduce classical allocation as a return-risk weighting problem, starting with Markowitz-style portfolio construction and MVO.
- Keep MVO central because the simulator includes filtered-universe ( Profile ) and full-universe MVO benchmarks.
- Mention that later approaches improve risk modeling, constraints, or robustness, but usually still assume the investable universe is already defined.
- Use this slide to separate the thesis from final weight optimization: this project focuses on what comes before it.

### Slide 8 - AI/ML Preselection Context

Talk focus:
- Explain that AI/ML has been used for asset filtering and preselection before optimization.
- State that the reviewed AI/ML preselection papers usually filter stocks by expected price, expected return, or profitability.
- Clarify that risk metrics such as Sharpe ratio, volatility, drawdown, or robustness usually appear later during weighting, optimization, or evaluation.


### Slide 9 - DEA Preselection Paper

Talk focus:
- Explain DEA briefly as an efficiency-screening method.
- Explain the main DEA comparison: Atta Mills and Anyomi (2022) use a two-stage portfolio-construction approach under uncertainty.
- Stage 1 used a DEA model to rank candidate stocks by efficiency and filter qualified stocks before allocation.
- Standard deviation is the risk-related DEA input used where the other three DEA inputs were return oriented.
- Clarify that DEA is not AI/ML in the same sense as predictive stock-selection models, and it is still an efficiency filter rather than learned investor-risk-tolerance ranking.
- Note that the paper studies stocks from the Shenzhen and Shanghai Stock Exchanges, not the Egyptian mixed-asset market setting used in this thesis.

### Slide 10 - RL And Investor Personalization Gap

Talk focus:
- Explain that RL in finance often learns trading decisions, rebalancing policies, or allocation weights directly.
- Explain that personalization research often maps investor profiles to advice, products, funds, or final portfolios.
- State the thesis gap clearly: learn an asset-level realized-risk ranking first, then map that ranking into profile-specific asset universes.

## 3. Proposed Solution Overview

Purpose: give the audience the full system view before the methodology details.

### Slide 11 - Contribution In One View

Talk focus:
- Present the pipeline as four linked contributions: point-in-time data engineering, monthly predicted risk ranking, profile universe selection, and historical diagnostic evaluation.
- Explain that each step has a separate responsibility so the claims stay clean.
- Use this slide as the high-level map the audience can return to during the technical section.
- Reuse the methodology-chapter pipeline figure here.
- At this overview stage, present the model as an AI risk-scoring component. Introduce RL and PPO later in the methodology section.

### Slide 12 - What The Model Predicts

Talk focus:
- Explain that the model outputs the predicted risk score for every active asset in a given decision month.
- Clarify that assets are sorted from low predicted risk to high predicted risk.
- Clarify the goal is correct asset ranking and not exact scores

## 4. Methodology: Data And Risk Target

Purpose: show that the financial data and target are built carefully enough for the RL model to be meaningful.

### Slide 13 - Raw Data Engineering

Talk focus:
- Explain the raw inputs: date, price, OHLC and volume.
- Emphasize that cleaned prices are used to compute authoritative returns.
- Explain the special handling for treasury bill and bond yield quotes: they are converted into fixed-maturity price proxies before return and risk calculations.
- Mention macro inputs such as USD/EGP and CPI as market-context features.

### Slide 14 - Point-In-Time Monthly Panel

Talk focus:
- Define one row as one active `(Date, AssetID)` monthly state.
- Explain that this panel was designed to support variable available assets per month
- Explain that assets are not backfilled before they existed or before reliable data is available.
- Stress the point-in-time rule: monthly features use only information available up to that month.
- Mention that asset identity metadata is excluded from model inputs, So the model only see the features not the asset so it cannot remember specific risk scores for specific assets

### Slide 15 - Feature Families

Talk focus:
- Group the model inputs by meaning rather than reading every feature mechanically.
- Risk behaviour, Liquidity, Technical state and market sensitivity
- Explain that the features describe asset behavior, not asset identity.
#### Realized Risk:
- Explain the three finance components: realized volatility captures general variability, downside deviation focuses on harmful negative movement, and maximum drawdown captures peak-to-trough loss.
- Explain that each component is rank-normalized within the same month so assets are compared only against the active alternatives at that time.
- Explain that the final target is the equal weighted average of the normalized component into `realized_risk`.

## 5. Methodology: PPO Ranking Model

Purpose: explain the reinforcement-learning formulation in a way that proves you understand the full PPO process, while staying tied to the finance objective.

### Slide 16 - What Is Reinforcement Learning

Talk focus:
- Explain reinforcement learning as a learning loop: the model observes a state, takes an action, receives a reward, and updates its policy.
- Explain that the reward function tells the model what behavior should improve.
- Explain that the policy is the model's decision rule, and training changes its weights so future actions are more likely to earn higher reward.
- Keep the explanation short and connect it directly to monthly asset-risk ranking.

### Slide 17 - Why Reinforcement Learning

Talk focus:
- Explain that the problem is not a single fixed-asset prediction problem; every month is a new decision over a changing active universe.
- Frame each month as an environment state: available assets each with its set of features
- Explain the model action: assign one risk-ranking score to every active asset, then evaluate the full monthly ordering.
- Explain why RL fits the thesis objective: the reward is computed at the decision-month level after the entire universe is ranked, so the model learns a scoring policy for monthly ranking decisions rather than independent asset labels.
- Clarify that RL is used for dynamic risk-ranking and universe selection

### Slide 18 - Why PPO

Talk focus:
- Explain PPO as the chosen policy-gradient method for learning the monthly ranking policy.
- Mention clipping explicitly: PPO limits how much the policy can change in one update, which helps avoid unstable jumps when financial months are noisy or unusually hard to rank.
- Introduce actor-critic only at a high level here: PPO also uses a critic to stabilize updates.
- Defer the full actor-critic architecture until after the audience understands what one monthly PPO decision contains.

### Slide 19 - PPO Episode Format

Talk focus:
- Define one PPO episode as one monthly decision.
- Explain the observation: a tensor of active-asset features plus an active-asset mask.
- Explain why the mask appears in the observation: every decision month can have a different number of available assets.
- Explain the action: one bounded continuous risk score per asset slot between [0,1].
- Explain the environment response: active assets are sorted by predicted score and compared against realized-risk ranks for that month.
- Use a figure showing the input as `N` active assets, each with its feature vector.

### Slide 20 - Variable Universe And Masking

Talk focus:
- Explain the practical problem: each month has a different number of active assets as some assets were offered publicly later than others like stocks.
- Padding gives a fixed tensor shape for neural-network training.
- Masks ensure padded rows do not affect the model during training.
- Make this slide examiner-friendly: masking is what lets the model handle a changing investable universe without pretending every month has the same assets.
- Transition from here into actor-critic: once the monthly tensor and mask are clear, the architecture can be explained without confusion.

### Slide 21 - Actor-Critic Architecture

Talk focus:
- Explain the architecture in four parts.
- A shared row encoder reads each asset using the same parameters.
- A pooled context vector summarizes the active month using mask-aware aggregation.
- The actor head outputs asset-level risk-ranking scores.
- The critic head estimates the expected monthly reward from the pooled active-universe context and stabilizes PPO learning.
- Explain advantage as the difference between the received monthly reward and the critic's expected reward, then state that PPO uses it to update the policy.
- Use a figure for the PPO internals, including the shared row-encoder MLP, actor-head MLP, critic-head MLP, and reward signal.


### Slide 22 - Reward Definition

Talk focus:
- Explain that the reward is computed after the whole monthly universe is scored.
- Present the reward formula: `0.7 * Spearman rank correlation + 0.3 * (1 - MSE)`.
- Explain the role of Spearman: it rewards correct ordering, which is the main thesis objective.
- Explain the role of MSE: it adds score discipline so the model is not only rewarded for relative order.

### Slide 23 - Profile-Specific Asset Universes

Talk focus:
- Explain that after assets are sorted, predicted ranks are converted into rank percentiles.
- Present the mapping without using internal rule names.
- Conservative asset universe: lowest 30% predicted-risk assets.
- Balanced asset universe: 20% to 80% predicted-risk assets.
- Aggressive asset universe: highest 30% predicted-risk assets.
- Explain why overlap is acceptable: suitability categories can share some middle-border assets and do not need to be strictly mutually exclusive.
- Figure used in thesis can be used here



## 6. Experiments

Purpose: show how the project was tested and why the selected model configuration is defensible.

### Slide 24 - Chronological Split Design

Talk focus:
- Present the chronological split as part of the leakage-control design.
- Training: 2011-01 to 2021-12; used to learn the PPO policy.
- Inner validation: 2022-01 to 2022-12; used for intermediate model-selection checks.
- Validation: 2023-01 to 2025-02; used to guide final framework, feature, and hyperparameter choices.
- Test: 2025-03 to 2026-01; held back for final reporting only.
- Explain that the test period is only used for final reporting.

### Slide 25 - Framework Selection

Talk focus:
- Explain that several formulations were compared before choosing the final one.
- State that framework testing used a fixed base feature set so the comparison measured the input/architecture formulation rather than changing features at the same time.
- Explain the trials as design choices, not code names: one-month versus three-month feature windows, asset-row features alone versus pooled active-universe context, and whether daily price information should be included more directly.
- Explain that adding daily price information introduced too much noise and dropped performance.
- State the promoted framework in plain language: a monthly PPO setup with a three-month view and active-universe context, because it best matched the thesis objective and evaluation behavior.

### Slide 26 - Feature And Hyperparameter Selection

Talk focus:
- Explain that feature selection followed a sequential evaluation process after the framework was locked.
- Stage 1: run leave-one-out / drop-one-feature tests on the base feature set to check whether each feature added value relative to the baseline.
- Stage 2: confirm any apparent drop-feature winner with additional seeds instead of promoting it from one seed only.
- Stage 3: test redesigns and replacements for individual feature families, such as alternate windows or definitions.
- Stage 4: test additions such as the downside-tail ratio to improve identification of high-risk assets.
- Explain that hyperparameters were tuned with Optuna, which runs multiple parameter trials, evaluates them on the validation objective, and uses earlier trial results to guide later suggestions.
- Explain the selection rule: validation reward was primary and validation Spearman was the guardrail.

### Slide 27 - Evaluation Logic

Talk focus:
- Explain the two-stage evaluation.
- First, evaluate predicted risk ranks against realized-risk ranks mainly using Spearman rank correlation.
- Second, evaluate conservative, balanced, and aggressive selected universes against the full active universe when used in similar portfolio allocation methods.
- Explain why equal weighting is used: it keeps the comparison focused on universe selection rather than weight optimization.
- State that return metrics are secondary historical diagnostics after risk metrics like volatility and downside deviation.

## 7. Results

Purpose: show that the model achieved the main thesis claim: predicted-rank asset universes produced distinct realized-risk behavior in the historical test.

### Slide 28 - Ranking Quality

Talk focus:
- Present the main model-ranking diagnostics.
- Test reward was about `0.7545`.
- Test Spearman diagnostic was about `0.6690`.
- Reward stayed positive across all 11 test months.

### Slide 29 - Profile-Universe Risk Separation

Talk focus:
- Present the strongest thesis result: the profile-specific asset universes separated realized risk in the expected order.
- Full universe mean realized risk: `0.500`.
- Conservative asset universe: `0.239`.
- Balanced asset universe: `0.536`.
- Aggressive asset universe: `0.688`.
- Monthly monotonicity on test: `11/11`.
- Explain the finance meaning: the conservative asset universe behaved materially safer by the target definition, while the aggressive asset universe captured higher-risk assets.

### Slide 30 - Economic Diagnostics

Talk focus:
- Present the historical cumulative return diagnostics carefully.
- Mention briefly that all universes use the same equal-weight allocation rule.
- Full universe: `49.59%`.
- Conservative asset universe: `29.91%`.
- Balanced asset universe: `50.17%`.
- Aggressive asset universe: `86.24%`.
- Explain that the aggressive asset universe also had higher volatility and larger drawdown, so the higher return is not a free improvement.
- Say explicitly that this is historical risk-return behavior in the test window, not future outperformance proof.

### Slide 31 - Baseline Comparison

Talk focus:
- Define the baseline as the filter-off full active universe under the same equal-weight rule.
- Explain that using the same equal-weight rule isolates the effect of asset universe filtering.
- Summarize the key comparison: conservative-universe filtering reduced realized risk versus the full universe; aggressive-universe filtering increased realized risk and had higher historical return in the short test window.
- Connect this result back to the goal: the system created risk-profile-specific candidate universes.

## 8. Conclusion

Purpose: answer the research questions directly and leave the audience with the exact contribution.

### Slide 32 - Research Question Answers

Talk focus:
- Include each research question and its answer, not only the RQ label.
- RQ1 question: Can AI/ML support dynamic asset-universe selection before allocation using asset-level realized-risk prediction?
- RQ1 answer: Yes in this historical setting; PPO produced meaningful realized-risk ranking behavior across the changing active universe.
- RQ2 question: Do the selected universes align with conservative, balanced, and aggressive investor risk-tolerance profiles?
- RQ2 answer: Yes; predicted-rank asset universes created distinct realized-risk groups in the expected order.
- RQ3 question: How do the proposed risk-tolerance-based asset universes compare with the full active-universe baseline under the same equal-weight historical simulation rule?
- RQ3 answer: Filtered universes differed from the full active universe, especially in realized risk, while return stayed a historical diagnostic rather than a future-performance claim.
- Keep the wording measured and avoid claiming general market superiority.


## 9. Optional Future Work

Purpose: explain optional next steps beyond the thesis scope.

### Slide 33 - Live Data And Forward Testing

Talk focus:
- Frame this as an optional future step, not a required part of the thesis result.
- Explain that one possible next validation step is live forward testing.
- Connect the pipeline to live market-data APIs.
- Rebuild monthly features as new data arrives through an ETL pipeline.
- Monitor ranking and selected-universe behavior in the live market.

### Slide 34 - Return-Aware Suitability Extensions

Talk focus:
- Frame this as another optional extension beyond the current risk-first objective.
- Explain that the current objective is risk suitability.
- Future work may add return-aware diagnostics after risk-ranked universes are formed to act as a secondary filter.
- Be careful with phrasing: this does not mean replacing risk ranking with return chasing.


## 10. References

Purpose: show the academic foundations without spending defense time on a long literature dump.

### Slide 35 - Key References

This should only act as a references slide listing the references below without description.
Talk focus:
- Present only the five core references listed below. Leave the descriptions and full bibliography in the written thesis.
- Markowitz (1952), *Portfolio Selection*
- Wang et al. (2020), *Portfolio Formation with Preselection Using Deep Learning from Long-Term Financial Data*
- Ma et al. (2021), *Portfolio Optimization with Return Prediction Using Deep Learning and Machine Learning*
- Chaweewanchon and Chaysiri (2022), *Markowitz Mean-Variance Portfolio Optimization with Predictive Stock Selection Using Machine Learning*
- Atta Mills and Anyomi (2022), *A Hybrid Two-Stage Robustness Approach to Portfolio Construction under Uncertainty*

## Appendix Candidates

Purpose: keep detailed backup material ready for questions without overloading the main presentation.

### Appendix A - Full Feature List

Talk focus:
- Keep exact final input feature names and window definitions here:
  `egarch_vol`, `downside_dev`, `max_drawdown`, `volume`, `atr_pct_20`,
  `beta_to_egx30`, `price_to_sma20`, `rsi_14`,
  `distance_to_3m_high`, `usd_vol`, `cpi_trajectory`,
  and `downside_tail_ratio_3m`.
- Group them into the corrected families:
  risk, volatility, and downside-tail behavior; liquidity; technical state;
  market sensitivity; and macro context.
- Add a short finance interpretation for each feature and explain why it helps
  the PPO rank assets by realized-risk behavior.
- Use this if asked how the model sees risk, liquidity, trend, macro context, or downside-tail behavior.

### Appendix B - Data Cleaning Rules

Talk focus:
- Explain yield-to-price proxy construction for money-market and bond series.
- Explain why authoritative returns are computed from cleaned prices instead of vendor `Change %`.
- Explain forward-fill rules and pre-listing exclusion.
- Use this for questions about data reliability and leakage.

### Appendix C - PPO Hyperparameters

Talk focus:
- Store the final tuned PPO parameters here.
- Explain why PPO clipping matters for stable updates.
- Explain why masking matters for the variable active universe.
- Use this if the CS examiner asks for implementation depth.

### Appendix D - Universe Mapping Method Ablation

Talk focus:
- Compare the universe-mapping alternatives tested: non-overlapping thirds and several overlapping percentile bands.
- Explain why the selected overlapping-tail mapping was selected for reported results.
- Use this if asked whether the universe thresholds were arbitrary.

### Appendix E - Finance Q&A Backup

Talk focus:
- Prepare short answers for expected finance questions.
- What is realized risk?
- Why combine volatility, downside deviation, and max drawdown?
- Why use EGX30?
- Why use an equal-weight diagnostic?
- Why do historical diagnostics not prove future performance?
