SHELL := /bin/bash
PY := uv run --with cyclopts --with pydantic --with tomli python skill_coordinator.py

.PHONY: help clone update install clean list status audit plugins plugins-remove plugins-list dry-run test

help: ## Show this help
	@echo "Claude Code Skills Coordinator"
	@echo ""
	@echo "Quick start:  make clone && make install"
	@echo "Update:       make update && make install"
	@echo ""
	@$(PY) --help

clone: ## Clone all upstream repos
	@$(PY) clone

update: ## Pull latest from all repos
	@$(PY) update

install: ## Symlink skills and agents from skills.toml
	@$(PY) install

clean: ## Remove all managed symlinks
	@$(PY) clean

list: ## Show installed skills and agents
	@$(PY) list

status: ## Show git status of each repo
	@$(PY) status

audit: ## Report skills with upstream drift
	@$(PY) audit

plugins: ## Install plugins from marketplace
	@$(PY) plugins install-plugins

plugins-remove: ## Uninstall all managed plugins
	@$(PY) plugins remove

plugins-list: ## List installed plugins
	@$(PY) plugins list

dry-run: ## Preview install without making changes
	@$(PY) install --dry-run

test: ## Run test suite
	@uv run --with cyclopts --with pydantic --with tomli --with pytest python -m pytest test_skill_coordinator.py -v
