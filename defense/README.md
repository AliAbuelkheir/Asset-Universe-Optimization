# Defense

This component is for bachelor defense preparation materials.

- `documents/` stores written defense notes and handouts.
- `slides/` stores presentation decks and exported slide assets.
- `scripts/` stores talk tracks, timing drafts, and rehearsal scripts.
- `qa/` stores expected questions, answers, objections, and examiner notes.
- `assets/` stores figures, screenshots, and other reusable defense media.

Keep defense claims aligned with the thesis-safe framing: portfolio simulator outputs are historical diagnostics, not guaranteed performance claims.

## Slide Image Snapshot

Use `scripts/export_slides.ps1` to refresh ordered PNG snapshots from the current PowerPoint deck:

```powershell
powershell -ExecutionPolicy Bypass -File defense/scripts/export_slides.ps1
```

The script renders `slides/defense.pptx` into `slides/current/` as `slide-001.png`, `slide-002.png`, and so on. It exports through PowerPoint at 1920x1080, verifies the full PNG set, then replaces the previous snapshot only after a successful run. The generated snapshot folder is ignored by Git.
