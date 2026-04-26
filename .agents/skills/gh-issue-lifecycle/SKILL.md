---
name: gh-issue-lifecycle
description: Create, de-duplicate, structure, sync, and resolve GitHub issues. Use when Codex needs to open a new GitHub issue, rewrite a vague issue into a template-backed body with acceptance criteria, mirror issues between GitHub and another backlog, or close the loop from issue to linked pull request.
---

# GitHub Issue Lifecycle

Use this skill to keep GitHub issues specific, falsifiable, and easy to resolve. Follow the default issue-body shape in [references/issue-structure.md](references/issue-structure.md) unless the repository already has an issue form or template that should take precedence.

## Create Issues

1. Read the existing issue list and any mirrored local backlog before creating anything.
2. De-duplicate by number, slug, title, labels, or mirrored external IDs.
3. Use the repo's issue form or template when it exists. If there is no template, use the default section shape from [references/issue-structure.md](references/issue-structure.md).
4. Prefer concrete evidence over abstract intent. Good issues describe the current broken or missing behavior first.
5. Keep acceptance criteria falsifiable. If it is not clear how to tell whether the work is done, the issue is underspecified.
6. Include linked follow-ups, related issues, or mirrored backlog IDs when they already exist.

## Structure Issues Well

- Separate the current problem from the requested change.
- State tests explicitly instead of assuming them.
- Bound risky work with optional `Change budget` or `Expected touch set` sections.
- Use checklists sparingly. A checklist is not a substitute for a clear problem statement and acceptance criteria.
- If the issue is exploratory, say what uncertainty should be reduced and what evidence would count as a useful outcome.

## Resolve Issues

1. Start from the GitHub issue plus any mirrored tracker entry.
2. Restate the acceptance criteria in your own words before coding when the issue is old, vague, or likely to have drifted.
3. Leave a short status note when coordination matters, especially if work is happening in a local checkout or separate worktree.
4. Implement the change and run the relevant validation.
5. Link the resolving PR with `Closes #<number>` or another valid closing keyword when the issue is actually satisfied.
6. Update any mirrored local backlog or tracker so closure state stays consistent.
7. Leave a short closing note or PR summary that maps the final change back to the issue's acceptance criteria.

## Sync GitHub And Another Backlog

- Keep mirrored IDs stable even if the GitHub issue number changes between repositories.
- GitHub is the collaborative surface. A local planner, TODO file, or external tracker can remain the durable planning surface when the repo uses one.
- Record enough metadata to reconnect the two systems later: issue number, title, state, and mirrored local ID.

## Templates And Commands

- `gh issue list --repo <owner>/<repo> --state all`
- `gh issue view <number> --repo <owner>/<repo>`
- `gh issue create --repo <owner>/<repo> --title ... --body-file ...`
- `gh issue edit <number> --title ... --body-file ...`

Read [references/issue-structure.md](references/issue-structure.md) when you need the default body shape, resolution pattern, or official GitHub guidance links.
