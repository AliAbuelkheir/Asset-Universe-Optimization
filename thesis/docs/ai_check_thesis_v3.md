# AI-Style Check: Thesis V3 PDF

Reviewed artifact: `thesis/Ali_Abuelkheir_thesis_v3.pdf`

Extraction artifact: `tmp/pdfs/Ali_Abuelkheir_thesis_v3.txt`

Date checked: 2026-06-04

## Bottom Line

The thesis has a low to moderate AI-style risk. It does not show the strongest common detector-prone signals such as generic transition chains, inflated adjectives, or broad unsupported claims. The writing is mostly technical, source-specific, and thesis-safe.

The main risk is stylistic repetition: the PDF repeatedly uses phrases such as "This thesis", "the thesis", "framework", "proposed", and formulaic chapter-summary language. That can make some sections feel machine-polished even when the content is specific and grounded.

This is not an AI-authorship determination. It is an editorial risk check based on the PDF text and rendered sample pages.

## Positive Signals

- The acknowledgments transparently disclose AI-based writing assistance for organization, wording review, and formatting suggestions while preserving author responsibility.
- The abstract, methodology, results, and conclusion use project-specific terminology: PPO, realized-risk target, filter-off baseline, equal-weight historical simulation, Spearman diagnostics, and Egyptian mixed-asset universe.
- The claim discipline is strong. The thesis repeatedly avoids guaranteed outperformance claims and separates selection diagnostics from portfolio-weight optimization.
- The scan found no meaningful use of common AI-cliche markers such as "delve", "crucial", "comprehensive", "leverage", "Moreover", "Furthermore", or "In conclusion".

## Main Risk Areas

### 1. Repeated Thesis Framing

Source locations:

- `thesis/Bachelor Thesis Template/abstract.tex:5`
- `thesis/Bachelor Thesis Template/abstract.tex:7`
- `thesis/Bachelor Thesis Template/introduction.tex:20`
- `thesis/Bachelor Thesis Template/introduction.tex:22`
- `thesis/Bachelor Thesis Template/introduction.tex:26`
- `thesis/Bachelor Thesis Template/conclusion.tex:9`
- `thesis/Bachelor Thesis Template/conclusion.tex:15`

Observed pattern:

- "This thesis" appears 19 times in the extracted PDF.
- "the thesis" appears 20 times.

Risk:

This is normal in academic writing, but repeated openings with "This thesis..." and "The thesis..." can sound generated when concentrated in the abstract, introduction, and conclusion.

Suggested direction:

Vary the subject when possible:

- "This study..."
- "The implemented system..."
- "The evaluation..."
- "The proposed selection stage..."
- "The Egyptian mixed-asset experiment..."

### 2. Heavy Use of "Framework" and "Proposed"

Source locations:

- `thesis/Bachelor Thesis Template/abstract.tex:7`
- `thesis/Bachelor Thesis Template/methodology.tex:6`
- `thesis/Bachelor Thesis Template/methodology.tex:13`
- `thesis/Bachelor Thesis Template/methodology.tex:20`
- `thesis/Bachelor Thesis Template/results.tex:55`
- `thesis/Bachelor Thesis Template/conclusion.tex:17`

Observed pattern:

- "framework" appears 44 times.
- "proposes/proposed" appears 18 times.

Risk:

"Framework" is technically valid here, but repeated use can make the writing feel generic. The strongest sections are the ones that name the actual mechanism instead: point-in-time panel, PPO risk-ranking policy, masked actor-critic ranker, and filter-off baseline.

Suggested direction:

Replace some "framework" uses with more concrete nouns:

- "risk-ranking pipeline"
- "selection method"
- "monthly PPO scorer"
- "point-in-time evaluation design"
- "pre-allocation selection stage"

### 3. Formulaic Conclusion Language

Source locations:

- `thesis/Bachelor Thesis Template/conclusion.tex:4`
- `thesis/Bachelor Thesis Template/conclusion.tex:9`
- `thesis/Bachelor Thesis Template/conclusion.tex:17`
- `thesis/Bachelor Thesis Template/conclusion.tex:24`

Risk:

The conclusion is accurate and safe, but the opening and future-work transitions are standard academic templates. This is the section most likely to read as AI-smoothed because it summarizes rather than explains.

Suggested targeted rewrites:

- Replace "This chapter concludes the thesis by..." with a direct summary of what was shown.
- Replace "Future work can extend the thesis in four directions" with "Four extensions follow from the current limits."
- Replace one or two "The contribution is..." sentences with mechanism-first phrasing.

### 4. Abstract Is Strong but Dense

Source location:

- `thesis/Bachelor Thesis Template/abstract.tex:9`

Risk:

The abstract is specific and claim-safe, but the final paragraph is very dense. Dense result summaries are not automatically AI-like, but they can feel polished in a detector-prone way.

Suggested direction:

Split or slightly simplify the result paragraph if the template allows it. Keep the numerical evidence, but reduce repeated nouns:

- "Under this comparison..."
- "The conservative bucket therefore..."
- "These findings support..."

Those three sentence starts are safe individually, but together they make the paragraph feel highly constructed.

## PDF and Metadata Notes

- `pdfinfo` reports 44 pages, A4 size, not encrypted, no JavaScript, and `Suspects: no`.
- Rendered sample pages for the title, abstract, appendix, and conclusion were readable with no obvious broken glyphs or layout failure.
- The PDF metadata has an odd `CreationDate` of 2009, likely inherited from the LaTeX template. This is not an AI-style issue, but it may look stale or template-derived in strict metadata review.

## Recommended Action

If no further revision time is available, the thesis is acceptable from an AI-style risk perspective because it includes transparent disclosure and has strong technical specificity.

If there is time for one focused pass, prioritize:

1. Reduce repeated "This thesis / the thesis" in the abstract, introduction, and conclusion.
2. Replace some generic "framework" uses with concrete mechanism names.
3. Make the conclusion less template-like while preserving the narrow claims.
4. Consider refreshing PDF metadata during the next LaTeX build if the template supports it.
