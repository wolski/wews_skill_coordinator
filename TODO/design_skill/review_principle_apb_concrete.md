# APB reviewed with the concrete skill

> **What this is.** [skill_concrete_draft.md](skill_concrete_draft.md) used as an instrument on
> `apb/src/anndata_proteomics`. Date: 2026-08-12. **APB only** — no `prozor`, no `apb_studio`.
>
> **Not a re-run of [review_principle_apb.md](review_principle_apb.md).** That review worked
> `converters/`, `rules/`, `modifications/apply_rules.py` and `readers/`. This one runs the skill's greps
> over the packages it never opened — `workflows/`, `adapters/`, `annotation/`, `fasta/`, `proteobench/`,
> `description.py`, `params/parsers/` — and reports what the skill finds there, plus a verdict on the skill
> itself.
>
> **No code was changed.** The first review is untouched.

---

## Headline: APB created 18 types to avoid `| None`, and gave 0 of them a method

An AST scan of every class named `Missing*` or `No*` (excluding exceptions):

| | |
| --- | --- |
| Identity / absent-case types defined | **18** |
| …that carry a single method | **0** |
| `isinstance(…, Missing…)` sites | **18**, across 8 modules |

```
MissingNamespaceText            MissingSearchParameters (×2, two modules)   MissingStoredRule
MissingRuleMetadata             MissingQcMetadata                MissingProteoBenchMetadata
MissingQuantificationLevel      MissingSoftwareName              MissingGeneName
MissingFastaHeaderDescription   MissingDiannVersion              MissingRuleVersion
MissingProteinSearchParameters  NoAdjacentResidue                NoQuantification
NoValuePattern                  NonNumericToken
```

Plus three more of the same shape that the `Missing*`/`No*` grep misses:
`StoredCleavageOrTrypsin`, `StoredMinimumLengthOrDefault`, `StoredMaximumLengthOrDefault`.

**This is the skill's shape 4 — "a discriminated union you already split, whose consumers still
discriminate" — at package scale, and it settles a question the first review could only assert.** APB did
not fail to adopt the modelling discipline. It adopted it *thoroughly*: eighteen types exist for no reason
other than to keep `| None` out of a field. Every one is an empty class, and every consumer asks which one
it holds.

The lesson that follows is the one the skill leads with, now evidenced rather than argued:

> The rule "replace `| None` with a named absent case" is **half a remedy**, and the half that removes
> branches is the other one. Adopted alone, at scale, it produces a codebase with more types and exactly as
> many `if`s — plus eighteen classes to read.

---

## Method, and a reproducibility check

Ran the skill's §3 shapes in order, with its §2 bounds applied to each candidate.

**Shape 1 — the validator-message grep — reproduced the first review exactly.** The skill's grep

```bash
rg -n 'is only valid (for|when)|only valid if|cannot define|requires .* when' --type py
```

returns six lines in four sites: `parse_rule.py:165`, `parse_rule.py:218`, `rule_components.py:205/209`,
`params/model.py:151/153`. Those are F1, F2, F4 and the withdrawn `MassTolerance` candidate — **no new
shape-1 findings anywhere in APB.** The instrument is stable, and the first review's rank-1 pass was
complete.

Everything below comes from shapes 2–5 in packages the first review did not open.

---

## C1 — `workflows/fasta.py`: three identity types whose docstrings state the behaviour they do not implement

**Shapes 2, 3, 4. Evidence.** The sharpest example of the headline, and the one to put in the skill.

Three empty dataclasses, each documenting a fallback policy:

```python
@dataclass(frozen=True, slots=True)
class StoredCleavageOrTrypsin:
    """Use the stored enzyme when present, otherwise Trypsin."""      # ← the whole behaviour, in prose

@dataclass(frozen=True, slots=True)
class StoredMinimumLengthOrDefault:
    """Use stored minimum peptide length, otherwise APB's default."""

@dataclass(frozen=True, slots=True)
class StoredMaximumLengthOrDefault:
    """Use stored maximum peptide length, otherwise APB's default."""
```

The behaviour each docstring describes is implemented three times, in three free functions, by
`isinstance`:

```python
def _resolve_minimum_length(                                          # workflows/fasta.py:436
    selection: MinimumLengthSelection,
    search_parameters: ProteinSearchParameterState,
) -> int:
    if isinstance(selection, MinimumPeptideLength):
        return selection.value
    if (
        isinstance(search_parameters, StoredProteinSearchParameters)
        and search_parameters.parameters.min_peptide_length is not None
    ):
        return int(search_parameters.parameters.min_peptide_length)
    return _DEFAULT_MIN_LENGTH
```

`_resolve_maximum_length` (`:450`) is the same body with `max_` substituted. `_resolve_cleavage` (`:416`)
is the same body with a four-arm head instead of two and a `logger.warning` before the default.
**Three functions, one shape, one case set each — and the case sets are the unions declared at lines
74/91/108.**

### A bound firing inside a single `if`, worth recording

The second condition is two checks with **opposite verdicts**:

- `isinstance(search_parameters, StoredProteinSearchParameters)` — asks *which variant is this*, on a
  two-member union APB owns, in three functions. **Shape 4. A finding.**
- `search_parameters.parameters.min_peptide_length is not None` — asks *did the vendor state a value*, on a
  DTO parsed from a vendor file. **Bound 1. Not a finding.** Absence, not kind.

The skill's §1 question is asked per-branch; this site shows it must be asked **per-condition**. That is an
amendment, recorded in §Verdict.

### Remedy

The selection types answer *"what value should I use?"*, and the stored-parameter state answers *"do you
have one?"*. Two small polymorphisms, no free functions:

```python
@dataclass(frozen=True, slots=True)
class MinimumPeptideLength:
    value: int
    def resolve(self, stored: ProteinSearchParameterState) -> int:
        return self.value                                    # explicit override ignores stored

@dataclass(frozen=True, slots=True)
class StoredMinimumLengthOrDefault:
    """Use stored minimum peptide length, otherwise APB's default."""
    def resolve(self, stored: ProteinSearchParameterState) -> int:
        return stored.min_peptide_length(default=_DEFAULT_MIN_LENGTH)   # ← docstring, now executable


@dataclass(frozen=True, slots=True)
class StoredProteinSearchParameters:
    parameters: Parameters
    def min_peptide_length(self, *, default: int) -> int:
        value = self.parameters.min_peptide_length            # `is None` stays: bound 1, absence
        return default if value is None else int(value)

@dataclass(frozen=True, slots=True)
class MissingProteinSearchParameters:
    def min_peptide_length(self, *, default: int) -> int:
        return default                                       # identity arm
```

Call sites become `inputs.minimum_length.resolve(inputs.search_parameters)`. All three `_resolve_*`
functions disappear; the `is not None` survives, on the one type that owns the parsed value, because it is
asking what happened.

**What this buys.** The `logger.warning` in `_resolve_cleavage` moves onto
`StoredCleavageOrTrypsin.resolve`, where "no enzyme and no override" is a state that class exists to
represent, instead of a fall-through at the bottom of a chain. Adding a fourth cleavage selection becomes
one class the type checker forces you to complete.

---

## C2 — `proteobench/metrics.py`: one string doing three jobs

**Shape 5 (a mode laundered through a string). Evidence.** The clearest instance in APB, and it is subtle
because the string is genuinely also a label.

```python
def _precision_metrics(frame, cutoff, *, aggregation: str) -> dict[str, float]:   # :160
    center_name = "median" if aggregation == "median" else "mean"                 # :167  job 1
    centers = grouped.transform(center_name)
    aggregate = _absolute_aggregate(aggregation)                                  # :170  job 2
    ...
    return {f"{aggregation}_abs_epsilon_precision_global": ...}                   # :183  job 3

def _absolute_aggregate(name: str) -> MetricAggregate:                            # :201
    if name == "median":
        return _median_absolute
    if name == "mean":
        return _mean_absolute
    raise ValueError(f"unsupported aggregation {name!r}")
```

The same `str` is (1) a pandas method name, (2) a dispatch key, (3) an output-column prefix. Job 3 is why
nobody noticed jobs 1 and 2 — a label has to be a string, so the parameter looks like data.

Note the ternary at `:167`: `"median" if aggregation == "median" else "mean"` is a **no-op that reads as a
normalisation**. It maps `"median"→"median"` and everything else→`"mean"`, so an unsupported value silently
becomes `mean` at line 167 and then raises at line 203. Two validation regimes for one parameter.

### Remedy

```python
@dataclass(frozen=True, slots=True)
class MedianAggregation:
    label: str = "median"                       # job 3
    pandas_name: str = "median"                 # job 1
    def absolute(self, values: pd.Series) -> float:
        return float(values.abs().median())     # job 2

@dataclass(frozen=True, slots=True)
class MeanAggregation:
    label: str = "mean"
    pandas_name: str = "mean"
    def absolute(self, values: pd.Series) -> float:
        return float(values.abs().mean())

type Aggregation = MedianAggregation | MeanAggregation

_BY_NAME: dict[str, Aggregation] = {"median": MedianAggregation(), "mean": MeanAggregation()}

def aggregation_for(name: str) -> Aggregation:       # lookup, per the skill's naming rule
    ...
```

`_precision_metrics(..., aggregation: Aggregation)` then uses `aggregation.pandas_name`,
`aggregation.absolute(...)` and `aggregation.label` — the ternary goes, `_absolute_aggregate` goes, and the
single validation point moves to `aggregation_for` at the CLI/config boundary where the string arrives.

**Bound checked:** the incoming value *is* a foreign string from config, so bound 2 applies — to
`aggregation_for`, which is exactly where the `isinstance`-equivalent belongs. Past that boundary the type
is APB's.

---

## C3 — the delimiter-by-extension rule now lives in three packages

**Shape 2, cross-package. Evidence.** Extends F6 rather than duplicating it.

`annotation/loader.py:62-70` enumerates its own extension set and re-derives the CSV/TSV delimiter:

```python
suffix = source.suffix.lower()
if suffix == ".toml":
    annotation = _load_toml(source)
elif suffix in {".csv", ".tsv"}:
    separator = "," if suffix == ".csv" else "\t"
    annotation = AnnotationTable(samples=pd.read_csv(source, sep=separator))
else:
    raise ValueError(f"Unsupported annotation format ...")
```

`separator = "," if suffix == ".csv" else "\t"` is the same knowledge as `readers/tabular.py`'s six
delimiter-binding wrappers and `readers/dispatch.py`'s two registry dicts — **a third package, with its own
spelling.** F6's remedy (`DelimitedText(FixedDelimiter(","))` and `format_for(path)`) covers this site too;
`annotation/loader.py` becomes `format_for(source).read(source)` for the tabular arm, keeping only its own
`.toml` case.

**Bound checked:** the suffix is a foreign `str` off a `Path`, so this is not an `isinstance` case — it is
bound 2's "the branch belongs at the boundary that produces your own types", and the defect is that three
boundaries exist for one decision.

---

## C4 — `fasta/annotation.py`: two split unions discriminated inside comprehensions

**Shape 4. Evidence.**

```python
type GeneNameResult = GeneName | MissingGeneName                        # :89
type FastaHeaderDescriptionResult = FastaHeaderDescription | MissingFastaHeaderDescription   # :104
```

Both correctly modelled, neither carrying a method, and the discrimination is inlined into pandas
expressions:

```python
"fasta.header": (header.value if isinstance(header, FastaHeaderDescription) else pd.NA),      # :259
present_gene_names = gene_names.map(lambda result: isinstance(result, GeneName))              # :294
[result.value if isinstance(result, GeneName) else pd.NA for result in gene_names],           # :297
```

Line 294 is the tell that the type is being used as a boolean: `map(lambda r: isinstance(r, GeneName))`
is `is not None` with more syntax.

### Remedy

The question all three sites ask is *"what goes in the DataFrame cell?"*:

```python
@dataclass(frozen=True, slots=True)
class GeneName:
    value: str
    def cell(self) -> str: return self.value
    def present(self) -> bool: return True

@dataclass(frozen=True, slots=True)
class MissingGeneName:
    def cell(self) -> float: return pd.NA
    def present(self) -> bool: return False
```

`[result.cell() for result in gene_names]` and `gene_names.map(GeneNameResult.present)`. Same for the header
union. Two methods on two tiny classes remove three inline discriminations.

**Why this one is worth reporting despite being small:** it is where the shape hides. Nobody scanning for
`isinstance` chains looks inside a list comprehension or a lambda, and both are inside pandas expressions
where a conditional reads as data plumbing.

---

## C5 — `MissingSearchParameters` is defined twice, in two packages

**Not a shape — a consequence of one.** `description.py:23` and `adapters/anndata/params.py:23` both define
a class of that name, and `adapters/anndata/params.py:35` returns `Parameters | MissingSearchParameters`
using its own. Two identity types for one absent case, distinguishable only by import path.

This is what eighteen behaviourless marker classes cost: they are cheap to write, so they get rewritten
rather than found. **A type with a method gets imported; a type that is only a tag gets re-declared.**
Recorded as evidence for the headline, not as separate work — C1's remedy is what makes these types worth
importing.

---

## Non-findings — bounds that fired in the new packages

The skill's bounds rejected more than they passed here, as in the first review.

- **`adapters/anndata/summary_metadata.py` (`isinstance(raw, str)`, `isinstance(raw, dict)`) — bound 2.**
  Narrowing values read back out of an HDF5/`uns` payload. Foreign until proven otherwise.
- **`annotation/loader.py:84-94` (`isinstance(obs, dict)`, `isinstance(samples, list)`) — bound 2.**
  Validating a decoded TOML document.
- **`annotation/validate_fasta.py` (6 × `isinstance(sequence, str)`) — bound 2.** Guarding against
  non-string cells in an object-dtype pandas column. Ugly, not a polymorphism problem — the fix is dtype
  discipline upstream, which is a different review.
- **`proteobench/metrics.py:220-227` (`isinstance(value, bool)`) — bound 1 + 2.** Excluding `bool` from an
  `int` check, the standard Python wart.
- **`params/parsers/*.py` — bound 2 throughout.** Twelve vendor parsers narrowing text and dicts.
- **`workflows/conversion.py:82` and `:108`** — `method = "software_version" if isinstance(version,
  PresentRuleVersion) else "columns"`, duplicated verbatim in two functions. Shape 5, and it *is* the shape
  — but the string is a provenance label written into `description`, never dispatched on. **Bound: two arms
  that will not grow, and no second dispatch.** Report as duplication, not as a missing polymorphism. Worth
  one line: hoist the ternary into `RuleVersion.selection_method()` and both copies go.

---

## Verdict on the skill

**What worked.**

1. **Shape 4 was the highest-yield check by a wide margin** — C1, C4, C5 and the headline all come from it.
   The skill promoting it to a first-class shape (the first review had to discover it mid-pass) is what made
   this review fast.
2. **Shape 5's grep found C2**, which no `isinstance` scan would reach. `-> str` returning literals is a
   cheap, high-signal query.
3. **The `Missing*`/`No*` prefix scan is the single best query in this codebase**, and the skill does not
   contain it. See amendments.
4. **The bounds did the work again.** ~40 candidates in the new packages, 5 findings. Bound 2 alone
   rejected the whole of `params/parsers/` and `annotation/validate_fasta.py`.

**What the skill got wrong or missed — four amendments.**

1. **Add a shape-4 grep the skill currently lacks.** It says "grep each member class name outside its own
   module", which requires already knowing the members. The generative query is:
   ```bash
   rg -n '^class (Missing|No|Empty|Absent|None|Null|Unset)[A-Z]' --type py   # find identity types
   rg -n 'isinstance\([^,]+, (Missing|No)[A-Z]\w*\)' --type py               # find their discriminators
   ```
   Two lines, and in APB the first returns 18 classes and the second 18 sites. **A codebase that has adopted
   named absent cases has this shape by default** — the discipline creates the types; nothing makes anyone
   add the method.
2. **§1's question must be asked per *condition*, not per branch.** C1's second `if` contains one finding
   and one bound-1 non-finding joined by `and`. A reader applying the skill per-`if` gets the wrong verdict
   either way round.
3. **Add the docstring tell.** *An empty class whose docstring describes behaviour is a missing method* —
   `"""Use the stored enzyme when present, otherwise Trypsin."""` on a class with no methods is the shape
   announcing itself in prose. Grep-able as a class body with a docstring, no fields and no methods.
4. **§5.2 needs a corollary for labels.** C2's string is a discriminator *and* a legitimate output label.
   The skill's "return the result, not the name of the operation" would have you delete the string; the
   right move is to keep it as a `label` field on the type and stop dispatching on it. **A discriminator
   that doubles as display text is the hardest case to see and the easiest to over-correct.**

**What the skill over-flagged.** Nothing outright, but shape 5 flagged
`workflows/conversion.py:82` correctly by pattern and wrongly by consequence — the string is never
dispatched on. The skill needs shape 5 to say: *check the far end actually branches on it*; if nothing does,
it is duplication, not a missing polymorphism.

---

## Back-test: the skill on the first review's own territory

The two reviews cover different packages, so **7 findings versus 5 says nothing about the instrument.** The
question that does have an answer: *run the skill's new queries over `converters/`, `rules/`,
`modifications/` and `readers/` — the first review's declared scope — and does it find anything that review
missed?*

**Yes — one solid finding.** And the other two candidates it turned up are the reason the skill now has a
site-count bound.

```bash
rg -n '^class (Missing|No|Non)[A-Z]' converters rules modifications readers   # → 4 hits
```

| Union | Consumer sites | Verdict |
| --- | --- | --- |
| `RuleVersion = PresentRuleVersion \| MissingRuleVersion` | **6, in 4 modules** | **Finding. Missed by the first review.** |
| `NoValuePattern \| RegexValuePattern` | 2 | Already reported — F5 |
| `AdjacentResidue \| NoAdjacentResidue` | 1 | **Not a finding** — bound M2 |
| `ParsedMass \| NonNumericToken` | 1 | **Not a finding** — bound M2 |

**Self-correction:** an earlier version of this section listed all three unreported unions as misses. Two of
them are discriminated in exactly **one** place each, which is bound M5 territory — two arms that will not
grow. Counting them was the skill over-reporting, and it is what produced bound **M2: a union needs ≥ 2
consumer sites, ideally in ≥ 2 modules, before it is worth reporting.** The back-test's honest result is
**one** missed finding, not three.

### The missed finding that matters: `RuleVersion`

```python
if isinstance(version, PresentRuleVersion):                                    # converters/pipeline.py:111
method = "software_version" if isinstance(version, PresentRuleVersion) else "columns"   # workflows/conversion.py:82
method = "software_version" if isinstance(version, PresentRuleVersion) else "columns"   # workflows/conversion.py:108
version_label = version.value if isinstance(version, PresentRuleVersion) else "missing" # scripts/cli.py:351
version_label = version.value if isinstance(version, PresentRuleVersion) else "missing" # scripts/cli.py:482
if isinstance(resolution.version, MissingRuleVersion):                                 # scripts/cli.py:500
```

**Two derived strings, each computed twice, verbatim.** `method` in two places in `workflows/conversion.py`;
`version_label` in two places in `scripts/cli.py`. They are two methods that do not exist:

```python
@dataclass(frozen=True, slots=True)
class PresentRuleVersion:
    value: str
    def selection_method(self) -> str: return "software_version"
    def label(self) -> str: return self.value

@dataclass(frozen=True, slots=True)
class MissingRuleVersion:
    def selection_method(self) -> str: return "columns"
    def label(self) -> str: return "missing"
```

Six discriminations become `version.selection_method()` and `version.label()`. **`converters/pipeline.py`
is squarely inside the first review's scope and it was not reported** — this is a miss, not a scope
difference.

`AdjacentResidue | NoAdjacentResidue` is the instructive *non*-finding: it is returned by
`_adjacent_residue()`, which the first review cited as a consumer of `ModificationLocation`. So the review
did walk past a second union in the same function — but with one consumer, walking past it was **correct**.
Two instruments, same verdict, and only the second one can say why.

### Why the skill found it and the principles did not

Not because the skill is stricter. Because **shape 4 exists in it as a first-class shape with its own scan.**
The first review had no such shape — it discovered the pattern mid-pass, after `isinstance` and validator
greps had already set its candidate list, so nothing sent it looking for identity types by name.

Honest attribution: the skill as written says *"grep each member class name outside its own module"*, which
requires already knowing the members. The generative query — `^class (Missing|No|Non)[A-Z]` — is amendment 1
above, derived while using the skill rather than supplied by it. **The skill made the shape findable; using
it made the query.**

### And one false positive the skill produced that the first review never hit

Shape 5 flagged `workflows/conversion.py:82` as a laundered discriminator. By pattern it is one. By
consequence it is not — nothing downstream branches on `"software_version"`; it is written into
`description` as a provenance label. The bound had to be applied by hand, which is amendment 4. **Net
precision is therefore about level, not better:** more true positives, one new class of false positive,
both now patched.

---

## Comparison to the first review

| | [review_principle_apb.md](review_principle_apb.md) | this one |
| --- | --- | --- |
| Instrument | the two principles, ranked by checkability | the concrete skill's 7 shapes + 4 bounds |
| Scope | `converters/`, `rules/`, `modifications/apply_rules.py`, `readers/` | `workflows/`, `adapters/`, `annotation/`, `fasta/`, `proteobench/`, `description.py`, `params/parsers/` |
| Findings | 7 + 1 withdrawn | 5 + 1 headline count |
| Rank-1 (validator) findings | 3 | **0 new** — the first pass was complete |
| Dominant shape | split-that-stopped-halfway (asserted from 3 unions) | same shape, **measured**: 18 types, 0 methods |

The two reviews agree on the diagnosis and disagree on nothing. The second one's contribution is that the
central claim stopped being an interpretation of three examples and became a count.
