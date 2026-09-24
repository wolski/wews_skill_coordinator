---
name: polymorphism-over-discrimination
description: >-
  Find and fix code that decides what to do by asking what something is. Use this skill whenever
  reviewing or writing Python that contains an isinstance chain, an `if mode == "x" / elif` chain,
  `if record.field is None` where the arms do different work, a validator that rejects field
  combinations ("X is only valid when Y is Z"), a function returning a string that names an
  operation, or a record carrying a kind flag plus fields belonging to only one kind. Use it when
  adding an arm to any existing chain of those, when adding an optional field to a type you own,
  when introducing a `Missing`/`No`-prefixed class, and when naming something Builder, Factory,
  Strategy, or Visitor. Also use it for any request to review Python design, reduce branching,
  clean up conditionals, or audit a package for structural problems — even when the user does not
  say "polymorphism". Python only.
---

# Polymorphism over discrimination

**Branching on what something *is*, in order to decide what to *do*, is a missing polymorphism.
Put the behaviour on the type.**

The bound is half the rule. This is **not** "few `if` statements are good". Branching on what
*happened* — empty, absent, invalid, out of range — is ordinary control flow. `if not values:
return None` is correct Python and must not trigger an abstraction reflex. A review that flags
guard clauses is worse than no review, because it teaches the reader to distrust the whole report.

## Start here: get the worklist mechanically

Do not start by grepping for `isinstance`. Most of what that finds is correct code, and reading it
burns the review's attention before it reaches anything real.

```bash
python scripts/find_candidates.py <package-dir>          # human-readable worklist
python scripts/find_candidates.py <package-dir> --json    # same data, machine-readable
```

One pass produces every candidate list below, already sorted, with the rejections that need no
judgement applied. On a 97-module package it rejected 57 % of `isinstance` sites outright and
ranked the remaining work in about two seconds.

**Read its `IDENTITY TYPES WITHOUT METHODS` section first.** That is consistently the highest-yield
output, for a reason worth understanding: a codebase that has adopted "replace `| None` with a named
absent case" grows those types by the dozen, and **nothing in that discipline makes anyone add the
method.** The modelling lands; the branch survives. On the package above: 18 such types, **0 with a
method**, discriminated in 8 modules.

## The one question

> Does this branch ask **what something is** (type, vendor, format, mode, strategy,
> which-variant), or **what happened** (missing, empty, out of range, this file lacks that column)?

*What it is* → continue. *What happened* → done, the `if` is correct.

**Ask it per condition, not per branch.** One `if` can join a finding and a non-finding with `and`:

```python
if (isinstance(params, StoredSearchParameters)          # which variant is this → FINDING
        and params.parameters.min_length is not None):  # did the vendor state one → correct
```

Judging that `if` as a unit gives the wrong answer whichever way you round.

## Bounds — cheapest disqualifier first

The first three need no reading. Most candidates die here, and that is the point: a shortlist you
can defend beats a long list you cannot.

**B1 — Is the `isinstance` target a class this package defines?** If not, you cannot give it a
method, so narrowing it is correct code at a parse boundary. `find_candidates.py` applies this for
you. The rejects are `str`, `dict`, `list`, `int`, `bool`, `h5py.Group`, `np.ndarray`, DataFrames.

Note carefully: **this is about where the foreign value is, not which package handles foreign
data.** `Tolerance.parse(value: object)` is the boundary; everything past it is yours and gets no
protection from this bound.

**B2 — Does the union have ≥ 2 consumer sites?** One site is B5 territory. Two in one module is
weak; **two modules is the threshold worth reporting.** Skipping this over-reports every small
result type. The script prints site and module counts per union.

**B3 — For a mode-string candidate, does anything at the far end branch on the value?** grep the
literal. If nothing compares against it, the string is a **label**, not a discriminator — that is
duplication at worst.

**B4 — Guard clauses, validation, emptiness, boundary checks.** Also: *ordering* (`min > max`),
*uniqueness*, *set equality*, *non-emptiness* validators police **values**, not kinds. The validator
shape only counts when **one field is a mode, kind or strategy and the others are that mode's
payload**. Quick proxy: the condition compares a field to a **literal** (`self.mode == "absolute"`)
→ candidate; a field to another **field** (`self.min > self.max`) → validation.

**B5 — Two arms that will demonstrably never grow.** Say so and move on.

**And one destination that is not a defect:** a single dispatch point at a factory or composition
root is right. A `dict[str, Handler]` with one lookup is the cure. The smell is the same case set
appearing *again* past that lookup.

## The shapes

Ordered by how mechanically checkable they are. Findings from the top are evidence; from the bottom,
opinion. **Say which you are reporting** — a review that mixes them loses the reader's trust in both.

| # | Shape | Where the script reports it |
| --- | --- | --- |
| 1 | **A validator rejecting field combinations**, one field being a kind | `VALIDATOR MESSAGES` — then apply B4 |
| 2 | **The same case set branched on in more than one function** | derive from the `union:` line + site counts |
| 3 | **`if x.field is None` on a type you own**, arms doing different work | `OPTIONAL-FIELD DISCRIMINATION` (bare guards pre-removed) |
| 4 | **A union you already split, whose consumers still discriminate** | `IDENTITY TYPES WITHOUT METHODS` — **read this first** |
| 5 | **A function turning a mode into a string another function branches on** | `MODE-STRING RETURNS` — then apply B3 |
| 6 | **`isinstance` / `== "literal"` chains** | `OWNED-TARGET ISINSTANCE` — foreign already rejected |
| 7 | **A record passed whole where the body reads one field** | `WIDE-PARAMETER READS` — **reports nothing on its own** |

Two tells the script surfaces but cannot judge:

- **The message text, for shape 1.** *"X is only valid when Y is Z"* → Y is a type discriminator.
  *"X must not exceed Y"* → validation. This fires while the validator is being written, which is
  before the case set has spread to three modules.
- **The docstring, for shape 4.** An empty class whose docstring *describes behaviour* is a missing
  method. `"""Use the stored enzyme when present, otherwise Trypsin."""` on a class with no fields
  and no methods is the defect announcing itself in prose.

## The remedy, in order

**The first two steps are gates.** Both can disqualify the whole finding, and both are cheaper than
any edit. Asking them late means writing a full remedy before discovering it was not needed.

1. **Gate — name the question every arm answers.** *"Which token index is this?"*, *"How do several
   values in one cell become one?"* That name is the method name. **If you cannot name it, stop: it
   is a DTO and the validator is doing its job.** Highest-value question in the skill; costs one
   sentence. See `references/anti-patterns.md` §4.
2. **Gate — is the type a storage schema?** A pydantic model, a TOML/JSON shape, a table row? Then
   the behaviour does *not* go on it: the remedy is a runtime type plus a factory, and the schema's
   validators are **correct and stay**. Getting this wrong converts a clean finding into a layering
   violation. See `references/anti-patterns.md` §3.
3. **Split the type**, or give the absent case an identity member. One class per case, each
   declaring only its own fields. Constraints the validator policed from outside become field
   declarations: `Field(min_length=1)`, a required `str` instead of `str | None`, a `Literal` for a
   forced name.
4. **Put the method on each class, and return the result — not a token naming it.**
5. **Write the factory.** A union with nothing to construct it is not finished. It is also where an
   unimplemented variant fails: a mode declared in the schema with no runtime class is a missing
   registry entry, raising once at construction time instead of partway through the work.
6. **Delete the branches.** If any survive, the polymorphism moved rather than happened.

**Do not stop at step 3.** Splitting a type without moving behaviour onto it produces shape 4 —
measurably the most common defect this skill finds.

## Naming

Pattern names are claims about structure, and a wrong one sends every future reader hunting for
machinery that is not there.

- `make_<thing>(...)` — constructs a new object of one of N types. A factory function.
- `<thing>_for(...)` — selects among existing instances. A lookup; constructs nothing.
- a named constructor (`Format.build`) only when the return type **is** the class. A union has no
  class to hang it on.
- **Not `Builder`** unless construction is incremental, stepwise and director-driven. And do not
  reach for a Builder to tidy a factory: a builder's internal state is a record whose fields may or
  may not be set yet — 2^N shapes validated at `build()`, which is this skill's own target defect
  wearing a respectable name.

## Reporting

State for each finding: the **shape**, the **bound it clears**, whether it is **evidence or
judgement**, and the **remedy as code**. A finding with no polymorphic remedy is a complaint. A
finding that cannot name the bound it clears is not a finding.

Report what the bounds rejected too, with counts. It is the only way a reader can tell a
discriminating instrument from one that flags everything.

## References

- **`references/anti-patterns.md`** — eight ways to do this wrong, each observed in practice.
  **Read before writing any remedy**; §3 and §4 are the two gates above and they are where remedies
  go wrong most often.
- **`references/worked-examples.md`** — three complete before/after remedies at increasing
  difficulty: a plain runtime union, a document/runtime split with a factory, and a policy object
  replacing a laundered mode string.
