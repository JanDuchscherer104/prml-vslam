## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current

## Library Documentation

Use the MCP library-docs tools when you need up-to-date API or usage
information for a dependency. The Context7 library IDs in
`.agents/references/agent_reference.md` work directly with these tools.

Workflow:
1. Call `mcp_MCP_DOCKER_resolve-library-id` with the library ID from the
   reference file to get the resolved library slug.
2. Call `mcp_MCP_DOCKER_get-library-docs` with that slug and a focused topic
   query.

Example for pydantic settings:
```
resolve-library-id("/pydantic/pydantic-settings")
get-library-docs(<slug>, topic="BaseSettings environment variables")
```

Prefer a narrow topic query over fetching the entire docs page to keep
context cost low.

## Skills

Gemini CLI has auto-discovered local skills from the `.agents/skills/` directory.
Call the `activate_skill` tool when your task falls into any of these domains:

- **Pydantic** (`activate_skill("pydantic")`)
  Activate when writing or reviewing Pydantic models or settings.

- **Agents DB and simplification** (`activate_skill("agents-db-and-simplification")`)
  Activate when interacting with `.agents/issues.toml`, `.agents/todos.toml`,
  `.agents/resolved.toml`, `make agents-db`, or when doing simplification,
  pruning, or LOC-reduction work.

- **Streamlit architecture** (`activate_skill("understanding-streamlit-architecture")`)
  Activate when debugging cross-layer Streamlit issues or planning architectural
  changes to the app.
