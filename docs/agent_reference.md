# Agent Reference

## Contract Ownership

- `src/prml_vslam/app/models.py`
  - App-owned Streamlit UI and session state only.
- `src/prml_vslam/io/interfaces.py`
  - Camera, frame, and replay-stream contracts owned by IO.
- `src/prml_vslam/datasets/interfaces.py`
  - Dataset identifiers and normalized dataset-level trajectories.
- `src/prml_vslam/eval/interfaces.py`
  - Evaluation controls, result payloads, and metrics-page discovery DTOs.
- `src/prml_vslam/methods/interfaces.py`
  - Method identifiers and method-run contracts only.
- `src/prml_vslam/pipeline/contracts.py`
  - Pipeline run requests, plans, manifests, artifact bundles, and summaries.
- `src/prml_vslam/pipeline/workspace.py`
  - Prepared-input and capture-manifest types used across methods and pipeline.

## Pipeline Boundary

The current artifact-first pipeline boundary is:

1. `RunRequest`
2. `RunPlan`
3. `SequenceManifest`
4. Stage artifact bundles such as `TrackingArtifacts`, `DenseArtifacts`, and
   `ReferenceArtifacts`
5. `RunSummary`

The planner remains lightweight. It does not yet execute stages, but all new
execution work should build on these typed contracts rather than reintroducing
planner-only request types or app-owned run semantics.

## Dataset Normalization

- ADVIO is owned by `src/prml_vslam/datasets/advio.py`.
- `AdvioSequence.to_sequence_manifest()` is the current normalization hook from
  dataset-owned structures into the shared pipeline boundary.
- Replay remains available through the OpenCV producer for streaming-style app
  integration.
- The repo now commits `src/prml_vslam/datasets/advio_catalog.json` as pinned
  upstream metadata for official scene archives and calibration sources.
- `AdvioDatasetService` owns local ADVIO summary statistics and selective scene
  or modality downloads into `PathConfig.resolve_dataset_dir("advio")`.

## App Boundary

- The packaged Streamlit app remains a thin surface over repo-owned services.
- Metrics discovery and `evo` execution are owned by
  `src/prml_vslam/eval/services.py`.
- `src/prml_vslam/app/services.py` is restricted to Record3D app glue and the
  session-local preview runtime controller.
- The ADVIO page is dataset-management UI only. It renders catalog metadata and
  explicit download actions, but dataset semantics stay in `datasets/`.
