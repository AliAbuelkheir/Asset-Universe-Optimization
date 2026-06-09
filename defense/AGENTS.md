# AGENTS.md

## Defense Purpose

This folder is for preparing the bachelor thesis defense and trial feedback
sessions. Keep all defense-specific planning, slide drafts, scripts, Q&A notes,
figures, and rehearsal material here.

## Current Defense Roadmap

1. Plan the talk structure as topics with 3-4 subtopics each.
   - Treat each subtopic as approximately one slide unless the content is too
     small or too dense.
   - Prefer a narrative arc over a thesis chapter dump: problem, gap, method,
     validation, simulator, limitations, contribution.

2. Write the exact presentation script.
   - Pair each slide with the intended spoken explanation.
   - Mark places where diagrams, charts, tables, demo screenshots, or result
     callouts are needed.
   - Keep claims thesis-safe and defensible.

3. Design the actual slides after the structure and script are stable.
   - Slides should support the spoken argument, not duplicate the full script.
   - Prioritize clear diagrams, compact result summaries, and visual evidence.
   - Use consistent terminology with the thesis and `ranked-risk-model/AGENTS.md`.

## Audience Context

- A trial defense with the Beltone team and the supervisor doctor is expected
  next week. Use it to collect feedback on clarity, finance assumptions,
  methodology framing, and likely examiner questions.
- The final defense audience includes the supervisor with a computer science
  background and a foreign German accounting professor.
- The defense must be understandable to both technical and finance/accounting
  listeners.
- The finance part must be especially strong: asset classes, risk definitions,
  ranking interpretation, benchmark framing, portfolio diagnostics, and the
  limits of historical simulation should be explained clearly.

## Claim Discipline

- Present the PPO model as a ranked-risk scorer over a variable asset universe,
  not as a guaranteed return optimizer.
- Report simulator outputs as historical simulation diagnostics, not proof of
  guaranteed outperformance.
- Keep model inference, investor risk tolerance, asset-universe selection, and
  weight optimization conceptually separate.
- Be explicit that ranked-risk prediction and portfolio allocation are separate
  stages.
- Avoid overclaiming financial performance. Emphasize risk ranking quality,
  leakage controls, point-in-time construction, and diagnostic comparisons.

## Finance Topics To Be Ready For

- Why these asset classes are included and what each represents in the Egyptian
  market context.
- Difference between return, volatility, downside deviation, max drawdown,
  realized risk, and predicted risk.
- Why ranks and buckets are useful for risk-aware selection.
- Why EGX30 is used as the equity benchmark and why full-universe comparisons
  matter.
- How treasury bill and bond yield quotes are converted for return/risk
  calculations.
- Why historical backtests/simulations do not imply future performance.
- What the optimizer does and does not prove.
- Why risk tolerance, asset selection, and weights should stay separated.

## Preparation Outputs

- `documents/`: outline documents, defense plan, examiner-oriented explanation
  notes, and finance cheat sheets.
- `scripts/`: slide-by-slide speaking script and timed rehearsal drafts.
- `slides/`: PPTX decks and exported slide images.
- `qa/`: expected questions, concise answers, objections, and trial feedback.
- `assets/`: diagrams, charts, screenshots, and reusable visuals.

## Working Rules

- Do not create, edit, modify, repair, or regenerate `.pptx` files in this
  folder. The user handles PowerPoint files manually. Keep slide content,
  speaker notes, and deck instructions in Markdown/source files only.
- Do not edit `../thesis/` from defense work unless explicitly requested.
- When a defense claim depends on model methodology, check
  `../ranked-risk-model/AGENTS.md` first.
- Keep defense materials aligned with the thesis-safe claim: the promoted model
  creates distinct realized-risk buckets from predicted ranks.
- Prefer simple, examiner-friendly explanations before adding technical detail.
- For every finance-heavy slide, prepare at least one likely question and a
  concise answer in `qa/`.
