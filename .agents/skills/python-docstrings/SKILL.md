---
name: python-docstrings
description: Write and refactor concise, contract-focused Python docstrings for modules, public classes, functions, methods, protocols, config models, DTOs, wrappers, and streaming or session APIs. Use when Python docstrings are missing, sparse, misleading, or need better cross-references, examples, units, shapes, lifecycle notes, or boundary semantics.
---

# Python Docstrings

## Overview

Write or refactor Python docstrings as API contracts. Prefer concise,
high-information docstrings that explain behavior, invariants, units, shapes,
ownership, sequencing, and boundary semantics instead of paraphrasing type
hints.

## Workflow

1. Read local rules first. Check repo-local `AGENTS.md`, package `README.md` or
   `REQUIREMENTS.md`, and any local docstring addendum before editing.
2. Identify the public API surface. Cover public modules, public classes,
   public functions, public methods, and meaningful typed fields or properties
   that form an external or cross-module contract.
3. Choose sections deliberately. Default to a summary line plus only the
   sections that add information: `Args:`, `Returns:`, `Yields:`,
   `Attributes:`, `Example:` or `Examples:`, `Notes:` or `Theory:`.
4. Write behavioral contracts. Document semantics, invariants, side effects,
   units, shapes, ownership, lifecycle, and boundary expectations. Do not
   restate obvious type hints.
5. Cross-reference internal symbols with Sphinx roles and link external sources
   with markdown. See [references/cross-references.md](./references/cross-references.md).
6. Add examples when misuse is likely or sequencing matters. See
   [references/examples.md](./references/examples.md).
7. Trim boilerplate. Remove empty sections, duplicated type information, and
   filler prose. Avoid `Raises:` unless callers genuinely need to rely on or
   handle the failure contract.
8. Optionally audit. Run [scripts/audit_docstrings.py](./scripts/audit_docstrings.py)
   to find missing or suspiciously short docstrings before or after a refactor.

## Writing Rules

- Start with a concise summary line that describes behavior, not the symbol
  name.
- Use Google-style sections, but omit sections that do not add information.
- Make module docstrings explain purpose, main contents, and responsibility
  boundaries.
- Make class docstrings explain role and when to use the abstraction.
- Make function and method docstrings explain behavior and semantics, not just
  parameters.
- Use `Attributes:` when instance state is part of the contract.
- Use `Yields:` for generators, iterators, and streaming-style APIs.
- Use `Example:` or `Examples:` for public APIs that are easy to misuse.
- Use `Notes:` or `Theory:` only when they materially help correct usage.
- If the repository carries a local docstring addendum, apply it after the
  general rules in this skill.

## References

- [General style](./references/general-style.md)
- [Cross-references](./references/cross-references.md)
- [Examples](./references/examples.md)
