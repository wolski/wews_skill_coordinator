# Claude Code Skills Coordinator

Manages Claude Code skills, agents, and plugins from multiple upstream repos. Skills are cloned into `repos/` (gitignored) and symlinked into `~/.claude/skills/`, agents into `~/.claude/agents/`, and skills are also mirrored to `~/.codex/skills/`.

## Quick start

```bash
make clone    # Clone all upstream repos
make install  # Symlink skills and agents
make plugins  # Install Claude Code plugins
```

## Updating

```bash
make update   # git pull all repos
make install  # Re-create symlinks (picks up new skills)
```

## Managing skills

Edit `skills.toml` to add or remove entries, then re-run `make install`.

```toml
[repos]
posit-dev-skills = "https://github.com/posit-dev/skills.git"

[skills.posit-dev-skills]
paths = ["r-lib/testing-r-packages"]

[skills.claude-kaiser-skills]
paths = ["r-development", "python-style-guide"]
agents = ["agents/dry-audit.md"]
```

## Upstream repos

| Local name | Source | Contents |
|-----------|--------|----------|
| `claude-kaiser-skills` | [wolski/claude-kaiser-skills](https://github.com/wolski/claude-kaiser-skills) | Custom skills for proteomics, R, Python, Snakemake; custom agents |
| `posit-dev-skills` | [posit-dev/skills](https://github.com/posit-dev/skills) | R package development, testing, cli, lifecycle |
| `marimo-team-skills` | [marimo-team/skills](https://github.com/marimo-team/skills) | Marimo notebook authoring, batch, migration |
| `anthropics-skills` | [anthropics/skills](https://github.com/anthropics/skills) | Skill creator workbench |
| `fgcz-skills` | [fgcz/skills](https://github.com/fgcz/skills) | FGCZ infrastructure, B-Fabric, bioinformatics |

## Plugins

Plugins are managed via `claude plugin install`, not symlinks:

- code-simplifier
- claude-md-management
- code-review
- hookify

```bash
make plugins         # Install all
make plugins-remove  # Uninstall all
make plugins-list    # Show installed
```

## All targets

```
make help            Show available targets
make clone           Clone repos (skip existing)
make update          Pull latest from all repos
make install         Symlink skills and agents
make clean           Remove all managed symlinks
make list            Show what's currently installed
make status          Show git status of each repo
make audit           Report skills with upstream drift
make dry-run         Preview install without making changes
make test            Run test suite
make plugins         Install plugins from marketplace
make plugins-remove  Uninstall all managed plugins
make plugins-list    List installed plugins
```

## Implementation

The Makefile delegates to `skill_coordinator.py` (Python CLI using cyclopts). All configuration — repos, plugins, skills, and agents — lives in `skills.toml` (loaded via Pydantic).
