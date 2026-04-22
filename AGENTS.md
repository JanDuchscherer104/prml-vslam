# PRML VSLAM Agent Guidance

This repository owns the configuration, artifact layout, evaluation, and reporting layers for an off-device monocular VSLAM benchmark on smartphone video with unknown intrinsics.

## Sources Of Truth

- `AGENTS.md`: the only full repo-wide agent policy. Nested `AGENTS.md` files should add scope-specific deltas only.
- `README.md`: repository workflow, setup, developer commands, and high-level deliverables.
- `docs/Questions.md`: high-quality human-maintained ground truth for challenge intent, clarified requirements, operator-facing scope, and product constraints. Consult it whenever a task touches project scope, assumptions, or evaluation intent.
- `.github/CODEOWNERS`: ownership hints for code paths, review surfaces, and intent resolution when repo responsibilities are ambiguous.
- `.agents/references/agent_reference.md`: lookup material for Context7 library IDs and primary sources relevant to this project.
- The nearest nested `AGENTS.md` overrides this file for its subtree.

## Repo Map

- `src/prml_vslam/`: installable package and pipeline code
- `tests/`: pytest suite
- `docs/report/main.typ`: report entry point
- `docs/slides/update-meetings/`: update-meeting slides

## Repo-Wide Rules

- Read the nearest nested `AGENTS.md` before editing.
  - Python/package rules: `src/prml_vslam/AGENTS.md`
  - App-specific Streamlit rules: `src/prml_vslam/app/AGENTS.md`
  - Documentation and Typst rules: `docs/AGENTS.md`
- Treat inline resolve comments and TODOs as task-local requirements when the user points at them directly. Implement the narrowest change that satisfies the comment, remove the stale comment in the same change, and keep exploration and verification proportional unless the comment explicitly asks for broader work.
- Stay within the requested task scope. Do not implement adjacent features or speculative improvements without explicit approval.
- Prefer direct, version-targeted API usage over compatibility shims.
  - Do not add `getattr`/`hasattr`/similar reflective fallbacks for known attributes when the repository already pins or otherwise targets a concrete external API version.
  - Before adding any workaround for an external dependency, check the exact version used by the repo and implement against that version directly unless the task explicitly requires multi-version support.
- Use conventional commits with concise, focused messages. Split larger changes into multiple logical commits when appropriate.
- Before creating a commit, run `make ci`.
- Do not use destructive git commands unless explicitly requested. This includes `git restore`, `git reset --hard`, and similar commands.

## Requirements Guidance

- When drafting requirements or specs, first extract every explicit user requirement before translating it into product or engineering requirements.
- When promoting prompt-derived guidance into scaffold files or skills, persist only reusable rules, boundaries, and stable facts. Keep one-off task wording, temporary branch context, and transient cleanup notes out of canonical guidance.
- For requirements work, prioritize `README.md`, `docs/Questions.md`, the nearest `AGENTS.md`, and `.github/CODEOWNERS` when resolving intent.
- Prefer package `README.md` and `REQUIREMENTS.md` files for ownership and implementation notes rather than restating that material in nested `AGENTS.md` files.
- Resolve discoverable repo facts locally before asking questions. If ambiguity still materially changes the spec, ask clarifying questions before finalizing it. In Plan Mode, prefer extensive clarification when ambiguity remains.

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- Use `make graphify` for a concise graphify artifact, runtime, hook, and freshness dashboard
- Use `make graphify-report` when you need the report summary without the full community listing
- After modifying code files in this session, run `make graphify-rebuild` to keep the graph current
- Use `make graphify-hook-install` once per clone to enable local post-commit/post-checkout graph refreshes
