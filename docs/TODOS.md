# Bootstrap TODOs

The bootstrap TODOs from project kickoff are resolved in the current repository scaffold.

## Completed

- [x] Initialized Typst templates for the report and update meetings:
  - report entry point: `docs/report/main.typ`
  - update meeting decks: `docs/slides/update-meetings/meeting-01` to `meeting-05`
  - final presentation deck: `docs/slides/final/main.typ`
- [ ] Ensure that the slides and paper can be compiled without any issues.
- [x] Chose a meeting-first slide architecture with shared partials and contributor-owned fragments to minimize merge conflicts.
- [x] Set up a `uv`-managed Python environment and documented the minimal setup flow in the README.
- [x] Added an installable `prml_vslam` package with an editable install path and CLI entry point.
- [x] Created an overview of work packages for issue planning in `docs/workpackages.md`.
- [x] Added CI scaffolding for `ruff` and `pytest`, plus a minimal `CODEOWNERS` file.
- [x] Added a minimal root `AGENTS.md` after the repo structure was stabilized.

## Locked-In Decisions

- Python is pinned to `3.11`.
- The package layout uses `src/prml_vslam/`.
- Heavy external VSLAM tools stay outside the base `uv` environment and are documented as external integrations.
- Slides are organized by meeting, with a unified `update-slides.typ` entrypoint and contributor-owned
  `<name>.typ` files inside each `meeting-0X` directory.
