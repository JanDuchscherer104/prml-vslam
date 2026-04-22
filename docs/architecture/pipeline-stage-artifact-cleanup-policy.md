# Pipeline Stage Artifact Cleanup Policy

This note records the target policy for cleaning up stage artifacts after a
pipeline run. It is a companion to
[pipeline-stage-refactor-target.md](./pipeline-stage-refactor-target.md) and
[pipeline-stage-refactor-pruning.md](./pipeline-stage-refactor-pruning.md).

The policy is target architecture only. Current legacy `RunRequest` TOML files
must not add executable cleanup tables until `StageConfig.cleanup` exists in
the active config models.

## Target Contract

Every future config derived from `StageConfig` exposes a nested `cleanup`
policy. Cleanup is stage runtime policy, not backend output policy, so it
belongs on the stage config base rather than under backend-specific output
sections such as `slam.outputs`.

Target policy shape:

```python
class ArtifactCleanupPolicy(BaseConfig):
    artifact_keys: list[str] = []
    on_completed: bool = True
    on_failed: bool = False
    on_stopped: bool = False
```

Target TOML shape:

```toml
[stages.slam.cleanup]
artifact_keys = ["native_output_dir", "native_rerun_rrd", "extra:*"]
on_completed = true
on_failed = false
on_stopped = false
```

Defaults preserve artifacts unless `artifact_keys` is non-empty.

## Artifact Selection

Cleanup selects artifacts by stable stage artifact keys from
`StageOutcome.artifacts`, not by filesystem paths. This avoids arbitrary path
deletion and keeps cleanup tied to the same artifact surface used by manifests,
summaries, and app inspection.

Supported selectors:

- exact keys such as `native_output_dir`, `native_rerun_rrd`, `rgb_dir`,
  `trajectory_tum`, `dense_points_ply`, or `viewer_rrd`
- safe prefix selectors with trailing `:*`, such as `extra:*`,
  `visualization:*`, or `reference_tum:*`

Unsupported selectors:

- arbitrary filesystem paths
- filesystem globs
- parent directory traversal
- deleting the run artifact root itself

The cleanup implementation must resolve selectors only against the
stage-local artifact map. A selector that matches no artifact keys is recorded
as a skipped cleanup item rather than treated as a filesystem pattern.

## Cleanup Timing

Cleanup runs after summary and stage manifests are written. This preserves a
complete provenance record of what was produced before selected artifacts are
pruned.

The cleanup epilogue should:

1. read the terminal `StageOutcome` values and artifact maps
2. match each stage cleanup policy against that stage's artifact keys
3. refuse unsafe paths
4. delete selected files/directories under the run artifact root
5. record cleanup metadata back into final provenance

Cleanup must not delete:

- `run_summary.json`
- `stage_manifests.json`
- the run artifact root
- paths outside the run artifact root
- artifacts that are not selected through `StageOutcome.artifacts`

## Terminal Status Policy

Cleanup behavior is controlled independently for completed, failed, and stopped
runs:

- `on_completed`: cleanup after a completed run
- `on_failed`: cleanup after a failed run
- `on_stopped`: cleanup after a stopped run

The recommended defaults are:

```toml
on_completed = true
on_failed = false
on_stopped = false
```

This saves disk space for successful runs while preserving debugging evidence
when a run fails or is stopped.

## Provenance

Final provenance should retain the original artifact references and mark
selected artifacts as pruned. Do not remove artifact references from manifests
or summaries just because the cleanup epilogue deleted their paths.

Cleanup metadata should record at least:

- stage key
- artifact key
- artifact path
- cleanup status: `deleted`, `missing`, `skipped_outside_run_root`,
  `skipped_unselected`, or `failed`
- reason or error message when applicable

Failed cleanup should not turn a successful run into a failed run. It should be
recorded as cleanup metadata and surfaced as a warning/status detail.

## Migration Note For `vista-full.toml`

[vista-full.toml](../../.configs/pipelines/vista-full.toml) currently uses the
legacy `RunRequest` shape. Until `StageConfig.cleanup` exists, do not add a
real `[slam.cleanup]` table or `[stages.slam.cleanup]` table to that file.

When the config migration is active, replace the inline TODO with a commented
target example:

```toml
# Target StageConfig cleanup policy:
# [stages.slam.cleanup]
# artifact_keys = ["native_output_dir", "native_rerun_rrd", "extra:*"]
# on_completed = true
# on_failed = false
# on_stopped = false
```

The executable cleanup table should be added only after the active config model
supports `StageConfig.cleanup`.

## Tests To Add With Implementation

- config tests proving every concrete `StageConfig` inherits `cleanup` with
  safe defaults
- selector tests for exact keys, prefix selectors, unmatched selectors, and
  rejected filesystem-like selectors
- safety tests for outside-run-root paths, summary artifacts, and run-root
  deletion refusal
- lifecycle tests for `on_completed`, `on_failed`, and `on_stopped`
- provenance tests proving pruned artifacts remain listed with cleanup metadata
- compatibility tests proving legacy TOML files remain loadable until the full
  `RunConfig + [stages.*]` migration lands
