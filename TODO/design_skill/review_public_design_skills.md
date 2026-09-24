# APB reviewed with the two public design skills

> **What this is.** `apb/src/anndata_proteomics` reviewed through the two skills assessed in
> a 2026-08-12 assessment of two public design skills —
> `wshobson/agents@python-design-patterns` and `pproenca/dot-skills@clean-architecture`.
> **APB only.** Third of three reviews; the others used
> [skill_principle.md](skill_principle.md) and [skill_concrete_draft.md](skill_concrete_draft.md).
>
> **Neither skill was installed.** Both are read locally from
> [python-design-patterns.md](python-design-patterns.md) and [clean-architecture.md](clean-architecture.md);
> the `clean-architecture` rules missing from that partial copy (`entity-rich-not-anemic`,
> `entity-value-objects`) were fetched read-only from GitHub. Installing would symlink into
> `~/.claude/skills/`, where `wews_skill_coordinator` already manages symlinks — the unresolved question in
> §8 of the assessment. Nothing on disk was changed by this review.
>
> **No code was changed.**

---

## Why this review is worth having

The first two reviews used one instrument, so they could only find what that instrument looks for. These two
skills carry **different priors**, and the interesting output is not their findings — it is the three places
where they **contradict each other, or contradict our own skill**. A contradiction between two standing
instructions is a live hazard: whichever fires first wins, silently.

Result up front:

| | Findings | Confirms our review | Contradicts it |
| --- | --- | --- | --- |
| `python-design-patterns` | 3 | 2 | **1** (Rule of Three) |
| `clean-architecture` | 4 | 2 | **1** (`entity-rich-not-anemic`) |
| Both | — | — | **1** shared blind spot |

And one strong positive neither of our reviews could have produced: **APB passes `dep-inward-only` cleanly**,
which is the rule its own `AGENTS.md` was written to enforce.

---

## Part 1 — `python-design-patterns`

Lenses: KISS · SRP ("one reason to change") · composition over inheritance · Rule of Three · functions
20–50 lines · constructor injection · "7+ parameters means too many responsibilities".

### P-1 — 21 functions exceed the skill's length guidance, and they cluster in one place

**Rule:** *"Keep functions small — 20–50 lines (varies by complexity), one purpose."*

21 functions in APB are over 50 lines. The distribution is the finding, not the count:

| Lines | Function | Location |
| --- | --- | --- |
| 132 | `fasta` | `scripts/cli.py:592` |
| 93 | `compute_intermediate` | `proteobench/intermediate.py:178` |
| 90 | `extract_params` | `params/parsers/maxquant.py:194` |
| 77 | `extract_params` | `params/parsers/alphadia.py:108` |
| 76 | `extract_params` | `params/parsers/fragpipe.py:520` |
| 75 | `convert_wide` | `converters/wide.py:133` |
| 69 / 67 / 62 | `extract_params` | `peaks.py:79`, `diann.py:538`, `spectronaut.py:134` |

**Six of the twelve longest are `extract_params`, one per vendor.** The skill's own troubleshooting section
covers this: *"apply the 'reason to change' test"*. Each `extract_params` changes for exactly one reason —
that vendor changed its export format. By the skill's own test they are **appropriately sized**, and the
length is inherent: they map ~30 vendor keys onto `Parameters`. Verdict: **not a defect**; the metric flags
them and the skill's own adjudication clears them, which is precisely the "a metric never adjudicates"
discipline in `AGENTS.md`.

`scripts/cli.py:592` at 132 lines is a different case — a CLI entry point mixing argument handling,
orchestration and output. That one is worth splitting, and it is the only clear P-1 finding.

### P-2 — three functions hit the skill's own "7+ parameters" trigger, and it diagnoses them correctly

**Rule, verbatim:** *"Injecting all dependencies through the constructor is producing constructors with 7+
parameters. This is a sign of too many responsibilities in one class, not a problem with dependency
injection."*

Exactly three callables in APB take ≥ 7 parameters:

```python
def _build_matrix(obs_codes, var_codes, values, key_ok, n_obs, n_var, aggfunc) -> DenseLayerMatrix:  # long.py:63
def _gather_layer_matrix(df, layer, headers, sample_order, var_index, var_keys, duplicate_mode)      # wide.py:45
def _assemble_feature_statistics(...)                                          # proteobench/intermediate.py:443
```

**Two of the three are findings our own review already reached by a different route.** `_build_matrix`'s
seventh parameter is `aggfunc: str` — the laundered discriminator from
[review_principle_apb.md](review_principle_apb.md) F7. `_gather_layer_matrix`'s seventh is
`duplicate_mode` — the same discriminator, in the wide converter. **Two instruments, independently, land on
the same parameter.** That is the strongest corroboration available in this exercise, and it arrives from a
skill that never mentions polymorphism.

The skill's remedy ("split the class first, then constructors shrink") and ours (`CellContributions` record +
a policy object) agree on the direction and differ only in vocabulary.

### P-3 — the six delimiter wrappers are a Rule-of-Three violation *by the skill's own arithmetic*

`readers/tabular.py` has two real implementations and **six** wrappers whose whole body binds a delimiter
(`read_csv`, `read_tsv`, `read_detected_text` and their `_preserving_strings` twins). The skill says *"Delete
before abstracting"* and *"Simple beats clever"*; six pre-composed wrappers over a 2-parameter function are
neither. Same finding as F6, reached via KISS instead of via polymorphism.

### ✗ Contradiction 1 — Rule of Three vs. "the same case set in two functions is already evidence"

| | Says |
| --- | --- |
| `python-design-patterns` | *"Wait until you have three instances before abstracting. Duplication is often better than premature abstraction."* |
| [skill_concrete_draft.md](skill_concrete_draft.md) shape 2 | The same case set in **more than one** function is the strongest evidence available. |

This is a real conflict, not a wording difference. Under Rule of Three, `_resolve_minimum_length` and
`_resolve_maximum_length` (two copies) are *fine* and you wait for a third. Under our shape 2 they are
already a finding.

**Resolution, and it is the skill's own escape hatch:**

> *"The rule of three says not to abstract yet, but the duplication is causing bugs when one copy is updated
> but not the other."* → *"Duplication that diverges in dangerous ways should be abstracted sooner. The rule
> of three is a heuristic, not a law."*

And APB has the divergence receipt: `readers/dispatch.py:read_table_columns` reports
`sorted(EXTENSION_TO_READER)` in its error message — **a set it does not itself use**. The copies drifted.
So the two rules reconcile, but only if the agent reads the troubleshooting section, which is in the *detail*
tier. **An agent that loads only `SKILL.md` gets "wait for three" with no caveat.** That is the hazard:
installed alongside our skill, `python-design-patterns` supplies a defensible-sounding reason to decline
every two-copy finding in both reviews.

---

## Part 2 — `clean-architecture`

Lenses used: the six `dep-` rules (the category the assessment judged this skill worth installing for) plus
`entity-rich-not-anemic`, `entity-value-objects`, `entity-no-persistence-awareness`.

### C-1 — `dep-inward-only` holds. Cleanly.

**Rule:** *source dependencies point inward only.* Unpacking the jargon, because the rule name says almost
nothing on its own:

Clean Architecture pictures a system as concentric rings. The **inside** is what the software is *about* —
domain rules that would still be true if you changed database, file format and UI. The **outside** is
mechanism — storage, frameworks, file parsers, CLIs. *Inward* means toward the middle. The rule is a
constraint on `import` statements only: **an outer ring may import an inner one; an inner ring may never
import an outer one.** Not "calls" — *imports*, because an import is what welds two modules together at
build time.

In APB's terms:

| Ring | Packages | May import |
| --- | --- | --- |
| outer (mechanism) | `adapters/anndata/`, `scripts/`, `readers/` | anything inside |
| middle (orchestration) | `workflows/` | `converters/`, `rules/`, … |
| inner (computation) | `converters/`, `rules/`, `modifications/`, `params/`, `fasta/` | each other only — **never** `adapters/`, `anndata`, `mudata` |

Concretely: `adapters/anndata/conversion.py` may import `converters/`; `converters/long.py` importing
`anndata` would violate it. And the *point* of the constraint is the thing `AGENTS.md` asks for in its first
paragraph — that a future Parquet or JSON backend can supply the same typed inputs. That is only possible if
no computation module has an `anndata` import in it. `dep-inward-only` is the mechanical test for that
promise.

Checked directly: no module in `converters/`, `rules/`, `modifications/`, `params/`, `annotation/`,
`fasta/`, `readers/` or `proteobench/` imports `anndata_proteomics.adapters`, `anndata`, or `mudata`.

```bash
# empty output across all eight packages
rg -n '^from anndata_proteomics\.adapters|^import anndata\b|^from mudata import' converters rules modifications params annotation fasta readers proteobench
```

And the arrow points the right way: `adapters/anndata/*` imports `workflows/*` (five modules do), never the
reverse. **This is the hard architectural rule at the top of `AGENTS.md`, independently verified by an
outside instrument.** Worth recording as a pass — the other two reviews are lists of defects and could leave
the impression that nothing holds.

### C-2 — `entity-no-persistence-awareness` fails on `Parameters`

**Rule:** *entities must not know how they are persisted.*

```python
class Parameters(_Strict):          # params/model.py:216 — 34 fields
    def to_series(self) -> pd.Series:                     # :404
        return pd.Series({field: self._legacy_value(field) for field in _SERIES_FIELDS})
    @classmethod
    def from_series(cls, series: pd.Series) -> Parameters: # :409
```

`Parameters` knows the ProteoBench CSV layout: the ordered field list, the `acquisition_method` special
case, the legacy value coercions. A change to that CSV format edits the model. Two more instances:
`rules/registry.py:108` calls `rule.model_dump_json(...)`, and `modifications/sdrf.py:8` has
`to_sdrf_value(mod)` as a free function — which is the shape this rule prefers.

**Remedy the rule implies:** move `to_series` / `from_series` into `adapters/` (or a `proteobench/`
serializer) as free functions over `Parameters`. `modifications/sdrf.py` already demonstrates the pattern in
this codebase.

**This is the same defect our review names differently.** `AGENTS.md` says storage adapters are not the
computational model; `clean-architecture` says entities must not know how they are persisted. Same rule,
different vocabulary, arrived at independently.

### C-3 — `entity-value-objects`: APB is exemplary, and this is the skill's best news

**Rule:** *replace primitive types with value objects that encapsulate validation and behaviour; immutable,
compared by value, self-validating.*

APB does this thoroughly: `Probability` (closed [0,1] with a coercing validator), `MassTolerance`,
`RuleVersion = PresentRuleVersion | MissingRuleVersion`, `CleavageRule`, and the 18 named absent-case types.
`frozen=True, slots=True` is the house style. Primitive obsession is largely absent.

**But it exposes exactly one gap, and it is our headline.** The rule requires value objects that encapsulate
*validation **and behaviour***. APB's satisfy the first and — for the 18 identity types — **none** of the
second (see [review_principle_apb_concrete.md](review_principle_apb_concrete.md)). By this rule APB is
half-compliant in a way that reads as fully compliant from a type listing.

### C-4 — `dep-acyclic-dependencies` and `dep-interface-ownership`: no findings, and one reason to be careful

No import cycles between packages were found. `dep-interface-ownership` (*"interfaces belong to clients, not
implementers"*) produced **no findings for a reason worth recording: APB has almost no interfaces.** There
are no `Protocol` definitions in the layers reviewed; polymorphism is done with unions of concrete frozen
dataclasses. The rule has nothing to bite on.

That is not a defect — it is the correct Python form, and inventing `Protocol`s to satisfy the rule is the
trap [skill_principle.md](skill_principle.md) bounds against ("a `Protocol` with a single implementer is
indirection with no substitution benefit"). Recorded because **a rule that finds nothing can read as a rule
that passed**, and here it did not run.

### ✗ Contradiction 2 — `entity-rich-not-anemic` vs. "behaviour does not go on the persistence schema"

The sharpest conflict in this exercise, because both sides are right and the resolution is invisible from
either rule alone.

| | Says |
| --- | --- |
| `entity-rich-not-anemic` (impact: **HIGH**) | *"Entities should contain behavior, not just data. Anemic domain models push business logic into services, scattering rules and duplicating validation."* |
| [skill_concrete_draft.md](skill_concrete_draft.md) §5.3 | A pydantic model describes what may appear in a file. **Do not put the behaviour on it.** Add a runtime type and a factory. |

Point an agent at `ParseRule` with `entity-rich-not-anemic` loaded and it will add `convert()`,
`coerce_layer()` and `explode_fragments()` **to the pydantic model** — fusing the file format with the
computation, which is the root cause both our reviews identify. The rule is not wrong; it is being applied
to the wrong kind of object.

**The resolution exists inside `clean-architecture` — in a different rule file.** Its category 6 includes
`adapt-dto-transformation` (*"transform data between layers"*), and `dep-data-crossing-boundaries` says *use
simple data structures across boundaries*. Read together: **`ParseRule` is a DTO crossing a boundary, not an
entity**, so `entity-rich-not-anemic` does not apply to it, and the behaviour belongs on the entity the DTO
is transformed into — which is exactly our `LongConversion` / `FactorLayer` / `DuplicatePolicy`.

Three rules, three files, and the conclusion only appears when all three are held at once. **A skill with 42
rules across 8 reference files, of which an agent loads the one that matched, will reliably produce the
half-answer.** Concretely: `entity-rich-not-anemic` is `impact: HIGH` and category 2; `adapt-dto-transformation`
is category 6, MEDIUM. The higher-priority rule is the one that misleads, and it fires first.

---

## Shared blind spot — neither skill can see the dominant defect

Both skills, run over the same code:

- neither mentions `isinstance` chains, mode flags, or discriminated unions;
- neither has any notion of a validator standing in for a type;
- `python-design-patterns` shows a `dict[str, type]` registry as the *destination* and stops there —
  correct, and silent about the same case set leaking past the registry, which is F6;
- **neither has a rule that would find shape 4** (a split union whose consumers still discriminate). APB's
  18 behaviourless identity types are invisible to both. `entity-value-objects` comes closest and *approves*
  of them.

`clean-architecture` gets nearest by a different road: `entity-rich-not-anemic` would call those 18 classes
anemic. But it would then prescribe putting the behaviour on the wrong layer (Contradiction 2), so following
it produces a codebase with behaviour on its pydantic models and the same eighteen `isinstance` sites.

**This closes §5 of the assessment.** The gap it identified — *"neither covers `Protocol` as the unit of
interface or replacing type-dispatch with polymorphism, in Python, with worked examples"* — is now measured
rather than predicted. Between them the two skills found 7 findings, 4 of which our reviews already had,
0 of the shape-4 family, and produced 2 direct contradictions.

---

## What this means for installing them

Not a decision — the assessment's §8 questions, now answerable with evidence.

1. **`python-design-patterns` is worth reading and risky as a standing instruction.** Its unique value is
   P-2: the "7+ parameters" trigger independently found two of our findings. Its cost is Contradiction 1 —
   `SKILL.md` alone teaches "wait for three", which declines a class of finding both our reviews rest on. If
   installed, the Rule of Three caveat must be surfaced *in the navigation tier*, not left in
   `references/details.md`.
2. **`clean-architecture`'s `dep-` category earns its place** — it verified C-1 and found C-2, and its
   vocabulary (*persistence awareness*, *dependency direction*) names things `AGENTS.md` already requires,
   which makes it useful for arguing. Its `entity-` category is the hazard: `entity-rich-not-anemic` at HIGH
   priority actively pushes toward the defect. If installed, install the category, not the skill — or record
   the DTO exception where the agent will see it.
3. **Both are polyglot where it matters least and monoglot where it matters most.** `entity-rich-not-anemic`
   is Java, `entity-value-objects` is TypeScript — confirming the assessment's caveat. The Python form of
   both is the frozen dataclass, which APB already uses; neither skill shows it.
4. **The local skill covers what neither does**, and this review is the argument for finishing it rather than
   installing a substitute. But it now has two obligations it did not have before: it must say what to do
   when Rule of Three is also loaded, and it must state the DTO/entity distinction in terms an agent holding
   `entity-rich-not-anemic` will recognise.

---

## Method and honest limits

- **`python-design-patterns`** was read complete (both files it ships).
- **`clean-architecture`** was read as `SKILL.md` + the 6 `dep-` rules from the local copy + 2 `entity-`
  rules fetched read-only. **34 of 42 rule files were not read** — the `usecase-`, `comp-`, `bound-`,
  `frame-` and `test-` categories are unexamined, and findings there are possible. The categories chosen are
  the two the skill itself ranks CRITICAL.
- **Mechanical checks** (function length, parameter counts, field counts, import direction) are AST and grep
  scans over `apb/src/anndata_proteomics`, reproducible from the commands quoted above.
- **`scripts/` is included** in the length scan and excluded from everything else; it is tooling, not the
  library.
- **The contradictions are the load-bearing claims here**, and each is quoted from both sides rather than
  paraphrased, so they can be checked without re-reading either skill.
