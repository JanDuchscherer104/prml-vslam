.DEFAULT_GOAL := help

# Color codes
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m

# Tooling
TYPST ?= typst

# Bibliography
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
BIB_TIMEOUT ?= 240

# Documentation
TYPST_ROOT ?= $(abspath .)
REPORT_TYP ?= docs/report/main.typ
REPORT_PDF ?= docs/report/build/report.pdf
UPDATE_SLIDES_TYP ?= docs/slides/update-meetings/update-slides.typ
UPDATE_SLIDES_PDF ?= docs/slides/build/update-meetings.pdf
FINAL_TYP ?= docs/slides/final/main.typ
FINAL_PDF ?= docs/slides/build/final.pdf

.PHONY: help fmt lint test bib-check bib-check-strict report-pdf slides-pdf final-slides docs-build

#  ═══════════════════════════════════════════════════════════════════════
#  🔧 Quality
#  ═══════════════════════════════════════════════════════════════════════

fmt: ## Auto-format Python files and apply Ruff fixes
	uv run ruff format .
	uv run ruff check . --fix

lint: ## Run non-mutating Ruff format and lint checks
	uv run ruff format --check .
	uv run ruff check .

test: ## Run the Python test suite
	uv run pytest

#  ═══════════════════════════════════════════════════════════════════════
#  📚 Bibliography
#  ═══════════════════════════════════════════════════════════════════════

bib-check: ## Run non-destructive bibliography normalization and field audits
	mkdir -p $(BIB_CACHE_DIR)
	rm -f $(BIB_REBIBER_OUTPUT) $(BIB_REBIBER_LOG) $(BIB_UPDATE_OUTPUT) $(BIB_CHECK_REPORT) $(BIB_UPDATE_REPORT) $(BIB_FIELD_REPORT) $(BIB_FACT_CACHE) $(BIB_UPDATER_CACHE) $(BIB_RESOLUTION_CACHE)
	timeout $(BIB_TIMEOUT) uv run rebiber -i $(BIB_FILE) -o $(BIB_REBIBER_OUTPUT) -d True -st True > $(BIB_REBIBER_LOG) 2>&1
	TMPDIR=$(abspath $(BIB_CACHE_DIR)) timeout $(BIB_TIMEOUT) uv run bibtex-update $(BIB_FILE) -o $(BIB_UPDATE_OUTPUT) --dry-run --check-fields --field-fill-mode recommended --skip-preprint-upgrade --max-workers 1 --cache $(BIB_UPDATER_CACHE) --resolution-cache $(BIB_RESOLUTION_CACHE) --report $(BIB_UPDATE_REPORT) --field-report $(BIB_FIELD_REPORT)

bib-check-strict: bib-check ## Run strict source-backed bibliography verification
	TMPDIR=$(abspath $(BIB_CACHE_DIR)) timeout $(BIB_TIMEOUT) uv run bibtex-check $(BIB_FILE) --strict --workers 1 --cache-file $(BIB_FACT_CACHE) --report $(BIB_CHECK_REPORT)

#  ═══════════════════════════════════════════════════════════════════════
#  📄 Docs
#  ═══════════════════════════════════════════════════════════════════════

report-pdf: ## Compile the Typst report PDF
	mkdir -p $(dir $(REPORT_PDF))
	$(TYPST) compile --root $(TYPST_ROOT) $(REPORT_TYP) $(REPORT_PDF)

slides-pdf: ## Compile the unified update-meeting slide deck
	@if [ ! -f "$(UPDATE_SLIDES_TYP)" ]; then \
		echo "$(RED)Missing slide deck: $(UPDATE_SLIDES_TYP)$(NC)"; \
		exit 1; \
	fi
	mkdir -p $(dir $(UPDATE_SLIDES_PDF))
	$(TYPST) compile --root $(TYPST_ROOT) $(UPDATE_SLIDES_TYP) $(UPDATE_SLIDES_PDF)

final-slides: ## Compile the final presentation slides
	mkdir -p $(dir $(FINAL_PDF))
	$(TYPST) compile --root $(TYPST_ROOT) $(FINAL_TYP) $(FINAL_PDF)

docs-build: report-pdf slides-pdf final-slides ## Build the report, meeting slides, and final slides

#  ═══════════════════════════════════════════════════════════════════════
#  ℹ️  Help
#  ═══════════════════════════════════════════════════════════════════════

help: ## Show this help message
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)             PRML VSLAM - Makefile Commands                $(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)Usage:$(NC) make <target>"
	@echo "$(YELLOW)Docs:$(NC)  make slides-pdf"
	@awk 'BEGIN {FS = ":.*?## "; section=""} \
		/^#  ═+$$/ {next} \
		/^#  [🔧📚📄ℹ️]/ {if (section) print ""; section=$$0; gsub(/^#  /, "", section); print "$(YELLOW)" section "$(NC)"; next} \
		/^[a-zA-Z0-9_.-]+:.*?## / {printf "  $(BLUE)%-18s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
