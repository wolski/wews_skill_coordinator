SHELL := /bin/bash
PY := uv run --with cyclopts --with pydantic --with tomli python skill_coordinator.py
PROFILE ?= full

.PHONY: help clone update install switch profiles clean list audit plugins plugins-remove plugins-list dry-run test

help: ## Show this help
	@echo "Claude Code Skills Coordinator"
	@echo ""
	@echo "Quick start:  make clone && make install"
	@echo "Update:       make update"
	@echo "Switch:       make switch PROFILE=python-design"
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
