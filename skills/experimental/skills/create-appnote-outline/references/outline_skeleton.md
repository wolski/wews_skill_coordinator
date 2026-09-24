# Outline skeleton

Bullets only. Paragraph titles as bold sub-headings under each numbered section; bullets under each paragraph title say what belongs in that paragraph, not how it will be phrased.

## Header block

- target journal, manuscript type, special issue, deadline, word limit and what it excludes
- **thesis**, one sentence, defensible as literally written
- **scope**: which packages are in this paper, which are named only as companions, and what that cut removes
- links to the requirements document and every fact document

## Manuscript sections

Each heading below becomes a generated `sections_<variant>/<slug>.tex` file when the manuscript is built, with the slug in brackets. Use these headings, in this order, unless the journal dictates others — then use the journal's and let the slugs follow.

**Abstract** — word limit stated in the heading. Bullets in the order the abstract will run: problem, gap, approach, what is preserved, scale, availability.

**1. Introduction** `[introduction]`, with a target word count. Most journals require an explicit comparison against existing approaches — check the guidelines, because some make it mandatory — so plan the comparison as its own paragraphs: what each existing approach solved, what it leaves out, and why the obvious fix is unavailable. End with where the contribution sits in the surrounding field.

**2. Experimental Section** `[design-and-implementation]`, or whatever the journal calls its methods section. Note in the outline if the journal forbids bullets here, because the prose will need complete sentences, and check whether this section is excluded from the word count — it often is, which changes the whole budget. Paragraph titles describe how the thing works and how it was evaluated, in the order a reader would need them. For a method: the formulation, the assumptions, the reference it is compared against. For a resource: the sources, the processing, the schema, the access route. For a protocol: materials, steps, controls. For software: the data model, the extension format, validation, outputs, testing, installation.

**3. Results and Discussion** `[results-and-discussion]`, the longest section. One paragraph title per result. Each carries the measurement, not the impression.

**4. Limitations and Future Work** `[limitations-and-future-work]`. Everything gathered eagerly in phase 2. Planned work is stated as planned; never as implemented.

**5. Conclusions** `[conclusions]`. Interpretation only. Journals commonly forbid a restatement of results here — check and note it.

**6. Data and Code Availability** `[data-and-code-availability]`, under whatever heading the journal uses. Repositories, licences, accessions and DOIs, and the reviewer's route to everything the paper relies on that does not depend on asking the authors.

**7. Supporting Information** — its own `.Rmd` variant, not a section. Draft contents as a numbered list, S1..Sn. Anything measured but too detailed for the main text goes here, including negative results and full per-dataset tables.

**8. Author Contributions, Acknowledgements, AI-use disclosure** `[author-contributions]` `[acknowledgements]` `[ai-use-disclosure]` — three short files, one each.

## The sections that are not manuscript sections

These make the outline actionable, and are the reason to write one at all.

**Suggested figures** — each with what it shows and what data it needs.

**Suggested tables** — same, plus whether a table is better as Supporting Information.

**Still to run before submission** — the outline's most useful list. Each entry names what will be done, on what inputs, and which claim in the outline it supports. Written now, these become the work plan; written later, they become the reason the deadline slips.

**Submission gates** — hard requirements, not preferences. Anything private that must be public, a licence conflict, a missing accession or DOI, material a reviewer cannot reach, a consent or ethics statement not yet obtained.

**Editorial decisions** — the questions only the author can answer: the manuscript type and therefore the word budget, author list and order, which material moves to Supporting Information, the title, and how any borderline component is presented.

**Claims checked** — the output of review round two. One bullet per headline claim: measured, inferred, or needs a run before print, and which run. Amend this list rather than rewriting it when a claim later changes.

## Recording the reviews

Both review rounds leave dated italic notes inline, at the paragraph they changed, saying what the earlier version claimed and why it was weakened or strengthened. A separate review file gets read once; an inline note is read every time someone edits that paragraph.
