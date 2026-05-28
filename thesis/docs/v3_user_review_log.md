# V3 User Review Log

Created on: 2026-05-24
Reset on: 2026-05-27

Purpose: Track user review notes for the V3 thesis while the thesis is being
reviewed. Items in this file are logged only and must not be implemented until
the user explicitly approves an edit pass.

## Review Items

No pending implementation items remain from this review batch.

### V3-001 Abstract Baseline Flow

- Source note: The final abstract paragraph feels abrupt around the sentence:
  "The empirical baseline is a filter-off full active universe under the same
  equal-weight historical diagnostic rule; ..."
- Discussion direction: Keep the filter-off full-active-universe baseline in the
  abstract because it directly supports RQ3 and matches the supervisor-facing
  baseline framing. Rephrase it so it explains why the comparison is being made:
  isolating the PPO selection stage while holding the equal-weight diagnostic
  constant.
- Thesis implications: Abstract-only wording change expected. No methodology,
  results, or conclusion change appears necessary because those sections already
  define the filter-off baseline and avoid unsupported return-optimization
  claims.
- Implemented wording uses "proposed risk-tolerance-based universe
  construction" instead of "selection stage" to stay consistent with the final
  RQ3 phrasing.
- Status: Implemented in `abstract.tex`.

### V3-002 RQ3 Wording

- Source note: User believes RQ3 should be reframed as: "How does the proposed
  risk-tolerance-based asset-universe compare with a full active-universe
  baseline when the same downstream weight allocation rule is applied".
- Current thesis state: `introduction.tex` already uses a close version:
  "How does the proposed risk-tolerance-based asset-universe selection stage
  compare with a full active-universe baseline when the same downstream
  weighting rule is applied?"
- Discussion direction: The change is directionally correct because RQ3 should
  be an empirical filter-on versus filter-off comparison, not a broad conceptual
  comparison against AI/ML literature. User rejected "selection stage" in the RQ
  wording because the comparison should name the outputs directly: the proposed
  risk-tolerance-based asset universe(s) versus the full active universe.
  Prefer "equal-weight historical simulation" or "equal-weight diagnostic rule"
  over "weight allocation rule" to avoid implying that the thesis implements a
  final optimizer.
- Thesis implications: Main thesis prose is already aligned in Introduction,
  Results, and Conclusion. During implementation, verify the compiled source/PDF
  uses the current RQ3 and consider updating stale copied guidance text only if
  it is treated as active documentation. Historical V2 review notes can remain
  unchanged unless the user wants a documentation cleanup.
- Proposed wording: "How do the proposed risk-tolerance-based asset universes
  compare with the full active-universe baseline when each is evaluated under
  the same equal-weight historical simulation rule?"
- Status: Implemented in `introduction.tex`, with related RQ3 wording aligned
  in `results.tex` and `conclusion.tex`.

### V3-003 Table 3.7 Placement and Chapter 3 Ordering

- Source note: User feels Table 3.7 is in the wrong place because it appears in
  the feature-set/input-selection area before the investor bucketing section.
- Current thesis state: Table 3.7 is `tab:promotion_protocol`, captioned
  "Promotion and reporting protocol". It appears near the end of
  `Feature-Set Testing and Input Selection`, before `Investor Risk Profile
  Mapping and Bucketing`.
- Discussion direction: The concern is valid. Table 3.7 is not only a feature
  table; it summarizes architecture, feature profile, reward definition,
  realized-risk target, PPO tuning, final model, and bucket diagnostics. User
  prefers keeping `Method Selection and Promotion Protocol` before
  `Feature-Set Testing and Input Selection` because that matches the actual
  implementation order: architecture/framework tests came before feature-set
  tests.
- Preferred structural fix after discussion: Table 3.7 should not sit between
  related methodology component sections. Because it summarizes the methodology
  / implementation order, place it before the detailed component sections as an
  upfront roadmap, most likely near the end of `Proposed Framework Overview`
  after the layered pipeline figure. Reframe the caption/text from a narrow
  "Promotion and reporting protocol" table into a "Methodology implementation
  and promotion order" table. This lets the reader see the full development
  sequence before reading the detailed sections.
- Additional wording consideration: Since an upfront table will mention items
  before their detailed sections, the surrounding prose should explicitly call
  it a roadmap. Rows should use concise stage names and avoid deep technical
  detail that belongs later. The Method Selection section can then keep the
  architecture/framework comparison discussion, while the roadmap table gives
  the whole chapter/implementation order.
- Thesis implications: Mostly structural. Section numbers and table numbering
  may shift, but LaTeX references should update automatically. Some local
  transition paragraphs would need rewriting so feature testing no longer
  depends on a promotion-protocol section that appears later. No empirical
  results or thesis claims need to change.
- Status: Implemented in `methodology.tex`.
  The table will be renumbered automatically because it was moved near the
  beginning of Chapter 3.

### V3-004 Table 4.4 Reporting Decision Column

- Source note: User does not like the `Reporting decision` column in Table 4.4
  (`tab:feature_selection_evidence`). It either should be removed or clarified
  so it shows what each testing phase achieved, such as removed features or
  added features.
- Current thesis state: Table 4.4 has columns `Testing phase`,
  `What was tested`, and `Reporting decision`. Some decisions are concrete
  (`Added the three-month downside-tail contribution ratio`), but others are
  generic (`Used as diagnostics for redundancy and weak inputs`).
- Discussion direction: Keep the third column, but rename and clarify it. If
  removed, the table loses the main result of each feature-testing phase. A
  clearer outcome column is more useful for defense because it shows that the
  feature phase was controlled and did not become arbitrary trial-and-error.
- Preferred wording direction: Rename `Reporting decision` to `Outcome for final
  input set` or `Feature-selection outcome`. Make each row action-oriented:
  baseline families retained; leave-one-out/drop checks did not justify
  removing a whole family; replacement/window checks did not replace the
  canonical definitions; additive tail/ratio checks added
  `downside_tail_ratio_3m`.
- Follow-up verification: User recalled that a feature may have been removed in
  leave-one-out checks. Repository evidence shows a removal/neutralization
  candidate for `distance_to_3m_high` (`drop_distance_to_3m_high` and
  `full_current_v2_no_distance_to_3m_high`), but the authoritative current-best
  model uses base feature profile `full_current_v1` and input feature set
  `shadow_add_downside_tail_ratio_3m`. The best-model metadata lists
  `distance_to_3m_high` among active input columns and adds
  `downside_tail_ratio_3m`. Therefore the table should not say a feature was
  removed from the final promoted model unless a separate active artifact proves
  otherwise. Safer wording: leave-one-out checks tested removals, including
  `distance_to_3m_high`, but no dropped feature was retained in the final
  current-best input set.
- Thesis implications: Table-only wording change plus possibly one preceding
  sentence. No results or model claims change. Keep validation-first language so
  test improvements from rejected candidates are not treated as selection
  evidence.
- Status: Implemented in `results.tex`.

### V3-005 Table 4.6 Promoted Model Configuration Cleanup

- Source note: User feels Table 4.6 (`tab:promoted_config`) needs cleaning by
  removing unneeded rows and columns. Example: `Base feature profile` is
  unnecessary because Table 4.5 already lists the exact final features. User is
  open to removing the table entirely.
- Current thesis state: Table 4.6 has two columns (`Item`, `Promoted value`) and
  rows for Model, Framework, Base feature profile, Additive feature, Input view,
  Actor context mode, Reward design, Risk target, and Training method. It sits
  after the final input-feature table and before the tuned PPO hyperparameter
  table.
- Discussion direction: Do not remove the table entirely unless it becomes
  fully redundant after editing. A short configuration table is useful in the
  Results chapter because it states exactly what model the remaining results
  evaluate. However, the current version repeats details already covered by
  Table 4.5 and Chapter 3.
- Preferred cleanup: Keep Table 4.6 but shrink it to the configuration choices
  that are necessary to interpret the reported results and are not already
  exhaustively listed nearby. Remove or merge rows such as `Base feature
  profile`, `Additive feature`, `Input view`, and `Actor context mode`.
  Suggested remaining rows: `Promoted model`, `Framework`, `Realized-risk
  target`, `Reward profile`, `Training procedure`, and possibly `Input features`
  only as a cross-reference to Table 4.5 if needed.
- Thesis implications: Table 4.6 becomes a concise evaluated-configuration
  summary, not a repeated inventory. Update the preceding and following
  sentences so they no longer claim that the table reports all final
  configuration values. The tuned hyperparameter table should remain separate.
- Status: Implemented in `results.tex`.

### V3-006 Table 4.8 Remove High-Risk Top-25 Percent Overlap Column

- Source note: User wants the `High-risk top-25% overlap` column removed
  entirely from Table 4.8 (`tab:split_ranking_results`).
- Current thesis state: The ranking-results introduction currently says
  high-risk top-25% overlap is included as a tail-ranking diagnostic, and
  Table 4.8 reports it alongside months, mean assets, reward, and Spearman.
- Discussion direction: Accept the removal. The abstract and main RQ1 evidence
  rely on reward and Spearman, so the overlap column adds a secondary diagnostic
  that may distract from the promoted thesis claim. Removing it makes the table
  cleaner and more consistent with the headline model-quality evidence.
- Thesis implications: Remove the column from Table 4.8 and revise surrounding
  sentences so they no longer introduce or refer to high-risk top-25% overlap.
  Keep reward first and Spearman as the rank-alignment diagnostic. Do not alter
  the underlying model metrics or current-best artifact documentation.
- Status: Implemented in `results.tex`.

### V3-007 Remove Table 4.13 Benchmark Asset Context

- Source note: User wants Table 4.13 removed along with its descriptions/text.
- Current thesis state: Table 4.13 (`tab:benchmark_asset_context`) reports
  fixed single-exposure benchmark context for money-market exposure, government
  bonds, EGX30 equity index, REIT index, and gold after the equal-weight
  baseline table.
- Discussion direction: Accept the removal. The table is contextual rather than
  necessary for answering RQ3. It may distract from the core comparison between
  the full active-universe baseline and the proposed risk-tolerance-based asset
  universes under the same equal-weight historical simulation rule.
- Thesis implications: Remove the paragraph introducing
  `tab:benchmark_asset_context`, remove the table itself, and connect the
  baseline comparison text directly to validation bucket diagnostics / bucket
  ablation. Table numbering will update automatically. The RQ3 claim remains
  intact because Table 4.12 already contains the required full-universe versus
  filtered-universe comparison.
- Status: Implemented in `results.tex`.
