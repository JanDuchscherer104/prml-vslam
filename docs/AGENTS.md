# Documentation Standards

This file applies to work under `docs/`, including the report, slide decks, and agent-facing
reference docs.

## Sources of Truth

- Use `README.md` for repository workflow, setup, and developer usage.
- Use `docs/Questions.md` as a high-quality human-maintained ground-truth source for challenge
  scope, clarified requirements, and product constraints.
- Use `.agents/references/agent_reference.md` as lookup material for library IDs and primary
  source references relevant to the docs work.
- Get typst-specific guidance via context7: `/websites/typst_app`

## Scope

- Report entry point: `docs/report/main.typ`
- Update-meeting deck: `docs/slides/update-meetings/update-slides.typ`
- Bibliography source: `docs/references.bib`

## General Rules

- Mirror the layout, spacing, caption style, and structure of nearby `.typ` files before making
  stylistic changes.
- Preserve the existing document architecture instead of introducing a new layout system.
- For slide work, prefer editing the relevant meeting fragment or shared partial rather than
  restructuring the full deck.
- Keep factual claims source-backed and consistent with the current benchmark contract and
  `docs/Questions.md` where challenge intent or scope is discussed.

## Typst Rules

- Keep Typst patterns stable and reproducible.
- Wrap images and tables in `#figure(...)` with a `caption:` and a `<label>`.
- Reference figures and tables via `@label`; reference bibliography entries via `@bib_key`.
- Prefer `#grid(...)` for multi-panel figure layouts.
- When experiment data is needed, load it from `csv()` or `json()` where practical, and keep the
  source structure readable enough to audit against the rendered output.
- Prefer Typst symbols and shorthands over raw Unicode glyphs when writing math or special symbols.
- For non-trivial Typst changes, use a compile-inspect-fix loop and rebuild the affected target.

## Report Writing

- Final manuscript text must be written in full paragraphs with flowing prose, not bullet lists.
- Keep the report aligned with its current IMRAD-like flow: introduction, related work, scope,
  methods, datasets, metrics, experiments, discussion, conclusion.
- Integrate citations into prose and prefer primary sources where possible.
- Verify factual claims against the cited source before adding or revising them.
- Write with clarity, precision, and a neutral scientific tone.
- Define important terms and abbreviations at first use, and keep terminology consistent across
  sections.
- Present results objectively; reserve interpretation, limitations, and broader implications for
  discussion and conclusion sections.
- Use figures and tables when they improve comprehension, and make them self-contained with
  complete captions, units, and relevant statistics.

## Slide Writing

- Slide fragments may use concise bullet lists when that improves scanability.
- Keep slide content aligned with the report and benchmark contract, but do not force report-style
  prose into every slide.
- Prefer incremental edits to the shared update-deck structure over one-off slide systems.

## Verification

- Rebuild the affected documentation target after meaningful Typst edits:
  - `make report-pdf` for report changes
  - `make slides-pdf` for update-meeting slide changes
  - `make final-slides` for final-presentation changes
  - `make docs-build` when multiple outputs were touched
