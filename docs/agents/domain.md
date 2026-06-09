# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root, or
- **`CONTEXT-MAP.md`** at the repo root if it exists — it points at one `CONTEXT.md` per context. Read each one relevant to the topic.
- **`docs/adr/`** — read ADRs that touch the area you're about to work in. In this multi-context repo, also check `<component>/docs/adr/` for context-scoped decisions.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The producer skill (`/grill-with-docs`) creates them lazily when terms or decisions actually get resolved.

## File structure

This is a multi-context repo (a `CONTEXT-MAP.md` at the root points to a `CONTEXT.md` per component):

```
/
├── CONTEXT-MAP.md                     ← points to each component's CONTEXT.md
├── docs/adr/                          ← system-wide decisions
├── ranked-risk-model/                 ← PPO asset ranked-risk model
│   ├── CONTEXT.md
│   └── docs/adr/                      ← context-specific decisions
├── portfolio-simulator/               ← MERN web simulator + Python ML service
│   ├── CONTEXT.md
│   └── docs/adr/
├── defense/                           ← defense prep materials and assets
│   └── CONTEXT.md
└── thesis/                            ← thesis source / PDF workspace
    └── CONTEXT.md
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/grill-with-docs`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_
