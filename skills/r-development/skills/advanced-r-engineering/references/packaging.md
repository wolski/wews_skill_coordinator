# Package Engineering Standards

Read this when turning code into a package, reviewing package structure, or deciding where
a dependency belongs. For the day-to-day devtools/roxygen2/testthat *mechanics*, defer to
the `r-package-development` skill — this file covers the engineering judgment around them.

## Package shape

For reusable R code, prefer an R package with:

- `DESCRIPTION` declaring dependencies intentionally;
- `R/` files organized by public function or coherent internal area;
- roxygen2 documentation beside exported functions;
- `@noRd` documentation for non-trivial internal helpers;
- `tests/testthat/` with focused tests;
- `vignettes/` or articles for workflows;
- `renv.lock` when reproducible project environments matter;
- CI running package checks;
- optional `pkgdown` site for user-facing packages.

## Dependency rules

- Put packages needed by exported functionality in `Imports`.
- Put packages used only in tests, examples, vignettes, or optional workflows in `Suggests`.
- Use `pkg::fn()` or explicit roxygen imports; avoid attaching dependencies just for
  convenience.
- Avoid `pkg:::fn()` except for temporary debugging; do not build package behavior on
  unexported APIs.
- Keep version requirements minimal but explicit when relying on recently introduced
  behavior.
