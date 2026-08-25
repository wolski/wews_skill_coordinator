# Performance And Memory

Read this when R code is slow, memory-heavy, or a hot path is suspected. The first rule is
measure before changing anything — do not rewrite hot paths on intuition.

## Start with measurement

```r
tmp <- tempfile()
Rprof(tmp, memory.profiling = TRUE)
result <- slow_call()
Rprof(NULL)
summaryRprof(tmp, memory = "both", lines = "show")
unlink(tmp)
```

- Use `profvis` for interactive profiling when available.
- Use `tracemem()` to investigate copying.
- Use `Rprofmem()` for allocation-heavy paths.

## Common improvements

- Replace `apply(x, 1, sum)` with `rowSums(x)`.
- Replace `apply(x, 2, mean)` with `colMeans(x)`.
- Replace repeated `c()`, `rbind()`, `cbind()`, `append()`, or `paste0()` growth inside
  loops with preallocation or list accumulation.
- Move invariant work out of loops.
- Prefer vectorized subsetting and assignment when it keeps the code clear.
- Use `data.table` deliberately for large tabular hot paths, but document and test
  by-reference mutation.
- Parallelize only when task size amortizes cluster startup, export, scheduling, and
  aggregation overhead.

## Validate at the boundary, not in the loop

Input validation and contract checks belong once at the function boundary, never inside a
hot vectorized loop — per-element assertions quietly defeat vectorization. Pay the check
once on entry, then trust the data on the fast path.

## data.table: decide whether mutation is allowed

Make by-reference mutation an explicit, documented choice — not an accident the caller
discovers.

```r
mutate_in_place <- function(dt) {
  dt[, score := value / max(value)]
  invisible(dt)
}

mutate_copy <- function(dt) {
  dt <- data.table::copy(dt)
  dt[, score := value / max(value)]
  dt
}
```
