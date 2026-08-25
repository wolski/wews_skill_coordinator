# Skills Coordinator

Manages switchable Claude Code and Codex skill profiles declared in `skills.toml`.
Every skill is installed directly from its GitHub repository with the pinned
[`skills`](https://github.com/vercel-labs/skills) npx CLI. There is no coordinator
skill cache and no coordinator-owned skill symlink layer.

Standalone Claude Code agent definitions remain Git-backed because `npx skills`
does not manage them. Claude plugins remain delegated to Claude's plugin manager.

## Quick start

```bash
make install                         # install the full profile
make profiles                        # show available profiles
make switch PROFILE=python-design    # activate a smaller profile
make update                          # update npx skills and agent definitions
```

A switch installs every selected package first. Only after all installs succeed
does it remove configured skills outside the selected profile. Skills not declared
in `skills.toml` are left alone.

## Configuration

Profiles are the authoritative skill inventory. Each entry combines its GitHub
package and exact npx skill name as `owner/repository@skill`.

```toml
[package_options."wolski/claude-kaiser-skills"]
full_depth = true

[profiles.python-design]
description = "Wolski's Python style and bounded design guidance, plus public Clean Architecture."
skills = [
    "wolski/claude-kaiser-skills@python-style-guide",
    "wolski/claude-kaiser-skills@design-principles",
    "wolski/claude-kaiser-skills@polymorphism-over-discrimination",
    "pproenca/dot-skills@clean-architecture",
]
agents = []

[profiles.python-design-public]
description = "Public Python design-pattern and Clean Architecture guidance, without Wolski skills."
skills = [
    "wshobson/agents@python-design-patterns",
    "pproenca/dot-skills@clean-architecture",
]
agents = []

[profiles.python]
description = "Broad Python engineering toolkit."
includes = ["python-design", "marimo"]
skills = ["google-deepmind/science-skills@uv"]

[profiles.full]
description = "Every configured profile and standalone Claude agent."
includes = ["*"]
agents = ["*"]
```

Every profile has a human-readable `description`, shown by `make profiles`.
The coordinator groups entries from the same package into one npx command. The
`includes` field composes named profiles, while `includes = ["*"]` composes every
other profile. The `full` profile therefore contains no direct skills. Cleanup
uses the union of every direct profile entry. A package-options entry is needed
only for npx behavior such as `--full-depth`, not for skill membership. A skill
name may have only one package owner. `agents = ["*"]` selects every configured
standalone agent.

Standalone agents have their own source declaration:

```toml
[agent_sources.claude-kaiser-skills]
repository = "https://github.com/wolski/claude-kaiser-skills.git"
agents = ["agents/dry-audit.md"]
```

The agent repository is cloned under `repos/` when required. No skill is read from
that clone.

## Commands

```text
make install         Install PROFILE (default: full)
make switch          Switch the direct npx installation to PROFILE
make profiles        List configured profiles
make update          Update global npx skills and agent sources
make clean           Remove only configured skills and managed agents
make list            List installed skills, agents, and matching profile
make status          Show standalone agent-source Git status
make audit           Compare installed skill hashes with review records
make dry-run         Preview a profile switch
make test            Run the test suite
make plugins         Install configured Claude plugins
make plugins-remove  Uninstall configured Claude plugins
make plugins-list    List installed Claude plugins
```

The Makefile delegates to the typed Cyclopts CLI in `skill_coordinator.py`. The
npx version is pinned there so installation behavior does not silently change.
