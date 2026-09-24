# Worked example: APB for Journal of Proteome Research

The run this skill was extracted from, September 2026. Useful as calibration for what the four phases actually produce.

## Phase 1 output

`JPR_requirements.md`. The finding that changed the plan: JPR has no Application Note type. The real types are Article 8,000 and Technical Note 4,500, among others, and the special-issue call routes a novel tool to the article and an update to a published tool to the technical note. Verified absence of any figure, table or reference cap. Two of the journal's own papers identified as required citations.

**The type decision is the author's, not the guideline's, and it must be taken before phase 3.** This run first planned an 8,000-word Article on the call's own rule, then the author chose the 4,500-word Technical Note, which forced a rewrite of the outline's whole word budget. Present the real types with their limits and ask which one, rather than recommending the one that buys the most room.

One structural fact made the rewrite cheap, and is worth checking for any journal: JPR's count **excludes the Experimental Section**, so halving the limit cost about 600 words of results, not 3,500.

## Phase 2 output

Six fact documents: the main package, the satellite packages, the test corpus, a second larger corpus, design and prior art, and the standards landscape.

What they surfaced that a code read alone would not have:

- an under-sold contribution — nine parameter formats reduced to one 36-field typed record — stated nowhere in the repository
- the thesis, in the author's own words in a planning note, implemented in the rules and written in no document
- a corpus reconciliation: 186 of 202 datasets covered, with the 16 named
- submission gates: one package private, an MIT-versus-GPL conflict between packages, nothing on a package index
- a second corpus carrying five public accessions and a checksummed DOI, which closed the data-deposition gate
- a measured negative result about a schema language that became a paper section

## Folder, after the fact

The APB folder was restructured to the layout in `project_structure.md` on 9 Sep 2026, in two passes. The first put the fact documents at the root beside the outline; the author corrected that: research goes in `context/`, written once and changed only on request, and `OUTLINE.md` is the one working document. Final state: `OUTLINE.md` at the root; `context/` holding `JOURNAL_requirements.md` (renamed from `JPR_requirements.md`), six `FACTS_*.md` and the pre-existing planning note; the capture TODO in `TODO/`; `pipeline/README.md` as the pointer. Twenty-nine relative links verified after each move. Starting with the layout would have cost nothing; retrofitting cost two rounds of link repair.

## Phase 3 and 4 output

One outline, roughly 3,700 words, bullets only, eight manuscript sections plus figures, tables, benchmarks, gates, decisions and claims.

Round one weakened the thesis: "preserves the union, not the intersection" did not survive its own measurement, which was 25 of 61 columns retained. It became "keeps far more, and makes the mapping auditable".

A later scan weakened a second claim the same way. "There is no living PSI standard for quantitative result matrices" was true but reckless — a community effort to build one was under way, and several likely reviewers were members of it. It became "no *adopted* standard covers this, and here is the active work; the tool is its test bed."

Both are the same lesson: a claim about an absence is the one a reviewer tests.
