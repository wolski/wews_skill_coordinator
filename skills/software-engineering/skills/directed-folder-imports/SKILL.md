---
name: directed-folder-imports
description: Migrate organically grown Python src packages to a directed folder dependency tree in which parent modules compose independent child packages, children never import parent modules or sibling children, and single-child-owned modules move into that child. Use this skill whenever a user asks to clean up a Python package structure or import graph, untangle upward/sideways/circular imports, split a monolith into packages, add import-linter architecture contracts, enforce folder boundaries in AGENTS.md, or transfer APB2-style import rules to another codebase.
---

# Directed Folder Imports

Turn a package that grew by convenience into a package whose directory tree states its dependency
direction. Treat this as an ownership migration, not a file-shuffling or linter-silencing exercise.

## The law

For a package `A/` with child packages `A/B/` and `A/C/`:

```text
A/*.py  -> A/B/*    allowed: a parent module imports downward
A/*.py  -> A/C/*    allowed: a parent module imports downward
A/B/*   -> A/*.py   forbidden: a child imports upward
A/C/*   -> A/*.py   forbidden: a child imports upward
A/B/*   -> A/C/*    forbidden: sibling children import sideways
A/C/*   -> A/B/*    forbidden: sibling children import sideways
```

Apply the law recursively inside every child package selected as an architectural boundary.
Modules directly in one directory may import one another when that directory is one component, but
cycles are still defects and an explicit module-layer order may be useful.

Directory placement also expresses ownership:

- Move a parent-level module used and owned by only one child into that child.
- Keep a module in the parent only when it implements the parent's external boundary or genuinely
  composes more than one child.
- Do not move a child-owned module upward merely because it imports an external library.
- Do not create `shared`, `common`, `utils`, `model`, or `helpers` as an ownership-free parking lot.

This is a component tree, not a claim that nested folders are automatically good. If two proposed
siblings must know each other's types and behavior, redraw the boundary before adding folders.

## Start with evidence

Do not move files on the first pass.

1. Read the closest project instructions, packaging configuration, CI, and architecture docs.
2. Inspect `git status` and preserve unrelated work. Establish the existing test/lint baseline.
3. Identify the actual import root (`src/<package>`, a flat package, or several roots).
4. Inventory production modules, public entry points, package data/resources, tests, and imports.
5. Run the project's existing dependency tool first. For Python, prefer Import Linter/Grimp over a
   new AST walker. Add a tool only after confirming none exists.
6. Record current violations as edges, not impressions:
   `source module -> imported module -> upward | sideways | cycle | framework leak`.

Read [migration-playbook.md](references/migration-playbook.md) for the evidence tables and phased
migration sequence.

## Design the target tree

Describe every intended folder in one sentence: what it owns, what it may import, and what imports
it. If that sentence cannot be written, the boundary is not ready.

Use this placement test for each module:

| Evidence | Placement |
| --- | --- |
| Owns one child's vocabulary or behavior and is consumed only there | Move into that child |
| Translates between two independent children | Parent composition module |
| Constructs implementations and injects them into consumers | Parent composition root |
| Defines storage/framework declarations | Adapter/schema child, independent of computation |
| Holds values one parent workflow consumes | Inward data child, if no sibling must import it |
| Needed directly by two supposed siblings | Recut/merge boundaries or inject a smaller capability |
| Merely re-exports a child object | Delete it or move the public boundary deliberately |

Prefer client-owned capabilities. If child `B` consumes behavior implemented by sibling `C`, put a
small `Protocol` or `Callable` shape in `B` and let `C` conform structurally without importing `B`.
The parent imports both and injects `C` into `B`. Simple values can be translated at that parent
boundary. This removes the sideways edge instead of hiding it.

Keep Pydantic/ORM/API schemas at storage boundaries. A storage model should not acquire runtime
behavior merely to avoid an import; project it into plain runtime values at a parent boundary.

## Choose a migration shape

Select one explicitly:

- **In-place slice:** suitable when the public imports are small and the current tests give strong
  coverage. Move one coherent dependency slice at a time.
- **New namespace/strangler:** suitable when legacy imports are dense or the replacement is a large
  redesign. Build the directed package beside the old one, cut one external entry point over, then
  delete the legacy implementation.

Do not maintain two implementations indefinitely. Compatibility imports are allowed only for an
explicitly preserved public API, with an owner and removal condition. Internal forwarding modules,
fallback imports, and duplicate implementations are carpets.

Before a substantial migration, write a plan and obtain approval. The plan must show:

- current and target trees;
- allowed and forbidden edges;
- module moves with ownership reasons;
- public API/resource-path consequences;
- the cutover and deletion point;
- enforcement and verification commands.

## Migrate in slices

For each slice:

1. Move the lowest-dependency values/schemas first when they already have a clear inward owner.
2. Move the behavior owned by that boundary; update every internal import directly.
3. Add or move the parent adapter/facade/composition root that connects independent children.
4. Move the corresponding tests to mirror the production ownership.
5. Run focused tests and the import contract before taking the next slice.
6. Delete superseded code once the entry point uses the new path.

Prefer real moves over copies. Keep `__init__.py` empty unless it is an intentionally supported
public import surface; re-exporting everything conceals the defining module and the dependency
edge. Never use dynamic imports, `sys.path` manipulation, type-check-only imports, or local imports
to fool the graph.

If the worktree is dirty, preserve it. Create a checkpoint commit only when the user authorizes a
commit; otherwise report the exact pre-existing state and keep the migration diff separable.

## Enforce the proven graph

Use Import Linter for Python package edges. Ruff is a formatter/linter and cannot express an
arbitrary recursive folder dependency graph. Read [import-linter.md](references/import-linter.md)
and create one exhaustive contract per meaningful container:

- list parent modules above their children;
- put independent siblings on the same `|` layer;
- add nested contracts for child packages with their own internal tree;
- add focused forbidden contracts for framework/backend isolation;
- run `lint-imports` from the ordinary lint/check target and CI.

Use architecture tests only for properties Import Linter cannot express, such as an exact set of
authorized cross-child composition modules, an intentionally empty package marker, or a public CLI
that may import only one facade. Do not duplicate the entire import graph in AST tests.

Add the concise rule to project agent instructions only after the target tree is agreed. Use the
copyable block in [agents-guidance.md](references/agents-guidance.md), replacing placeholders with
verified paths and commands.

## Verify completion

Run, in this order:

1. focused tests for each moved slice;
2. Import Linter and cycle detection;
3. formatter, linter, and strict type checker;
4. the complete repository test gate proportionate to the change;
5. package/wheel/resource smoke tests when modules or package data moved;
6. public entry-point/import smoke tests;
7. non-blocking architecture diagnostics, interpreted rather than optimized.

Report:

- the before/after tree and import edges;
- modules moved, deleted, or deliberately retained in the parent;
- public compatibility decisions;
- contracts added and what each one proves;
- verification results and any remaining legacy island.

The work is complete when the code, folder tree, linter contracts, tests, and agent guidance say the
same thing. A clean linter result obtained through ignores, aliases, or indirection is not complete.

## Failure modes to reject

- Creating folders to improve a metric without a named ownership boundary.
- Moving all records into `models.py` or all helpers into `utils.py`.
- Putting a facade inside one child when it imports that child's sibling.
- Letting a child import its parent's configuration or errors.
- Solving a sideways dependency with a sibling `shared/` package.
- Enforcing an imagined target graph before checking real imports and public APIs.
- Claiming Ruff enforces the rule.
- Keeping old and new paths alive through broad re-exports.
- Refactoring the whole repository when one bounded package can establish the new rule first.
