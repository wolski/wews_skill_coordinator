# Skills Coordinator

Manages switchable Claude Code and Codex skill profiles declared in `skills.toml`.
Every skill is installed directly from its GitHub repository with the pinned
[`skills`](https://github.com/vercel-labs/skills) npx CLI. There is no coordinator
skill cache and no coordinator-owned skill symlink layer.

Wolski-owned skill source lives in this repository. Third-party skills remain at
their authoritative upstream repositories. Claude plugins remain delegated to
Claude's plugin manager.

## Quick start

```bash
make install                         # install the full profile
make profiles                        # show available profiles
make switch PROFILE=python-design    # activate a smaller profile
make update                          # update npx skills
```

A switch installs every selected package first. Only after all installs succeed
does it remove configured skills outside the selected profile. Skills not declared
in `skills.toml` are left alone.

## Configuration

Profiles are the authoritative skill inventory. Each entry combines its GitHub
package and exact npx skill name as `owner/repository@skill`.

```toml
[package_options."wolski/wews_skill_coordinator"]
full_depth = true

[profiles.python-design]
description = "Wolski's Python style and bounded design guidance, plus public Clean Architecture."
skills = [
    "wolski/wews_skill_coordinator@python-style-guide",
    "wolski/wews_skill_coordinator@design-principles",
    "wolski/wews_skill_coordinator@polymorphism-over-discrimination",
    "pproenca/dot-skills@clean-architecture",
]

[profiles.python-design-public]
description = "Public Python design-pattern and Clean Architecture guidance, without Wolski skills."
skills = [
    "wshobson/agents@python-design-patterns",
    "pproenca/dot-skills@clean-architecture",
]

[profiles.python]
description = "Broad Python engineering toolkit."
includes = ["python-design", "marimo"]
skills = ["google-deepmind/science-skills@uv"]

[profiles.full]
description = "Every configured skill profile."
includes = ["*"]
```

Every profile has a human-readable `description`, shown by `make profiles`.
The coordinator groups entries from the same package into one npx command. The
`includes` field composes named profiles, while `includes = ["*"]` composes every
other profile. The `full` profile therefore contains no direct skills. Cleanup
uses the union of every direct profile entry. A package-options entry is needed
only for npx behavior such as `--full-depth`, not for skill membership. A skill
name may have only one package owner.

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

## Commands

```text
make install         Install PROFILE (default: full)
make switch          Switch the direct npx installation to PROFILE
make profiles        List configured profiles
make update          Update global npx skills
make clean           Remove only configured skills
make list            List installed skills and matching profile
make audit           Compare installed skill hashes with review records
make dry-run         Preview a profile switch
make test            Run the test suite
make plugins         Install configured Claude plugins
make plugins-remove  Uninstall configured Claude plugins
make plugins-list    List installed Claude plugins
```

The Makefile delegates to the typed Cyclopts CLI in `skill_coordinator.py`. The
npx version is pinned there so installation behavior does not silently change.
