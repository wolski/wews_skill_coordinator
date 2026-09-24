# Prompt audit — active profile (2026-09-24)

The two PTM skills in the active profile describe an older ptm-pipeline. Commands like `ptm-pipeline update`, `validate`, `info`, `make all` and `snakemake -j4 reports` no longer exist, and the model follows them literally. They need a rewrite against the current CLI, not a patch. The other findings are wrong names and signatures in `adding-models-to-prolfqua` and `phosphoproteomics-ptm-analysis`; [prompt_audit_active.patch](prompt_audit_active.patch) fixes the verified ones in 9 hunks. Nothing applied; `patch -p1 --dry-run` from `~` is clean.

## Scope

- Active profile `python-bfabric-proteomics`: 22 skills
- Already audited today: 7 wews skills (see [TODO_prompt_audit_skills.md](TODO_prompt_audit_skills.md))
- This run: `constructor-or-dataclass`, plus the 7 active fgcz skills Witold authored
- Out: the 4 `bfabric-*` skills (Paul Gueguen, Leonardo Schwarz); `uv`, `skill-creator`, `agent-rules` (npx overwrites edits)
- All fgcz files live in `repos/fgcz-skills`, the team repo
- Checked by hand: ptm-pipeline CLI (HEAD 3ca6f7b: `init`, `run`, `clean` only; template has no Makefile), prolfqua and prophosqua signatures

## Clean

- constructor-or-dataclass
- fix-prolfqua-dea-app, apart from one Medium item below
- Group 1 (pressure language, scripts) is clean in every file; the findings are all stale facts

## Rewrite needed — no patch

### run-ptm-pipeline — High

- L32, 107-133: `info`, `init --dry-run`, `init-default`, `make validate`, `validate --quick` — none exist; use `init . .`, `init default . .`, `init . . --force`
- L137-167: `make dry-run`, `make all CORES=4`, data/reports tiers; the direct `snakemake … -n all` also breaks (target must precede `--configfile`) → `ptm-pipeline run dry .`, `ptm-pipeline run . -j 4`
- L187-205: output tree and "every report reads `PTM_results.xlsx`" — reports read the h5mu files; the workbook is an export
- L223-225: `ptm.sh render --report Analysis_seqlogo.Rmd` — no rule renders it; `ptm_statistics.qmd` does
- L236-241, 311-313: "all 17 rules", `init-default`, `validate` in the wrapper example
- L3 description: routes on `"make all"`, "init/validate/run, the data and reports tiers"
- `references/worked-example.md` repeats the same stale commands

### fix-ptm-pipeline — High

- L8-22: `ptm-pipeline update`, `remove_legacy_src`, "before 0.3.0" — no update command since 2026-09-21
- L32-65: report table points at `Analysis_*.Rmd`; the live reports are `ptm_statistics.qmd` / `ptm_enrichment.qmd` via `prophosqua:::report_file()`
- L74-76, 161-170: `combine_ptm_results()` and the xlsx-as-input claims; the workbook comes from `R/export_ptm_h5mu.R`
- L123, 136-143: `diff` over a Makefile, `ptm-pipeline update .` → `init . . --force` (review `ptm_config.yaml` first)
- L190-196: migration-relative "outputs now … unlike the old rules", also stale → remove
- L221-234: `snakemake -j4 reports` → `snakemake all -j4`, or `render_statistics` for a report-only fix
- The site-annotation stop (L83-110) is still correct; keep it

### phosphoproteomics-ptm-analysis — High

- L264-316, 335-356, 540-563: a hand-written Snakefile with `DIR_OUT = f"PTM_{date.today()}"` (moves the output dir daily, forcing full reruns) and R code in the work dir — contradicts the real pipeline → replace with a pointer to `run-ptm-pipeline` / `fix-ptm-pipeline`
- L200/207-209, 250/253, 524-528: example bugs — `contrast` dropped before filtering, `write_gct` missing `contrast_name`, a local `filter_contaminants` shadowing prophosqua's (Medium; read, not run)
- L358-371, 405-424, 509-520: generic R (caching, Rmd params, arrow) the model already knows → remove (Medium)
- L3 description: no "use when", no boundary against the pipeline skills (Medium)

## In the patch — verified point fixes

- adding-models-to-prolfqua L28: `to_wide` → `data_wide` (High; `LFQData.R:281`)
- adding-models-to-prolfqua L61-65: add missing `get_missing()` to required methods (High)
- adding-models-to-prolfqua L155, 160: `.ehandler` → `.error_handler` (High; `R/utilities.R:2`)
- adding-models-to-prolfqua L203: `ContrastsLmerFacade` → `ContrastsLmerNestedFacade` (High)
- adding-models-to-prolfqua L211-212, 302: `.builtin_facade_entry` → entry in `.seed_facade_registry()` (High)
- phosphoproteomics-ptm-analysis L39: `LFQData$new(lfq_config, data)` → `(data, lfq_config)` (High; checked)
- phosphoproteomics-ptm-analysis L170: `join_by` → `join_column` (High; checked)
- interview-to-spec L155: "planned — PR #23" → talking-to-humans exists (High)

## Report only — not in the patch

- adding-models-to-prolfqua L139: strategies are R6 classes now (`StrategyLM`, …) — sentence rewrite, not a rename
- adding-models-to-prolfqua L190-192, 300: facades inherit `ContrastsFacadeBase`, not `ContrastsInterface` directly — wants a paragraph
- phosphoproteomics-ptm-analysis L42, 54, 62: `strategy_lm()`, `load_and_preprocess_data()`, `n_to_c_expression_multicontrast()` need arguments the examples omit — the right values are analysis-specific
- prolfquapp-dea L60: `prolfquapp_docker.sh` is not copied by `copy_shell_script()`; say where to get it (Medium)
- interview-to-spec L105-106: separate "create `TODO/`?" gate conflicts with "no second confirmation" → fold into the write prompt (Medium)
- fix-prolfqua-dea-app L245-251: "runner reuses the cached env" — A414 `app.yml` sets `refresh: True` (Medium; deployed host not checked)

## Flag only

- fix-prolfqua-dea-app L178-211: Firth sections may be dated (`pl = FALSE` landed); has its own escape hatch
- fix-ptm-pipeline L177-182: bookdown `fig.cap` trap; reports are Quarto now — re-test
- Hard-wrapped Markdown in several fgcz files; fix only when those paragraphs are next edited

## Verify

- PTM skills: rewrite against `ptm-pipeline --help` and `template/Snakefile`, then run `ptm-pipeline run dry .` on a real order
- prolfqua fixes: `R CMD check` is not needed; `args(prolfqua::…)` confirms each name
