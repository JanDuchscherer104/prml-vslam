# Issue Structure

## Recommended Default Shape

1. `Target`
2. `Current problem`
3. `Required change`
4. `Acceptance criteria`
5. `Test expectations`
6. `Related issues` or linked follow-ups
7. Optional `Change budget`
8. Optional `Expected touch set`
9. Optional `Sources`

## Creation Notes

- Prefer evidence over abstract feature intent.
- Keep acceptance criteria falsifiable.
- Use the repo's issue form or template when it exists and map this structure into that surface.
- If a mirrored backlog exists, include its stable ID in the issue body or metadata.

## Resolution Pattern

1. Re-check the issue body against the current repo state.
2. Restate the acceptance criteria if the issue has drifted or is underspecified.
3. Implement the fix or feature.
4. Verify the explicit test expectations.
5. Link the PR with `Closes #<number>` or a similar closing keyword.
6. Update any mirrored tracker so closure state stays consistent.

## Useful Commands

- `gh issue list --state all`
- `gh issue view <number>`
- `gh issue create --title ... --body-file ...`
- `gh issue edit <number> --title ... --body-file ...`

## Official GitHub Guidance

- Issue forms: <https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms>
- Issue templates: <https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository>
- Issue fields: <https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-and-managing-issue-fields>
- PR and issue linking: <https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue>
