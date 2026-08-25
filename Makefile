SHELL := /bin/bash
PY := uv run --with cyclopts --with pydantic --with tomli python skill_coordinator.py
PROFILE ?= full

.PHONY: help update install switch profiles clean list audit plugins plugins-remove plugins-list dry-run test

help: ## Show this help
	@echo "Claude Code Skills Coordinator"
	@echo ""
	@echo "Quick start:  make install"
	@echo "Update:       make update"
	@echo "Switch:       make switch PROFILE=python-design"
	@echo ""
	@$(PY) --help

update: ## Update installed npx skills
	@$(PY) update

install: ## Install PROFILE directly through npx skills
	@$(PY) install --profile "$(PROFILE)"

switch: ## Switch the direct npx installation to PROFILE
	@$(PY) switch --profile "$(PROFILE)"

profiles: ## List configured skill profiles
	@$(PY) profiles

clean: ## Remove configured npx skills
	@$(PY) clean

list: ## Show npx-installed skills and matching profile
	@$(PY) list

audit: ## Report skills with upstream drift
	@$(PY) audit

plugins: ## Install plugins from marketplace
	@$(PY) plugins install-plugins

plugins-remove: ## Uninstall all managed plugins
	@$(PY) plugins remove

plugins-list: ## List installed plugins
	@$(PY) plugins list

dry-run: ## Preview a profile switch without making changes
	@$(PY) switch --profile "$(PROFILE)" --dry-run

test: ## Run test suite
	@uv run --with cyclopts --with pydantic --with tomli --with pytest python -m pytest test_skill_coordinator.py -v
