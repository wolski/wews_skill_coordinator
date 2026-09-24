# Are the `isinstance` calls in `params/` a code smell?

**Short answer: no, your colleague is wrong about this code — but he is right about the principle, and there is one small thing in `params/parsers/fragpipe.py` worth fixing. It is not an `isinstance` chain.**

The `isinstance` count is not measuring what he thinks it measures. Of the 71 `isinstance` calls in
`apb/src/anndata_proteomics/params/`, 51 narrow types you did not write (`str`, `dict`, `list`,
`int`, `float`, `bool`, `Path`, `bytes`, `pd.Series`, `BaseModel`). You cannot put a method on
`dict`. Those are parse-boundary narrowing, which is correct Python, and they are 71 % of the total
before any judgement is applied.

Of the 20 that survive, 19 fail on grounds that have nothing to do with taste — they are each
discriminated in exactly one function, so there is no duplicated case set to remove.

Counts, by file:

| File | `isinstance` calls | Narrow a type you own | Survive review |
| --- | --- | --- | --- |
| `params/model.py` | 32 | 6 | 0 |
| `params/parsers/fragpipe.py` | 10 | 9 | 0 (see the `uses_diann` finding below) |
| `params/parsers/metamorpheus.py` | 4 | 4 | 0 |
| `params/parsers/diann.py` | 7 | 1 | 0 |
| `params/parsers/maxquant.py` | 13 | 0 | 0 |
| everything else in `params/` | 5 | 0 | 0 |

(Your "29 in `model.py`" is 32 by AST count. Doesn't change anything.)

---

## `model.py`: six candidates, zero findings

Four of the six sit inside a `parse(value: object)` classmethod or a pydantic `mode="before"`
validator:

- `model.py:114` — `Probability.parse`
- `model.py:161` — `MassTolerance.parse`
- `model.py:371` — `Parameters._coerce_modifications`
- `model.py:510` — `_modification_from_item`

The thing being dispatched on in all four is typed `object`. It arrives from a vendor file, a CSV
cell, or a `.uns` payload. There is no type to hang a method on, because the whole point of the
function is that you do not yet know what you have. `if isinstance(value, MassTolerance): return
value` is an idempotency short-circuit on an untyped input, not a behaviour switch. This is the
correct shape for a decoder and changing it would make the code worse.

The remaining two are `Parameters._legacy_value` (`model.py:442`, `:444`), which asks whether a
field's value is a `Probability` or a `MassTolerance` on the way to a ProteoBench CSV cell. That one
is genuinely dispatching on your own types — but it is two arms, in one function, in one module, and
`Probability` and `MassTolerance` are the only two non-scalar field types `Parameters` has. Nothing
to gain.

### The one that looks worst, and why it still isn't a finding

If your colleague had pointed at `MassTolerance._validate_shape` (`model.py:142-154`) instead of
counting `isinstance`, he would have picked the textbook example:

```python
value: NonNegativeFloat | None = None
unit:  ToleranceUnit | None = None
mode:  ToleranceMode                  # Literal["absolute", "automatic"]
label: str | None = None

@model_validator(mode="after")
def _validate_shape(self) -> MassTolerance:
    if self.mode == "absolute":
        if self.value is None: raise ValueError("absolute tolerance requires value")
        if self.unit  is None: raise ValueError("absolute tolerance requires unit")
    else:
        if self.unit  is not None: raise ValueError("automatic tolerance cannot define unit")
        if self.value is not None: raise ValueError("automatic tolerance cannot define numeric bounds")
```

`mode` is a kind tag. `value` + `unit` are the `"absolute"` payload. `label` is the `"automatic"`
payload. A validator exists purely to reject the combinations the type allows but reality doesn't.
On paper this is exactly the "split into `AbsoluteTolerance | AutomaticTolerance`" case.

It still fails, on two independent grounds:

1. **Nothing computes on it.** I checked every read of `.mode`, `.value`, `.unit`, and `.label`
   across `src/`. Producers construct tolerances (`alphadia.py:104-105`, `alphapept.py:98`,
   `fragpipe.py:372`, `metamorpheus.py:109`); `_legacy_value` dumps the whole model without looking
   inside. **No non-test code branches on `mode`.** The only reads of those fields in the repository
   are assertions in `tests/`. So there is no method to move onto the split types — you would get two
   record shapes with no behaviour between them, which is a schema, not a polymorphism. Splitting
   buys a second name and nothing else.

2. **It is a persistence schema.** `MassTolerance` round-trips through the ProteoBench CSV and lands
   in AnnData `.uns`. Someone can write `{"mode": "automatic", "unit": "ppm"}` into a stored payload
   and must be told it is nonsense. A combination-rejecting validator on a document schema is
   correct and stays. Splitting it would ripple through the persisted `.uns` shape and the CSV
   round-trip for no behavioural gain.

**Revisit this if that changes.** The moment something needs to *do* different work for automatic vs
absolute — format a display string, widen a search window, compare two tolerances — this becomes a
real finding and the split is right. Today the validator is doing its job.

---

## The one thing actually worth fixing: `uses_diann` in `fragpipe.py`

Not an `isinstance` problem. A boolean:

```
fragpipe.py:540   uses_diann = values["diann.run-dia-nn"] == "true"
fragpipe.py:541   fdrs = _workflow_identification(values, uses_diann)           # branches on it
fragpipe.py:542   quantification = _workflow_quantification(values, uses_diann) # branches on it
fragpipe.py:558   "quantification_software": "DIA-NN" if uses_diann else None
fragpipe.py:561   if uses_diann and isinstance(workflow.diann_version, WorkflowVersion)
```

Four places re-answering one question: *is this a DIA-NN-backed FragPipe workflow, or a
Philosopher/IonQuant one?* That is the same case set decided in more than one function, which is the
strongest objective evidence there is — and it is the pattern `AGENTS.md` names directly ("do not use
boolean switches to make one function select among different behaviors").

It is also nameable, which is the test that matters. Each arm answers "what did this workflow's
identification and quantification stages do?" Two types (`DiannWorkflow`, `PhilosopherWorkflow`),
each with `identification_fdrs()`, `quantification()`, and `quantification_software()`, and the flag
plus all four branches disappear.

**Bound on this:** it is one module, one vendor, four sites, and FragPipe workflows are realistically
DIA-NN or not-DIA-NN forever. Call it optional cleanup on the next occasion someone is in that file.
It does not justify a refactor of its own.

### While you're there: `_add_variant_parameter_data`

`fragpipe.py:495-517` is the densest `isinstance` cluster in the directory — four branches over four
unions the code has already split (`DiannIdentificationFdrs | PhiReportIdentificationFdrs`,
`LabelFreeQuantification | DiannQuantification | NoQuantification`, `BoundedChargeRange |
LowerBoundedChargeRange`, `WorkflowVersion | WorkflowVersionUnavailable`).

By count it looks like the worst code in `params/`. It isn't, because every one of those unions is
discriminated in exactly that one function — there is no scattered case set. But it does show the
half-finished move: the types got split and no behaviour moved onto them, so the caller is still
asking "which one is it". If the `uses_diann` cleanup above happens, giving each variant a
`parameter_fields() -> FragPipeVariantData` is the natural companion, and it removes an existing
redundancy for free: `max_precursor_mz` is written at line 503 and overwritten at line 517 with the
same value whenever the charge range is bounded.

---

## What the code already gets right

The largest case set in the whole subsystem — 12 vendor labels — is a `dict[str, ParseFn]` in
`params/registry.py:98-111` with a single lookup in `get_parser`. I grepped for vendor-name
comparisons anywhere downstream of that lookup: **zero hits.** The case set is decided once and never
reappears.

That is precisely the refactoring your colleague is asking for, already done, at the level where it
pays. A single dispatch point at a factory is the cure, not the smell — the smell is the same case
set showing up *again* past that lookup, and it doesn't.

Same story at `metamorpheus.py:164` (`_try_load` classifies each file once at the boundary;
`_load_pair` just sorts the pair into a known order) and `diann.py:217` (`MissingDiannVersion`,
discriminated in exactly one place in the entire package).

---

## Bottom line

`params/model.py` and `params/parsers/` are boundary code. Their job is turning vendor text, TOML,
JSON, and CSV cells into typed values, and `isinstance` density is what that job looks like when it
is done correctly. The `isinstance` count is a proxy for "how many foreign formats does this
subsystem eat", not for design quality.

Tell your colleague: the principle is right and it is in `AGENTS.md` for a reason, but the metric he
used doesn't select for it. 71 % of the hits are unactionable by construction, and the one real
instance in this directory is a `bool`, which his grep would never have found.

**If he wants a target for this, `params/` is the wrong directory.** Elsewhere in the package there
are 19 `Missing*` / `No*` / `Non*` identity types and none of them carries a method —
`MissingNamespaceText` alone is discriminated in four different modules under `adapters/anndata/`,
and `description.py` has six more. That is the same case set decided in several places, which is the
thing worth removing. I have not reviewed those in depth; flagging them as where the effort would
actually pay.
