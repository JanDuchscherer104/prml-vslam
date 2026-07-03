---
name: report-final-deliverables
description: Use when writing, revising, or reviewing PRML VSLAM final report or slide deliverables under docs/report or docs/slides, including Typst figures, tables, citations, bibliography references, scientific claims, VSLAM metrics, alignment, method or dataset framing, protocol text, limitations, result statements, and final presentation prose.
---

# Report Final Deliverables

Use this as the compact front door for final report and final slide work. Keep
the hot path short: route to the owning source files, verify claims, and avoid
copying external workflow trees into this repository.

## Grounding

Start every report or slide task from the local sources of truth:

1. Read `docs/AGENTS.md` and the target Typst entry point or fragment.
2. For scope, challenge framing, or claim decisions, read `docs/Questions.md`
   and use the final-paper guidance below.
3. For citations, inspect `docs/references.bib`. For method, dataset, or
   protocol facts, prefer package `README.md` or `REQUIREMENTS.md`, tracked
   artifacts, and primary papers or official sources.

Do not use tests, app UI files, branch names, PR numbers, or raw chat text as
manuscript evidence. Tests can verify behavior, but they are not report
references.

## Final Paper Guidance

Write the report as a benchmark-methodology paper, not as a general leaderboard.
The defensible contribution is the measurement substrate: source normalization,
method adapters, frame and scale semantics, alignment protocol, persisted
artifacts, manifests, and diagnostic visualization. Local result tables may
describe the available artifact sweep, but broad method-ranking claims require a
frozen method-dataset matrix, sampling policy, and archived metric artifacts.

Architecture belongs in the main text only when it explains a scientific
consequence, such as artifact interpretation, frame semantics, alignment, or
metric admissibility. Detailed implementation diagrams belong in the appendix.

Before adding or revising a result sentence, verify that the claimed run exists
as a frozen artifact with configuration, normalized input, method output,
alignment metadata, and metric CSV or JSON files. Each result row should make
the dataset, sequence set, method, sampling policy, trajectory reference,
alignment mode, cloud reference, ICP threshold, hardware or runtime context,
and artifact provenance recoverable from the manuscript or appendix.

Figures and tables must have self-contained captions that state what produced
the display item and whether it is a protocol checklist, local result summary,
or supplementary architecture diagram.

## Professor/Moodle Deliverable Gate

Final report work must cover the stable Moodle/professor content requirements
without depending on ignored `.agents/work/` course-material files being present
in every clone:

- Domain Introduction & Goals
- Methodology
- Results
- Future Work
- Retrospective: what went right, what went wrong
- Work breakdown for the report and the code

Map these requirements onto the current scientific report structure instead of
forcing awkward top-level headings. Domain introduction and goals belong in the
introduction and benchmark-scope framing. Methodology covers source
normalization, method adapters, datasets, metrics, alignment, and artifact
protocol. Results belong in the experimental protocol and local evidence
tables. Future work belongs in discussion or conclusion. Retrospective content
should be short, neutral, and placed in discussion, conclusion, or an appendix
subsection. Work breakdown should be reported separately from scientific
evidence, preferably as an appendix or supplementary table.

Respect the course constraints when checking final deliverables: the report
target is 15 pages excluding bibliography and appendix; the current Typst report
template is the template unless explicitly changed; all team members need an
equal share of report and code work; the final presentation is 20 minutes with
equal speaking time; and the delivered project consists of prototype, report,
presentation, and working code with a descriptive README.

## Writing Workflow

Work section by section.

- Report prose must be full paragraphs with neutral scientific tone.
- Slide text may be concise fragments or bullets when that improves scanability.
- Match the nearby Typst style, spacing, labels, captions, and citation style.
- Keep architecture details only when they explain scientific consequences,
  artifact interpretation, frame semantics, or metric choices.
- Keep the current report shape: introduction, related work, scope, methods,
  datasets, metrics, experiments, discussion, conclusion, and appendix, while
  still representing the Moodle-required retrospective and work-breakdown
  content.
- Preserve five-member equal participation in final deliverables; evidence
  ownership is not final authorship or final speaking ownership.

## Claim Audit

Before finalizing a sentence, classify the claim:

- implementation fact
- method summary
- dataset or protocol statement
- result
- limitation
- future work
- retrospective/process claim
- work-breakdown/contribution claim

Then verify it against the correct evidence tier. Do not turn implementation
status, protocol design, or planned validation into empirical superiority.
State unvalidated dense-cloud, efficiency, and leaderboard claims as future
validation targets unless frozen metric artifacts exist.

## VSLAM And Metric Rules

For trajectory or geometry metrics, name the reference source, pose direction
or coordinate frame, alignment mode, units, thresholds, and artifact
provenance. Make clear whether the statement is protocol, result, or
interpretation.

Handle these topics explicitly when they appear:

- monocular scale ambiguity and Sim(3) alignment
- SE(3), Sim(3), or gravity-aware scale-yaw-translation alignment
- ARCore or ARKit as optional provider or baseline evidence, not hidden ground
  truth
- dense-cloud placement versus dense-cloud quality
- source normalization across ADVIO, TUM RGB-D, Record3D, and custom captures
- method-local world frames versus benchmark-normalized outputs

## Scientific Writing QA

Before final delivery, check the report against the professor's scientific
writing rules:

- use concise, precise, neutral language
- introduce technical terms and abbreviations before first use
- back claims with citations, tracked artifacts, or explicit limitations
- name prior work clearly instead of claiming external work as project work
- make results reproducible, checkable, and tied to the artifact contract
- reference every figure, table, and listing in text and give it a meaningful
  caption
- explain every variable used in mathematical notation
- avoid a heading immediately followed by another heading
- inspect the final PDF for text overflow, bad word breaks, and page/layout
  problems

## Typst Edit Loop

Use the smallest focused Typst edit.

- Wrap figures and tables in `#figure(...)` with `caption:` and a label.
- Reference figures and tables with `@label`.
- Reference bibliography entries with `@bib_key`.
- Prefer existing `booktabs` and grid patterns.
- Do not replace the local IEEE-style report template or slide template unless
  explicitly requested.

After meaningful Typst edits, run the owning build:

```bash
make report-pdf
make slides-pdf
make final-slides
```

Report only commands that actually ran. If a build cannot run, state the exact
blocker and the next-best check used.
