# Skills Coordinator

Manages switchable Claude Code and Codex skill profiles declared in `skills.toml`.
Installation is mixed by design:

- A source with a `path` is installed from a working copy on this machine as **symlinks**. Editing the source is live at once for both agents — no commit, push, or reinstall in between.
- A source without a `path` is installed from its GitHub repository with the pinned [`skills`](https://github.com/vercel-labs/skills) npx CLI.

Wolski-owned skill source lives in this repository and is therefore a local
source. `fgcz/skills` is a private repository the user commits to, so it is
installed from its `repos/fgcz-skills` checkout rather than fetched. Claude
plugins remain delegated to Claude's plugin manager.

## Quick start

`coord` is this repository's command-line tool. Install it once as an editable tool, so it runs from any directory and always acts on this checkout:

```bash
uv tool install --editable .
coord update                                  # clone missing checkouts, pull the others, update npx skills
coord install                                 # active profile's skills, plugins, and agent config links
coord list profiles                           # show available profiles
coord clean skills && coord install skills --profile python-design  # switch profiles
```

Every group and command explains itself with `--help`, and every command that changes something takes `--dry-run`.

`coord install` only adds: it installs the profile's skills and removes nothing. `coord clean skills` removes every installed skill without reading `skills.toml`. Switching profiles is therefore `coord clean skills && coord install`.

## Install layout

Both install kinds produce the same layout, which is the one npx already uses:

```text
~/.agents/skills/<skill>     shared store, read directly by Codex
                             npx: a real directory
                             local source: a symlink into this machine's checkout
~/.claude/skills/<skill>  ->  ../../.agents/skills/<skill>
```

Nothing is written to `~/.codex/skills`; the npx CLI classifies Codex as a
universal agent that reads the shared store. Coordinator-installed entries are
identified structurally — a symlink in the store that resolves inside a
configured source root — so no extra state file is kept and
`~/.agents/.skill-lock.json` stays npx-owned. An entry that is not
coordinator-managed is reported as `CONFLICT` and never overwritten.

## Configuration

Every repository gets a short name under `[sources]`. Profiles come in two kinds, so a profile's skills are never more than one lookup away:

- **Base profile:** concrete skills, listed under their source's short name — a local skill as `<category>/<name>`, an npx skill by its name. Every skill has exactly one base profile.
- **Composition:** `includes` naming base profiles only. A composition is never included by another profile; `full` includes every base profile with `["*"]`.

```toml
active = "python-bfabric"

[sources.wews]
repo = "wolski/wews_skill_coordinator"
path = "skills"
owned = true

[sources.fgcz]
repo = "fgcz/skills"
path = "repos/fgcz-skills"
git_url = "https://github.com/fgcz/skills.git"

[sources.deepmind]            # no path: installed with npx
repo = "google-deepmind/science-skills"

[profiles.full]
description = "Every configured skill profile."
includes = ["*"]

[profiles.python]
description = "Python design and workflow tooling."
includes = ["python-design", "workflow"]

[profiles.workflow]
description = "Pipelines and environments."
wews = ["workflow-development/snakemake-compact"]
deepmind = ["uv"]

[profiles.python-design]
description = "Wolski's bounded Python design guidance."
wews = [
    "software-engineering/design-principles",
    "software-engineering/polymorphism-over-discrimination",
]

[profiles.fgcz-communication]
description = "FGCZ communication and requirements-elaboration workflows."
fgcz = ["communication/interview-to-spec"]
```

`active` selects the profile `coord install` installs. `coord install skills --profile NAME` installs another one without changing `active`; `coord list skills` warns when the installed skills do not match `active`.

Every profile has a human-readable `description`, shown by `coord list profiles` in two tables, compositions and base profiles. A base-profile key other than `description` must name a source, so a misspelled key is an error rather than an ignored line; a profile with both `includes` and skills is an error too.
The coordinator groups npx entries from the same package into one command. A skill name may have only one source. The `fgcz-*` base profiles mirror the contributing top-level folders in the FGCZ checkout, so those folder groups are independently selectable and the `fgcz` composition combines them.

### Adding a source

One `[sources.<name>]` block plus profile entries is the whole change:

| field | meaning |
| --- | --- |
| `repo` | `owner/repository`; for an npx source this is what npx installs |
| `path` | local sources only: root of the checkout, relative to this repository |
| `owned` | local sources only: `true` for skills this repository authors; the bookkeeping report treats that checkout as the authoritative copy |
| `git_url` | local sources only, optional; lets `coord update` clone and pull it |
| `full_depth` | npx sources only: pass `--full-depth` to npx |

A source no profile uses is an error.

A local profile entry `<category>/<name>` names the directory `<category>/skills/<name>` under the source root, which must hold a `SKILL.md`; no basename lookup is performed. Nothing else in the checkout is looked at: a skill on disk that `skills.toml` does not name, or names only in a comment, is simply not installed.

A source may be absent — not cloned yet, or on a branch that predates a skill. That
is not a configuration error: `coord update` clones it, and `coord install` reports
each configured skill its checkout does not carry as `MISSING` and exits non-zero.

## Owned skill source

Personal skills use the following source layout:

```text
skills/<category>/skills/<skill>/
├── SKILL.md
├── references/   # when needed
├── scripts/      # when needed
├── assets/       # when needed
└── evals/        # when maintained by the skill
```

Category folders organize source; they are not Claude plugin packages and contain
no plugin manifests. A skill owns its resources and must not read files from a
sibling skill. The repository root composes the categories through `skills.toml`.

Before adding a personal skill in an FGCZ domain, inspect `fgcz/skills`. Reuse a
duplicate there, contribute missing institutional behavior upstream, or define a
clearly non-overlapping personal responsibility. Do not keep two broad owners for
the same workflow.

## Source checkouts

The coordinator never switches, resets, or cleans a source checkout — those are
working copies you commit from. It reports their state instead: `coord list skills` prints
each source's branch, short HEAD, and how far behind its upstream it is, so a
checkout parked on a feature branch is visible rather than silent. What is
installed is whatever that branch currently holds.

`coord update` fast-forwards each source that declares a `git_url` and warns
instead of failing when a pull does not apply, so one dirty checkout cannot block
the rest.

## Commands

```text
coord install                 skills, plugins, and agent config links
coord install skills          a profile's skills, adding only (--profile NAME, default: active)
coord install plugins         the Claude plugins in skills.toml
coord install config          link ~/.agents/AGENTS.md and the output styles from agent-config/
coord clean                   prints its commands; removes nothing by itself
coord clean skills            every installed skill; does not read skills.toml
coord clean skills all PATH   every folder holding a SKILL.md under PATH (default .), after asking
coord clean plugins           uninstall the Claude plugins in skills.toml
coord clean memory            memory stores no project claims, after asking
coord clean memory all        every memory store, after asking
coord list                    skills, profiles, and plugins
coord list skills             local sources, installed skills, the matching profile
coord list profiles           every profile with size, includes, and description
coord list plugins            installed Claude plugins
coord update                  clone missing checkouts, pull the others, update npx skills
coord report                  all three reports below
coord report audit            skills whose content changed since review
coord report bookkeeping      every SKILL.md under ~/projects
coord report memory           Claude's per-project memory store
```

`coord report audit` compares npx skills against the folder hash in the npx lock file and local skills against the last commit touching the skill directory in its own repository, both against `last_reviewed_sha:` in `.kairos/knowledge/`.

The npx version is pinned in `src/wews_skill_coordinator/skills/npx.py` so installation behavior does not silently change.

## Development

```bash
uv sync               # dev environment
uv run pytest         # tests
uv run lint-imports   # import contracts
uvx ruff check src tests
uv run --with pyright pyright
```

`cli.py` is the only module that knows command names. It composes independent domains — `skills/`, `plugins/`, `agent_config/`, `memory/`, `reports/` — which build on `config/` and the foundation modules `paths.py` and `console.py`. The import-linter contracts in `pyproject.toml` enforce that direction.

## Bookkeeping

The `bookkeeping` command inventories every `SKILL.md` under a folder and says
how each one is held and who manages it. It only reads.

```bash
coord report bookkeeping                            # scans ~/projects
coord report bookkeeping ~/work --out /tmp/x        # any folder, any destination
coord report bookkeeping ~/work --out /tmp/x --no-html
```

It writes three files from one scan: `<out>.csv` with a row per file for filtering, `<out>.md` grouped by verdict, and `<out>.html` rendered from that Markdown.

Each row records how the file is held — `real-file`, `symlinked-file`, or
`via-symlinked-dir` — so a copy is never mistaken for a view of a source. Where a
skill exists in several places, the scan picks the authoritative copy (owned
source first, then a source checkout) and measures the others against it.

Symlinked directories are not descended into. One pointing at the home directory
or at an ancestor of the scan root is named in the report rather than followed,
and a file that cannot be read is listed as unread rather than counted as absent.

## Claude memory

`coord report memory` inventories Claude Code's per-project memory under `~/.claude/projects/<slug>/memory/` and says which stores can go.

```bash
coord report memory             # report only
coord clean memory --dry-run    # list the stores no project claims
coord clean memory              # list them, then ask
coord clean memory all          # every store, then ask
```

## Removing things after asking

`coord clean skills all PATH`, `coord clean memory` and `coord clean memory all` list what they found, then ask once:

- `n` (or Enter): keep everything
- `b`: move it to a backup folder — `~/.coord_trash` is suggested, Enter accepts it — under a timestamped subfolder that keeps each item's relative path
- `y`: delete it

`--dry-run` lists without asking. A symlinked skill folder loses only its link, never the source it points at. `skills all` skips `.git`, `.venv`, `node_modules`, and PATH itself — run inside a checkout, it offers that checkout's own skills too.

A store's slug is the project's absolute path with every separator flattened to
`-`, which swallows any `_`, `.` or `-` already in the name. It cannot be
inverted by substitution, so each slug is resolved against the filesystem by
search: `-Users-wolski-projects-wews-skill-coordinator` finds
`/Users/wolski/projects/wews_skill_coordinator`.

A slug that resolves nowhere means one of two things, and they are not the same.
The project may be **deleted**, or merely **moved** — so the leaf name is looked
for elsewhere first, skipping dot-directories and caches. Only a store with no
resolution and no relocation candidate is called removable, and only those are
ever deleted. Everything else is reported and kept.

The scan also flags facts absent from `MEMORY.md` (nothing will recall them),
`[[links]]` and index entries pointing at missing files, empty stores, and
anything untouched past `--stale-days` (default 90).
