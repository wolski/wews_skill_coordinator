# Fact documents

One `context/FACTS_<area>.md` per evidence area. Dense, numeric, and unflattering where the facts are unflattering — and **written once**. A fact document is the record of what was known when the outline was built. A later measurement gets a dated section appended, or a new document; the existing text is rewritten only when the user asks. `OUTLINE.md` is where claims move; the facts stay put.

## Four states, never collapsed

Every claim is one of:

- **measured** — something was run or done; quote the command, the instrument, the query
- **inferred** — derived from something measured; say from what
- **not checked** — named as a gap, not omitted
- **contradicted** — the project's own documents say one thing and reality says another; the most valuable kind

Collapsing "returned zero rows", "the run failed", "the file was missing" and "I did not check" into one sentence destroys the finding.

## What to measure, by kind of paper

The phases do not change with the subject; this list does.

**A method or algorithm.** Agreement with a reference implementation, on named inputs, with the residual. Behaviour at the edges where it is expected to fail. Cost against problem size. Sensitivity to the parameters a user will actually change.

**A resource, dataset or database.** Record counts, total size, the schema, provenance for every part, licences, checksums, accessions or DOIs, update cadence, and how a reader reaches it without asking the authors.

**A protocol.** Reproducibility across operators, sites or days; the failure modes and their frequency; the cost and the time; what an equivalent established protocol gives.

**A software tool.** Coverage against the space it claims, correctness against known answers, cost in time and memory with the machine stated, extension cost for a new case, and what it refuses rather than silently mishandling.

In every case: reconcile the claimed scope against the demonstrated scope, and report `N of M covered` with the shortfall named. That number is usually a headline result.

## Reconcile, do not assume

Two counts that appear to conflict are not a conflict until joined. Do the join, and report what the join leaves over — that residue is the honest coverage claim.

## The thesis is already written somewhere

Search the project's planning notes, decision records, grant text and commit messages for the author's own statement of why the work exists. Quote it exactly. If the idea is real in the work but written in no document, report that: the paper becomes the first place it is stated, which raises its value and means nothing can be cited for it.

## Limitations, gathered eagerly

A dedicated section in the relevant fact document, written while gathering rather than at the end. Include the awkward ones: cases the work does not cover, components that are private or unreleased, licence incompatibilities, data a reviewer cannot reach, results from a cited paper that could not be reproduced and why, and the absence of any independent uptake.

## Stale documentation

Every place where the project's own documents disagree with reality, with the file and line. Two uses: they are cheap fixes before submission, and a reviewer who finds them first reads them as carelessness.

## Contradictions between a recorded decision and what was done

When a decision record rejected an approach and the work went ahead with it anyway, do not pick a side. Record both, then state the narrow case in which the original objection still holds. That reasoning is usually publishable material in its own right.
