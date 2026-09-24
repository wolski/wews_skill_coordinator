# Review: `workflows/fasta.py` and `workflows/conversion.py`

Read-only review. No code changed.

## Short answer

The design is sound. Both modules obey the typed-computation-boundary rule cleanly — no
AnnData/MuData imports, no `.X`/`.var`/`.uns` access, extraction lives in the adapter, and the
pure-computation tests in `tests/test_fasta_workflow.py` need no container fixture. That part is
working.

The `_resolve_cleavage` / `_resolve_minimum_length` / `_resolve_maximum_length` trio bothers you for
a specific, nameable reason, and it is not the reason it first looks like. It is **not** that the
three functions are near-copies of each other (they are, but that is a symptom). It is that
**twelve classes were created to remove a branch, and then none of them was given the behaviour, so
every branch is still there — just now with more type names around it.**

The finding is real but small: a clarity defect, not a correctness or extensibility risk. There is a
*stronger* instance of the same defect, in the same file's `PeptideValidation` union, that you did
not ask about. Details and a recommendation on what is worth doing follow.

---

## 1. Why the trio feels repetitive — the precise articulation

Here is the shape, stripped down:

```python
def _resolve_minimum_length(selection, search_parameters) -> int:
    if isinstance(selection, MinimumPeptideLength):          # ← what IS this selection?
        return selection.value
    if (isinstance(search_parameters, StoredProteinSearchParameters)   # ← what IS this state?
            and search_parameters.parameters.min_peptide_length is not None):  # ← what HAPPENED?
        return int(search_parameters.parameters.min_peptide_length)
    return _DEFAULT_MIN_LENGTH
```

Three different questions are being asked in one function, and only one of them belongs there.

The first two ask **what something is** — which variant of `MinimumLengthSelection` did the caller
build, and which variant of `ProteinSearchParameterState` did the adapter build. Deciding what to
*do* by asking what something *is* is a missing method on the type.

The third asks **what happened** — did this vendor's parameter file actually state a minimum peptide
length. That is ordinary control flow, it is correct, and it must stay. `Parameters` is a pydantic
storage schema describing what may appear in a vendor parameter file; `min_peptide_length: ... |
None` genuinely means "the file may not say", and no amount of polymorphism removes that fact.

So the compound `if` at lines 443-445 (and 425-427, and 457-459) is **half a defect and half correct
code fused into one condition**. Judging it as a unit gives the wrong answer whichever way you round
— which is, I think, exactly why it has resisted articulation. Your instinct that something is wrong
is right; your inability to name it comes from the fact that the sentence "this `if` is wrong" is
false.

### The tell, in your own prose

```python
@dataclass(frozen=True, slots=True)
class StoredCleavageOrTrypsin:
    """Use stored search enzyme, with a visible trypsin fallback."""


@dataclass(frozen=True, slots=True)
class StoredMinimumLengthOrDefault:
    """Use stored minimum peptide length, otherwise APB's default."""
```

Empty classes. No fields, no methods. And the docstring on each one is a **verb phrase describing
what to do** — "Use the stored enzyme, otherwise trypsin". That is the missing method announcing
itself in prose. The class says what it does; the code that does it lives 350 lines away in a
private function; nothing connects them but a name.

That is the repetition you are feeling. It is not three similar functions. It is **the same fact
written twice per parameter, in two places, in two languages** — once as English in a docstring, once
as Python in an `isinstance` arm.

### The evidence, counted

I checked every `Stored…`-vs-explicit selection union in the package:

| Union | Module | Classes | Methods on them |
| --- | --- | --- | --- |
| `CleavageSelection` | `workflows/fasta.py` | 3 | **0** |
| `MinimumLengthSelection` | `workflows/fasta.py` | 2 | **0** |
| `MaximumLengthSelection` | `workflows/fasta.py` | 2 | **0** |
| `ProteinSearchParameterState` | `workflows/fasta.py` | 2 | **0** |
| `FastaAccessionsSelection` | `adapters/anndata/fasta.py` | 3 | **0** |
| `ReportedProteinsSelection` | `adapters/anndata/fasta.py` | 2 | **0** |

Fourteen classes across six unions, zero methods on any of them. The trio is not an anomaly — it is
the house idiom, applied consistently, and the idiom has one systematic weakness: **it splits the
type and stops.** Splitting a union without moving behaviour onto the members leaves every consumer
exactly where it started, asking "which one is it?", only now with `isinstance` instead of `is None`.

`ProteinSearchParameterState` is branched on in three separate functions (lines 425, 443, 457) with a
character-for-character identical first conjunct. That is the objective, countable part of the
finding.

### Honest bounding — how big is this really?

I want to be straight about the strength of the evidence, because the fix is cheap but so is
over-reacting to it:

- Taken individually, each of `CleavageSelection`, `MinimumLengthSelection` and
  `MaximumLengthSelection` is discriminated in **exactly one place**. A union discriminated once is
  weak evidence on its own — a lot of perfectly good small result types look like that.
- `ProteinSearchParameterState` is discriminated three times, but all three are in the same module.
  Same-module repetition is weaker evidence than the same case set escaping into a second module.
- The case set will almost certainly never grow. There are three digestion parameters, there have
  been three for as long as the module has existed, and a fourth is not on any roadmap I can see.

So: **this is a readability and single-point-of-truth finding, not an extensibility risk.** If you
never touch it, nothing will break. The reason to fix it is that the current shape makes the
correct part (`is not None` — "the vendor didn't say") and the incorrect part (`isinstance` — "which
variant is this") indistinguishable at a glance, which is precisely the confusion you reported.

---

## 2. What I would do instead

Two moves. The first is the one that matters; the second is what stops the branch from merely
relocating.

### Move 1 — put the behaviour on the selection types

The question every arm answers has a name: *"what cleavage rule should the digest use?"*,
*"what minimum peptide length should the digest use?"*. That name is the method name.

```python
@dataclass(frozen=True, slots=True)
class NamedCleavage:
    enzyme: str
    def resolve(self, stored: ProteinSearchParameterState) -> ResolvedCleavage:
        return resolve_cleavage_name(self.enzyme)


@dataclass(frozen=True, slots=True)
class CustomCleavage:
    rule: CleavageRule
    def resolve(self, stored: ProteinSearchParameterState) -> ResolvedCleavage:
        return custom_cleavage(self.rule)


@dataclass(frozen=True, slots=True)
class StoredCleavageOrTrypsin:
    """Use stored search enzyme, with a visible trypsin fallback."""
    def resolve(self, stored: ProteinSearchParameterState) -> ResolvedCleavage:
        enzyme = stored.stated_enzyme()
        if enzyme is None:                       # ← "the vendor didn't say" — correct, stays
            logger.warning(
                "no enzyme in search parameters and no cleavage override; "
                "using Trypsin for the peptide count"
            )
            return DEFAULT_CLEAVAGE
        return resolve_cleavage_name(enzyme)
```

The docstring on `StoredCleavageOrTrypsin` now sits directly above the code that implements it. That
is the whole point of the change.

`resolve_protein_annotation_input` becomes:

```python
cleavage = inputs.cleavage.resolve(inputs.search_parameters)
minimum = inputs.minimum_length.resolve(inputs.search_parameters)
maximum = inputs.maximum_length.resolve(inputs.search_parameters)
```

and the three private `_resolve_*` functions are deleted.

Note that two of the three arms ignore the `stored` argument. That is normal and not a smell — an
explicit override does not consult the vendor's file, by definition.

### Move 2 — give the absent parameter state an identity value

Move 1 alone would leave `isinstance(stored, StoredProteinSearchParameters)` inside the three
`Stored…OrDefault.resolve` bodies. The branch would have moved, not disappeared. The fix is to make
the two members of `ProteinSearchParameterState` answer the "what did the search state" question
uniformly:

```python
@dataclass(frozen=True, slots=True)
class StoredProteinSearchParameters:
    parameters: Parameters
    def stated_enzyme(self) -> str | None:
        return self.parameters.enzyme
    def stated_minimum_length(self) -> int | None:
        return self.parameters.min_peptide_length
    def stated_maximum_length(self) -> int | None:
        return self.parameters.max_peptide_length


@dataclass(frozen=True, slots=True)
class MissingProteinSearchParameters:
    """The protein container has no stored search parameters."""
    def stated_enzyme(self) -> str | None:
        return None
    def stated_minimum_length(self) -> int | None:
        return None
    def stated_maximum_length(self) -> int | None:
        return None
```

The `| None` here is not new sum-typing sneaking back in — it is the pydantic schema's own optionality
being forwarded verbatim. `Parameters` describes a file, the file may omit a field, and that is
correct and stays. What disappears is the *second*, redundant absent-case: "there is no parameter
block at all" and "there is a block that doesn't state this field" are two spellings of one outcome,
and Move 2 makes them one.

After both moves, every `isinstance` in the digestion path is gone and exactly one `if … is None`
survives per parameter — the one that was always correct.

### The more aggressive option, and why I would not take it

You could delete `ProteinSearchParameterState` entirely and have the adapter hand over `Parameters()`
(all fields `None`, which I verified constructs cleanly) when the container has no stored block. That
collapses the union to nothing and removes six methods.

I would not do it. It erases a real distinction — "no parameter file was ever parsed" versus "a
parameter file was parsed and said nothing about the enzyme" — that you may want for provenance later.
Nothing in `workflows/fasta.py` uses that distinction today, but throwing away a fact you already have
is harder to undo than keeping six three-line methods. Mentioning it for completeness; the recommendation
is Moves 1 and 2.

---

## 3. The one I would fix first, which you did not ask about

By the same test, the strongest instance in this file is not the trio. It is `PeptideValidation`.

`_complete_level_validation` (line 370) is a **correct** factory — a single dispatch point producing
one of two types is exactly right, and I would leave it alone. But the union it produces then gets
re-discriminated downstream, in a different module:

```
adapters/anndata/fasta.py:585-588      adapters/anndata/fasta.py:615-618
    leading_protein_field = (              leading_protein_field = (
        result.reported_protein_field           result.reported_protein_field
        if isinstance(result, PeptideLevelValidationWithReportedProteins)
        else None                              else None
    )                                      )
```

Two sites, byte-identical expression, in a module that is not the one that owns the union. That is a
case set escaping past its factory — the pattern the trio only hints at. The fix is four lines:

```python
class PeptideLevelValidation:
    def leading_protein_field(self) -> str | None:
        return None

class PeptideLevelValidationWithReportedProteins:
    reported_protein_field: str
    def leading_protein_field(self) -> str | None:
        return self.reported_protein_field
```

Both adapter sites become `result.leading_protein_field()`. Two branches deleted, no new types, and
the layering direction is unchanged (the adapter already imports from `workflows`). If you only do
one thing from this review, do this one — it is smaller than the trio fix and the evidence for it is
stronger.

---

## 4. What is *not* a problem — please don't refactor these

Several things in these two files look like the same pattern and are not. Flagging them explicitly so
a future pass doesn't "fix" them.

**`conversion.py` line 82 and 108 — the `method` string.** This looks like the classic
"function turns a mode into a string that another function branches on":

```python
method = "software_version" if isinstance(version, PresentRuleVersion) else "columns"
```

I grepped for anything comparing against those literals. **Nothing does.** The value is a typed
`Literal` that gets written straight through to `uns["anndata_proteomics"]["rule_selection_method"]`
as provenance and read back for the description record. It is a **label, not a discriminator** — the
string names something for a human reading the output file, and no control flow depends on it.
Verdict: not a design defect. It *is* two lines of literal duplication between
`select_rule_from_parameters` and `select_rules_from_parameters`, worth a shared one-liner if you're
in there anyway, but nothing more. (Side note: the third `Literal` member, `"rule_config"`, is
produced only in tests and by the CLI's explicit-rule path — that is intentional, not a gap.)

**`select_rule_from_parameters` vs `select_rules_from_parameters`.** Near-identical bodies, but they
differ in a way that matters: the singular *must* raise `RuleUnavailableError` for the level you
asked for, the plural *must* swallow it and skip. That is a genuine behavioural difference, not a
missing parameter, and collapsing them into one function with a flag would be a step backwards. Leave
them.

**`calculate_feature_mapping_update`'s two shape checks**, `_require_shared_is_uniprot`, and
`_peptide_feature_names`' set-equality check. These are validators policing *values* — shape
mismatch, disagreement, name-set mismatch. They ask what happened, not what something is. All
correct, all should stay exactly as they are.

**`_complete_level_validation` itself.** Single dispatch point at a factory, producing two different
result types. Correct. (Its *output* is the problem — see §3 — not the dispatch.)

---

## 5. Two small concrete things while you're in there

**a) The default peptide lengths exist in three places, with two different values.**

| Location | min | max |
| --- | --- | --- |
| `workflows/fasta.py:51-52` (`_DEFAULT_MIN_LENGTH`/`_DEFAULT_MAX_LENGTH`) | 7 | 30 |
| `fasta/annotation.py:128-129` (`FastaAnnotationConfig` field defaults) | 7 | 30 |
| `fasta/annotation.py:180-181` (`count_peptides` keyword defaults) | **6** | 30 |

The production path always passes explicit values (`fasta/annotation.py:304-308` threads `config`
through), so the `6` is only reachable by calling `count_peptides` directly — which the tests do.
It is not currently a bug, but it is a bug waiting for someone to call `count_peptides` without a
`min_length`. I would give `count_peptides` no default at all, or point all three at one constant.

**b) `_packaged_documents()` re-reads and re-parses every packaged rule document on each call to
`select_rule_from_parameters`.** `select_rules_from_parameters` correctly hoists it out of the level
loop; the singular does not hoist because it has no loop — but `convert_level_from_parameters` calls
the singular, so a caller converting several levels one at a time pays the full document load each
time. Currently the CLI calls it once per invocation, so this is latent, not live. Worth knowing
before someone loops it.

---

## Recommendation

In priority order:

1. **`PeptideValidation.leading_protein_field()`** (§3) — four lines, deletes two duplicated branches
   in the adapter, strongest evidence of the three findings.
2. **The `count_peptides` default of 6** (§5a) — one line, removes a latent inconsistency.
3. **The trio** (§2, Moves 1 and 2) — about 40 lines moved, deletes three private functions and six
   `isinstance` checks. Do it because it makes the correct `is None` checks visibly correct, not
   because the current code is fragile. It isn't.

And a general note, since the idiom shows up six times: when you split a union into named cases, the
split is only half the work. **If nothing gets a method, every caller is still asking "which one is
it?" and you have paid for the types without collecting on them.** That is the single sentence behind
everything above.
