---
name: mempalace-repo
description: Use when working with the repo-local MemPalace setup for PRML VSLAM, especially to refresh or search mined docs and Codex chat histories, inspect palace status, or generate wake-up context from the repo-local palace.
---

# MemPalace Repo

Use this skill when the task is about the repo-local MemPalace setup in this
repository.

## What This Skill Owns

- the repo-local palace at `.artifacts/mempalace/palace`
- the staged docs source tree under `.artifacts/mempalace/sources/docs`
- the staged Codex raw session copies under `.artifacts/mempalace/sources/chats`
- refresh/search workflows through the wrapper script

## Workflow

1. Refresh the staged docs and chat sources, then mine them into the repo-local
   palace:

```bash
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py refresh
```

2. Inspect the current palace state:

```bash
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py status
```

3. Search the mined docs and chat history:

```bash
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py search "your query"
```

4. Generate wake-up context from the repo-local palace:

```bash
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py wake-up
```

5. The repo-local Codex startup hook runs
   `.agents/scripts/mempalace_startup_context.sh`, which refreshes MemPalace in
   the background and prints wake-up context at session start.

6. When a task produces durable context, keep the final-answer debrief concise
   but complete enough for later mining: decisions, files changed, validation,
   blockers, and follow-up facts.

## Guardrails

- Treat the repo-local palace as derived state. Refresh it instead of editing
  mined source trees by hand.
- Prefer repo-scoped raw Codex session JSONLs over the flattened exports for
  conversation mining; MemPalace has a dedicated Codex normalizer for the raw
  session format.
- Keep docs and chat histories in separate wings so searches can be scoped when
  needed.
- Do not assume the global `~/.mempalace` palace is the one this repo uses; the
  wrapper script pins a repo-local palace path.
- Treat `.artifacts/mempalace/` as derived state. Do not hand-edit staged
  sources, logs, or palace index files.
