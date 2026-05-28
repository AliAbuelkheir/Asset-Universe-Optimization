# Doctor Feedback Matrix

Last updated: 2026-05-06

This file tracks the first feedback cycle from the doctor and maps each item to
the planned V2 response. It is a working control document, not thesis prose.

## Feedback Items

| ID | Feedback item | Current status | V2 response | Thesis/document location |
| --- | --- | --- | --- | --- |
| F1 | Research questions need to be explicit and clear. | Not yet implemented in thesis text. | Add 2-3 explicit RQs after the problem statement once the baseline framing is confirmed. Draft RQs are stored below. | `introduction.tex` |
| F2 | Add one or two RQs covering RL, asset selection, and risk adaptation. | Not yet implemented in thesis text. | Use RQs that distinguish risk ranking, bucket separation, and baseline comparison. | `introduction.tex` |
| F3 | Clarify target asset types. | Partially documented in repo, not explicit enough in thesis. | State that the thesis uses a mixed Egyptian-market universe: 91-day T-bills, 5-year government bonds, EGX30/equity exposure, EGX30 constituent stocks when available, REIT, gold, USD, and CPI macro inputs. | `introduction.tex`, `methodology.tex` |
| F4 | Expand literature to about 30 papers. | Current thesis cites about 16 papers. | Expand the defended set to about 30 verified papers across portfolio preliminaries, preselection, personalization, RL/DRL, and closest-gap papers. | `docs/papers.md`, `references.bib`, later `literature_review.tex` |
| F5 | Start literature with portfolio-management preliminaries and investor profiles. | Current literature starts directly from thesis framing and preselection. | Reorganize V2 literature flow from classical portfolio management to investor profiles, ML/deep/RL methods, preselection, and gap synthesis. | `literature_review.tex` after baseline memo approval |
| F6 | Discuss and compare algorithms/methods and their limitations. | Current review has narrative critique but no matrix. | Add a comparison matrix using method dimensions relevant to the thesis. | `docs/papers.md`, later `literature_review.tex` |
| F7 | Build a comparison table showing where papers fit or fall short. | Not yet implemented in thesis text. | Use the matrix in `docs/papers.md` as the thesis source table. | `docs/papers.md`, later `literature_review.tex` |
| F8 | Determine which literature papers serve as the baseline. | Needs careful framing. | Present a baseline group rather than one exact paper: classical full-universe/equal-weight/MVO, ML preselection plus optimizer papers, investor-risk recommendation papers, and RL allocation papers. | `docs/baseline_comparison_memo.md`, later `results.tex` |
| F9 | Evaluate whether a direct baseline paper exists. | Researched and unresolved as an exact match. | Defend that no one-to-one paper was found for independent Egyptian mixed-asset RL risk ranking before allocation; propose baseline group plus ablation. | `docs/baseline_comparison_memo.md` |
| F10 | Avoid unsupported return-optimization claims. | Already documented in repo guidance. | Keep thesis-safe claim: the model creates distinct realized-risk buckets from predicted ranks. Treat returns as secondary diagnostics. | `AGENTS.md`, `project_guide.md`, later `results.tex` |

## Draft Research Questions

RQ1: Can a month-level reinforcement-learning model rank the active Egyptian
asset universe by realized risk without using asset identity or future
information?

RQ2: Do predicted risk ranks produce distinct conservative, balanced, and
aggressive asset-universe buckets compared with a full-universe benchmark?

RQ3: How does the proposed dynamic risk-ranking stage compare conceptually and
empirically with classical allocation, machine-learning preselection,
personalized recommendation, and reinforcement-learning portfolio-management
baselines?

## Meeting Point For The Doctor

The proposed meeting question is whether the doctor accepts a baseline group
plus an internal ablation, because the literature search found close papers but
not an exact match for the thesis setup.

The closest paper is Orra et al. 2025, which combines investor-specific risk
profiles, volatility-guided asset grouping, and DRL allocation. The difference
is that the current thesis evaluates a month-level RL risk-ranking stage over a
variable Egyptian mixed-asset universe, with allocation and investor-tier
serving kept outside the active training path.
