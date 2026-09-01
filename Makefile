SHELL := /bin/bash
PY := uv run --with cyclopts --with pydantic --with tomli --with markdown python skill_coordinator.py
PROFILE ?=
PROFILE_ARG = $(if $(strip $(PROFILE)),--profile "$(PROFILE)",)
SCAN_ROOT ?= $(HOME)/projects
BOOK_OUT ?= TODO/skill_bookkeeping
MEMORY_ROOT ?= $(HOME)/.claude/projects
MEMORY_OUT ?= TODO/claude_memory

.PHONY: help clone update install switch profiles clean list audit bookkeeping memory memory-prune plugins plugins-remove plugins-list dry-run test config

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
	@echo "  PROFILE          optional profile override (now: $(if $(PROFILE),$(PROFILE),skills.toml active.profile))"
	@echo "  SCAN_ROOT        folder bookkeeping scans (now: $(SCAN_ROOT))"
	@echo "  BOOK_OUT         bookkeeping output prefix (now: $(BOOK_OUT))"
	@echo "  MEMORY_ROOT      Claude memory store (now: $(MEMORY_ROOT))"
	@echo "  MEMORY_OUT       memory report prefix (now: $(MEMORY_OUT))"
	@echo "  DRY_RUN          set to preview memory-prune"
	@echo ""
	@$(PY) --help

clone: ## Clone missing source checkouts declared with a git_url
	@$(PY) clone

update: ## Update npx skills and fast-forward every source checkout
	@$(PY) update

install: ## Install PROFILE from npx packages and local checkouts
	@$(PY) install $(PROFILE_ARG)

switch: ## Switch the installation to PROFILE
	@$(PY) switch $(PROFILE_ARG)

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

memory: ## Inventory Claude's memory store; write CSV, Markdown, and HTML
	@$(PY) memory "$(MEMORY_ROOT)" --out "$(MEMORY_OUT)"

memory-prune: ## Delete memory stores nothing claims (DRY_RUN=1 to preview)
	@$(PY) memory "$(MEMORY_ROOT)" --out "$(MEMORY_OUT)" --prune $(if $(DRY_RUN),--dry-run,)

plugins: ## Install plugins from marketplace
	@$(PY) plugins install-plugins

plugins-remove: ## Uninstall all managed plugins
	@$(PY) plugins remove

plugins-list: ## List installed plugins
	@$(PY) plugins list

dry-run: ## Preview a profile switch without making changes
	@$(PY) switch $(PROFILE_ARG) --dry-run

config: ## Symlink global AGENTS.md and output styles from agent-config/
	@mkdir -p $(HOME)/.agents $(HOME)/.claude/output-styles
	@ln -sf $(CURDIR)/agent-config/AGENTS.md $(HOME)/.agents/AGENTS.md
	@ln -sf $(CURDIR)/agent-config/output-styles/answer-first.md $(HOME)/.claude/output-styles/answer-first.md
	@echo "linked ~/.agents/AGENTS.md and ~/.claude/output-styles/answer-first.md"

test: ## Run test suite
	@uv run --with cyclopts --with pydantic --with tomli --with pytest --with markdown \
		python -m pytest test_skill_coordinator.py test_skill_bookkeeping.py \
			test_claude_memory.py -v
