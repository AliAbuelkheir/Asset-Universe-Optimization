# Defense Diagram Design

Use these rules for future diagrams and figures created in `defense/assets/`.

## Visual Style

- Keep diagrams simple enough to understand within a few seconds.
- Use transparent backgrounds so figures inherit the slide's light-gray background.
- Use `#0C171F` navy for text, borders, arrows, and primary shapes.
- Use `#00F700` green only as a minimal accent, such as a small marker or short highlight.
- Do not use green for large filled areas, thick bars, borders, or body text.
- Prefer thin navy outlines and generous whitespace over filled shapes.
- Use rounded rectangles sparingly and consistently.

## Typography

- Use **Century Gothic** for all diagram text.
- Use bold text only for headings, family names, or key outcomes.
- Keep body labels short and presentation-readable.
- Avoid placing a title inside a figure when the PowerPoint slide already has a title.

## Content

- Show only information needed to support the spoken script.
- Prefer grouped concepts over detailed tables.
- Avoid repeating explanations that will be spoken.
- Keep model inputs, targets, and outputs visually separate when they appear together.

## Output Files

- Keep an editable source file beside each rendered asset.
- Export a transparent PNG as the primary PowerPoint asset.
- Create any white-background or PDF preview outside `defense/` and delete it
  after visual review; do not retain duplicate renders in the asset folder.
- Use descriptive names such as `slide_15_feature_families_transparent.png`.


## Motion Graphics

- Match the slide canvas with a solid light-gray background (`#F2F3F3`) when
  exporting H.264, because the PowerPoint-compatible codec does not preserve
  transparency.
- Use Century Gothic throughout motion assets so typography remains consistent
  with the deck.
- Keep chart structure, bars, labels, and explanatory text in navy (`#0C171F`).
- Use green (`#00F700`) only for short cap markers, small transition
  emphasis, or a compact visual cue; it must not become a large fill.
- Keep data identities in fixed screen positions whenever the intended lesson is
  change over time. Animate the measured value, not the category location.
- State chart direction explicitly whenever a larger mark could be interpreted
  as better performance.
- Include a concise historical-diagnostic qualifier in full-slide videos.
