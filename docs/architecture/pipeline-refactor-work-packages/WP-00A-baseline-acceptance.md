# WP-00A Baseline Acceptance

Status: Draft

Owner: Unassigned

Dependencies:
- WP-00 Spec Freeze

Owned paths:
- `docs/architecture/pipeline-refactor-work-packages/WP-00A-baseline-acceptance.md`
- baseline acceptance notes or scripts created specifically for this package

Read-only context paths:
- `.configs/pipelines/vista-full.toml`
- `.configs/pipelines/`
- `docs/architecture/pipeline-stage-protocols-and-dtos.md`
- `docs/architecture/pipeline-stage-present-state-audit.md`
- `.agents/skills/rerun-slam-integration/SKILL.md`

Target architecture sections:
- `Tests To Plan With The Code Refactor`
- `Stage Matrix`
- `SLAM Stage Target Sequence`


Goal:
- Freeze the behavior-preservation gate before implementation packages move production code.
- Define the reference worktree/tag, smoke matrix, artifact checks, event/status checks, and Rerun `.rrd` inspection expectations.

Out of scope:
- Refactoring production code.
- Requiring byte-identical SLAM or reconstruction outputs.
- Changing committed pipeline config files just to run a smoke variant.
- Replacing package-specific tests owned by later work packages.

Implementation notes:
- Create a clean reference worktree from the last pre-implementation refactor
  commit before production code changes begin:
  `git worktree add --detach ../prml-vslam-wp00a-reference HEAD`.
- Run the reference worktree and the candidate worktree with clean config
  copies, never by editing `.configs/pipelines/vista-full.toml`.
- Smoke config copies may disable `visualization.connect_live_viewer` to avoid
  launching an interactive viewer, but must keep
  `visualization.export_viewer_rrd = true` whenever viewer artifacts are in the
  acceptance surface.
- Smoke config copies should use unique `experiment_name` values and an
  isolated temporary `output_dir` so offline and streaming runs do not append
  to the same `summary/run-events.jsonl` file.
- Compare candidate behavior against the reference worktree by stage order,
  stage outcomes, artifact presence/type, summary/manifests, event/status
  projection, and viewer artifact validity.
- Scientific outputs do not need to be byte-identical unless a work package
  explicitly changes only packaging around deterministic mock data.
- Use the repo-local
  [Rerun SLAM integration skill](../../.agents/skills/rerun-slam-integration/SKILL.md)
  whenever `.rrd` files or Rerun entity semantics are affected.

## Reference Worktree

- Reference command:
  `git worktree add --detach ../prml-vslam-wp00a-reference HEAD`.
- Run setup in the reference worktree with the same dependency extras as the
  candidate smoke, normally `uv sync --extra dev --extra vista --extra streaming`.
- Store reference artifacts under the reference worktree's `.artifacts/`
  directory. Do not compare against artifacts from a dirty local tree.
- If a future implementation package starts from a branch that already contains
  WP-00A, capture the reference from the branch point immediately before the
  first production refactor commit, not from the implementation commit itself.

## Smoke Matrix

Use clean copies derived from `.configs/pipelines/vista-full.toml`:

| Smoke | Config copy requirement | Command | Expected current executable stages |
| --- | --- | --- | --- |
| Offline ViSTA full | Copy keeps `mode = "offline"`; optionally sets `visualization.connect_live_viewer = false`; must not mutate the committed config. | `uv run prml-vslam run-config <offline-copy.toml>` | `ingest`, `slam`, `gravity.align`, `reference.reconstruct`, `summary` |
| Streaming ViSTA full | Copy changes only `mode = "streaming"` plus non-semantic smoke controls such as live-viewer launch suppression; must keep the same source/backend/output policy. | `uv run prml-vslam run-config <streaming-copy.toml>` | streaming prepare: `ingest`, `slam`; streaming finalize: `slam`, `gravity.align`, `reference.reconstruct`, `summary` when the stream closes cleanly |

Recommended smoke-copy helper:

```bash
tmp_dir="$(mktemp -d)"
cp .configs/pipelines/vista-full.toml "$tmp_dir/vista-full-offline.toml"
cp .configs/pipelines/vista-full.toml "$tmp_dir/vista-full-streaming.toml"
uv run python - "$tmp_dir/vista-full-offline.toml" "$tmp_dir/vista-full-streaming.toml" <<'PY'
from pathlib import Path
import sys

offline = Path(sys.argv[1])
streaming = Path(sys.argv[2])

offline_text = offline.read_text()
offline_text = offline_text.replace('experiment_name = "vista-full-tuning"', 'experiment_name = "wp00a-vista-full-offline"', 1)
offline_text = offline_text.replace('mode            = "offline"', 'mode            = "offline"', 1)
offline_text = offline_text.replace('output_dir      = ".artifacts"', 'output_dir      = ".artifacts/wp00a-smoke"', 1)
offline_text = offline_text.replace("connect_live_viewer = true", "connect_live_viewer = false", 1)
offline.write_text(offline_text)

streaming_text = streaming.read_text()
streaming_text = streaming_text.replace('experiment_name = "vista-full-tuning"', 'experiment_name = "wp00a-vista-full-streaming"', 1)
streaming_text = streaming_text.replace('mode            = "offline"', 'mode            = "streaming"', 1)
streaming_text = streaming_text.replace('output_dir      = ".artifacts"', 'output_dir      = ".artifacts/wp00a-smoke"', 1)
streaming_text = streaming_text.replace("connect_live_viewer = true", "connect_live_viewer = false", 1)
streaming.write_text(streaming_text)
PY
```

## Artifact Assertions

For each successful reference and candidate smoke, inspect the run artifact root
reported by `plan-run-config` or the CLI terminal snapshot.

- Required summary artifacts:
  - `summary/run_summary.json`
  - `summary/stage_manifests.json`
  - `summary/run-events.jsonl`
- Required stage-manifest checks:
  - stage ids appear in the expected order for the smoke mode
  - terminal statuses match the corresponding `StageOutcome.status`
  - `config_hash` and `input_fingerprint` fields are present for every
    executed stage
  - output paths exist for every declared materialized artifact
- Required artifact-ref checks:
  - `ingest` includes `input/sequence_manifest.json` and benchmark inputs when
    prepared by the source
  - `slam` includes normalized trajectory and point-cloud artifacts expected by
    the selected ViSTA output policy
  - `gravity.align` includes `alignment/ground_alignment.json` when enabled
  - `reference.reconstruct` includes `reference/reference_cloud.ply` plus
    reconstruction metadata when enabled and available
  - `summary` includes summary and stage-manifest artifact refs
  - viewer-affecting runs include the expected `.rrd` artifact refs when
    `export_viewer_rrd = true`

Scientific artifact bytes may differ across reference and candidate runs. The
acceptance comparison is structural unless a work package explicitly claims a
deterministic packaging-only change.

## Event And Status Assertions

- Durable lifecycle events must include `run.submitted`, `run.started`,
  `stage.queued`, `stage.started`, terminal `stage.completed` or
  `stage.failed` for each executed stage, and one terminal run event.
- If a run root was reused and `summary/run-events.jsonl` contains older
  attempts, compare only the events for the latest intended attempt or rerun the
  smoke with a unique `experiment_name`/`output_dir` pair.
- Stage terminal events must carry `StageOutcome` values whose status matches
  the stage manifest and run summary projections.
- Streaming runs must preserve live/progress semantics:
  - packet/session telemetry remains visible in the live snapshot or current
    telemetry events
  - streaming source EOF, stop, or source/backend error is reflected in the
    terminal run state
  - downstream finalize-only stages are skipped after streaming stop/error when
    current behavior requires that skip
- Candidate target refactors may move progress and packet telemetry from
  durable telemetry events to `StageRuntimeUpdate`, but the projected app/CLI
  status must remain equivalent for operators.

## Rerun Inspection Expectations

When a package touches viewer artifacts, Rerun paths, transforms, intrinsics,
depth, pointmaps, timelines, or `.rrd` generation, inspect affected `.rrd`
outputs with the repo-local Rerun SLAM integration skill.

Minimum checks:

- Run `rrd_entity_inventory.py` on each affected repo-owned `.rrd` output.
- Confirm expected stable entity families still exist for source RGB, live or
  keyed model camera images, camera/frusta, trajectory, pointmaps, and aligned
  reference clouds when those modalities are enabled.
- Use `run_event_timeline.py` to correlate keyframe/pose/visualization notices
  with `summary/run-events.jsonl` for streaming runs.
- Use `rrd_component_arrivals.py` on narrow entity paths when an implementation
  changes transforms, pinhole camera logging, depth images, or pointmaps.
- Preserve Rerun boundary ownership: DTOs, stage runtimes, methods, and
  visualization adapters must not call the Rerun SDK directly; sinks/policy
  remain the SDK boundary.

Termination criteria:
- A clean reference worktree/tag command is documented.
- The smoke matrix names offline and streaming `vista-full.toml` runs.
- Artifact assertions cover stage outcomes, manifests, summaries, expected artifact refs, and affected viewer artifacts.
- Event/status assertions cover durable lifecycle events, terminal stage outcomes, and live/progress projection where applicable.
- Rerun `.rrd` inspection expectations are documented for viewer-affecting packages.
- The baseline gate is referenced by all implementation work packages.

Required checks:
- `make ci`
- `uv run prml-vslam run-config .configs/pipelines/vista-full.toml` with `mode = offline` via a clean config copy or equivalent override
- `uv run prml-vslam run-config .configs/pipelines/vista-full.toml` with `mode = streaming` via a clean config copy or equivalent override
- inspect affected artifact roots for summaries, stage manifests, run events, and expected artifact refs
- inspect affected `.rrd` outputs with the Rerun SLAM integration skill when viewer artifacts change
- `git diff --check`

Known risks:
- Treating “command exits successfully” as sufficient can miss broken artifact/event semantics.
- Mutating shared config files for smoke variants can pollute the baseline.
- Requiring byte-identical outputs can block structural refactors for irrelevant numerical differences.
- Skipping Rerun inspection can hide viewer-regression bugs until late integration.
