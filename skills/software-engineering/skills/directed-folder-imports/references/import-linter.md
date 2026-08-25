# Import Linter enforcement

Use this reference after the target folder tree is agreed and at least one migrated slice exists.
Import Linter checks imports; it does not decide module ownership for you.

## Install and wire it

Add `import-linter` using the project's existing dependency manager. Keep the configuration at the
repository root and run `lint-imports` from the normal lint/check command and CI.

```ini
[importlinter]
root_packages =
    acme
include_external_packages = True
```

Do not add a second wrapper script when the existing task runner can call `lint-imports` directly.

## Parent with independent children

Suppose the parent contains four composition/application modules and three independent children:

```ini
[importlinter:contract:acme-directory-tree]
name = acme children never import upward or sideways
type = layers
exhaustive = True
containers =
    acme
layers =
    conversion
    detect
    compile
    facade
    parsing | rules | vendor_parameters
```

Layers are written from outer/highest to inner/lowest. Modules on one `|` line are independent:
none may import another. Order parent modules only when that dependency is intentional; use `|`
for parent modules that should also remain independent.

`exhaustive = True` is important. A new top-level module must be assigned deliberately rather than
silently escaping the contract.

## Nested child tree

Add another contract for a child that has its own inward leaves:

```ini
[importlinter:contract:parsing-directory-tree]
name = parsing descends into data and parameters
type = layers
exhaustive = True
containers =
    acme.parsing
layers =
    parser
    contracts
    decomposition | input_adapter | output_adapter
    errors
    data | parameters
```

One contract cannot infer every recursive folder boundary. Encode each architectural container
whose children are meant to be independent.

## Focused forbidden dependencies

Use a forbidden contract for framework isolation or a particularly important boundary:

```ini
[importlinter:contract:computation-has-no-storage-framework]
name = parsing computation has no storage framework
type = forbidden
source_modules =
    acme.parsing.data
    acme.parsing.parameters
    acme.parsing.contracts
forbidden_modules =
    pydantic
    sqlalchemy
    pandas
    numpy
```

Set `include_external_packages = True` when checking third-party imports.

Use `allow_indirect_imports = True` only when the architectural statement is genuinely about
reachability, not to make a direct-edge contract look stronger than intended.

## What Import Linter does not replace

Use a focused architecture test for facts such as:

- only `compile.py` and `facade.py` may import two independent children;
- the CLI imports only the application facade;
- package `__init__.py` files remain empty;
- a runtime module does not inspect schema discriminator strings;
- the installed wheel includes moved JSON/TOML resources.

Do not rewrite all imports in an AST test. That duplicates Import Linter and creates two graphs that
can drift.

## Ruff is not this tool

Ruff can ban specific imports or enforce style, but it does not model an arbitrary recursive
package tree with parent, child, sibling, and exhaustive ownership relationships. Keep Ruff as the
formatter/linter and Import Linter as the architectural graph check.

## Adoption in a wild project

If the entire legacy package cannot pass immediately:

1. contract the new/migrated package first;
2. prohibit new edges into known legacy areas;
3. list remaining legacy components explicitly in the migration plan;
4. expand the contract after each real move;
5. never use blanket ignores to manufacture a green graph.

The contract should be merge-blocking once its scoped package passes. Diagnostic graph counts may
remain non-blocking gauges; they are not substitutes for the explicit law.

