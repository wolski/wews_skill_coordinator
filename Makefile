SHELL := /bin/bash
SKILLS_DIR := $(HOME)/.claude/skills
REPOS_DIR := $(CURDIR)/repos
CONF := skills.conf

.PHONY: help clone update install clean list status

help: ## Show this help
	@echo "Claude Code Skills Coordinator"
	@echo ""
	@echo "Quick start:  make clone && make install"
	@echo "Update:       make update && make install"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*##"}; {printf "  %-12s %s\n", $$1, $$2}'

clone: ## Clone all upstream repos into repos/ (skip if exists)
	@mkdir -p $(REPOS_DIR)
	@[ -d $(REPOS_DIR)/claude-kaiser-skills ] \
		&& echo "  exists   claude-kaiser-skills" \
		|| (echo "  cloning  claude-kaiser-skills" && git clone --depth 1 https://github.com/wolski/claude-kaiser-skills.git $(REPOS_DIR)/claude-kaiser-skills)
	@[ -d $(REPOS_DIR)/posit-dev-skills ] \
		&& echo "  exists   posit-dev-skills" \
		|| (echo "  cloning  posit-dev-skills" && git clone --depth 1 https://github.com/posit-dev/skills.git $(REPOS_DIR)/posit-dev-skills)
	@[ -d $(REPOS_DIR)/marimo-team-skills ] \
		&& echo "  exists   marimo-team-skills" \
		|| (echo "  cloning  marimo-team-skills" && git clone --depth 1 https://github.com/marimo-team/skills.git $(REPOS_DIR)/marimo-team-skills)
	@[ -d $(REPOS_DIR)/anthropics-skills ] \
		&& echo "  exists   anthropics-skills" \
		|| (echo "  cloning  anthropics-skills" && git clone --depth 1 https://github.com/anthropics/skills.git $(REPOS_DIR)/anthropics-skills)

update: ## Pull latest from all repos
	@for repo in $(REPOS_DIR)/*/; do \
		name=$$(basename "$$repo"); \
		if [ -d "$$repo/.git" ]; then \
			echo "  pulling  $$name"; \
			git -C "$$repo" pull --ff-only 2>/dev/null || \
				echo "  WARNING: pull failed for $$name (check manually)"; \
		fi; \
	done

install: ## Symlink skills from skills.conf into ~/.claude/skills/
	@mkdir -p $(SKILLS_DIR)
	@# Remove existing symlinks that point into our repos dir
	@for link in $(SKILLS_DIR)/*; do \
		if [ -L "$$link" ]; then \
			target=$$(readlink "$$link"); \
			case "$$target" in \
				$(REPOS_DIR)/*) rm "$$link" ;; \
			esac; \
		fi; \
	done
	@# Create symlinks from skills.conf
	@while IFS= read -r line || [ -n "$$line" ]; do \
		line=$$(echo "$$line" | sed 's/#.*//; s/^[[:space:]]*//; s/[[:space:]]*$$//'); \
		[ -z "$$line" ] && continue; \
		repo=$$(echo "$$line" | awk '{print $$1}'); \
		skill_path=$$(echo "$$line" | awk '{print $$2}'); \
		skill_name=$$(basename "$$skill_path"); \
		source="$(REPOS_DIR)/$$repo/$$skill_path"; \
		target="$(SKILLS_DIR)/$$skill_name"; \
		if [ ! -d "$$source" ]; then \
			echo "  MISSING  $$repo/$$skill_path"; \
			continue; \
		fi; \
		if [ -e "$$target" ]; then \
			echo "  CONFLICT $$skill_name (already exists, skipping)"; \
			continue; \
		fi; \
		ln -s "$$source" "$$target"; \
		echo "  linked   $$skill_name -> $$repo/$$skill_path"; \
	done < $(CONF)

clean: ## Remove all managed symlinks from ~/.claude/skills/
	@for link in $(SKILLS_DIR)/*; do \
		if [ -L "$$link" ]; then \
			target=$$(readlink "$$link"); \
			case "$$target" in \
				$(REPOS_DIR)/*) \
					echo "  removed  $$(basename $$link)"; \
					rm "$$link" ;; \
			esac; \
		fi; \
	done

list: ## Show currently installed skills
	@echo "Installed skills in $(SKILLS_DIR):"
	@echo ""
	@for link in $(SKILLS_DIR)/*; do \
		if [ -L "$$link" ]; then \
			name=$$(basename "$$link"); \
			target=$$(readlink "$$link"); \
			case "$$target" in \
				$(REPOS_DIR)/*) \
					rel=$${target#$(REPOS_DIR)/}; \
					echo "  $$name -> $$rel" ;; \
				*) \
					echo "  $$name -> $$target (external)" ;; \
			esac; \
		elif [ -d "$$link" ]; then \
			echo "  $$(basename $$link) (directory, not managed)"; \
		fi; \
	done

status: ## Show git status of each repo
	@for repo in $(REPOS_DIR)/*/; do \
		name=$$(basename "$$repo"); \
		if [ -d "$$repo/.git" ]; then \
			echo "=== $$name ==="; \
			git -C "$$repo" log --oneline -1; \
			echo ""; \
		fi; \
	done
