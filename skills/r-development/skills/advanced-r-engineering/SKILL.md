---
name: advanced-r-engineering
description: R engineering judgment for reviewing, refactoring, profiling, and architecting R code — as distinct from writing it. This skill should be used when R code needs a design or correctness review, an object-system decision (S3 vs S4 vs R6), performance profiling or memory work, dependency and API design, or a maintainability assessment of a package or serious R codebase. Trigger on requests like "review this R function/package", "is S4 or R6 right here", "why is this R code slow", "profile this", or "refactor this R module". Defer to r-development for writing tidyverse/dplyr/ggplot2 code and data wrangling, to r-package-development for devtools/roxygen2/testthat mechanics, and to verify-review-findings for the confirm-or-refute discipline on individual findings.
---

# Advanced R Engineering

Use this skill when R code needs engineering judgment, not just syntax help. Prefer
package-shaped, tested, documented, and profiled solutions. Keep interfaces small, explicit,
and idiomatic for R.

## When to use this skill

This is the *judgment and review* skill for R — it decides what and whether, and hands the
mechanics to its siblings. Reach for it to review/refactor code, choose an object system,
profile a hot path, or design an API or dependency surface.

Defer instead when the task is really:

- **Writing** tidyverse/dplyr/ggplot2 code or wrangling data → `r-development`.
- **Package mechanics** — devtools workflow, roxygen2, testthat scaffolding → `r-package-development` (and `testing-r-packages` for testthat 3 patterns).
- **Confirming or refuting an individual review finding** before reporting it → the `verify-review-findings` skill. This skill tells you *what good R looks like*; that one governs *the rigor of each finding*.

## Core Defaults

- Prefer plain functions and S3 generics for most public APIs — they keep objects ordinary and extensible.
- Use S4 only when formal class contracts, validators, or multiple dispatch are genuinely needed.
- Use R6 only when mutable state, object lifecycles, caches, external resources, or encapsulated state are central to the domain.
- Put reusable code in an R package rather than loose scripts, so it can be tested, documented, and versioned.
- Profile before optimizing — intuition about R hot paths is unreliable, and the real cost is often somewhere surprising.
- Prefer specialized vectorized primitives and whole-object operations over scalar loops.
- Avoid accidental copies, silent mutation, repeated object growth, and unclear ownership of mutable objects.
- Use automated style, tests, documentation, dependency declaration, and CI for code that matters.

## Review Workflow

1. Inspect the existing project shape before recommending changes:
   - `DESCRIPTION`, `NAMESPACE`, `R/`, `tests/`, `man/`, `vignettes/`, `inst/`, `src/`
   - `renv.lock`, `.Rprofile`, `.github/workflows/`, `pkgdown/`, `.lintr`
2. Identify the public API:
   - exported functions
   - S3/S4/R6 classes
   - user-facing return types
   - lifecycle or compatibility promises
3. Check correctness before style:
   - invalid assumptions about missing values, factors, recycling, row names, grouped data, or object classes
   - inconsistent parameter names or return shapes
   - hidden mutation through environments, R6 objects, reference classes, or `data.table`
   - unstated dependencies on global options, working directory, locale, random seed, or attached packages
4. Check maintainability:
   - functions with too many responsibilities
   - package code mixed with analysis code
   - duplicated validation logic
   - public helpers that should remain internal
   - internal helpers that lack tests for important edge cases
5. Check verification:
   - testthat coverage for normal paths, edge cases, and expected errors
   - `devtools::check()` or `R CMD check`
   - deterministic tests for random, time-dependent, networked, or file-system behavior
   - CI coverage of supported R and platform versions

## Style And API Design

Prefer the tidyverse style guide defaults unless the package already has a different
established style: snake_case names, dots primarily for S3 methods, verb-like function names,
noun-like object names, two-space indentation, explicit argument names when ambiguity is
possible, and comments that explain *why*, not *what*.

Keep APIs boring, because predictability is what makes them safe to depend on:

- stable return types;
- clear error messages;
- minimal public surface;
- no surprise mutation;
- no hidden reliance on global state;
- consistent parameter names across related functions;
- predictable handling of `NA`, empty inputs, and zero-row data frames.

For report, vignette, or workflow-specific requests, first change the call site
using existing package APIs. Treat new exported arguments, NEWS entries, Rd
topics, roxygen changes, or public helpers as package API changes; make those
only when the user explicitly asks for a package-level feature or the existing
API cannot express the requested behavior.

## Testing Checklist

For behavior changes, ask whether tests cover:

- ordinary successful usage;
- empty inputs;
- missing values;
- invalid classes or malformed objects;
- expected error messages;
- deterministic random behavior with `set.seed()`;
- platform-specific behavior, especially paths, parallelism, and compiled code;
- S3/S4/R6 invariants and print/summary/predict methods when relevant.

Prefer tests of public behavior over tests of private implementation details. Test private
helpers directly only when they encode important, complicated logic that is otherwise hard to
exercise.

## Review Output

When reviewing R code, lead with concrete findings:

- cite file and line;
- explain the behavioral risk;
- name the minimal fix;
- mention missing verification when relevant.

Avoid broad rewrites unless the code structure prevents a correct localized fix. When a large
refactor is justified, separate it from bug fixes and state the migration path.

## Deep-dive references

Load these only when the task reaches that decision — the summaries above are enough for most
reviews.

- **Object system choice (S3 / S4 / R6)** — when designing or reviewing a class hierarchy: [references/object-systems.md](references/object-systems.md)
- **Performance and memory** — when profiling, fixing a hot path, or reasoning about copies and `data.table` mutation: [references/performance.md](references/performance.md)
- **Package engineering standards** — when packaging code or placing a dependency: [references/packaging.md](references/packaging.md)
- **Contracts and input validation** — when designing how a function defends its inputs (checkmate, vctrs, `arg_match`) or guarantees outputs: [references/contracts-and-validation.md](references/contracts-and-validation.md)

## Useful Commands

```r
devtools::load_all()
devtools::test()
devtools::check()
devtools::document()
lintr::lint_package()
```

```bash
R CMD check path/to/pkg
air format --check .
air format .
```
