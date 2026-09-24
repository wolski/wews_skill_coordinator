# AGENTS.md

This repository owns Wolski-authored skills and coordinates their installation alongside authoritative third-party skills with the `coord` CLI. A source in `skills.toml` with a `path` is symlinked from a working copy on this machine; a source without one is installed with the pinned `npx skills` CLI. Both kinds land in the same layout, for Claude Code and Codex.

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
- Code lives in `src/wews_skill_coordinator/`, tests in `tests/` mirroring it:
  - `cli.py`: command names, help texts, and argument handling only; the only module that knows commands.
  - `skills/`, `plugins/`, `agent_config/`, `memory/`, `reports/`: independent domains, named after what they handle. `coord install skills` and `coord clean skills` both call `skills/`.
  - `config/`: the `skills.toml` schema, loader, and source checkouts.
  - `disposal.py`: the shared list-ask-remove step (`n` keep, `b` back up, `y` delete).
  - `paths.py`, `console.py`: foundation. Modules read `paths.NAME` at call time so tests can repoint it.
- Imports point one way: `cli` → domains → `config` → `paths` / `console`. Domains never import each other. `memory/store.py` and `reports/bookkeeping.py` import nothing from this repository; `reports/view.py` builds the view the skill scan consumes. `uv run lint-imports` enforces this.
- `reports/bookkeeping.py` and `memory/store.py` never install, move, or delete anything. Removal happens only in `disposal.py`, after listing what will go and asking `n|b|y`; `n` is the default and a dry run never asks.
- Configuration and documentation belong in `skills.toml`, `pyproject.toml`, `README.md`, `AGENTS.md`, and `CLAUDE.md`.

## Workflow

1. `coord install skills` (or `--profile NAME`) resolves a profile in `skills.toml` and installs exactly its skills. It removes nothing and never inspects what else is on disk.
2. A skill that changed installation kind loses its old entry first. Remaining npx packages are installed, then local skills are symlinked into `~/.agents/skills/<name>` with a `~/.claude/skills/<name>` link beside them.
3. `coord clean skills` removes every symlink in `~/.agents/skills` and every npx skill, without reading `skills.toml`. Switching profiles is `coord clean skills && coord install`.
4. `coord update` clones missing source checkouts, fast-forwards each checkout that declares a `git_url`, and updates npx skills.
5. `coord report bookkeeping [ROOT]` scans for every `SKILL.md`, records whether each is a real file, a symlink, or an alias, and who manages it, then writes a CSV, a Markdown report, and an HTML rendering.
6. `coord report memory` reports Claude Code's per-project memory stores the same way, resolving each slug back to a directory. `coord clean memory` offers the stores nothing claims, `coord clean memory all` every store, and `coord clean skills all PATH` every skill folder under PATH; each lists, then asks `n|b|y`. `--dry-run` lists and must write nothing.

Every repository is a `[sources.<name>]` block with `repo = "owner/repository"`. Add `path` to install it from a local checkout, with `owned = true` only when this repository authors the skills (the bookkeeping report treats it as authoritative); without `path` it is installed with npx, and `full_depth = true` passes `--full-depth`. A profile is either a base profile or a composition, never both. A base profile lists skills under the source's name — local skills as `<category>/<name>`, npx skills by name — and every skill belongs to exactly one base profile. A composition's `includes` names base profiles only and is never itself included; `full` includes every base profile with `["*"]`. Add a new skill to the one base profile it belongs to, and a new use case as a composition. Mirror each contributing FGCZ source folder with an independently selectable `fgcz-*` base profile.

## Verification

- Run `uv run pytest` and `uv run lint-imports` after coordinator or profile changes.
- Run `uvx ruff check src tests`.
- Run strict typing with `uv run --with pyright pyright` (strict mode is set in `pyproject.toml`).
- Validate changed skills with the skill creator's `quick_validate.py` and run
  their deterministic evals or smoke tests when present.
- Preview a profile change with `coord install skills --profile NAME --dry-run` before switching; a dry run must write nothing and must report the same actions a real run takes.
