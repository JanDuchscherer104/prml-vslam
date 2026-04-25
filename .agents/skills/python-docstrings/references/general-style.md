# General Style

## Quick Rules

- Treat docstrings as API contracts, not filler.
- Prefer short summary lines followed by dense explanation.
- Document behavior, invariants, side effects, units, shapes, ownership, and
  lifecycle expectations.
- Do not paraphrase obvious type hints.
- Avoid `Raises:` by default. Add it only when the failure behavior is part of
  the caller-facing contract.

## Section Selection

Use only the sections that add information:

- Module docstrings:
  - explain purpose
  - explain main contents
  - explain responsibility boundaries
- Function and method docstrings:
  - use `Args:` and `Returns:` when the call contract is non-trivial
  - use `Yields:` for generators, iterators, or streaming APIs
  - add `Example:` or `Examples:` when sequencing or setup is easy to misuse
- Class docstrings:
  - explain the abstraction's role and when to use it
  - use `Attributes:` when instance state is part of the public contract
- Configs and datamodels:
  - explain what each meaningful field changes or represents
  - call out units, ranges, defaults, and persistence semantics when they
    matter
- Use `Notes:` or `Theory:` only when they materially help the caller use the
  API correctly

## Summary-Line Rules

- Keep the first line short and concrete.
- Describe what the symbol does, not what it is called.
- Prefer present tense and direct phrasing.

Good:

- `Normalize native outputs into :class:\`SlamArtifacts\`.`
- `Translate one :class:\`SlamUpdate\` into explicit backend events.`

Weak:

- `This function normalizes outputs.`
- `Class for handling backend events.`

## What To Document

Prioritize the information a caller cannot recover from the signature alone:

- invariants and preconditions
- coordinate frames, units, and shapes
- ownership and mutation semantics
- persistence or artifact boundaries
- sequencing expectations
- what is normalized versus what remains upstream-native

## What To Avoid

- repeating the function name in prose
- converting every type hint into a sentence
- adding every possible section mechanically
- inserting long theory blocks for simple helpers
- adding examples that do not teach anything
