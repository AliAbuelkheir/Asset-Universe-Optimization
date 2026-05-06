# Papers

Last updated: 2026-05-06

This file is the active local paper tracker for the thesis. The thesis is now
framed as AI/ML-supported investor-suitable asset-universe selection before
allocation. PPO ranking and Egyptian market data are implementation choices
used to study that problem.

## Literature Streams

| Literature stream | What it proves | What it misses | How this thesis responds |
| --- | --- | --- | --- |
| AI/ML preselection before optimization | Asset selection before weight allocation is a valid and measurable portfolio-construction stage. | Selection is usually driven by return prediction, profitability, Sharpe, efficiency, robustness, or optimizer performance. | Reframes preselection as investor-suitability by risk tolerance before allocation. |
| Investor-profile and risk-tolerance recommendation | Investor profile and risk tolerance should change financial recommendations. | Outputs are often advice, funds, product types, or final portfolios rather than an explicit pre-allocation asset universe. | Connects investor-risk suitability to the asset-universe construction stage. |
| Classical and risk-based allocation | Portfolio optimization and risk objectives are established baselines. | The investable universe is usually assumed to be fixed. | Places the proposed method before these optimizers as a universe-selection stage. |
| RL/DRL portfolio management | Adaptive AI can learn from financial market states and changing regimes. | Most methods learn allocation or trading actions directly. | Uses RL as an implementation path for dynamic risk-suitability scoring before allocation. |
| Closest investor-specific DRL work | Investor-specific asset grouping plus DRL exists. | Closest work is stock-only and allocation-centered. | Evaluates a mixed-asset, variable-universe, risk-tolerance bucket stage before allocation. |

## Paper-by-Paper Comparison

Legend: Y = yes, P = partial, N = no.

| Paper | AI/ML used | Selects assets before allocation | Investor risk tolerance | Selection criterion | Evaluation target | Similarity to thesis | Gap fulfilled | Use in thesis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `markowitz1952` | N | N | N | Fixed universe, mean-variance weights | Efficient frontier | Low | Does not decide which assets are suitable before weights. | Classical background; shows fixed-universe assumption. |
| `blacklitterman1992` | N | N | P | Investor views affect expected returns/allocation | Global allocation | Low | Investor views enter allocation, not universe selection. | Background for investor-conditioned allocation. |
| `rockafellar2000optimization` | N | N | P | CVaR/downside risk objective | Tail-risk optimization | Low | Optimizes weights after universe is given. | Risk objective support. |
| `demiguel2009optimal` | N | N | N | 1/N naive diversification | Out-of-sample portfolio benchmark | Low | No suitability filtering. | Full-universe equal-weight benchmark. |
| `lopezdeprado2016building` | N | N | N | Hierarchical risk allocation | Diversification and risk allocation | Low | Allocates within a fixed universe. | Risk-based allocation baseline. |
| `bodnar2021quantile` | N | N | P | Quantile-based risk objective | Risk-oriented allocation | Low | Risk-aware optimization, not preselection. | Tail-risk literature support. |
| `wang2020portfolioformation` | Y | Y | N | Deep learning preselection from long-term financial data | Downstream portfolio formation | High | Adds investor-risk-tolerance suitability to preselection. | Main baseline family. |
| `ma2021returnprediction` | Y | Y | N | ML/DL return prediction | Portfolio optimization performance | High | Selection is return-driven rather than investor-risk-suitability-driven. | Main baseline family. |
| `kaczmarek2022building` | Y | Y | N | Machine-learning return predictions | MVO, HRP, and 1/N portfolio results | High | No explicit investor risk-tolerance universe. | Main baseline family. |
| `chaweewanchon2022` | Y | Y | N | Predictive stock selection with ML | Markowitz optimization | High | Stock prediction before weights, not risk-tolerance suitability. | Main baseline family. |
| `mills2022twostage` | P | Y | N | Robust two-stage asset qualification under uncertainty | Portfolio robustness | Medium-high | Qualification is not investor-risk-group-specific. | Staged-selection support. |
| `hosseinzadeh2023dea` | N/P | Y | N | DEA efficient-asset preselection | Portfolio strategy performance | Medium | Efficiency screening, not investor suitability. | Preselection baseline, non-ML/operations-research angle. |
| `abdi2024prospective` | Y | Y | N | LSTM and Sharpe-ratio maximization | Optimized portfolio performance | High | Sharpe-focused selection, not investor-risk-tolerance buckets. | Main baseline family. |
| `chou2025ensemble` | Y | Y | P | Ensemble stock preselection and multiobjective optimization | Stepwise decision-supported portfolio management | Very high | Investor preferences appear, but selection is still stock and optimizer-centered. | Strong baseline family; likely key comparison. |
| `musto2015personalized` | Y/P | P | Y | Case-based personalized financial advice | Advisory/recommender quality | Medium | Personalized advice, not explicit pre-allocation universe construction. | Investor-profile support. |
| `alsabah2021roboadvising` | Y/P | N | Y | Learned investor risk preferences from choices | Personalized robo-advising | Medium | Models risk preference but does not select an asset universe first. | Risk-preference modeling support. |
| `yu2021personalized` | N/P | N | Y | Personalized mean-CVaR optimization | Individual portfolio allocation | Medium | Risk tolerance affects weights, not preselection. | Investor-risk-aware optimization support. |
| `asemi2023demographics` | Y | P | Y | ANFIS maps demographics/feedback to investment type | Investment-type recommendation | Medium | Recommends type/category, not asset-level universe before weights. | Profile-to-suitability support. |
| `asemi2024investmenttype` | Y | P | Y | ANFIS/MNN with investor and expert feedback | Investment-type recommendation | Medium | Investment-type recommendation, not asset-level selection. | Investor-input recommendation support. |
| `wei2025fundrecommendation` | Y | P | Y | Dynamic utility learning | Fund recommendation | Medium | Recommends funds, not a separate allocation-ready asset universe. | Dynamic personalization support. |
| `schneider2025riskappetite` | Y | P | Y | Risk-appetite-conditioned LLM portfolio/stock selection | Stock recommendations by risk appetite | High | Closely supports risk appetite, but not implemented as a tested pre-allocation ML pipeline. | Risk-appetite evidence and thesis motivation. |
| `capponi2022personalizedrobo` | Y/P | N | Y | Client interaction and personalized optimization | Robo-advised allocation | Medium | Personalizes allocation, not universe selection. | Dynamic investor-profile support. |
| `deng2017deepdirect` | Y | N | N | DRL signal representation and trading | Trading performance | Low-medium | RL finance method, not investor-suitable universe selection. | RL implementation background. |
| `jiang2017portfolioframework` | Y | N | N | DRL portfolio weights | Portfolio management performance | Medium | Learns allocation directly rather than preselection. | DRL portfolio-management baseline. |
| `liu2020finrl` | Y | N | N | DRL environments and agents | Trading/backtesting framework | Medium | Framework support, not thesis problem. | Implementation reference for financial RL. |
| `lucarelli2020deepq` | Y | N | N | Deep Q-learning portfolio decisions | Crypto portfolio results | Low-medium | Allocation/trading, not investor-risk universe selection. | DRL method support. |
| `soleymani2020deepbreath` | Y | N | N | Online DRL with autoencoder representation | Portfolio optimization | Medium | Optimizes portfolio weights directly. | DRL implementation support. |
| `pinelis2022machineallocation` | Y | N | P | ML reward-risk timing for allocation | Portfolio allocation | Medium | Risk-return allocation, not pre-allocation selection. | ML allocation reference. |
| `choudhary2025riskadjusted` | Y | N | P | PPO agents with risk-adjusted rewards | Portfolio optimization metrics | Medium-high | Risk-aware PPO, but action is allocation/portfolio optimization. | Risk-aware PPO support. |
| `rezaei2025taxonomy` | Y | N | N | DRL portfolio-management taxonomy | Survey and experimental taxonomy | Medium | Survey of allocation/trading methods, not selection stage. | Literature framing for DRL choices. |
| `orra2025deep` | Y | Y | Y | Volatility-guided grouping by investor risk category plus DRL allocation | MVO, DJI, equal-weight comparison | Very high | Closest paper; thesis extends framing to mixed Egyptian variable universe and pre-allocation suitability evaluation. | Closest single comparison paper. |

## Reclassified Defended Set

### Main Baseline Family: AI/ML Preselection Before Optimization

- `wang2020portfolioformation`
- `ma2021returnprediction`
- `kaczmarek2022building`
- `chaweewanchon2022`
- `mills2022twostage`
- `hosseinzadeh2023dea`
- `abdi2024prospective`
- `chou2025ensemble`

### Closest Comparison: Investor-Specific / Risk-Aware Preselection

- `orra2025deep`
- `chou2025ensemble`
- `schneider2025riskappetite`

### Investor-Profile Support

- `musto2015personalized`
- `alsabah2021roboadvising`
- `yu2021personalized`
- `asemi2023demographics`
- `asemi2024investmenttype`
- `wei2025fundrecommendation`
- `capponi2022personalizedrobo`

### RL/DRL Implementation Support

- `deng2017deepdirect`
- `jiang2017portfolioframework`
- `liu2020finrl`
- `lucarelli2020deepq`
- `soleymani2020deepbreath`
- `pinelis2022machineallocation`
- `choudhary2025riskadjusted`
- `rezaei2025taxonomy`

### Classical Allocation Background

- `markowitz1952`
- `blacklitterman1992`
- `rockafellar2000optimization`
- `demiguel2009optimal`
- `lopezdeprado2016building`
- `bodnar2021quantile`

## Thesis Gap Wording

Existing AI/ML preselection papers validate asset selection before allocation,
but usually select assets for expected return, profitability, efficiency,
Sharpe-like performance, or final optimizer quality. Personalized finance
papers validate investor-risk conditioning, but usually do not build an
explicit pre-allocation asset universe. This thesis connects these two streams
by selecting an investor-suitable asset universe using risk-tolerance-oriented
bucket construction before allocation.

## Experimental Baseline Decision

Use the AI/ML preselection literature as the main baseline family and evaluate
the implementation against:

- full active universe equal weight
- repeated random selection/rank assignments
- realized-risk oracle buckets as a non-investable diagnostic upper bound
- bucket-method ablations over predicted risk percentiles

The result should be described as risk-tolerance-oriented universe construction,
not final portfolio optimization.

## Near-Miss / Supporting Papers

- `qin2024followakoinvestor`
  FollowAKOInvestor: stock recommendation by aggregating investor sentiment
  with machine learning. Verified in Expert Systems with Applications, 2024,
  DOI `10.1016/j.eswa.2024.123522`. Useful as a ranking-based stock
  recommendation analogy, but weaker fit because it is sentiment-driven stock
  recommendation rather than risk-tolerant universe selection.
- `oehler2024chatgptrobo`
  Does ChatGPT provide better advice than robo-advisors? Verified in Finance
  Research Letters, 2024, DOI `10.1016/j.frl.2023.104898`. Supporting context
  for investor-profile-conditioned advisory comparisons.
- `lin2023mgma`
  An adaptive multiple-asset portfolio strategy with user-specified risk
  tolerance. Verified in Mathematics, 2023, DOI `10.3390/math11071637`.
  Investor risk tolerance is explicit, but the paper is allocation-focused.
- `bartram2021machine`
  Machine learning for active portfolio management. Verified in The Journal of
  Financial Data Science, 2021, DOI `10.3905/jfds.2021.1.071`. Broad ML
  portfolio-management coverage, not direct preselection support.

Removed during verification:

- `salah2025meta`
  Removed from the tracker because the verification pass did not find a
  reliable matching paper from publisher, DOI, arXiv, SSRN, or equivalent
  sources. Do not re-add it unless a real source is identified.
