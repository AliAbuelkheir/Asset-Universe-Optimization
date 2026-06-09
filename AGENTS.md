# AGENTS.md

## Repository Layout

- `ranked-risk-model/` is the existing PPO asset ranked-risk project. Its own `AGENTS.md` remains the source of truth for data, training, evaluation, leakage, and thesis-safe PPO claims.
- `portfolio-simulator/` is the stateless MERN-compatible web simulator that calls the PPO project through a Python ML service.
- `thesis/` stays unchanged and remains the thesis source/PDF workspace.
- `defense/` contains defense preparation materials such as documents, slides, scripts, Q&A notes, and supporting assets.

## Working Rules

- Do not mix web serving logic into `ranked-risk-model/src/training`.
- Do not move, rewrite, or clean `thesis/` unless explicitly requested.
- Keep model inference, investor risk tolerance, asset-universe selection, and weight optimization separated by adapters.
- Until external model files are provided, keep questionnaire inference disabled and keep the optimizer clearly labeled as a mock equal-weight adapter.
- Report portfolio results as historical simulation diagnostics, not as proof of guaranteed outperformance.

## Agent skills

### Issue tracker

Issues and PRDs live as local markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical triage roles, using their default label strings. See `docs/agents/triage-labels.md`.

### Domain docs

Multi-context: `CONTEXT-MAP.md` at the root points to a `CONTEXT.md` per component. See `docs/agents/domain.md`.

