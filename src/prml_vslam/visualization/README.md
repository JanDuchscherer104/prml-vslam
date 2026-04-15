# Visualization

This package owns thin viewer/export policy plus the repo-owned Rerun
integration layer.

## Current Scope

- visualization policy through `VisualizationConfig`
- repo-owned normalized `.rrd` export helpers
- preserved native upstream `.rrd` handling

Rerun recordings are viewer artifacts. TUM trajectories, PLY clouds, manifests,
and stage summaries remain the scientific/provenance source of truth.

## Rerun Usage

Start the live viewer with the project blueprint:

```bash
uv run rerun .configs/visualization/vista_blueprint.rbl --serve-web
```

When using the web viewer, open the encoded proxy URL:

```text
http://127.0.0.1:9090/?url=rerun%2Bhttp%3A%2F%2F127.0.0.1%3A9876%2Fproxy
```

Enable `connect_live_viewer = true` in the pipeline request, or toggle
**Connect live Rerun viewer** in the Streamlit Pipeline page before starting the
run.

To inspect a persisted repo-owned recording:

```bash
uv run rerun .artifacts/<run_id>/visualization/viewer_recording.rrd .configs/visualization/vista_blueprint.rbl
```

`connect_live_viewer` and `export_viewer_rrd` can be enabled together. The
streaming runner attaches both gRPC and file sinks to the same explicit
recording stream through the Rerun multi-sink API.
