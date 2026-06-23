# Defense Revision Checklist

This is the single canonical checklist for the final defense deck and preparation.

## Current State

- The saved deck contains 49 slides.
- A video is embedded on Slide 5.
- A limitations slide is included.
- Main-deck revision is substantially complete.
- Studying, Q&A preparation, and rehearsal have not started.

## Remaining PPTX Fixes

- [x] **Slide 41 - Individual-risk limitation:** replace "scores each asset
  independently" with the accurate boundary: the method does not model
  covariance, portfolio weights, or marginal portfolio-risk contribution.
- [x] **Slide 41 - Speaker notes:** replace the duplicated research-question
  notes with a concise explanation of the three limitations shown.
- [x] **Slide 21 - Realized-risk target notes:** state that seven target-weight
  profiles were tested, the results showed weak sensitivity to the weights, and
  equal weighting was retained as the most transparent balanced definition.
- [x] Recheck slide numbering and transitions after adding the video and
  limitations slide.

## Locked Timing Decisions

- [x] Resolved: accept the bullet-based experiment slides instead of the
  proposed matrix and four-lane redesign.
- [x] Resolved: intentionally omit the EGP 100,000 ending-value callouts.
- [x] Resolved: keep the current return-aware suitability design instead of the
  longer optimizer/correlation/constraints/allocation pipeline.
- [x] Resolved: omit the detailed appendix package and retain only the existing
  formulas slide.
- [x] Resolved: retain the research-question answer-reveal animation.
- [x] Resolved: replace the short test-window limitation card with the
  individual-asset-risk scope limitation.
- [x] Resolved: retain the ranking-chart entrance/exit animation solution.

## Preparation Still Required

### Study

- [x] Study the realized-risk target, reward, seven objective-weight profiles, weak-sensitivity result, Spearman correlation, and MSE.
- [x] Study PPO, actor-critic roles, the three MLPs, masked pooling, pooled context, advantage, clipping, and variable-universe masking.
- [x] Memorize the chronological splits, checkpoint-selection role, seeds, bucket mappings, limitations, and promoted configuration.
- [ ] Study all 12 promoted inputs: name, construction/window, family, interpretation, and expected relationship to risk.
- [x] Practice explaining why asset identity is excluded and why target-only realized-risk components are not model inputs.

### Examiner Q&A

- [ ] Prepare concise answers on risk persistence and the missing persistence baseline.
- [ ] Prepare the boundary between individual-asset risk screening and final portfolio risk, including correlation and diversification limitations.
- [ ] Prepare the rationale and sensitivity evidence for the composite realized-risk target.
- [x] Prepare answers on the 11-month test window, stochastic training, promoted-checkpoint reporting, and official USD/EGP representation.
- [x] Prepare plain-language answers on why PPO was used, actor versus critic, masking, reward construction, and the model's exact contribution.

### Timing and Rehearsal

- [ ] Rehearse the complete presentation, including the video, to a maximum of 16 minutes.
- [ ] Keep Slides 10-13, the four literature slides, to approximately 90 seconds total.
- [ ] Produce and rehearse a 12-minute emergency version.
- [ ] Rehearse once with animations disabled and confirm that every slide is still understandable.
- [ ] Run a hostile Q&A rehearsal covering persistence, portfolio-risk scope, target weights, nondeterminism, the short test period, and exchange rates.
- [ ] Verify the final deck on the presentation laptop.

## Final Verification

- [ ] All numerical claims match the thesis and model artifacts.
- [ ] Slide 41 wording and speaker notes accurately describe the limitations.
- [ ] Slide numbers, transitions, videos, animations, fonts, and links work on the presentation laptop.
- [ ] The complete rehearsed delivery finishes within 16 minutes.
- [ ] The emergency delivery finishes within 12 minutes.

## Working Rule

Update this file directly as work is completed. Do not create a second defense
TODO or a separate completed-work archive.