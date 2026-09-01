# Skills Coordinator

Manages switchable Claude Code and Codex skill profiles declared in `skills.toml`.
Installation is mixed by design:

- Packages declared under `[sources]` are installed from a working copy on this
  machine as **symlinks**. Editing the source is live at once for both agents —
  no commit, push, or reinstall in between.
- Every other package is installed from its GitHub repository with the pinned
  [`skills`](https://github.com/vercel-labs/skills) npx CLI.

Wolski-owned skill source lives in this repository and is therefore a local
source. `fgcz/skills` is a private repository the user commits to, so it is
installed from its `repos/fgcz-skills` checkout rather than fetched. Claude
plugins remain delegated to Claude's plugin manager.

## Quick start

```bash
make clone                           # fetch missing source checkouts
make install                         # install active.profile from skills.toml
make profiles                        # show available profiles
make switch PROFILE=python-design    # activate a smaller profile
make update                          # update npx skills and pull checkouts
```

A switch installs every selected package first. Only after all installs succeed
does it remove configured skills outside the selected profile. Skills not declared
in `skills.toml` are left alone.

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

Profiles are the authoritative skill inventory. A locally sourced entry uses its
exact source-relative directory as
`owner/repository@<category>/skills/<name>`. An npx-installed entry uses the
package's skill selector as `owner/repository@skill-name`.

```toml
active.profile = "python-bfabric"

[sources."wolski/wews_skill_coordinator"]
path = "skills"
owned = true

[sources."fgcz/skills"]
path = "repos/fgcz-skills"
git_url = "https://github.com/fgcz/skills.git"

[package_options."pproenca/dot-skills"]
full_depth = true

[profiles.python-design]
description = "Wolski's Python style and bounded design guidance, plus public Clean Architecture."
skills = [
    "wolski/wews_skill_coordinator@software-engineering/skills/python-style-guide",
    "wolski/wews_skill_coordinator@software-engineering/skills/design-principles",
    "wolski/wews_skill_coordinator@software-engineering/skills/polymorphism-over-discrimination",
    "pproenca/dot-skills@clean-architecture",
]

[profiles.fgcz-communication]
description = "FGCZ communication and requirements-elaboration workflows."
skills = [
    "fgcz/skills@communication/skills/interview-to-spec",
]

[profiles.python]
description = "Broad Python engineering toolkit."
includes = ["python-design", "marimo"]
skills = ["google-deepmind/science-skills@uv"]

[profiles.full]
description = "Every configured skill profile."
includes = ["*"]
```

`active.profile` explicitly selects the profile used by `make install`,
`make switch`, and `make dry-run` when `PROFILE` is not supplied. An explicit
`PROFILE=name` overrides it for that invocation; `make list` reports a warning
when the installed skills do not match the configured active profile.

Every profile has a human-readable `description`, shown by `make profiles`.
The coordinator groups npx entries from the same package into one command. The
`includes` field composes named profiles, while `includes = ["*"]` composes every
other profile. The `full` profile therefore contains no direct skills. Cleanup
uses the union of every direct profile entry. A skill name may have only one
package owner. The `fgcz-*` profiles mirror the contributing top-level folders
in the FGCZ checkout, so those folder groups are independently selectable and
the broad `fgcz` profile composes them.

### Adding a folder as a source

One `[sources]` block plus profile entries is the whole change:

| field | meaning |
| --- | --- |
| `path` | root of the checkout, relative to this repository |
| `owned` | `true` only for skills this repository owns; the tree must then match `skills.toml` exactly, in both directions |
| `git_url` | optional; enables `make clone` and the pull in `make update` |

Skills are discovered at `<category>/skills/<name>/SKILL.md` under the root. A
local profile entry must repeat that exact relative directory; no basename
lookup or flattened fallback is performed. The frontmatter `name` must equal the
directory name. In an `owned` source anything off that pattern is an error. In a
third-party checkout it is simply not a skill this repository installs, because
such a checkout legitimately carries
far more skills than any profile selects.

A source may be absent — not cloned yet, or on a branch that predates a skill. That
is not a configuration error: `make clone` fetches it, and `make install` reports
each configured skill its checkout does not carry as `MISSING` and exits non-zero.
`[package_options]` applies to npx behavior only and may not name a source.

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
working copies you commit from. It reports their state instead: `make list` prints
each source's branch, short HEAD, and how far behind its upstream it is, so a
checkout parked on a feature branch is visible rather than silent. What is
installed is whatever that branch currently holds.

`make update` fast-forwards each source that declares a `git_url` and warns
instead of failing when a pull does not apply, so one dirty checkout cannot block
the rest.

## Commands

```text
make clone           Clone missing source checkouts declared with a git_url
make install         Install active.profile (or the PROFILE override)
make switch          Switch to active.profile (or the PROFILE override)
make profiles        List configured profiles
make update          Update npx skills and fast-forward source checkouts
make clean           Remove configured npx skills and every coordinator symlink
make list            Show configured active profile and installed profile match
make audit           Compare installed skill content with review records
make dry-run         Preview a profile switch
make test            Run the test suite
make plugins         Install configured Claude plugins
make plugins-remove  Uninstall configured Claude plugins
make plugins-list    List installed Claude plugins
```

`make audit` compares npx skills against the folder hash in the npx lock file and
local skills against the last commit touching the skill directory in its own
repository, both against `last_reviewed_sha:` in `.kairos/knowledge/`.

The Makefile delegates to the typed Cyclopts CLI in `skill_coordinator.py`. The
npx version is pinned there so installation behavior does not silently change.

## Bookkeeping

The `bookkeeping` command inventories every `SKILL.md` under a folder and says
how each one is held and who manages it. It only reads.

```bash
make bookkeeping                                   # scans ~/projects
make bookkeeping SCAN_ROOT=~/work BOOK_OUT=/tmp/x  # any folder, any destination
python skill_coordinator.py bookkeeping ~/work --out /tmp/x --no-html
```

It writes three files from one scan: `<BOOK_OUT>.csv` with a row per file for
filtering, `<BOOK_OUT>.md` grouped by verdict, and `<BOOK_OUT>.html` rendered
from that Markdown.

Each row records how the file is held — `real-file`, `symlinked-file`, or
`via-symlinked-dir` — so a copy is never mistaken for a view of a source. Where a
skill exists in several places, the scan picks the authoritative copy (owned
source first, then a source checkout) and measures the others against it.

Symlinked directories are not descended into. One pointing at the home directory
or at an ancestor of the scan root is named in the report rather than followed,
and a file that cannot be read is listed as unread rather than counted as absent.

## Claude memory

`make memory` inventories Claude Code's per-project memory under
`~/.claude/projects/<slug>/memory/` and says which stores can go.

```bash
make memory                     # report only
make memory-prune DRY_RUN=1     # show what would be deleted
make memory-prune               # delete it
```

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
