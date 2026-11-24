# R-package review

Over 20–23 Nov you ran three skill-based review rounds on prolfqua: one with the tidyverse skills, then two rOpenSci self-review rounds. All ran in Claude Code; Codex ran none.

| Date | Review | Skills (one agent each) | Output |
|---|---|---|---|
| 20 Nov | Tidy-skills review | `tidy-r`, `tidyverse-style`, `ggplot2`, plus a merging agent | [TODO_tidy_skills_review.md](/Users/wolski/projects/prolfqua_fml/TODO/prolfqua/Archive/TODO_tidy_skills_review.md) |
| 21 Nov | rOpenSci round 1 | `run-test-audit`, `run-dependency-review`, `run-complexity`, `run-performance-review`, plus a consolidating agent | 4 reports in [ropensci_self_review/](/Users/wolski/projects/prolfqua_fml/TODO/prolfqua/ropensci_self_review/) → [V1 TODO](/Users/wolski/projects/prolfqua_fml/TODO/prolfqua/Archive/TODO_ropensci_self_review_V1.md) |
| 22 Nov | rOpenSci round 2 | Same four, plus `run-package-review` (with pkgcheck) and a statistical-standards pass (`stats-standards-compliance`, `stats-standards`), plus a merging agent | 6 reports in [round2/](/Users/wolski/projects/prolfqua_fml/TODO/prolfqua/ropensci_self_review/round2/) → [V2 TODO](/Users/wolski/projects/prolfqua_fml/TODO/prolfqua/Archive/TODO_ropensci_self_review_V2.md) |

Follow-up work:

- Tidy-skills review: plan items B, C and D carried out on 21 Nov
- Round 1 findings: waves 1–3, 22 Nov
- Round 2 findings: waves 4–5, 23 Nov
- Wave-4 decisions: walked through one by one with `interview-to-spec`

Related work that wasn't a skill review run:

- 15 Nov: statistical-standards compliance estimate by a plain agent, without the rOpenSci skills, which were installed the next night → [srr_compliance_estimate.tsv](/Users/wolski/projects/prolfqua_fml/TODO/prolfqua/srr_compliance_estimate.tsv), [TODO_ropensci_compliance.md](/Users/wolski/projects/prolfqua_fml/TODO/prolfqua/TODO_ropensci_compliance.md)
- 17 Nov: `peer-review-author` and `stats-standards` loaded to plan the compliance blocks A–H
- 18 Nov: a plain agent reviewed two TODO documents, no skill
- 20 Nov: the same three tidy skills reviewed prolfquapp → [TODO_review_tidy_ggplot.md](/Users/wolski/projects/prolfqua_fml/TODO/prolfquapp/TODO_review_tidy_ggplot.md)

Never used: `package-release`, `package-maintenance`, `blog-post`.

How I checked: I scanned the Claude session logs since 9 Nov, including subagent logs, for skill calls, agent launches and report files. Almost all of the review work is in sessions `578c3df0` and `798279d1`. The five Codex sessions in prolfqua_fml on 17 Nov were carrying out plans. From how often the skill paths appear in their logs, they probably opened `package-standards` and `stats-standards` (inferred), but they ran no review.

## Suggested review bundles

Five bundles of review skills, suggested on 24 Nov for bringing prozor up to date. Each bundle runs one agent per skill, then one merging agent that turns the reports into a TODO.

| # | Bundle | Skills | Covers |
|---|---|---|---|
| A | CRAN health | `r-cran-status`, `r-cran-extrachecks` (Posit); `package-maintenance`, `package-release` (rOpenSci) | Live CRAN state and deadlines, CRAN rules that `R CMD check` misses, maintainer and release process |
| B | Tests | `review-testing` (Posit); `run-test-audit` (rOpenSci) | Test quality and coverage gaps; for a package without tests, a test plan. Run before any refactoring |
| C | Code and design | `critical-code-reviewer` (Posit); `run-complexity`, `run-dependency-review`, `run-performance-review` (rOpenSci) | Correctness, complexity, dependencies, hot paths |
| D | Standards and style | `package-standards` (rOpenSci); `r-tidyverse-style` (Posit) | DESCRIPTION, README, docs, CI setup, style |
| E | Tidy-skills review | `tidy-r`, `tidyverse-style`, `ggplot2` (profile `tidy-r`) | Modern tidyverse idioms (native pipe, `join_by()`, `.by`, tidyselect), tidyverse style guide, ggplot2 plots. Run on prolfqua and prolfquapp on 20 Nov |

Order: A → B → C → D → E, then a final round with `run-package-review` (including pkgcheck) to check the fixes and catch what the bundles missed, like prolfqua's round 2. A comes first because it is the fastest win and keeps the package on CRAN.

Running a bundle:

- Prerequisites: the workspace Makefile and an `AGENTS.md` in the package, since review agents run `make test` and `make check`
- Run `R CMD check --as-cran` once beforehand and give all agents the log, instead of four parallel checks
- Subagents may not write files: they return their report as text, and the main session saves it as `REPORT_<skill>.md`
- Reports and the merged TODO go to `TODO/<package>/`
- Posit's `r-testthat` is in the active `posit` profile; use it to write tests before bundle B, and to act on its findings
- Bundle B: run the test suite and `covr` once beforehand and give both agents the logs; the reviewers do mutation testing on a scratch copy of the repository, never on the working tree

Used so far:

- 24 Nov, prozor, bundle A: 4 reports and [TODO_cran_health.md](/Users/wolski/projects/prolfqua_fml/TODO/prozor/TODO_cran_health.md); work packages WP1–WP3 fixed and pushed the same day. This was the first use of `package-release` and `package-maintenance`.
- 24 Nov, prozor, bundle B: 2 reports and [TODO_tests.md](/Users/wolski/projects/prolfqua_fml/TODO/prozor/TODO_tests.md), on the test suite written the same day with `r-testthat`. Both reviewers used mutation testing on their own; 18 of 33 relevant mutants survived, and their probes found 3 bugs that coverage alone would not have shown. First use of `review-testing` and `run-test-audit`.
