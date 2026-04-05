# AGENTS Internal Database

Purpose: a compact, repository-local alignment database for stable project facts, workflow rules,
configuration policy, and tracked technical debt.

## 0) Mission Snapshot
- Build the repository-owned scaffold for an off-device monocular VSLAM benchmark on smartphone
  video or streams with unknown intrinsics.
- Keep artifact boundaries typed and explicit.
- Treat the Streamlit workbench as an inspection and bounded-demo surface, not the owner of core
  pipeline semantics.

## 1) Non-Negotiable Workflow
- Read this file, `README.md`, `docs/Questions.md`, and the nearest `AGENTS.md` before substantial
  work.
- Use `rg` and narrow file reads instead of bulk-loading the repository.
- Never use destructive git commands unless the user explicitly requests them.
- Keep changes scoped to the requested task; record validated debts in `.agents/issues.toml` and
  `.agents/todos.toml` instead of opportunistically fixing unrelated areas.

## 2) Configuration Policy
- `BaseConfig` is the repo-owned config-as-factory base.
- TOML is the preferred persisted configuration surface for repo-owned `BaseConfig` derivatives.
- Use:
  - `BaseConfig.from_toml()` to hydrate persisted configs.
  - `BaseConfig.to_toml()` / `save_toml()` to emit repo-owned configs.
  - `PathConfig.resolve_toml_path()` for repo-relative TOML files.
- Inline construction of `BaseConfig` graphs is acceptable for focused tests, tiny examples, and
  short-lived local helpers, but durable CLI, app, and benchmark workflows should converge on TOML
  inputs.

## 3) Contract Ownership Snapshot
- `prml_vslam.interfaces.*` owns canonical shared datamodels.
- `prml_vslam.protocols.*` owns shared protocol seams such as `FramePacketStream`.
- `app` owns Streamlit-only state and rendering concerns.
- `io` owns transport and packet ingestion, not app session snapshots.
- `pipeline` owns planning, normalized run contracts, and the bounded streaming session service.

## 4) Internal Tracking Databases
- `.agents/issues.toml`
  - Use for validated defects, integration gaps, and architectural debt.
  - Keep entries stable and update `status`, `priority`, `summary`, `files`, and `notes` as the
    repo evolves.
- `.agents/todos.toml`
  - Use for actionable follow-up work linked to issue IDs.
  - Keep acceptance criteria explicit and update status in place instead of deleting rows.

## 5) Current Stable Facts
- `BaseConfig` already supports TOML IO in `src/prml_vslam/utils/base_config.py`.
- `PathConfig.resolve_toml_path()` already exists and should anchor repo-relative config resolution.
- The current bounded pipeline demo runtime lives in `prml_vslam.pipeline.session`, not in
  `prml_vslam.app`.
- Packet-stream worker lifecycle is shared through `prml_vslam.utils.packet_session`.
