# Eval

This package remains the thin explicit evaluation layer for persisted run
artifacts.

## Current Scope

- discover normalized run artifacts
- resolve reference and estimate trajectories
- run explicit `evo` APE trajectory evaluation
- persist and reload evaluation results

## Boundary

`prml_vslam.eval` does not own benchmark-policy composition. Policy now lives in
`prml_vslam.benchmark`, while evaluation execution remains here.

## MVP 1 Usage

This section describes how to execute and validate MVP 1 trajectory evaluation.

### 1. Enable trajectory evaluation in RunRequest TOML

Ensure your RunRequest TOML includes:

- benchmark.trajectory.enabled = true
- benchmark.trajectory.baseline_source set appropriately
	- for current datasets this is typically ground_truth

### 2. Plan and run

Plan run:

```bash
uv run prml-vslam plan-run-config <your_config.toml>
```

Execute run:

```bash
uv run prml-vslam run-config <your_config.toml>
```

### 3. Check expected artifacts

Under the run root, MVP 1 should produce:

- evaluation/trajectory_metrics.json
- summary/run_summary.json
- summary/stage_manifests.json

### 4. Validate trajectory stage status

- In run_summary, trajectory_evaluation should appear with ran or failed.
- In stage_manifests, trajectory_evaluation should include input and output provenance paths.

### 5. Use Streamlit

Start app:

```bash
uv run streamlit run streamlit_app.py
```

Current MVP 1 behavior:

- Pipeline page accepts plans containing trajectory_evaluation.
- Metrics page can load persisted trajectory metrics and explicitly recompute when needed.

## Current MVP 1 Status

The README content above is up to date with the current implementation state:

- trajectory evaluation is part of the executable offline pipeline stage slice
- trajectory stage status and provenance are persisted in summary artifacts
- Streamlit pipeline and metrics surfaces support MVP 1 trajectory evaluation flow
