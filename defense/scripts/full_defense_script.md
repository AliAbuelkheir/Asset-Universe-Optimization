# Full Defense Script

This is the main slide-by-slide speaking script for the current defense topic slide map.

## Time Summary

- Opening: ~45 sec
- Problem Statement: ~2 min 30 sec
- Literature Review: ~2 min 5 sec
- Proposed Solution Overview: ~1 min
- Methodology: Data And Risk Target: ~1 min 35 sec
- Methodology: PPO Ranking Model: ~3 min 40 sec
- Experiments: ~1 min 45 sec
- Results: ~1 min 35 sec
- Conclusion: ~25 sec
- Future Work: ~40 sec
- References: ~15 sec
- Main talk total: ~16 min 30 sec
- Optional appendix backup: ~3 min to 4 min if needed in discussion

## Slide 1 - Title

**Talk track**

Good morning. My name is Ali, and this presentation covers my bachelor thesis on Asset Universe Selection based on Investor Profile in Portfolio Optimization using AI.

The core idea is simple. Portfolio construction starts with two connected questions: which assets should be considered in the first place, and then how much should be allocated to each asset?

My thesis studies that earlier selection stage. Before deciding final weights, it ranks assets according to their predicted risk behavior, then uses that ranking to build candidate universes that better match the investor profile.

**Transition**
I'll start with a quick roadmap.

**Estimated time**
~25 sec

## Slide 2 - Talk Roadmap

**Talk track**

I will begin with the problem definition, then the literature gap, then the proposed solution, followed by methodology, experiments, results, conclusion, and future work.

**Transition**
So firstly, what is the actual portfolio problem I am trying to solve?

**Estimated time**
~20 sec

## Slide 3 - The Fixed-Universe Assumption

**Talk track**

Many portfolio optimization methods make a fixed-universe assumption. This means the investable assets are treated as already known and fixed before optimization begins.

After that assumption is made, the main task becomes how to allocate weights inside that predefined universe.

But there is an earlier decision that also matters: which assets should even enter the allocation stage. If that first decision is weak, even a strong optimizer is limited by the menu of assets it receives.

My thesis focuses on this earlier step. It studies asset-universe selection before allocation.

**Slide bullets**

- Fixed-universe assumption: the investable assets are predefined before optimization.
- The optimizer only decides weights inside that fixed asset menu.
- This thesis studies the earlier question: which assets should enter the universe?

**Estimated time**
~30 sec

## Slide 4 - Why Risk-Tolerance Universe Selection Matters

**Talk track**

In the Egyptian investment market, many investors are highly sensitive to instability because of inflation, currency fluctuations, and broader economic uncertainty. That often pushes investors toward assets they see as more stable, such as gold, bank certificates, or foreign currency exposure.

This thesis takes a risk-first view of suitability. The goal is to align the starting asset universe with the investor profile, then study how that universe performs based on historical diagnostics.

So conservative, balanced, and aggressive investors should not always begin from the same candidate universe. Market conditions change, and the risk behavior of assets changes with them.

**Estimated time**
~35 sec

## Slide 5 - Scope And Asset Universe

**Talk track**

The thesis works in an Egyptian mixed-asset setting. The scored asset universe includes 91-day treasury bills, 5-year government bonds, EGX30 ETF, EGX30 constituent stocks, Real Estate Investment Trust exposure, and gold.

USD/EGP conversion rate and CPI are used as macro-context inputs. They are not treated as selected portfolio assets in the main universe, but they help describe the market environment around each monthly decision.

This setup is more realistic than an equities-only view because it gives the model defensive assets, growth assets, real-asset exposure, and macro context in the same system.

**Transition**
With that scope in place, the thesis asks three direct research questions.

**Estimated time**
~35 sec

## Slide 6 - Research Questions

**Talk track**

The first question asks whether AI and machine learning can support dynamic asset-universe selection before allocation using predictions of each asset's realized-risk behavior.

The second asks whether the selected universes actually align with conservative, balanced, and aggressive investor profiles.

The third asks how the proposed risk-tolerance-based universes compare with the full active universe when both are evaluated under the same equal-weight historical simulation rule.

Together, these questions keep the project focused on asset suitability for the investor.

**Transition**
Before presenting my method, I need to place it inside the literature.

**Estimated time**
~30 sec

## Slide 7 - Classical Allocation Context

**Talk track**

Classical portfolio construction usually treats the problem as a return-risk weighting problem. Markowitz and later allocation methods mainly study how to divide weights once the investable universe is already known.

That literature is still important here because it gives the benchmark logic behind equal-weight and MVO allocation comparisons. But it usually assumes the asset set has already been defined.

**Estimated time**
~30 sec

## Slide 8 - AI/ML Preselection Context

**Talk track**

In the literature, AI and machine learning have already been used as a filtering step before portfolio optimization. The model helps decide which stocks should enter the portfolio construction stage.

However, these papers select assets using expected price, expected return, profitability, or related performance signals. After that, the selected candidates move into an optimizer.

Risk measures such as Sharpe ratio, volatility, drawdown, or robustness usually appear later during weight allocation, optimization, or evaluation. That is why the literature gap remains open for risk-tolerance-oriented universe selection.

**Estimated time**
~35 sec

## Slide 9 - DEA Preselection Paper

**Talk track**

One useful exception is the DEA paper, because it also splits the process into two stages. First, assets are screened and qualified. Then weight allocation happens after that.

In Atta Mills and Anyomi, DEA is used to rank candidate stocks by efficiency under uncertainty. Standard deviation appears as the key risk-related input, while the rest of the screening still leans toward return and robustness considerations.

So the paper supports pre-allocation screening, but the main filter is still efficiency. It is also a statistical DEA method, not an AI model that learns investor-specific risk-tolerance universes.

**Transition**
After that, the remaining gap becomes easier to state clearly.

**Estimated time**
~30 sec

## Slide 10 - RL And Investor Personalization Gap

**Talk track**

RL in finance is often used for trading decisions, rebalancing policies, or direct allocation weights. Personalization research often maps investor profiles to advice, products, funds, or final portfolio choices.

My thesis connects these two directions differently. It predicts asset risk behavior first, then uses that ranking to build profile-specific asset universes.

That is the main gap the project tries to fill.

**Transition**
Now I can show the whole contribution in one view before going into technical details.

**Estimated time**
~30 sec

## Slide 11 - Contribution In One View

**Talk track**

The full pipeline has four linked parts: point-in-time data engineering, monthly predicted risk ranking, profile-specific asset-universe mapping, and historical diagnostic evaluation.

Each part has a separate responsibility. That separation keeps the claims clean and makes the system easier to defend slide by slide.

**Transition**
The next slide explains the exact prediction the model produces each month.

**Estimated time**
~30 sec

## Slide 12 - What The Model Predicts

**Talk track**

For every active asset in a specific month, the model outputs a predicted risk score. Those scores are then sorted ascendingly, from lower predicted risk to higher predicted risk.

The main goal is ranking quality. What matters most is whether safer and riskier assets are ordered well relative to each other inside that month.

This ranked list becomes the foundation for investor-specific asset selection later.

**Estimated time**
~30 sec

## Slide 13 - Raw Data Engineering

**Talk track**

The raw financial inputs include date, price, OHLC fields, and volume for each asset. From those inputs, I build a monthly point-in-time panel for the model.

An important detail is that treasury bill and bond series are quoted as yields. So before calculating returns and risk features, those quotes are converted into fixed-maturity price proxies.

I also include macroeconomic context through USD/EGP conversion rate and Consumer Price Index, or CPI, because market conditions influence how risky the active universe is in each month.

**Transition**
That cleaned daily layer then feeds the monthly state panel used by the model.

**Estimated time**
~30 sec

## Slide 14 - Point-In-Time Monthly Panel

**Talk track**

One row in the panel means one active asset in one month. So the model sees the market as a changing set of asset states.

The point-in-time rule is strict. Features for a month only use information available up to that month, and assets are never backfilled before they truly existed or before reliable data is available.

The panel keeps asset identity as metadata, but the model input itself uses only features. That helps the policy learn behavior patterns instead of memorizing asset names.

**Transition**
Once the panel exists, the next question is what information each row actually contains.

**Estimated time**
~30 sec

## Slide 15 - Feature Families

**Talk track**

I present the features in families because that is easier to follow than reading a long list one by one. The main families are risk behavior, liquidity, technical state, market sensitivity, and macro context.

The target, realized risk, combines three finance components: realized volatility, downside deviation, and maximum drawdown. Each component is rank-normalized within the same month. This means every component is converted into a relative comparison among the active assets in that month, so the model compares assets against the alternatives that actually existed at that time.

The final realized-risk target is the equal-weight average of those normalized components. That target is what the PPO model tries to rank assets by.

**Transition**
Before explaining why I used reinforcement learning, I will quickly define what reinforcement learning means in this project.

**Estimated time**
~35 sec

## Slide 16 - What Is Reinforcement Learning

**Talk track**

Reinforcement learning is a learning setup where a model improves through interaction and feedback. The model observes a state, takes an action, receives a reward, and then updates its policy.

The policy is basically the model's decision rule. The reward function tells the model what behavior should improve. If an action leads to a better reward, the model adjusts its internal policy so similar actions become more likely in the future.

In this thesis, the state is one monthly active asset universe. The action is assigning risk scores to the assets. The reward tells the model how good the final monthly ranking was compared with realized risk. Over training, the model adapts so its future rankings are more likely to receive higher reward.

**Transition**
With that idea clear, I can explain why this problem fits reinforcement learning.

**Estimated time**
~35 sec

## Slide 17 - Why Reinforcement Learning

**Talk track**

Reinforcement learning fits this problem for three main reasons. First, the available assets change from month to month. Second, the model scores the full monthly set together rather than treating each asset as an isolated prediction. Third, the reward is calculated only after the complete universe has been ranked.

The figure shows how these ideas form one monthly decision environment. The state is the active asset universe and its features. The action is assigning one risk score to every active asset, and the resulting scores create the predicted monthly ranking.

The predicted ranking is then compared with the realized-risk ranking to calculate the reward. That feedback is used to update the scoring policy, so it can produce better rankings in future decision months.

**Transition**
Among reinforcement learning methods, I used PPO because it gives a more controlled training update.

**Estimated time**
~30 sec

## Slide 18 - Why PPO

**Talk track**

PPO is a policy-gradient method that updates the policy in a controlled way. The clipping step is especially useful here because financial months can be noisy, and large jumps in policy behavior can quickly become unstable.

It also uses an actor-critic architecture that makes the updates more stable, especially in difficult months where the ranking problem is less clear.

**Transition**
Before opening the actor-critic architecture, I first need to define what one PPO decision looks like in this thesis.

**Estimated time**
~30 sec

## Slide 19 - PPO Episode Format

**Talk track**

One PPO episode represents one complete monthly ranking decision.

The episode begins with the month's fixed-size asset-feature tensor and an active-asset mask. The mask identifies the rows representing assets that are actually available during that month.

The PPO policy assigns one continuous risk score between zero and one to every active asset. These scores are then sorted to create the predicted low-to-high risk ranking.

Finally, the complete predicted ranking is compared with the realized-risk ranking for the same month. That comparison produces one reward for the entire monthly decision, rather than a separate reward for each asset.

**Transition**
To make this work across months with different numbers of available assets, the model needs padding and masking.

**Estimated time**
~25 sec

## Slide 20 - Variable Universe And Masking

**Talk track**

The practical challenge is that every month has a different number of active assets. A neural network still needs a consistent tensor shape, so the input is padded to a fixed size.

The mask tells the model which rows are real and which rows are just padding. That way, padded rows do not pollute action sampling, learning, or reward calculations.

This is what lets the system work with a changing investable universe in a technically clean way.

**Transition**
With the monthly decision and masking logic clear, I will explain the actor-critic architecture.

**Estimated time**
~25 sec

## Slide 21 - Actor-Critic Architecture

**Talk track**

The architecture starts by encoding every asset with the same row encoder. Those row representations are then pooled into one context vector that summarizes the active month.

The actor combines each asset representation with that monthly context and outputs one risk score per asset. In parallel, the critic uses the pooled context to estimate the expected reward for the complete monthly decision.

The actor's scores first form a ranking, and that complete ranking is evaluated to produce the actual monthly reward. PPO compares this actual reward with the critic's expected reward. The difference is called the advantage, and it tells PPO how the policy should learn from that month.

This structure combines asset-level scoring with a month-level baseline.

**Transition**
The final training signal then comes from the reward function.

**Estimated time**
~30 sec

## Slide 22 - Reward Definition

**Talk track**

The reward is computed after the entire monthly universe is scored. Seventy percent of it measures how close the predicted ranking was to the realized-risk ranking, and thirty percent measures how close the predicted score values were to the target values.

The first part uses Spearman rank correlation because the thesis is mainly a ranking problem. The second part uses MSE to discourage the model from placing all assets too close together, where a very small score change could easily flip the ranking.

So the reward keeps the ranking objective central while still giving the scores some shape.

**Transition**
Once the model produces a ranked list, I can map that list into profile-specific asset universes.

**Estimated time**
~25 sec

## Slide 23 - Profile-Specific Asset Universes

**Talk track**

After ranking, the predicted positions are converted into rank percentiles. These percentiles are then used to form three profile-specific asset universes.

The conservative asset universe uses the lowest 30 percent of predicted-risk assets. The balanced asset universe uses the middle 20 to 80 percent band. The aggressive asset universe uses the highest 30 percent of predicted-risk assets.

The overlap is intentional because some assets can reasonably fit two neighboring investor profiles depending on where they sit in the ranked distribution.

**Transition**
With the full method defined, the next step is to show how I tested it.

**Estimated time**
~30 sec

## Slide 24 - Chronological Split Design

**Talk track**

The evaluation follows a strict chronological split to control leakage. Training covers 2011-01 to 2021-12, and this is where the PPO policy learns from historical months.

Inner validation covers 2022-01 to 2022-12, and it is used for intermediate model-selection checks. Validation covers 2023-01 to 2025-02, and it guides the final framework, feature, and hyperparameter choices. Test covers 2025-03 to 2026-01, and it is held back for final reporting only.


**Transition**
Before feature tuning, I first had to decide which PPO framework made the most sense.

**Estimated time**
~40 sec

## Slide 25 - Framework Selection

**Talk track**

Several formulations were compared before locking the final framework. The goal was to understand which input structure actually fits the ranking problem, while keeping the base feature set fixed.

I tested whether the model should look at only the most recent month or a three-month feature window. I also tested whether adding pooled context from the whole active universe in that month improved the model's performance.

I also explored variants that included daily price information more directly, but in these trials that appeared to add noise and did not improve validation performance. The three-month view with active-universe context had the best performance, so it was promoted as the final framework for the next stage.

**Transition**
After the framework was locked, I moved to feature tuning and hyperparameter tuning phases.

**Estimated time**
~35 sec

## Slide 26 - Feature And Hyperparameter Selection

**Talk track**

Feature selection followed a sequential process. I first used drop-one-feature ablations on the fixed feature set, then confirmed promising changes with three-seed runs. After that, I tested redesigned feature-family alternatives and new additions such as the downside-tail ratio.

Hyperparameter tuning came after the framework and feature decisions. I used Optuna, a hyperparameter optimization tool that runs multiple parameter trials, evaluates them on the validation objective, and uses earlier results to suggest better configurations.

The main selection metric was validation reward, with validation Spearman kept as the ranking-quality guardrail.

**Transition**
Once the model was locked, I evaluated it in two connected stages.

**Estimated time**
~35 sec

## Slide 27 - Evaluation Logic

**Talk track**

The first stage evaluates ranking quality directly by comparing predicted risk ranks with realized-risk ranks, mainly using Spearman correlation.

The second stage evaluates what those rankings mean for investor groups by forming conservative, balanced, and aggressive universes and comparing them with the full active universe under the same equal-weight rule.

Equal weighting keeps the focus on universe selection. Return metrics are reported, but the main reading remains risk separation.

**Transition**
Now I can show the core results.

**Estimated time**
~25 sec

## Slide 28 - Ranking Quality

**Talk track**

The promoted model achieved a test reward of about 0.7545 and a test Spearman diagnostic of about 0.669. Those are the main ranking-quality signals at the thesis level.

Another useful detail is that reward stayed positive across all 11 test months. That gives a more stable picture than looking at a single average alone.

So before even forming profile-specific asset universes, the monthly ranking behavior is already meaningful.

**Transition**
The strongest thesis result appears when those rankings are converted into profile-specific asset universes.

**Estimated time**
~25 sec

## Slide 29 - Profile-Universe Risk Separation

**Talk track**

The profile-specific asset universes separated realized risk in the expected order. The full universe mean realized risk was 0.500, the conservative universe was 0.239, the balanced universe was 0.536, and the aggressive universe was 0.688.

The monotonic ordering held in all 11 out of 11 test months. That is the cleanest evidence that the model can produce distinct investor-oriented universes from predicted ranks.

From a financial point of view, the main message is straightforward: the conservative asset universe behaved materially safer, while the aggressive asset universe carried clearly higher realized risk.

**Transition**
After risk separation, we can look carefully at the return side of the same test window.

**Estimated time**
~30 sec

## Slide 30 - Economic Diagnostics

**Talk track**

Using the same equal-weight allocation rule, cumulative return in the test window was 49.59 percent for the full universe, 29.91 percent for the conservative universe, 50.17 percent for the balanced universe, and 86.24 percent for the aggressive universe.

The aggressive universe also carried higher volatility and a deeper drawdown. So the higher return came with visibly higher risk exposure.

That is why I present these numbers as historical diagnostics. They help interpret the selected universes economically, but they do not prove future outperformance.

**Transition**
That brings us to the baseline comparison.

**Estimated time**
~25 sec

## Slide 31 - Baseline Comparison

**Talk track**

The baseline here is the full active universe under the same equal-weight rule. Keeping the allocation rule fixed makes the comparison much cleaner.

Under that comparison, conservative-universe filtering materially reduced realized risk versus the full universe, while aggressive-universe filtering produced higher realized risk and stronger return participation in the short test window.

So the filtering stage itself already changes the opportunity set in a meaningful, investor-specific way.

**Transition**
With that evidence in place, I can answer the research questions directly.

**Estimated time**
~25 sec

## Slide 32 - Research Question Answers

**Talk track**

RQ1 asks whether AI and machine learning can support dynamic asset-universe selection before allocation using asset-level realized-risk prediction. In this historical setting, the answer is yes: the PPO model produced meaningful realized-risk ranking behavior across the changing active universe.

RQ2 asks whether the selected universes align with conservative, balanced, and aggressive investor profiles. For this question, also yes: the predicted-rank universes produced distinct realized-risk groups in the expected order.

RQ3 asks how the proposed risk-tolerance-based universes compare with the full active universe under the same equal-weight historical simulation rule. The answer is that the filtered universes behaved differently from the full active universe, especially in realized risk, while return remained a historical diagnostic rather than a future-performance claim.

These answers stay measured, but they are still strong enough to defend the contribution clearly.

**Transition**
The last content section is future work.

**Estimated time**
~40 sec

## Slide 33 - Live Data And Forward Testing

**Talk track**

These are possible next steps beyond the thesis scope. One future direction is live forward testing: connecting the pipeline to live market-data APIs, rebuilding the monthly features over time, and monitoring how the selected asset universes behave in real conditions.

That would matter because historical evidence is useful, but forward observation is a stronger test of stability.

**Transition**
There is also a natural extension on the objective side.

**Estimated time**
~20 sec

## Slide 34 - Return-Aware Suitability

**Talk track**

The current thesis defines suitability mainly through investor risk tolerance. However, risk alone may not provide a complete view of whether an asset is suitable for an investor.

Return information could later be considered within the set of choices that already satisfy the investor's risk requirements. The exact implementation would require further research, but the main principle is that return awareness should refine suitability without overriding the investor's risk limits.

**Transition**
I'll close the main talk with the core references behind the framing.

**Estimated time**
~20 sec

## Slide 35 - Key References

**Talk track**

These are the five core references most directly supporting the problem framing, the preselection literature, and the baseline context for this thesis.

I keep the slide short during the talk and leave the fuller literature detail to the written thesis and discussion.

**Estimated time**
~15 sec

## Appendix A - Full Feature List

**Talk track**

If I am asked what the model actually sees, this appendix is the direct answer. The final feature set includes `egarch_vol`, `downside_dev`, `max_drawdown`, `volume`, `atr_pct_20`, `beta_to_egx30`, `price_to_sma20`, `rsi_14`, `distance_to_3m_high`, `usd_vol`, `cpi_trajectory`, and the additive `downside_tail_ratio_3m`.

I would explain them by family: risk and downside behavior, liquidity, technical state, market sensitivity, and macro context. That grouping is easier to defend than reading names without interpretation.

**Estimated time**
~40 sec

## Appendix B - Data Cleaning Rules

**Talk track**

This appendix is for data-quality questions. The most important points are yield-to-price proxy conversion for money-market and bond series, authoritative returns from cleaned prices, forward-fill limits, and exclusion of pre-listing history.

If someone asks why the pipeline is trustworthy, these are the rules I would emphasize first.

**Estimated time**
~35 sec

## Appendix C - PPO Hyperparameters

**Talk track**

This slide stores the tuned PPO settings and helps if the discussion becomes more technical. The main speaking focus here would be clipping, mask-aware learning, and why one episode equals one decision month.

I would use it only if the discussion moves toward implementation depth.

**Estimated time**
~35 sec

## Appendix D - Universe Mapping Method Ablation

**Talk track**

This appendix compares the tested universe-mapping alternatives: non-overlapping thirds and several overlapping percentile bands.

The key takeaway is that the selected overlapping-tail mapping gave the strongest high-minus-low realized-risk spread while keeping monotonic ordering across all 11 test months, which is why it became the reported method.

**Estimated time**
~35 sec

## Appendix E - Finance Q&A Backup

**Talk track**

This appendix is a compact backup for common finance questions: what realized risk means, why it combines volatility, downside deviation, and maximum drawdown, why EGX30 is used, why equal weight is used for the benchmark, and why historical diagnostics stay limited in interpretation.

These answers should stay short and confident because they support the main talk rather than replace it.

**Estimated time**
~35 sec
