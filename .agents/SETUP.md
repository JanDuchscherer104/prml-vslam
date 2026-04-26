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
- `uvx code-index-mcp`
- the repo-local skills under `.agents/skills/`

If a server needs credentials, configure them locally and do not commit them to
the repository.
