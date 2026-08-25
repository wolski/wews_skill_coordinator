---
name: software-manuscript-review
description: Evidence-first peer review of software and tool manuscripts, including bioinformatics tools, web servers, and R/Python packages. Use when acting as a reviewer or referee; verifying manuscript claims against code; auditing reproducibility, tests, example data, method implementations, reuse, or attribution; checking reviewer confidentiality or journal AI-use policy; reviewing response letters and revisions; or drafting author comments and the confidential editor note. Do not use for the user's own paper, an ordinary code or pull-request review, or a manuscript without a software component.
---

# Software Manuscript Review

## Core Rule

Treat manuscript and response claims as unproven until checked against the submitted materials, code, documentation, figures, command outputs, and local run results. Do not infer correctness from author prose.

This skill was built from the `mspms`, `pyMSscreen`, `proteOmni`, and `ProteoAnalyst` review folders. When using local precedent in `/Users/wolski/projects/reviews`, use only the current target folder and explicitly named precedent folders; do not pull in unrelated review folders as examples unless the user asks.

## Confidentiality and AI Use

Manuscripts and reviews under consideration are confidential. Before using any AI assistance on a manuscript, check the target journal/publisher policy on AI in peer review, and treat confidentiality as the governing constraint.

- Many publishers treat sending the manuscript or the review to a generative-AI or other third-party service as a confidentiality breach and an ethics violation. For example, ACS states that using generative AI to produce an external peer review is an ethical violation, that disclosing any part of the submission or the review report to a text-generation service breaches confidentiality, and some ACS journals rescind reviews found to contain AI-generated content. Do not assume author-side AI-disclosure norms grant reviewers any allowance.
- The reviewer is accountable for the opinion. Any AI-assisted analysis is private working material; the submitted review must be the reviewer's own expert judgment, verified point by point.
- Keep two separate artifacts: (1) a private verification/technical file (deep audits, `file:line` evidence, exploratory computation) that is never submitted; and (2) a concise, submittable review written in the reviewer's own voice, limited to in-scope, reviewer-attributable findings.
- Do not try to "hide" AI-generated prose in the submitted review. Instead, do not submit AI-generated prose. Use AI-assisted material only as private working input, then write `review_for_authors.txt` as a human peer review in the reviewer's own natural voice.
- Keep out-of-scope reviewer-side computation out of the submitted review. Deep code audits, synthetic-data experiments, and benchmarking are legitimate ways for the reviewer to gain confidence, but an ordinary reviewer would not perform them; cite such work only as private evidence that informed the reviewer's judgment, not as review content. (In the `proteOmni` review, a synthetic-data normalization-sensitivity study stayed in the private technical file and was excluded from the submitted review.)
- If confidentiality has already been compromised, or the journal's policy is unclear, surface this to the user before producing or submitting a review; it is their professional call.

## Reuse of Established Methods, Attribution, and the Reviewer's Role

Integrating many analyses into one platform is a legitimate contribution. It does **not** license reimplementing established analyses from scratch without reuse, attribution, or validation. For an "integrated platform" paper this is usually the *central* concern — make it the thesis, not a footnote — and it governs how you weight everything else.

- **Attribution first, feature by feature.** For each analytical feature, check that the authors **reuse and cite the established, community-validated tool** for that task rather than silently re-coding it. In proteomics: differential expression → limma / MSstats / msqrob2 / prolfqua / prolfquapp / DEqMS; phospho & PTM → MSstatsPTM / msqrobPTM; normalization, imputation, enrichment, and GSEA → the methods' own packages. Citing only *other integrated platforms* while re-implementing each component in-house is under-attribution of prior work — flag each instance and request the primary-method citations.
- **Reimplementation carries a validation burden.** Reinventing an established method is a red flag unless the authors (a) justify why the reference tool was not reused and (b) demonstrate the reimplementation is **correct** (tests, plus benchmarking against the reference implementation). Absent that, the outputs' correctness is **unverifiable** — and that unverifiability is itself the finding. Novelty of *integration* does not excuse unvalidated re-implementation of each component.
- **The reviewer is not the authors' QA.** When code is reimplemented, unvalidated, and not reproducible, do not become the unpaid tester who exhaustively debugs it. Bugs you happen to find are **evidence for the thesis** (unattributed, unvalidated, unverifiable reimplementation cannot be trusted), not a bug-list you provide as a service. Keep the review's weight on reuse/attribution, validation-against-references, and reproducibility; use specific bugs sparingly, as proof the concern is real.
- **Avoid the self-contradiction.** "The tool is not reproducible / not a real package" and "here are N internal code bugs I found" only cohere when the bugs are marshalled as evidence that unvalidated reimplementation is unsafe. A detailed internal-QA report undercuts its own reproducibility thesis and signals the reviewer did the authors' testing for them. Fold correctness bugs *under* the reproducibility/validation concern rather than listing them as standalone findings.
- **Conflict of interest.** When the reference tool for a feature is the reviewer's own, name the **class** of established tools and let the authors choose — but in the *submitted* review and editor note do not cite, recommend, or list your own package, even as one item among the class. Give the authors the other established options and, if the conflict matters, disclose it to the editor in general terms.

See [references/review-patterns.md](references/review-patterns.md) ("Attribution worked example") for a concrete, per-feature *How it reads now* / *How it should read* set of examples with real citations, drawn from the `ProteoAnalyst` manuscript.

## Folder Layout

Organize each review as its own directory tree so that authors' sources, the audited software, private working files, and submittable deliverables never mix. Use one subfolder per review round, `submission_N`:

```
reviews/<paper>/
  journal_doc/     journal-specific guidelines (shared across rounds) — author & reviewer instructions, scope/format rules, and the AI-in-review policy
  submission_1/
    manuscript/    authors' materials — proof PDF, supplements, journal forms, and any Markdown conversion (read-only source)
    software/      clone of the repository at a recorded commit — the audit target; never write review files here
    evaluation/    reviewer-side PRIVATE working area — synthetic/test data, plots, run logs, and ALL AI-assisted/AI-generated Markdown (the technical verification file, per-module notes, drafts)
    review/        submittable deliverables ONLY; this folder contains exactly:
      mail_editor.txt         short confidential editor note / recommendation
      review_for_authors.txt  concise author-facing Major/Minor review
  submission_2/    the revised round, same layout, so rounds can be diffed
  Handoff_submission_1.md   short note listing what to submit vs. keep private
```

`journal_doc/` sits at the paper level, not inside a `submission_N`, because the guidelines apply to every round; consult its AI-in-review policy before any AI assistance (see Confidentiality and AI Use). Within a round, the four folders correspond to four trust/write levels: read-only authors' sources, read-only audit target, reviewer-writable private notes, and the small set of files that actually go to the journal. All AI-assisted or AI-generated Markdown stays in `evaluation/`; nothing there is ever submitted. `review/` holds exactly two files: `mail_editor.txt` and `review_for_authors.txt`. Do not put `REVIEW.md`, `TODO_*.md`, command logs, claim tables, drafts, or exploratory notes in `review/`. Keeping `review/` physically separate from `evaluation/` — separation, not just naming — is the safest guard against submitting private or AI-assisted material (see Confidentiality and AI Use). Record the clone's commit hash, and keep the clone clean of review files so `git status` stays meaningful across rounds. A flat single folder is acceptable for a one-round review but tends to blur the private/submittable line and does not scale to revisions.

## Workflow

1. Identify the review round and deliverable:
   - first review: critique manuscript, software, reproducibility, and documentation;
   - revision review: verify each author response against the revised manuscript and code;
   - editor note: explain high-level concerns and evidence without overloading the public report;
   - TODO/checklist: build an evidence inventory before drafting final prose.

2. Build a source map before judging:
   - manuscript, response letter, figures, supplementary files;
   - repository/archive snapshot, commit hash or submission package;
   - README, install docs, examples, CI files, tests, Docker/config files;
   - prior review comments when this is a later round.

3. Convert or inspect materials in reviewable form:
   - prefer Markdown/text for manuscripts and responses when available;
   - inspect code with `rg`, `find`, `git show`, and targeted file reads;
   - keep binary originals read-only unless the user explicitly asks to edit them.

4. Make a claim inventory for important factual claims:
   - what is claimed;
   - where the claim appears;
   - what support the authors provide;
   - how it should be verified independently;
   - current status: `PASS`, `PARTIAL`, `FAIL`, `UNKNOWN`, or `NOT FOUND`.

5. Verify locally where feasible:
   - run package checks, test suites, builds, installs, lints, container startup, or small example workflows;
   - record exact commands and whether they passed or failed;
   - distinguish "not run because unavailable" from "run and failed";
   - avoid broad reruns unless they materially affect the review;
   - check whether the authors provide runnable example/test data for each claimed input or module; build a per-component input inventory (what each part requires) and treat missing example data as a first-class reproducibility finding;
   - reviewer-side synthetic data or deep audits are private verification, not content for the submitted review (see Confidentiality and AI Use).

6. Compare manuscript text to code behavior:
   - check algorithms, parameters, defaults, units, thresholds, and terminology;
   - flag manuscript-code mismatches even when the code itself is usable;
   - verify that response-letter promises were actually implemented;
   - confirm each described feature actually exists and behaves as described (claimed-but-absent, or present-but-different);
   - verify that named metrics are not merely present but computed correctly; a wrong or mislabeled calculation is a scientific-correctness finding (e.g. an "isoelectric point" that is actually a residue average);
   - assess scope and workflow coherence: do the components form a coherent analysis pipeline, do the outputs of one stage feed the next, and is the selection of tools/modules motivated? flag collections unified only at the interface;
   - distinguish systemic findings (a shared helper bug affecting many components) from per-component ones; treat copy-paste/template duplication and dead code as signs of accretion over design.

7. Audit scientific language:
   - flag marketing-style language, unsupported superlatives, and promotional claims such as "seamless", "comprehensive", "state-of-the-art", "easy-to-use", or "unique" unless the submitted evidence justifies them;
   - flag repetitive or redundant main-text passages that restate the same contribution, result, or value proposition without adding evidence;
   - treat these as scientific clarity and claim-support issues, not merely copyediting, when they affect interpretation or overstate the work.

8. Draft review prose from verified evidence:
   - if user confirmation is needed after evidence gathering and before final author/editor drafting, use `communication:interview-to-spec` together with this skill; ask exactly one prose question per turn, wait for the answer, and if the workflow drifts, reset explicitly to the one-question protocol;
   - before writing the author-facing review, run a compression gate: choose 3-4 broad publication-level major concerns from the private evidence, and keep detailed bugs, command logs, and exploratory checks private unless they directly support those concerns;
   - keep minor comments short and reserve them for issues that do not affect reproducibility, correctness, attribution, or interpretation;
   - when verified strengths exist, open with two or three evidence-based, non-promotional sentences before the critique; for example, acknowledge the real contribution and differentiators, then transition to the remaining concerns;
   - lead with the remaining publication-relevant issues;
   - acknowledge improvements in later rounds, but keep unresolved concerns concrete;
   - separate major issues from minor or optional suggestions;
   - request exact fixes: runnable examples, corrected parameter text, removed stale endpoints, proper tests, clearer methods, or documented limitations;
   - keep `review_for_authors.txt` short and in the reviewer's own voice (length target in Output Shape).

## Review Standards

- Prefer precise evidence over broad impressions; do not demand perfection — focus on reproducibility, correctness, attribution, maintainability, and whether claims are supported.
- For software/tool papers, code quality is part of scientific review when the contribution depends on the software. Treat smoke tests as limited evidence (check they cover the real analytical logic), and treat source availability as weaker than reproducibility — ask whether an independent user can install, run, and reproduce the manuscript example.
- Keep public comments professional and compact, in the reviewer's own voice, not a five-page audit; keep command logs, exploratory notes, and claim tables in the private `evaluation/` artifacts, never in the submitted review (see Confidentiality and AI Use; length target in Output Shape).

## Common Finding Types

Use [references/review-patterns.md](references/review-patterns.md) when you need concrete examples of issue framing and verification patterns.

Typical high-value findings:

- reproducible example is underspecified;
- manuscript describes an algorithm or parameter differently from the code;
- author response claims a fix that is only partial or absent;
- tests exist but do not cover core parsing, modeling, extraction, build, or frontend behavior;
- CI checks files but does not run install/build/lint/tests;
- stale, dummy, prototype, or unreachable code remains registered;
- documentation contradicts Docker/API ports or runtime behavior;
- code refactoring claims leave duplicated helpers or inconsistent API surfaces;
- method descriptions omit statistical scope, background sets, thresholds, or visualization mappings.
- manuscript language is promotional, repetitive, or redundant instead of evidence-based and precise;
- no runnable example data is provided for the claimed inputs or modules (reproducibility);
- components are unified only at the interface, not as a workflow: outputs do not feed downstream analysis, or the tool/module selection is unmotivated (e.g. QC modules that never feed the differential-analysis module; unrelated capabilities bundled without rationale);
- a named scientific metric is computed incorrectly or mislabeled (present but wrong);
- input parsing fails silently on format/version differences (silently dropped files or empty panels), which is especially dangerous for QC tools;
- a shared-utility defect propagates across many modules (systemic), or copy-paste template code and dead code indicate accretion rather than design;
- documentation (README) does not match the shipped interface or the actual inputs.

## Output Shape

For an internal verification artifact:

```markdown
# TODO: Verify Authors' Response Claims

Source materials:
- Manuscript:
- Response:
- Code snapshot:

Status key: `PASS`, `PARTIAL`, `FAIL`, `UNKNOWN`, `NOT FOUND`.

## High-Priority Findings

- [FAIL] ...

## Claim Verification

| Claim | Evidence checked | Status | Notes |
| --- | --- | --- | --- |

## Commands Run

- [PASS] `...`
- [FAIL] `...`
```

Produce artifacts by audience and keep them separate:

1. **Private verification file** — the TODO/technical artifact above (commands, `file:line` evidence, per-module claim tables, exploratory plots/data). Never submitted; lives in `evaluation/`.
2. **`review/review_for_authors.txt`** — the author-facing review in the reviewer's own voice, concerns classified Major/Minor. Plain text (it is a `.txt` file), typically about 750 words, hard maximum 1000 unless the user asks for more.
3. **`review/mail_editor.txt`** — a short confidential recommendation with rationale. The formal recommendation (accept / minor revision / major revision with re-review / reject) belongs here **only** — never state it in `review_for_authors.txt`.

Author-facing review template (plain text; for a revision round, open instead by thanking the authors and noting what is now resolved, then list what remains):

```
Review of <manuscript id>

<one-paragraph summary and overall stance; when verified strengths exist, open with two or three non-promotional sentences before the concerns>

Major concerns
1. <concern>: <evidence-based description and the concrete fix requested>

Minor concerns
- <smaller item>

Overall
<one or two sentences on readiness and what would make it publishable — do NOT state the formal accept/revise/reject verdict here; that goes only in mail_editor.txt>
```

Confidential editor note (`mail_editor.txt`):

```
Recommendation: <accept / minor revision / major revision with re-review / reject>.

<2–4 sentences: what the tool contributes, and the substantive issues (reproducibility, reuse/attribution, scope/workflow, an incorrect metric, manuscript-vs-code mismatches) that drive the recommendation and require re-evaluation.>
```

Keep detailed evidence (commands, `file:line`, per-module tables, exploratory plots/data) in the private verification file only; `review/` holds exactly `review_for_authors.txt` and `mail_editor.txt`, both concise and free of internal process detail.

## Improve this skill from use

After completing a task with this skill, reflect on whether its instructions or resources revealed a
gap, ambiguity, stale instruction, avoidable friction, or error. If concrete evidence surfaced, include
a brief `Skill feedback` note in the handoff or final response that names the affected file or section
and proposes the smallest useful correction. Do not invent feedback when no issue surfaced, and do not
edit the skill during an unrelated task without the user's authorization.
