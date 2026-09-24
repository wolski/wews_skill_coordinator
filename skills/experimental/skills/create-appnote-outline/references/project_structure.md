# Article project structure and the build pipeline

The outline this skill produces is the first file of a manuscript project that already has a shape. Follow it from the start, so the outline's sections land where the build expects them.

Reference implementation: `queue_generator/qg_article/`, a JASMS application note carried through to submission.

## Folder layout

```
<project>_article/
  OUTLINE.md                   the working document: phase 3, amended in 4 and after
  context/                     research, written once, changed only on request
    JOURNAL_requirements.md      phase 1
    FACTS_<area>.md              phase 2, one per evidence area
    BIBLIOGRAPHY.md              phase 2, verified DOIs grouped by outline paragraph
    dois.txt                     phase 2, seed for pipeline/references/dois.txt
    <pre-existing inputs>        planning notes, converted PDFs, prior manuscripts
  TODO/                        working notes, review actionables, response letters
  feedback_<person>/           one folder per reviewer or co-author, as received
  authors.tsv                  author list, affiliations, ORCIDs, in submission order
  cover_letter_<journal>.txt
  pipeline/                    everything below
```

`context/` is research: the skill writes its requirements and fact documents there once, and nothing in it changes afterwards unless the user asks. `TODO/` and `feedback_<person>/` are working notes as received. None of it is touched by a build.

## The pipeline: one Rmd is the source of everything

```
manuscript.Rmd ──knit──▶ manuscript.knit.md ──pandoc──▶ manuscript.docx
                              │
                              └──pandoc --natbib──▶ manuscript.full.tex
                                        │
                                  full-pdf / full-html      (check the conversion alone)
                                        │
                              split_tex_sections.py
                                        │
                                  sections/*.tex
                                        │
              main.tex ──\input{sections/_inputs}──▶ main.pdf   (achemso, submission)
```

Three outputs from one source: the publisher-class submission PDF, a standalone bookdown PDF, and a DOCX for co-authors who comment in Word.

## What is hand-maintained and what is generated

| Path | Status |
| --- | --- |
| `<name>.Rmd` | **the source.** Title and abstract live in its YAML and flow everywhere else |
| `main_<variant>.tex` | hand-maintained publisher wrapper: document class, authors, affiliations |
| `sections_<variant>/*.tex` | **generated. Never edit** — regenerated on every build |
| `title_<variant>.tex`, `abstract_<variant>.tex` | generated from the Rmd YAML |
| `references/dois.txt` | **auto-derived** from the citations in the Rmd. Never hand-maintained |
| `references/doi_references_key.bib` | generated; keys are the lowercase DOI |
| `figures/` | static figures and the scripts that make them |

Citing is therefore just writing `[@10.1021/acs.jproteome.4c00911]`, or a DOI markdown link that a helper rewrites. The DOI set is re-derived and the bibliography refetched whenever it changes.

## The build interface

A `Makefile` is a thin wrapper over a self-contained orchestrator CLI (`uv` script, cyclopts, `./qgpub` in the reference project). The CLI owns the dependency chain with make-style mtime checks, so one command knits, fetches references, builds the full `.tex`, splits sections and runs `latexmk` as needed.

Typical targets: `article`, `supplement`, `docx`, `figures`, `clean`, plus a `pack_submission.sh` that zips what the publisher's system wants.

Variants — article, supplement, and sometimes a shorter note — are separate `.Rmd` plus `main_*.tex` pairs sharing the same scripts and bibliography.

## Why the outline should know about this

**Section names become filenames.** In the reference project: `introduction.tex`, `design-and-implementation.tex`, `results-and-discussion.tex`, `limitations-and-future-work.tex`, `conclusions.tex`, `data-and-code-availability.tex`, `author-contributions.tex`, `acknowledgements.tex`, `ai-use-disclosure.tex`. Give the outline the same section headings, in the same order, and the split is a no-op rather than a reconciliation.

**Figures are code.** A figure named in the outline should be produced by a script in `figures/`, not pasted in. Name the script when the figure is proposed.

**The abstract has one home.** It lives in the Rmd YAML and is generated into a LaTeX fragment. Nothing else should carry a second copy.

**Word counts are measured on the built document**, not on the outline. The outline's per-section budgets are targets to check against the knitted output once prose exists.

## Where this skill stops

This skill produces `OUTLINE.md`. Setting up `pipeline/` and writing the Rmd is the next job, not this one. Say so when handing back.

What the skill does do: create `context/`, `TODO/` and `pipeline/` when missing, and write `pipeline/README.md` — one paragraph saying the folder is not set up yet, what the chain will be, and where the template lives (`queue_generator/qg_article/pipeline/`, with its orchestrator, `scripts/`, `Makefile` and `pack_submission.sh` as the pieces to copy). That README is the only file the skill writes outside the three document kinds, and it is a pointer, not a build.
