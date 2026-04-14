# Skill Coordinator TODO

## Immediate

- [x] Initial setup: Makefile, skills.conf, README, CLAUDE.md
- [x] Clone all 4 repos, verify `make install` works (25 skills linked)
- [ ] After push: `make update && make install` to pick up prolfqua-adding-models
- [ ] Clean up claude-kaiser-skills: remove copied upstream skills that are now managed by coordinator (marimo-notebook, marimo-batch, streamlit-to-marimo, skill-creator, skill-development, r-package-development)
- [ ] Create GitHub repo for wews_skill_coordinator and push

## Skill review progress (using skill-creator/skill-development guidelines)

### Completed (2026-04-08)
- `r-development` — full rewrite: description (3rd person, triggers), namespacing rule, new sections (ggplot2, purrr, stringr, reshaping, IO), no-dontrun rule, scope boundary with r-package-development
- `python-style-guide` — description fix, removed ALL CAPS, imperative style
- `python-style-guide-compact` — removed (redundant subset of full version)
- `mixed-r-python-pipeline` — description fix, removed second-person, framed local paths

### Not yet reviewed (need description, writing style, progressive disclosure checks)
- `snakemake-compact`
- `shell-scripting`
- `scverse` and `scverse-compact`
- `plotly` and `plotly-compact`
- `pixi`
- `general-agentic`
- `phosphoproteomics-ptm-analysis`
- `prolfqua-adding-models`
- `bfabricpy`
- `bookdown`
- `school-study-materials`

### Upstream skills (not reviewed, used as-is)
- `r-package-development` — verbatim from posit-dev/skills (description still needs trigger phrase update)
- `testing-r-packages`, `r-cli-app`, `cli`, `lifecycle` — new from posit-dev/skills (2026-04-09)
- `marimo-notebook`, `marimo-batch`, `streamlit-to-marimo` — from marimo-team/skills, descriptions updated
- `skill-creator` — from anthropics/skills

## Other TODOs
- [ ] Check if official skills exist upstream for: scverse, plotly, snakemake
- [ ] Consider whether compact variants (scverse-compact, plotly-compact) are still needed
- [ ] Clean up deprecated fish functions (`claude_python`, `claude_scpython`, `claude_snake`) from `~/.config/fish/functions/`
- [ ] Consider adding more posit-dev/skills: `quarto-authoring` (has many references)
