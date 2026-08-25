# AGENTS.md guidance

Use this concise block after verifying the actual package names and check commands. Put it in the
closest AGENTS.md governing the package. Do not paste speculative module names.

```markdown
## Architecture and import direction

Directory nesting is an import rule, not decoration. For a package `A/` with child packages
`A/B/` and `A/C/`:

- modules directly in `A/` may import from `A/B/` and `A/C/`;
- code under `A/B/` or `A/C/` must not import modules directly in `A/`;
- `A/B/` and `A/C/` must not import one another; and
- a module in `A/` owned only by `A/B/` moves into `A/B/`; genuine cross-child composition
  remains in `A/`.

Apply the same rule recursively to `[NAME THE NESTED PACKAGES]`. `[NAME THE PARENT MODULES]` are
the authorized cross-child composition boundary. Do not add compatibility re-exports, `utils` or
`shared` buckets to bypass ownership.

The executable contracts live in `[PATH TO .importlinter]`. Run `[VERIFIED LINT COMMAND]`; CI and
`[VERIFIED CHECK COMMAND]` run the same `lint-imports` gate.
```

Also document scoped exceptions, if any, as temporary migration islands with an owner and removal
condition. “Legacy code” without a named boundary is not an exception.

Keep the rule short in AGENTS.md and point to the architecture document for the concrete tree.
AGENTS.md tells an agent what to preserve; the linter proves the edges, and the architecture
document explains why the components exist.

