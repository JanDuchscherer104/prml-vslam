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
GRAPHIFY_DIR ?= graphify-out
GRAPHIFY_REPORT ?= $(GRAPHIFY_DIR)/GRAPH_REPORT.md
GRAPHIFY_GRAPH ?= $(GRAPHIFY_DIR)/graph.json
GRAPHIFY_HTML ?= $(GRAPHIFY_DIR)/graph.html
GRAPHIFY_PYTHON ?= python3

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

.PHONY: help fmt lint lint-check ci typst-lint typst-check test bib-check report-pdf slides-pdf final-slides docs-build agents-db loc loc-py graphify graphify-status graphify-report graphify-rebuild graphify-view

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

loc-py: ## Print Python LOC for src/ and tests/ (example: make loc LOC_ARGS="--todo --fixme")
	$(UV_RUN) python scripts/loc_stats.py $(LOC_ARGS)

loc: ## Alias for loc-py (pass flags with LOC_ARGS="--todo --fixme")
	$(MAKE) loc-py

graphify: graphify-status graphify-report ## Show graphify status and report summary

graphify-status: ## Check graphify artifacts and Python runtime availability
	@test -d "$(GRAPHIFY_DIR)" || { echo "Missing graphify directory: $(GRAPHIFY_DIR)"; exit 1; }
	@test -f "$(GRAPHIFY_REPORT)" || { echo "Missing graphify report: $(GRAPHIFY_REPORT)"; exit 1; }
	@test -f "$(GRAPHIFY_GRAPH)" || { echo "Missing graphify graph data: $(GRAPHIFY_GRAPH)"; exit 1; }
	@printf "graphify artifacts: %s\n" "$(GRAPHIFY_DIR)"
	@printf "report: %s\n" "$(GRAPHIFY_REPORT)"
	@printf "graph data: %s\n" "$(GRAPHIFY_GRAPH)"
	@test ! -f "$(GRAPHIFY_HTML)" || printf "viewer: %s\n" "$(GRAPHIFY_HTML)"
	@$(GRAPHIFY_PYTHON) -c "import importlib.util; parent = importlib.util.find_spec('graphify'); spec = importlib.util.find_spec('graphify.watch') if parent else None; print('runtime: ' + ('available' if spec else 'missing'))"

graphify-report: ## Print the top of the graphify report
	@test -f "$(GRAPHIFY_REPORT)" || { echo "Missing graphify report: $(GRAPHIFY_REPORT)"; exit 1; }
	@sed -n '1,80p' "$(GRAPHIFY_REPORT)"

graphify-rebuild: ## Rebuild graphify code artifacts for this repository
	@$(GRAPHIFY_PYTHON) -c "import importlib.util, sys; parent = importlib.util.find_spec('graphify'); spec = importlib.util.find_spec('graphify.watch') if parent else None; sys.exit(0 if spec else 1)" || { echo "Missing graphify runtime. Install the package that provides graphify.watch or set GRAPHIFY_PYTHON."; exit 1; }
	$(GRAPHIFY_PYTHON) -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"

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
