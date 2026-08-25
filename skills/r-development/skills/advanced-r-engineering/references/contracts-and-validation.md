# Contracts And Validation

Read this when designing or reviewing how a function defends its inputs and guarantees its
outputs — i.e. design-by-contract in R. This is the proactive counterpart to the
`verify-review-findings` structural-fix advice ("state and enforce the contract up front"):
a contract written into the function is one a reviewer never has to reconstruct.

## Preconditions: validate inputs at the boundary

Adopt this as a default for exported functions. Explicit input checks turn the implicit
assumptions the review workflow hunts for (missing values, wrong classes, bad recycling,
zero-row frames) into loud, early, well-located failures. Tooling, heaviest to lightest:

- **`checkmate`** — the default recommendation. C-level fast, comprehensive, with clear
  messages. Designed precisely for function-entry checks.

  ```r
  summarise_scores <- function(x, weights = NULL) {
    checkmate::assert_numeric(x, any.missing = FALSE, min.len = 1L)
    checkmate::assert_numeric(weights, len = length(x), null.ok = TRUE)
    # ... fast path can now trust x and weights ...
  }
  ```

  The family: `assert_*` (stop on failure), `check_*` (return `TRUE` or a message string),
  `test_*` (return a logical), and the compact `qassert()` / `qtest()`.

- **`rlang::arg_match()`** (or base `match.arg()`) — for enumerated string arguments; gives a
  "did you mean" message instead of a silent partial match.

- **`vctrs`** (`vec_assert()`, `vec_size()`, `vec_recycle()`) — for type and size contracts.
  This is the right tool for the recycling/size failure modes the review workflow flags,
  because it makes size rules explicit rather than relying on base R's silent recycling.

- **`stopifnot()`** — base R, zero-dependency. Fine for lightweight internal asserts; named
  conditions (R ≥ 4.0) improve the otherwise terse messages.

## Postconditions: prefer tests over runtime checks

R culture rarely enforces postconditions at runtime, and that is usually the right call. The
idiomatic place to assert "this function guarantees X" is a **testthat test**, not a runtime
guard — you get the guarantee without paying for it on every call. Packages like `ensurer`
(`ensure()`) and `valaddin` can attach runtime post/precondition checks, but adoption is thin;
reach for runtime postconditions only for a critical invariant that is cheap to verify.

## Data-frame and pipeline contracts

For tabular data rather than scalar arguments — common in analysis pipelines — use a data
validation layer instead of hand-rolled checks:

- **`assertr`** — assertions inside a dplyr pipeline (`verify()`, `assert()`, `insist()`).
- **`pointblank`** — validation with reporting and reusable agents.
- **`validate`** — rule sets defined separately from the code.

## Object invariants

Push class invariants into the object system rather than re-checking them at every call site
(see [object-systems.md](object-systems.md)): a constructor + validator for S3,
`setValidity()` / `validObject()` for S4, validation in `initialize()` (or active bindings)
for R6. An object that cannot exist in an invalid state needs no defensive checks downstream.

## The performance caveat

Validate **once at the boundary**, never inside a hot vectorized loop — per-element
assertions silently defeat vectorization (see [performance.md](performance.md)). `checkmate`
is cheap, but cheap-per-call still adds up across millions of iterations. Check on entry,
then trust the data on the fast path.
