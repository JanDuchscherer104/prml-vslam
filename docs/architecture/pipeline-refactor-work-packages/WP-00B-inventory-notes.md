# WP-00B Inventory Notes

This note records the audit evidence for
[WP-00B DTO Class Inventory Audit](./WP-00B-dto-class-inventory-audit.md).

## Dependency And Scope

- `WP-00 Spec Freeze` is frozen, so the declared WP-00B dependency is
  satisfied.
- `WP-00A Baseline Acceptance` is WIP. WP-00B does not depend on WP-00A, but
  later implementation packages still use WP-00A as the behavior-preservation
  gate.
- `pipeline-stage-protocols-and-dtos.md` remained read-only. Classification
  changes were made in the DTO migration ledger instead.
- Inline source TODOs were added after the audit at user request for DTOs and
  classes that the ledger marks for replacement, collapse, movement, or
  deletion once the target pipeline architecture is implemented.
- `WP-R` is waived for this package because the audit changed only
  documentation and did not change production behavior.

## AST Inventory

Command shape:

```bash
uv run python - <<'PY'
# Parse every src/prml_vslam/**/*.py file with ast.
# Collect classes whose direct bases include BaseData, BaseConfig,
# TransportModel, BaseModel, Protocol, StrEnum, Enum, or IntEnum.
# Inspect subscripted bases such as FactoryConfig[...] through their value.
PY
```

Result:

- Python files scanned: `155`
- Audited classes found: `207`
- Ledger literal-missing classes before WP-00B addendum: `101`
- Coverage after the ledger addendum: every audited class appears in
  `pipeline-dto-migration-ledger.md`.

## code-index Cross-Check

The code-index MCP project path was set to `/home/jandu/repos/prml-vslam` and
the deep index was rebuilt. Summaries were reviewed for the required high-risk
files:

- `src/prml_vslam/pipeline/contracts/events.py`
- `src/prml_vslam/pipeline/contracts/request.py`
- `src/prml_vslam/pipeline/contracts/runtime.py`
- `src/prml_vslam/interfaces/slam.py`
- `src/prml_vslam/interfaces/ingest.py`
- `src/prml_vslam/benchmark/contracts.py`
- `src/prml_vslam/eval/contracts.py`
- `src/prml_vslam/methods/configs.py`
- `src/prml_vslam/methods/protocols.py`
- `src/prml_vslam/reconstruction/contracts.py`
- `src/prml_vslam/visualization/contracts.py`
- `src/prml_vslam/app/models.py`

The code-index review confirmed the highest-risk migration surfaces are the
current pipeline event/request/runtime DTOs, live SLAM DTOs still in
`interfaces.slam`, method backend protocols/configs, and app-facing snapshot
models.

## graphify Context

`graphify-out/GRAPH_REPORT.md` was read before final classification.

Relevant graph context:

- Corpus: `197` files, about `1,226,581` words.
- Graph: `3169` nodes, `7494` edges, `216` communities.
- High-connectivity hubs include `PathConfig`, `CameraIntrinsics`,
  `DatasetId`, `AppContext`, `SequenceManifest`, `FrameTransform`,
  `Record3DDevice`, `PacketSessionSnapshot`, and `Console`.

The hub list supports prioritizing package-wide contracts and shared DTOs in
the ledger while treating app, dataset, IO, plotting, and wrapper-local DTOs as
explicitly out of scope unless they cross pipeline public contracts.
