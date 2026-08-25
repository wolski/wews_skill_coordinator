# Review Patterns

These patterns are distilled from the `mspms` and `pyMSscreen` review folders.

## First-Round Software Manuscript Review

Use a two-part structure:

1. Manuscript and method claims
2. Software package/code/reproducibility concerns

For manuscript claims, check novelty, prior work, method rationale, definitions, statistical descriptions, figures, and terminology. In the `mspms` review, useful issues included an overstated "first platform" claim, missing rationale for label-free intensity quantification, unclear upstream search-software choices, undefined domain terms, unclear log-scale handling, and incomplete iceLogo algorithm documentation.

Also audit scientific language. Promotional or marketing-style terms do not belong in the main article unless directly supported by evidence. Flag unsupported superlatives, value-proposition language, and repeated claims of reliability, ease, novelty, or broad applicability. In `mspms`, the "Further comments" pattern included reducing repetition and replacing vague phrases such as "numerous" with concrete counts or percentages.

For software concerns, inspect maintainability and correctness. In `mspms`, useful issues included duplicated validation functions, a wrong missing-column condition, copy-paste error messages, O(n^2) row binding, exploratory code in package sources, and separation-of-concerns concerns.

## Revision-Round Verification

Create a table or checklist mapping reviewer comment to expected change, status, and evidence. The `mspms` verification report used categories such as Introduction, Methods, iceLogo, Results, Figure Legends, Citations, Code Refactoring, Bug Fixes, Performance, New Features, and Vignette.

Use `VERIFIED` only when the revised manuscript or code contains the change. Use `PARTIAL` when the change exists but differs from the response or remains incomplete. Use `NOT FOUND` when the response claims a change but the submitted material does not show it.

## Response-Claim Audit

For a second-round software review, compare author promises directly to the current repository snapshot. The `pyMSscreen` review tracked repository URL, local clone, commit hash, commit date, and a status key.

High-priority finding style:

```markdown
- [FAIL] The README is still not sufficient to exactly reproduce the manuscript example. It links the dataset but does not give exact file-to-tag/adduct mapping.
- [FAIL] The manuscript claims a 7-point moving average, but active peak selection uses 5 points in backend and frontend code.
- [PARTIAL] Tests were added, but they are smoke tests and do not cover parsing, adduct/mass logic, state generation, extraction, prescreening, or frontend build.
```

## Local Verification Commands

Record commands as evidence, not decoration. Useful command classes:

- repository clone or snapshot identification;
- package install or dependency resolution;
- backend test suite;
- frontend `npm ci`, `npm run build`, and `npm run lint`;
- R package `devtools::test()` or `devtools::check()`;
- targeted `rg` checks for parameters, endpoints, duplicate helpers, or stale code.

If a command fails because the local environment lacks a dependency, say that. Do not convert an environment failure into a software finding unless the missing dependency is itself undocumented or undeclared.

## Review Prose Tone

Use concise, professional second-round phrasing:

```markdown
Thank you for adding ... This is an improvement. However, ...
```

Then name the remaining concrete mismatch and requested correction. Avoid vague demands such as "improve documentation"; specify exact missing files, parameters, command outputs, or examples.

For language concerns, avoid broad style lectures. Tie the issue to scientific interpretation:

```markdown
The manuscript repeatedly states that the workflow is comprehensive and easy to use, but these claims are not supported by reproducibility evidence or user-facing examples. Please replace promotional language with specific, verifiable descriptions of the supported inputs, tested workflows, and limitations.
```

```markdown
Several paragraphs restate the same contribution without adding new data or methodological detail. The main text should be tightened so repeated value statements are replaced by concrete quantitative results, exact parameters, or removed.
```

## Decision Guidance

Recommend acceptance only after the main claims, examples, and core software concerns are verified. For `mspms`, acceptance followed a high verification rate and only minor discrepancies. For `pyMSscreen`, remaining issues stayed publication-relevant because reproducibility, manuscript-code consistency, tests, and stale endpoints were still unresolved.

## proteOmni (Multi-Module Dashboard) Patterns

The `proteOmni` review was a first-round review of a multi-module R/Shiny QC dashboard (eight modules wrapping different proteomics search engines plus one statistics module). It surfaced patterns useful for any multi-component tool paper.

### Major concerns that recurred

1. **No runnable example data for any module (reproducibility).** The repository shipped only code; the figure datasets were cited as a raw public accession with no processing detail, so no figure or module could be reproduced. A **per-module input inventory** (what each module requires) made the gap concrete and turned "no data" into a specific, actionable request (one small example per module + a figure-regeneration recipe).
2. **Scope/workflow incoherence.** The modules were unified only at the interface (a shared menu), not as an analysis pipeline: seven QC viewers did not feed the single differential-analysis module, which took a generic matrix; the *de novo* modules produced no quantification and could not connect at all. The manuscript gave no rationale for the tool selection and no end-to-end workflow. Ask for a workflow diagram and a selection rationale, or an honest reframing as independent viewers.
3. **A named metric computed incorrectly.** The isoelectric point was a plain average of per-residue pKa constants, not a net-charge (Henderson–Hasselbalch) pI — present in the UI but scientifically wrong, and shared across modules. Verifying metric *correctness* (not just presence) is essential; the same utilities file had a correct GRAVY, so check each metric individually.
4. **Manuscript features that don't match the code.** Claimed-but-absent (PSManalyst PCA), present-but-different (MaxQuant "annotated spectra" merely re-plotting the search engine's own annotations; "mass accuracy error" in Th not ppm; default imputation KNN not the claimed missForest), and diagnostics described with chemistry/thresholds the code doesn't implement (the RT-shift modification panel).
5. **Silent failure on input-format/version differences.** Hardcoded, version-specific column names with errors swallowed by `tryCatch`, so mismatched inputs were dropped or produced empty panels with no message — a data-integrity risk specific to QC tools.
6. **Statistical framing.** A power-based "minimum detectable difference" computed at nominal α from same-data variance, while significance was called on FDR-adjusted values — the threshold did not match the discovery criterion. Reframe as a descriptive, data-conditional sensitivity estimate, not a power analysis validating results.

### Method patterns

- **Convert the proof PDF to Markdown first** (`pdftotext -layout`), then work from text.
- **Parallel per-module verification.** With many modules, verify each module's manuscript claims against its code independently (one pass per module), then consolidate into systemic vs per-module findings.
- **Run the tool.** Launch headlessly and smoke-test that it serves; confirm declared dependencies resolve. Firsthand-verify the highest-impact claims (e.g. grep for the absent PCA; read the metric's implementation).
- **Reviewer-side deep verification stays private.** Generating a synthetic dataset to exercise the statistics module (and finding that the default normalization suppressed real effects) was valuable for the reviewer's confidence but out of scope for a normal review — it lived in the private technical file and was excluded from the submitted review. See "Confidentiality and AI Use" in the skill.

### Output patterns

- **Two audiences.** A detailed private technical file (per-module claim tables, `file:line`, systemic issues, verification appendix, exploratory plots) plus a concise authors-facing review classified Major/Minor in the reviewer's own voice.
- **Editor letter.** A short confidential recommendation ("major revision with re-review") with a 2–4 sentence rationale, kept separate from the author comments (they map to ScholarOne's separate fields).
- **Keep review artifacts out of the cloned repository** and out of anything submitted; a `Handoff` note listing what to submit vs. what to keep private is useful.

## Attribution worked example (ProteoAnalyst)

This is the concrete form of the "Reuse of Established Methods, Attribution" section in `SKILL.md`. For an integrated-platform paper, go feature by feature: quote what the manuscript actually says, show the missing primary-method attribution, and give the corrected sentence that **names and cites the established tool**. Make it easy for the authors by pointing out that they already do this correctly for two features — GSEA (*"ProteoAnalyst performs GSEA using the fgsea R package (35)"*) and co-expression (*"built upon the widely used Weighted Gene Correlation Network Analysis (WGCNA) (37, 38)"*) — so the ask is only to extend that same standard to every module. (COI: where the reference tool for a feature is the reviewer's own, cite the **class**, do not single it out — e.g. list "MSstats / msqrob2 / prolfqua" together, never one alone.)

**1. Variance-stabilizing / quantile normalization**
- *How it reads now:* "Data transformation options include log2 transformation, log2 transformation with median centering, quantile normalization and Variance Stabilizing Normalization (VSN)." — PQN is cited (ref 17), but VSN and quantile normalization carry no method citation.
- *How it should read:* "…quantile normalization (Bolstad et al., 2003; `preprocessCore`) and variance-stabilizing normalization (VSN; Huber et al., 2002; `vsn`)."

**2. Missing-value imputation (KNN, BPCA)**
- *How it reads now:* "ProteoAnalyst also offers established methods including replace by mean or median, K-Nearest Neighbors (KNN) and Bayesian PCA (19)." — only a general imputation-strategy review is cited (ref 19); the algorithms/packages actually used are not.
- *How it should read:* "…K-nearest-neighbour imputation (Troyanskaya et al., 2001; `impute`) and Bayesian PCA (Oba et al., 2003; `pcaMethods`, Stacklies et al., 2007), together with MinDet/MinProb/QRILC (`imputeLCMD`, Lazar et al., 2016)."

**3. Over-representation analysis (ORA)**
- *How it reads now:* "…perform enrichment analysis based on Gene Ontology (23), KEGG (24), Reactome (25), or PANTHER (26)"; "Functional analysis uses overrepresentation analysis and GSEA." — the gene-set **databases** are cited, but the ORA **test/implementation** is not (the code uses a custom hypergeometric test with an undisclosed background).
- *How it should read:* "Over-representation is assessed with a hypergeometric test against the quantified proteome as background (as implemented in `clusterProfiler`; Wu et al., 2021), with Benjamini–Hochberg FDR." — or, if kept in-house, "a custom hypergeometric test benchmarked against `clusterProfiler`."

**4. Phosphosite protein-abundance correction / PTM occupancy**
- *How it reads now:* "intensities are normalized against parent protein levels via log-ratio subtraction. This isolates true changes in phosphorylation stoichiometry from confounding shifts in baseline protein expression." — reimplemented in-house; MSstatsPTM is cited only as "conceptually related."
- *How it should read:* "Phosphosite abundance is corrected against the matched parent protein and tested using `MSstatsPTM` (Kohler et al., 2023) [or `msqrobPTM`]; where the correction is implemented in-house it is benchmarked against these, and reported as a relative, abundance-adjusted site ratio rather than 'true stoichiometry'."

**5. Biomarker machine-learning models**
- *How it reads now:* "…supervised machine learning models, including logistic regression, Random Forests, Support Vector Machines (SVM), and Partial Least Squares-Discriminant Analysis (PLS-DA)." — no implementation is cited for any model.
- *How it should read:* "…Random Forests (`randomForest`; Liaw & Wiener, 2002), SVM (`e1071`), and PLS-DA (`ropls`; Thévenot et al., 2015), with ROC analysis via `pROC` (Robin et al., 2011)."

Same pattern applies to the STRING interactome used in Case Study 2 ("PPI network analysis with the STRING interactome" → cite Szklarczyk et al., 2023) and to differential expression, which cites limma (22)/DEqMS (7) for the test but not the established proteomics DEA frameworks it re-implements the workflow around (MSstats / msqrob2 / prolfqua).

**Model review comment:** "Several modules re-implement well-established methods but cite only the underlying database or a general review, not the reference implementation. The manuscript already attributes GSEA to fgsea and co-expression to WGCNA/CEMiTool — please apply that same standard throughout (VSN/quantile normalization, KNN/BPCA/QRILC imputation, ORA, phosphosite abundance correction and PTM occupancy, the STRING interactome, and the biomarker ML/ROC models), and, where a method is re-implemented rather than reused, justify why and validate it against the reference implementation."
