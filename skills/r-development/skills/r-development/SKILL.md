---
name: r-development
description: >
  This skill should be used when the user asks to "write R code", "create an R script",
  "analyze data in R", "use dplyr", "use tidyverse", "optimize R performance",
  "write a ggplot", "use purrr", "help with rlang", or "wrangle data in R". Also use
  this skill whenever the user is working with .R, .Rmd, .qmd, or .Rproj files, mentions
  R packages like dplyr, tidyr, ggplot2, purrr, stringr, or lubridate, or needs guidance
  on tidyverse patterns, native pipe, data wrangling, or R metaprogramming — even if they
  do not explicitly say "R development". Covers modern tidyverse (dplyr 1.1+, native pipe,
  join_by, .by), rlang metaprogramming, ggplot2, purrr, stringr, performance optimization,
  and R object systems. For devtools workflow, testing with testthat, roxygen2
  documentation, and NEWS.md conventions, defer to the r-package-development skill instead.
---

# R Development

Follow these guidelines when writing or reviewing R code. Prioritize modern tidyverse patterns (dplyr 1.1+), native pipe, explicit namespacing, and performance-aware practices.

## Core Principles

1. **Use modern tidyverse patterns** — Prefer dplyr 1.1+ features, native pipe, and current APIs
2. **Profile before optimizing** — Use profvis and bench to identify real bottlenecks
3. **Write readable code first** — Optimize only when necessary and after profiling
4. **Follow tidyverse style guide** — Consistent naming, spacing, and structure
5. **Use explicit namespacing** — Write `package::function()` (e.g., `dplyr::filter()`, `stringr::str_detect()`). Never rely on `library()` calls. This makes code self-documenting about where each function comes from and avoids namespace conflicts
6. **No `\dontrun{}` in examples** — All roxygen2 `@examples` must be runnable. Never wrap examples in `\dontrun{}` — this hides broken code from `R CMD check`. If an example needs external resources, use `\donttest{}` instead or make the example self-contained

## Modern Tidyverse Essentials

### Native Pipe (`|>` not `%>%`)

Use native pipe `|>` instead of magrittr `%>%` (R 4.1+):

```r
# Modern
data |>
  dplyr::filter(year >= 2020) |>
  dplyr::summarise(mean_value = mean(value))

# Avoid legacy pipe
data %>% dplyr::filter(year >= 2020)
```

### Join Syntax (dplyr 1.1+)

Use `dplyr::join_by()` for all joins:

```r
# Equality join
transactions |>
  dplyr::inner_join(companies, by = dplyr::join_by(company == id))

# Inequality join
transactions |>
  dplyr::inner_join(companies, dplyr::join_by(company == id, year >= since))

# Rolling join (closest match)
transactions |>
  dplyr::inner_join(companies, dplyr::join_by(company == id, closest(year >= since)))
```

Control match behavior:

```r
# Expect 1:1 matches
dplyr::inner_join(x, y, by = dplyr::join_by(id), multiple = "error")

# Ensure all rows match
dplyr::inner_join(x, y, by = dplyr::join_by(id), unmatched = "error")
```

### Per-Operation Grouping with `.by`

Use `.by` instead of `dplyr::group_by() |> ... |> dplyr::ungroup()`:

```r
# Modern approach (always returns ungrouped)
data |>
  dplyr::summarise(mean_value = mean(value), .by = category)

# Multiple grouping variables
data |>
  dplyr::summarise(total = sum(revenue), .by = c(company, year))
```

### Column Operations

Use modern column selection and transformation:

```r
# pick() for column selection in data-masking contexts
data |>
  dplyr::summarise(
    n_x_cols = ncol(dplyr::pick(starts_with("x"))),
    n_y_cols = ncol(dplyr::pick(starts_with("y")))
  )

# across() for applying functions to multiple columns
data |>
  dplyr::summarise(
    dplyr::across(where(is.numeric), mean, .names = "mean_{.col}"),
    .by = group
  )

# reframe() for multi-row results per group
data |>
  dplyr::reframe(quantiles = quantile(x, c(0.25, 0.5, 0.75)), .by = group)
```

### Data Reshaping

Use `tidyr::pivot_longer()` and `tidyr::pivot_wider()` for reshaping:

```r
# Wide to long
data |>
  tidyr::pivot_longer(
    cols = starts_with("year_"),
    names_to = "year",
    names_prefix = "year_",
    values_to = "value"
  )

# Long to wide
data |>
  tidyr::pivot_wider(
    names_from = category,
    values_from = value,
    values_fill = 0
  )
```

## Reading and Writing Data

Use readr for text-based formats and readxl for Excel:

```r
data <- readr::read_csv("data.csv")
readr::write_csv(data, "output.csv")

# Excel files
data <- readxl::read_excel("data.xlsx", sheet = "Sheet1")

# R-native format for intermediate results
readr::write_rds(data, "cached.rds")
data <- readr::read_rds("cached.rds")
```

## String Operations

Prefer stringr for consistent, pipe-friendly string manipulation:

```r
text |>
  stringr::str_to_lower() |>
  stringr::str_trim() |>
  stringr::str_replace_all("old", "new")

# Pattern matching
stringr::str_detect(text, "pattern")
stringr::str_extract_all(text, "\\d+")

# String interpolation
stringr::str_glue("Column {col} has {n} values")
```

## Functional Programming with purrr

Use type-stable map variants and modern purrr 1.0+ patterns:

```r
# Type-stable mapping
purrr::map_dbl(data_list, \(df) mean(df$value))
purrr::map_chr(data_list, \(df) df$name[[1]])

# Row-binding results (purrr 1.0+, replaces map_dfr)
results <- data_splits |>
  purrr::map(\(split) process(split)) |>
  purrr::list_rbind()

# Walking for side effects
purrr::walk2(plots, filenames, \(p, f) ggplot2::ggsave(f, p))

# Safely handling errors
safe_read <- purrr::safely(readr::read_csv)
results <- purrr::map(file_paths, safe_read)
successes <- purrr::map(results, "result") |> purrr::compact()
```

## ggplot2 Essentials

Build plots with the layered grammar of graphics:

```r
data |>
  ggplot2::ggplot(ggplot2::aes(x = year, y = value, color = group)) +
  ggplot2::geom_point() +
  ggplot2::geom_smooth(method = "lm") +
  ggplot2::facet_wrap(~category) +
  ggplot2::labs(title = "Title", x = "Year", y = "Value") +
  ggplot2::theme_minimal()
```

Apply consistent theming across an analysis by defining a custom theme function or setting `ggplot2::theme_set()` at the top of the script. Use `ggplot2::ggsave()` to export plots with explicit dimensions and DPI.

## rlang Metaprogramming

For comprehensive rlang patterns, see [references/rlang-patterns.md](references/rlang-patterns.md).

### Quick Reference

- **`{{}}`** — Forward function arguments to data-masking functions
- **`!!`** — Inject single expressions or values
- **`!!!`** — Inject multiple arguments from a list
- **`.data[[]]`** — Access columns by name (character vectors)
- **`dplyr::pick()`** — Select columns inside data-masking functions

Example function with embracing:

```r
my_summary <- function(data, group_var, summary_var) {
  data |>
    dplyr::summarise(mean_val = mean({{ summary_var }}), .by = {{ group_var }})
}
```

## Performance Optimization

For detailed performance guidance, see [references/performance.md](references/performance.md).

### Key Strategies

1. **Profile first**: Use `profvis::profvis()` and `bench::mark()`
2. **Vectorize operations**: Avoid loops when vectorized alternatives exist
3. **Use dtplyr**: For large data operations (lazy evaluation with data.table backend)
4. **Parallel processing**: Use `furrr::future_map()` for parallelizable work
5. **Memory efficiency**: Pre-allocate, use appropriate data types

```r
# Profile code
profvis::profvis({
  result <- data |>
    complex_operation() |>
    another_operation()
})

# Benchmark alternatives
bench::mark(
  approach_1 = method1(data),
  approach_2 = method2(data),
  check = FALSE
)
```

## Common Migration Patterns

### Base R to Tidyverse

```r
# Data manipulation
subset(data, condition)         # -> dplyr::filter(data, condition)
data[order(data$x), ]           # -> dplyr::arrange(data, x)
aggregate(x ~ y, data, mean)    # -> dplyr::summarise(data, mean(x), .by = y)

# Functional programming
sapply(x, f)                    # -> purrr::map(x, f)  (type-stable)
lapply(x, f)                    # -> purrr::map(x, f)

# Strings
grepl("pattern", text)          # -> stringr::str_detect(text, "pattern")
gsub("old", "new", text)        # -> stringr::str_replace_all(text, "old", "new")
```

### Old to New Tidyverse

```r
# Pipes
%>%                             # -> |>

# Grouping
group_by() |> ... |> ungroup()  # -> dplyr::summarise(..., .by = x)

# Joins
by = c("a" = "b")              # -> by = dplyr::join_by(a == b)

# Reshaping
gather() / spread()             # -> tidyr::pivot_longer() / tidyr::pivot_wider()
```

## Additional Resources

For detailed guidance beyond the essentials above, consult these reference files:

- **[references/rlang-patterns.md](references/rlang-patterns.md)** — Comprehensive data-masking and metaprogramming patterns including embracing, injection, dynamic dots, and pronouns
- **[references/performance.md](references/performance.md)** — Profiling with profvis, benchmarking with bench, vectorization, dtplyr for large data, and memory optimization
- **[references/package-development.md](references/package-development.md)** — API design patterns for tidyverse-style package functions: dependency strategy, input validation, error handling, and naming conventions. For devtools workflow, testing commands, roxygen2 documentation, and NEWS.md conventions, defer to the r-package-development skill
- **[references/object-systems.md](references/object-systems.md)** — S3, S4, S7, R6, and vctrs: decision matrix for choosing an object system, class definitions, and migration strategies
