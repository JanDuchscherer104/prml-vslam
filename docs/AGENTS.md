# Documentation Standards

This file applies to work under `docs/` and is docs-only delta guidance on top of the root [AGENTS.md](../AGENTS.md).

## Sources of Truth

- Use [../README.md](../README.md) for repository workflow, setup, and developer usage.
- Refer to *read-only* [Questions.md](./Questions.md) for challenge scope, clarified requirements, and product constraints.
- Use package `README.md` and `REQUIREMENTS.md` files when a docs change needs current implementation or package-contract detail.
- Use [.agents/references/agent_reference.md](../.agents/references/agent_reference.md) as lookup material for library IDs and primary sources referenced by docs work.

## Scope

- report entry point: `docs/report/main.typ`
- update-meeting deck: `docs/slides/update-meetings/update-slides.typ`
- bibliography source: `docs/references.bib`

## Documentation Rules

- Preserve the current document architecture instead of introducing a new layout system.
- Keep factual claims source-backed and consistent with the current repo docs and code-backed package docs.
- Keep the root `README.md` as the project front door. Put environment and runbook detail in `SETUP.md`, and keep package-specific mechanics in the owning package `README.md` rather than repeating them in root docs.
- Avoid operational sprawl and low-level command duplication across documentation surfaces; link to the owning doc when detail already exists elsewhere.
- Mirror the layout, spacing, caption style, and structure of nearby `.typ` files before making stylistic changes.

## Typst Rules

- Keep Typst patterns stable and reproducible.
- Wrap images and tables in `#figure(...)` with a `caption:` and a `<label>`.
- Reference figures and tables via `@label`; reference bibliography entries via `@bib_key`.
- Prefer `#grid(...)` for multi-panel figure layouts.
- Prefer Typst symbols and shorthands over raw Unicode glyphs when writing math or special symbols.
- For non-trivial Typst changes, use a compile-inspect-fix loop and rebuild the affected target.

## Report Writing

- Final manuscript text must stay in full paragraphs with flowing prose, not bullet lists.
- Keep terminology consistent across report and slide surfaces.
- Keep the report aligned with its current IMRAD-like flow: introduction, related work, scope, methods, datasets, metrics, experiments, discussion, conclusion.
- Integrate citations into prose and prefer primary sources where possible.
- Verify factual claims against the cited source before adding or revising them.
- Write with clarity, precision, and a neutral scientific tone.
- Define important terms and abbreviations at first use, and keep terminology consistent across sections.
- Present results objectively; reserve interpretation, limitations, and broader implications for discussion and conclusion sections.

### Slide Writing

- Slide fragments may use concise bullet lists when that improves scanability.
- For slide work, prefer editing the relevant fragment or shared partial rather than restructuring the whole deck.

## Verification

- Rebuild the affected documentation target after meaningful Typst edits:
  - `make report-pdf` for report changes
  - `make slides-pdf` for update-meeting slide changes
  - `make final-slides` for final-presentation changes
  - `make docs-build` when multiple outputs were touched
