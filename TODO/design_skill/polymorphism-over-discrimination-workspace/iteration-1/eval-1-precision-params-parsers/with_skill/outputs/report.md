# Is the `isinstance` count in `params/` a code smell?

## Straight answer

**No — not on the evidence he is citing.** The `isinstance` count in `params/model.py` is not a smell;
it is what a vendor-file parse boundary looks like. Of the 32 `isinstance` calls in that file, **24
narrow foreign types** (`str`, `dict`, `list`, `int`, `float`, `bool`, `BaseModel`) inside pydantic
`mode="before"` validators. You cannot put a method on `str`, so those branches are correct code and
there is no polymorphic remedy to offer. Refactoring `model.py` to "polymorphism" would make it worse.

**But he is accidentally right about two specific things**, neither of which is in `model.py` and
neither of which is about the count:

1. **The Unimod lookup-result union is discriminated in three modules and has no method.** This is
   the one finding that clears every bound cleanly. Fix it.
2. **`params/parsers/fragpipe.py` split three unions and never put the behaviour on them.** All four
   remaining `isinstance` sites there project variants onto an optional-field `TypedDict` that exists
   only because the projection is done by asking types what they are.

So: one real cross-module finding, one real single-module cleanup, and ~62 of the 71 `isinstance`
calls in `params/` that should be left exactly as they are. The correct response to your colleague is
"which ones?", not "how many?".

---

## The measurement

Run mechanically over `apb/src/anndata_proteomics/params/`, then over the whole package so the
`isinstance` targets defined outside `params/` (e.g. `UnimodMatch`) are counted as owned:

| | count |
| --- | --- |
| `isinstance` calls in `params/` (16 modules) | **71** |
| → target a type the package does **not** define — no method can be added | **47 (66 %)** |
| → target a type the package **does** define | **24** |
| of those 24: `parse(value: object)` idempotency guards at the vendor boundary | 4 |
| of those 24: single-site branches below the reporting threshold | 6 |
| of those 24: **participate in a reportable finding** | **14** |

`model.py` specifically: 32 `isinstance` calls (his "29" is close; it is 32 today), of which **8**
target owned types, and **exactly one** of those 8 belongs to a finding — and the remedy for that one
lives in `modifications/unimod_registry.py`, not in `model.py`. `model.py` needs no restructuring.

Also worth knowing before you take his advice: **`params/parsers/maxquant.py` has 13 `isinstance`
calls and every single one is foreign** (`dict`, `list`, `str`, `pd.Series`,
`collections.abc.MutableMapping`) — it walks a parsed XML/mqpar structure. It is the second-highest
count in the directory and contains zero findings. A count-driven refactor would have started there.

---

## Finding 1 — the Unimod lookup result (evidence; act on this)

**Shape 4** (a union already split, whose consumers still discriminate), plus **shape 2** (the same
case set branched on in more than one function).

**Bounds cleared:** B1 — `UnimodMatch` / `UnrecognizedUnimodName` / `UnrecognizedUnimodMass` are
plain frozen dataclasses defined in `apb/src/anndata_proteomics/modifications/unimod_registry.py:42-60`,
so a method can go on them. B2 — **3 consumer sites across 3 modules**, which is the threshold the
bound actually asks for.

Sites, all asking the same question and answering it the same way:

- `apb/src/anndata_proteomics/params/parsers/sage.py:25`
- `apb/src/anndata_proteomics/params/parsers/fragpipe.py:190`
- `apb/src/anndata_proteomics/params/model.py:522`

```python
# sage.py:22-27
result = unimod_registry.find_by_mass(mass, tolerance=MASS_TOLERANCE)
if isinstance(result, unimod_registry.UnimodMatch):
    return result.entry.name
return str(mass)                     # fallback differs per caller; the branch does not
```

**Gate 1 (name the question every arm answers):** *"which display name does this modification
carry?"* Nameable in one sentence, so the finding survives.
**Gate 2 (is it a storage schema?):** No. These are runtime result types living beside the lookup
functions that produce them. The method goes straight on them — no factory, no second type, no
layering question.

**Remedy** — in `unimod_registry.py`, on all three classes:

```python
@dataclass(frozen=True)
class UnimodMatch:
    entry: UnimodEntry
    def display_name(self, fallback: str) -> str:
        return self.entry.name

@dataclass(frozen=True)
class UnrecognizedUnimodName:
    name: str
    def display_name(self, fallback: str) -> str:
        return fallback                       # identity arm

@dataclass(frozen=True)
class UnrecognizedUnimodMass:
    mass_delta: float
    def display_name(self, fallback: str) -> str:
        return fallback                       # identity arm
```

Every call site collapses to one line with no branch:

```python
# sage.py
return unimod_registry.find_by_mass(mass, tolerance=MASS_TOLERANCE).display_name(str(mass))

# fragpipe.py:187-195 — the second lookup becomes the fallback, and the chain reads in order
canonical = unimod_registry.find_by_mass(mass, tolerance=_MASS_TOLERANCE)
vendor = lookup_mass_mod(mass, _VENDOR_MASS_TO_MOD, tol=_MASS_TOLERANCE)
return canonical.display_name(vendor.display_name(source_token.strip()))

# model.py:517-535 — no `isinstance`; the token-shaped fallback stays a token
```

`lookup_mass_mod`'s own pair (`MassModificationMatch` / `UnrecognizedModificationMass` in
`params/parsers/_common.py:13-24`) is the same union shape and gets the same method, which is what
makes the `fragpipe.py` line above read as a plain fallback chain.

**One site deliberately stays:** `model.py:547`, inside `_find_modification`. That branch asks *did
the name lookup fail, so should I try a mass lookup?* — it selects a **search strategy**, not a
behaviour of the result, and inventing an `or_lookup_by_mass()` method to remove it would be a method
no caller wants. Leave it.

---

## Finding 2 — `params/parsers/fragpipe.py` split three unions and stopped (judgement on the bound; evidence on the shape)

**Shape 4 and shape 6.** The types are already there. The factories are already there
(`_workflow_identification`, `_workflow_quantification`, `_workflow_charge_range`,
`fragpipe.py:458-492`). Step 4 of the remedy — *put the method on each class* — was never done, so the
callers still discriminate. That is textbook shape 4, and the candidate scan flags
`NoQuantification` (`fragpipe.py:109`) as an identity type with **no methods** and 3 consumer sites.

**Bound honesty:** B1 clears (all types defined in that file). **B2 is marginal** — 8 owned sites,
but all in one module, and the skill's reporting threshold is two modules. So I am reporting this as a
judgement call, not as evidence, and here is the justification I would accept from someone else:

- `WorkflowVersionEvidence` is discriminated at **four** sites (`530`, `556`, `561`, `567`), three of
  which are the *identical expression* `x.value if isinstance(x, WorkflowVersion) else None`.
- `FragPipeVariantData` (`fragpipe.py:151-159`) is a `TypedDict(total=False)` whose docstring says
  *"Fields whose presence depends on tagged workflow stages."* That is a 6-field record with 2^6
  possible shapes, and it exists **only** because the projection is done by discrimination. Remove
  the discrimination and the optional-field record has no reason to exist.
- The clearest tell that the polymorphism is missing: `_add_variant_parameter_data` **fabricates an
  instance of the other variant to reuse a function** —

```python
# fragpipe.py:503-517, condensed
data["max_precursor_mz"] = _maximum_precursor_mz(
    digest_mass_range,
    LowerBoundedChargeRange(minimum=charge_range.minimum),   # downcast to reach the helper
).maximum
...
if isinstance(charge_range, BoundedChargeRange):
    precursor_mz = _precursor_mz_range(digest_mass_range, charge_range)
    data["max_precursor_charge"] = charge_range.maximum
    data["min_precursor_mz"] = precursor_mz.minimum
    data["max_precursor_mz"] = precursor_mz.maximum          # written a second time
```

`max_precursor_mz` is written twice. It is not a bug — both formulas reduce to
`digest_mass.maximum / charge.minimum` — but a reader has to verify that by hand, and the first write
only type-checks because a `BoundedChargeRange` was rebuilt as the *other* member of its own union.
Note also that the two free functions `_precursor_mz_range` and `_maximum_precursor_mz`
(`fragpipe.py:423-439`) are exactly the two shape-7 hits the scan reports for this directory: a
function takes a whole `DigestMassRange` + charge record because the operation is the charge type's
behaviour and has nowhere to live.

**Gate 1:** *"which parameter fields does this workflow stage declare?"* Nameable.
**Gate 2:** These are frozen dataclasses in the parser module, not a persistence schema — the method
goes on them directly.

**Remedy** — one method per class, identity arms included:

```python
@dataclass(frozen=True, slots=True)
class DiannIdentificationFdrs:
    psm: float
    protein: float
    def variant_fields(self) -> FragPipeVariantData:
        return {}                                             # DIA-NN reports no peptide FDR

@dataclass(frozen=True, slots=True)
class PhiReportIdentificationFdrs:
    psm: float
    peptide: float
    protein: float
    def variant_fields(self) -> FragPipeVariantData:
        return {"ident_fdr_peptide": self.peptide}

@dataclass(frozen=True, slots=True)
class LabelFreeQuantification:
    match_between_runs: bool
    def variant_fields(self) -> FragPipeVariantData:
        return {"enable_match_between_runs": self.match_between_runs}

@dataclass(frozen=True, slots=True)
class DiannQuantification:
    match_between_runs: bool
    method: str
    def variant_fields(self) -> FragPipeVariantData:
        return {
            "enable_match_between_runs": self.match_between_runs,
            "quantification_method": self.method,
        }

@dataclass(frozen=True, slots=True)
class NoQuantification:
    def variant_fields(self) -> FragPipeVariantData:
        return {}                                             # the method the split never got

@dataclass(frozen=True, slots=True)
class BoundedChargeRange:
    minimum: int
    maximum: int
    def variant_fields(self, digest_mass: DigestMassRange) -> FragPipeVariantData:
        return {
            "max_precursor_charge": self.maximum,
            "min_precursor_mz": digest_mass.minimum / self.maximum,
            "max_precursor_mz": digest_mass.maximum / self.minimum,
        }

@dataclass(frozen=True, slots=True)
class LowerBoundedChargeRange:
    minimum: int
    def variant_fields(self, digest_mass: DigestMassRange) -> FragPipeVariantData:
        return {"max_precursor_mz": digest_mass.maximum / self.minimum}
```

and, for the version union (this is the 3x repeated expression, gone):

```python
@dataclass(frozen=True, slots=True)
class WorkflowVersion:
    value: str
    def declared_version(self) -> str | None:
        return self.value

@dataclass(frozen=True, slots=True)
class WorkflowVersionUnavailable:
    def declared_version(self) -> str | None:
        return None
```

`_add_variant_parameter_data` then disappears entirely — `extract_params` composes the fragments:

```python
parameter_data: FragPipeParameterData = {
    ...
    "software_version": (
        workflow.fragpipe_version.declared_version()
        or _legacy_fragpipe_version(workflow.header).declared_version()   # 530 collapses too
    ),
    "search_engine_version": workflow.msfragger_version.declared_version(),
    "quantification_software_version": (
        workflow.diann_version.declared_version() if uses_diann else None
    ),
    **fdrs.variant_fields(),
    **quantification.variant_fields(),
    **charge_range.variant_fields(digest_mass_range),
}
```

All eight owned `isinstance` sites in the module go to zero; `max_precursor_mz` is written once by
whichever charge type owns the answer; `_precursor_mz_range` and `_maximum_precursor_mz` fold into the
methods. `if uses_diann` stays and is correct — it asks *what happened* (did this workflow run
DIA-NN), not *what something is*.

Note `-> str | None` on `declared_version()` is not a reintroduced discriminator: `Parameters`
declares those fields as `str | None`, so the method returns the **result**, not a token naming an
operation. Do not add an `evidence_kind() -> str` accessor anywhere near this.

---

## What the bounds rejected — and why each "no" is a real no

This is the part to show your colleague, because it is where the count comes from.

| Rejected | Count | Bound | Why |
| --- | --- | --- | --- |
| Foreign `isinstance` targets in `params/` | **47** | B1 | `str`/`dict`/`list`/`int`/`float`/`bool`/`pd.Series`/`BaseModel` — no method can be added. All inside `mode="before"` validators or file/JSON walkers. |
| `parse(value: object)` idempotency guards | 4 | B1 | `model.py:114, 161, 371, 510`. `Probability.parse` / `MassTolerance.parse` / `_modification_from_item` take `object` straight from a vendor file. The foreign value is *at* that boundary; narrowing it there is the boundary's job. |
| `MassTolerance` mode validator | 2 messages | Gate 1 + Gate 2 | See below — this is the one that looks most like his case and is not. |
| `_legacy_value` type dispatch | 2 | B2/B5 | `model.py:442-446`, one site, one module, two arms serialising to a CSV cell. If a third typed field lands in `Parameters`, that is when to add `legacy_value()` per type. Not before. |
| `metamorpheus._load_pair` | 4 calls | single dispatch point | `metamorpheus.py:153-161`. `_try_load` classifies each file (correct — it is the factory); `_load_pair` then puts the pair in canonical order. Both arms perform the *same* operation and the `raise` is the "neither combination" case. A dispatch at the factory is the cure, not the defect. |
| `diann._append_unimod` version check | 1 | B2/B5 | `diann.py:217`. One site, and it asks whether version evidence exists at all before deciding it cannot classify the flag. Absence → *what happened*. |
| `record.value is not None` | 1 | B4 | `fragpipe.py:449`, a comprehension filter. Emptiness/absence, not kind. |
| `_validate_order` in `model.py` | — | B4 | `min > max` compares a field to another **field**. Value validation, not a discriminator. |

### The one that looks like his case: `MassTolerance` (`model.py:126-154`)

If your colleague had pointed here, he would have had a much better argument, and he would still have
been wrong *today*. The shape is the classic tell — a `mode: Literal["absolute", "automatic"]`
discriminator plus three fields that belong to only one mode, policed from outside by a validator that
rejects combinations:

```python
if self.mode == "absolute":
    if self.value is None: raise ValueError("absolute tolerance requires value")
    if self.unit is None:  raise ValueError("absolute tolerance requires unit")
else:
    if self.unit is not None:  raise ValueError("automatic tolerance cannot define unit")
    if self.value is not None: raise ValueError("automatic tolerance cannot define numeric bounds")
```

Two gates kill it:

- **Gate 1 — name the method each split type would implement.** I cannot, and I checked rather than
  assumed: `grep` over the whole package finds **no consumer anywhere that branches on
  `MassTolerance.mode`**. The only reader of `mode` is that validator. `label` is only ever *written*.
  Nothing computes with a tolerance — it is parsed, stored, and serialised. Splitting into
  `AbsoluteTolerance` / `AutomaticCalibration` would buy a second name and no behaviour, which is
  inventing a method to justify a split.
- **Gate 2 — it is a persistence schema.** `MassTolerance` round-trips through
  `Parameters.to_series()` / `from_series()` to a ProteoBench CSV and through `model_dump(mode="json")`
  into the APB namespace. A combination-rejecting validator on a document schema is **correct and
  stays** — someone can write that combination into a file and must be told.

**When to revisit:** the moment anything needs to *do* something with a tolerance — convert ppm to Da
at a given m/z, widen a search window, compare two vendors' tolerances. That operation is the method,
and it arrives with a real caller. Split it then, as a runtime type plus a factory, and leave the
pydantic validator where it is.

---

## What I would actually tell him

- "29 `isinstance` calls" is not evidence of anything. In `params/` **66 %** of them narrow types the
  package does not define, and the file with the second-highest count (`maxquant.py`, 13) contains
  zero findings. The metric would have sent you to the wrong file.
- The defect worth naming is not `isinstance` — it is **splitting a union and not moving behaviour
  onto it**. `params/` did the modelling well (`WorkflowVersion`/`WorkflowVersionUnavailable`,
  `NoQuantification`, `UnimodMatch`/`Unrecognized...`, `MissingDiannVersion`) and then left the callers
  asking which member they got. Nothing in the "replace `| None` with a named absent case" discipline
  makes anyone add the method, which is why this is the most common finding in the package: **18
  identity types, 0 of them with a method.**
- Do Finding 1 (3 modules, ~15 lines, no architecture). Do Finding 2 if you are touching FragPipe
  anyway — it deletes a function, an optional-field `TypedDict`, and a double write. Change nothing
  in `model.py`.

## Files referenced

- `/Users/wolski/projects/anndata_bridge/apb/src/anndata_proteomics/params/model.py`
- `/Users/wolski/projects/anndata_bridge/apb/src/anndata_proteomics/params/parsers/fragpipe.py`
- `/Users/wolski/projects/anndata_bridge/apb/src/anndata_proteomics/params/parsers/sage.py`
- `/Users/wolski/projects/anndata_bridge/apb/src/anndata_proteomics/params/parsers/_common.py`
- `/Users/wolski/projects/anndata_bridge/apb/src/anndata_proteomics/params/parsers/metamorpheus.py`
- `/Users/wolski/projects/anndata_bridge/apb/src/anndata_proteomics/params/parsers/diann.py`
- `/Users/wolski/projects/anndata_bridge/apb/src/anndata_proteomics/params/parsers/maxquant.py`
- `/Users/wolski/projects/anndata_bridge/apb/src/anndata_proteomics/modifications/unimod_registry.py`

No files under `apb/` were modified; this was a read-only review.
