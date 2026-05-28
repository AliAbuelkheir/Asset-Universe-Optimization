# Baseline Comparison Memo

Last updated: 2026-05-06

## Position

The thesis baseline should be framed around the closest real literature family:
AI/ML-based asset preselection before portfolio optimization. These papers are
not merely adjacent; they validate the central thesis idea that asset-universe
construction can be a separate decision stage before final weight allocation.

The narrower gap is that most preselection papers choose assets for expected
return, profitability, efficiency, Sharpe-like performance, or downstream
optimizer quality. This thesis instead frames preselection as an
investor-suitability problem:

- conservative investors prioritize realized-risk control
- balanced investors need a risk-return tradeoff
- aggressive investors tolerate higher risk to access higher return opportunity

The current implementation supports this as an evaluation framing. The PPO
model is trained to score realized-risk behavior, then the selected universe is
formed through risk-tolerance buckets. Return, Sharpe, Sortino, and drawdown are
reported as economic diagnostics; they should not be described as optimized
targets unless a future return-aware objective is implemented and rerun.

## Main Baseline Family

| Baseline family | Representative papers | Why it matters | Thesis gap relative to this family |
| --- | --- | --- | --- |
| AI/ML preselection before optimization | Wang et al. 2020; Ma et al. 2021; Kaczmarek and Perez 2022; Chaweewanchon and Chaysiri 2022; Mills and Anyomi 2022; Abdi et al. 2024; Chou and Pham 2025 | Establishes that selecting assets before weight allocation is a valid portfolio-construction stage. | Selection is usually driven by return prediction, Sharpe, efficiency, robustness, or final optimizer performance rather than investor-risk-tolerance suitability. |
| Closest investor-specific preselection + DRL | Orra et al. 2025 | Combines investor-specific risk categories, volatility-guided asset grouping, and DRL allocation. | Closest single paper, but it remains stock-only and allocation-centered; this thesis evaluates investor-suitable universe construction over a mixed Egyptian universe before allocation. |
| Personalized/risk-tolerance finance | Musto et al. 2015; Alsabah et al. 2021; Yu and Liu 2021; Asemi et al. 2023; Asemi et al. 2024; Wei and Liu 2025; Schneider and Yilmaz 2025; Capponi et al. 2022 | Shows that investor profile and risk tolerance should change financial recommendations. | These papers usually output advice, funds, product types, or allocation decisions rather than a distinct pre-allocation universe filter. |
| Classical and risk-based allocation | Markowitz 1952; Black and Litterman 1992; Rockafellar and Uryasev 2000; DeMiguel et al. 2009; Lopez de Prado 2016; Bodnar et al. 2021 | Establishes optimization and risk-evaluation baselines. | These methods usually assume the investable universe is already fixed. |
| RL/DRL portfolio management | Deng et al. 2017; Jiang et al. 2017; Liu et al. 2020; Lucarelli and Borrotti 2020; Soleymani and Paquet 2020; Pinelis and Ruppert 2022; Choudhary et al. 2025; Rezaei and Nezamabadi-Pour 2025 | Justifies adaptive AI/RL methods for financial decision-making. | Most learn trading or allocation actions directly rather than a risk-tolerance-oriented asset-universe selection stage. |

## Experimental Baseline Plan

The thesis evaluation should compare the promoted risk-tolerance selection step
against:

- full active universe equal weight as the neutral investable benchmark
- repeated random rank assignments as a no-skill bucket baseline
- realized-risk oracle buckets as a non-investable diagnostic upper bound
- bucket-method ablations such as `tail_30_overlap`, `tercile_no_overlap`,
  `overlap_40_50`, and `wide_overlap_50_60`

This matches the current repository state because the active model outputs
asset risk scores and risk-tolerance buckets, not final allocation weights.

## Thesis-Safe Claim

Safe:

- The method constructs investor-risk-tolerance-oriented asset universes before
  allocation.
- The low-risk universe has materially lower realized risk than the full active
  universe in the current evaluation.
- The high-risk universe has higher realized risk and, in the current short
  test window, higher cumulative return; this is consistent with a risk-return
  gradient.

Unsafe:

- The PPO model optimizes expected return.
- The method proves improved final portfolio optimization returns.
- The current model directly solves investor-tier allocation weights.

## Meeting Question

Ask the doctor whether it is acceptable to use AI/ML asset preselection before
optimization as the main baseline family, with Orra et al. 2025 as the closest
single comparison paper, while positioning this thesis as the risk-tolerance
extension of that family.
