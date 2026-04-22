# WP-00B DTO Class Inventory Audit

Status: Complete

Owner: Unassigned

Dependencies:
- WP-00 Spec Freeze

Owned paths:
- `docs/architecture/pipeline-dto-migration-ledger.md`
- `docs/architecture/pipeline-refactor-target-dir-tree.md`
- `docs/architecture/pipeline-refactor-work-packages/`
- inventory notes or scripts created specifically for this audit

Read-only context paths:
- `src/prml_vslam/**/*.py`
- `docs/architecture/pipeline-stage-protocols-and-dtos.md`
- `docs/architecture/pipeline-stage-refactor-target.md`
- `docs/architecture/pipeline-refactor-target-dir-tree.md`
- `graphify-out/GRAPH_REPORT.md`
- `src/prml_vslam/REQUIREMENTS.md`
- package-local `REQUIREMENTS.md` files

Target architecture sections:
- `Generic DTO And Domain Payload Architecture`
- `DTO Simplification Targets`
- `Public Contract Placement`
- `Benchmark Versus Eval`
- `Future Implementation Inventory`

Goal:
- Inspect every Python source file under `src/prml_vslam`.
- Classify every `BaseData`, `BaseConfig`, `TransportModel`, important
  `Protocol`, and important enum class as migrated, moved, kept canonical, out
  of scope, or future specialization.
- Keep the DTO migration ledger complete enough that implementation work
  packages do not invent DTO ownership or deletion timing.

Out of scope:
- Production code changes by default.
- Broad inline `TODO(...)` insertion across source files.
- Moving or deleting DTOs.
- Changing runtime behavior.

Implementation notes:
- Use [Pipeline Stage Protocols And DTOs](../pipeline-stage-protocols-and-dtos.md)
  for current executable DTO behavior. This file is read-only for WP-00B.
- Use [Pipeline DTO Migration Ledger](../pipeline-dto-migration-ledger.md) as
  the canonical classification output.
- Use a three-pass audit workflow:
  1. AST inventory as the authoritative coverage source.
  2. code-index MCP as a symbol/import cross-check and targeted inspection aid.
  3. graphify as architecture/dependency triage for review priority.
- Prefer updating the ledger, target directory tree, and work-package scopes
  over adding source comments.
- Add inline source TODOs only for high-risk misplaced symbols that are likely
  to be misused before migration. Each inline TODO must name the owning work
  package and removal condition, for example:
  `TODO(pipeline-refactor/WP-08): Replace ArrayHandle with TransientPayloadRef after payload resolver lands.`

Inventory fields:
- `symbol`
- `file`
- `line`
- `bases`
- `module_owner`
- `package_category`
- `public_or_private`
- `current_role`
- `target_action`
- `target_owner`
- `owning_wp`
- `ledger_status`
- `deletion_gate_or_keep_reason`

AST inventory guidance:
- Parse every `src/prml_vslam/**/*.py` file with Python `ast`.
- Collect every class definition whose direct bases include one of:
  `BaseData`, `BaseConfig`, `TransportModel`, `BaseModel`, `Protocol`,
  `StrEnum`, `Enum`, or `IntEnum`.
- Resolve imported base names from `ImportFrom` and `Import` nodes where
  possible, including aliases.
- Include subscripted bases such as `FactoryConfig[...]` by inspecting the
  subscript value.
- Include target runtime/proxy/manager symbols named in
  [Target Directory Tree](../pipeline-refactor-target-dir-tree.md) even when
  they are plain classes rather than DTO/config/protocol bases.
- Treat the AST inventory as authoritative. A missing code-index or graphify
  hit must not remove a symbol from the audit.

code-index MCP guidance:
- Set the project path to `/home/jandu/repos/prml-vslam`.
- Build the deep index before requesting file summaries:
  `mcp__code_index__.build_deep_index`.
- Use `search_code_advanced` for broad class-pattern searches with pagination.
- Use `get_file_summary` for DTO-heavy files to capture class names, imports,
  and public boundary hints.
- Use `get_symbol_body` for ambiguous ownership cases where class bases,
  docstrings, or fields decide whether a symbol is canonical, migration-only,
  or out of scope.
- Use code-index results as a validation layer over the AST inventory, not as
  the coverage source.

graphify guidance:
- Follow the repo-local graphify workflow before final classification.
- Read `graphify-out/GRAPH_REPORT.md` for graph scale and community structure.
- Use graphify to prioritize files with broad architecture impact, especially
  hubs around `pipeline`, `interfaces`, `methods`, `benchmark`, `eval`, `app`,
  and `visualization`.
- Graphify communities and inferred edges guide review order and risk, but do
  not define inventory completeness.

Minimum high-risk files to review with code-index summaries:
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

Classification guidance:
- `pipeline/contracts/*`: likely migration, provenance, event, snapshot,
  transport, or request DTOs.
- `interfaces/*`: keep only if semantics are truly shared across packages.
- `methods/*`: method-owned backend configs, backend protocols, and live SLAM
  semantic DTOs.
- `benchmark/*`: baseline/reference policy only; no target stage enablement or
  metric results.
- `eval/*`: metric semantics, metric execution contracts, and persisted
  evaluation artifacts.
- `app/*`: usually out of scope unless it crosses pipeline/public contract
  boundaries.
- `datasets/*` and `io/*`: usually out of scope unless they define source
  contracts or prepared benchmark/reference inputs.
- `visualization/*`: viewer policy and validation DTOs; no stage runtime/Rerun
  SDK leakage into DTOs.
- `reconstruction/*`: reconstruction-owned backend configs, protocols, and
  artifact DTOs.

Reconciliation rule:
- Every AST-audited symbol must appear in
  `pipeline-dto-migration-ledger.md` or in an explicitly named out-of-scope
  list.
- If the target owner is unclear, record the ambiguity in the ledger or the
  package notes instead of guessing.
- Work-package ownership must match the package index and target directory
  tree.

Current-state DTO reference rule:
- `pipeline-stage-protocols-and-dtos.md` remains inspection-only for WP-00B.
- Classify current executable seam classes in
  [Pipeline DTO Migration Ledger](../pipeline-dto-migration-ledger.md) when they
  have migration, ownership, or deletion implications.
- Do not edit the current-state reference in this package; if a later package
  needs to change that file, it must own the path explicitly.

Termination criteria:
- Every class derived from `BaseData`, `BaseConfig`, `TransportModel`, or
  `BaseModel` is classified in the ledger or explicitly marked out of scope.
- Important protocol and enum classes that affect pipeline contracts are
  classified.
- AST inventory count is recorded in the audit notes.
- The minimum high-risk files listed above are reviewed with code-index
  summaries.
- Graphify is used to identify cross-package hubs before final classification.
- Work packages that touch DTO/config/message boundaries link to both the
  current-state DTO reference and the ledger.
- Current executable seam classes with migration, ownership, or deletion
  implications are classified in
  `pipeline-dto-migration-ledger.md`; broader migration-only or out-of-scope
  classes are not dumped into the current-state reference.
- Any inline TODO added by exception includes a work-package id and a concrete
  deletion or migration condition.

Required checks:
- AST inventory over `src/prml_vslam/**/*.py` for `BaseData`, `BaseConfig`,
  `TransportModel`, `BaseModel`, `Protocol`, `StrEnum`, `Enum`, and `IntEnum`
  classes.
- Coverage check proving every audited symbol appears in
  `pipeline-dto-migration-ledger.md` or an explicitly named out-of-scope list.
- code-index MCP deep-index build plus summaries for the minimum high-risk
  files.
- graphify context read from `graphify-out/GRAPH_REPORT.md`.
- `git diff --check`

WP-R:
- Waived for this docs-only inventory audit because no production
  implementation or runtime behavior changed.

Known risks:
- Broad source TODOs can create churn and drift from canonical docs.
- Over-classifying implementation-only helper classes can make the ledger noisy.
- Missing app/dataset/IO DTOs in the out-of-scope section can make future
  agents think those DTOs were forgotten.
- Relying on grep or code-index alone can miss aliased, subscripted, or
  inherited base classes.
- Treating graphify inferred edges as coverage proof can hide unconnected DTOs.
