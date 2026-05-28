# Methodology V2 Edit Log

Workspace: `C:\Ali\CS\Bachelor thesis`

## Sources Checked

- `AGENTS.md`
- `ppo-risk-model/AGENTS.md`
- `ppo-risk-model/docs/project_guide.md`
- `ppo-risk-model/docs/framework_phase.md`
- `ppo-risk-model/docs/feature_phase.md`
- `ppo-risk-model/docs/ppo_tuning_phase.md`
- `ppo-risk-model/src/training/experiment_profiles.py`
- `ppo-risk-model/src/training/portfolio_evaluation.py`
- `thesis/Bachelor Thesis Template/methodology.tex`
- `thesis/Bachelor Thesis Template/bachelor.tex`

## Requested Change Register

| ID | Request | Planned thesis action | Status |
| --- | --- | --- | --- |
| 1 | Expand CNN/daily-input discussion. | Added academic daily-flat/daily-strip CNN explanation. | Done |
| 2 | Remove "expected return alone" and add point-in-time leakage language. | Rewritten scope/objective wording around realized-risk ordering and chronological point-in-time evaluation. | Done |
| 3 | Redesign Figure 3.2 data pipeline. | Replaced TikZ figure with source CSVs, macro inputs, engineering, monthly panel, metadata/features/target-only branches. | Done |
| 4 | Replace vague realized-risk weight wording with exact trials. | Added compact objective-profile table from `experiment_profiles.py`. | Done |
| 5 | Reframe `realized_risk` as ordering signal. | Rewritten composite-target section around cross-sectional ordering and secondary numeric score prediction. | Done |
| 6 | Include exact reward-function audits. | Added reward-profile table from `experiment_profiles.py`. | Done |
| 7 | Move dataset/point-in-time section before realized-risk target. | Reordered methodology sections. | Done |
| 8 | Limit Investing.com format claim to raw market CSV files. | Rewritten raw data wording. | Done |
| 9 | Clarify CPI and USD/EGP are macro features. | Updated raw data table and macro feature discussion. | Done |
| 10 | Replace generic reward paragraph with exact runs. | Covered by reward audit table. | Done |
| 11 | Use small methodology tables/lists instead of log-dump prose. | Added objective, reward, framework, and bucket audit tables. | Done |
| 12 | Improve daily-input variants paragraph. | Added motivation, definitions, 23-day/4-channel setup, and promotion conclusion. | Done |
| 13 | Defend PPO as supporting investor-profile asset selection, not as the thesis objective. | Rewritten RL/PPO and alternatives sections. | Done |
| 14 | Add bucket-method table. | Added table for `tercile_no_overlap`, `overlap_40_50`, `wide_overlap_50_60`, and `tail_30_overlap`. | Done |
| 15 | Revise evaluation wording to selected universe vs full/raw universe without committing to equal weights. | Rewritten evaluation text and Figure 3.7; allocation layer remains separate. | Done |
| 16 | Remove Table 3.8. | Removed the promoted investor profile bucket definitions table from Section 3.8 while keeping the bucket-method audit table and percentile-band diagram. | Done |

## Verification Register

| Step | Result |
| --- | --- |
| LaTeX compile | Done. `pdflatex -interaction=nonstopmode -halt-on-error bachelor.tex` completed successfully after reruns. No undefined references or fatal errors. Remaining log issue is one tiny list-of-figures overfull line. |
| Chapter 3 visual inspection | Done. Rendered methodology pages with `pdftoppm`; checked pages covering Chapter 3 figures and tables. |
| Final PDF copy to thesis parent folder | Done. Copied compiled PDF to `thesis/bachelor.pdf` and `thesis/ali_abuelkheir_thesis_v2.pdf`. |
