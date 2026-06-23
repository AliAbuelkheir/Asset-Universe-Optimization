---
name: update-defense-docs
description: Refresh the bachelor-defense Markdown artifacts from defense/slides/defense.pptx. Use when the defense deck, slide order, slide text, diagrams, or speaker notes change, or when the user asks to sync, extract, regenerate, or update the defense speaker script and slide guide from PowerPoint.
---

# Update Defense Docs

Regenerate the two canonical Markdown companions to the manually edited defense deck:

- `defense/scripts/defense_speaker_script.md`: speaker notes, slide by slide
- `defense/documents/defense_slide_guide.md`: each slide's main idea, visible bullets, and a short chart/diagram reminder when relevant

Never modify `defense/slides/defense.pptx`.

## Workflow

1. Confirm the repository root contains `defense/slides/defense.pptx`.
2. Extract the current deck with a bounded command:

```powershell
python .agents/skills/update-defense-docs/scripts/extract_defense_pptx.py defense/slides/defense.pptx --output defense/deck-extract.tmp.json --script-output defense/scripts/defense_speaker_script.md
```

3. Read `defense/deck-extract.tmp.json` and regenerate `defense/documents/defense_slide_guide.md` in slide order.
4. For every guide entry, include:
   - `## Slide N: Title`
   - one concise `**Main idea:**` sentence
   - visible bullet points when the slide contains a list
   - `**Diagram reminder:**` or `**Chart reminder:**` only when a visual needs explanation
5. Derive the guide from the current slide text, notes, and visuals. Do not copy the full script into it.
6. Preserve speaker-note text as written. Do not silently improve grammar, claims, transitions, or numbers. State `_No speaker notes in the PowerPoint deck._` for empty notes.
7. Flag obvious deck inconsistencies in the guide, such as notes that discuss a different slide, rather than inventing replacement narration.
8. Delete `defense/deck-extract.tmp.json` after verification.

## Verification

- Confirm both Markdown files contain exactly one ordered section per slide.
- Confirm their highest slide number equals the extracted deck count.
- Compare a sample from the beginning, middle, and end against the JSON.
- Confirm all numerical claims in the guide came from current slide text or notes.
- Run the skill validator after changing this skill:

```powershell
python C:/Users/aliab/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/update-defense-docs
```

Treat results and returns as historical diagnostics, not guarantees. Keep predicted-risk ranking, investor suitability, universe selection, and allocation conceptually separate.
