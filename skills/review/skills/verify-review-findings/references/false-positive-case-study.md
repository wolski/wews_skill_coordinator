# Case study: a two-count false positive, and the structural fix

A real review finding from the `prolfqua` R package. It illustrates the full loop the `verify-review-findings` skill
prescribes: refute a finding empirically, classify it, find the genuine (smaller) bug it masked, and
restructure so the confusion that produced the false positive cannot recur.

## The finding as written

> `get_contrast()` resolves contrast sides positionally via `intersect()`.
> `sides <- intersect(.get_sides(contrast), colnames(data))` returns matches in *column* order, not contrast
> order, and silently drops a side whose name is absent (e.g. a typo'd level), producing a wrong/NA fold change
> with no error. **Fix:** preserve contrast-side order explicitly and `stop()` if either side is missing.

Two distinct claims: (A) wrong ordering; (B) silent drop of a missing level → wrong/NA result.

## The original code

```r
.get_sides <- function(contrast) {
  get_ast <- function(ee) purrr::map_if(as.list(ee), is.call, get_ast)
  ast_list <- get_ast(rlang::parse_expr(contrast))
  ast_array <- array(as.character(unlist(ast_list)))
  gsub("`", "", ast_array)
}

get_contrast <- function(data, hierarchy_keys, contrasts) {
  for (i in seq_along(contrasts)) {                       # LOOP 1: compute estimate
    data <- dplyr::mutate(data, !!names(contrasts)[i] := !!rlang::parse_expr(contrasts[i]))
  }
  res <- vector(mode = "list", length(contrasts))
  names(res) <- names(contrasts)
  for (i in seq_along(contrasts)) {                       # LOOP 2: extract the two sides
    sides <- .get_sides(contrasts[i])
    sides <- intersect(sides, colnames(data))             # <- the flagged line
    df <- dplyr::select(
      data, dplyr::all_of(hierarchy_keys),
      group_1 = dplyr::all_of(sides[1]),
      group_2 = dplyr::all_of(sides[2]),
      estimate = dplyr::all_of(names(contrasts)[i])
    )
    df$group_1_name <- sides[1]; df$group_2_name <- sides[2]
    df$contrast <- names(contrasts)[i]
    res[[names(contrasts)[i]]] <- df
  }
  dplyr::ungroup(dplyr::bind_rows(res))
}
```

## Refuting the finding (the five checks)

**Claim A — wrong ordering. REFUTED empirically.** Base R `intersect(x, y)` returns elements in the order of
its **first** argument. The flagged call passes the contrast-derived sides first, so contrast order is
preserved — the opposite of the claim.

```bash
Rscript -e 'print(base::intersect(c("group_A","-","group_B"), c("group_B","group_A")))'
#> [1] "group_A" "group_B"
```

`.get_sides("group_A - group_B")` returns `c("-", "group_A", "group_B")` — operators included. So `intersect`
is doing **double duty**: it drops the `"-"` token *and* keeps the order. Both correct.

**Claim B — silent drop → wrong/NA. REFUTED by reading the whole function.** A missing/typo'd level errors at
**LOOP 1** (`dplyr::mutate(... := !!rlang::parse_expr("group_A - group_Xyz"))` → `object 'group_Xyz' not
found`), long before LOOP 2 runs. It fails loud, once per contrast — never silently. Reading LOOP 2 in
isolation hid this.

**Reachability.** Callers trace only to the deprecated `ContrastsMissing` class; the numeric `estimate` is
computed independently in LOOP 1 and was always correct.

**Concrete failure.** None could be constructed for either claim. Both are false positives.

## The genuine bug the finding masked

For **composite/averaging** contrasts like `"(group_A + group_B)/2 - group_Ctrl"`, `.get_sides` yields more
than two group tokens; `sides[1]`/`sides[2]` take the first two (`group_A`, `group_B`) and ignore `group_Ctrl`.
The `estimate` stays correct, but `group_1`/`group_2` (consumed downstream for an average-abundance column) are
mislabeled. Narrow, real, and only on the deprecated path — but worth fixing.

This is the payoff of refuting carefully: the stated bug was wrong, yet the investigation surfaced the actual
defect, which a `stop()`-on-missing-side "fix" would have missed entirely.

## Why a competent reviewer misread it — the confusion smells

1. **Load-bearing non-obvious semantics, uncommented.** Correctness rode on `intersect`'s first-arg ordering —
   a detail widely assumed to go the other way — with no comment. `colnames(data)` as the second arg reads like
   the authoritative lookup table, inviting "column order."
2. **A helper doing double duty.** `.get_sides` returns operators mixed with names, so `intersect` silently
   strips operators *and* selects columns *and* fixes order. From the call site it looks like a membership
   lookup, which is what raised the order worry.
3. **Guards separated from the code they protect.** The missing-level guarantee lives in LOOP 1; the suspicious
   extraction in LOOP 2. The proof of safety was a loop away.

All three are the same root: correctness expressed through an opaque token list + `intersect`, instead of a
stated contract.

## The structural fix

A contrast is a difference `LHS - RHS`. State and enforce exactly that; evaluate each side directly.

```r
# Split a contrast "LHS - RHS" into its side expressions; NULL if not a binary minus.
.contrast_sides_expr <- function(contrast) {
  expr <- rlang::parse_expr(contrast)
  if (rlang::is_call(expr, "-") && length(expr) == 3L) {
    list(lhs = expr[[2]], rhs = expr[[3]], full = expr)
  } else {
    NULL
  }
}

get_contrast <- function(data, hierarchy_keys, contrasts) {
  res <- vector(mode = "list", length(contrasts))
  names(res) <- names(contrasts)
  for (i in seq_along(contrasts)) {
    cname <- names(contrasts)[i]
    sx <- .contrast_sides_expr(contrasts[i])
    if (is.null(sx)) {
      stop("get_contrast: contrast '", cname, "' (", contrasts[i],
           ") is not of the required form 'LHS - RHS'.", call. = FALSE)
    }
    # A level absent from `data` errors here at mutate -- once per contrast, not per row.
    dd <- dplyr::mutate(data, group_1 = !!sx$lhs, group_2 = !!sx$rhs, estimate = !!sx$full)
    df <- dplyr::select(dd, dplyr::all_of(hierarchy_keys), "group_1", "group_2", "estimate")
    df$group_1_name <- rlang::as_label(sx$lhs)
    df$group_2_name <- rlang::as_label(sx$rhs)
    df$contrast <- cname
    res[[cname]] <- df
  }
  dplyr::ungroup(dplyr::bind_rows(res))
}
```

What each smell-fix did:

- **Stated and enforced the contract** (`LHS - RHS`, error otherwise) — the precondition is now readable, and
  malformed input is rejected loudly instead of guessed at.
- **Removed the double-duty `intersect` and the operator-emitting `.get_sides`** (deleted; confirmed no other
  callers) — sides come straight from the parsed AST, correct for averaging contrasts too.
- **Collapsed two loops into one** — the missing-level guard now sits in the same statement that uses it.
- **No load-bearing comment needed** — the residual subtlety is gone, so the only comments explain *intent*,
  not *gotchas*.

Behavior for simple `A - B` contrasts is byte-identical (`lhs = quote(group_A)` →
`mutate(group_1 = group_A)` == old `select(group_1 = group_A)`).

## Lock it with tests

Test-first, including one test that **pins the behavior the reviewer misread** so it can never be re-flagged:

```r
test_that("get_contrast preserves contrast-side order for a simple contrast", {
  data <- tibble::tibble(protein_Id = c("p1","p2"), group_A = c(10,20), group_B = c(4,5))
  res <- suppressMessages(prolfqua::get_contrast(data, "protein_Id", c(AvsB = "group_A - group_B")))
  expect_equal(res$group_1, c(10, 20))   # locks the ordering the finding wrongly claimed was broken
  expect_equal(res$group_2, c(4, 5))
  expect_equal(res$estimate, c(6, 15))
})

test_that("get_contrast errors loudly when a contrast level is absent", {
  data <- tibble::tibble(protein_Id = "p1", group_A = 10)
  expect_error(suppressMessages(prolfqua::get_contrast(data, "protein_Id", c(bad = "group_A - group_Xyz"))))
})

test_that("get_contrast derives group_1/group_2 from the sides for averaging contrasts", {
  data <- tibble::tibble(protein_Id = c("p1","p2"), group_A = c(10,20), group_B = c(4,5), group_Ctrl = c(1,2))
  res <- suppressMessages(
    prolfqua::get_contrast(data, "protein_Id", c(x = "(group_A + group_B)/2 - group_Ctrl"))
  )
  expect_equal(res$group_1, c(7, 12.5))   # the real bug, now fixed
  expect_equal(res$group_2, c(1, 2))
})

test_that("get_contrast rejects a contrast that is not a difference 'LHS - RHS'", {
  data <- tibble::tibble(protein_Id = "p1", group_A = 1, group_B = 2)
  expect_error(
    suppressMessages(prolfqua::get_contrast(data, "protein_Id", c(bad = "group_A + group_B"))),
    "LHS - RHS"
  )
})
```

## The transferable lesson

1. A finding is a hypothesis. Refute it empirically — check the actual semantics, read the whole flow, trace
   reachability — before reporting.
2. A false positive triggered by confusing code is a real defect. Fix the confusion structurally: state the
   contract, kill double-duty cleverness, co-locate guards, delete dead fallbacks.
3. Careful refutation often surfaces the *real* bug the misread masked.
4. Lock both the fix and the previously-misread behavior with tests, so the next reviewer cannot repeat the
   misread.
