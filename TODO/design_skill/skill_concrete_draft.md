---
name: polymorphism-over-discrimination
description: >-
  Use when writing or editing code that decides what to do by asking what something is — an isinstance
  chain, an `if mode == "x" / elif` chain, `if record.field is None` where the arms do different work, a
  validator that rejects field combinations ("X is only valid when Y is Z"), a function that returns a
  string naming an operation, or a record carrying a kind flag plus fields belonging to one kind. Also fires
  when adding an arm to any existing chain of those, when adding an optional field to a type you own, and
  when naming something Builder, Factory, Strategy, or Visitor. Python only.
---

# Polymorphism over discrimination

> **Draft — step 3 of 3.** Derived from [skill_principle.md](skill_principle.md) (the principles) and
> [review_principle_apb.md](review_principle_apb.md) (running them over ~10k lines of Python). Every
> anti-pattern in §5 is a mistake made *while producing that review*, not a hypothetical.
> Not installed. See *Open items* at the end.

**Branching on what something *is*, in order to decide what to *do*, is a missing polymorphism. Put the
behaviour on the type.**

The bound is half the rule. This is **not** "few `if` statements are good". Branching on what *happened* —
empty, absent, invalid, out of range — is ordinary control flow. `if not values: return None` is correct
Python and must not trigger an abstraction reflex.

---

## 1. The one question

> Does this branch ask **what something is** (type, vendor, format, mode, strategy, which-variant), or
> **what happened** (missing, empty, out of range, this file lacks that column)?

*What it is* → read on. *What happened* → you are done, the `if` is correct.

---

## 2. Bounds — cheapest disqualifier first

Most candidates are not defects. Run these in order; **the first three need no reading at all**, and on a
real codebase they remove most of the list before judgement starts.

### Mechanical rejects — no reading

**M1. Is the `isinstance` target a type you define?** If the class named in `isinstance(x, C)` is not
declared in your package, you cannot put a method on it. Reject.

```bash
# classify every isinstance site; anything not naming a local class is out
python - <<'EOF'
import ast, pathlib
owned = {n.name for f in pathlib.Path(".").rglob("*.py")
         for n in ast.walk(ast.parse(f.read_text())) if isinstance(n, ast.ClassDef)}
for f in sorted(pathlib.Path(".").rglob("*.py")):
    for n in ast.walk(ast.parse(f.read_text())):
        if (isinstance(n, ast.Call) and getattr(n.func, "id", "") == "isinstance"
                and len(n.args) == 2):
            names = [x.id for x in ast.walk(n.args[1]) if isinstance(x, ast.Name)]
            if names and any(x in owned for x in names):
                print(f"{f}:{n.lineno}  CANDIDATE  {names}")
EOF
EOF
```

Measured on one 97-module package: **231 sites → 98 candidates, 57 % rejected with no judgement.** The
rejects are `str`, `dict`, `list`, `int`, `float`, `bool`, `h5py.Group`, `np.ndarray`, `AnnData` — narrowing
at a parse boundary, which is correct code.

Note carefully: **this is about where the foreign value is, not which package handles foreign data.**
`Tolerance.parse(value: object)` is the boundary; everything past it is yours and gets no protection.

**M2. Does the union have two or more consumer sites?** A union discriminated in exactly one place is bound
M5 territory, not a finding. Two sites in one module is weak; **two modules is the threshold worth
reporting.** Skipping this over-reports every small result type (`ParsedMass | NonNumericToken`, discriminated
once, is fine).

**M3. For a shape-5 candidate, does anything at the far end branch on the string?** grep the returned
literal. If nothing compares against it, the string is a **label**, not a discriminator — that is duplication
at worst, not a missing polymorphism.

### Judgement rejects — require reading

**M4. Guard clauses, validation, emptiness, boundary checks.** `if not values: return None`.
Also: *ordering* (`min > max`), *uniqueness*, *set equality*, *non-emptiness* validators police **values**,
not kinds. The validator shape only counts when **one field is a mode, kind, or strategy and the others are
that mode's payload.** Cheap AST proxy: the condition compares a field to a **literal** (`self.mode ==
"absolute"`) → candidate; a field to another **field** (`self.min > self.max`) → validation.

**M5. Two arms that will demonstrably never grow.** Say so and move on.

### Split compound conditions before judging

One `if` can contain a finding and a non-finding joined by `and`. Evaluate **each conjunct separately**:

```python
if (isinstance(params, StoredSearchParameters)          # ← which variant is this: FINDING
        and params.parameters.min_length is not None):  # ← did the vendor state one: M4, correct
```

Judging the `if` as a unit gives the wrong answer whichever way you round.

### And one destination that is not a defect

**A single dispatch point at a factory or composition root is right.** A `dict[str, Handler]` with one
lookup is the cure. The smell is the same case set appearing *again* past that lookup.

---

## 3. The shapes, most mechanically checkable first

| # | Shape | How to find it |
| --- | --- | --- |
| 1 | **A validator rejecting field combinations** where one field is a kind | grep validators; read the message. ***"X is only valid when Y is Z"* → Y is a type discriminator.** *"X must not exceed Y"* → validation. |
| 2 | **The same case set branched on in more than one function** | grep the discriminator name across the package. Countable, objective, and the strongest evidence available. |
| 3 | **`if x.field is None` / `is not None` on a type you own**, arms doing different work | grep `\.<field> is (not )?None`. `A \| None` is a two-member union spelled sideways; a record with N optional fields is 2^N types. |
| 4 | **A discriminated union you already split, whose consumers still discriminate** | **The highest-yield check there is.** Find the identity types by name, then their discriminators — see the two greps below. Apply M2: ≥ 2 consumer sites, ideally in ≥ 2 modules. |
| 5 | **A function that turns a mode into a string another function branches on** | grep for `-> str` returning literals like `"sum"`, `"first"`, `"csv"`. Then **apply M3** — if nothing branches on the string it is a label, not a discriminator. |
| 6 | **`isinstance` / `== "literal"` chains** | grep, apply **M1** (57 % reject with no reading), then §1 by hand on what survives. |
| 7 | **A record passed whole where the body reads one field** | AST scan. **Reports nothing on its own** — it is a queue: for each hit, re-run shapes 1–6 on the field being reached for. See §5.8. |

Four greps that pay for themselves:

```bash
# shape 1 — the tell is in the message text, not the code
rg -n 'is only valid (for|when)|only valid if|cannot define|requires .* when' --type py

# shape 3 — do not grep only for isinstance; most discrimination is spelled `is not None`
rg -n '\.\w+ is (not )?None' --type py

# shape 4, part 1 — the identity types. Run this FIRST on any codebase that avoids `| None`.
rg -n '^class (Missing|No|Non|Empty|Absent|Null|Unset)[A-Z]' --type py

# shape 4, part 2 — their discriminators
rg -n 'isinstance\([^,]+, (Missing|No|Non)[A-Z]\w*\)' --type py
```

**Run the shape-4 pair before anything else.** A codebase that has adopted "replace `| None` with a named
absent case" has this shape *by construction* — the discipline creates the types, and nothing makes anyone
add the method. Measured on one 97-module package: **18 identity types, 0 with a method, 18 discrimination
sites in 8 modules.**

**The docstring tell, free recall:** an empty class whose docstring *describes behaviour* is a missing
method. `"""Use the stored enzyme when present, otherwise Trypsin."""` on a class with no fields and no
methods is the defect announcing itself in prose.

---

## 4. The remedy, in order

**The first two steps are gates.** Both can disqualify the whole finding, and both are cheaper than any
edit — an earlier draft of this skill asked them fifth and sixth, which meant writing a full remedy before
discovering it was not needed.

1. **Gate — name the question every arm answers.** *"Which token index is this?"*, *"How do several values
   in one cell become one?"*, *"How do I coerce this column to numbers?"* That name is the method name.
   **If you cannot name it, stop: it is a DTO and the validator is doing its job (§5.4).** This is the
   single highest-value question in the skill and it costs one sentence.
2. **Gate — is the type a storage schema?** A pydantic model, a TOML/JSON shape, a table row? Then the
   behaviour does *not* go on it (§5.3): the remedy is a runtime type plus a factory, and the schema's
   validators are **correct and stay**. Getting this wrong turns a clean finding into a layering violation.
3. **Split the type**, or give the absent case an identity member (§5.1). One class per case, each declaring
   only its own fields. Constraints the validator policed from outside become field declarations:
   `Field(min_length=1)`, a required `str` instead of `str | None`, a `Literal` for a forced name.
4. **Put the method on each class, and return the result — not a token naming it** (§5.2).
5. **Write the factory.** A union with nothing to construct it is not finished (§5.7).
6. **Delete the branches.** If any survive, the polymorphism moved rather than happened.

**Do not stop at step 3.** Splitting a type without moving behaviour onto it produces shape 4 — which is,
measurably, the most common defect this skill finds.

---

## 5. Eight ways to do this wrong

Every one of these was produced while deriving this skill, and corrected only when challenged. They are the
failure modes to expect, in the order they tend to appear.

### 5.1 Replacing `| None` with `| NoThing`

```python
fragments: Fragments | NoFragments = NO_FRAGMENTS       # ✗ Fragments is already a 2-member union
```

Three members spelled as two, and every consumer is back to asking *"is it the `NoFragments` one?"* — `is
None` under a new name. **The absent case is a member of the union, with a discriminator value and the
identity behaviour:**

```python
class NoFragments(RuleModel):
    label_strategy: Literal["none"] = "none"
    def explode(self, df: pd.DataFrame) -> pd.DataFrame:
        return df                                        # ✓ identity arm carries behaviour

type Fragments = Annotated[
    NoFragments | PositionalFragments | ColumnLabeledFragments, Field(discriminator="label_strategy")
]
```

A type split whose empty member has no method leaves the caller discriminating — that is shape 4.

### 5.2 Returning a token instead of the result

```python
class SumDuplicates:
    def aggfunc(self) -> str: return "sum"              # ✗ caller must dispatch on the string
```

The caller then writes `if aggfunc == "sum": ...`, and you have moved the branch one call deeper while
adding a stringly-typed hop. **Return the result, not the name of the operation:**

```python
class SumDuplicates:
    def combine(self, cells: CellContributions) -> Matrix: ...   # ✓ does the thing
```

### 5.3 Putting the behaviour on the persistence schema

A pydantic model describes **what may appear in a file**. It is not the computational model. Hanging
conversion logic on it fuses the file format with the computation — and it is why an agent that splits a
pydantic union finds nowhere legitimate to put the method and **stops at the split**.

```
Document (pydantic, knows the format)  →  factory (the one place a tag is read)  →  Runtime (behaviour)
```

The runtime type carries **no discriminator field** — it *is* the type. The document keeps its tag, because
a decoder needs it. Corollary, and it changes verdicts: **a combination-rejecting validator on a document
schema is correct and stays.** Someone can write that combination in the file and must be told. It is a
missing polymorphism only when the validated type is *also* what computes.

### 5.4 Inventing a method to justify a split

If, after splitting, you find yourself writing a method no caller wants, undo it.

> **If you cannot name the method that would go on the split types, it is a DTO and the validator is doing
> its job.** A missing polymorphism is missing *behaviour*. Two record shapes with no behaviour between them
> are a schema; splitting buys a second name and nothing else.

Cheapest test available — try to finish the sentence *"and then each type would implement …"*.

### 5.5 Treating the current module layout as a constraint

"A method here would import-cycle, so I will use `singledispatch` instead" — no. **A cycle means the code is
in the wrong file.** If an operation is a type's behaviour, the type and the operation belong in one module,
and moving them there is part of the remedy. Relatedly: **do not invent a layering rule to justify the
detour.** Check what the project's rules actually forbid before reasoning from an observed import habit.

`functools.singledispatch` is a legitimate encoding of the same polymorphism — reach for it when the
operation genuinely is not the type's behaviour (a second backend wanting a different conversion of the same
data), not to route around a file boundary.

### 5.6 Calling it a Builder

Pattern names are claims about structure. A function that takes a tag and returns one of N types is a
**factory function**; a `dict` lookup returning stateless singletons is not even that, it *selects*. GoF
Builder means incremental construction through a stepwise interface driven by a director. Naming:

- `make_<thing>(...)` — constructs a new object of one of N types
- `<thing>_for(...)` — selects among existing instances
- named constructor (`Format.build`) only when the return type **is** the class; a union has no class to
  hang it on

And do not reach for a Builder to tidy a factory: a builder's internal state is a record whose fields may or
may not be set yet — 2^N shapes validated at `build()`, which is the defect this skill exists to remove,
reintroduced with a respectable name. Builder earns its place when construction is caller-configurable
across many combinations, never for one fixed sequence.

### 5.7 Showing the union and stopping

A union with no factory is unfinished — nothing yet turns the document's tag into the type. **The factory is
also where an unimplemented variant fails**: a mode declared in the schema with no runtime class is a
missing registry entry, which raises once at construction time instead of partway through the work.

```python
_BY_MODE: dict[Mode, Policy] = {"error": ErrorOnDuplicates(), "aggregate": SumDuplicates()}
                                                     # "keep_all_as_raw_table": absent on purpose
```

Hazard: shared singletons are safe only while the types are frozen and stateless. If one gains state, the
dict must hold classes, not instances, or two runs share an accumulator.

### 5.8 Narrowing a signature instead of giving the thing a type

Shape 7 (`f(rule: ParseRule)` reading only `rule.axis.duplicates.mode`) tempts a cosmetic fix — narrow the
parameter. **A function reaches for the whole record because the thing it actually wants has no type yet.**
Give that thing a type and the parameter narrows for free; narrow the parameter and every branch survives.
Treat shape-7 hits as a queue of shape 1–6 candidates.

---

## 6. Worked example — smallest complete case

Four functions in one module each ask *where does this modification sit?* and answer it per type:

```python
type ModificationLocation = ResidueLocation | TerminalLocation | TerminalOnlyLocation | UnlocalizedLocation

def _record_unknown_token(location: ModificationLocation, sequence_length: int, ...) -> None:
    if isinstance(location, ResidueLocation):
        unknown_tokens[location.sequence_index] = raw_token
    elif isinstance(location, TerminalLocation | TerminalOnlyLocation):
        index = -1 if location.position == "N-term" else sequence_length
        unknown_tokens[index] = raw_token
```

Shape 2 (four functions, one case set) and shape 6. Bounds: own types, same file, `if` asks *what it is*. No
factory needed — these are already plain runtime dataclasses, not documents, so §5.3 does not apply.

```python
@dataclass(frozen=True, slots=True)
class ResidueLocation:
    residue: str
    sequence_index: int
    def token_index(self, sequence_length: int) -> int:
        return self.sequence_index

@dataclass(frozen=True, slots=True)
class TerminalLocation:
    position: Literal["N-term", "C-term"]
    def token_index(self, sequence_length: int) -> int:
        return -1 if self.position == "N-term" else sequence_length

# every call site, no branch
unknown_tokens[location.token_index(sequence_length)] = raw_token
```

Adding a fifth location kind becomes one class the type checker forces you to complete, instead of four
functions nothing forces you to find.

---

## Open items before this is installable

- [ ] **Untested trigger.** The `description` above is the whole mechanism and has never fired in a real
      session. It is long; a shorter one may fire more reliably. Measure before trusting it.
- [ ] **Split into tiers.** §1–§4 are the navigation tier (~90 lines) and belong in `SKILL.md`; §5 and §6
      belong in `references/anti-patterns.md` and `references/worked-example.md`. Kept in one file here
      because this is a draft for review, not an install.
- [ ] **§5.3 is the largest claim and the least portable.** The document/factory/runtime separation is right
      for a codebase whose types come from files. In a project whose pydantic models genuinely are the
      domain, it will mislead. Consider gating it on "is this type loaded from a file?".
- [ ] **Examples are all from one codebase.** Good for recognition there, unproven elsewhere. Decide whether
      this ships workspace-local or general before generalising them away.
- [ ] **Shape 7 may be net-negative.** It is judgement-heavy and an agent applying it mechanically produces
      `Protocol` noise. §5.8 is the mitigation; verify it is enough, or drop shape 7.
