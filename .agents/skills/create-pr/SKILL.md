---
name: create-pr
description: Create, update, or publish GitHub pull requests with a reviewer-first structure. Use when Codex needs to draft or revise a PR title/body, open a PR from a prepared branch, or reshape an existing PR into a summary paragraph, focused verification list, compact work-package map, and detailed work-package sections instead of a raw changelog.
---

# Create PR

Write PRs that help reviewers understand the change quickly. Keep the body architecture-first: one summary paragraph, explicit verification, a compact work-package overview, then one detailed section per work package.

Use the concrete body pattern in [references/pr-body-shape.md](references/pr-body-shape.md).

## Workflow

1. Ground the branch.
   - Read repo guidance that affects contributor-facing output such as `AGENTS.md`, `CODEOWNERS`, `CONTRIBUTING.md`, and any PR template.
   - Inspect `git status -sb`, `git diff --stat`, and the key diffs against the intended base branch.
   - Separate unrelated local edits before staging or publishing.
2. Define the PR shape.
   - Group the branch into 2-7 work packages.
   - Name packages by boundary, contract, or reviewer concern, not by commit order.
   - Prefer scopes such as `API split`, `CLI plumbing`, `adapter cleanup`, `config migration`, `docs refresh`, `benchmark harness`, `UI scaffolding`, or `CI hardening`.
3. Validate before writing.
   - Run the narrowest formatter, linter, and test commands that match the touched surface.
   - Add focused commands when repo-wide validation is too expensive.
   - If a command could not be run, say so explicitly in the PR body.
4. Write the title.
   - Use a concise sentence describing the branch outcome.
   - Prefer product or contract language over implementation trivia.
   - Keep a prefix such as `[codex]` only when another workflow requires it.
5. Write the body using the default shape in [references/pr-body-shape.md](references/pr-body-shape.md).
6. Choose the execution path.
   - If the branch still needs staging, commit, push, or PR creation, pair this skill with the active publish workflow for the session.
   - If the branch is already published, create or update the PR directly with `gh pr create` or `gh pr edit`.

## CLI Execution Path

Prefer explicit GitHub CLI commands over interactive prompts when writing a structured body.

1. Resolve the base branch.
   - If the user names a base branch, use it.
   - Otherwise check `git config branch.$(git branch --show-current).gh-merge-base`.
   - If no branch-specific merge base is configured, use the remote default branch.
2. Write the PR body to a temporary Markdown file.
   - Use `--body-file` so GitHub receives real newlines and tables intact.
   - Treat `--template` as a starting point only. If the repo has a PR template, merge any required prompts into the structured body instead of replacing the work-package format.
3. Create the PR explicitly:

```bash
gh pr create \
  --draft \
  --base "$BASE" \
  --head "$(git branch --show-current)" \
  --title "$TITLE" \
  --body-file "$BODY_FILE"
```

4. Add metadata only when requested or clearly implied:
   - `--reviewer`
   - `--label`
   - `--milestone`
   - `--project`
   - `--assignee`
5. Update an existing PR with the same structured body:

```bash
gh pr edit <number-or-branch> \
  --title "$TITLE" \
  --body-file "$BODY_FILE"
```

## GitHub CLI Notes

- Prefer explicit `--title` and `--body-file` over `gh pr create --fill`.
- Use `gh pr create --draft` by default unless the user explicitly asks for ready review.
- Do not rely on `gh pr create --dry-run` as a no-side-effect probe; it may still push changes.
- Preserve any `--recover <token>` value or generated body file path if creation fails.
- Use `gh pr create --no-maintainer-edit` only when the user explicitly asks for it.
- Use closing keywords such as `Closes #123` only when the branch actually resolves that issue.

## Body Guidance

- Keep `## Summary` to one paragraph that explains the branch at the product and architecture level.
- Under `Focused verification completed:`, list only commands that actually ran.
- Use `## Work Packages` as a compact reviewer map before the detailed sections.
- Use one `## WPn — ...` section per work package.
- Default subsection order inside each work package:
  - `### Scope`
  - `### Key files`
  - `### Initial success criteria resolution`
- Add `### Symbol mapping` when the branch moves public symbols or renames import surfaces.
- Add `### API/path mapping` when the branch moves config fields, file paths, CLI commands, or external contract names.
- Add `### Remaining follow-ups` only when the branch intentionally leaves work unresolved.
- Keep work-package sections outcome-oriented. Do not narrate every commit.

## Status Language

Prefer exact status labels when they fit the evidence:

- `resolved`
- `mostly resolved`
- `partially resolved`
- `not carried forward intentionally`
- `new scope, baseline resolved`
- `new scope, scaffold resolved`

If the status needs nuance, explain it after the label instead of inventing vague wording.

## Review Lens

- If the branch touches core libraries plus adapters or integrations, state whether the boundary stayed clean.
- If the branch touches examples, demos, or app code, clarify whether the change is local to that surface or reflects a broader contract change.
- If the branch touches tooling, docs, or contributor scaffolding, summarize the durable operator or reviewer impact instead of listing files mechanically.
- Mention determinism, rebuildability, deployment, or local-tooling implications when they materially changed.

## Publish Rules

- Reuse the structured body shape instead of GitHub autofill.
- Default to a draft PR unless the user explicitly asks for ready review.
- Never stage unrelated local changes silently.
- Prefer `gh pr edit` over recreating the PR when only the title or body needs revision.

## Output Requirements

- Never paste raw `git diff` into the PR body.
- Never imply validation that did not happen.
- Prefer architecture and contract language over file-by-file changelog prose.
- Keep the body reviewer-first: summary paragraph, verification list, work-package overview, then detailed sections.
- If CLI creation or edit fails, preserve the body file path or recovery token long enough to retry without retyping the body.
