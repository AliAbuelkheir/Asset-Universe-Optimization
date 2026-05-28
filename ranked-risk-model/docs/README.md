# Docs

This folder is the documentation hub for the thesis project. `AGENTS.md`
remains the repository source of truth when wording conflicts.

## Core Technical Docs

- [project_guide.md](project_guide.md)
  is the compact technical guide: data contract, active PPO setup, current best
  model, thesis evaluation, and inference boundary.
- [framework_phase.md](framework_phase.md)
  is the closed framework-selection record.
- [feature_phase.md](feature_phase.md)
  is the closed feature and tail-candidate record.
- [ppo_tuning_phase.md](ppo_tuning_phase.md)
  is the closed PPO tuning and current-best rerun record.

## Thesis Support Docs

- [papers.md](papers.md)
  tracks the defended literature set, comparison matrix, and baseline argument.
- [baseline_comparison_memo.md](baseline_comparison_memo.md)
  summarizes the baseline position for supervisor discussion.
- [doctor_feedback_matrix.md](doctor_feedback_matrix.md)
  maps supervisor feedback to planned thesis revisions.

## Supporting Files

- `diagrams/` stores diagram assets.
- The current rendered thesis PDF lives under `../../thesis/`.

## Usage Rules

- Use `project_guide.md` for the current technical state.
- Use phase docs only for historical methodology and decisions.
- Use `papers.md` and the baseline memo for thesis literature and defense
  framing.
- Keep generated runs and reports under `outputs/generated/`; do not add local
  run dumps to `docs/`.
