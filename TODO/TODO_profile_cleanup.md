# Profile cleanup

> Status: implemented 2026-09-24; 168 tests, strict pyright, ruff, import-linter pass. `coord install` not yet run with the new profiles.

> Two kinds of profile, one level of indirection: every skill sits in exactly one base profile, and a composition is a flat list of base profiles.

## Rules

- **Base profile:** lists concrete skills only; no `includes`
- **Composition:** `includes` only, and only base profiles; never included anywhere
- **One home per skill:** each skill in exactly one base profile (proposed on top of your two rules — it is what makes "where does X come from" a single grep)
- `full`: the composition of every base profile, `includes = ["*"]`
- A base profile stays installable on its own: `coord install skills --profile r`

Today's violations:
- Mixed: `python`, `proteomics`
- Composition inside composition: `python-communication` → `python-bfabric` → `python-bfabric-proteomics`
- Skills in two profiles: `uv`, `scverse`, `plotly` (python + science); `prolfquapp-dea`, `adding-models-to-prolfqua` (r + fgcz-proteomics-data-analysis); `bfabric-app-runner` (proteomics + fgcz-infrastructure)

## Base profiles — 17, each skill once

| profile | skills |
| --- | --- |
| python-design | constructor-or-dataclass, design-principles, polymorphism-over-discrimination, directed-folder-imports, polars-first |
| python-style | python-style-guide |
| python-design-public | python-design-patterns |
| workflow | mixed-r-python-pipeline, snakemake-compact, shell-scripting, pixi-package-manager, uv |
| scientific-python | scverse, plotly |
| science-databases | the 14 deepmind databases (uniprot … gtex); no `uv` |
| marimo | the 8 marimo-team skills, marimo-background-jobs |
| r | r-development, advanced-r-engineering, bookdown, posit's r-package-development, testing-r-packages, r-cli-app, cli, lifecycle |
| fgcz-bfabric-lims | bfabric-connect, bfabric-query, bfabric-tools, bfabric-dataset |
| fgcz-communication | interview-to-spec |
| fgcz-infrastructure | bfabric-app-runner, fgcz-gitlab, fgcz-modules |
| fgcz-meta-skills | fgcz-context, constitution, skill-contribution, verification-loops, create-pull-request, lessons-compounder |
| fgcz-proteomics-data-analysis | phosphoproteomics-ptm-analysis, prolfquapp-dea, adding-models-to-prolfqua, fix-prolfqua-dea-app, fix-ptm-pipeline, run-ptm-pipeline |
| review | multiagent-review, verify-review-findings, software-manuscript-review |
| meta | skill-creator, agent-rules |
| education | school-study-materials |
| experimental | create-appnote-outline |

Changes against today:
- `python`'s own skills split into `workflow` (with the only `uv`) and `scientific-python`
- `science` loses `uv`, `scverse`, `plotly`; renamed `science-databases`
- `r` loses the two prolfqua skills; they live in `fgcz-proteomics-data-analysis`
- The five `fgcz-*` profiles still mirror the fgcz folders unchanged

## Compositions — 5

```toml
[profiles.full]
description = "Every base profile."
includes = ["*"]

[profiles.python-bfabric-proteomics]      # active: 25 skills
description = "Daily FGCZ work: Python design and workflow, B-Fabric, proteomics/PTM analysis."
includes = [
    "python-design",
    "workflow",
    "scientific-python",
    "fgcz-communication",
    "fgcz-bfabric-lims",
    "fgcz-proteomics-data-analysis",
    "meta",
]

[profiles.python]                         # 12 skills
description = "Python design, workflow tooling, and plotting."
includes = ["python-design", "workflow", "scientific-python"]

[profiles.science]                        # 16 skills
description = "Scientific Python plus literature, sequence, structure, and pathway databases."
includes = ["scientific-python", "science-databases"]

[profiles.fgcz]                           # 20 skills
description = "Every FGCZ source folder."
includes = [
    "fgcz-bfabric-lims",
    "fgcz-communication",
    "fgcz-infrastructure",
    "fgcz-meta-skills",
    "fgcz-proteomics-data-analysis",
]
```

The active profile, today versus proposed:
- Drops `marimo` (9 skills): not in use
- Keeps no `review`: not wanted active
- 34 skills today, 25 proposed; the other 9 are exactly the marimo ones

Dropped:
- `python-communication`, `python-bfabric`: they only existed as layers; re-add as flat compositions if you install them directly
- `proteomics`: mixed, and its extra skill `bfabric-app-runner` belongs to `fgcz-infrastructure`; `fgcz` or the active profile covers it

## Code changes this needs

- `config/schema.py`: reject a profile with both or neither of `includes` and skills; reject `includes` naming a composition; reject a skill in two base profiles; `*` expands to base profiles only
- The inclusion-cycle check goes away: one level cannot cycle
- `skills.toml`: bases grouped first, compositions at the top
- Tests: new rules; production counts (`full` still 72 skills — nothing is deleted, only moved)
- `coord list profiles`: bases and compositions as two tables
