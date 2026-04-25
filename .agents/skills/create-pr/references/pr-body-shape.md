# PR Body Shape

Model the body after the structured pattern used in `prml-vslam` PR #51: short architecture summary, explicit verification, compact work-package map, then one detailed section per work package.

## Default Section Order

1. `## Summary`
2. `Focused verification completed:`
3. `## Work Packages`
4. `## WPn — ...`

## Skeleton

```md
## Summary
<one paragraph describing what changed and why it matters>

Focused verification completed:
- `pytest tests/test_api.py -q`
- `ruff check src tests`
- `npm test -- --runInBand`

## Work Packages
| WP | Scope | Primary surfaces | Status |
| --- | --- | --- | --- |
| WP1 | API split | `src/api`, `tests/test_api.py` | resolved |
| WP2 | CLI plumbing | `src/cli`, `docs/cli.md` | mostly resolved |

## WP1 — API Split
### Scope
- <what changed>

### Key files
- `src/api/contracts.py`
- `tests/test_api.py`

### Initial success criteria resolution
- `public API moved without duplicate owners`: `resolved`
- `legacy import kept temporarily`: `partially resolved`
```

## Notes

- Keep `Summary` to one paragraph.
- Keep `Focused verification completed:` limited to real commands that ran.
- Prefer 2-7 work packages.
- Use `### Symbol mapping` when public symbols move.
- Use `### API/path mapping` when config fields, file paths, or CLI commands move.
- Use `### Remaining follow-ups` only when intentionally unresolved work remains.
- Good status language includes `resolved`, `mostly resolved`, `partially resolved`, `not carried forward intentionally`, `new scope, baseline resolved`, and `new scope, scaffold resolved`.
