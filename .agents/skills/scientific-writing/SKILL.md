---
name: scientific-writing
description: Use when drafting, revising, or reviewing PRML VSLAM scientific prose for the report, slides, papers, abstracts, or literature-backed technical narrative.
metadata:
  mode: "writing"
  not_when:
    - "implementation-only code edits with no scientific prose"
    - "generic biomedical manuscript formatting unrelated to this project"
  handoff_to:
    - "typst-authoring for Typst layout, compilation, or figure placement"
    - "mempalace-repo for prior-session rationale and durable decisions"
    - "graphify for architecture navigation before writing about code structure"
  evidence_required:
    - "repo artifact, experiment output, source code, or primary paper for each technical claim"
    - "docs/Questions.md when prose touches project scope or evaluation intent"
  applies_to:
    - "docs/**"
    - "README.md"
    - "SETUP.md"
  triggers:
    - "scientific writing"
    - "paper"
    - "report prose"
    - "abstract"
    - "related work"
    - "discussion"
  must_read:
    - "AGENTS.md"
    - "docs/AGENTS.md when editing docs/"
    - "docs/Questions.md when scope, requirements, or evaluation intent is discussed"
  verification:
    - "render or compile the touched Typst/docs surface when non-trivial"
    - "run citation/source checks when claims or bibliography entries change"
---

# Scientific Writing

Use this skill for PRML VSLAM scientific prose. The audience is a computer
vision and spatial computing project, not a generic biomedical journal.

## Use When

- Writing or revising report, slides, abstract, introduction, method, results,
  discussion, limitations, or related-work text.
- Turning implementation or experiment facts into source-backed prose.
- Reviewing scientific claims for scope, evidence, and wording.
- Explaining architecture or evaluation choices in public-facing docs.

## Do Not Use When

- The task is only code, config, or command execution.
- A generic manuscript rule conflicts with this repo's scope, artifacts, or
  report format.
- The request needs layout mechanics first; use `typst-authoring` for Typst
  structure, rendering, and figure placement.

## Rules

- Draft with bullet outlines if useful, but final scientific prose must be
  connected paragraphs unless the target template explicitly requires a list.
- Ground every technical claim in one of: repo code, generated artifacts,
  experiment output, docs/Questions.md, or a primary source.
- Prefer primary papers and official docs for method, dataset, metric, and API
  claims. Use surveys only for broad field context.
- State scope and limits directly: dataset, method version, run configuration,
  metric, artifact path, or section boundary.
- Keep interpretation separate from measured results. Results state what was
  observed; discussion explains plausible reasons and limitations.
- Do not import generic defaults such as mandatory AI-generated figures, fixed
  figure quotas, CONSORT/STROBE/PRISMA checklists, or `research-lookup`
  requirements unless the concrete section genuinely needs them.
- Avoid inflated prose. Replace "novel", "robust", "seamless", "holistic",
  and "pivotal" with the mechanism, metric, comparison, or limitation.
- Use Context7 or official docs when prose depends on current library behavior;
  use `.agents/references/agent_reference.md` for known library IDs.

## Workflow

1. Identify the target surface and audience.
2. Read the owning docs guidance and the specific artifacts or sources behind
   the claims.
3. Build a short outline with claim, scope, evidence, limitation, and citation
   or repo path for each paragraph.
4. Convert the outline into prose with one job per paragraph.
5. Check that citations, terms, metrics, and limitations match the source
   artifacts.
6. Run the smallest render, compile, or source check that proves the touched
   surface still works.

## Paragraph Check

For each paragraph, answer:

1. What is the paragraph's single job?
2. What claim does it make?
3. What evidence supports it?
4. What scope or limitation prevents overclaiming?
5. Does the final sentence set up the next paragraph or close the section?

If any answer is unclear, fix structure and evidence before polishing style.
