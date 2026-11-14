---
name: bioconductor-submission
description: >
  Prepare, submit and shepherd an R package through Bioconductor review: the go/no-go fit check,
  readiness checks (BiocCheck on the tarball, size and file limits, AI-use disclosure), the
  BiocContributions issue and bot, pushes to BiocStaging during review, point-by-point replies to
  reviewers, and the first pushes to git.bioconductor.org after acceptance. Use this skill whenever
  the user asks whether a package is "ready for Bioconductor" or "ready for Bioc", wants to submit or
  resubmit, mentions BiocCheck, BiocContributions, BiocStaging, git.bioconductor.org, BiocCredentials,
  a 0.99.z version bump, a Bioconductor build report, or a reviewer's comments on a submission issue,
  even if they only say "Bioc". Distilled from the 2026 reviews of prolfqua (#171, accepted),
  saintexpress (#170, withdrawn) and apbCatalogR (#261, accepted). Not for CRAN submissions or
  general R package development.
---

# Bioconductor submission

Distilled from three 2026 submissions:

- prolfqua #171: accepted 21 Oct after one review round, 54 days in total
- saintexpress #170: withdrawn 12 Nov over SummarizedExperiment
- apbCatalogR #261: accepted 12 Nov after two rounds, 9 days in total

Bioconductor rules change between cycles. When the bot messages on the issue contradict this file, follow the bot.

Phases:

0. Fit check: before any work
1. Readiness: "is it ready?"
2. Submit: opening the issue
3. Review: reviewer comments and build reports
4. Accepted: git.bioconductor.org and the release

## Ground rules

These come from Witold's corrections during the three reviews. Breaking each one cost a review round, a public mess, or his trust.

- **Ask before every push and every public post.** This covers:
  - pushes to BiocStaging and git.bioconductor.org;
  - comments on the submission issue, including `/accept-policies`;
  - posts on Zulip or bioc-devel.

  Name the remote, the branch and the commit range (`git push biocstaging main:devel`, `f015f97..bb1605f`), and wait for a yes at that moment. Approving a plan or a proposal does not approve the push. A wrong push cannot be undone: BiocStaging `devel` is protected and git.bioconductor.org refuses force-pushes. An unapproved push on saintexpress needed a revert release.
- **Dependencies are Witold's decision.** Never add Imports, Depends or Suggests to satisfy a reviewer without asking. On apbCatalogR, a dplyr rewrite done for a `for`-loop *Note* added 11 dependencies and made lookups 20× slower; it was reverted the next day.
- **Never cite our own packages as precedent** (prolfqua, prolfquapp, apbCatalogR …).
  - Cite released Bioconductor packages by other authors, and check on git.bioconductor.org what their repo and `.Rbuildignore` actually contain.
  - Check that the dates hold: precedent from packages older than the current rules (artMS) was dismissed.
- **Never invent a justification.** Every "we keep X because Y" must be true and checkable.
- **Draft first, post once.** Reply drafts go in a file for Witold to review. Deleting a GitHub comment does not help: the notification emails have already gone out.
- **Stop when told to wait.** Show findings before acting on them, even under a standing "commit and push".

## Phase 0: fit check

New packages must now work with Bioconductor's core data structures. saintexpress was withdrawn when the Core Team and Technical Committee made SummarizedExperiment integration a condition. By then its other 15 review points had all been fixed, and that work was wasted for Bioconductor.

- If BiocCheck reports "No hard Bioconductor dependencies detected … consider a CRAN submission", stop and put the choice to Witold:
  - import SummarizedExperiment (or another core class), export functions that take and return it, and build the vignette around it;
  - or go to CRAN.
- These were rejected or did not help:
  - a wrapper defined only in the vignette;
  - ExpressionSet ("legacy");
  - SummarizedExperiment in Suggests only;
  - footprint or webR arguments;
  - pre-2020 precedent;
  - an `Infrastructure` biocView used to downgrade the warning.
- Only Depends and Imports count toward that check.
- A class from another Bioconductor package can pass. apbCatalogR returned anndataR `AnnData` objects, with no SummarizedExperiment, and was accepted. Reviewers differ, so present this as a risk, not a guarantee.
- Settle the package name now, including its capitalisation. Renaming saintexpress after withdrawal broke downstream CI (pak takes the name from the repo, case-sensitively) and forced a CRAN resubmission.

## Phase 1: readiness

1. **Static precheck** from the package root: `bash <skill-dir>/scripts/precheck.sh <pkg-dir> [<tarball>]`.
   - Read-only; prints FAIL (blocks submission), CHECK (a reviewer may raise it) or OK.
   - Covers what BiocCheck misses or checks only on the tarball: version, folder name, DESCRIPTION fields, file sizes at the tip and in history, tracked dev files, the README AI section, NEWS heading, CITATION, and the code patterns reviewers flag.
2. **BiocCheck on the tarball, as a new package**:
   ```r
   BiocCheck::BiocCheck("<pkg>_0.99.0.tar.gz", `new-package` = TRUE)
   ```
   - Build the tarball first with `make build`.
   - Running on the source dir reports stray local files (`vignettes/*.html`, `_quarto/NEWS.md`). `make check-bioc` runs on the source dir, without `new-package`.
   - Use the BiocCheck devel version; release versions lag behind roxygen2 8 fields.
3. **Fix every ERROR and WARNING.** Write a one-line reason for each remaining NOTE; it goes into the issue or the first reply.
4. **Walk the checklist below** and "What reviewers ask" (Phase 3). Reviewers reuse their templates. On apbCatalogR, the points pre-empted from Lori's saintexpress review were never raised.
5. **Write the README AI section** (Phase 2). Answering only in a comment cost apbCatalogR a second round.

Report readiness as one line per check (passed / failed / not run), then the blockers. A package is not ready while any of these remains:

- an ERROR or WARNING;
- a NOTE without a written reason;
- a missing AI section.

### DESCRIPTION

- `Version: 0.99.z` for a new package.
- `Authors@R` only, no `Author:` or `Maintainer:` field. A `Maintainer:` line added in the 0.99.0 bump became a review item on prolfqua.
- `cre` person:
  - email registered on support.bioconductor.org (for Witold: `wewolski@gmail.com`, his account since prozor/specL);
  - ORCID in `comment = c(ORCID = ...)`. BiocCheck reads the ORCID from `cre` only.
- `fnd` role for the funder (jianhong asked). A funder name can trigger a spurious biocViews suggestion; justify that NOTE.
- `Depends: R (>= x.y)` matching the target release (R 4.6 for 3.23/3.24). Pin the same R version in every CI workflow: on prolfqua the agent updated `r.yaml` but missed `pkgdown.yaml`.
- No `Remotes:` (BiocCheck ERROR). Every dependency comes from CRAN or Bioconductor.
- Version bounds no higher than the current Bioconductor release ships.
  - `rhdf5 (>= 2.57.5)`, copied from anndataR devel, broke CI on 3.23 and cost apbCatalogR a release.
  - `devtools::check()` does not enforce Suggests minimums.
- Description field of at least 3 sentences.
- biocViews from the current vocabulary, with a reason for each suggested term you leave out.
- `stats`, `utils` and `methods` in Imports also need `@importFrom` or `::`. R CMD check missed an unimported `stats`; Lori did not.

### Repository contents

- Folder name equals `Package:`. A clone or worktree under another name gives a BiocCheck ERROR.
- Reviewers look at the git repo, not only the tarball:
  - Lori asked for `Makefile` and `air.toml` to go, although both were in `.Rbuildignore`; jianhong did not raise it.
  - Guideline: files for other applications "should ideally be in a different branch".
  - `*.Rproj`, `.DS_Store`, logs and `*.so` must not be committed.
- If you keep dev files, prepare a defence citing released packages by other authors. iscream, fraq, clustifyr and anndataR were checked on 2026-11-09.
- No certificates or site deployment configs in the repo, even if build-ignored.
- `inst/CITATION`:
  - ASCII only (an en dash gave a WARNING);
  - no `packageDescription()` fallback (it warns on r-universe, where the package is not installed);
  - a `doi` (WARNING without one). Mint the Zenodo DOI first if you want one: a GitHub release plus `.zenodo.json` with an explicit licence.
- One NEWS file, its top heading naming the version.

### Size and time

- Source tarball ≤ 10 MB. prolfqua reached 10.01 MB because of a plotly widget in a vignette; a static plot replaced it.
- Every file ≤ 5 MB. `prevent_large_files.py` checks only the size of each changed file **at the pushed tip**.
  - Old large blobs in history pass the hook, but the repo stays large.
  - To remove them: `git filter-repo --strip-blobs-bigger-than 5M` before submitting. This is a force-push on GitHub; ask first.
- Tarball paths ≤ 100 bytes (R CMD check WARNING).
- `R CMD check --no-build-vignettes` should take under about 10 minutes.
  - Build-system timeouts: INSTALL 60, BUILD with vignettes 40, CHECK 40, BiocCheck 20 minutes.
- Vignettes must run real code; all-`eval = FALSE` is not accepted. Wrap Shiny apps in `if (interactive())`.

### Code

- No exported names containing `.`. Don't keep a `.Deprecated` alias either, or the WARNING comes back.
- No `.Deprecated` / `.Defunct` in a new package. Delete the deprecated code; prolfqua moved `lm_missing` to a side package.
- None of these:
  - `suppressWarnings()` / `suppressMessages()`;
  - `<<-`;
  - `cat()` / `print()` outside `show` methods;
  - `paste()` inside `message()` / `stop()`;
  - commented-out code, TODO comments, `@param` for absent arguments.
- Style NOTEs (functions ≤ 50 lines, lines ≤ 80 characters, 4-space indents): either reformat (apbCatalogR moved to 80/4) or justify with the project style guide (accepted on prolfqua).
- roxygen2 8 writes 2-space indents in NAMESPACE `importFrom()` blocks. Justify the NOTE; never hand-edit NAMESPACE.
- No network access in tests, examples or vignettes. Cache downloads with BiocFileCache (preferred) or `tools::R_user_dir(pkg, "cache")`; avoiding downloads altogether is simplest.
- Check arguments at the exported boundary. Match input columns by name, never by position: positional renaming gave silently wrong scores in saintexpress.

### Documentation, tests, data

- A package man page (`"_PACKAGE"`) so `?pkg` works. Examples for every export; use `if (interactive())` rather than `\dontrun` for apps.
- A vignette named after the package. The landing page shows vignettes, not the README. It should contain:
  - an introduction: the field, why this package, why Bioconductor;
  - a comparison with related Bioconductor packages;
  - `BiocManager::install("<pkg>")`;
  - input and output schema tables;
  - the tuning arguments explained;
  - BiocStyle, and `sessionInfo()` at the end.
- Help pages document named arguments, not `...` passed on to internals, plus a table of required input columns and types.
- Every claim in the docs has a test ("matches the native tool" needs agreement fixtures with tolerances). Cover every branch a reviewer can see.
- Small real data, not only simulated.
  - Use a subset: 67 KB instead of 1.35 MB cut CI from 10 minutes to 15 seconds.
  - Record how it was made in `inst/scripts/`.
  - Add an `inst/extdata/README.md` listing source, commit, files and sizes.
- Skip browser and Shiny tests on the builders. `skip_on_cran()` also skips on Bioconductor, which does not set `NOT_CRAN`.

### Accounts (only a local BiocCheck shows these)

- The `cre` email must be registered on the Support Site (ERROR otherwise) and must watch the package name as a tag (ERROR otherwise). The profile form requires a Handle, and saving it once dropped the existing tags; check them afterwards.
- Subscribed to bioc-devel: shows as a NOTE ("cannot determine"). The email must also accept mail from noreply@ and BBS-noreply@bioconductor.org.
- HTTP 429 from the Support Site check means rate limiting; re-run.

## Phase 2: submit

- Draft the issue for **`Bioconductor/BiocContributions`**. The old `Bioconductor/Contributions` bot closes new issues with a redirect; agents have looked there by mistake twice. The issue:
  - title: the package name;
  - `Repository:` the GitHub URL;
  - a DOI line, if there is one;
  - the AI line below.

  Open it only after an explicit yes.
- Bot sequence and labels:
  1. `precheck-passed`, `awaiting policy acceptance`.
  2. Witold comments exactly `/accept-policies` himself → `policies-accepted`, `pre-review`.
  3. The bot clones the repo to `BiocStaging/<pkg>` (branch `devel`) and invites the submitter. Accept at `github.com/BiocStaging/<pkg>/invitations`.
  4. First r-universe build, after 1–14 h → `Build OK` / `Note` / `Warning` / `ERROR`.
  5. Reviewer assigned → `review in progress`.
  6. `package accepted`; the bot closes the issue. `doi-created` follows a day later (`10.18129/B9.bioc.<pkg>`).
- A WARNING in the first build: justify it in a comment straight away. The bot says no reviewer is assigned until errors and warnings are fixed or justified, and saintexpress stalled for weeks with one unjustified.
- In comments, put roxygen tags in backticks: a bare `@param` pinged the GitHub user PARAM.

### AI use and provenance

The policy (`contributions.bioconductor.org/ai-policy-third-party.html`) applies to "a non-trivial portion … copied from somewhere else", AI output included. It asks you to:

- discuss it in the issue;
- give provenance ("Assisted-by: Name of AI");
- cite the provenance in the code;
- confirm the code can be redistributed under the package licence;
- accept responsibility for its maintenance.

jianhong went further: round 1 asked for the tools, the extent of their use and how the output was reviewed and tested; round 2 required a README or CONTRIBUTING section.

Issue line:

```markdown
AI use: written with AI coding agents (<tools>); see the "AI use and provenance" section of the README.
```

README section accepted on #261. Adapt every line, and keep every claim checkable: name the real test file, CI jobs and commit.

```markdown
## AI use and provenance

AI coding agents helped write this package:

- Tools: Claude Code (Anthropic), and in-house open-weight models such as Qwen
- Extent: <much of the R code, the tests and the documentation; what it was ported from or built on>
- Marking: most commits written with AI help carry an `Assisted-by: AI coding agent` trailer; <earlier commits do not>, so treat the whole code base as AI-assisted
- Review: the maintainer reviewed every change before committing it
- Testing: <tests/testthat/<file>.R checks …>; R CMD check, BiocCheck and lintr run in CI on every push

Provenance and licence:

- No code is copied from other software projects <or: name the source and its licence>
- <Data in inst/extdata/: source, licence>
- Anthropic's terms assign the rights in generated output to the user, and the open-weight models' licences claim no rights in it, so all code can be redistributed under this package's <licence> licence

The maintainer is responsible for all code in this package, whatever helped write it, and for its reliability and maintenance.
```

- Confirm with Witold which tools were actually used for each package.
- The licence sentence is the agent's own reading of the tools' terms, with no legal review behind it.

## Phase 3: review

### Pushing during review

- During review, push to GitHub `BiocStaging/<pkg>`. git.bioconductor.org answers `DENIED by fallthru` until acceptance.
  ```bash
  git remote add biocstaging https://github.com/BiocStaging/<pkg>.git   # SSH was refused on #261; HTTPS with gh worked
  git push biocstaging main:devel
  ```
- Bump `z` for every push you want built. The bot posts "New build detected … version X" for each version.
- `devel` is protected: a revert is a new commit with a new `z`.
- Only the submitter is a collaborator.
- Fixes land in the canonical repo first. A Bioconductor fork carries only the version, the NEWS heading and a README note.
- Run BiocCheck before `make new-version`: that target commits, tags and pushes in one go, and once left a tag one commit behind the final fix.
- Keep one agent session per repo. On apbCatalogR, concurrent sessions committed each other's work.

### Reading build reports

- An r-universe table per build (source, bioc-checks, linux, macos-arm64, windows, wasm) at `biocstaging.r-universe.dev/<pkg>#checktable`. Lag after a push: 30 minutes to 10 hours.
- A green "Bioconductor Checks" job can still contain WARNINGs: grep its log for `✖ n ERRORS | ⚠ n WARNINGS`.
- macOS jobs sometimes fail in Homebrew setup. That is infrastructure; re-run before debugging.

### What reviewers ask

**jianhong** (prolfqua, apbCatalogR). Her review is a checklist of "Important" (must fix) and "Note" (please consider) items, and she asks for a point-by-point answer. Recurring items:

- AI use (Important; new in November 2026).
- `::` → `@importFrom`. Keep `::` only for Suggests behind `requireNamespace()`.
- `for` loops: she lists the lines. Her checker matches `for (`, so it also flags functions whose names end in `for`. Base-R `vapply` / `Map` / `Reduce` were fine.
- Code repetition → shared helpers.
- Also on her list:
  - `.` in function names;
  - CITATION format;
  - `Authors@R`, ORCID, `fnd`;
  - a README for `inst/extdata`;
  - BiocFileCache;
  - `.Deprecated`, `suppressWarnings`, `cat` / `print`, `paste` in conditions;
  - commented-out code, TODOs, stale `@param`;
  - exposing hidden arguments;
  - a package man page, BiocStyle, a main vignette;
  - NEWS heading = version;
  - typo lists.

**Lori Shepherd / lshep** (saintexpress, 16 points; full list in `prolfqua_fml/TODO/saintexpress/Archive/TODO_review_lshep_2026-11-09.md`):

- dev files out of the repo;
- a used but unimported `stats`;
- the `?pkg` page;
- real data;
- a vignette introduction with a "why Bioconductor" rationale, related packages, schema tables and tuning;
- exported help pages that don't point to internals and use named arguments instead of `...`;
- column tables, and a validator that matches what the main function accepts;
- matching columns by name;
- strict argument checks;
- tests for every claim and every branch;
- merged duplicate code;
- **interoperability with core classes**: "a separate function … allows a SummarizedExperiment class object directly (and returns one as such)". This became a condition of acceptance.

**Outsiders can weigh in.** Laurent Gatto quoted our own written argument ("a container class would add a dependency without adding functionality") as proof the package did not belong. Arguing against core data structures in writing works against you.

**A stalled review** (9 weeks without one) moved after a polite ping on the issue that cc'd lshep and named the release deadline.

**Kept with a one-line reason, and accepted** (prolfqua):

- `::` ("origin explicit; R CMD check verifies it");
- `for` loops ("few items / side effects");
- repetition across parallel backends ("merging adds branching");
- style NOTEs ("project style guide, enforced by lintr/air");
- an exported name with a typo ("downstream callers").

### Triage and reply

- Keep one TODO per submission in the workspace's `TODO/<pkg>/`. Witold asked "Why 3 todos?" when there were three.
  - Every reviewer point goes in verbatim, in the reviewer's order, with a one-line plan and a status.
- Walk the points one at a time in chat. Witold decides each one ("3. approved …"). No code during the walk; update the TODO afterwards.
- Settle the contentious point first (a data structure, a dependency, a policy question).
- Answer a Note literally and lightly.
- Draft the reply in `TODO/<pkg>/bioc_review_<issue>_reply.md` and link it in chat. Post with `gh issue comment <n> -R Bioconductor/BiocContributions --body-file <file>` after approval.

Reply structure that worked on #171 and #261:

```markdown
Thank you @<reviewer> for the review. Version 0.99.<z> addresses every point; answers in the order of your review.

**<Reviewer's heading> (Important)**
- Fixed: <what changed, one line> (<repo>@<sha>)

**<Reviewer's heading> (Note)**
- We keep <X> because <one true, checkable reason>.

**Build**
- BiocCheck: 0 ERRORS, 0 WARNINGS, <n> NOTES
- <NOTE>: <one-line reason>

Since your review, <pkg> also carries:
- <pre-empted improvement>

Witold
```

- Mirror the reviewer's headings. If the review uses checkboxes, tick each with `- [x]`.
- If a co-author answers, open with "on behalf of the maintainer".
- Fragment bullets and a neutral tone, even when Witold is angry. Leave out internal version history ("Who cares about 0.99.1").
- Back each claim with a measurement and its method (dependency count, `du`, RSS, platform).
- End a policy question with a direct question that a yes or no answers.
- "Link to the vignette" means the `.Rmd` source, not rendered HTML.

## Phase 4: accepted

The bot's instructions:

```bash
git remote remove biocstaging
git remote add upstream git@git.bioconductor.org:packages/<pkg>
git push upstream main:devel        # approval and a z bump every time
```

**Access and pushing**

- SSH keys go through BiocCredentials (`git.bioconductor.org/BiocCredentials`).
  - Activation only works with an email Bioconductor already has on file.
  - Keys can be added, not removed.
- Check access without writing anything:
  - `ssh -T git@git.bioconductor.org` lists `R W packages/<pkg>`;
  - `git ls-remote https://git.bioconductor.org/packages/<pkg>`.

  Never test access with a dummy commit.
- Before each push: `git fetch upstream` and merge `upstream/devel` (maintainers sometimes commit there directly). Then:
  - check no file is over 5 MB and there are no merge markers;
  - push to GitHub and wait for its CI on the devel R version;
  - push to upstream.
- Devel build report: `bioconductor.org/checkResults/devel/bioc-LATEST/<pkg>/`. It is a 404 for a day or two after acceptance; after that, a push shows up within 24–48 h. A package that keeps ERRORs gets deprecated.

**Version hook** (`prevent_bad_version_numbers.py`, in `github.com/Bioconductor/git-hooks`)

- In devel, `x` never changes, `y` stays or is set to `99` (it must be odd), and `z` only goes up.
- A GitHub repo at `1.9.0` therefore cannot push to a devel at `0.99.z`. Either keep a fork with the Bioconductor version, or align both repos (the prolfqua plan: `1.99.0` in both after the release).
- At release, `0.99.z` becomes `1.0.0` (release) and `1.1.0` (devel).

**Bioconductor 3.24 dates**

- Accepted by Wed 18 Nov 2026.
- Build clean by Fri 20 Nov.
- Release Wed 25 Nov.
- Check `bioconductor.org/developers/release-schedule/` for later cycles. A package accepted after the deadline waits about six months for the next release.

**Withdrawal** has no bot command: the maintainer comments and closes the issue.
