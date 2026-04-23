.DEFAULT_GOAL := help

CPU_COUNT ?= $(shell getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.logicalcpu 2>/dev/null || nproc 2>/dev/null || python3 -c 'import os; print(os.cpu_count() or 1)' 2>/dev/null || echo 1)
UV_RUN ?= uv run
RUFF ?= $(UV_RUN) ruff
PRE_COMMIT ?= $(UV_RUN) --extra dev pre-commit run --all-files --show-diff-on-failure
TYPST ?= typst
TYPSTYLE ?= typstyle
PYTEST ?= $(UV_RUN) --extra dev pytest
PYTEST_WORKERS ?= auto
PYTEST_ARGS ?= -n $(PYTEST_WORKERS)
PARALLEL_MAKE ?= $(MAKE) -j$(CPU_COUNT)
AGENTS_DB ?= $(UV_RUN) python .agents/scripts/agents_db.py
AGENTS_ARGS ?= rank
LOC_ARGS ?=
MEMPALACE ?= python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py
MEMPALACE_QUERY ?=
GRAPHIFY_DIR ?= graphify-out
GRAPHIFY_REPORT ?= $(GRAPHIFY_DIR)/GRAPH_REPORT.md
GRAPHIFY_GRAPH ?= $(GRAPHIFY_DIR)/graph.json
GRAPHIFY_HTML ?= $(GRAPHIFY_DIR)/graph.html
GRAPHIFY_PYTHON ?= $(UV_RUN) --preview-features extra-build-dependencies --group dev python
GRAPHIFY_CLI ?= $(UV_RUN) --preview-features extra-build-dependencies --group dev graphify

BIB_FILE ?= docs/references.bib
BIB_CACHE_DIR ?= .cache/bib
BIB_REBIBER_OUTPUT ?= $(BIB_CACHE_DIR)/references.rebiber.bib
BIB_REBIBER_LOG ?= $(BIB_CACHE_DIR)/rebiber.log
BIB_UPDATE_OUTPUT ?= $(BIB_CACHE_DIR)/references.updated.bib
BIB_CHECK_REPORT ?= $(BIB_CACHE_DIR)/check-report.json
BIB_UPDATE_REPORT ?= $(BIB_CACHE_DIR)/update-report.jsonl
BIB_FIELD_REPORT ?= $(BIB_CACHE_DIR)/field-report.json
BIB_FACT_CACHE ?= $(BIB_CACHE_DIR)/fact-cache.db
BIB_UPDATER_CACHE ?= $(BIB_CACHE_DIR)/updater-cache.db
BIB_RESOLUTION_CACHE ?= $(BIB_CACHE_DIR)/resolution-cache.db
BIB_ARTIFACTS ?= $(BIB_REBIBER_OUTPUT) $(BIB_REBIBER_LOG) $(BIB_UPDATE_OUTPUT) $(BIB_CHECK_REPORT) $(BIB_UPDATE_REPORT) $(BIB_FIELD_REPORT) $(BIB_FACT_CACHE) $(BIB_UPDATER_CACHE) $(BIB_RESOLUTION_CACHE)
BIB_TIMEOUT ?= 240
BIB_WORKERS ?= $(CPU_COUNT)

TYPST_ROOT ?= $(abspath .)
TYPST_COMPILE ?= $(TYPST) compile --root $(TYPST_ROOT)
REPORT_TYP ?= docs/report/main.typ
REPORT_PDF ?= docs/report/build/report.pdf
UPDATE_SLIDES_TYP ?= docs/slides/update-meetings/update-slides.typ
UPDATE_SLIDES_PDF ?= docs/slides/build/update-meetings.pdf
FINAL_TYP ?= docs/slides/final/main.typ
FINAL_PDF ?= docs/slides/build/final.pdf

.PHONY: help fmt lint lint-check ci typst-lint typst-check test bib-check report-pdf slides-pdf final-slides docs-build agents-db loc loc-py open3d-stubs mempalace mempalace-refresh mempalace-status mempalace-search mempalace-wake-up graphify graphify-status graphify-report graphify-rebuild graphify-hook-status graphify-hook-install graphify-view

lint: ## Auto-format Python files and apply Ruff fixes
	$(RUFF) format .
	$(RUFF) check . --fix

lint-check: ## Run non-mutating Ruff format and lint checks
	$(RUFF) format --check .
	$(RUFF) check .

ci: ## Run the local CI verification suite
	$(PRE_COMMIT)
	$(PARALLEL_MAKE) test report-pdf slides-pdf

typst-lint: ## Run non-mutating Typst formatting checks
	$(TYPSTYLE) --check $(REPORT_TYP) $(UPDATE_SLIDES_TYP)

typst-check: ## Lint and compile the report and update slides
	$(PARALLEL_MAKE) typst-lint report-pdf slides-pdf

test: ## Run the Python test suite (for parallel runs: make test PYTEST_ARGS="-n auto")
	$(PYTEST) $(PYTEST_ARGS)

agents-db: ## Run the local .agents backlog tool (example: make agents-db AGENTS_ARGS="rank --kind todos")
	$(AGENTS_DB) $(AGENTS_ARGS)

mempalace: mempalace-status ## Show repo-local MemPalace status

mempalace-refresh: ## Refresh repo-local MemPalace docs and Codex chat histories
	$(MEMPALACE) refresh

mempalace-status: ## Show repo-local MemPalace status
	$(MEMPALACE) status

mempalace-search: ## Search repo-local MemPalace (example: make mempalace-search MEMPALACE_QUERY="pipeline DTO")
	@test -n "$(MEMPALACE_QUERY)" || { echo "Set MEMPALACE_QUERY"; exit 1; }
	$(MEMPALACE) search "$(MEMPALACE_QUERY)"

mempalace-wake-up: ## Print repo-local MemPalace wake-up context
	$(MEMPALACE) wake-up

loc-py: ## Print Python LOC for src/ and tests/ (example: make loc LOC_ARGS="--todo --fixme")
	$(UV_RUN) python scripts/loc_stats.py $(LOC_ARGS)

loc: ## Alias for loc-py (pass flags with LOC_ARGS="--todo --fixme")
	$(MAKE) loc-py

open3d-stubs: ## Regenerate repo-local Open3D .pyi files
	$(UV_RUN) --extra dev python scripts/generate_open3d_stubs.py

graphify: graphify-status ## Show a concise graphify dashboard

graphify-status: ## Check graphify artifacts and Python runtime availability
	@test -d "$(GRAPHIFY_DIR)" || { echo "Missing graphify directory: $(GRAPHIFY_DIR)"; exit 1; }
	@test -f "$(GRAPHIFY_REPORT)" || { echo "Missing graphify report: $(GRAPHIFY_REPORT)"; exit 1; }
	@test -f "$(GRAPHIFY_GRAPH)" || { echo "Missing graphify graph data: $(GRAPHIFY_GRAPH)"; exit 1; }
	@printf "graphify artifacts: %s\n" "$(GRAPHIFY_DIR)"
	@printf "report: %s\n" "$(GRAPHIFY_REPORT)"
	@printf "graph data: %s\n" "$(GRAPHIFY_GRAPH)"
	@test ! -f "$(GRAPHIFY_HTML)" || printf "viewer: %s\n" "$(GRAPHIFY_HTML)"
	@$(GRAPHIFY_PYTHON) -c 'from importlib.metadata import version; print("runtime: available (graphifyy " + version("graphifyy") + ")")'
	@$(GRAPHIFY_PYTHON) -c 'import json, re; from pathlib import Path; report = Path("$(GRAPHIFY_REPORT)").read_text(encoding="utf-8"); graph = json.loads(Path("$(GRAPHIFY_GRAPH)").read_text(encoding="utf-8")); date = re.search(r"^# Graph Report - .*\(([^)]*)\)", report, re.M); summary = re.search(r"^- (\d+) nodes .+? (\d+) edges .+? (\d+) communities detected", report, re.M); nodes = graph.get("nodes", []); links = graph.get("links", graph.get("edges", [])); print("graph date: " + (date.group(1) if date else "unknown")); print("nodes: " + (summary.group(1) if summary else str(len(nodes)))); print("links: " + (summary.group(2) if summary else str(len(links)))); print("communities: " + (summary.group(3) if summary else "unknown"))'
	@if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then dirty=$$(git status --short -- "$(GRAPHIFY_REPORT)" "$(GRAPHIFY_GRAPH)" "$(GRAPHIFY_HTML)"); if [ -n "$$dirty" ]; then echo "artifact dirty state: modified"; else echo "artifact dirty state: clean"; fi; fi
	@printf "next: make graphify-report | make graphify-rebuild | make graphify-hook-install\n"

graphify-report: ## Print the top of the graphify report
	@test -f "$(GRAPHIFY_REPORT)" || { echo "Missing graphify report: $(GRAPHIFY_REPORT)"; exit 1; }
	@$(GRAPHIFY_PYTHON) -c 'import re; from pathlib import Path; report = Path("$(GRAPHIFY_REPORT)").read_text(encoding="utf-8"); print(report.splitlines()[0]); wanted = ("Corpus Check", "Summary", "Suggested Questions"); [print("\n## " + name + "\n" + match.group(1).strip()) for name in wanted for match in [re.search(r"^## " + re.escape(name) + r"\n(.*?)(?=^## |\Z)", report, re.M | re.S)] if match]'

graphify-rebuild: ## Rebuild graphify code artifacts for this repository
	$(GRAPHIFY_CLI) update .

graphify-hook-status: ## Show local graphify git hook status without failing
	@$(GRAPHIFY_CLI) hook status || true

graphify-hook-install: ## Install local graphify post-commit/post-checkout hooks
	$(GRAPHIFY_CLI) hook install

graphify-view: ## Print the graphify HTML viewer path
	@test -f "$(GRAPHIFY_HTML)" || { echo "Missing graphify viewer: $(GRAPHIFY_HTML)"; exit 1; }
	@printf "%s\n" "$(GRAPHIFY_HTML)"

bib-check: ## Run strict source-backed bibliography verification
	mkdir -p $(BIB_CACHE_DIR)
	rm -f $(BIB_ARTIFACTS)
	timeout $(BIB_TIMEOUT) $(UV_RUN) rebiber -i $(BIB_FILE) -o $(BIB_REBIBER_OUTPUT) -d True -st True > $(BIB_REBIBER_LOG) 2>&1
	TMPDIR=$(abspath $(BIB_CACHE_DIR)) timeout $(BIB_TIMEOUT) $(UV_RUN) bibtex-update $(BIB_FILE) -o $(BIB_UPDATE_OUTPUT) --dry-run --check-fields --field-fill-mode recommended --skip-preprint-upgrade --max-workers $(BIB_WORKERS) --cache $(BIB_UPDATER_CACHE) --resolution-cache $(BIB_RESOLUTION_CACHE) --report $(BIB_UPDATE_REPORT) --field-report $(BIB_FIELD_REPORT)
	TMPDIR=$(abspath $(BIB_CACHE_DIR)) timeout $(BIB_TIMEOUT) $(UV_RUN) bibtex-check $(BIB_FILE) --strict --workers $(BIB_WORKERS) --cache-file $(BIB_FACT_CACHE) --report $(BIB_CHECK_REPORT)

report-pdf: ## Compile the Typst report PDF
	mkdir -p $(dir $(REPORT_PDF))
	$(TYPST_COMPILE) $(REPORT_TYP) $(REPORT_PDF)

slides-pdf: ## Compile the unified update-meeting slide deck
	test -f "$(UPDATE_SLIDES_TYP)" || { echo "Missing slide deck: $(UPDATE_SLIDES_TYP)"; exit 1; }
	mkdir -p $(dir $(UPDATE_SLIDES_PDF))
	$(TYPST_COMPILE) $(UPDATE_SLIDES_TYP) $(UPDATE_SLIDES_PDF)

final-slides: ## Compile the final presentation slides
	mkdir -p $(dir $(FINAL_PDF))
	$(TYPST_COMPILE) $(FINAL_TYP) $(FINAL_PDF)

docs-build: ## Build the report, meeting slides, and final slides
	$(PARALLEL_MAKE) report-pdf slides-pdf final-slides

help: ## Show this help message
	@echo "Usage: make <target>"
	@awk 'BEGIN {FS = ":.*?## "}; /^[a-zA-Z0-9_.-]+:.*?## / {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
