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
5. Use `make graphify-view` to locate the generated HTML graph viewer.
6. Use `make graphify-hook-status` to check local post-commit/post-checkout hooks without failing the workflow.
7. Use `make graphify-hook-install` once per clone to install the local graph refresh hooks.
8. After modifying code files in a graphify-enabled repository, run `make graphify-rebuild`.

## Notes

- Keep graphify commands repo-relative.
- Do not hardcode local machine paths in graphify instructions or config.
- If `make graphify-status` reports that the runtime is missing, the existing artifacts can still guide codebase navigation, but rebuilds require the official `graphifyy` package and `graphify` CLI.
