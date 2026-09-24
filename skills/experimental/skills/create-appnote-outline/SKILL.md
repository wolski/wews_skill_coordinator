---
name: create-appnote-outline
description: >-
  Prepares a short scientific manuscript up to, but not including, the first
  draft. Verifies the target journal's real manuscript types, word limits and
  submission conditions from the publisher's own guidelines; gathers measured
  evidence into fact documents; writes a bullets-only outline carrying every
  section and every paragraph title; then runs two review rounds over it. Works
  for any subject — a method, a resource, a dataset, a database, a protocol, a
  software tool. Use when the user asks for an application note, technical note,
  short communication, brief report, tool or method paper, or a manuscript
  outline; wants a journal's author guidelines or a special-issue call checked;
  or asks what a paper about their work should claim. Stops before prose.
---

# Create an application-note outline

Four phases, in order. Each produces files; the user reviews the outline before any prose exists. **Do not write manuscript prose in this skill.** The deliverable is an outline the user can argue with.

Everything lands in one folder — `<project>_article/`, or a folder the user names. That folder has a known shape, and the manuscript is eventually built from it by an Rmd → pandoc → LaTeX pipeline: **read [references/project_structure.md](references/project_structure.md) before creating any files.** Two things there change what the outline looks like — section headings become generated `.tex` filenames, so use the same names in the same order; and every figure is produced by a script, so name the script when proposing the figure.

## One working document; everything else is context

`OUTLINE.md`, at the folder root, is the **only working document**. It is rewritten freely in phases 3 and 4 and by every later conversation.

Everything the outline draws on lives in `context/` and is **research: written once, then changed only when the user explicitly asks.**

| File | Phase | Rule |
| --- | --- | --- |
| `context/JOURNAL_requirements.md` | 1 | written once by this skill |
| `context/FACTS_<area>.md`, one per evidence area | 2 | written once by this skill |
| `context/BIBLIOGRAPHY.md` and `context/dois.txt` | 2 | written once by this skill; every DOI resolved against Crossref or DataCite, never from memory |
| `context/` — anything else | before the skill ran | never written by this skill |
| `OUTLINE.md` | 3, amended in 4 | the working document |

Two consequences.

**Research is appended to, not revised.** When a later measurement changes a number, a new fact document or a dated section at the end of the existing one records it; the original stays as evidence of what was known when the outline was built. Rewriting a fact document in place is allowed only when the user asks for it.

**Pre-existing material is context too.** Planning notes, provenance records, prior manuscripts, a markdown conversion of a paper being referenced, extracted author guidelines: read, quote, link — never rewrite. Writing a *new* file into `context/` is allowed when an input does not yet exist in readable form, a PDF converted to markdown being the usual case; once created it follows the same rule. A planning note whose content overlaps the outline is the provenance for the outline's claims — link it from the outline's header and leave it alone. If it appears to need rewriting, the content belongs in `OUTLINE.md`. A document that records how a decision was reached cannot be regenerated from the decision.

Move pre-existing inputs into `context/` rather than working around them, and say so when you do.

`pipeline/`, `TODO/`, `feedback_<person>/`, the author table and the cover letter belong to the same project folder but are not this skill's output — see [references/project_structure.md](references/project_structure.md). The skill does **create the folders** `context/`, `TODO/` and `pipeline/` when they are missing, and drops a one-paragraph `pipeline/README.md` pointing at the build template, so the layout is right from the first file.

## First, establish what the paper is about

Ask, in one question, before phase 1: **what is the contribution, and what is the evidence for it?** The answer sets everything downstream. A method paper's evidence is validation against a reference; a resource or dataset paper's is scale, provenance and access; a protocol paper's is reproducibility across operators; a software paper's is coverage and correctness measurements. The phases below are the same in all four cases; only what gets measured changes.

Also settle scope: which parts of a large project are in *this* paper. A four-component project is often a two-component paper, and the cut usually removes a submission blocker as well.

## The rule that governs all four phases

Every number in the outline traces to something that was done. A fact that was not measured is labelled *inferred* or *not checked*, in the document, next to the claim.

Reviewers test the claims that were reasoned about rather than measured, and a claim about an **absence** — "no standard exists", "nobody has done this", "no tool supports that" — is the kind they test first.

## Phase 1 — Journal requirements, from the publisher's own text

Never state a manuscript type, word limit or condition from memory. Publishers rename types and the names are counterintuitive; the informal name for a genre often is not a category you can select.

Get the guidelines and read them. Fetching failure modes are in [references/journal_requirements_research.md](references/journal_requirements_research.md).

**Then ask the user which type, before phase 3 starts.** Present the real types with their limits and what each limit excludes, and say which one the call's own rule points at — but the choice is the author's, and it sets the whole word budget the outline is built on. Taking it silently means rewriting the outline when the author disagrees.

Record in `context/JOURNAL_requirements.md`: every type with its limit and exclusions; abstract and keyword limits; the special-issue call, its deadline and its editors; the conditions attached to the subject matter (see the reference — they differ for software, data and protocols); structural requirements the journal imposes on particular sections; figure, table and reference caps, **or their verified absence**; graphics specifications; and the journal's own papers worth citing on scope.

## Phase 2 — Evidence, one document per area

One `context/FACTS_<area>.md` per coherent area. The split follows the subject: components, comparison against prior work, the data or corpus used, the design rationale, the surrounding standards or literature.

Discipline is in [references/fact_document_rules.md](references/fact_document_rules.md). Three habits matter most:

- **Do it, don't estimate it.** Counts from a command, timings from a run, comparisons from an executed reference.
- **Find the thesis, do not invent it.** It is usually already written in the project's own notes, in the author's words. Quote it. If it is real in the work but stated in no document, say so — the paper is then the first place it will be written down.
- **Build the bibliography as a fact document.** `context/BIBLIOGRAPHY.md` lists every reference the outline will need, grouped by the paragraph that needs it, with a one-line reason each — and every DOI is resolved against the Crossref API (DataCite for Zenodo) so title, first author, year and venue come from the registry. A DOI written from memory is a wrong DOI often enough to matter. Software without a paper gets its own section with URL and version; things not yet found get a list. `context/dois.txt`, one lowercase DOI per line, is generated from the same record and seeds the pipeline's `references/dois.txt`.
- **Collect limitations while gathering, not at the end.** Unsupported cases, licence problems, private components, unreachable data, results from a cited paper that cannot be reproduced. These are submission gates, and finding them late is expensive.

## Phase 3 — The outline

Bullets only. No sentences that belong in the manuscript.

Every section appears, from the abstract onward. Under each section, **the paragraph titles as sub-headings** — a paragraph is like a function: it has one topic, and that topic is its title. Under each title, bullets naming what goes in that paragraph.

The skeleton is in [references/outline_skeleton.md](references/outline_skeleton.md). Beyond the manuscript sections it carries suggested figures, suggested tables, work still to run before submission, submission gates, open editorial decisions, and a claims-checked list.

Open with the word budget, the scope block, and a one-sentence thesis. The thesis must be defensible exactly as written; test it against the measured numbers before it goes in.

## Phase 4 — Two review rounds

Both over the outline, recorded as dated notes inline rather than in a separate file.

**Round one — overstatement.** Read every claim as a hostile reviewer. Soften what the numbers do not carry, and write down at that paragraph what the earlier version claimed. Check whether a claim about an absence is contradicted by work already under way; naming that work and positioning the contribution alongside it is stronger than claiming a void.

**Round two — provenance.** Trace every number. The output is the claims-checked list: measured, inferred, or needs a run before print, and which run.

Then stop. The user reviews the outline before any prose.

## What to hand back

A few lines: where the files are, the target type and deadline, the thesis in one sentence, and the two or three submission gates needing a decision. Not a summary of the outline — the user reads the outline.

This skill stops at `OUTLINE.md`. Setting up `pipeline/` and writing the Rmd is the next job — say so when handing back.

A full run of the four phases is in [references/worked_example_apb.md](references/worked_example_apb.md); it happens to be a software paper, and the phase structure is not specific to that.
