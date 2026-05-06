# AGENTS.md

## Repository Layout

- `ppo-risk-model/` is the existing PPO asset ranked-risk project. Its own `AGENTS.md` remains the source of truth for data, training, evaluation, leakage, and thesis-safe PPO claims.
- `portfolio-simulator-web/` is the stateless MERN-compatible web simulator that calls the PPO project through a Python ML service.
- `thesis/` stays unchanged and remains the thesis source/PDF workspace.

## Working Rules

- Do not mix web serving logic into `ppo-risk-model/src/training`.
- Do not move, rewrite, or clean `thesis/` unless explicitly requested.
- Keep model inference, investor risk tolerance, asset-universe selection, and weight optimization separated by adapters.
- Until external model files are provided, keep questionnaire inference disabled and keep the optimizer clearly labeled as a mock equal-weight adapter.
- Report portfolio results as historical simulation diagnostics, not as proof of guaranteed outperformance.

