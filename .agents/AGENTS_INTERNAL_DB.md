# AGENTS Internal Database

Purpose: a compact, repository-local alignment database for stable project facts, ownership boundaries, configuration policy, and current technical context. Add highly important facts here that are not discoverable or easily inferred from the current repo state, and that should be included in the canonical agent guidance as per [AGENTS.md](../AGENTS.md) and nested `AGENTS.md` files. This file is for operational memory, not for new policy or detailed implementation notes that should live in package `README.md` or `REQUIREMENTS.md` files.

This file is operational memory, not a replacement for the full repo-wide policy in [../AGENTS.md](../AGENTS.md) or the maintenance workflow in [skills/agents-db-and-simplification/SKILL.md](skills/agents-db-and-simplification/SKILL.md).

## Mission Snapshot

- Build the repository-owned scaffold for an off-device monocular VSLAM benchmark on smartphone video or streams with unknown intrinsics.
- Keep artifact boundaries typed and explicit.
- Treat the Streamlit workbench as an inspection and bounded-demo surface, not the owner of core pipeline semantics.

## Configuration Policy

- `BaseConfig` is the repo-owned config-as-factory base.
- TOML is the preferred persisted configuration surface for repo-owned `BaseConfig` derivatives.
- Use:
  - `BaseConfig.from_toml()` to hydrate persisted configs
  - `BaseConfig.to_toml()` and `save_toml()` to emit repo-owned configs
  - `PathConfig.resolve_toml_path()` for repo-relative TOML files
- Inline construction of `BaseConfig` graphs is acceptable for focused tests, tiny examples, and short-lived local helpers, but durable CLI, app, and benchmark workflows should converge on TOML inputs.

## Stable Ownership Snapshot

- `prml_vslam.interfaces.*` owns canonical shared datamodels.
- `prml_vslam.protocols.*` owns shared protocol seams such as `FramePacketStream`.
- `app` owns Streamlit-only state and rendering concerns.
- `io` owns transport and packet ingestion, not app session snapshots.
- `pipeline` owns planning, normalized run contracts, and the bounded streaming session service.

## Current Stable Facts

- `BaseConfig` already supports TOML IO in `src/prml_vslam/utils/base_config.py`.
- `PathConfig.resolve_toml_path()` already exists and should anchor repo relative config resolution.
- The current bounded pipeline demo runtime lives in `prml_vslam.pipeline.session`, not in `prml_vslam.app`.
- Packet-stream worker lifecycle is shared through `prml_vslam.utils.packet_session`.
