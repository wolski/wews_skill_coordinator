# Claude Code Skills Coordinator

Manages Claude Code skills from multiple upstream repos via a single Makefile. Skills are cloned into `repos/` (gitignored) and symlinked into `~/.claude/skills/`.

## Quick start

```bash
make clone    # Clone all upstream repos
make install  # Symlink selected skills into ~/.claude/skills/
```

## Updating

```bash
make update   # git pull all repos
make install  # Re-create symlinks (picks up new skills)
```

## Managing skills

Edit `skills.conf` to add or remove skills, then re-run `make install`.

Format: one skill per line — `repo-name  path/to/skill`

```
# Example
posit-dev-skills    r-lib/testing-r-packages
marimo-team-skills  skills/marimo-notebook
```

## Upstream repos

| Local name | Source | Contents |
|-----------|--------|----------|
| `claude-kaiser-skills` | [wolski/claude-kaiser-skills](https://github.com/wolski/claude-kaiser-skills) | Custom skills for proteomics, R, Python, Snakemake |
| `posit-dev-skills` | [posit-dev/skills](https://github.com/posit-dev/skills) | R package development, testing, cli, lifecycle |
| `marimo-team-skills` | [marimo-team/skills](https://github.com/marimo-team/skills) | Marimo notebook authoring, batch, migration |
| `anthropics-skills` | [anthropics/skills](https://github.com/anthropics/skills) | Skill creator workbench |

## All targets

```
make help     # Show available targets
make clone    # Clone repos (skip existing)
make update   # Pull latest from all repos
make install  # Symlink skills into ~/.claude/skills/
make clean    # Remove all managed symlinks
make list     # Show what's currently installed
make status   # Show git status of each repo
```
