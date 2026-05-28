# V2 Review Analysis and V3 Revision Brief

Generated on: 2026-05-23

Workspace: `C:\Ali\CS\Bachelor thesis`

This file is the planning and traceability artifact for the V3 thesis revision.
It consolidates the general review comments, the individual thesis review, the
archived V2 thesis state, and the repository evidence that should constrain
the V3 edits. Status entries in the matrices describe the V2 baseline captured
before V3 source changes were applied.

File naming note: this artifact is named `v2_review_analysis.md` because the
doctor's review comments were applied to the V2 thesis state and used to plan
the V3 revision.

## V2 Baseline Thesis and Repository Status

| Area | Current status | V3 implication |
| --- | --- | --- |
| Versioning | V1 is already archived under `thesis/versions/v1_submitted_initial_feedback/`. The live thesis source has now been archived as V2 under `thesis/versions/v2_methodology_reviewed/`. | All subsequent thesis source edits are V3 edits. |
| Live thesis source | Active source is `thesis/Bachelor Thesis Template/`. | V3 edits should be applied in place to this directory. |
| Methodology | Chapter 3 is substantially revised and aligned with the PPO risk-ranking project, but several reviewer compliance items remain incomplete. | Preserve the core structure, then refine actor-critic detail, equations, algorithms, RQ mapping, citations, and hyperparameter placement. |
| Results | `results.tex` is placeholder text. | Chapter 4 must be fully written. This is the largest V3 work item. |
| Conclusion | `conclusion.tex` is placeholder text. | Chapter 5 must answer the research questions directly and avoid overclaiming. |
| Project source of truth | `ppo-risk-model/AGENTS.md` is the source of truth for data, training, evaluation, leakage, and thesis-safe PPO claims. | Claims in V3 must match the ranked-risk PPO system, not the separate web allocator. |
| Web simulator | `portfolio-simulator-web/` is a separate serving/simulation layer. | Do not mix its allocation or questionnaire logic into the thesis methodology unless explicitly scoped. |

Core thesis-safe framing:

- The thesis studies pre-allocation asset-universe selection, not final portfolio optimization.
- The active model is a month-level PPO risk-ranking policy over a variable Egyptian mixed-asset universe.
- Portfolio and return metrics are historical diagnostics, not proof of guaranteed outperformance.
- The optimizer remains separate from model inference and investor risk-tolerance selection.
- Questionnaire inference is not part of the active thesis method unless external model files and evaluation scope are explicitly added.

## Research Questions and Alignment

Current research questions from Chapter 1:

| RQ | Current question | V3 alignment action |
| --- | --- | --- |
| RQ1 | Can AI/ML support dynamic asset-universe selection before allocation using asset-level realized-risk prediction? | Define support through validation/test ranking metrics, high-risk overlap, and realized-risk bucket separation. |
| RQ2 | Do the selected universes align with conservative, balanced, and aggressive investor risk-tolerance profiles? | Evaluate predicted-rank buckets against the full active universe using realized-risk, return, volatility, and drawdown diagnostics. |
| RQ3 | How does direct asset-risk prediction differ from existing AI/ML preselection criteria such as return prediction, price movement, Sharpe-like performance, efficiency, or optimizer quality? | Treat this mainly as conceptual/literature positioning plus internal baseline context, not same-dataset replication of prior papers. |

Add a small Chapter 3 table mapping each RQ to:

- methodology component
- evaluation metric or diagnostic
- expected Chapter 4 evidence

## General Review Matrix

| # | Review point | Applicability | Current evidence | V3 remediation |
| ---: | --- | --- | --- | --- |
| 1 | Start methodology with motivation. | Applies | `methodology.tex` opens with scope and contribution, but the motivation is concise. | Add one explicit sentence linking the motivation to fixed-universe allocation assumptions and RQ1/RQ2. |
| 2 | Outline architecture/framework/pipeline before details. | Applies | Figure 3.1 and framework overview already precede details. | Keep the structure and add a short reader-map paragraph listing data, target, PPO scoring, bucketing, and evaluation. |
| 3 | Add evaluation design if user interaction is required. | Partially applies | The thesis discusses investor profiles, but no user study is active. Root rules say questionnaire inference is disabled. | State explicitly that V3 evaluates model/profile buckets historically, not user interaction or questionnaire usability. Do not add A/B testing unless the scope changes. |
| 4 | Make illustrations visible. | Applies | Chapter 3 has seven TikZ figures. | Render-check final PDF for figure readability and excessive shrinking. Keep figures vector/native, not screenshots. |
| 5 | Cite and discuss algorithms. | Partially applies | PPO is described, but method citations and algorithmic steps are incomplete. | Cite PPO, EGARCH, Optuna if used. Add algorithms for panel construction and monthly PPO scoring/bucketing. Discuss only key lines/steps. |
| 6 | No consecutive titles without text. | Partially applies | Methodology mostly complies, but Results and Conclusion are placeholders. | Replace all placeholder text and add transition paragraphs before subsections. |
| 7 | Capitalize title words except prepositions. | Partially applies | Most headings are Title Case. `Experiments Setup` should be `Experimental Setup`. | Standardize all chapter, section, and subsection titles. |
| 8 | Include prompt templates if prompting is central. | Not applicable | The active model is PPO, not prompt-based. | No prompt appendix is required. Add a clarification that there are no LLM prompts if reviewer confusion persists. |
| 9 | End chapters with natural summaries/bridges. | Partially applies | Methodology has a summary. Literature and Introduction can close more clearly; Results/Conclusion are placeholders. | Add short closing bridges to Chapters 1-3. End Chapter 3 with a bridge into Results. |
| 10 | Defer implementation details to implementation/results; black-box AI can be mentioned in methodology. | Partially applies | Methodology includes exact feature lists, thresholds, and hyperparameters. | Keep conceptual process in Chapter 3. Move final values, run IDs, and selected configs into Chapter 4 or appendix. |
| 11 | Hyperparameter/threshold values belong in Results; methodology states selection process. | Partially applies | Chapter 3 currently includes promoted PPO hyperparameters and bucket threshold table. | Retain the tuning and bucket-selection process in Chapter 3, but put final numeric values and evidence in Chapter 4. |
| 12 | Formulate processes as steps/algorithms. | Partially applies | Diagrams and tables exist, but no algorithm blocks are used. | Add concise algorithms for data construction and PPO scoring/bucketing/evaluation. |
| 13 | Number and cite mathematical formulas. | Partially applies | Reward equation is numbered automatically but unlabeled and not referenced. | Add labels and text references for reward, realized-risk score, and rank-percentile bucket mapping. |
| 14 | Align methodology with Chapter 1 research questions. | Applies | The methodology aligns broadly with RQ1-RQ3. | Make alignment explicit with an RQ-to-method/evidence table. |
| 15 | Tone down AI writing and personalize. | Partially applies | Writing is thesis-specific but sometimes generic. | Add concrete decisions, constraints, Egyptian-market data details, and run outcomes. Reduce generic "this chapter" phrasing where possible. |
| 16 | Declaration: original work and help acknowledged. | Partially applies | Declaration exists but has typo `acknowlegement`; no AI-assistance acknowledgement is present. | Fix typo. Add a transparent AI-assistance acknowledgement if applicable, without weakening original-work declaration. |
| 17 | Reduce large white spaces. | Partially applies | Placeholder Abstract, Results, and Conclusion create sparse pages. | Fill placeholder chapters and render-check float placement, blank pages, and list pages. |
| 18 | Fix submission date. | Applies | `bachelor.tex` still uses `Day`, `Month`, `Year`. | Replace with final intended submission date. If unknown, use the current known submission target only after user confirmation. |
| 19 | Figures/tables must be numbered, captioned, cited; no screenshots of tables. | Partially applies | Chapter 3 captions/labels exist, but many are not cited in text. | Cite every figure and table by number in the surrounding text. Keep tables as LaTeX. |
| 20 | Figure captions below, table captions above. | Applies | Current Chapter 3 follows this convention. | Preserve convention. |
| 21 | Expand abbreviations at first use and add abbreviation list. | Partially applies | Appendix acronym list is dummy content. | Populate list for AI, ML, RL, PPO, EGX, CPI, USD, REIT, EGARCH, MSE, CNN, ATR, RSI, SMA, GAE, MVO, CVaR, and DRL. Expand first uses. |
| 22 | Use numeric square-bracket citations. | Applies | `ieeetr` is used. | Keep IEEE numeric citations and avoid using citations as sentence subjects or objects. |
| 23 | Say "in this thesis"; use correct tense. | Partially applies | Text mixes "this work", "the thesis", and completed-experiment phrasing. | Standardize own contribution wording. Present tense for methodology structure, past tense for completed experiments/results. |
| 24 | Results chapter should not use IDE/CLI screenshots. | Applies | Current Results has no screenshots. | Use LaTeX tables and exported/native plots only. |
| 25 | Chapter 4 starts with environment, data, parameters, results, statistics, discussion. | Applies | Chapter 4 is currently placeholder. | Rewrite Chapter 4 with experimental setup, data/splits, selected configs, ranking results, bucket diagnostics, baselines, discussion, and limitations. |
| 26 | Results discussion should show understanding. | Applies | Discussion section is placeholder. | Interpret what metrics mean, why bucket separation matters, where the model fails, and what the results do not prove. |

## Individual Review Matrix

Reviewer comment:

> You need to provide more details/elaboration on the actor-critic architecture
> (what models, different or same, prompts used, agents or simply LLMs, etc.).
> What is the criteria of the risk target promotion? What is your baseline?
> Will it be in the results chapter?

| Sub-issue | Applicability | Current evidence | V3 remediation |
| --- | --- | --- | --- |
| Actor-critic architecture needs more detail. | Applies | Chapter 3 has a short actor-critic paragraph and Figure 3.4. Source code shows a custom Stable-Baselines3 `MaskedActorCriticPolicy`. | Expand the section with a component table and precise wording: one PPO RL policy, shared row encoder, pooled context, actor head, critic head, masked distribution. |
| Clarify model type: LLMs, prompts, agents? | Applies | No prompts or LLMs are used in the active modeling pipeline. The word "agent" can be misread. | State that "agent" means PPO reinforcement-learning policy interacting with a Gym environment. There are no LLM prompts or multi-agent LLM components in training or inference. |
| Same or different actor/critic models? | Applies | Actor and critic are implemented in one policy class. They share row encoding, then use separate heads. | Add: shared row encoder, actor uses row embeddings plus pooled context to score assets, critic uses pooled universe summary to estimate month value. |
| Risk target promotion criteria. | Applies | Current target is `risk_v1_equal_333`. Alternatives are listed as audited profiles, but full empirical promotion evidence is not documented. | Describe `risk_v1_equal_333` as a methodological balanced target: equal ranked volatility, downside deviation, and drawdown. Treat alternatives as sensitivity definitions unless full results are added. |
| Current-best model promotion criteria. | Applies | Project guide states current best selected by three-seed validation high-risk top-25 overlap improvement with reward and Spearman guardrails; test metrics only reporting. | Add a promotion-gates table: framework, feature/tail candidate, PPO tuning, current-best artifact, bucket method. |
| Baseline definition. | Applies | Literature review names AI/ML preselection family. Project docs define full-universe equal weight, random rank buckets, realized-risk oracle, and bucket ablations. | Chapter 4 should include both literature baseline positioning and empirical baselines: full active universe equal weight, random no-skill buckets, oracle upper bound, bucket-method ablations. |
| Will baseline/results be in Chapter 4? | Applies | `results.tex` is placeholder. | Yes. Chapter 4 should hold final numeric evidence, model-selection results, ranking metrics, bucket diagnostics, baselines, ablations, and limitations. |

## Actor-Critic Details to Add

Use this technical description in V3, adapted into thesis prose:

- The implemented system is a single Proximal Policy Optimization (PPO) reinforcement-learning policy, not a large language model (LLM), not a prompt-based agent, and not a multi-agent LLM workflow.
- All model inputs are numeric market, technical, and macroeconomic features.
- One episode corresponds to one decision month.
- The observation contains a padded asset feature tensor and an active-asset mask.
- The active framework is `pit_3m_flat_context`: three prior monthly states are concatenated per asset and combined with pooled active-universe context.
- The current-best input contains 12 features per monthly state, so three months produce 36 numeric input values per asset row.
- The actor and critic are contained in one `MaskedActorCriticPolicy`.
- The row encoder is shared and applied identically to every active asset row.
- The pooled context uses mask-aware mean pooling, max pooling, and normalized active-asset count.
- The actor concatenates asset embeddings with pooled context and outputs one bounded risk-score distribution per active asset.
- The action distribution is a masked sigmoid-squashed Gaussian, producing scores in `[0, 1]`.
- The critic uses the pooled universe summary to output one scalar value estimate for the decision month.
- Padded rows are excluded from action sampling, log probability, entropy/loss contribution, reward, and evaluation.

Suggested component table:

| Component | V3 description |
| --- | --- |
| Input | Padded active-universe tensor plus active mask. |
| Row encoder | Shared multilayer perceptron applied to each asset row. |
| Context | Mask-aware pooled active-universe summary using mean, max, and active-count information. |
| Actor head | Asset-level head that outputs one bounded predicted-risk score distribution per active asset. |
| Critic head | Month-level value head that estimates the value of the full monthly ranking decision. |
| Distribution | Masked sigmoid Gaussian over asset scores. |
| Masking | Padded rows do not affect sampling, log-probability, losses, reward, or metrics. |

## Promotion Criteria to State

| Decision | Criteria | Test use |
| --- | --- | --- |
| Framework | Compare candidate monthly/daily frameworks on validation reward and Spearman under the same decision months and no leakage. | Reporting only. |
| Feature profile | Keep fixed framework, screen features by validation reward with Spearman guardrail. | Reporting only. |
| PPO tuning | Optimize validation reward with validation Spearman as a guardrail. | Reporting only. |
| Current-best model | Three-seed validation high-risk top-25% overlap improvement with validation reward and Spearman guardrails. | Reporting only. |
| Risk target | Use equal ranked volatility, downside deviation, and drawdown as a balanced methodological target. | Not a test-selected target unless full target-profile evidence is reported. |
| Bucket method | Prefer selective tails and validation robustness; report test bucket-method comparison as final evidence. | Reporting/evidence, not selection if selected earlier. |

## Baseline Plan

Use two baseline layers:

1. Literature baseline family:
   - AI/ML asset preselection before optimization.
   - Closest single-paper comparison: Orra et al. 2025, because it links risk profiles, grouping, and DRL allocation.
   - Do not claim same-dataset numeric superiority over prior papers.

2. Empirical baseline diagnostics:
   - Full active universe equal weight: main investable neutral benchmark.
   - Random rank buckets: no-skill bucket baseline.
   - Realized-risk oracle buckets: non-investable upper diagnostic bound.
   - Bucket-method ablations: `tail_30_overlap`, `tercile_no_overlap`, `overlap_40_50`, `wide_overlap_50_60`.

## Chapter 4 Results Content

Replace Chapter 4 with these sections:

1. `Experimental Environment`
   - Python version, major libraries, operating environment, training/evaluation scripts.
   - Include package versions if verified locally.

2. `Data Coverage and Splits`
   - Panel range: October 2010 to January 2026.
   - Training: January 2011 to December 2022.
   - Validation: January 2023 to February 2025.
   - Test: March 2025 to January 2026.
   - State clearly that test is used only for final reporting.

3. `Model and Parameter Selection`
   - Framework winner: `pit_3m_flat_context`.
   - Current-best model: `downside_tail_ratio_3m_refined50`.
   - Feature set: `full_current_v1` plus `downside_tail_ratio_3m`.
   - PPO tuned candidate: `refined50`.
   - Report final hyperparameters here, not primarily in methodology.

4. `Ranking Results`
   - Validation reward and Spearman.
   - Test reward and Spearman.
   - High-risk and low-risk top-25% overlap.
   - Monthly robustness table for test months.

5. `Risk-Bucket Diagnostics`
   - `tail_30_overlap` bucket results.
   - Full vs low vs medium vs high realized-risk table.
   - Return, volatility, Sharpe/Sortino if available, and drawdown as secondary diagnostics.

6. `Baseline and Ablation Comparison`
   - Full-universe equal weight.
   - Random rank buckets.
   - Oracle buckets.
   - Bucket-method ablations.
   - Literature baseline positioning.

7. `Discussion and Limitations`
   - Interpret metric meaning.
   - Explain why low/high risk separation supports RQ2.
   - Discuss short test window and validation exceptions.
   - State that high return in high-risk bucket is consistent with a risk-return gradient, not return prediction.

Key result values currently supported by project docs/artifacts:

| Result | Value |
| --- | ---: |
| Validation reward, current best | 0.7081 |
| Validation Spearman, current best | 0.6047 |
| Validation high-risk top-25 overlap | 0.4772 |
| Test reward, current best | 0.7515 |
| Test Spearman, current best | 0.6652 |
| Test high-risk top-25 overlap | 0.4949 |
| Test full-universe realized risk, `tail_30_overlap` comparison | 0.500 |
| Test low-risk bucket realized risk | 0.239 |
| Test medium-risk bucket realized risk | 0.536 |
| Test high-risk bucket realized risk | 0.688 |
| Test full-universe cumulative return | 49.59% |
| Test low-risk cumulative return | 29.91% |
| Test medium-risk cumulative return | 50.17% |
| Test high-risk cumulative return | 86.24% |

## Chapter 5 Conclusion Content

Answer each research question directly:

- RQ1: The PPO risk-ranking model provides evidence that AI/ML can support dynamic pre-allocation universe selection through realized-risk ranking, based on validation/test Spearman, reward, and tail-overlap diagnostics.
- RQ2: Predicted-rank buckets form distinct realized-risk groups. The conservative bucket is materially below the full universe, the aggressive bucket is materially above it, and the balanced bucket acts as an overlapping middle participation universe.
- RQ3: The thesis differs from common AI/ML preselection by making direct asset-risk suitability the selection criterion rather than expected return, price direction, Sharpe-like performance, or final optimizer quality.

Keep these limitations:

- Short final test window.
- Egyptian mixed-asset universe with available source data only.
- No production investor questionnaire inference.
- No return-trained objective.
- No final weight-optimization claim.
- No guarantee of outperformance.

## Formatting and Compliance Checklist

- Fix `acknowlegement` to `acknowledgement`.
- Replace placeholder submission date.
- Replace supervisor placeholders if final names are known.
- Replace placeholder abstract, results, and conclusion text.
- Populate abbreviation list.
- Expand abbreviations on first use.
- Cite every figure/table in the text.
- Add equation labels and references.
- Keep figure captions below figures and table captions above tables.
- Use "in this thesis" for own-work phrasing where appropriate.
- Use past tense for completed experiments/results and present tense for current method descriptions.
- Avoid "in this paper".
- Avoid screenshots from IDE, CLI, or rendered tables.
- Keep Chapter 4 title as `Results` unless the supervisor explicitly allows `Results and Limitations`.

## Risks and Contradictions to Avoid

- Do not describe the active model as an LLM, prompt-based agent, or multi-agent workflow.
- Do not mix the separate `portfolio-simulator-web` allocator into the thesis actor-critic architecture.
- Do not claim the PPO model optimizes expected return.
- Do not claim guaranteed outperformance.
- Do not claim the system solves final investor-tier allocation weights.
- Do not claim questionnaire inference is implemented in the thesis method.
- Do not use test metrics as selection criteria while also claiming test is untouched; keep test as reporting/final evidence.
- Do not describe alternative realized-risk target profiles as empirically promoted unless their full validation results are added.

## V3 Implementation Order

1. Archive V2.
2. Write this analysis file.
3. Update methodology for review compliance and individual actor-critic questions.
4. Rewrite Chapter 4 Results.
5. Rewrite Chapter 5 Conclusion.
6. Fix title page, declaration typo, abbreviation list, and placeholder front matter.
7. Compile and inspect the PDF.
8. Reconcile any warnings, overfull pages, missing references, or unsupported claims.

## Current Thesis Critic Audit Against Doctor's Feedback

Audit target: current live thesis source under `thesis/Bachelor Thesis Template/`
after the V3 revision pass.

Audit stance: this section evaluates the current thesis as a draft that would be
sent back to the doctor. It focuses on remaining risk, not only completed work.

Overall verdict: the current thesis is much closer to the doctor's feedback than
the archived V2 baseline. The major methodological gaps are now addressed:
Chapter 3 opens with motivation, maps research questions to method evidence,
explains the PPO actor-critic architecture, numbers the key equations, and
separates methodological process from final reported values. Chapter 4 is no
longer a placeholder and now reports environment, splits, model configuration,
ranking metrics, bucket diagnostics, baselines, ablations, and limitations.
Chapter 5 answers RQ1-RQ3 directly and keeps claims narrow.

The remaining weaknesses are mostly presentation and defense risks:

- The previous title-page supervisor placeholder has been resolved in the live
  V3 source with `Dr. Mervat Abuelkheir`.
- Chapter 4 is table-heavy. It is compliant because the tables are native LaTeX,
  numbered, captioned, and cited, but the chapter could read more convincingly
  with one or two native plots if there is time.
- Some methodology tables still contain dense implementation detail. This is
  defensible because the doctor asked for actor-critic elaboration, but it
  should not grow further.
- The final test window is short. This is acknowledged, but the defense should
  be prepared for questions about generalization.

### General Review Compliance Audit

| # | Doctor feedback | Current status | Critic evaluation | Remaining V3 action |
| ---: | --- | --- | --- | --- |
| 1 | Start methodology with motivation. | Satisfied | Chapter 3 now starts by explaining the fixed-universe assumption and why pre-allocation universe selection is the thesis problem. | No source change required. |
| 2 | Outline architecture/framework before details. | Satisfied | Figure 3.1 and the opening framework paragraph introduce data, construction, learning, selection, and evaluation layers before details. | No source change required. |
| 3 | Add evaluation design for user interaction if required. | Satisfied with scope clarification | The thesis explicitly states that it does not run a user-interaction experiment and that investor profiles are represented as risk buckets, not questionnaire users. | Keep this scope boundary during defense. |
| 4 | Make illustrations visible. | Mostly satisfied | Rendered figures are visible and vector-based. The chapter uses several TikZ diagrams. | Optional: add Results plots only if time permits. |
| 5 | Cite and discuss algorithms. | Satisfied | PPO, EGARCH, and Optuna are cited; algorithms for panel construction and monthly scoring/bucketing are included and discussed by role. | No source change required. |
| 6 | Avoid consecutive titles without text. | Satisfied | Current chapters now include explanatory text before section progression. | No source change required. |
| 7 | Title capitalization. | Mostly satisfied | Major chapter and section titles use Title Case. Technical tokens in tables remain lower-case where they are artifact names. | Do not capitalize code-like run IDs or target names. |
| 8 | Include prompt templates if prompting is central. | Satisfied as not applicable | Chapter 3 explicitly clarifies that the active system is not an LLM, does not use prompt templates, and is not a multi-agent LLM workflow. | No source change required. |
| 9 | End chapters naturally. | Satisfied | Chapter 3 has a summary bridge into Results; Chapter 5 ends with future work. | Optional: add a short Results chapter closing paragraph only if the doctor expects one. |
| 10 | Defer implementation details away from methodology. | Mostly satisfied | Methodology now defers final selected values to Chapter 4. Some feature and architecture detail remains, but it directly supports the individual review. | Do not add more implementation minutiae to Chapter 3. |
| 11 | Move hyperparameter/threshold values to Results. | Satisfied | Chapter 3 states selection process; final hyperparameters and bucket bands are reported in Chapter 4. | No source change required. |
| 12 | Formulate process as steps/algorithms. | Satisfied | Two algorithms now describe the point-in-time panel and monthly PPO scoring/bucketing. | No source change required. |
| 13 | Number and cite mathematical formulas. | Satisfied | Realized-risk rank, target composite, PPO reward, rank percentile, and bucket membership equations are numbered and referenced. | No source change required. |
| 14 | Align methodology with Chapter 1 RQs. | Satisfied | Chapter 3 includes an RQ-to-method/evidence mapping table and Chapter 4 follows the same RQ structure. | No source change required. |
| 15 | Tone down AI writing and personalize. | Improved, still subjective | The text is now thesis-specific and grounded in Egyptian data, PPO artifacts, and actual metrics. Some prose remains formal and generated-sounding in places, but not obviously generic. | During final polish, replace any overly smooth paragraphs with more direct personal research decisions. |
| 16 | Declaration/originality/help acknowledgement. | Mostly satisfied | The typo was fixed and the acknowledgments now include transparent AI-assistance acknowledgement. | Confirm whether the official declaration page itself needs a separate AI-assistance line. |
| 17 | Reduce large white spaces. | Mostly satisfied | Placeholder-driven sparse pages were removed; rendered pages are acceptable. Template chapter-opening pages still naturally contain whitespace. | No source change required unless Overleaf rendering differs. |
| 18 | Fix submission date. | Satisfied | Title page renders `8 June, 2026`. | Confirm this is the intended official date. |
| 19 | Figures/tables numbered, captioned, cited; no screenshots. | Satisfied | Figures and tables are LaTeX/TikZ, numbered, captioned, and cited in the surrounding text. | No source change required. |
| 20 | Caption placement conventions. | Satisfied | Figure captions appear below figures; table captions appear above tables. | No source change required. |
| 21 | Expand abbreviations and add list. | Mostly satisfied | Appendix now renders a real abbreviation list, and major first uses are expanded. | Final manual scan recommended for every abbreviation in Chapters 2-4. |
| 22 | Numeric square-bracket citations. | Satisfied | IEEE numeric style is preserved. | No source change required. |
| 23 | Use "in this thesis" and correct tense. | Mostly satisfied | Own-work wording now uses thesis-safe phrasing; Results use past tense for experiments and present tense for interpretation. | Final copyedit only. |
| 24 | No IDE/CLI screenshots in Results. | Satisfied | Results use native LaTeX tables only. | No source change required. |
| 25 | Chapter 4 starts with environment, data, parameters, results, statistics, discussion. | Satisfied | Chapter 4 starts with Experimental Environment, then Data Coverage and Splits, Model and Parameter Selection, Ranking Results, Risk-Bucket Diagnostics, Baseline/Ablation, and Discussion/Limitations. | Optional: add plots if a stronger visual presentation is desired. |
| 26 | Results discussion should show understanding. | Satisfied | Chapter 4 explains monthly variation, risk separation, why high return is not return prediction, and what the test does not prove. | No source change required. |

### Individual Review Compliance Audit

| Individual review point | Current status | Critic evaluation | Remaining V3 action |
| --- | --- | --- | --- |
| More details on actor-critic architecture. | Satisfied | Chapter 3 now explains a single PPO actor-critic policy with shared row encoder, pooled active-universe context, actor head, critic head, masked sigmoid-squashed Gaussian distribution, and padded-row masking. | No source change required. |
| What models? Same or different? | Satisfied | The thesis states that actor and critic are separate heads inside one masked PPO policy sharing the row encoder. It also separates promoted monthly pooled-context PPO from rejected variants. | No source change required. |
| Prompts used? | Satisfied | The thesis explicitly says there are no LLM prompts or prompt templates in the active method. | No source change required. |
| Agents or simply LLMs? | Satisfied | The thesis clarifies that "agent" means PPO reinforcement-learning policy, not an LLM agent. | No source change required. |
| Criteria of risk target promotion. | Satisfied | Chapter 3 defines the promotion protocol and Chapter 4 reports the promoted target and selected configuration. | No source change required. |
| What is the baseline? | Mostly satisfied | Chapter 4 now includes full-universe equal weight, random rank buckets, oracle buckets as non-investable upper bounds, bucket-method ablations, and literature baseline positioning. | The only possible criticism is that prior-paper baselines are not reimplemented on the same dataset; the thesis should defend this as scope/literature positioning. |
| Will baseline be in Results? | Satisfied | Baselines and ablations are now in Chapter 4. | No source change required. |

### Current Open Issues Before Doctor Review

| Priority | Issue | Why it matters | Recommended action |
| --- | --- | --- | --- |
| Medium | Results chapter is table-heavy. | The doctor's feedback emphasizes visible illustrations. Tables are valid, but visual plots can improve readability. | If time permits, add one native plot for monthly Spearman or risk-bucket separation. |
| Medium | Abbreviation first-use compliance needs a final manual pass after any new edits. | The list exists and several first-use issues were fixed, but later edits can introduce new abbreviation usage. | Re-run a source/PDF scan before submission for AI, ML, RL, PPO, EGX, CPI, USD, REIT, EGARCH, MSE, CNN, GAE, MVO, and CVaR. |
| Low | Underfull LaTeX warnings remain in narrow tables. | They do not break the PDF, but they indicate awkward line wrapping. | Accept unless the doctor is very formatting-sensitive; fixing may require wider tables or shorter labels. |
| Low | Some appendix/list pages are sparse due to the template. | This is mostly structural, not content failure. | Leave unless Overleaf output differs visually. |

### Critic Summary

The current V3 draft is defensible against the doctor's methodology feedback.
The largest conceptual risk from the individual review, confusion about whether
the actor-critic system is an LLM/prompt/multi-agent setup, is directly resolved.
The methodology now aligns with the research questions and the Results chapter
contains the missing baseline and promotion evidence.

The draft is now free of the previous supervisor-placeholder blocker. The next
best improvement would be to add one or two Results visuals if time permits.
That is not required for correctness, but it would better satisfy the feedback
that illustrations are crucial and would make the Results chapter easier to
read.
