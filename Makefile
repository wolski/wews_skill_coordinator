SHELL := /bin/bash
PY := uv run --with cyclopts --with pydantic --with tomli --with markdown python skill_coordinator.py
PROFILE ?= full
SCAN_ROOT ?= $(HOME)/projects
BOOK_OUT ?= TODO/skill_bookkeeping

.PHONY: help clone update install switch profiles clean list audit bookkeeping plugins plugins-remove plugins-list dry-run test

help: ## Show this help
	@echo "Claude Code Skills Coordinator"
	@echo ""
	@echo "Quick start:  make clone && make install"
	@echo "Update:       make update"
	@echo "Switch:       make switch PROFILE=python-design"
	@echo ""
	@echo "Targets:"
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN{FS=":.*?## "}{printf "  %-16s %s\n", $$1, $$2}'
	@echo ""
	@echo "Variables:"
	@echo "  PROFILE          profile for install/switch/dry-run (now: $(PROFILE))"
	@echo "  SCAN_ROOT        folder bookkeeping scans (now: $(SCAN_ROOT))"
	@echo "  BOOK_OUT         bookkeeping output prefix (now: $(BOOK_OUT))"
	@echo ""
	@$(PY) --help

clone: ## Clone missing source checkouts declared with a git_url
	@$(PY) clone

update: ## Update npx skills and fast-forward every source checkout
	@$(PY) update

install: ## Install PROFILE from npx packages and local checkouts
	@$(PY) install --profile "$(PROFILE)"

switch: ## Switch the installation to PROFILE
	@$(PY) switch --profile "$(PROFILE)"

profiles: ## List configured skill profiles
	@$(PY) profiles

clean: ## Remove configured npx skills and every coordinator symlink
	@$(PY) clean

list: ## Show source checkouts, installed skills by kind, and matching profile
	@$(PY) list

audit: ## Report skills whose content changed since review
	@$(PY) audit

bookkeeping: ## Scan SCAN_ROOT for SKILL.md files; write CSV, Markdown, and HTML
	@$(PY) bookkeeping "$(SCAN_ROOT)" --out "$(BOOK_OUT)"

plugins: ## Install plugins from marketplace
	@$(PY) plugins install-plugins

plugins-remove: ## Uninstall all managed plugins
	@$(PY) plugins remove

plugins-list: ## List installed plugins
	@$(PY) plugins list

dry-run: ## Preview a profile switch without making changes
	@$(PY) switch --profile "$(PROFILE)" --dry-run

test: ## Run test suite
	@uv run --with cyclopts --with pydantic --with tomli --with pytest --with markdown \
		python -m pytest test_skill_coordinator.py test_skill_bookkeeping.py -v
