# MemPalace - PRML VSLAM Codex Plugin

This repo uses the MemPalace Codex plugin in a repo-local MCP-only shape.
The plugin manifest points at the repo `.venv` and the repo-local palace at
`.artifacts/mempalace/palace`.

## Prerequisites

- Python 3.9+
- Codex CLI installed and configured
- MemPalace installed in the repo `.venv`

## Installation

## Repo-Local Workflow

Refresh and mine the repo-local docs plus Codex chat histories:

```bash
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py refresh
```

Inspect or search the repo-local palace:

```bash
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py status
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py search "ViewCoordinates.RDF"
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py wake-up
```

Show the MCP command shape that this repo uses:

```bash
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py mcp
```

The repo-local skill that owns this workflow lives at:

- `.agents/skills/mempalace-repo/SKILL.md`

## Support

- Repository: https://github.com/MemPalace/mempalace
- Issues: https://github.com/MemPalace/mempalace/issues
