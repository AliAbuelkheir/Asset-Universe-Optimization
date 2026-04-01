# Papers

Last updated: 2026-03-31

This file is the active local paper tracker for the project.

## Active Defended Set

### Core

- `orra2025deep`
  Deep Reinforcement Learning for Investor-Specific Portfolio Optimization: A
  Volatility-Guided Asset Selection Approach.
  Closest current paper because it combines investor risk categories, AI, and
  explicit asset selection before downstream portfolio construction.

### Preselection / Ranking Support

- `wang2020portfolioformation`
  Deep-learning stock preselection before downstream optimization.
- `kaczmarek2022building`
  Machine-learning stock preselection before portfolio optimization.
- `ma2021returnprediction`
  ML return prediction feeding downstream portfolio formation.
- `mills2022twostage`
  Two-stage stock qualification before final allocation.
- `qin2024followakoinvestor`
  Ranking-based stock recommendation analogy, useful but weaker fit.

### Personalization Support

- `musto2015personalized`
  Personalized financial advice driven by investor information.
- `asemi2024investmenttype`
  AI-based investment-type recommendation using investor inputs.
- `wei2025fundrecommendation`
  Personalized fund recommendation with learned utility.
- `oehler2024chatgptrobo`
  Investor-profile-conditioned AI advisory comparison.
- `schneider2025riskappetite`
  Stock portfolio selection conditioned on investor risk appetite.

## Current Workbook Migration Status

Migrated from the previous workbook sheets:

- retained:
  `Paper 1`, `Paper 3`, `Paper 4`, `Paper 12`
- archived from the previous set:
  `Paper 2`, `Paper 5`, `Paper 6`, `Paper 7`, `Paper 8`, `Paper 9`,
  `Paper 10`, `Paper 11`, `Paper 13`, `Paper 14`

## Archived / Near-Miss Papers

- `lin2023mgma`
  investor risk tolerance is explicit, but the paper is allocation-focused
- `bartram2021machine`
  broad ML portfolio-management coverage, not direct preselection support
- `salah2025meta`
  survey-level context, not a defended method paper
- `capponi2022personalizedrobo`
  personalization is relevant, but no explicit preselection stage

## Main Gap The Literature Still Shows

Very few papers combine all of the following at once:

- investor-profile input
- AI or ML
- explicit preselection before final weights

That remains the main defendable thesis gap.

## Next Actions

- keep the defended set stable while the data-engineering phase finishes
- sync `references.bib` only after the defended set is final
- use this file as the local paper tracker going forward

