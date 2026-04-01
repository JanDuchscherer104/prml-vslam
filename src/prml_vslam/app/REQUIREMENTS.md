# PRML VSLAM Metrics-First Streamlit App Requirements

## Summary

This document is the source of truth for the future metrics-first Streamlit app refactor that will
target `src/prml_vslam/app/`.

The app's primary audience is repo developers and researchers reviewing benchmark outputs, not the
future emergency-call operator product. The v1 app focuses on trajectory evaluation and `evo`-driven
analysis, with the primary navigation flow:

`dataset -> sequence -> method/run`

The current Streamlit workbench in `src/prml_vslam/app.py` is legacy context. Its planning,
materialization, offline runtime, and streaming-demo capabilities are not required v1 scope for the
new metrics-first app unless they are reintroduced deliberately later.

Record3D streaming is now one such deliberate later addition: it may exist as a clearly separated
secondary inspection page, but it must not collapse the app back into a monolithic workbench or
displace the metrics-first primary flow.

## Sources Of Truth

- `README.md` defines the project workflow, current Streamlit entrypoint, evaluation scope, and
  deliverables.
- `docs/Questions.md` defines the clarified project intent, including operator-facing long-term
  goals, real-time context, and dataset expectations.
- `AGENTS.md` and `src/prml_vslam/AGENTS.md` define standing repo and Python-package engineering
  rules.
- `.github/CODEOWNERS` identifies `@JanDuchscherer104` as the sole code owner. When product or
  architecture intent is ambiguous, owner-authored repo guidance is authoritative until superseded.
- The existing app surface in `src/prml_vslam/app.py`, the evaluation contracts in
  `src/prml_vslam/eval/trajectory.py`, and the current artifact layout under `artifacts/` define
  the concrete local baseline this refactor must respect.

## Extracted Input Requirements

The following requirements are extracted directly from the initiating prompt before interpretation:

- The current Streamlit app is considered inadequate and needs a clearer requirements foundation.
- Create a `REQUIREMENTS.md` file in `prml_vslam/app`.
- List all app requirements in that file.
- If uncertainty remains, ask extensively for details in Plan Mode before locking the spec.
- Follow best practices for developing Streamlit apps with Pydantic state management.
- Use a simple modern design.
- Display `evo` metrics for the selected dataset.
- Integrate natively with `PathConfig`.
- Use Plotly for plotting.
- Define plotting in separate plotting modules.
- Type all interfaces.
- Every explicit requirement from the prompt must be extracted first before interpretation.
- CODEOWNERS-backed owner intent must be foundational to the contents of this requirements document.

Prompt note: the original `PathConfig` clause was truncated in the user prompt. Subsequent
clarification established that all path handling is the responsibility of `PathConfig`, and the app
may assume its fields are valid.

## Functional Requirements

- The v1 app must be a metrics-first Streamlit application centered on evaluation review rather than
  pipeline execution.
- The primary workflow must start with dataset selection, then sequence selection, then method or
  run selection.
- The app must display `evo` trajectory evaluation metrics for the selected dataset slice.
- The app must surface the provenance needed to interpret each metric result:
  dataset, sequence, method or run, pose relation, alignment flag, scale-correction flag, matching
  pairs, metric values, and source paths.
- The app must read persisted evaluation results when they already exist.
- The app must offer an explicit user action to compute `evo` metrics when the required trajectory
  artifacts exist but no persisted evaluation result is available yet.
- The app must not compute metrics implicitly on page load, rerun, or selector change.
- The app must handle missing data honestly and explicitly. If required trajectories or evaluation
  outputs are absent, the UI must explain what is missing instead of fabricating placeholders or
  silently falling back.
- The app should support dataset roots exposed by `PathConfig`. ADVIO should be treated as a
  first-class dataset because it is already present in repo docs, tests, and local sample data.
- For datasets without meaningful sequence subdivision, the sequence step may collapse to one
  logical unit, but the selection model must remain compatible with the canonical
  `dataset -> sequence -> method/run` flow.

## Architecture Requirements

- The future refactor target is `src/prml_vslam/app/`.
- `streamlit_app.py` must remain a thin entrypoint that delegates into packaged app bootstrap code.
- The app package must be composed of small, typed modules instead of one monolithic file.
- Page modules must focus on rendering and orchestration, not on inline domain logic.
- App logic that is useful outside Streamlit must stay in reusable non-UI modules rather than being
  reimplemented inside page code.
- The app must reuse the existing evaluation contract surface in `prml_vslam.eval`, especially
  `TrajectoryEvaluationConfig`, `evaluate_tum_trajectories`, and persisted evaluation outputs, or a
  future equivalent that preserves the same role.
- Existing planning, materialization, offline runtime, and streaming-demo workbench flows should be
  treated as legacy context during the metrics-first refactor, not as mandatory v1 modules.

## State Management Rules And Typing

- All app-facing interfaces must be typed.
- Typed interfaces include state models, page context objects, service adapters, repository or
  artifact selectors, action handlers, and plotting function signatures.
- App state must be modeled with Pydantic.
- One session-state adapter must be the only code allowed to read from or write to raw
  `st.session_state`.
- Page modules and widgets must work against typed state objects instead of mutating arbitrary
  `st.session_state` keys.
- Persisted state must be JSON-friendly so that Streamlit reruns and navigation restore cleanly.
- State transitions for explicit actions such as dataset selection, run selection, and evaluation
  requests must be representable through typed models rather than loose dictionaries.

## PathConfig Integration Requirements

- All path discovery, default roots, and path ownership must come from `PathConfig`.
- The app must consume `PathConfig` as the authoritative source for dataset roots, artifact roots,
  and any other app-relevant path defaults.
- The app must not introduce parallel ad hoc path-default logic in page code.
- The app may assume `PathConfig` fields are valid once provided.
- This document intentionally references `PathConfig` as a contract without naming its concrete
  module path yet, because that symbol is not visible in the current checkout. The implementation
  should bind to the real contract once it is present in the working tree.

## Plotting Rules

- All plotting must use Plotly.
- Plotly figure construction must live in dedicated plotting modules inside `src/prml_vslam/app/`.
- Page modules must call typed plotting functions and must not build complex figures inline.
- Plotting modules must accept typed, domain-level inputs and return Plotly figure objects.
- The metrics UI should combine compact summary cards with Plotly-based visual summaries where the
  visualization adds interpretive value beyond a table.

## UX Rules

- The visual direction must be simple, modern, and light-first.
- Layout should prioritize compact analysis surfaces over decorative marketing-style sections.
- Prefer restrained typography, compact cards, compact tables, and clear spacing.
- Minimize sidebar dependence. Primary navigation and interpretation should work in the main
  content area.
- Avoid hero-copy-first layouts, ornamental prose, and visual noise that displaces metrics or
  provenance.
- User actions that change state materially, such as triggering evaluation, must be explicit and
  clearly labeled.

## Acceptance Scenarios

### Persisted Metrics Review

- A user selects a dataset, a sequence, and a method or run.
- The app resolves the relevant artifact paths through `PathConfig` and repo-owned artifact
  conventions.
- If a persisted evaluation result exists, the app renders the metrics summary and provenance
  without recomputing anything.

### Explicit Metric Computation

- A user selects a dataset slice whose reference and estimated trajectories exist.
- No persisted evaluation summary exists yet, or the user intentionally wants a fresh evaluation.
- The app exposes a clear compute action.
- When triggered, the app runs the existing `evo` evaluation path explicitly, then renders the
  result and any persisted output path.

### Missing Data Handling

- A user selects a dataset slice that lacks the required reference trajectory, estimate trajectory,
  or both.
- The app does not run hidden fallbacks.
- The UI explains which required artifact is missing and why the evaluation cannot proceed yet.

### Selection Flow Stability

- The app preserves the user's dataset, sequence, and run selection across Streamlit reruns and
  internal navigation through typed persisted state.
- The selection state remains valid JSON-serializable session data.

## Non-Functional Requirements

- The app must remain readable and maintainable as the codebase transitions away from the current
  monolithic `src/prml_vslam/app.py`.
- The app must fail clearly when dependencies or required artifacts are missing.
- The app must avoid inventing benchmark semantics that conflict with repo-owned contracts.
- The app must prefer reuse of existing repo contracts and artifact formats over app-local
  reinvention.

## Acceptance Criteria

- The requirements document preserves every explicit app-relevant prompt requirement in extracted
  form before interpretation.
- The future app architecture targets `src/prml_vslam/app/` with a thin `streamlit_app.py`
  entrypoint.
- The future app is metrics-first and uses the primary flow `dataset -> sequence -> method/run`.
- The app reads persisted `evo` results when present.
- The app offers an explicit compute action for `evo` metrics when the necessary trajectories
  exist.
- The app never computes metrics implicitly on page load or selector change.
- All app-facing interfaces are typed.
- Pydantic-backed state and a single session-state adapter govern persistent Streamlit state.
- Plotly figure construction lives in dedicated plotting modules, not in page modules.
- `PathConfig` is the sole authority for path defaults and path ownership.
- The UI stays simple, modern, light-first, and analysis-oriented.

## Out Of Scope For V1

- Recreating the full existing workbench scope from `src/prml_vslam/app.py`.
- Treating offline pipeline execution, workspace materialization, or streaming demos as mandatory
  first-class surfaces in the new metrics-first app.
- Introducing hidden fallback path logic outside `PathConfig`.
- Replacing the repo's existing `evo` evaluation contracts with an unrelated app-local metric
  implementation.
