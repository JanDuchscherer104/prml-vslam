# Documentation Standards

This file applies to work under `docs/`, especially the report and slide decks.

## Scope

- Report entry point: `docs/report/main.typ`
- Update-meeting deck: `docs/slides/update-meetings/update-slides.typ`
- Bibliography source: `docs/references.bib`

## Before Editing

- Gather relevant context from $Typst , then mirror the layout, spacing, caption style, and structure of nearby `.typ` files.
- Preserve the existing document architecture instead of inventing new layout systems.
- For slides, prefer updating the relevant meeting fragment or shared partial instead of restructuring the full deck.

## Typst Rules

- Keep Typst patterns stable and reproducible.
- Wrap images and tables in `#figure(...)` with a `caption:` and a `<label>`.
- Reference figures and tables via `@label`; reference bibliography entries via `@bib_key`.
- Prefer `#grid(...)` for multi-panel figure layouts.
- If data from experiments is required, load from `csv()` or `json()`, and arrange the table source code spatial arrangement equivalentl to the render.
- Perfer Typst symbols  `sym.*` and shorthands over raw Unicode glyphs when writing math or special symbols.
- For non-trivial Typst changes, use a compile-inspect-fix loop and rebuild the affected target.

## Scientific Writing Rules

- Final manuscript text must be written in full paragraphs with flowing prose, not bullet lists.
- Bullet points are acceptable for private planning notes and, when clearly justified, limited methods-style lists.
- Keep the report aligned with its current IMRAD-like flow: introduction, related work, scope, methods, datasets, metrics, experiments, discussion, conclusion.
- Integrate citations into prose and prefer primary sources where possible.
- Verify factual claims against the cited source before adding or revising them.
- Write with clarity, precision, and a neutral scientific tone.
- Define important terms and abbreviations at first use, and keep terminology consistent across sections.
- Present results objectively; reserve interpretation, limitations, and broader implications for discussion and conclusion sections.
- Use figures and tables when they improve comprehension, and make them self-contained with complete captions, units, and relevant statistics.

## Verification

- Rebuild the affected documentation target after meaningful edits:
  - `make report-pdf`
  - `make slides-pdf`
  - `make final-slides`
