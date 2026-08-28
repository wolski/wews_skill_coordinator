# AGENTS.md

This repository owns Wolski-authored skills and coordinates their installation
alongside authoritative third-party skills. Packages declared under `[sources]`
in `skills.toml` are symlinked from a working copy on this machine; every other
package is installed with the pinned `npx skills` CLI. Both kinds land in the
same layout, for Claude Code and Codex.

Precedence: the closest `AGENTS.md` wins and applies to its subtree.

## Rules

- Do not edit installed skill files under `~/.agents`, `~/.claude`, or `~/.codex`.
  For a local source those paths are symlinks into a checkout, so editing them
  edits the source by accident and outside version control.
- Edit personal skill source under `skills/<category>/skills/<skill>/`. It is
  symlinked, so the change is live at once; commit and push it here as usual.
- Treat third-party skill sources as read-only, except `repos/fgcz-skills`, which
  is a checkout the user commits to. Never switch, reset, or clean a source
  checkout on the user's behalf.
- Before adding a personal skill in an FGCZ domain, inspect `fgcz/skills`. Reuse a
  duplicate, contribute missing institutional guidance there, or state a narrow
  non-overlapping responsibility.
- Each skill owns its `SKILL.md`, references, scripts, assets, agents, and evals.
  A skill must not read resources from a sibling skill or category.
- Category folders are organizational source boundaries, not Claude plugins. The
  repository root composes them through `skills.toml`.
- Coordinator behavior, and every CLI command, belongs in `skill_coordinator.py`
  and `test_skill_coordinator.py`. The read-only inventory scan belongs in
  `skill_bookkeeping.py` and `test_skill_bookkeeping.py`; it never installs,
  moves, or deletes anything.
- `skill_coordinator` imports `skill_bookkeeping`, never the reverse. The
  coordinator owns `skills.toml` and the CLI, so it builds the `Coordinator`
  view the scan consumes; the scan imports nothing from this repository.
- Configuration, command aliases, and documentation belong in `skills.toml`,
  `Makefile`, `README.md`, `AGENTS.md`, and `CLAUDE.md`.

## Workflow

1. `make install` or `make switch PROFILE=...` resolves a profile in `skills.toml`.
2. A skill that changed installation kind loses its old entry first. Remaining
   npx packages are installed, then local skills are symlinked into
   `~/.agents/skills/<name>` with a `~/.claude/skills/<name>` link beside them.
3. Configured skills outside the profile are removed only after additions succeed:
   npx names through the CLI, local names by unlinking.
4. `make clone` fetches missing source checkouts; `make update` updates npx skills
   and fast-forwards each checkout that declares a `git_url`.
5. `make bookkeeping`, or `skill_coordinator.py bookkeeping ROOT`, scans for every
   `SKILL.md`, records whether each is a real file, a symlink, or an alias, and
   who manages it, then writes a CSV, a Markdown report, and an HTML rendering.

Add skills directly to topical profiles as `owner/repository@skill-name`; `full`
includes all profiles automatically. Compose named profiles with `includes`. Add
`[package_options."owner/repository"]` only when an npx-installed package requires
an option such as `full_depth = true`; it may not name a source. Add
`[sources."owner/repository"]` to install a package from a local checkout, with
`owned = true` only when this repository owns the skills.

## Verification

- Run `make test` after coordinator or profile changes.
- Run `uvx ruff check` over every module changed, and `make test` covers both
  test files.
- Run strict typing with `uv run --with cyclopts --with pydantic --with tomli
  --with pytest --with markdown --with pyright pyright <changed modules>`.
- Validate changed skills with the skill creator's `quick_validate.py` and run
  their deterministic evals or smoke tests when present.
- Preview a profile change with `make dry-run PROFILE=...` before switching; a
  dry run must write nothing and must report the same actions a real run takes.
