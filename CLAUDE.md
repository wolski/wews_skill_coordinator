# CLAUDE.md

This is a **coordinator repo** — it manages symlinks to skills from multiple upstream repositories. It does NOT contain skill files directly.

## Rules

- **DO NOT edit skill files in this repo** — they live in `repos/` which is gitignored
- **To edit custom skills**: `cd repos/claude-kaiser-skills`, make changes, commit and push there
- **Upstream skills are read-only** — update them with `make update`
- **Only edit**: `Makefile`, `skills.conf`, `README.md`, `CLAUDE.md`, `.gitignore`

## How it works

1. `make clone` clones upstream repos into `repos/`
2. `make install` reads `skills.conf` and creates symlinks in `~/.claude/skills/`
3. `make update` pulls latest from all repos
4. `make clean` removes managed symlinks

## Adding a new skill source

1. Add the repo URL to `Makefile` (REPO_URL_xxx variable and REPOS list)
2. Add skill entries to `skills.conf`
3. Run `make clone && make install`
