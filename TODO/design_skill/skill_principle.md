---
name: design-principles
description: >-
  Two bounded design principles for Python, and the part refactoring catalogues leave out: exactly where
  each one stops. Principle 1 — a parameter's type should name the smallest capability the function
  actually exercises, not the concrete class the caller happens to hold. Principle 2 — branching on what
  something *is* in order to decide what to *do* is a missing polymorphism. Use this skill when deciding
  whether an abstraction is warranted at all: should this parameter be a Protocol or ABC, should this type
  be split, is this if/elif chain acceptable, is `X | None` the honest signature, am I widening `list` to
  `Iterable` truthfully, does this validator mean the type is really several types. Use it when a reviewer
  asks for "less coupling" or "more abstraction" and you need to judge whether they are right, and before
  adding any interface, Protocol, ABC, or base class. To instead sweep an existing package for
  branch-based discrimination, use the polymorphism-over-discrimination skill.
---

# Two design principles, and where they stop

> Both principles are easy to state, easy to over-apply, and the over-application is a real failure rather
> than a theoretical one. So each is stated three ways: **statement**, **violation shapes** (what to look
> for), and **where it stops** (what to leave alone). A finding is only a finding if it passes the
> statement *and* clears the bounds.
>
> For a mechanical sweep of an existing package — a candidate finder, greppable shapes, worked remedies —
> use `fgcz-infrastructure/skills/polymorphism-over-discrimination/SKILL.md`, which narrows principle 2
> into an audit workflow. This skill is the judgement layer above it.
>
> **Origin.** Java/OO practice: composition over inheritance, interfaces for code reuse, and avoiding
> `if/else` cascades. Neither principle is novel — principle 1 is Dependency Inversion plus Interface
> Segregation; principle 2 is Fowler's *Replace Conditional with Polymorphism* (refactoring catalogue,
> 1999).
>
> **Validation status, so the two are not weighted equally.** Principle 2 was applied twice to a
> 97-module Python package and produced 12 findings that survived review. Principle 1 produced **zero**
> — its strongest shape (P1.2, a record passed whole where the body reads one field) fired on nothing
> that was worth changing. Keep it as a lens while reading; do not open a finding on it without a
> named second implementation.

---

**The direction both principles point in is the same one: polymorphism.** Principle 1 asks what a function
is allowed to know about its argument; principle 2 asks what it is allowed to decide about it. Both answer
by moving the knowledge onto the type.

## How each one fails when taken absolutely

- Principle 1 produces a `Protocol` for every parameter, including the ones with exactly one implementation
  forever — indirection with no substitution benefit.
- Principle 2 produces *"few `if` statements = good"*, which is wrong. Guard clauses, validation and
  boundary checks are correct Python and must survive. A review that flags them is worse than no review,
  because it teaches the reader to distrust the whole report.

---

## Principle 1 — parameters name capabilities, not implementations

### Statement

A parameter's type should name the **smallest capability the function actually exercises**, not the concrete
class the caller happens to be holding.

The type should describe *what the function needs*, not *which implementation provides it today*.

### Violation shapes

1. The signature names a concrete class, but the body calls only one or two of its methods.
2. The signature names a container or facade, and the body reaches into two or three attributes of it.
3. The type is `list[T]` but the body only iterates it once.
4. The function takes a `Path` when it only ever consumes the text inside.
5. A parameter exists only to be passed through to another call, untouched by this function.

### Where it stops

- **One implementation, and no second one you can name.** The test is concrete: *can you name a second
  implementation that exists or is actually coming?* If not, keep the concrete type. A `Protocol` with a
  single implementer is indirection with no substitution benefit.
- **Accept abstractions, return concretions.** The caller of a result usually should know exactly what it
  received. Widening applies to inputs, not outputs.
- **Do not widen past the truth.** `Iterable[T]` beats `list[T]` only if the body genuinely iterates once.
  If it indexes or takes `len()`, `Sequence[T]` is the honest type; if it iterates twice, `Iterable[T]` is a
  latent bug, not a better signature.

---

## Principle 2 — branching that selects behaviour is a missing polymorphism

### Statement

Branching on **what something is** — its type, vendor, format, mode, or a string naming an algorithm — in
order to decide **what to do**, is a **missing polymorphism**. The behaviour belongs on the type; the caller
should not have to discriminate.

**On *which* type, though.** If the branched-on type is a storage schema — a pydantic document, a TOML/JSON
shape, a table row — the behaviour does not go on it, because that fuses the file format with the
computation and points a dependency the wrong way. The remedy is then a runtime type plus a factory, and
the schema's validators are correct and stay.

Branching on **what happened** — empty, absent, invalid, out of range — is ordinary control flow and correct.

**The bound is half the principle.** This is *not* "few `if` statements are good".
`if not values: return None` is correct Python and must not trigger an abstraction reflex.

### Violation shapes

1. `isinstance(x, A) / elif isinstance(x, B)` chains where each arm does the analogous thing differently.
2. `if fmt == "csv" … elif fmt == "parquet"` — dispatch on a string that names an implementation.
3. **The same branch set appearing in more than one function.** The strongest signal: that set has become a
   de-facto type with no name.
4. Adding one new vendor, format, or mode requires editing N existing functions.
5. **`if record.field is None` / `is not None` on a type you own, where the arms do different things.**
   `A | None` is a sum type — a two-member union, the same shape as a four-member one, just spelled
   differently. A record with N optional fields is 2^N types, and each consumer re-derives which it got.
6. **A validator that rejects combinations of fields, one of which is a kind.** If the type needs a runtime
   check saying "field X is only valid when field Y is Z", the code already knows there are several types
   and is policing at runtime what a split type would make unrepresentable. The qualifier is not optional —
   see the first bound below.
7. **A `bool` field or flag selecting behaviour.** `if params.uses_diann:` is the same defect as
   `if fmt == "diann":` with the discriminator narrowed to two cases and its name hidden in the field name.
   Worth stating separately because it is invisible to every grep aimed at `isinstance` or `== "literal"` —
   on the package this was tested against, the only real instance in one whole subpackage was a `bool`, and
   the tool-assisted pass missed it while an unassisted read found it.

### Where it stops

Ordered cheapest-first: the first two disqualify most candidates and neither requires reading the bodies.

- **Can you name the question every arm answers?** *"Which token index is this?"*, *"how do several values
  in one cell become one?"* That name would be the method name. **If you cannot name it, stop** — the type
  is a data-transfer object and its validator is doing its job. This is the single highest-yield question
  here and it costs one sentence; skipping it is how a full remedy gets written for a finding that was
  never there.
- **Does the case set have two or more consumer sites?** One site is a local branch, not a missing type.
  Two in one module is weak; **two modules is the threshold worth reporting.** Skipping this over-reports
  every small result type.
- **Validators that police *values*, not kinds.** *Ordering* (`min > max`), *uniqueness*, *set equality*,
  *non-emptiness* all reject combinations of fields and are all correct code. Shape 6 counts only when one
  field is a mode, kind or strategy **and the others are that mode's payload**. Quick proxy: the condition
  compares a field to a **literal** (`self.mode == "absolute"`) → candidate; a field to another **field**
  (`self.min > self.max`) → validation, leave it.
- **Guard clauses, empty/`None` checks, boundary conditions.** `if not values: return None` is correct and
  must not trigger an abstraction reflex.
- **A mode string nothing branches on at the far end.** If the value is only recorded, logged or written
  out, it is a **label**, not a discriminator — duplication at worst. Grep the literal before reporting.
- **A single dispatch point at a factory or composition root is right, not wrong.** The registry `dict` is
  the cure, not the disease. The smell is the same case set appearing *again past* that lookup.
- **Two arms that will demonstrably never grow.** Say so and move on.

---

## Using this as a detector

Ranked by how mechanically checkable each shape is — findings from the top of this list are evidence,
findings from the bottom are opinion, and a review should say which it is reporting.

| Rank | Shape | Why |
| --- | --- | --- |
| 1 | P2.3 — same branch set in >1 function | Countable. Set membership is objective, and the second site is what proves the set has become a de-facto unnamed type. |
| 2 | P2.6 — validator whose message names a *mode* and a *payload* | The check is a written admission that the type is several types — **but only with that qualifier.** Bare "rejects a field combination" also describes `min > max`, which is correct code; apply the literal-vs-field proxy before reporting. |
| 3 | P2.5 / P2.7 — `is None` on an owned optional field, or a `bool` selecting behaviour | Greppable once you know to look. Needs the arms compared: different *behaviour* vs. a different *value*. |
| 4 | P2.4 — new case requires editing N functions | Countable, once the branch sets are known. The most persuasive form to report, because the cost is concrete. |
| 5 | P2.1 / P2.2 — `isinstance` / string dispatch chains | Greppable, but noisy: each needs "what happened vs what it is" applied by hand, and the majority reject. |
| 6 | P1.1 / P1.2 — concrete type, few members used | Requires reading each body. Judgement. Produced no findings on the package this was tested against. |
| 7 | P1.3 / P1.4 — over-narrow collection and `Path` types | Easy to spot, low value individually. |

**Do not grep only for `isinstance`.** That single omission is what made the first pass over the test
package miss its worst module outright — the discrimination there is spelled `is not None`, so it never
entered the candidate set at all. P2.5 (`is None`), P2.6 (a validator) and P2.7 (a `bool`) are each
invisible to a *different* query, which is why this table ranks by **checkability**, not by where a grep
happens to point — and why a tool that enumerates candidates must be treated as a floor rather than as the
worklist.

**Reporting rule.** Every finding must state which shape it matches *and* which bound it clears. A finding
that cannot name the bound it clears is not a finding — for principle 1 that means naming the plausible
second implementation; for principle 2 it means showing the branch is on *what something is*, not on *what
happened*.
