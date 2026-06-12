# Codex Setup

This repository ships shared Codex defaults in `.codex/config.toml`. Keep
machine-local trust settings, personal connectors, and secrets in
`~/.codex/config.toml`.

## Requirements

- Codex CLI or Codex desktop app
- Docker with MCP Toolkit support
- `uv`

## Bootstrap

Pull or update the shared Docker MCP Toolkit profile:

```bash
docker mcp profile pull docker.io/janduchscherer104/codex:latest
```

Then open this repository in Codex. The repo-local config wires:

- `docker mcp gateway run --profile codex`
- `uvx code-index-mcp --project-path .`
- `python3 .agents/scripts/graphify_repo.py mcp`
- `python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py mcp`
- the repo-local skills under `.agents/skills/`

If a server needs credentials, configure them locally and do not commit them to
the repository.

## MCP Surfaces

- Docker MCP Toolkit exposes shared external tools such as Context7. Use
  `.agents/references/agent_reference.md` for the repo's known Context7 library
  IDs before falling back to broad web search.
- Code Index is the fast local symbol and file discovery surface. The checked-in
  config uses `--project-path .` so linked worktrees point at their own source
  tree.
- Graphify serves `graphify-out/graph.json` through the repo wrapper. Because
  `graphify-out/graph.json` and `graphify-out/graph.html` are Git LFS artifacts,
  the wrapper materializes `graph.json` before MCP startup when the checkout
  only has a pointer file.
- MemPalace serves the repo-local palace through the repo wrapper. The wrapper
  uses the installed `mempalace` and `mempalace-mcp` executables and pins
  `.artifacts/mempalace/palace` instead of the global `~/.mempalace` palace.

## MemPalace Mining Scope

The refresh helper stages two wings:

- `prml-vslam-docs`: root docs, `docs/` markdown/Typst/bibliography/text files,
  package README/REQUIREMENTS/AGENTS files, repo-local agent skills, agent
  references, agents-db TOML state, and checked-in Codex config/hooks.
- `prml-vslam-chats`: raw repo-scoped Codex session JSONL files copied from the
  configured Codex home, plus compact JSONL exports for inspection.

Do not mine `.artifacts/`, `.omx/`, `graphify-out/`, caches, generated binary
outputs, or full source files by default. Those surfaces are derived, runtime
local, or too noisy for durable recall. If a future task needs more memory
coverage, prefer adding compact owner surfaces under `.agents/references/`,
`.agents/skills/`, or the agents DB instead of mining large generated output.

MemPalace init is heuristic-only by default. To use local Ollama refinement
during init, run with:

```bash
MEMPALACE_INIT_LLM=1 \
MEMPALACE_INIT_LLM_PROVIDER=ollama \
MEMPALACE_INIT_LLM_MODEL=gemma4:e4b \
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py refresh
```

External subscription or OpenAI-compatible providers are opt-in only. Set
`MEMPALACE_ACCEPT_EXTERNAL_LLM=1` only after deciding that the staged repo docs
and agent scaffold may be sent to that provider.
