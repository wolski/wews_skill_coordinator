# Prompt audit — owned skills (2026-09-24)

Of 14 owned skills, 4 are clean. `general-agentic` needs the most work: a reasoning-reproduction template, action-count cadences, and a blanket stop-and-ask-on-failure rule that conflicts with the global AGENTS.md. The other hits are mostly factual rot (wrong paths, Click instead of cyclopts, nonexistent pixi flags). Proposed patch: [prompt_audit_skills.patch](prompt_audit_skills.patch), 20 hunks. Nothing applied; `patch -p1 --dry-run` from `~` is clean.

## Assumptions

- Target: Opus 5.5
- Scope: 12 skills from [skills](../skills) installed via `~/.agents/skills`, plus [commit](/Users/wolski/.claude/skills/commit/SKILL.md) and [scientific-outreach](/Users/wolski/.claude/skills/scientific-outreach/SKILL.md)
- Out of scope: `repos/fgcz-skills` (team-owned, mostly Paul Gueguen); upstream marimo/skill-creator skills
- Read by two parallel agents; High claims re-checked by hand
- Not checkable locally: pixi (not installed), scanpy (not installed)

## Clean

- design-principles
- directed-folder-imports
- marimo-background-jobs
- scientific-outreach (one Low flag)

## In the patch

### general-agentic — 3 High, 8 Medium

- L51-78, High, G1b reasoning reproduction: DOING/EXPECT/RESULT template before every action → one-line stated expectation
- L150-160, High, G1b cadence: "Batch size: 3", "More than 5 actions" → verify against observable output
- L448, High, G1b plan scaffold: "Sequential Thinking, present plan, get signoff" → say what is unclear, ask
- L84-97, Medium, G1a caps + over-constraint: stop-and-ask on every failure → ask only when destructive, scope-changing, or ambiguous (matches AGENTS.md)
- L470-474, Medium, G1c duplicate: RULE 0 restates the failure rule with a stricter threshold → remove
- L164-173, Medium, G1d retention crutch: "Every ~10 actions… scroll back" → one line
- L225, Medium, numeric judgment: "5+ competing theories" → "several"
- L282, L454-456, Medium, G1a trait claims → desired behavior
- L317, Medium, G1a: "Temptation… Resist." → remove; the criteria that follow it stay
- L446, Medium, G1e: banned "you're absolutely right" → respond with substance
- L458, Medium, G1b: "think first, present theories" → removed with L454 block

### Others

- [polymorphism-over-discrimination](../skills/software-engineering/skills/polymorphism-over-discrimination/SKILL.md) L28-30, Medium, G2 pinned model names: "Opus- and Fable-class models only" → condition on being delegated the sweep
- polymorphism-over-discrimination L53-54, Medium, G2 history: "learned by failing it" → drop clause
- [polars-first](../skills/software-engineering/skills/polars-first/SKILL.md) L72, Medium, G2 history: APB2 anecdote → remove
- [mixed-r-python-pipeline](../skills/workflow-development/skills/mixed-r-python-pipeline/SKILL.md) L41, High, G2 stale path: `projects/ptm-pipeline` → `projects/prolfqua_fml/ptm-pipeline` (verified)
- mixed-r-python-pipeline L44/77/90, High, G2: Click → cyclopts; the reference `cli.py` imports cyclopts, and AGENTS.md requires it
- [snakemake-compact](../skills/workflow-development/skills/snakemake-compact/SKILL.md) L16, High, G1d fossil: stray "Always show details" → remove
- snakemake-compact L160-166, Medium, G2 wrong claim: `rule clean` runs nested snakemake and hits the outer run's lock → shell comment
- snakemake-compact L3, Medium, G3 under-described description → when-to-use added
- [scverse](../skills/scientific-python/skills/scverse/SKILL.md) L277-281, Medium, G2: `seurat_v3` on log data → `layer="counts"`
- scverse L311, Medium, G2: `use_highly_variable` deprecated → `mask_var`
- [pixi-package-manager](../skills/workflow-development/skills/pixi-package-manager/SKILL.md) L996-999, High: nonexistent skills referenced → `uv`
- [commit](/Users/wolski/.claude/skills/commit/SKILL.md) L1, High, G3: no frontmatter, so the listing shows "Commit Skill" → name + description added

## Report only — no patch hunk yet

These are Medium, but the fix needs a docs check or is a large removal:

- pixi, L25/278/1211: `--import-environment` flag doesn't exist (per agent; `pixi` not installed)
- pixi, L109-114 and others: conda syntax and packages under `[project].dependencies`
- pixi, L647-652: `[tool.pixi.platforms]` table → `workspace.platforms` list
- pixi, L601/L1051: `pixi list --export`, `pixi add --force-reinstall` don't exist
- pixi, L689: `[tool.pixi.task.*]` → `tasks`
- pixi, L796-826: GitHub Actions pins stale; `upload-artifact@v3` retired
- pixi, L430/745: `pip install -e .` inside pixi bypasses the lockfile
- pixi, L920-975/L1270-1286: marketing summary and generic checklist → remove
- pixi, L3: description lacks when-to-use
- [plotly](../skills/scientific-python/skills/plotly/SKILL.md) L855/924: plotly 6 export needs Kaleido v1 + Chrome
- [shell-scripting](../skills/workflow-development/skills/shell-scripting/SKILL.md) L10-142: generic bash tutorial → keep Snakemake/Fish/Zsh notes and the template pointer
- shell-scripting L118: duplicate of L116

## Flag only (Low)

- polymorphism-over-discrimination: past-package anecdotes that also carry reasons for bounds
- general-agentic L433 "STOP COMPLETELY"; L103-109 feedback section mid-protocol
- plotly: basic px examples are general knowledge
- scverse: leiden flavor warning; `max_genes` labelled as doublet removal
- scientific-outreach L31-39: exact-phrase bans can push toward synonyms

## Verify

- Apply general-agentic hunks, then run one debugging session and see whether it still over-asks or goes silent on failure
- pixi: check against `pixi --help` / pixi docs before rewriting
- Session-start check: the earlier output-style edits load in new sessions (this session still shows its startup copy)
