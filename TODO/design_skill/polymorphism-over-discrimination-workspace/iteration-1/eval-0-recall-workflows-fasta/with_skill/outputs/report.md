# Design review: `workflows/fasta.py` and `workflows/conversion.py`

Read-only review. No files under `apb/` were modified.

## Short answer

The design is broadly sound — both modules honour the typed-boundary rule, take concrete values,
and never touch `.X`/`.obs`/`.uns`. The `_resolve_*` trio is not sound, and your instinct is right,
but it is repetitive for a narrower reason than it looks.

**Three type unions were split and then never given the method that justified splitting them.**
The dispatch that should be a method is hand-written three times as an `isinstance` cascade. On top
of that, a fourth union (`ProteinSearchParameterState`) is discriminated once inside each of those
three cascades, purely so the code can ask "are you the present one?" before reading a field.

Of the eight `isinstance` sites in `workflows/fasta.py`, **seven** are that defect. Removing them
needs two moves and no new module, function, or file. The residual repetition that remains after
those two moves is **not** a defect and I would leave it — see "What I would not do".

## How I got the worklist

`scripts/find_candidates.py` over `apb/src/anndata_proteomics` (97 modules, 251 classes, ~2 s). It
rejected **132 foreign `isinstance` targets** (`str`, `dict`, `list`, `int`, `float`, `h5py.Group`,
`ndarray`, `MuData`) before anything was read, leaving 99 owned-target candidates package-wide. Ten
of those 99 are in the two files you named: 8 in `fasta.py`, 2 in `conversion.py`.

---

## Finding A — the `_resolve_*` trio

**Shapes:** 4 (a union you already split, whose consumers still discriminate) and 6 (`isinstance`
chain).
**File:** `/Users/wolski/projects/anndata_bridge/apb/src/anndata_proteomics/workflows/fasta.py`
lines 55-110 (the types), 259-286 and 416-461 (the consumers).

### Why it feels repetitive: name the thing that is repeated

The three functions are the same five-line template, once per digestion setting:

```
if isinstance(selection, <TheExplicitOne>):                  return <use it>
if <parameters are present> and <that field> is not None:     return <derive from stored>
return <APB default>
```

That template is a **precedence policy** — *explicit override → stored search parameter → APB
default* — and it is written out longhand three times rather than expressed once. The cost of a
fourth digestion setting (missed cleavages, say) is currently: 2 dataclasses, 1 module-level
singleton, 1 free function, 1 field on `ProteinAnnotationInput`, 1 field on
`AnnDataProteinFastaConfig`, and 1 ternary in `cli.py`. Six edits in three files for one setting.
That is the repetition you are feeling, and it is real.

But only part of it is a defect, and separating the two parts is the whole point of the review.

### Per condition, not per branch

Judging each `if` as a unit gives the wrong answer here, because `_resolve_cleavage` joins a finding
and a non-finding with `and`:

| Line | Condition | Asks | Verdict |
| --- | --- | --- | --- |
| 420 | `isinstance(selection, NamedCleavage)` | which variant | **finding** |
| 422 | `isinstance(selection, CustomCleavage)` | which variant | **finding** |
| 425 | `isinstance(search_parameters, StoredProteinSearchParameters)` | which variant | **finding** |
| 426 | `search_parameters.parameters.enzyme is not None` | did the vendor state one | **correct — keep** |
| 440 | `isinstance(selection, MinimumPeptideLength)` | which variant | **finding** |
| 443 | `isinstance(search_parameters, StoredProteinSearchParameters)` | which variant | **finding** |
| 444 | `...min_peptide_length is not None` | did the vendor state one | **correct — keep** |
| 454 | `isinstance(selection, MaximumPeptideLength)` | which variant | **finding** |
| 457 | `isinstance(search_parameters, StoredProteinSearchParameters)` | which variant | **finding** |
| 458 | `...max_peptide_length is not None` | did the vendor state one | **correct — keep** |

The three `is not None` checks ask what *happened* — the vendor parameter file was silent about this
setting. That is ordinary control flow and survives the remedy unchanged. **Anyone who tells you
those three lines are the problem is misreading it**; they are the correct half.

### Bounds, honestly graded

- **B1 — cleared firmly.** All five classes (`NamedCleavage`, `CustomCleavage`,
  `MinimumPeptideLength`, `MaximumPeptideLength`, `StoredProteinSearchParameters`) are defined in
  `workflows/fasta.py` itself. You can give them methods.
- **B2 — mixed, and I want to be precise.** Each `*Selection` union is discriminated at exactly
  **one** site, which on its own is B2/B5 territory. `ProteinSearchParameterState` is discriminated
  at **3 sites in 1 module** — clears the site threshold, weak on the two-module threshold.
- **Evidence vs judgement.** The *shape-4 diagnosis is evidence*: three unions, zero methods
  between them, and the docstrings describe behaviour on classes that have none —
  `"""Use stored search enzyme, with a visible trypsin fallback."""`,
  `"""Use stored minimum peptide length, otherwise APB's default."""`. A docstring that describes
  behaviour on a class with no methods is the finding announcing itself in prose. The *repetition
  argument above is judgement*, resting on the growth cost rather than on a site count.

### Gate 1 — name the question every arm answers

- `CleavageSelection` → *"which cleavage rule digests these proteins?"* → `resolve() -> ResolvedCleavage`
- `MinimumLengthSelection` / `MaximumLengthSelection` → *"what peptide-length bound does the digest use?"* → `resolve() -> int`

Nameable, so these are not DTOs. Gate passes.

`ProteinSearchParameterState` is the interesting one: the question its arms answer is *"what did the
search parameters state?"* — which is not behaviour at all. It does not need a method. It needs an
**identity value**, which is the second remedy option, and it is why this union should disappear
rather than grow a method.

### Gate 2 — is any of this a storage schema?

The `*Selection` types: **no**. Plain frozen slotted dataclasses in the workflow module, constructed
by `cli.py:652-666` and defaulted in `AnnDataProteinFastaConfig`. Behaviour may go on them.

`params.model.Parameters`: **yes** — pydantic `_Strict`, describing what may appear in a vendor
parameter file. **Do not put digestion policy on it.** This is the trap worth naming explicitly,
because "give `Parameters` a `min_length_or_default()`" removes the same branches and looks clean
while fusing the vendor file format with the digestion computation and pointing a dependency the
wrong way.

### Move 1 — delete `ProteinSearchParameterState`; give the absent case an identity value

`Parameters()` constructs cleanly with every relevant field `None` (verified in the repo env:
`enzyme=None, min_peptide_length=None, max_peptide_length=None`; the model has no required fields).
That *is* "search parameters that state nothing". The package already has the precedent:
`rules/rule_document.py` takes plain `Parameters` in `matches()` and `is_available_for()` and treats
unset fields as "not stated" — no absent-case union in sight.

```python
# workflows/fasta.py — delete StoredProteinSearchParameters, MissingProteinSearchParameters,
# ProteinSearchParameterState, MISSING_PROTEIN_SEARCH_PARAMETERS (lines 113-127).

@dataclass(frozen=True, slots=True)
class ProteinAnnotationInput:
    protein_groups: pd.Series
    match_on: str
    search_parameters: Parameters          # was ProteinSearchParameterState
    ...
```

The three compound conditions each collapse to their correct half. Three of the eight `isinstance`
sites in the file go away.

**This is also a double read removed at the adapter.** `adapters/anndata/fasta.py:252-256` currently
calls `has_search_parameters(target)` *and then* `require_search_parameters(target)` — two namespace
reads — to rebuild a union that `read_search_parameters(target)` already returns. After Move 1:

```python
# adapters/anndata/fasta.py
stored = read_search_parameters(target)
search_parameters = Parameters() if isinstance(stored, MissingSearchParameters) else stored
```

**Behaviour is unchanged.** Today `_resolve_cleavage` emits the same warning for "no parameters at
all" and "parameters with no enzyme"; with the identity value the warning condition is literally the
same predicate. Nothing anywhere distinguishes the two states — I checked every reader of
`search_parameters`, and `ProteinAnnotationProvenance` records only the resolved values, not their
source. The "were parameters stored" fact is already recorded separately as
`search_parameters_version_status` by `adapters/anndata/conversion.py:92`.

Worth noting while you are here: `MissingProteinSearchParameters` is the **third** near-identical
absent-parameters type in the package, alongside `MissingSearchParameters` in
`adapters/anndata/params.py:23` and another in `description.py:23`. The candidate script grades the
`adapters` one higher than the workflow one (3 sites / 2 modules). Move 1 removes one of the three;
the other two are outside the files you named.

### Move 2 — put `resolve` on the selection types

```python
@dataclass(frozen=True, slots=True)
class StoredCleavageOrTrypsin:
    """Use stored search enzyme, with a visible trypsin fallback."""

    def resolve(self, parameters: Parameters) -> ResolvedCleavage:
        if parameters.enzyme is None:                      # what happened — correct guard, kept
            logger.warning(
                "no enzyme in search parameters and no cleavage override; "
                "using Trypsin for the peptide count"
            )
            return DEFAULT_CLEAVAGE
        return resolve_cleavage_name(parameters.enzyme)


@dataclass(frozen=True, slots=True)
class NamedCleavage:
    """Use one explicit enzyme name."""

    enzyme: str

    def resolve(self, parameters: Parameters) -> ResolvedCleavage:
        return resolve_cleavage_name(self.enzyme)


@dataclass(frozen=True, slots=True)
class CustomCleavage:
    """Use one explicit cleavage rule."""

    rule: CleavageRule

    def resolve(self, parameters: Parameters) -> ResolvedCleavage:
        return custom_cleavage(self.rule)


@dataclass(frozen=True, slots=True)
class StoredMinimumLengthOrDefault:
    """Use stored minimum peptide length, otherwise APB's default."""

    def resolve(self, parameters: Parameters) -> int:
        if parameters.min_peptide_length is None:
            return _DEFAULT_MIN_LENGTH
        return int(parameters.min_peptide_length)


@dataclass(frozen=True, slots=True)
class MinimumPeptideLength:
    """Use one explicit minimum peptide length."""

    value: int

    def resolve(self, parameters: Parameters) -> int:
        return self.value
```

`Maximum*` mirrors it. The call site becomes three lines with no branch, and `_resolve_cleavage`,
`_resolve_minimum_length` and `_resolve_maximum_length` are deleted:

```python
def resolve_protein_annotation_input(
    inputs: ProteinAnnotationInput,
) -> ProteinAnnotationCalculation:
    """Resolve digestion selections without consulting a storage backend."""
    cleavage = inputs.cleavage.resolve(inputs.search_parameters)
    minimum = inputs.minimum_length.resolve(inputs.search_parameters)
    maximum = inputs.maximum_length.resolve(inputs.search_parameters)
    ...
```

**No import moves, no cycle, no new module.** `resolve_cleavage_name`, `custom_cleavage`,
`DEFAULT_CLEAVAGE`, `logger` and `Parameters` are already imported at the top of
`workflows/fasta.py`, and `.importlinter` places `workflows` above both `params` and `fasta`, so the
methods live exactly where the classes already are. Methods are compatible with
`frozen=True, slots=True`.

`tests/test_architecture_boundaries.py:132` already forbids `adapters/anndata/fasta.py` from calling
`resolve_protein_annotation_input`, `resolve_cleavage_name` or `custom_cleavage` directly, so the
gate that would catch the wrong version of this remedy (resolving in the adapter) is already in
place.

### Do I need a factory?

No, and that matters — a union with nothing to construct it is unfinished, but this one is already
finished. `cli.py:652-666` maps `options.cleavage: str | None` to a selection in one ternary at the
composition root, and `AnnDataProteinFastaConfig` supplies the defaults. A single dispatch point at a
composition root is the cure, not the smell. Adding a `make_cleavage_selection()` would be a wrapper
with one caller.

### Branch count after the remedy

Seven of the eight owned-target `isinstance` sites in `workflows/fasta.py` are gone, along with three
functions, one three-member union, one singleton constant, and one redundant namespace read in the
adapter. If any of the seven survive, the polymorphism moved rather than happened.

### What I would not do

**Do not generalise the three `resolve` bodies into one `StoredOrDefault[T](field_name, default)`.**
After Move 2, `StoredCleavageOrTrypsin.resolve`, `StoredMinimumLengthOrDefault.resolve` and
`StoredMaximumLengthOrDefault.resolve` are still three copies of "read one field; if it is `None` use
a default". That is where the repetition instinct wants to keep going, and it should stop.

The generic version is parameterised by a **field name**, not by behaviour: it trades three
three-line methods, each naming a real setting and type-checked against `Parameters`, for one
reflective accessor the type checker cannot follow. It exists to reduce a count, which is the defect
the diagnostics are meant to detect rather than a way to satisfy them. Three short methods that each
name a genuinely different setting are the correct end state.

The honest summary: about a third of the repetition you have been feeling is a real missing
polymorphism, and the rest is the irreducible cost of three distinct settings. Removing the first
third makes the remainder stop looking like a smell.

---

## Finding B — `RuleVersion` in `workflows/conversion.py`

**Shapes:** 4 and 2 (the same case set branched on in more than one function).
**Grade: evidence**, and on the bounds this is the *stronger* of the two findings.
**File:** `/Users/wolski/projects/anndata_bridge/apb/src/anndata_proteomics/workflows/conversion.py`
lines 82 and 108.

```python
method = "software_version" if isinstance(version, PresentRuleVersion) else "columns"
```

That line appears **twice, verbatim, 26 lines apart** — in `select_rule_from_parameters` and again
inside the loop of `select_rules_from_parameters`.

**Bounds:** B1 cleared (`PresentRuleVersion` / `MissingRuleVersion` are defined in
`rules/parse_rule.py:79-92`). B2 cleared decisively — **7 sites across 4 modules**, well past the
two-module threshold, and the top-ranked shape-4 hit in the whole package:

| Site | What it does |
| --- | --- |
| `rules/parse_rule.py:386` | filter candidate documents by version — **the only behaviour selection** |
| `converters/pipeline.py:109-112` | `version_status()` → `"present"` / `"missing"` for storage |
| `workflows/conversion.py:82` | → `"software_version"` / `"columns"` for storage |
| `workflows/conversion.py:108` | the same expression again |
| `scripts/cli.py:351` | `version.value if isinstance(...) else "missing"` for display |
| `scripts/cli.py:482` | the same expression again |
| `scripts/cli.py:500` | `if isinstance(resolution.version, MissingRuleVersion): logger.warning(...)` |

`MissingRuleVersion` has zero methods and a docstring that describes a situation.

### B3 — the mode-string shape does **not** fire, and that changes the remedy

I checked whether anything branches on `"software_version"` / `"columns"`. Nothing does.
`RuleSelectionMethod` is a `Literal` written to the APB namespace as `uns["rule_selection_method"]`
(`adapters/anndata/conversion.py:50, 78`), and the only other use is `methods.add(...)` followed by
`len(methods) != 1` in `to_mudata` — a **uniqueness check**, which is value validation, not kind
discrimination.

So these strings are **labels, not laundered discriminators**. That rejection matters: the tempting
remedy "give `RuleVersion` a `selection_method()` method" would in general be the anti-pattern of
returning a token instead of a result. Here it is defensible because the string is terminal output —
but the win is deduplication, not polymorphism, and it should be described that way.

### What I would change

**Do — one real method.** `rules/parse_rule.py:386` is the one site that selects behaviour. The
question is *"does this version evidence rule out this document?"*, and `MissingRuleVersion` has a
clean identity answer: no evidence rules nothing out.

```python
# rules/parse_rule.py — beside the types, beside software_version_matches. No import moves.
@dataclass(frozen=True, slots=True)
class PresentRuleVersion:
    value: str

    def excludes(self, document_version: str) -> bool:
        return not software_version_matches(document_version, self.value)

    def label(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class MissingRuleVersion:
    """Rule construction has no software-version evidence."""

    def excludes(self, document_version: str) -> bool:
        return False                       # identity arm: no evidence excludes nothing

    def label(self) -> str:
        return "missing"
```

`ParseRuleBuilder.build` loses a compound condition:

```python
if self.version.excludes(document.software_version):
    continue
```

and `cli.py:351` / `cli.py:482` both become `version.label()`, killing that verbatim duplicate too.
`label()` is display text nobody branches on, so it is rendering, not laundering.

**Do — stop deriving `method` twice in `conversion.py`.** `converters/pipeline.py` already owns
`version_status(version)`, the sibling derivation for the other stored key. A
`rule_selection_method(version) -> RuleSelectionMethod` next to it, called from both places in
`conversion.py`, is consistent with what is already there and removes the duplicated ternary.

**Do not — move `version_status()` or `rule_selection_method()` onto the classes.** Those are
persistence vocabularies (`uns` key wording, `RuleSelection.method` wording). Putting them on the
types would make a `rules`-layer computation type know how three different consumers spell the same
distinction, which points knowledge the wrong way. Two label-producing methods on a two-member union
is already the ceiling.

### Otherwise `conversion.py` is fine

The duplication between `select_rule_from_parameters` and `select_rules_from_parameters` is **not** a
defect worth collapsing. The plural version hoists `_packaged_documents()` and
`resolve_rule_version()` out of the loop, and `_packaged_documents()` re-reads and re-validates every
packaged rule JSON per call — calling the singular function N times would be materially slower. That
is staging with a real reason, not a carpet. The `except RuleUnavailableError: continue` at lines
106-107 is control flow on what *happened* and is correct.

One naming note, since `conversion.py` calls it twice: `ParseRuleBuilder` (`rules/parse_rule.py:368`)
is not a Builder. It is a frozen dataclass with six required fields and one `build()` that filters
candidates and raises on 0 or >1 — no incremental construction, no stepwise interface, no director,
and no partially-set state. It is a **factory** whose parameters happen to be bundled as a record,
and the name sends a reader hunting for machinery that is not there. Cosmetic and not urgent, but it
is a claim about structure that the structure does not support.

---

## What the bounds rejected, with counts

A shortlist is only trustworthy if you can see what it threw away.

**Package-wide, before reading anything:** 132 foreign `isinstance` targets rejected under B1 (57 %
of all sites), leaving 99 owned-target candidates. 10 of those are in the two files under review.

**In `workflows/fasta.py`:**

| Rejected | Count | Bound |
| --- | --- | --- |
| `isinstance(inputs, PeptideLevelWithReportedProteinsInput)` in `_complete_level_validation:375` | 1 | **B2/B5 plus the blessed factory.** One consumer site, and the arms return *different types* — that is a factory turning `PeptideValidationInput` into `PeptideValidation`, which is the cure, not the smell. `PeptideLevelInput` has no reported proteins to give a method to. Correct as written. |
| `parameters.enzyme / min_peptide_length / max_peptide_length is not None` (426, 444, 458) | 3 | **B4 / the one question.** Asks what *happened* — the vendor was silent. Survives the remedy unchanged. |
| Shape checks in `calculate_feature_mapping_update` (343, 348) | 2 | **B4.** Field-to-field comparison, ordinary validation. |
| Set equality in `_peptide_feature_names` (398) | 1 | **B4.** Set equality polices values, not kinds. |
| Uniqueness in `_require_shared_is_uniprot` (411) | 1 | **B4.** Uniqueness check. |
| Validator messages of the "X is only valid when Y is Z" shape | **0** | Neither file has one. |
| Wide-parameter reads | **0** | Neither file appears among the script's 53 hits. |

**In `workflows/conversion.py`:** 2 candidates, both Finding B. Nothing rejected, nothing else
flagged.

---

## Two observations that are not skill findings

**1. The peptide-length defaults are declared three times, and one copy disagrees.**
`workflows/fasta.py:51-52` has `_DEFAULT_MIN_LENGTH = 7` / `_DEFAULT_MAX_LENGTH = 30`;
`fasta/annotation.py:128-129` has `FastaAnnotationConfig(min_length: int = 7, max_length: int = 30)`;
and `fasta/annotation.py:179-181` has `count_peptides(min_length: int = 6, max_length: int = 30)` —
**6, not 7**. The `FastaAnnotationConfig` default is dead on the protein-annotation path because
`resolve_protein_annotation_input` always supplies a value, and `count_peptides`'s `6` is reachable
only by direct callers. Not a live bug today, but three declarations of one number with one of them
different is the setup for one. Worth picking a single home.

**2. The trio's observability is inconsistent.** `_resolve_cleavage` logs a warning when it falls
back to trypsin; `_resolve_minimum_length` and `_resolve_maximum_length` silently substitute 7 and 30
with no log at all. Three functions written to the same template with different visibility is exactly
the drift that longhand repetition produces — and it is a decision worth making deliberately rather
than inheriting. (Note also that `resolve_cleavage_name` in `fasta/annotation.py` has its *own*
warn-then-fall-back-to-trypsin path for an unknown enzyme name, so the trypsin fallback is
implemented twice, in two modules, with two different messages.)

---

## One spillover, outside the files you named

The `PeptideValidation` union that `_complete_level_validation` correctly constructs is then
**re-discriminated twice, verbatim**, in `adapters/anndata/fasta.py:585-589` and `615-619`:

```python
leading_protein_field = (
    result.reported_protein_field
    if isinstance(result, PeptideLevelValidationWithReportedProteins)
    else None
)
```

That is the same case set appearing again past the factory, and it manufactures a `str | None` from a
union that was split precisely to avoid one. Two sites in one module, so weak on the bounds, and it
is in the adapter rather than in the two files you asked about — but it is the same shape as Finding
A and worth a look when you are next in that file.

## Bottom line

`conversion.py` is in good shape apart from one duplicated ternary and a misleading `Builder` name.
`fasta.py`'s structure is right and its trio is not: the three unions are correct modelling that
stopped one step short. Two moves — pass `Parameters` with an identity value instead of a fourth
union, and put `resolve()` on the selection types — remove 7 of 8 `isinstance` sites, three
functions, one union, and one duplicated namespace read, without adding a module, a wrapper, or a
factory. Then stop; the three short `resolve` bodies that remain are not a defect.
