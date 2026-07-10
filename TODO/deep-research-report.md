# Design by Contract in R Functions and R6 Classes

## Executive summary

R’s design-by-contract tooling is real, but it is fragmented. The strongest current choices for general-purpose runtime contracts are **checkmate** and **chk** when speed and low overhead matter, **assertthat** and **assertions** when human-readable errors and low-friction adoption matter, **valaddin** when you want to retrofit input validation onto existing closures, **assertr** when the problem is really data-pipeline validation, and **dbc** when you want a GitHub-only package that leans explicitly into function-input and function-output verification. The package **precondition** was the clearest CRAN package to expose explicit `precondition()` and `postcondition()` APIs with rich diagnostics, but it was archived from CRAN in April 2026. Older packages such as **assertive** and **ensurer** are historically important, but both are archived on CRAN and are poor greenfield defaults today. citeturn39search0turn39search18turn18search3turn32view0turn7view4turn39search20turn20view0turn10view0turn23search0turn27search0

For **plain functions**, contracts are best used at the public boundary: validate arguments immediately, compute, then validate only the output properties that are semantically important and non-obvious. For **S4**, the native mechanism is still `setValidity()` and `validObject()`, optionally aided by helpers like `assertthat::validate_that()` because it returns a character vector suitable for validation methods. For **R6**, there is no comparable built-in validity hook in the R6 API; in practice, checks belong in `initialize()` and in all mutating methods, while `checkmate::checkR6()` is useful when validating incoming R6 objects. citeturn16search2turn16search4turn36view0turn15search0turn15search1turn33view4

Published quantitative evidence in R is limited, but the best benchmark source is the **R Journal** paper on **checkmate**. In that benchmark, `qassert()` and `assertNumeric()` outperformed `stopifnot()`, `assertthat`, and `assertive` on non-trivial checks, especially for large vectors and early-exit failures; on a `1e7`-element benchmark, `checkmate` showed essentially no extra memory footprint over baseline process startup, while base-R and `assertthat` used substantially more and `assertive` used much more. These numbers are from older package versions and should be treated as directional rather than current absolutes, but the architectural explanation remains relevant: `checkmate` pushes many checks into compiled code and avoids intermediate allocations. citeturn30view0turn31view0turn7view0

Almost all R contract tooling is **runtime checking**, not static checking. Static analysis tools such as **lintr** and **codetools** complement contracts by detecting style, syntax, and some semantic problems without execution, and there are experimental efforts such as **typeChecker**, but these do not replace runtime preconditions and postconditions for values that are only known when code runs. citeturn17search5turn17search1turn17search12

The pragmatic recommendation for most package codebases is: choose **one** primary assertion style, wrap it behind a very small internal API, use **S4 validity** for S4 classes, use **method-body checks** for R6, add **tests for both success and failure paths**, and avoid archived packages for greenfield work unless you vendor or own the risk. citeturn16search2turn14search2turn14search5turn23search0turn27search0turn39search17

## Package landscape

In the reviewed ecosystem, contract tooling falls into a few practical families. One family extends or replaces `stopifnot()` with better messages and modest API changes, represented by **assertthat**, **assertions**, **assert**, **checkarg**, and **chk**. A second family emphasizes **speed and defensive programming**, led by **checkmate** and, in a different style, **dbc**. A third family emphasizes **wrapping or decorating functions**, especially existing closures, represented by **valaddin**, **ensurer**, and the archived **precondition** package. A fourth family is really about **data-pipeline assertions** rather than generic function contracts, represented by **assertr**. In the reviewed sources, dedicated function-contract packages were concentrated on CRAN and GitHub, while the closest Bioconductor-style mechanism was still the S4 validity system in base R’s `methods` package. citeturn29search0turn18search3turn32view0turn27search4turn22view0turn39search18turn39search0turn20view0turn7view4turn28view0turn10view0turn39search20turn16search2turn16search4

| Package | License | CRAN/GitHub | API style | Supports R6 | Supports S3/S4 | Performance notes | Example usage | Maturity/maintenance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `assertthat` citeturn18search3turn36view0turn36view1turn36view2 | GPL-3 | CRAN + GitHub/r-lib | `assert_that()`, `validate_that()`, `on_failure()` | Yes, by putting checks inside methods | Yes; `validate_that()` is explicitly easier to use in S4 validate methods | Fine for ordinary boundary checks; slower than `qassert()` in the published checkmate benchmark | `assert_that(is.numeric(x), length(x) == 1)` | Current and widely used; simple and stable API |
| `checkmate` citeturn39search0turn34view0turn33view2turn33view3turn33view4turn30view0 | BSD_3_clause + file LICENSE | CRAN + GitHub | `assert_*`, `check_*`, `test_*`, `expect_*`, plus DSL `qassert()` | Yes; native `checkR6()` support | Yes, and works well in package code and tests | Best published runtime and memory results among compared packages; substantial code in C | `assert_numeric(x, any.missing = FALSE, lower = 0)` | Mature, current, and the best default for hot paths |
| `chk` citeturn39search18turn37view0turn37view1 | MIT | CRAN + GitHub | `chk_*` for fail-fast checks and `vld_*` for boolean validation | Yes, by method-body use | Yes, as ordinary functions in methods | Designed to be simple, customizable, fast, and pipe-friendly | `chk_number(x)` or `x |> chk_not_null()` | Stable lifecycle; current and focused |
| `assertions` citeturn7view3turn32view0 | MIT in repo / current CRAN package | CRAN + GitHub | Generic `assert()`, many `assert_*`, `assert_create()` / `assert_create_chain()` | Yes, by method-body use | Yes, via ordinary functions and custom wrappers | Ergonomics-first; no published benchmark located in reviewed sources | `assert_number(x, msg = "Please supply a number!")` | Active, but README marks lifecycle as experimental |
| `valaddin` citeturn7view4turn6search3turn35view0turn35view2turn35view3 | MIT + file LICENSE | CRAN + GitHub | `firmly()`, `%checkin%`, formula-based checks, reversible with `loosely()` | Yes, but by wrapping method functions manually | Yes, for ordinary functions and methods | Wrapper/formula evaluation adds overhead; useful where retrofitting matters more than absolute speed | `firmly(f, ~is.numeric)` | Current, niche, and intentionally focused on input validation |
| `assertr` citeturn39search20turn38view0turn38view1turn38view2 | MIT + file LICENSE | CRAN + GitHub | Pipeline verbs: `verify()`, `assert()`, `insist()`, `assert_rows()` | Limited relevance; manual only | Limited relevance; mainly data-frame workflows | Cost scales with data scans and row/column predicates; not intended as a generic function-contract engine | `df %>% verify(nrow(.) > 0)` | Current, but domain-specific to data pipelines |
| `precondition` citeturn10view0turn9search0turn39search17 | License not visible in reviewed excerpts | Archived from CRAN; GitHub mirror exists | Explicit `precondition()`, `postcondition()`, `sanity_check()`, debug markers | Yes, by method-body use | Yes, by ordinary use inside methods | Rich diagnostics, but expressions may be evaluated more than once | `precondition("x positive", {x} > 0)` | Conceptually strong, but archived from CRAN in 2026 |
| `ensurer` citeturn27search0turn28view0turn27search6 | MIT + file LICENSE | Archived from CRAN; GitHub mirror exists | `ensure_that()` and reusable `ensures_that()` contracts | Yes, by method-body use | Yes, by ordinary use inside methods | Lightweight and readable, especially with pipes; no current CRAN support | `x %>% ensure_that(is.numeric(.))` | Historically useful, but archived from CRAN in 2024 |
| `dbc` citeturn20view0turn21view0turn19view3 | MIT + file LICENSE | GitHub only | Many generated `assert_is_*` helpers; optional `assertion_type` | Yes, by method-body use | Yes, by ordinary use inside methods | No published benchmark found in reviewed sources; appears aimed at production/internal usage modes | `dbc::assert_is_data_frame_with_required_names(...)` | Active on GitHub, with a 2026 release, but not on CRAN |

The main legacy system worth understanding historically is **assertive**. It aimed to make code very readable, offered a huge family of `is_*` and `assert_*` helpers, explicitly distinguished runtime assertions from unit tests, and produced unusually detailed failure reports. That same diagnostic richness is also why it performed poorly in the published benchmark against `checkmate`. Today, however, `assertive` and `assertive.base` are both archived from CRAN, so they are better treated as design references than as default dependencies for new work. citeturn26view0turn23search0turn23search1turn31view0

Two simpler secondary packages are also relevant. **assert** is a lightweight alternative to `stopifnot()` and `assert_that()` for validating function arguments and analysis scripts, while **checkarg** focuses on concise and readable argument checking and can combine checking with default assignment. Both are useful to know, but neither has the combination of maturity, test integration, documentation breadth, and current mindshare that makes `checkmate`, `chk`, `assertthat`, or `assertions` the stronger general recommendations. citeturn27search4turn22view0

## Integration with functions, S3, S4, and R6

For ordinary functions, the cleanest R contract pattern is still the classic one: assert inputs at the very start of the function, compute the result, and assert only the result properties that form part of the function’s real contract. This is exactly the niche `stopifnot()` was designed for, but packages such as `assertthat`, `checkmate`, `chk`, and `assertions` improve message quality, consistency, and composability. `assertthat` is especially close to a direct `stopifnot()` replacement, while `checkmate` exposes a family split into checking, asserting, testing, and expectation functions. citeturn29search0turn13search10turn18search3turn39search0turn33view2

A typical modern package-level pattern is to put **boundary checks** on all exported functions and keep deeper internal helpers lighter. This improves failure locality without turning every helper into a wall of repetitive validation. Packages like `chk` and `checkmate` support that style well because they are terse and focused on developer-facing API boundaries, while `assertions` works well when you want deliberately polished user-facing messages. citeturn39search18turn39search0turn32view0

The following example shows a balanced boundary-plus-result contract in a plain function:

```r
scale01 <- function(x) {
  checkmate::assert_numeric(x, any.missing = FALSE, min.len = 1)
  rng <- range(x)
  checkmate::assert_true(rng[1] < rng[2])

  out <- (x - rng[1]) / (rng[2] - rng[1])

  # Postcondition: documented promise of this function
  checkmate::assert_numeric(out, any.missing = FALSE, lower = 0, upper = 1)
  out
}
```

That style matches `checkmate`’s defensive-programming orientation and keeps the precondition/postcondition distinction explicit even though the package does not name them that way. citeturn39search0turn30view0

For **S3**, there is no special contract mechanism to learn: S3 methods are ordinary functions selected through `UseMethod()`, so the same assertion packages can be used inside any `generic.class` method. The design question is not technical compatibility but whether the contract belongs on the generic, the method, or both. In practice, generic-level checks should validate arguments common to all methods, and method-level checks should validate class-specific assumptions. citeturn16search3turn16search1

For **S4**, there is a native answer: `setValidity()` / `validObject()`. A validity method returns `TRUE` for a valid object or a character vector describing invalidity; `validObject()` accumulates those errors. This is a better fit than ad hoc runtime contracts for invariants that belong to the class definition itself. `assertthat::validate_that()` is explicitly documented as useful in S4 validate methods because it returns a character vector rather than throwing immediately. citeturn16search2turn16search4turn16search0turn36view0

A concise S4 pattern looks like this:

```r
setClass(
  "ProbVector",
  slots = c(x = "numeric"),
  validity = function(object) {
    assertthat::validate_that(
      length(object@x) > 0,
      all(!is.na(object@x)),
      all(object@x >= 0),
      abs(sum(object@x) - 1) < 1e-8,
      msg = "`x` must be a non-missing probability vector summing to 1"
    )
  }
)
```

That pattern fits S4 particularly well because the contract becomes part of the class rather than being repeated across constructors and mutators. citeturn16search2turn16search4turn36view0

For **R6**, the situation is different. R6 emphasizes reference semantics, public/private members, active bindings, and inheritance, but its documentation does not provide an S4-like built-in validity protocol. The practical implication is simple: put checks in `initialize()`, in every state-mutating method, and optionally in active bindings if they expose writable state. Where you need to validate that an incoming object really is an R6 instance with specific public/private members, `checkmate::checkR6()` is the only reviewed package with an explicit R6-aware helper. citeturn15search0turn15search1turn33view4

An R6-friendly contract pattern looks like this:

```r
Counter <- R6::R6Class(
  "Counter",
  public = list(
    value = NULL,

    initialize = function(value = 0) {
      checkmate::assert_numeric(value, len = 1, any.missing = FALSE, lower = 0)
      self$value <- value
    },

    increment = function(n = 1) {
      checkmate::assert_numeric(n, len = 1, any.missing = FALSE, lower = 1)
      old <- self$value
      self$value <- self$value + n

      # Postcondition on mutated object state
      checkmate::assert_true(self$value >= old)
      invisible(self)
    }
  )
)
```

This pattern is usually preferable to decorating R6 methods dynamically because it keeps the class contract visible where the mutation happens. citeturn15search1turn33view4turn39search0

If you prefer **decorator-like retrofitting** rather than editing function bodies, `valaddin` is unusual and useful. `firmly()` transforms an existing closure into one with input validation, `%checkin%` keeps checks adjacent to the function, and `loosely()` can recover the original underlying function. The package is explicitly oriented toward **input validation**, not general postconditions. citeturn7view4turn35view0turn35view2turn35view3

```r
safe_log <- valaddin::firmly(log, ~is.numeric, ~{. > 0})
safe_log(1:3)
```

For **tidyverse-style code**, the most natural options are `assertr` for data pipelines, `valaddin` for formula-based wrappers, `assertions` for `cli`-styled messages, and `precondition` for `rlang`-style bullet diagnostics. `assertthat` also lives comfortably in that ecosystem because it comes from the same developer tradition and supports custom failure messages directly. citeturn38view0turn35view0turn32view0turn10view0turn13search11

## Runtime cost and checking model

The most useful published benchmark remains Michel Lang’s **R Journal** paper on **checkmate**. It compared `checkmate::assertNumeric()` and `qassert()` with `base::stopifnot()`, `assertthat::assert_that()`, and `assertive` for the contract “numeric, non-missing, non-negative.” On a valid scalar numeric input, `qassert()` was fastest, `assertNumeric()` was close behind, `stopifnot()` was somewhat slower, `assertthat` was about **5× slower than `qassert()`**, and `assertive` was **more than 70× slower**. On a valid vector of length `1e6`, `checkmate` was roughly **3.5× faster** than `stopifnot()` and `assert_that()`, and `assertive` was **more than 1200× slower**. On a `1e6` vector whose first element was missing, `checkmate` gained even more from early stopping: about **25× faster** than base R and `assertthat`, and about **7000× faster** than `assertive`. citeturn31view0

The paper also reported memory use for `x = runif(1e7)`. A no-op script used about **105 MB**; loading `checkmate` and running the assertion left memory essentially unchanged at about **105 MB**; the equivalent base-R and `assertthat` assertions used about **185 MB**; and `assertive` used about **1602 MB**. The explanation given in the paper is architectural: `checkmate` avoids creating intermediate logical vectors for common checks and instead loops directly over SEXPs in compiled code. citeturn31view0turn7view0

A compact way to read the benchmark is this:

```text
Relative runtime from the published checkmate benchmark
(lower is better; qassert/checkmate baseline = 1)

Valid scalar numeric:
qassert        1
assertNumeric  ~1
stopifnot      >1
assert_that    ~5
assertive      >70

Valid vector, length 1e6:
checkmate      1
stopifnot      ~3.5
assert_that    ~3.5
assertive      >1200

Missing value in first element, length 1e6:
checkmate      1
stopifnot      ~25
assert_that    ~25
assertive      ~7000
```

These results are from older package versions and an older R release, so they should not be read as exact 2026 timings. They are still analytically useful because the key drivers they test—compiled loops, early exit, and avoiding intermediate allocations—are stable design properties, and current `checkmate` still advertises that a substantial part of the package is written in C to minimize execution-time worries. citeturn31view0turn39search0

For the rest of the ecosystem, benchmark evidence is much thinner, so the best one can do is infer from API design. `chk` is designed to be simple, fast, and pipe-friendly, and returns the original object on success, which makes it attractive for boundary checks in modern package code. `assertr` necessarily pays the cost of scanning selected rows or columns. `valaddin` adds wrapper and formula-evaluation overhead but buys incremental adoption. `precondition` explicitly warns that assertion expressions can be evaluated more than once, so side effects and expensive expressions are a poor fit. citeturn39search18turn38view0turn35view0turn10view0

Base R is still the baseline. `stopifnot()` is intended for regression tests and function argument checking, and since R 3.6.0 it uses less overhead because it no longer wraps each expression in extra condition handling. If you need **zero dependencies** and your contracts are simple, `stopifnot()` is still respectable. The trade-off is message quality and extensibility. citeturn29search0

On **static vs runtime checking**, the reviewed contract packages are overwhelmingly runtime tools. They validate values after dispatch, at call time, or after computation. Static tools such as **lintr** and **codetools** analyze source code without executing it, and experimental efforts such as **typeChecker** add some form of static type reasoning, but none of these gives you true runtime postconditions over arbitrary R values. In other words, static analysis and contracts in R are complementary, not competing. citeturn17search5turn17search1turn17search12

## Testing, debugging, readability, and maintainability

The cleanest way to think about contracts and tests in R is that they solve different problems. A contract checks assumptions **during execution** and fails close to the point of misuse. A unit test checks expected behavior **during development and CI**. `ensurer` makes this distinction explicit, stating that it is not a substitute for `testthat`, and the `assertive` README also distinguishes runtime assertions from development-time tests. citeturn28view0turn26view0

The testing ecosystem integrates well with contract usage. `testthat` encourages custom expectations, and `checkmate` goes further by exposing many `expect_*` helpers and even a test backend registration mechanism. `covr` is framework-agnostic and measures line coverage for both R and compiled code, making it useful for ensuring you exercise both valid and invalid contract paths. citeturn14search14turn14search2turn33view3turn12view3turn14search5turn14search17

Error reporting differs substantially across packages, and that difference has real maintainability consequences. **checkmate** deliberately chooses concise messages and early exit, prioritizing speed and sane program flow over per-element reports. **assertthat** improves friendliness over `stopifnot()` and supports custom failure messages through `msg` and `on_failure()`. **assertions** focuses heavily on user-friendly, stylable messages through `cli` and easy custom assertion creation. **precondition** goes furthest on diagnostics, with custom bullet messages, explicit pre/post/sanity semantics, and debug markers that can expose intermediate values in assertion failures. **assertive** historically provided the richest report-like messages, but that richness was one reason it was much slower. citeturn31view0turn36view1turn36view3turn32view0turn10view0turn26view0

This matters for debugging ergonomics. If your primary problem is **rapid diagnosis by package maintainers**, concise fail-fast checks are often enough and can be substantially cheaper. If your primary problem is **actionable error messages for less technical users**, investing in custom messages, condition classes, and perhaps more descriptive contract wrappers pays off. In modern R-package practice, `rlang::abort()` is especially useful because it supports structured bullet-style errors and condition metadata, while `testthat` can then assert on condition class rather than brittle exact message text. citeturn13search2turn13search11turn14search2

Used well, contracts can improve readability and maintainability because they act as **executable documentation**. Base R itself says `stopifnot()` can make argument checking easier to read; `assertive` explicitly describes readability as a goal; and `checkarg` frames readability as part of robustness. The catch is “used well”: contracts improve maintenance when they are standardized, local, and meaningful. They hurt maintenance when they are ad hoc, duplicated, inconsistent across files, or packed with low-value checks that obscure the business logic. citeturn29search0turn26view0turn22view0

A useful pattern for serious packages is to define a very small internal assertion layer—functions like `req_flag()`, `req_nonempty_df()`, or `req_prob_vector()`—backed by your chosen package. `assertions::assert_create()` is designed to help you build those wrappers, and `checkmate::makeAssertCollection()` can help aggregate multiple failures in a controlled way. That gives you stable, domain-specific contracts while decoupling the rest of the codebase from a specific assertion package’s surface syntax. citeturn32view0turn33view2

## Adoption patterns, migration, and antipatterns

For **new package code**, the best default recommendation is:

- use **checkmate** if you want the strongest combination of performance, breadth, and test integration; citeturn39search0turn31view0
- use **chk** if you want a lighter, pipe-friendly, modern developer API with fewer concepts; citeturn39search18turn37view0
- use **assertthat** or **assertions** if your team values message ergonomics and low ceremony above raw speed; citeturn18search3turn32view0
- use **assertr** only when the contract is really a data quality assertion over a pipeline; citeturn38view0turn38view1
- use **S4 validity** for S4 class invariants and ordinary method-body checks for **R6**. citeturn16search2turn16search4turn15search1

For **existing codebases**, the lowest-risk migration path is incremental. First, inventory all uses of `stopifnot()`, manual `if (!cond) stop(...)`, and archived packages. Second, pick one primary package and build a tiny internal adapter layer. Third, migrate only exported functions, constructors, S4 validity methods, and R6 mutators first. Fourth, add explicit tests for failure paths and inspect coverage with `covr`. Finally, profile only after contracts are in place; if a hotspot appears, downgrade that hotspot to a cheaper assertion style or a coarser contract boundary. citeturn29search0turn23search0turn27search0turn39search17turn14search5turn14search17

If packages are unavailable or you want a dependency-light house style, lightweight decorators are easy to write. The key best practice is to signal **structured** errors, ideally with `rlang::abort()`, so tests can match on class and callers can handle contract failures programmatically. citeturn13search11turn14search2

```r
abort_contract <- function(message, class = "contract_error") {
  if (requireNamespace("rlang", quietly = TRUE)) {
    rlang::abort(message, class = c(class, "error"))
  } else {
    stop(message, call. = FALSE)
  }
}

with_contract <- function(f, pre = NULL, post = NULL) {
  force(f)
  force(pre)
  force(post)

  function(...) {
    args <- list(...)

    if (!is.null(pre)) {
      pre_ok <- pre(args)
      if (!isTRUE(pre_ok)) {
        abort_contract(
          if (is.character(pre_ok)) pre_ok else "Precondition failed",
          class = "precondition_error"
        )
      }
    }

    value <- f(...)

    if (!is.null(post)) {
      post_ok <- post(value, args)
      if (!isTRUE(post_ok)) {
        abort_contract(
          if (is.character(post_ok)) post_ok else "Postcondition failed",
          class = "postcondition_error"
        )
      }
    }

    value
  }
}

safe_divide <- with_contract(
  function(x, y) x / y,
  pre = function(args) {
    if (!is.numeric(args$x) || length(args$x) != 1) return("`x` must be numeric scalar")
    if (!is.numeric(args$y) || length(args$y) != 1) return("`y` must be numeric scalar")
    if (isTRUE(args$y == 0)) return("`y` must be non-zero")
    TRUE
  },
  post = function(value, args) {
    if (!is.numeric(value) || length(value) != 1 || is.na(value)) {
      return("result must be a non-missing numeric scalar")
    }
    TRUE
  }
)
```

That decorator is intentionally simple, but it already covers the most important contract behaviors: fail-fast preconditions, explicit postconditions, and testable error classes. citeturn13search11turn14search2

A small R6-specific helper can also keep method checks readable:

```r
contract <- function(expr, msg = deparse(substitute(expr))) {
  if (!isTRUE(expr)) stop(msg, call. = FALSE)
  invisible(TRUE)
}

Account <- R6::R6Class(
  "Account",
  public = list(
    balance = NULL,
    initialize = function(balance = 0) {
      contract(is.numeric(balance) && length(balance) == 1 && !is.na(balance),
               "`balance` must be a non-missing numeric scalar")
      contract(balance >= 0, "`balance` must be non-negative")
      self$balance <- balance
    },
    deposit = function(amount) {
      contract(is.numeric(amount) && length(amount) == 1 && !is.na(amount),
               "`amount` must be a non-missing numeric scalar")
      contract(amount > 0, "`amount` must be positive")
      old <- self$balance
      self$balance <- self$balance + amount
      contract(self$balance >= old, "balance must not decrease after deposit")
      invisible(self)
    }
  )
)
```

For teams that want postconditions with richer diagnosis, the archived `precondition` package is still an excellent design reference: it distinguishes preconditions, postconditions, and sanity checks explicitly, supports diagnostics through debug markers, and documents its failure semantics carefully. If you do not want to depend on an archived package, emulating its concepts with lightweight wrappers like the above is often the right compromise. citeturn10view0turn39search17

The main **antipatterns** are consistent across packages. Do not put expensive whole-object postconditions inside tight inner loops when one boundary check would do. Do not write contract expressions with side effects, especially with tools like `precondition` that may evaluate expressions more than once. Do not use runtime contracts as a substitute for unit tests. Do not bind a new codebase to archived packages unless you are prepared to vendor them or absorb maintenance yourself. And do not let every file invent its own assertion idiom; inconsistency is one of the fastest ways for contracts to reduce readability instead of improving it. citeturn10view0turn31view0turn28view0turn23search0turn27search0turn39search17

A short adoption checklist for a production R codebase is:

- standardize on one primary assertion style and hide it behind a tiny internal wrapper layer; citeturn32view0turn33view2
- put preconditions on exported functions, constructors, and R6 mutators first; citeturn15search1turn16search2
- reserve postconditions for non-obvious semantic guarantees, not every trivial helper; citeturn10view0turn31view0
- test both success and failure paths with `testthat`, and track them with `covr`; citeturn14search14turn14search5turn14search17
- avoid archived packages for greenfield work unless you have a deliberate support plan. citeturn23search0turn27search0turn39search17

The bottom line is that design by contract is very workable in R, but the best implementation depends on what you value most. If the priority is **speed and package engineering**, choose **checkmate** or **chk**. If it is **ergonomic messaging**, choose **assertthat** or **assertions**. If it is **retrofitting** existing closures, choose **valaddin**. If it is **data-pipeline validation**, choose **assertr**. If it is **formal class invariants**, prefer **S4 validity** for S4 classes and disciplined method-body checks for **R6**. citeturn39search0turn39search18turn18search3turn32view0turn7view4turn38view0turn16search2turn15search1