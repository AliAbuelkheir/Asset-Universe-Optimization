# Defense

This component contains the current bachelor-defense workspace.

- `documents/defense_revision_roadmap.md` is the canonical revision checklist.
- `documents/defense_slide_guide.md` summarizes each slide's main idea, bullets, and visual reminder.
- `scripts/defense_speaker_script.md` mirrors the speaker notes in the current deck.
- `slides/defense.pptx` is the only PowerPoint deck and is edited manually.
- `assets/` keeps editable diagram sources and one useful render per diagram.
- `scripts/export_slides.ps1` produces disposable slide snapshots for review.
- `qa/` is reserved for concise examiner questions and answers after the slide
  revisions stabilize.

Record all task progress directly in the roadmap by changing Markdown
checkboxes from `[ ]` to `[x]`; do not create a second TODO list.

Keep defense claims aligned with the thesis-safe framing: ranked-risk inference,
investor suitability, universe selection, and allocation are separate stages;
portfolio results are historical diagnostics, not guarantees.

## Slide Image Snapshot

Use `scripts/export_slides.ps1` to refresh ordered PNG snapshots from the current PowerPoint deck:

```powershell
powershell -ExecutionPolicy Bypass -File defense/scripts/export_slides.ps1
```

The script renders `slides/defense.pptx` into the disposable
`slides/current/` directory. Remove that directory after visual review; it is
not a source artifact.

Use `$update-defense-docs` after editing the deck to refresh the speaker script and slide guide.
