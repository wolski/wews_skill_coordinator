# coord CLI

> Status: implemented 2026-09-24; 163 tests, strict pyright, ruff, import-linter all pass; `coord install skills --dry-run` identical to the Makefile baseline.
>
> Replace the Makefile with a hierarchical `coord` command, split `skill_coordinator.py` by domain, and simplify `skills.toml`.

## Requirements

Why: the Makefile is a flat list of 17 targets wrapping one 1,100-line script, and `skills.toml` repeats the full source in every skill line. Wanted: a proper Python CLI with hierarchical commands and a config that reads at a glance.

In scope:
- `coord` command, callable from any directory
- Groups: `install`, `clean`, `list`, `update`, `report`
- A help text on every group and subcommand (`coord install --help`)
- Domain split of `skill_coordinator.py` — behaviour and architecture in one change
- New `skills.toml` layout; stays TOML at the repo root

Out of scope:
- JSON config — TOML keeps comments
- Compatibility with the old `skills.toml` format — converted once
- Changes to what gets installed

Done when:
- `coord --help` and every `coord <group> --help` print useful text
- Every profile resolves to the same skill set as before the conversion
- `coord install --dry-run` reports the same actions as today's `make dry-run`
- Makefile deleted; README uses `coord`
- Tests and the import-linter contract pass

## Design

### Command tree

- `coord install`: everything — skills, plugins, config links
  - `skills [--profile X]`
  - `plugins`
  - `config`
- `coord clean`: prints subcommands only, removes nothing
  - `skills`
  - `plugins`
  - `memory`
- `coord list`: everything
  - `skills`
  - `profiles`
  - `plugins`
- `coord update`: clones missing checkouts, fast-forwards sources, updates npx skills
- `coord report`: everything
  - `audit`
  - `bookkeeping [--scan-root --out]`
  - `memory [--root --out]`
- `--dry-run` on every command that changes something

Makefile → coord:

| make | coord |
| --- | --- |
| install, switch | install skills [--profile] |
| dry-run | install skills --dry-run |
| clone, update | update |
| clean | clean skills |
| plugins / plugins-remove / plugins-list | install / clean / list plugins |
| config | install config |
| list / profiles | list skills / list profiles |
| audit / bookkeeping / memory | report audit / bookkeeping / memory |
| memory-prune | clean memory |
| test | uv run pytest |

Bare `coord install`: after a fresh clone, one command does everything. Bare `coord clean`: removal is named explicitly.

### Package layout

```
src/wews_skill_coordinator/
├── cli.py                 the coord command; the only file that knows command names
├── paths.py               repo root, ~/.claude/skills, ~/.agents/skills
├── config/
│   └── schema.py          reads and validates skills.toml
├── skills/
│   ├── profiles.py        resolves a profile to its skills
│   ├── npx.py             installs and removes npx skills
│   └── links.py           creates and removes local skill symlinks
├── plugins/
│   └── marketplace.py     installs and removes Claude plugins
├── agent_config/
│   └── links.py           AGENTS.md and output-style symlinks
├── memory/
│   └── store.py           today's claude_memory.py
└── reports/
    ├── audit.py           installed skill content vs review records
    └── bookkeeping.py     today's skill_bookkeeping.py
```

- Folders named after what they handle; `install skills` and `clean skills` both call `skills/`
- Imports one way: `cli` → domains → `config`, `paths`; domains never import each other; import-linter enforces it
- Repo root = `Path(__file__).parents[2]`; install with `uv tool install --editable .` so edits are live
- `list` and `report` print `rich` tables

### skills.toml layout

```toml
active = "python-bfabric-proteomics"

[sources.wews]
repo = "wolski/wews_skill_coordinator"
path = "skills"
owned = true

[sources.fgcz]
repo = "fgcz/skills"
path = "repos/fgcz-skills"
git_url = "https://github.com/fgcz/skills.git"

[sources.deepmind]            # no path = installed via npx
repo = "google-deepmind/science-skills"

[profiles.science]
description = "Scientific Python plus literature and sequence databases."
wews = ["scientific-python/scverse", "scientific-python/plotly"]
deepmind = ["uv", "uniprot-database"]
```

- One `[sources.*]` table: `path` = local symlink, no `path` = npx
- Local skills written `category/name`; the `/skills/` segment is implied
- One `[profiles.*]` table; `includes` unchanged; profile keys other than `description` / `includes` name sources
- File order: `active`, sources, plugins, combined profiles (`python-bfabric-proteomics`, `fgcz`, `full`), then topic profiles

### Set aside

- JSON: no comments; the layout was the readability problem, not the format
- `skills.toml` in `src/`: a non-editable install would freeze a copy; the repo root is needed for `skills/` anyway
- Separate topic-group and profile tables: an extra concept, and `marimo` or `r` could no longer be installed alone
- Packages per command group: `install` and `clean` share the same link and npx logic

### Risks

- Behaviour and architecture change together, so a regression is harder to attribute — mitigated by the baseline capture in step 1
- Unknown profile keys become source lookups; a typo must fail validation, not silently select nothing

## Implementation plan

- [x] 1. Baseline: save the output of `make dry-run`, `make list` and `make profiles`, plus every profile's resolved skill set, to `TODO/coord_baseline/`
- [x] 2. Package skeleton: `src/wews_skill_coordinator/`, `pyproject.toml` with `uv_build` and `[project.scripts] coord = "wews_skill_coordinator.cli:app"`, drop `package = false`, add `import-linter` to the dev group
- [x] 3. `paths.py`, then `config/schema.py` for the new layout; schema rejects profile keys that are neither a source nor `description` / `includes`
- [x] 4. Convert `skills.toml` to the new layout; test that every profile resolves to its baseline skill set
- [x] 5. Split `skill_coordinator.py` into `skills/`, `plugins/`, `agent_config/`; move `claude_memory.py` → `memory/store.py`, `skill_bookkeeping.py` → `reports/bookkeeping.py`, audit → `reports/audit.py`
- [x] 6. `cli.py`: the five groups, bare-group behaviour, `--dry-run`, docstring help, `rich` tables
- [x] 7. Tests to `tests/`, mirroring the package; import-linter contract in `pyproject.toml`
- [x] 8. Delete the Makefile; update the README; `uv tool install --editable .`
- [x] 9. Verify against the baseline: `coord install --dry-run`, `coord list`, `coord list profiles`; `uv run pytest`; `lint-imports`

Files touched:
- `pyproject.toml`, `skills.toml`, `README.md`
- `Makefile` (deleted)
- `skill_coordinator.py`, `claude_memory.py`, `skill_bookkeeping.py` (moved and split)
- `test_*.py` → `tests/`

Tests:
- The current 145 tests move and keep passing, including the pinned real-config counts (72 references)
- New: schema rejects an unknown profile key; old-vs-new profile resolution equality; CLI help smoke test per group

## Differences from the plan

- `reports/audit.py` became `skills/audit.py`: audit reads the installed links, and domains may not import each other
- `config/` holds three modules: `schema.py`, `checkout.py` (source inventories), `load.py`
- Sources are two types, `LocalSource` and `NpxSource`, told apart by `path`; `[package_options]` became `full_depth` on the npx source
- npx list output is parsed into `InstalledSkill` records
- `coord install config` replaces a stale symlink but never a real file (the Makefile's `ln -sf` would have)
- Strict pyright is set in `pyproject.toml`; that surfaced six untyped `default_factory=list` fields in the moved scan modules, now typed

## Decisions on the open questions

- `coord install skills --profile X` does not write `active`; the override stays per-invocation, as before
- `owned = true` exists only on local sources, where it still means the tree must match `skills.toml` exactly
