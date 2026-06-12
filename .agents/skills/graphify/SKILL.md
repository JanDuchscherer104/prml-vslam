---
name: graphify
description: Use when working in a repository with graphify-out/, especially before answering architecture or codebase questions and after code edits that should refresh graphify artifacts.
---

# Graphify

Use this skill in repositories that carry a `graphify-out/` knowledge graph.

## Workflow

1. Before answering architecture or codebase questions, inspect `graphify-out/GRAPH_REPORT.md` to understand god nodes and community structure.
2. If `graphify-out/wiki/index.md` exists, use it as the first navigation surface before reading raw files directly.
3. Use `make graphify` for a concise artifact, runtime, hook, and freshness dashboard.
4. Use `make graphify-report` when you only need the report summary.
5. Use `python3 .agents/scripts/graphify_repo.py mcp` as the repo-local MCP
   startup wrapper; it materializes `graphify-out/graph.json` if the checkout
   only has a Git LFS pointer.
6. Use `make graphify-view` to locate the generated HTML graph viewer.
7. Use `make graphify-hook-status` to check local post-commit/post-checkout hooks without failing the workflow.
8. Use `make graphify-hook-install` once per clone to install the local graph refresh hooks.
9. After modifying code files in a graphify-enabled repository, run `make graphify-rebuild`.

## Notes

- Keep graphify commands repo-relative.
- Do not hardcode local machine paths in graphify instructions or config.
- `graphify-out/graph.json` and `graphify-out/graph.html` are Git LFS-managed
  artifacts in this repo. Treat pointer files as a normal checkout state for
  status/report commands, but materialize `graph.json` before MCP startup.
- If `make graphify-status` reports that the runtime is missing, the existing artifacts can still guide codebase navigation, but rebuilds require the official `graphifyy` package and `graphify` CLI.
