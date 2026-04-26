# PRML VSLAM — Claude-Specific Guidance

This file extends `AGENTS.md` with Claude Code-specific instructions.
`AGENTS.md` is still the full repo-wide policy; read it first.

## Library Documentation

Use the MCP library-docs tools when you need up-to-date API or usage
information for a dependency. The Context7 library IDs in
`.agents/references/agent_reference.md` work directly with these tools.

Workflow:
1. Call `mcp__MCP_DOCKER__resolve-library-id` with the library ID from the
   reference file to get the resolved library slug.
2. Call `mcp__MCP_DOCKER__get-library-docs` with that slug and a focused topic
   query.

Example for pydantic settings:
```
resolve-library-id("/pydantic/pydantic-settings")
get-library-docs(<slug>, topic="BaseSettings environment variables")
```

Prefer a narrow topic query over fetching the entire docs page to keep
context cost low.

## Skills

The `.agents/skills/` directory contains reference skill files. Read the
relevant `SKILL.md` when the task falls in that domain:

- **Pydantic** — `.agents/skills/pydantic/SKILL.md`
  Read when writing or reviewing Pydantic models or settings.

- **Agents DB** — `.agents/skills/agents-db/SKILL.md`
  Read when interacting with `.agents/issues.toml`, `.agents/todos.toml`,
  `.agents/resolved.toml`, or `make agents-db`.

- **Simplification** — `.agents/skills/simplification/SKILL.md`
  Read when doing simplification, pruning, redundancy reduction, or
  LOC-reduction work. Pair it with **Agents DB** when the task is backlog-guided.

- **Streamlit architecture** — `.agents/skills/understanding-streamlit-architecture/SKILL.md`
  Read when debugging cross-layer Streamlit issues or planning architectural
  changes to the app.

## Graphify

The global `~/.claude/CLAUDE.md` registers the `/graphify` skill.
Project-specific graphify rules are in `AGENTS.md` under `## graphify`.
