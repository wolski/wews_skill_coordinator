# CLAUDE.md

This is a coordinator repository. Skills are installed directly from GitHub by
`npx skills`; they are not cloned or cached here.

## Rules

- Do not edit installed skill files under `~/.agents`, `~/.claude`, or `~/.codex`.
- Edit custom skills in their source repository, commit, and push there; then run
  `make update` or switch profiles to reinstall them.
- Treat third-party skill sources as read-only.
- Coordinator behavior belongs in `skill_coordinator.py` and
  `test_skill_coordinator.py`.
- Configuration, command aliases, and documentation belong in `skills.toml`,
  `Makefile`, `README.md`, `AGENTS.md`, and this file.
- The only repository retained under `repos/` is a source for standalone Claude
  agent definitions, which the npx CLI does not manage.

## How it works

1. `make install` or `make switch PROFILE=...` resolves a profile in `skills.toml`.
2. The coordinator installs selected skills directly with the pinned npx CLI for
   Claude Code and Codex.
3. Once all additions succeed, it removes configured skills outside the profile.
4. It clones and links profile-selected standalone Claude agents separately.
5. `make update` delegates skill updates to npx and pulls agent sources.

## Adding a skill

1. Add `owner/repository@skill-name` directly to the relevant profiles in
   `skills.toml`. `full` includes every profile automatically.
2. Run `make dry-run PROFILE=<profile>` and `make switch PROFILE=<profile>`.

Add `[package_options."owner/repository"]` only when the package requires an npx
option such as `full_depth = true`.

Profiles may compose named profiles with `includes = ["one", "two"]`. Only the
`full` aggregate should use `includes = ["*"]`.
