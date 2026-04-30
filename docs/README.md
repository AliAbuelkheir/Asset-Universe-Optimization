# Docs

This directory uses three primary phase documents plus supporting reference
docs. The active phase is evaluation and reporting design.

## Main Documents

- [framework_phase.md](/C:/Ali/CS/Bachelor%20thesis/docs/framework_phase.md)
  records framework methodology, tested frameworks, and the locked framework
  conclusion
- [feature_phase.md](/C:/Ali/CS/Bachelor%20thesis/docs/feature_phase.md)
  records feature-phase methodology, the feature experiment matrix, and
  feature decisions
- [ppo_tuning_phase.md](/C:/Ali/CS/Bachelor%20thesis/docs/ppo_tuning_phase.md)
  records PPO tuning methodology, planned parameter sweeps, and tuning
  decisions
- [top_candidate_reruns.md](/C:/Ali/CS/Bachelor%20thesis/docs/top_candidate_reruns.md)
  records the tuned top-candidate rerun matrix and current final-model
  selection

## Supporting Reference Docs

- [project_guide.md](/C:/Ali/CS/Bachelor%20thesis/docs/project_guide.md)
  is the compact technical guide for the data contract, PPO setup, current best
  model, and future inference boundary
- [papers.md](/C:/Ali/CS/Bachelor%20thesis/docs/papers.md)
  is the literature tracker

## Supporting Files

- `diagrams/` stores diagram assets
- `Ali_Abuelkheir_thesis.pdf` is a local rendered thesis file kept for
  reference

## How To Use This Folder

- Read and update `framework_phase.md` during framework work.
- Read and update `feature_phase.md` during feature work.
- Read and update `ppo_tuning_phase.md` during PPO tuning work.
- Read and update `top_candidate_reruns.md` when final model reruns are
  repeated.
- Read `project_guide.md` when you want the consolidated technical overview.
- Keep `papers.md` focused on the defended literature set.

Current best model details live in `project_guide.md`. If a future web app is
added, its input/output contract should follow the inference boundary described
there.

If wording conflicts across repository markdown files, `AGENTS.md` remains the
source of truth.
