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
- [9. Future Work](#9-future-work)
- [10. References](#10-references)
- [Appendix Candidates](#appendix-candidates)

## 0. Opening

Purpose: set the scope quickly and make it clear that the project is about risk-aware asset-universe selection before final portfolio allocation.

### Slide 1 - Title

Talk focus:
- State the thesis title, presenter, supervisor, and project context.
- Frame the work as a pre-allocation portfolio-management component: selecting an asset universe that matches investor risk tolerance.
- Clarify from the beginning that the system ranks assets by predicted risk behavior; it is not claiming guaranteed future returns.

### Slide 2 - Talk Roadmap

Talk focus:
- Walk the audience through the defense structure: problem, literature gap, proposed solution, methodology, experiments, results, conclusion, and future work.
- Tell them the methodology section will be the most detailed part because it explains the full RL/PPO process.
- Mention that finance interpretation will appear throughout, especially in the target, bucket, and result slides.

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

### Slide 5 - Scope And Asset Universe

Talk focus:
- Define the Egyptian mixed-asset setting used in the project.
- Cover the included asset categories: 91-day treasury bills, 5-year government bonds, EGX30, EGX30 constituent stocks, REIT exposure, gold in EGP, USD/EGP, and CPI.
- Explain why this is more realistic than using equities only: the investor can compare defensive, growth, real-asset, and macro-sensitive exposures.

### Slide 6 - Research Questions

Talk focus:
- Present the three research questions as the thesis contract.
- RQ1 asks whether AI/ML can support dynamic asset-universe selection using realized-risk ranking.
- RQ2 asks whether the selected universes align with conservative, balanced, and aggressive profiles.
- RQ3 asks how the selected universes compare against the full active universe under the same equal-weight diagnostic rule.

## 2. Literature Review

Purpose: keep the literature short and use it only to justify the project gap.

### Slide 7 - Classical Allocation Context

Talk focus:
- Briefly introduce classical allocation as a return-risk weighting problem, starting with Markowitz-style portfolio construction.
- Mention that later approaches improve risk modeling, constraints, or robustness, but usually still assume the investable universe is already defined.
- Use this slide to separate the thesis from final weight optimization: this project focuses on what comes before it.

### Slide 8 - AI/ML Preselection Context

Talk focus:
- Explain that AI/ML has been used for asset filtering and preselection before optimization.
- Summarize the common signals: expected return, price movement, Sharpe-like metrics, efficiency, robustness, or optimizer quality.
- Identify the gap: these approaches usually do not directly select assets according to investor risk-tolerance suitability.

### Slide 9 - RL And Investor Personalization Gap

Talk focus:
- Explain that RL in finance often learns trading decisions, rebalancing policies, or allocation weights directly.
- Explain that personalization research often maps investor profiles to advice, products, funds, or final portfolios.
- State the thesis gap clearly: learn an asset-level realized-risk ranking first, then map that ranking into profile-specific asset universes.

## 3. Proposed Solution Overview

Purpose: give the audience the full system view before the methodology details.

### Slide 10 - Contribution In One View

Talk focus:
- Present the pipeline as four linked contributions: point-in-time data engineering, PPO-based monthly risk ranking, investor-profile universe selection, and historical diagnostic evaluation.
- Explain that each step has a separate responsibility so the claims stay clean.
- Use this slide as the high-level map the audience can return to during the technical section.

### Slide 11 - What The Model Predicts

Talk focus:
- Explain that the model outputs one risk-ranking score for every active asset in a given decision month.
- Clarify that assets are sorted from low predicted risk to high predicted risk.
- Define the target in finance terms: a composite realized-risk rank built from realized volatility, downside deviation, and maximum drawdown.

### Slide 12 - What The Model Does Not Claim

Talk focus:
- State the boundaries clearly before showing results.
- The model does not optimize final portfolio weights.
- It does not prove future return outperformance.
- It does not use asset identity metadata as a shortcut.
- It keeps risk ranking, risk-tolerance mapping, and allocation as separate stages.

## 4. Methodology: Data And Risk Target

Purpose: show that the financial data and target are built carefully enough for the RL model to be meaningful.

### Slide 13 - Raw Data Engineering

Talk focus:
- Explain the raw inputs: date, price, OHLC, volume, and quoted change fields from market-data files.
- Emphasize that cleaned prices are used to compute authoritative returns instead of trusting vendor change fields.
- Explain the special handling for treasury bill and bond yield quotes: they are converted into fixed-maturity price proxies before return and risk calculations.
- Mention macro inputs such as USD/EGP and CPI as market-context features.

### Slide 14 - Point-In-Time Monthly Panel

Talk focus:
- Define one row as one active `(Date, AssetID)` monthly state.
- Explain why the long monthly panel is needed: each month has a variable active asset universe.
- Explain that assets are not backfilled before they existed or before reliable data is available.
- Stress the point-in-time rule: monthly features use only information available up to that month.

### Slide 15 - Feature Families

Talk focus:
- Group the model inputs by meaning rather than reading every feature mechanically.
- Risk and volatility: EGARCH volatility, downside deviation, and max drawdown.
- Liquidity: volume.
- Technical state: ATR percentage, moving-average distance, RSI, and distance from recent high.
- Market sensitivity and macro context: beta to EGX30, USD volatility, CPI trajectory, and downside-tail contribution.
- Explain that the features describe asset behavior, not asset identity.

### Slide 16 - Composite Realized-Risk Target

Talk focus:
- Explain the three finance components: realized volatility captures general variability, downside deviation focuses on harmful negative movement, and maximum drawdown captures peak-to-trough loss.
- Explain that each component is rank-normalized within the same month so assets are compared only against the active alternatives at that time.
- Explain that the final target averages the normalized component ranks into `realized_risk`.
- Make the claim precise: the model learns ordering of realized risk, not a perfectly calibrated numeric risk forecast.

### Slide 17 - Leakage Controls

Talk focus:
- Explain why leakage control is central: the model must not learn from future information.
- Cover chronological train, validation, and test splits.
- Mention that asset identity metadata is excluded from model inputs.
- Explain that synthetic forward-filled rows are not allowed to create fake OHLC, volume, or target evidence.
- State that test results are reserved for final reporting only.

## 5. Methodology: PPO Ranking Model

Purpose: explain the reinforcement-learning formulation in a way that proves you understand the full PPO process, while staying tied to the finance objective.

### Slide 18 - PPO Episode Format

Talk focus:
- Define one PPO episode as one monthly decision.
- Explain the observation: a padded tensor of active-asset features plus an active-asset mask.
- Explain the action: one bounded continuous risk score per asset slot.
- Explain the environment response: active assets are sorted by predicted score and compared against realized-risk ranks for that month.

### Slide 19 - Reward Definition

Talk focus:
- Explain that the reward is computed after the whole monthly universe is scored.
- Present the reward formula: `0.7 * Spearman rank correlation + 0.3 * (1 - MSE)`.
- Explain the role of Spearman: it rewards correct ordering, which is the main thesis objective.
- Explain the role of MSE: it adds score discipline so the model is not only rewarded for relative order.

### Slide 20 - Variable Universe And Masking

Talk focus:
- Explain the practical problem: each month has a different number of active assets.
- Padding gives a fixed tensor shape for neural-network training.
- Masks ensure padded rows do not affect action sampling, log probabilities, entropy, PPO loss, reward, or evaluation metrics.
- Make this slide examiner-friendly: masking is what lets the model handle a changing investable universe without pretending every month has the same assets.

### Slide 21 - Actor-Critic Architecture

Talk focus:
- Explain the architecture in four parts.
- A shared row encoder reads each asset using the same parameters.
- A pooled context vector summarizes the active month using mask-aware aggregation.
- The actor head outputs asset-level risk-ranking scores.
- The critic head estimates the expected monthly reward and stabilizes PPO learning.

### Slide 22 - Investor Bucket Mapping

Talk focus:
- Explain that after assets are sorted, predicted ranks are converted into rank percentiles.
- Present the selected `tail_30_overlap` bucket rule.
- Conservative universe: lowest 30% predicted-risk assets.
- Balanced universe: 20% to 80% predicted-risk assets.
- Aggressive universe: highest 30% predicted-risk assets.
- Explain why overlap is acceptable: suitability categories can share some middle-border assets and do not need to be strictly mutually exclusive.

## 6. Experiments

Purpose: show how the project was tested and why the selected model configuration is defensible.

### Slide 23 - Chronological Split Design

Talk focus:
- Present the chronological split as part of the leakage-control design.
- Training: 2011-01 to 2021-12.
- Inner validation: 2022-01 to 2022-12.
- Validation: 2023-01 to 2025-02.
- Test: 2025-03 to 2026-01.
- Explain that the test period is only used for final reporting.

### Slide 24 - Framework Selection

Talk focus:
- Explain that several formulations were compared before choosing the final one.
- Monthly PPO without context tested the basic monthly-ranking setup.
- Monthly PPO with pooled active-universe context added information about the whole decision month.
- Daily-flat and daily-CNN variants were explored but not selected.
- State the final choice: monthly PPO with pooled context, because it best matched the thesis objective and evaluation behavior.

### Slide 25 - Feature And Hyperparameter Selection

Talk focus:
- Explain that feature selection was iterative, not arbitrary.
- Mention feature drops, replacements, window changes, and additive tail-risk features.
- State that the final feature set kept risk, liquidity, technical, beta, and macro families.
- Mention that `downside_tail_ratio_3m` was added in the final feature set.
- State that PPO tuning selected the final `refined50` configuration.

### Slide 26 - Evaluation Logic

Talk focus:
- Explain the two-stage evaluation.
- First, evaluate predicted risk ranks against realized-risk ranks.
- Second, evaluate conservative, balanced, and aggressive selected universes against the full active universe.
- Explain why equal weighting is used: it keeps the comparison focused on universe selection rather than weight optimization.
- State that return metrics are secondary historical diagnostics.

## 7. Results

Purpose: show that the model achieved the main thesis claim: predicted-rank buckets produced distinct realized-risk behavior in the historical test.

### Slide 27 - Ranking Quality

Talk focus:
- Present the main model-ranking diagnostics.
- Test reward was about `0.7545`.
- Test Spearman diagnostic was about `0.6690`.
- Reward stayed positive across all 11 test months.
- Discuss October 2025 as the weakest month, framing it as a stress case and limitation rather than hiding it.

### Slide 28 - Risk-Bucket Separation

Talk focus:
- Present the strongest thesis result: the buckets separated realized risk in the expected order.
- Full universe mean realized risk: `0.500`.
- Low-risk bucket: `0.239`.
- Medium-risk bucket: `0.536`.
- High-risk bucket: `0.688`.
- Monthly monotonicity on test: `11/11`.
- Explain the finance meaning: the conservative bucket behaved materially safer by the target definition, while the aggressive bucket captured higher-risk assets.

### Slide 29 - Economic Diagnostics

Talk focus:
- Present the historical cumulative return diagnostics carefully.
- Full universe: `49.59%`.
- Low-risk bucket: `29.91%`.
- Medium-risk bucket: `50.17%`.
- High-risk bucket: `86.24%`.
- Explain that the high-risk bucket also had higher volatility and larger drawdown, so the higher return is not a free improvement.
- Say explicitly that this is historical risk-return behavior in the test window, not future outperformance proof.

### Slide 30 - Baseline Comparison

Talk focus:
- Define the baseline as the filter-off full active universe under the same equal-weight rule.
- Explain that using the same equal-weight rule isolates the effect of PPO filtering.
- Summarize the key comparison: low-risk filtering reduced realized risk versus the full universe; high-risk filtering increased realized risk and had higher historical return in the short test window.
- Connect this result back to the goal: the system created risk-profile-specific candidate universes.

## 8. Conclusion

Purpose: answer the research questions directly and leave the audience with the exact contribution.

### Slide 31 - Research Question Answers

Talk focus:
- Answer each research question in one controlled sentence.
- RQ1: PPO supported dynamic realized-risk ranking in this historical setting.
- RQ2: Predicted-rank buckets created distinct realized-risk groups.
- RQ3: Filtered universes differed from the full active universe under the same equal-weight diagnostic rule.
- Keep the wording measured and avoid claiming general market superiority.

### Slide 32 - Main Contribution

Talk focus:
- Summarize the technical contribution: leakage-controlled data pipeline, composite realized-risk target, and masked PPO actor-critic ranker for a variable active universe.
- Summarize the portfolio-management contribution: investor-profile universe construction before allocation.
- Summarize the evaluation contribution: selection diagnostics are separated from allocation and return claims.

### Slide 33 - Limitations

Talk focus:
- Present limitations confidently, as future research boundaries rather than weaknesses to hide.
- The final test window is 11 months.
- Results are specific to the Egyptian market, available instruments, and selected proxies.
- Some non-equity exposures are represented through benchmark or proxy series.
- The high-risk return result is not proof of return prediction.
- No production questionnaire or live user study is claimed.

## 9. Future Work

Purpose: explain the most realistic next steps after the thesis.

### Slide 34 - Live Data And Forward Testing

Talk focus:
- Explain that the next major validation step is live forward testing.
- Connect the pipeline to live market-data APIs.
- Rebuild monthly features as new data arrives.
- Monitor ranking and bucket behavior without breaking point-in-time discipline.

### Slide 35 - Return-Aware Suitability Extensions

Talk focus:
- Explain that the current objective is risk suitability.
- Future work can add return-aware diagnostics after risk buckets are formed.
- Be careful with phrasing: this does not mean replacing risk ranking with return chasing.
- Mention that this is especially relevant for medium and high-risk investor profiles.

### Slide 36 - Downstream Allocation Experiments

Talk focus:
- Explain that selected universes can later feed final portfolio optimizers.
- Compare equal weighting, mean-variance optimization, risk parity, or other allocation methods after selection.
- Emphasize that selection and weight optimization should remain analytically separate so the contribution stays measurable.

### Slide 37 - Other Markets And Asset Classes

Talk focus:
- Explain that external validity should be tested beyond the Egyptian dataset.
- Possible extensions include US equities, broader multi-asset universes, regional markets, or crypto.
- Discuss what may change: liquidity, volatility structure, available macro variables, and market depth.

## 10. References

Purpose: show the academic foundations without spending defense time on a long literature dump.

### Slide 38 - Key References

Talk focus:
- Group references by role rather than listing every citation orally.
- Classical allocation and risk: Markowitz, Black-Litterman, CVaR, and risk parity.
- AI/ML preselection before optimization.
- Investor personalization and robo-advisory studies.
- RL and DRL portfolio-management literature.
- PPO methodology.
- Closest comparison context: investor-specific grouping or personalization work.

## Appendix Candidates

Purpose: keep detailed backup material ready for questions without overloading the main presentation.

### Appendix A - Full Feature List

Talk focus:
- Keep exact final input feature names and window definitions here.
- Add a short finance interpretation for each feature.
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

### Appendix D - Bucket Method Ablation

Talk focus:
- Compare the bucket rules tested: `tail_30_overlap`, `tercile_no_overlap`, `overlap_40_50`, and `wide_overlap_50_60`.
- Explain why `tail_30_overlap` was selected for reported results.
- Use this if asked whether the bucket thresholds were arbitrary.

### Appendix E - Finance Q&A Backup

Talk focus:
- Prepare short answers for expected finance questions.
- What is realized risk?
- Why combine volatility, downside deviation, and max drawdown?
- Why use EGX30?
- Why use an equal-weight diagnostic?
- Why do historical diagnostics not prove future performance?
