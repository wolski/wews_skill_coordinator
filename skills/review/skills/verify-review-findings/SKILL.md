---
name: verify-review-findings
description: Verify code-review findings before reporting them, and turn confusing-but-correct code into structural fixes. Use this skill when reviewing code, triaging or acting on review findings (e.g. a review TODO), deciding "is this actually a bug?", confirming or refuting a suspected defect, or fixing a bug found in review. Enforces a confirm-or-refute discipline that prevents false positives (flagging a non-bug) caused by non-obvious language semantics, helpers doing hidden double duty, and guards that live elsewhere in the flow — and treats a false positive triggered by unclear code as a real communication defect to be fixed structurally. Complements multiagent-review (which orchestrates the review) by governing the rigor of each individual finding.
---

# Verify Review Findings — Confirm or Refute, Fix Structure

A review finding is a **hypothesis, not a verdict**. Before reporting any correctness finding, confirm or
refute it against the code's actual semantics and full control/data flow. A false positive is expensive: it
erodes trust in the whole review, and acting on it wastes effort or introduces a regression "fixing" code that
was correct.

This skill governs the rigor applied to each finding. For dispatching a multi-specialist review panel, use the
`multiagent-review` skill; for R-specific engineering judgment, use `advanced-r-engineering`. This skill applies
in single-pass review too.

## The core discipline: confirm or refute before reporting

Never flag a suspicious-looking line in isolation. For every candidate correctness bug, do all of the following
before writing it down as a bug:

1. **Read the whole function, not the line.** The disproof of a suspected bug often lives a few lines away —
   in an earlier loop, a sibling branch, or the function's preamble.

2. **Find where inputs are validated.** A guard that makes the suspicious line safe may run earlier in the
   same function, in a different loop, or in the caller. If a typo'd/missing input would already have errored
   upstream, the "silent wrong result" you imagined cannot happen.

3. **Verify the exact semantics of any stdlib/library call the finding hinges on — empirically.** Do not trust
   intuition about ordering, recycling, `NA` propagation, partial matching, or silent coercion. Run a two-line
   snippet and look. In R:

   ```r
   # Does intersect() return first-arg order or second-arg order? Check, don't guess.
   base::intersect(c("group_A", "-", "group_B"), c("group_B", "group_A"))
   #> "group_A" "group_B"   <- first-argument (contrast) order, operators dropped
   ```

   ```bash
   Rscript -e 'print(base::intersect(c("a","-","b"), c("b","a")))'
   ```

4. **Trace callers and reachability.** Is the suspicious path on a primary path, or is it dead / deprecated /
   guarded out? A "bug" in an unreachable branch is a different (lower) severity than one on the hot path.

5. **Construct the concrete failure.** State it as: *input X → produces wrong output Y, expected Z.* If a
   reproducing input cannot be constructed, the finding is probably not a bug — downgrade or drop it.

If a finding survives all five, it is real. If it does not, it is a **false positive** — but stop before
discarding it.

## Classify every finding

- **TRUE BUG** — a concrete reproducing input produces a wrong result or a crash. Fix the root cause
  (see below).
- **FALSE POSITIVE — code is correct and clear.** Drop it. Record the evidence (the semantic check, the
  upstream guard) so it is not re-flagged next review.
- **FALSE POSITIVE — code is correct but *misread because it is confusing*.** This is the important case: the
  confusion is itself a real, lower-severity defect — a **communication bug**. Correct code that an experienced
  reviewer reads as broken will be "fixed" into an actual bug eventually. The remedy is **structural
  clarification**, not a behavior change.

Reporting a finding honestly includes saying "this specific claim was a false positive, and here is why" — with
the evidence. That is more valuable than silently deleting it.

## Why correct code reads as buggy: the confusion smells

When a false positive traces to confusing structure, look for these signatures — each is a structural defect
worth fixing even though behavior is correct:

1. **Load-bearing reliance on non-obvious language semantics, uncommented.** Correctness rides on a detail many
   competent programmers get wrong: set-operation ordering, vector recycling, `NA`/`NULL` propagation, partial
   argument matching, implicit numeric/character coercion. No comment flags it. The reader assumes the common
   (wrong) mental model and "finds" a bug.

2. **A helper doing implicit double duty.** One opaque call quietly does two or three jobs at once (e.g. filter
   *and* reorder *and* strip tokens). From the call site it looks like one thing, so its other effects read as
   missing or wrong.

3. **Guards separated from the code they protect.** Validation in loop 1; the code that depends on it in
   loop 2. Reading loop 2 alone, the protection is invisible and the code looks unguarded.

4. **Dead or fallback branches that silently do something arbitrary.** A branch that "handles" malformed input
   by guessing (e.g. taking the first two tokens) instead of rejecting it. It is both unreachable noise and a
   latent wrong-result generator.

5. **Multi-pass designs over an opaque intermediate representation.** Correctness is smeared across passes over
   a token list / index map / scratch column, so no single place states what the function guarantees.

## The structural-fix playbook

When the diagnosis is "correct but confusing," restructure so correctness is self-evident. Prefer, in order:

- **State and enforce the contract up front.** Validate inputs at the top; `stop()`/raise with a clear message
  on violation. The function's precondition becomes readable, not implicit.
- **Replace clever double-duty calls with explicit single-purpose steps.** One statement, one job.
- **Co-locate guards with the code they protect.** Move validation next to the operation that relies on it, or
  merge the passes so the guarantee is visible where it matters.
- **Delete dead fallbacks.** Do not preserve arbitrary silent behavior "just in case." Reject malformed input
  loudly instead.
- **Collapse to a single linear pass** when the multi-pass design exists only to thread an opaque
  intermediate.
- **Comment only the residual.** Add a comment exactly where a genuinely non-obvious, load-bearing semantic
  remains — not as a substitute for restructuring.

The test: after the change, a competent reviewer reading the function top-to-bottom sees the contract and the
data flow directly, with no off-screen subtlety to misread.

## Then fix it properly

For both true bugs and structural clarifications:

- **Fix the root cause in the correct upstream location** — never a bandaid (a `tryCatch` swallow, a normalize
  wrapper, a skip condition) unless explicitly requested.
- **Add the test first.** Write a test that reproduces the bug (or pins the contract), run it against the
  unchanged code to confirm it fails (or, for a false positive, confirm it *passes* — locking the behavior the
  reviewer misread so it is not re-flagged), then make the change and confirm green.
- **Lock the previously-misread behavior with a regression test.** If a reviewer misread `intersect` ordering
  once, a test asserting the order makes the next misread impossible to land.
- **Run the affected suite and any downstream consumers**; report pass/fail honestly, including pre-existing
  warnings.
- Record the disposition (true bug fixed / false positive with evidence / restructured for clarity) where the
  finding was tracked.

## Worked example

A detailed end-to-end case — a real review finding that was a false positive on two counts, the empirical
checks that refuted it, the one genuine narrow bug it masked, and the structural rewrite that removed the
confusion — is in [references/false-positive-case-study.md](references/false-positive-case-study.md). Read it
for a concrete model of the whole loop: refute → classify → restructure → test-first → lock.
