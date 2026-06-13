---
name: scientific-writing
description: Use when writing or revising PRML VSLAM scientific report, slides, captions, related work, methods, results, discussion, or source-backed manuscript prose.
metadata:
  mode: "research"
  applies_to:
    - "docs/**"
  evidence_required:
    - "docs/AGENTS.md"
    - "docs/Questions.md when scope, assumptions, or challenge intent matter"
    - "primary source or repo artifact for factual claims"
  handoff_to:
    - "typst-authoring for non-trivial Typst layout or compile work"
---

# Scientific Writing

Use this repo-local skill instead of generic manuscript-writing defaults when
the task touches PRML VSLAM documentation, report text, slides, captions,
related work, methods, results, discussion, or bibliography-backed claims.

## Read First

1. `docs/AGENTS.md` for documentation and Typst ownership.
2. `docs/Questions.md` when challenge scope, assumptions, or product intent
   matter.
3. The nearest report, slide, or docs source being edited.
4. `.agents/references/agent_reference.md` when dependency docs or primary
   source links are needed.

## Rules

- Defer to `docs/AGENTS.md` and nearby Typst/report patterns for layout,
  citation, and build commands.
- Do not apply generic biomedical reporting defaults unless the task explicitly
  concerns those study types.
- Do not require generated schematics by default. Add or revise figures only
  when the report, slide narrative, or user request needs them.
- Write report/manuscript text in full paragraphs with neutral scientific prose.
  Slide fragments may use concise bullets when scanability matters.
- Keep claims source-backed. Prefer primary papers, official docs, current repo
  artifacts, and package-owned contracts over secondary summaries.
- Keep implementation-heavy architecture detail out of main scientific prose
  unless the section is explicitly about system design; route dense detail to
  appendices, figures, or architecture docs when appropriate.
- Preserve existing terminology and section flow before inventing new framing.

## Workflow

1. Identify the owning surface: report, slides, architecture docs, or source
   manifest.
2. Extract the scientific claim, result, method, or narrative gap to fix.
3. Gather only the sources needed to support that change.
4. Draft in prose first for report text; use bullets only for slide-ready
   fragments or planning notes.
5. Check citation keys, figure labels, and terminology against nearby sources.
6. Rebuild the affected target when Typst or generated docs changed.

## Verification

- `make report-pdf` for report changes.
- `make slides-pdf` for update-meeting slide changes.
- `make final-slides` for final-presentation changes.
- `make docs-build` when multiple documentation outputs changed.
- For text-only scaffold changes to this skill, parse frontmatter and inspect
  links instead of rebuilding documents.
