# Current Best Model

This directory is overwritten on every best-model promotion.

- model id: `downside_tail_ratio_3m_refined50`
- framework: `pit_3m_flat_context`
- feature profile: `full_current_v1`
- additive feature: `downside_tail_ratio_3m`
- input feature set: `shadow_add_downside_tail_ratio_3m`
- tuned PPO candidate: `refined50`
- seed: `13`
- selection rule: `tail_aware_validation_high_risk_overlap_with_reward_spearman_guardrails`
- source artifact: `outputs/generated/runs/tail_candidates/refined50/TAIL-REFINED50-DOWNSIDE_TAIL_RATIO_3M-S13`
- promoted at: `2026-04-30T13:11:03Z`

Canonical files:

- `best_model.zip`
- `final_model.zip`
- `setup_summary.json`
- `setup_metadata.json`
- `split_summary.csv`
- `monthly_metrics.csv`
- `ranked_predictions.csv`
- `best_model_manifest.json`

All non-canonical generated runs belong under `outputs/generated/` and are ignored by git.
