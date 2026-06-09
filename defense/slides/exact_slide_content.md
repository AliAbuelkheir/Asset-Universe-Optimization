# Exact Defense Slide Content

Status: working copy for manual PowerPoint editing.

Purpose: this file contains the exact visible slide content for the current defense deck. Use it as the copy source when manually editing the PPTX. It is not speaker notes and it should stay shorter than the full script.

## Main Slides

### Slide 1 - Title

Title:
Asset Universe Selection Based on Investor Profiles in Portfolio Optimization Using AI

Subtitle:
Bachelor Thesis Defense

Presenter:
Ali Abuelkheir

Memory cue:
Risk-aware asset-universe selection before portfolio allocation

### Slide 2 - Talk Roadmap

Title:
Talk Roadmap

Bullets:
- Problem statement and literature gap
- Proposed ranked-risk solution
- Methodology and experiments
- Results, conclusion, and future work

### Slide 3 - The Fixed-Universe Assumption

Title:
The Fixed-Universe Assumption

Claim:
Many portfolio methods assume the investable universe is fixed before optimization begins.

Bullets:
- Fixed-universe assumption: the investable assets are predefined before optimization.
- The optimizer only decides weights inside that fixed asset menu.
- This thesis studies the earlier question: which assets should enter the universe?

### Slide 4 - Why Risk-Tolerance Universe Selection Matters

Title:
Why Risk-Tolerance Universe Selection Matters

Claim:
Different investor profiles should not always begin from the same asset universe.

Bullets:
- Egyptian investors face inflation, currency movement, and market uncertainty
- Asset risk behavior changes as market conditions change
- Suitability is treated as risk behavior first, not only expected return

### Slide 5 - Scope And Asset Universe

Title:
Scope And Asset Universe

Claim:
The project uses an Egyptian mixed-asset setting rather than an equities-only universe.

Table:
| Category | Role in the system |
| --- | --- |
| 91-day treasury bills | Defensive money-market exposure |
| 5-year government bonds | Fixed-income exposure |
| EGX30 ETF and EGX30 stocks | Egyptian equity-market exposure |
| REIT and gold | Real-asset exposure |
| USD/EGP and CPI | Macro-context inputs, not selected portfolio assets |

### Slide 6 - Research Questions

Title:
Research Questions

Bullets:
- RQ1: Can AI/ML support dynamic asset-universe selection before allocation using asset-level realized-risk prediction?
- RQ2: Do selected universes align with conservative, balanced, and aggressive investor profiles?
- RQ3: How do selected universes compare with the full active universe under the same equal-weight diagnostic rule?

### Slide 7 - Classical Allocation Context

Title:
Classical Allocation Context

Claim:
Classical portfolio theory mainly studies how to allocate weights after the universe is known.

Bullets:
- Markowitz-style methods frame allocation as a return-risk weighting problem
- MVO remains useful as benchmark logic
- The thesis focuses on the pre-allocation selection step

### Slide 8 - AI/ML Preselection Context

Title:
AI/ML Preselection Context

Claim:
AI/ML has been used for asset preselection, but usually through return-oriented signals.

Bullets:
- Existing work filters assets before optimization
- Common signals include expected price, expected return, or profitability
- Risk metrics usually appear later in weighting, optimization, or evaluation

### Slide 9 - DEA Preselection Paper

Title:
DEA Preselection Paper

Claim:
DEA is a useful two-stage screening example, but it is statistical rather than AI/ML.

Bullets:
- Atta Mills and Anyomi screen assets before allocation
- Standard deviation appears as the key risk-related input
- The method mainly filters by efficiency using a statistical DEA approach rather than AI-based ranking

### Slide 10 - RL And Investor Personalization Gap

Title:
RL And Investor Personalization Gap

Claim:
The gap is to learn asset-level risk behavior first, then map it to investor-specific universes.

Bullets:
- RL finance work often targets trading, rebalancing, or direct weights
- Personalization often maps profiles to advice, products, or final portfolios
- This thesis ranks asset risk first, then builds profile-specific universes

### Slide 11 - Contribution In One View

Title:
Contribution In One View

Claim:
The system separates data engineering, risk ranking, profile mapping, and historical diagnostics.

Bullets:
- Point-in-time data engineering
- Monthly predicted risk ranking
- Profile-specific universe mapping
- Equal-rule historical diagnostic evaluation

### Slide 12 - What The Model Predicts

Title:
What The Model Predicts

Claim:
For each month, the model scores active assets by predicted risk behavior.

Bullets:
- One predicted risk score per active asset
- Assets sorted from lower predicted risk to higher predicted risk
- Ranking quality matters more than exact score values

### Slide 13 - Raw Data Engineering

Title:
Raw Data Engineering

Claim:
The raw market data is cleaned into a point-in-time model-ready panel.

Bullets:
- Inputs include date, price, OHLC fields, and volume
- T-bill and bond yield quotes are converted into price proxies
- USD/EGP and CPI add macro market context

### Slide 14 - Point-In-Time Monthly Panel

Title:
Point-In-Time Monthly Panel

Claim:
Each row represents one active asset in one decision month.

Bullets:
- Features use only information available up to that month
- Assets are not backfilled before they existed
- Asset identity stays metadata and is excluded from model inputs

### Slide 15 - Feature Families

Title:
Feature Families

Claim:
Features describe asset behavior, while realized risk defines the ranking target.

Bullets:
- Input families: risk behavior, liquidity, technical state, market sensitivity, macro context
- Realized risk combines volatility, downside deviation, and maximum drawdown
- Components are rank-normalized within each month and averaged equally

### Slide 16 - What Is Reinforcement Learning

Title:
What Is Reinforcement Learning

Claim:
RL learns a policy through state, action, reward, and update.

Bullets:
- State: one monthly active asset universe
- Action: assign risk scores to active assets
- Reward: compare the final monthly ranking with realized risk

### Slide 17 - Why Reinforcement Learning

Title:
Why Reinforcement Learning

Claim:
The ranking problem is a repeated monthly decision over a changing active universe.

Bullets:
- Available assets change from month to month
- The model scores a full monthly set, not isolated assets
- Reward arrives after the complete universe is ranked

### Slide 18 - Why PPO

Title:
Why PPO

Claim:
PPO gives controlled policy updates for noisy financial ranking decisions.

Bullets:
- Clipping limits unstable policy jumps
- Actor-critic structure stabilizes learning
- Suitable for month-level reward feedback

### Slide 19 - PPO Episode Format

Title:
PPO Episode Format

Claim:
One PPO episode equals one monthly ranking decision.

Bullets:
- Observation: active-asset feature tensor plus mask
- Action: one continuous risk score for each real asset row
- Reward: quality of the full monthly predicted ranking

### Slide 20 - Variable Universe And Masking

Title:
Variable Universe And Masking

Claim:
Masking lets the model handle months with different numbers of active assets.

Bullets:
- Padding gives a consistent tensor shape
- The mask separates real asset rows from padding rows
- Padded rows do not affect actions, learning, or reward calculations

### Slide 21 - Actor-Critic Architecture

Title:
Actor-Critic Architecture

Claim:
The architecture combines asset-level scoring with month-level context.

Bullets:
- Shared row encoder reads every active asset
- Pooled context summarizes the active month
- Actor outputs risk scores; critic estimates expected monthly reward

### Slide 22 - Reward Definition

Title:
Reward Definition

Claim:
The reward keeps ranking quality central while giving predicted scores discipline.

Formula:
Reward = 0.7 * Spearman rank correlation + 0.3 * (1 - MSE)

Bullets:
- Spearman rewards correct ordering
- MSE discourages collapsed or poorly shaped scores
- Reward is computed after the whole monthly universe is scored

### Slide 23 - Profile-Specific Asset Universes

Title:
Profile-Specific Asset Universes

Claim:
Predicted ranks are mapped into investor-profile asset universes.

Bullets:
- Conservative: lowest 30% predicted-risk assets
- Balanced: 20% to 80% predicted-risk band
- Aggressive: highest 30% predicted-risk assets

### Slide 24 - Chronological Split Design

Title:
Chronological Split Design

Claim:
The evaluation uses time-ordered splits to control leakage.

Table:
| Split | Date range | Purpose |
| --- | --- | --- |
| Training | 2011-01 to 2021-12 | Learn the PPO policy |
| Inner validation | 2022-01 to 2022-12 | Intermediate model-selection checks |
| Validation | 2023-01 to 2025-02 | Final framework, feature, and hyperparameter choices |
| Test | 2025-03 to 2026-01 | Final reporting only |

### Slide 25 - Framework Selection

Title:
Framework Selection

Claim:
The promoted framework uses a monthly PPO setup with a three-month view and active-universe context.

Bullets:
- Compared one-month versus three-month feature windows
- Compared asset-row features alone versus pooled active-universe context
- Daily price variants appeared noisy and did not improve validation performance

### Slide 26 - Feature And Hyperparameter Selection

Title:
Feature And Hyperparameter Selection

Claim:
Feature and hyperparameter choices were selected through staged validation checks.

Bullets:
- Feature tests used drop-one ablations, seed confirmation, redesigned feature families, and additions
- Optuna tuned PPO hyperparameters through validation trials
- Validation reward was primary; validation Spearman was the ranking-quality guardrail

### Slide 27 - Evaluation Logic

Title:
Evaluation Logic

Claim:
Evaluation separates ranking quality from portfolio diagnostics.

Bullets:
- Stage 1: compare predicted risk ranks with realized-risk ranks
- Stage 2: compare profile universes with the full active universe
- Equal weighting keeps the focus on universe selection

### Slide 28 - Ranking Quality

Title:
Ranking Quality

Claim:
The promoted model produced meaningful monthly realized-risk ranking behavior.

Metrics:
| Metric | Test result |
| --- | --- |
| Test reward | 0.7545 |
| Test Spearman diagnostic | 0.6690 |
| Positive reward months | 11 / 11 |

### Slide 29 - Profile-Universe Risk Separation

Title:
Profile-Universe Risk Separation

Claim:
Profile-specific universes separated realized risk in the expected order.

Metrics:
| Universe | Mean realized risk |
| --- | --- |
| Full active universe | 0.500 |
| Conservative universe | 0.239 |
| Balanced universe | 0.536 |
| Aggressive universe | 0.688 |

Callout:
Monthly monotonicity: 11 / 11 test months

### Slide 30 - Economic Diagnostics

Title:
Economic Diagnostics

Claim:
Historical return diagnostics differed across universes, but do not prove future outperformance.

Metrics:
| Universe | Test cumulative return |
| --- | --- |
| Full active universe | 49.59% |
| Conservative universe | 29.91% |
| Balanced universe | 50.17% |
| Aggressive universe | 86.24% |

Callout:
Higher aggressive return came with higher volatility and deeper drawdown.

### Slide 31 - Baseline Comparison

Title:
Baseline Comparison

Claim:
Filtering changed the opportunity set under the same equal-weight rule.

Bullets:
- Baseline: full active universe with filtering off
- Conservative filtering reduced realized risk versus the full universe
- Aggressive filtering increased realized risk and had stronger historical return participation

### Slide 32 - Research Question Answers

Title:
Research Question Answers

Bullets:
- RQ1: In this historical setting, PPO supported dynamic asset-universe selection using realized-risk prediction
- RQ2: Predicted-rank universes aligned with conservative, balanced, and aggressive profiles
- RQ3: Filtered universes differed from the full active universe, especially in realized risk

Footer cue:
Return remains a historical diagnostic, not a future-performance claim.

### Slide 33 - Live Data And Forward Testing

Title:
Live Data And Forward Testing

Claim:
Forward testing is a natural next validation step beyond the thesis scope.

Bullets:
- Connect the pipeline to live market-data APIs
- Rebuild monthly features as new data arrives
- Monitor selected-universe behavior in live market conditions

### Slide 34 - Return-Aware Suitability

Title:
Return-Aware Suitability

Claim:
Return awareness can provide a more complete view of suitability while risk limits remain primary.

Visual:
- Large outer boundary: Risk-Suitable Choices
- Inner element: Return Awareness
- Outcome: More Complete Investor Suitability
- Guardrail: Risk limits remain primary

### Slide 35 - Key References

Title:
Key References

References:
- Markowitz (1952), Portfolio Selection
- Wang et al. (2020), Portfolio Formation with Preselection Using Deep Learning from Long-Term Financial Data
- Ma et al. (2021), Portfolio Optimization with Return Prediction Using Deep Learning and Machine Learning
- Chaweewanchon and Chaysiri (2022), Markowitz Mean-Variance Portfolio Optimization with Predictive Stock Selection Using Machine Learning
- Atta Mills and Anyomi (2022), A Hybrid Two-Stage Robustness Approach to Portfolio Construction under Uncertainty

## Appendix Slides

### Appendix A - Full Feature List

Title:
Full Feature List

Features:
`egarch_vol`, `downside_dev`, `max_drawdown`, `volume`, `atr_pct_20`, `beta_to_egx30`, `price_to_sma20`, `rsi_14`, `distance_to_3m_high`, `usd_vol`, `cpi_trajectory`, `downside_tail_ratio_3m`

Families:
- Risk, volatility, and downside-tail behavior
- Liquidity and technical state
- Market sensitivity and macro context

### Appendix B - Data Cleaning Rules

Title:
Data Cleaning Rules

Bullets:
- Convert money-market and bond yield quotes into price proxies
- Compute authoritative returns from cleaned prices, not vendor `Change %`
- Limit forward-fill and exclude pre-listing history
- Preserve point-in-time construction to reduce leakage risk

### Appendix C - PPO Hyperparameters

Title:
PPO Hyperparameters

Bullets:
- PPO clipping supports stable policy updates
- Mask-aware learning handles variable active universes
- One episode equals one decision month
- Use this slide only for implementation-depth questions

### Appendix D - Universe Mapping Method Ablation

Title:
Universe Mapping Method Ablation

Bullets:
- Compared non-overlapping thirds and overlapping percentile bands
- Selected overlapping-tail mapping for reported results
- Chosen mapping preserved 11 / 11 monotonic test months
- Use this slide if asked whether thresholds were arbitrary

### Appendix E - Finance Q&A Backup

Title:
Finance Q&A Backup

Questions:
- What is realized risk?
- Why combine volatility, downside deviation, and maximum drawdown?
- Why use EGX30?
- Why use an equal-weight diagnostic?
- Why do historical diagnostics not prove future performance?
