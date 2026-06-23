# Defense Speaker Script

> Source: `defense/slides/defense.pptx` speaker notes. Regenerate with `$update-defense-docs` after the deck changes.
> Note text is preserved as written in PowerPoint; empty notes are stated explicitly.

## Slide 1: Portfolio Optimization

Good morning. My name is Ali, and this presentation covers my bachelor thesis on Asset Universe Selection based on Investor Profile in Portfolio Optimization.

The core idea is simple. Portfolio construction starts with two connected questions: which assets should be considered in the first place, and then how much should be allocated to each asset?

My thesis studies that earlier selection stage. It ranks assets according to their predicted risk behavior, then uses that ranking to build candidate universes that match the investor profile.

Transition

I'll start with a quick roadmap.

## Slide 2: Roadmap

Script

I will begin with the problem definition, then the literature gap, then the proposed solution, followed by methodology, experiments, results, conclusion, and future work.

Transition: So firstly, what is the actual portfolio problem I am trying to solve?

## Slide 3: Problem Definition

_No speaker notes in the PowerPoint deck._

## Slide 4: The Fixed-Universe Assumption

Script

Many portfolio optimization methods assume a fixed asset universe. After that assumption is made, the main task becomes how to allocate weights inside that predefined universe.

But there is an earlier decision that also matters: which assets should enter the allocation stage. If that first decision is weak, even a strong optimizer is limited by the menu of assets it receives.

## Slide 5: Untitled visual slide

In the Egyptian investment market, inflation, currency movements, and changing economic conditions can alter the volatility and behavior of different assets. For example, an asset suitable for a conservative investor in one period may not remain suitable under different conditions.

This video shows it directly. The x axis represent the assets, and its height is its risk rank in that month. As the months advance, watch the ranking reshuffle.

Transition: As seen in the video, asset's risk is not persistent which is exactly why the investable universe has to be selected based on market conditions.

## Slide 6: Why Universe Selection Matters?

Therefore, this thesis takes a risk-first view on suitability to ensure that only assets consistent with the investor’s risk tolerance are considered. The resulting filtered universe provides the foundation for the next portfolio construction decisions involving other suitability metrics like returns, diversification, and allocation.

## Slide 7: Scope and Asset Universe

The thesis works with a mixed Egyptian asset universe rather than focusing only on equities. The universe includes fixed-income securities represented by 91-day treasury bills and 5-year government bonds. Egyptian equities are represented by individual EGX30 companies, while the EGX30 index is included separately as the overall market benchmark. The universe also includes real-estate exposure through a EGX Real Estate index and gold exposure through the price of 24-karat gold in Egypt.Transition

With the raw asset universe now defined, the thesis asks three direct research questions.

## Slide 8: Research Questions

Script

The first question asks whether Reinforcement learning can support dynamic asset-universe selection before allocation using predicted risk behavior.

The second asks whether the selected universes actually align with conservative, balanced, and aggressive investor profiles.

The third asks how the candidate Universes compare with the full active universe when both are evaluated under the same allocation rule.

Transition: Before presenting my method, Lets dig into the Literature review.

## Slide 9: Literature Review

_No speaker notes in the PowerPoint deck._

## Slide 10: Classical Allocation Context

Script

Classical portfolio construction usually treats the problem as a return-risk weighting problem. Markowitz and later allocation methods mainly study how to divide weights once the asset universe is already known.

That literature is still important here because it gives the benchmark logic behind equal-weight allocation comparisons.

## Slide 11: AI/ML Preselection Context

In the literature, AI and machine learning have already been used as a filtering step before portfolio optimization. The model helps decide which stocks should enter the portfolio construction stage.

However, these papers select assets using expected price, expected return, profitability, etc. After that, the selected universe move into the allocation optimizer where risk measures such as Sharpe ratio, volatility or drawdown usually appear. That is why the literature gap remains open for risk-oriented universe selection.

## Slide 12: DEA Preselection Paper

One useful exception is the paper by Atta Mills and Anyomi, which uses Data Envelopment Analysis, or DEA, to rank candidate stocks using multiple efficiency metrics.

Among these metrics, standard deviation is the only risk-related input.

The paper therefore supports screening assets before portfolio allocation, but its main objective remains efficiency. It also uses a statistical approach rather than an AI model that learns predicted risk behavior.

## Slide 13: RL And Investor Personalization

RL in finance is often used for trading decisions or direct allocation weights. Personalization research often maps investor profiles to advice, products, funds, or full portfolio choices.

My thesis connects these two directions differently. It predicts asset risk behavior first using Reinforcement Learning, then uses that prediction to build personalized asset universes.

Transition: Now I can show the whole contribution before going into technical details.

## Slide 14: Proposed Solution

_No speaker notes in the PowerPoint deck._

## Slide 15: Contribution In One View

The full pipeline has four linked parts:

Data Layer: Collects, cleans, and transforms the raw financial data into the model input.

Construction and Learning Layer: The model estimates each asset’s future risk behavior and ranks the assets accordingly. This ranking becomes the foundation used in the Selection layer

Asset Universe Selection Layer: Uses the investor’s profile to select the appropriate group of assets from the ranking.

Evaluation Layer: Tests the resulting portfolios using historical data..

Transition:

## Slide 16: Methodology

Now we are ready to go deeper into the technical details

## Slide 17: Chronological Split Design

I will first define how the data was divided. The split is strictly chronological.

The training period is where the model learns. The inner-validation period is used to select the strongest checkpoint from a training run. The main validation period is then used to compare framework choices, features, bucket mappings, and hyperparameters. Finally, the test period is reserved for final reporting.

I will now explain how se data were transformed

## Slide 18: Raw Data Engineering

I collected the raw financial input for each asset individually including date, price, OHLC fields, and volume.

An important detail is that treasury bill and bonds are quoted as yields. So before calculating returns, those yields are converted into price proxies.

I also include macroeconomic context through USD/EGP conversion rate and Consumer Price Index, or CPI, because market conditions influence how risky the active universe is in each month.

Transition: From those inputs, I build a monthly panel for the model.

## Slide 19: Point-In-Time Monthly Panel

Script

One row in the panel means one active asset in a specific month, so the model only sees active assets for a specific month.

Features for a specific row only use information available up to that point in time, and assets are never backfilled before they truly existed.

The panel keeps asset identity as metadata which is hidden from the model’s input. That helps the policy learn behavior patterns across the universe instead of memorizing specific asset behavior.

Transition:

Once the panel exists, the next question is what information each row actually contains.

## Slide 20: Feature Families

Script

Rather than presenting the model inputs as one long list, I group them by the type of behavior they describe.

Risk behavior captures recent instability and the severity of harmful losses. Liquidity describes how actively the asset trades. Technical state summarizes recent price behavior, including range, momentum, and position relative to previous highs. Market sensitivity describes how strongly the asset is correlated with the broader equity market. Finally, macro context captures shared currency and inflation conditions affecting every active asset.

Transition: The next step is defining the realized risk used in the ordering that the model should learn.

## Slide 21: Realized Risk Target

The realized-risk target combines realized volatility, downside deviation, and maximum drawdown. Each component is rank-normalized within the same month. This means an asset is compared only with the other assets that were active at that time, rather than being judged using an absolute scale.

The three ranks are averaged equally to form the ordering the model predicts. I also tested alternative formulas, but they produced weak sensitivity to the weights. Therefore Equal weights was promoted as the most transparent and balanced definition.

Transition: Before explaining why I used reinforcement learning, I will quickly explain it.

## Slide 22: What Is Reinforcement Learning

Reinforcement learning is a learning setup where a model improves through interaction and feedback. The model observes a state, takes an action, receives a reward, and then updates its policy.

The policy is basically the model's decision rule. The reward function tells the model what behavior should improve. If an action leads to a better reward, the model adjusts its internal policy so similar actions become more likely in the future.

Transition: With that idea clear, I can explain why this problem fits reinforcement learning.

## Slide 23: Why Reinforcement Learning

Script

Reinforcement learning fits this problem for three main reasons. First, the available assets change from month to month. Second, the model scores the full monthly set together rather than treating each asset as an isolated prediction. Third, the reward is calculated only after the complete universe has been ranked.

The figure shows how these ideas form one monthly decision environment. The state is the active asset universe and its features. The action is assigning one risk score to every active asset.

The predicted ranking is then compared with the realized-risk ranking to calculate the reward. That feedback is used to update the scoring policy, so it can produce better rankings in future decision months.

Transition: Among reinforcement learning methods, I used PPO because it gives a more controlled training update.

## Slide 24: Why PPO

Financial months can differ significantly, and an unusually difficult month could cause the model to change its behavior too aggressively. PPO reduces this risk through clipping, which limits how far the updated policy can move from the previous policy during one training update.

PPO also uses an actor-critic architecture. The actor makes decisions, while the critic evaluates them and provides a learning signal that helps train the model more reliably.

Transition: Before explaining the actor-critic architecture in more details, I first need to define what one PPO decision looks like.

## Slide 25: PPO Episode Format

Script

One PPO episode equals one monthly decision. The observation is a tensor of all asset features, together with a mask that marks which rows are real assets. This setup supports a different number of available assets depending on the decision month.

The action is one continuous risk score for each real asset row, between zero and one. After the model scores the month, the assets are sorted and compared with the realized-risk ordering for that same month.

So the reward is based on how well the full monthly ranking matches reality.

## Slide 26: Variable Universe & Masking

Script

The practical challenge is that every month has a different number of active assets. A neural network still needs a consistent tensor shape, so the input is padded to a fixed size.

The mask tells the model which rows are real and which rows are just padding. That way, padded rows do not pollute learning, or reward calculations.

Transition: Now I will explain the actor-critic architecture.

## Slide 27: Actor-Critic Architecture

This architecture contains three MLP neural networks.

First, the shared row encoder MLP reads every asset’s feature row and converts it into a learned representation. These representations are also pooled to summarize the active universe for that month.

Internally inside the PPO, the actor is the second neural network. It receives each asset’s representation together with the pooled monthly context and outputs one risk score per asset.

The critic is the third neural network. It receives the pooled context and estimates the reward expected for that monthly decision.

After the complete ranking is evaluated, PPO receives the observed monthly reward. The advantage is the observed reward minus the critic’s estimate. A positive advantage means the outcome was better than expected, while a negative advantage means it was worse. PPO uses this signal to update its policy.

TRANSITION: Now we can observe how monthly reward is calculated.

## Slide 28: Reward Definition

Script

The reward is computed after the entire monthly universe is scored. Seventy percent of it measures how close the predicted ranking was to the realized-risk ranking, and thirty percent measures how close the predicted score values were to the target values to discourage the model from placing all assets too close together.

The first part uses Spearman rank correlation. The second part uses MSE.

Transition: Once the model produces a ranked list, I can map that list into profile-specific asset universes.

## Slide 29: Profile-Specific Asset Universes

After ranking, the predicted positions are converted into rank percentiles. These percentiles are then used to form three profile-specific asset universes.

The conservative asset universe uses the lowest 30 percent of predicted-risk assets. The balanced asset universe uses the middle 20 to 80 percent band. The aggressive asset universe uses the highest 30 percent of predicted-risk assets.

The overlap is intentional because some assets can reasonably fit two neighboring investor profiles.

## Slide 30: Experiments

With the full method defined, the next step is to show the experiments.

## Slide 31: Framework Selection

Several formulations were compared to understand which input structure fits the problem, while keeping the base feature set fixed.

I tested whether the model should look at only the most recent month or a three-month feature window. I also tested whether adding context from the whole active universe improved the model's performance.

I also explored variants that included daily price information more directly, but that appeared to add noise and did not improve the model’s performance.

The three-month view with active-universe context had the best performance, so it was promoted as the final framework for the next stage

## Slide 32: Features and Reward Function

Script

Feature selection followed a sequential process. I first used drop-one-feature ablations on the fixed feature set, then confirmed promising changes with three-seed runs. After that, I tested redesigned feature-family alternatives and new feature additions.

Reward formula experiments came afterwards where I compared different balances between ranking quality, score accuracy. I also tested the addition of tail-risk emphasis to focus on getting the riskiest assets first.

Transition: I then tuned the PPO configuration.

## Slide 33: Hyper-parameters and Selection

Hyperparameter tuning came afterwards where I used Optuna which is a hyperparameter tuning tool. I then confirmed the selected configuration across three random seeds before locking the PPO model.

After the model was finalized, I compared different ways of mapping the predicted ranking to investor profiles. These included several mapping structures with different levels of overlap and selectivity across the three investor profiles. Selection criteria was producing the clearest separation between conservative and aggressive while maintaining the expected monotonic ordering.

Transition: Once the model was locked, I evaluated it in two connected stages.

## Slide 34: Evaluation Logic

Script

The first stage evaluates ranking quality directly by comparing predicted risk ranks with realized-risk ranks.

The second stage evaluates what those rankings mean for investor groups by forming conservative, balanced, and aggressive universes and comparing them with the full active universe under the same equal-weight rule.

Equal weights rule keeps the focus on universe selection.

Transition: Now I can show the core results.

## Slide 35: Results

_No speaker notes in the PowerPoint deck._

## Slide 36: Ranking Quality

The model achieved a mean reward of 0.75. Its Spearman correlation of approximately 0.67 also shows high agreement between the predicted and realized-risk rankings.

Looking at the graph, the horizontal axis shows each asset’s realized-risk rank, while the vertical axis shows the rank predicted by the model. Points closer to the orange diagonal represent stronger agreement between the two rankings. Although the predictions are not perfect, the overall upward pattern reflects the positive Spearman correlation.

The next slide examines whether the predicted ranks separate assets into clearly different realized-risk buckets.

## Slide 37: Risk Separation

The asset universes realized risk is in the expected order. The full universe mean realized risk was 50% because the risk was normalized. The monotonic ordering held in all test months. That is the cleanest evidence that the model can produce distinct risk-oriented universes.

From a financial point of view, the main message is that the conservative asset universe behaved materially safer, while the aggressive asset universe carried clearly higher risk.

Transition: After risk separation, we can look carefully at the returns

## Slide 38: Return Separation

Using the same equal-weight allocation rule, cumulative return in the test window showed monotonic ordering.

The aggressive universe also carried higher volatility, so, the higher return came with visibly higher risk exposure.

Transition: That brings us to the baseline comparison.

## Slide 39: Baseline Comparison

Script

The baseline here is the full active universe under the same equal-weight rule. Under that comparison, conservative-universe filtering materially reduced realized risk versus the full universe, while aggressive-universe filtering produced higher realized risk and stronger return participation.

The risk based filtering stage by itself already changes the opportunity set in a meaningful way.

## Slide 40: Limitations & Conclusion

_No speaker notes in the PowerPoint deck._

## Slide 41: Key Limitations

Among the limitations, an important extension is to connect the asset-level risk to portfolio-level risk. This thesis evaluates whether the model can identify assets appropriate for different risk profiles. In practice, these predictions would be combined with asset correlations to assess how including each asset changes the risk of the complete portfolio.

Second, PPO can produce different learned policies across training runs. We therefore confirmed the configuration across three seeds and reported the promoted checkpoint.

Third, the model uses official USD-to-EGP exchange rates. These rates may not fully represent parallel-market or actual transaction prices during periods of currency pressure.

Transition: With these limitations stated clearly, I can now answer the research questions directly.

## Slide 42: Research Question Answers

RQ1 asks whether Reinforcement learning can support dynamic asset-universe selection using asset’s predicted risk. The answer is yes: the PPO model produced meaningful profile asset universes across the changing active universe.

RQ2 asks whether the selected universes align with conservative, balanced, and aggressive investor profiles. For this question, also yes: the predicted-rank universes produced distinct realized-risk groups in the expected order.

RQ3 asks how the proposed risk-tolerance-based universes compare with the full active universe under the same equal-weight historical simulation rule. The answer is that the filtered universes behaved differently from the full active universe in realized risk and returns.

Transition The last content section is future work.

## Slide 43: Future Work

_No speaker notes in the PowerPoint deck._

## Slide 44: Live Data and Forward Testing

These are possible next steps beyond the thesis scope. One future direction is connecting the pipeline to live market-data APIs, rebuilding the monthly features over time, and monitoring how the selected asset universes behave in real conditions.

Transition: There is also a natural extension on the objective side.

## Slide 45: Return-Aware Suitability

Another possible extension is return-aware suitability where a future version may add return-aware utility logic after the risk-ranked universes are formed.

That would let the system stay investor-aware while exploring richer tradeoffs inside each selected universe.

Transition: I'll conclude with the key references behind the ideas we've discussed.

## Slide 46: Key References

These are the five core references directly supporting the problem framing and the preselection literature for this thesis.

## Slide 47: Q&A

_No speaker notes in the PowerPoint deck._

## Slide 48: Thank You

_No speaker notes in the PowerPoint deck._

## Slide 49: Asset Universe Selection Formulas

_No speaker notes in the PowerPoint deck._
