# AGENTS.md

This repository owns Wolski-authored skills and coordinates their installation
alongside authoritative third-party skills. The pinned `npx skills` CLI installs
configured profiles for Claude Code and Codex.

Precedence: the closest `AGENTS.md` wins and applies to its subtree.

## Rules

- Do not edit installed skill files under `~/.agents`, `~/.claude`, or `~/.codex`.
- Edit personal skill source under `skills/<category>/skills/<skill>/`, commit and
  push it here, then run `make update` or switch profiles to reinstall it.
- Treat third-party skill sources as read-only.
- Before adding a personal skill in an FGCZ domain, inspect `fgcz/skills`. Reuse a
  duplicate, contribute missing institutional guidance there, or state a narrow
  non-overlapping responsibility.
- Each skill owns its `SKILL.md`, references, scripts, assets, agents, and evals.
  A skill must not read resources from a sibling skill or category.
- Category folders are organizational source boundaries, not Claude plugins. The
  repository root composes them through `skills.toml`.
- Coordinator behavior belongs in `skill_coordinator.py` and
  `test_skill_coordinator.py`.
- Configuration, command aliases, and documentation belong in `skills.toml`,
  `Makefile`, `README.md`, `AGENTS.md`, and `CLAUDE.md`.

## Workflow

1. `make install` or `make switch PROFILE=...` resolves a profile in `skills.toml`.
2. Selected skills are installed directly with the pinned npx CLI for Claude Code
   and Codex.
3. Configured skills outside the profile are removed only after additions succeed.
4. `make update` delegates installed-skill updates to npx.

Add skills directly to topical profiles as `owner/repository@skill-name`; `full`
includes all profiles automatically. Compose named profiles with `includes`. Add
`[package_options."owner/repository"]` only when the package requires an npx option
such as `full_depth = true`.

## Verification

- Run `make test` after coordinator or profile changes.
- Run `uvx ruff check skill_coordinator.py test_skill_coordinator.py`.
- Run strict typing with `uv run --with cyclopts --with pydantic --with tomli
  --with pytest --with pyright pyright skill_coordinator.py
  test_skill_coordinator.py`.
- Validate changed skills with the skill creator's `quick_validate.py` and run
  their deterministic evals or smoke tests when present.
