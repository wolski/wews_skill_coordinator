# Explicit paths for local skill references

> Make the source-relative folder path the configured identity of every locally
> managed skill; never resolve a local skill by a flattened basename.

Status: implemented and verified on 2026-08-28.

## Requirements

- A profile entry for a package declared under `[sources]` must contain the exact
  skill directory relative to that source root.
- Examples:

  ```toml
  "fgcz/skills@communication/skills/interview-to-spec"
  "fgcz/skills@proteomics-data-analysis/skills/adding-models-to-prolfqua"
  "wolski/wews_skill_coordinator@software-engineering/skills/python-style-guide"
  ```

- The old flattened local form, such as
  `fgcz/skills@interview-to-spec`, is invalid. Do not retain a compatibility
  lookup or search by basename.
- The configured path must be relative, normalized, and exact. Reject absolute
  paths, `.` or `..` components, paths outside the source, and paths that do not
  identify a directory containing `SKILL.md`.
- The final path component must equal the skill's frontmatter `name`. This name
  remains the runtime install name because Claude Code and Codex require the flat
  `~/.agents/skills/<name>` store.
- Continue rejecting duplicate runtime names, even when their source paths differ,
  because two skills cannot occupy the same runtime store entry.
- References to packages not declared under `[sources]` remain npx skill selectors,
  for example `pproenca/dot-skills@clean-architecture`. The coordinator does not
  own or inventory those source trees, and npx accepts a skill name rather than a
  repository-relative path.
- Represent each FGCZ source folder that contributes configured skills as its own
  composable profile in `skills.toml`:

  - `fgcz-bfabric-lims`
  - `fgcz-communication`
  - `fgcz-infrastructure`
  - `fgcz-meta-skills`
  - `fgcz-proteomics-data-analysis`

- The broad `fgcz` profile includes all five FGCZ folder profiles. The
  `proteomics` profile includes the complete `fgcz-bfabric-lims` and
  `fgcz-proteomics-data-analysis` profiles plus its existing individual
  infrastructure dependency. Other logical profiles may still select individual
  exact paths when they intentionally need only part of a folder group.
- Folder profiles contain the complete configured inventory from that folder, so
  the configuration visibly mirrors the local source structure rather than
  presenting one flattened FGCZ list.

## Design

### Reference model

`SkillReference` retains the `owner/repository@selector` envelope, but `selector`
has installation-kind-specific meaning:

- local package: exact POSIX source-relative directory path;
- npx package: npx skill name, with `/` forbidden.

Parsing performs syntax-only validation. Configuration validation, which knows
the `[sources]` packages, applies the local-path or npx-name rules. The runtime
skill name is derived from the local path's final component or equals the npx
selector.

### Local inventory

Replace the flattened `dict[name, directory]` inventory with records keyed by
their exact source-relative directory path. Each record carries:

- `source_path`: normalized POSIX path such as
  `proteomics-data-analysis/skills/adding-models-to-prolfqua`;
- `name`: validated frontmatter/install name;
- `directory`: resolved filesystem directory.

Discovery may still scan `<category>/skills/<name>/SKILL.md` to validate owned
inventory and enumerate third-party checkouts, but resolution must be a direct
path-key lookup. It must never search the inventory for a matching basename.

Owned sources compare configured paths with discovered paths exhaustively.
Non-owned sources require each configured path to exist but may contain additional
paths. Existing handling of off-pattern skills in non-owned sources remains.

### Reconciliation and presentation

Profile resolution converts exact local path records into `LocalSkill` values.
Installation, kind flips, rollback, cleanup, audit, and active-profile matching
continue to operate on the validated runtime name. `list` continues to show the
source-relative path for local installations.

No migration alias is added: a flattened local reference fails configuration
validation with an error showing the expected exact path form.

### Folder-aligned profiles

Use the existing profile-composition mechanism rather than adding a second group
abstraction. A folder becomes an ordinary installable profile:

```toml
[profiles.fgcz-communication]
description = "FGCZ communication workflows."
skills = [
    "fgcz/skills@communication/skills/interview-to-spec",
]

[profiles.fgcz-proteomics-data-analysis]
description = "FGCZ proteomics data-analysis skills."
skills = [
    "fgcz/skills@proteomics-data-analysis/skills/adding-models-to-prolfqua",
    # other configured skills from the same source folder
]

[profiles.fgcz]
description = "All configured FGCZ skill groups."
includes = [
    "fgcz-bfabric-lims",
    "fgcz-communication",
    "fgcz-infrastructure",
    "fgcz-meta-skills",
    "fgcz-proteomics-data-analysis",
]
```

This keeps one composition concept: folder groups and broader workflow bundles
are both profiles. `full` continues to include every profile and deduplicates
references through the existing resolver.

## Implementation plan

- [x] Update `SkillReference` and local inventory types in
  `skill_coordinator.py` so local selectors remain exact paths through parsing,
  validation, profile resolution, and reporting.
- [x] Add strict local-path validation and preserve strict npx-name validation.
- [x] Migrate every local-source occurrence in `skills.toml` to its exact path,
  including all Wolski and FGCZ entries; leave npx entries unchanged.
- [x] Add the five FGCZ folder profiles, move their complete configured inventories
  into those profiles, and compose `fgcz` and `proteomics` from them without
  duplicating whole folder lists.
- [x] Update inventory, profile, reconciliation, and production-configuration
  tests in `test_skill_coordinator.py`.
- [x] Add regression tests proving that flattened local references, basename
  fallback, traversal, absolute paths, wrong categories, and frontmatter/path
  disagreement are rejected.
- [x] Update `README.md`, `AGENTS.md`, and the mixed-install TODO so examples and
  configuration rules show exact local paths and do not describe local references
  as flattened names.
- [x] Run `make test`, Ruff checks and formatting, Pyright, `git diff --check`,
  and dry runs for `python-design` and `full`.

## Verification results

- `make test`: 142 tests passed.
- `uvx ruff check skill_coordinator.py test_skill_coordinator.py`: passed.
- `uvx ruff format --check skill_coordinator.py test_skill_coordinator.py`:
  passed after formatting the changed test module.
- Pyright over the changed Python module and test: 0 errors, 0 warnings.
- `git diff --check`: passed.
- `make dry-run PROFILE=python-design`: passed and reported the selected profile.
- `make dry-run PROFILE=full`: passed, resolved all 71 configured runtime names,
  and displayed local targets with their category paths.
- `make profiles`: `fgcz` resolves 20 skills from the five folder profiles;
  `proteomics` resolves 11 skills from its two included folder profiles and one
  direct infrastructure skill.

## Acceptance

- `skills.toml` visibly preserves source categories for all local skills.
- FGCZ folder categories are independently selectable profiles, and `fgcz`
  composes the complete configured FGCZ inventory from them.
- `fgcz/skills@interview-to-spec` fails; the exact
  `fgcz/skills@communication/skills/interview-to-spec` succeeds.
- `fgcz/skills@adding-models-to-prolfqua` fails; the exact
  `fgcz/skills@proteomics-data-analysis/skills/adding-models-to-prolfqua`
  succeeds.
- No local profile resolution uses a basename-to-directory map or fallback.
- Existing mixed installation, rollback, external-source cleanup, audit, list,
  clone, update, and dry-run behavior remains covered and passing.

## Open question

- A general `agent-workflows` profile is intentionally not invented in this
  refactor. `interview-to-spec` becomes independently selectable through
  `fgcz-communication`; a broader agent taxonomy can be designed separately.
