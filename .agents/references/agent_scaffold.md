# Agent Scaffold Contract

Use this guide when changing repo-local agent instructions, skills, references,
MCP wiring, or generated assistant-support artifacts. Keep it compact: this is
a routing contract, not another policy layer.

## Source Order

1. User request and current task context.
2. Nearest `AGENTS.md` for repo or subtree policy.
3. Human-maintained repo truth such as `README.md`, `SETUP.md`,
   `docs/Questions.md`, package `README.md`, and package `REQUIREMENTS.md`.
4. Task-specific skills under `.agents/skills/`.
5. Lookup references under `.agents/references/`.
6. Derived or advisory systems such as Graphify, MemPalace, code-index, Context7,
   MCP servers, prior chat memory, and generated work notes.

When sources disagree, update the owner surface instead of duplicating a second
definition in a helper file.

## What Belongs Where

- `AGENTS.md`: durable repo policy, source order, safety boundaries, and
  verification expectations.
- Nested `AGENTS.md`: subtree-specific deltas only.
- `.agents/skills/*/SKILL.md`: compact repeatable workflows with activation
  cues, required reads, rules, and verification.
- `.agents/references/*.md`: lookup tables, source maps, upstream contracts,
  and longer distilled guidance that would bloat a skill.
- `.codex/config.toml`: repo-local Codex and MCP wiring that can be portable
  across linked worktrees. Keep machine-local trust and secrets outside the repo.
- `.omx/`: runtime or planning artifacts. Promote only stable decisions back to
  the owning source above.
- `.artifacts/`, `graphify-out/`, MemPalace palaces, and code indexes: derived
  evidence. Refresh or rebuild them; do not treat them as policy.

## Skill Header Pattern

New skills should include a small `metadata:` block when it improves routing:

```yaml
---
name: skill-name
description: One sentence saying when to use the skill.
metadata:
  mode: "implementation | research | review | maintenance | router"
  applies_to:
    - "path/or/glob/**"
  evidence_required:
    - "file, command, artifact, or source required before acting"
  handoff_to:
    - "adjacent-skill-name"
---
```

Do not mass-normalize old skill headers unless a validator or routing failure
shows the change will pay for its review cost.

## Tool And MCP Boundaries

- Use Graphify for architecture orientation and graph freshness checks.
- Use MemPalace for prior-session, durable-decision, and previous-attempt
  lookup.
- Use code-index for broad symbol/file lookup when `rg` is too shallow.
- Use Context7 for current dependency documentation before version-sensitive
  implementation or advice.
- Use MCP tools as discovery and execution channels. Durable decisions still
  land in `AGENTS.md`, skills, references, docs, code, tests, or backlog files.

Repo-local MCP config should prefer repo-relative roots, for example `cwd = "."`
and `--project-path "."`, so linked worktrees do not silently index the primary
checkout.

## External Scaffold Examples

- OpenAI Codex best practices: testing, checks, behavior confirmation, and
  review expectations can live in `AGENTS.md`.
  <https://developers.openai.com/codex/learn/best-practices>
- AGENTS.md format guide: common sections include project overview, build/test
  commands, style, testing, security, and nested instructions.
  <https://agents.md/>
- Claude Code memory: project memory should hold stable facts and route longer
  procedures into task-specific instructions.
  <https://code.claude.com/docs/en/memory>
- GitHub Copilot custom instructions: repository and path-specific instructions
  should describe how to understand, build, test, and validate changes.
  <https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions>
- Cursor/NVIDIA NeMo rule practice: hierarchical, generated, and scoped rules
  reduce drift when the source documentation remains the owner.
  <https://docs.nvidia.com/nemo/agent-toolkit/1.2/extend/cursor-rules-developer-guide.html>
- Public scaffold inventory: `github/awesome-copilot` curates agents,
  instructions, skills, hooks, workflows, plugins, and MCP examples.
  <https://github.com/github/awesome-copilot>
- MCP specification: tools, resources, prompts, and roots are discoverable
  protocol capabilities, not project policy by themselves.
  <https://modelcontextprotocol.io/specification/2025-06-18/>

## Maintenance Checklist

- Keep root and nested `AGENTS.md` concise.
- Link to references instead of copying long lists into skills.
- Prefer one owner for each durable rule.
- Add verification commands to the surface that owns the workflow.
- After scaffold changes, parse TOML/YAML/frontmatter and run a cheap repo
  orientation smoke check such as `make graphify-report`.
