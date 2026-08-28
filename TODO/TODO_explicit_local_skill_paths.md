# Explicit paths for local skill references

> Make the source-relative folder path the configured identity of every locally
> managed skill; never resolve a local skill by a flattened basename.

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
- Do not change which profiles include which skills in this refactor. Profile
  reorganization, including a possible agent-workflows profile, is separate work.

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

## Implementation plan

- [ ] Update `SkillReference` and local inventory types in
  `skill_coordinator.py` so local selectors remain exact paths through parsing,
  validation, profile resolution, and reporting.
- [ ] Add strict local-path validation and preserve strict npx-name validation.
- [ ] Migrate every local-source occurrence in `skills.toml` to its exact path,
  including all Wolski and FGCZ entries; leave npx entries unchanged.
- [ ] Update inventory, profile, reconciliation, and production-configuration
  tests in `test_skill_coordinator.py`.
- [ ] Add regression tests proving that flattened local references, basename
  fallback, traversal, absolute paths, wrong categories, and frontmatter/path
  disagreement are rejected.
- [ ] Update `README.md`, `AGENTS.md`, and the mixed-install TODO so examples and
  configuration rules show exact local paths and do not describe local references
  as flattened names.
- [ ] Run `make test`, Ruff checks and formatting, Pyright, `git diff --check`,
  and dry runs for `python-design` and `full`.

## Acceptance

- `skills.toml` visibly preserves source categories for all local skills.
- `fgcz/skills@interview-to-spec` fails; the exact
  `fgcz/skills@communication/skills/interview-to-spec` succeeds.
- `fgcz/skills@adding-models-to-prolfqua` fails; the exact
  `fgcz/skills@proteomics-data-analysis/skills/adding-models-to-prolfqua`
  succeeds.
- No local profile resolution uses a basename-to-directory map or fallback.
- Existing mixed installation, rollback, external-source cleanup, audit, list,
  clone, update, and dry-run behavior remains covered and passing.

## Open question

- None for path identity. Reorganizing logical profiles by agent workflow or FGCZ
  source category is intentionally outside this refactor.
