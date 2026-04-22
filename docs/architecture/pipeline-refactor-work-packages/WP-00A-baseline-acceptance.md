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
- Create a clean reference worktree or tag from the pre-refactor branch/commit before production implementation begins.
- Recommended clean reference worktree command:
  `git worktree add ../prml-vslam-wp00a-reference HEAD`.
- Run smoke variants from clean config copies or explicit non-mutating overrides so `mode = offline` and `mode = streaming` can both be exercised from `.configs/pipelines/vista-full.toml` without committing local config churn.
- Compare behavior against the reference worktree by stage order, stage outcomes, artifact presence/type, summary/manifests, event/status projection, and viewer artifact validity.
- Scientific outputs do not need to be byte-identical unless a work package explicitly changes only packaging around deterministic mock data.
- Use the repo-local [Rerun SLAM integration skill](../../.agents/skills/rerun-slam-integration/SKILL.md) whenever `.rrd` files or Rerun entity semantics are affected.

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
