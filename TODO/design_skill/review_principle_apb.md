# APB reviewed against the principles

> Step 2 of 3. Applies [skill_principle.md](skill_principle.md) to `apb/src/anndata_proteomics` as a
> **test of the principles**, not an audit of the code. Date: 2026-08-12.
>
> **Second pass.** The first pass ran a detector whose top-ranked shapes were `isinstance` and string
> dispatch. Adding P2.5 (`is None` on an owned optional field) and P2.6 (a validator rejecting field
> combinations) changed the result substantially: the new rank-1 shape is the highest-yield one in this
> codebase, and it finds a class of defect the first pass could not see at all.
>
> **No code was changed.** Each finding now carries a **Remedy** section, because the point of the
> principle is not "delete the `if`" — it is *put the behaviour on the type*. A finding without a
> polymorphic remedy is a complaint.

---

## Method

Ran the detector ranking from `skill_principle.md` §"Using this as a detector", top-down:

| Rank | Shape | How it was run |
| --- | --- | --- |
| 1 | P2.6 validator rejecting field combinations | grep 47 `@model_validator` / `@field_validator` sites, read each |
| 2 | P2.3 same branch set in >1 function | grep each discriminator name across the package |
| 3 | P2.5 `is None` / `is not None` on an owned optional field | grep `\.<field> is (not )?None` |
| 4 | P2.4 new case requires editing N functions | derived from the branch sets found at rank 2 |
| 5 | P2.1 / P2.2 `isinstance` / string dispatch | 223 `isinstance` + 31 `elif` sites, read by module |
| 6–7 | P1 shapes | AST scan for params typed as an APB class where the body reads one attribute |

Corpus: 97 modules, 254 classes, 651 functions, 223 `isinstance` sites, 47 validators.

**Reporting rule applied:** each finding states its shape, the bound it clears, and its remedy. Findings are
labelled **evidence** (mechanically checkable) or **judgement** (required reading).

---

## Result summary

| | Candidates | Findings | Blocked by a bound |
| --- | --- | --- | --- |
| **P2.6** validator rejects field combinations | 47 validators | **3** (F1, F2, F4) | 43, +1 withdrawn on a bound |
| **P2.3** same branch set in >1 function | — | **5** (F1, F3, F4, F5, F7) | — |
| **P2.5** `is None` on an owned optional field | 17 sites | **1** (F3) | the rest fold into F2/F4's remedies |
| **P2.1/P2.2** `isinstance` / string dispatch | 223 + 31 | **2** (F4, F6) | the large majority |
| **P1** parameters name capabilities | 53 single-attribute params | **1**, judgement (F7) | 7 (whole-object use) |

**The first pass reported two findings; this one reports seven, plus one candidate withdrawn.** The three
extra rank-1/rank-3 findings (F1, F2, F3) were invisible to a detector that greps for `isinstance`, and
they are the ones with the largest blast radius — F2 alone accounts for four validators, nine
`input_shape` branch sites across five modules, and three functions that raise when handed the wrong
variant of the type they declare. The withdrawn candidate (`MassTolerance`) is kept, unnumbered, next to the other non-findings: it has the
rank-1 shape exactly and is *not* a defect, and the test that separates it — **can you name the method
that would go on the split types?** — is the most portable thing this review produced.

**The dominant shape in APB has a name now:** *the union is already split, and every consumer still
discriminates on it* (F5). APB does the hard modelling step correctly and then does not put the behaviour
on the types, so the branch survives the split. That shape did not appear in step 1 and belongs there —
see [What carries back into step 1](#what-carries-back-into-step-1).

---

## The remedy architecture — stated once, used by every finding below

Every finding's remedy has the same shape, so it is described here rather than seven times.

**The root cause the seven findings share is that APB's pydantic rule models are simultaneously the
document schema and the computational model.** They are two jobs: one describes what may appear in a TOML
file, the other converts DataFrames. Fusing them is why a decoder tag ends up on the object that computes,
why validators end up standing in for types, and why every consumer re-derives what it was handed.

AGENTS.md already names this rule for containers — *"AnnData and MuData are storage adapters, not APB's
computational model"*. **TOML-plus-pydantic is a storage adapter for rules**, and the same rule applies.

Three layers, and the middle one is the whole point:

| Layer | Where | What it is | Holds |
| --- | --- | --- | --- |
| **Document** | `rules/` | pydantic. Knows the file format. | `source: str` as written, tags, `optional_select` maps |
| **Factory** | `rules/` → `converters/` | **the one place that reads a tag** | — |
| **Runtime** | `converters/` | plain frozen dataclasses. Behaviour, no tags. | compiled `re.Pattern`, resolved column lists, the coercion already chosen |

```python
def make_conversion(rule: ParseRule) -> Conversion: ...   # LongConversion | WideConversion, per shape
```

Three consequences that decide most of what follows:

1. **The runtime type carries no discriminator field.** It does not need one — it *is* the type. Tags exist
   so a decoder can pick a class; once the class is picked the tag is dead weight, and leaving it on the
   computing object is what invites the next `if`.
2. **The document's validators stop being a design smell and become what they are: input validation.**
   Rejecting `sample_name_cleanup` in a long-rule TOML is branching on *what happened* — someone wrote a bad
   file. That is correct and it stays. It is only a missing polymorphism when the validated type is *also*
   the computational model, because then the combination it polices leaks into every consumer. **This
   refines bound four** — see [below](#bound-four-new-not-every-combination-rejecting-validator-is-a-discriminator).
3. **The two type families are not duplication.** The document holds `source: str`; the runtime holds a
   `re.Pattern` compiled once. The runtime type is the *elaborated* form, and building it is where the
   `re.compile` calls now scattered through the converters happen — once, at the boundary.

`ModificationLocation` (F5) is the exception that shows the rule: those types are already plain runtime
dataclasses, not pydantic documents, so its remedy is just methods — no factory, no second family.

### Every runtime union needs a factory — and none of these is a Builder

**Terminology, because an earlier draft got it wrong.** These were all called `build_*`, which reads as the
GoF *Builder* pattern. None of them is one. Builder constructs a complex object **incrementally** through a
stepwise interface driven by a director (`addX()`, `addY()`, `getResult()`); every function here is a single
call. They are **factory functions**, in two shapes:

| Shape | Naming | Functions | What it does |
| --- | --- | --- | --- |
| **Lookup** | `<thing>_for(...)` | `policy_for`, `format_for` | tag → one of N stateless singletons. Selects; constructs nothing. |
| **Factory** | `make_<thing>(...)` | the rest | document fields → a new runtime object of one of N types |

`make_conversion` and `make_axis_plan` additionally *compose* — they assemble already-made parts into one
record. That is the closest thing here to Builder and still is not it: one call, no stepwise interface.
Composition is an implementation detail of those two factories, not a separate pattern.

**Does APB have any Builders? No — and the one class named for it is not one.**
`ParseRuleBuilder` (`rules/parse_rule.py:368`) is a frozen dataclass holding six pieces of evidence with a
single `build()` that filters candidate documents and returns the one matching rule. That is a *parameter
object plus a resolve operation* — closer to a query than a builder. Worth knowing before adding a
`build_*` name anywhere in `rules/`, because it would suggest kinship with a pattern nothing here uses.

### Would a real Builder make `make_conversion` / `make_axis_plan` more readable?

**No.** Three candidates, written out so the answer is visible rather than asserted.

**(a) Factory function — what F2 proposes.** One shared prelude, one branch, two returns:

```python
def make_conversion(rule: ParseRule) -> Conversion:
    layers = tuple(make_layer(layer) for layer in rule.layers)
    computers = tuple(make_computer(c, rule) for c in rule.columns.var.compute)
    modifications = make_applier(rule)
    axis = make_axis_plan(rule.axis, rule.columns)
    if rule.input_shape == "long":
        return LongConversion(layers, computers, modifications, make_exploder(rule.fragments), axis)
    return WideConversion(layers, computers, modifications, make_sample_namer(rule.sample_name_cleanup), axis)
```

**(b) GoF Builder.** Incremental, stepwise, director-driven:

```python
conversion = (ConversionBuilder(rule)
    .with_layers().with_computers().with_modifications().with_axis().build())
```

Worse on three counts, and the second is disqualifying:

- **Every part is mandatory and the order is fixed.** Builder earns its place when construction is
  *caller-configurable across many combinations*. There is one combination.
- **A builder's internal state is a record whose fields may or may not be set yet** — 2^N shapes, validated
  at `build()`. That is the exact defect this review is about, reintroduced as a pattern and given a
  respectable name. (a) returns a frozen record with every field required, checked statically.
- **It adds a stage to the call graph with no branching benefit** — the carpet test.

If a test later needs a conversion with a stub layer reader, `dataclasses.replace` covers it without any of
that.

**(c) Per-class named constructors** — `LongConversion.from_rule(rule)` / `WideConversion.from_rule(rule)`,
which *is* permitted by the naming rule above since each returns its own class. This is the tempting one,
and it is still worse:

```python
def make_conversion(rule: ParseRule) -> Conversion:          # now 3 lines
    if rule.input_shape == "long":
        return LongConversion.from_rule(rule)
    return WideConversion.from_rule(rule)
```

The four shared lines now appear in both `from_rule` bodies. Factoring them back out into a
`_common_parts(rule)` helper returns a bag of four unrelated values and puts a fourth stage in the chain —
so (c) trades one readable function for two duplications or one bag.

**And the `if` does not go away in any of them.** It is the single dispatch point at a factory, which this
review's own bound explicitly blesses. (c) does not remove it; (b) hides it inside `build()`. Keeping it
visible in a nine-line function is the honest version.

This whole terminology question is now a workspace rule — see *"Never use a design-pattern name unless the
code matches that pattern's definition"* in [AGENTS.md](../../AGENTS.md), which cites both
`ParseRuleBuilder` and this document's own `build_*` misnaming as the evidence.

The full set, so a missing one is visible at a glance:

```python
make_conversion(rule: ParseRule)                       -> LongConversion | WideConversion              # F2
make_layer(layer: LayerDocument)                       -> FactorLayer | NumericLayer                   # F1
make_values(pattern: ValuePatternDocument, missing)    -> PlainNumericValues | RegexNumericValues      # F5
make_computer(document: ColumnComputeDocument, rule)   -> ColumnComputer                               # F4
make_exploder(fragments: FragmentsDocument)            -> NoFragments | Positional… | ColumnLabeled…   # F5
make_applier(rule: ParseRule)                          -> NoModifications | TokenRegex… | SiteList…    # F3
make_sample_namer(cleanup: SampleNameCleanupDocument)  -> NoCleanup | PatternNamer                     # F2
make_axis_plan(axis: Axis, columns: Columns)           -> AxisPlan                # a record, not a union
policy_for(duplicates: Duplicates)                     -> DuplicatePolicy                              # F7
format_for(path: Path)                                 -> DelimitedText | Parquet                      # F6
```

**A remedy that shows the union and stops has not finished**, because nothing yet turns the document's tag
into the type. Where a finding elides its factory for brevity, it is still required.

All but `make_axis_plan` return a union, which is why all but that one are free functions rather than
classmethods — the rule stated in F6: **named constructor when the return type is the class; free function
when it is a union of several.** Every one except `format_for` is reached from `make_conversion`;
`format_for` stands alone at the reader boundary because its input is a `Path`, not a rule document.

**The factory is also where an unimplemented variant fails.** A mode declared in the document schema with
no runtime class produces a missing registry entry, which raises once at construction time instead of
partway through a conversion — see F7's `keep_all_as_raw_table`.

**One hazard the lookup shape carries.** `_BY_MODE` and `_BY_EXTENSION` hold shared singleton instances,
which is safe only while those types are frozen and stateless. If a policy ever gains state — collecting
which cells collided, say, so the conversion can report them — the dict must hold classes or factories, not
instances, or two conversions will share one accumulator.

---

## Finding 1 — `Layer` carries a mode flag plus three fields valid for only one mode

**Shape:** P2.6 (rank 1) **and** P2.3 (rank 2). **Class: evidence.**

`rules/rule_components.py:167` — `Layer` declares `encoding_mode: EncodingMode` alongside `categories`,
`missing_values` and `value_pattern`, then spends a validator rejecting the combinations that flag makes
illegal (`rule_components.py:197`):

```python
if self.encoding_mode == "factor" and not self.categories:
    raise ValueError(f"Layer {self.name!r}: encoding_mode='factor' requires non-empty 'categories'.")
if self.encoding_mode == "factor" and self.missing_values:
    raise ValueError(f"Layer {self.name!r}: 'missing_values' is only valid for numeric layers.")
if self.encoding_mode == "factor" and isinstance(self.value_pattern, RegexValuePattern):
    raise ValueError(f"Layer {self.name!r}: 'value_pattern' is only valid for numeric layers.")
```

Three rejections in one validator, all saying *this field belongs to the other mode*. That is the written
admission that `Layer` is two types.

The cost lands downstream, where the same three-arm branch set is written twice:

| Site | Code |
| --- | --- |
| `converters/wide.py:91` | `_coerce_layer_series` — `factor` → `elif RegexValuePattern` → default |
| `converters/long.py:133` | the identical chain, inline in the layer loop |

```python
# wide.py:91                                  # long.py:133 (inline, same three arms)
if layer.encoding_mode == "factor":           if layer.encoding_mode == "factor":
    return encode_factor(...)                     values = encode_factor(...)
if isinstance(layer.value_pattern, Regex…):   elif isinstance(layer.value_pattern, Regex…):
    return coerce_regex_numeric(...)              values = coerce_regex_numeric(...)
return coerce_numeric(...)                    else:
                                                  values = coerce_numeric(...)
```

**Bound cleared:** `Layer` is APB's own pydantic model, defined in APB, populated from APB's own rule
documents. Nothing foreign is involved, so the parse-boundary bound does not apply. And this is not "two
arms that will never grow" — the codebase has already grown the third (`value_pattern`) *inside* the
numeric arm.

### Remedy — the polymorphism

The document keeps the flag — a TOML file has to spell `encoding_mode` somehow, and `_validate_encoding`
stays as ordinary input validation. **The factory turns that flag into a type, once**, and the runtime
types carry the coercion:

```python
# rules/ — document. Unchanged shape, unchanged validator. Knows the file format, nothing else.
class LayerDocument(RuleModel):
    name: str
    source: str
    encoding_mode: EncodingMode = "numeric"
    categories: dict[str, int] = Field(default_factory=dict)
    missing_values: list[float] = Field(default_factory=list)
    value_pattern: ValuePatternDocument = NO_VALUE_PATTERN
    required: bool = False

# converters/ — runtime. No mode field: the class is the mode.
@dataclass(frozen=True, slots=True)
class FactorLayer:
    name: str
    source: str
    categories: Mapping[str, int]                 # non-empty by construction, not by validator
    def coerce(self, series: pd.Series) -> pd.Series:
        return encode_factor(series, self.categories)

@dataclass(frozen=True, slots=True)
class NumericLayer:
    name: str
    source: str
    missing_values: tuple[float, ...]
    pattern: re.Pattern[str] | None               # compiled once, here — see below
    def coerce(self, series: pd.Series) -> pd.Series: ...

type LayerReader = FactorLayer | NumericLayer
```

Both call sites collapse to one line with no branch:

```python
values = layer.coerce(df[layer.source])   # wide.py and long.py, identically
```

**What this buys, precisely.** The three rejections in `_validate_encoding` still run against the document,
where they belong — a user *can* write `encoding_mode = "factor"` with `missing_values` in a TOML file and
must be told. But downstream of the factory that combination is **unrepresentable**: `FactorLayer` has no
`missing_values` field. Both copies of the three-arm branch disappear, and the regex in `value_pattern` is
compiled once at construction time instead of per layer per conversion.

**Note the remaining `| None`.** `pattern: re.Pattern[str] | None` above is deliberate, and F5 fixes it —
the numeric coercion splits into its own two runtime types rather than carrying an optional pattern. It is
left visible here so the two findings compose rather than appearing to contradict.

---

## Finding 2 — `ParseRule` is two types wearing a string flag

**Shape:** P2.6 (rank 1, ×4) + P2.4 + P2.5. **Class: evidence.**

`rules/parse_rule.py:95` — one `ParseRule` model carries `input_shape: InputShape` (`"long" | "wide"`) and
three optional blocks. Four validators then police which combinations are legal:

| Validator | Line | Rejects |
| --- | --- | --- |
| `_cleanup_only_for_wide` | 162 | `sample_name_cleanup is not None and input_shape == "long"` |
| `_wide_obs_has_no_optional_select` | 195 | `input_shape == "wide" and columns.obs.optional_select` |
| `_fragments_only_for_fragment_level` | 205 | `fragments is not None and quantification_level != "fragment"` |
| `_wide_layer_sources_are_sample_regexes` | 110 | *interprets `layer.source` differently per shape* |

The fourth is the sharpest: `Layer.source` is documented (`rule_components.py:170-173`) as meaning *an exact
column name* for long rules and *a regex with a `(?P<sample>…)` group* for wide ones. **One field, two
types, disambiguated by a flag on a different object.**

Two further sites prove the type is already behaving as two:

```python
def required_long_headers(self) -> frozenset[str]:          # parse_rule.py:140
    if self.input_shape != "long":
        raise ValueError("required_long_headers is defined only for long-format rules")
```

A method on the type that raises for half its own instances is a method on the wrong type. Its mirror
images sit in the converters:

```python
if rule.input_shape != "wide":                              # converters/wide.py:135
    raise ValueError(f"convert_wide called with {rule.input_shape!r} rule")
if rule.input_shape != "long":                              # converters/long.py:99
    raise ValueError(f"convert_long called with {rule.input_shape!r} rule")
```

Three runtime checks that a type system would make unnecessary.

**Bound cleared:** APB's own model, no foreign input. The `if` is on *what the rule is*, not on what
happened — `converters/assemble.py:62` uses it to pick which conversion to run.

### Remedy — the polymorphism

**The document stays one model.** `input_shape` is a legitimate key in a rule file, and the four validators
are legitimate checks on a file someone hand-wrote. Nothing about the TOML format is wrong; what is wrong is
that this model is also what `convert_table` computes with.

**The factory reads the flag once and returns a conversion object.** After that the flag does not exist:

```python
# converters/ — runtime. Per-shape, no tag, no optional blocks that mean "I am the other kind".
@dataclass(frozen=True, slots=True)
class LongConversion:
    layers: tuple[LayerReader, ...]
    computers: tuple[ColumnComputer, ...]         # F4
    modifications: ModificationApplier            # NoModifications is a member — never None
    fragments: FragmentExploder                   # NoFragments is a member — never None
    axis: AxisPlan

    def required_headers(self) -> frozenset[str]: ...    # no guard — always meaningful here
    def convert(self, df: pd.DataFrame) -> ConversionPieces: ...

@dataclass(frozen=True, slots=True)
class WideConversion:
    layers: tuple[LayerReader, ...]
    computers: tuple[ColumnComputer, ...]
    modifications: ModificationApplier
    sample_names: SampleNamer                     # compiled cleanup regex, or the identity namer
    axis: AxisPlan

    def convert(self, df: pd.DataFrame) -> ConversionPieces: ...

type Conversion = LongConversion | WideConversion


def make_conversion(rule: ParseRule) -> Conversion:      # the only place input_shape is read
    layers = tuple(make_layer(layer) for layer in rule.layers)
    computers = tuple(make_computer(c, rule) for c in rule.columns.var.compute)
    modifications = make_applier(rule)           # NoModifications when no compute consumes it — F3
    axis = make_axis_plan(rule.axis, rule.columns)
    if rule.input_shape == "long":
        return LongConversion(
            layers=layers,
            computers=computers,
            modifications=modifications,
            fragments=make_exploder(rule.fragments),
            axis=axis,
        )
    return WideConversion(
        layers=layers,
        computers=computers,
        modifications=modifications,
        sample_names=make_sample_namer(rule.sample_name_cleanup),
        axis=axis,
    )
```

**A question the split forces, which the flat model let APB avoid:** `fragments` appears on
`LongConversion` and not on `WideConversion` above. Is that right — can a wide rule ever carry a
`[fragments]` block? Today `_fragments_only_for_fragment_level` ties fragments to
`quantification_level == "fragment"` and says nothing about shape, so the flat model permits the
combination and nobody has had to decide. Writing the two classes makes the decision unavoidable. That is
not a cost of the split; it is the split doing its job.

Then `converters/assemble.py:62-65` — the branch the whole flag exists to serve —

```python
if rule.input_shape == "long":
    pieces = convert_long(df, rule)
else:
    pieces = convert_wide(df, rule)
```

becomes

```python
pieces = conversion.convert(df)
```

**What this buys, precisely.** `_cleanup_only_for_wide` and `_wide_obs_has_no_optional_select` keep doing
their job on the document — and become *unable to matter* downstream, because `LongConversion` has no
`sample_names` field to set wrongly. `_wide_layer_sources_are_sample_regexes` stops being a validator that
asks "am I wide?" and becomes the factory's `re.compile` step for `WideConversion` — the check happens
because compiling is what building a wide conversion *does*. All three `raise …called with …rule` guards
become type errors caught before the program runs. And `Layer.source`'s two meanings finally separate:
the document keeps the `str`, `WideConversion` holds the compiled `re.Pattern`, `LongConversion` holds a
column name.

**On the absent blocks.** Write `fragments: FragmentExploder`, **never** `Fragments | NoFragments`. Union-
ing a `NoX` onto an existing union makes a three-member type spelled as a two-member one, and every consumer
is back to asking *"is it the `NoFragments` one?"* — `is None` under a new name. `NoFragments` is a
**member** of the union, with `explode(df) -> df`. APB already does exactly this one file away —
`ValuePattern = NoValuePattern | RegexValuePattern` with a module-level `NO_VALUE_PATTERN`.

**Second-order effect worth stating:** `sample_name_cleanup: SampleNameCleanup | None` becomes
`SampleNameCleanup = NO_CLEANUP`, with `NoCleanup` a member of that union — the same shape as `NoFragments`
above. That kills one more branch, in `converters/wide.py:123`:

```python
def _apply_sample_cleanup(samples: list[str], rule: ParseRule) -> list[str]:
    if rule.sample_name_cleanup is None:
        return samples          # ← disappears: NoCleanup.apply(samples) returns samples
```

This is the clearest small case in the codebase, because the absent arm's behaviour is *visible in the
deleted code*: the branch's body was already `return samples`. Moving that one line onto `NoCleanup.apply`
is the whole remedy. **The split is not the point — it is where the identity behaviour goes.** A type split
with no method on the empty member leaves the caller asking "is it the empty one?", which is Finding 5.

---

## Finding 3 — `converters/assemble.py` re-derives which `ParseRule` variant it received

**Shape:** P2.5 (rank 3). **Class: evidence.** Consequence of F2; reported separately because it is where
the cost is actually paid, and because it contains a provably dead branch.

`convert_table` opens by asking twice which kind of rule it has:

```python
def convert_table(df, rule: ParseRule, *, strict: bool = False) -> ConversionPieces:
    if rule.modifications is not None and _modifications_consumed(rule):    # :46
        df = apply_modifications(df.copy(), rule.modifications)
    if rule.fragments is not None:                                          # :51
        df = df[_columns_needed_for_long(df, rule)]                         # :57
        df = explode_fragments(df, rule.fragments)
```

`_columns_needed_for_long` then asks the same two questions again:

```python
def _columns_needed_for_long(df, rule: ParseRule) -> list[str]:
    ...
    if rule.modifications is not None:                                      # :97
        ...
    if rule.fragments is not None:                                          # :100
        ...
```

**Line 100 is provably always true.** `_columns_needed_for_long` has exactly one call site — line 57 —
which is inside `if rule.fragments is not None:` at line 51. The function cannot be reached with
`fragments` absent, and the branch is dead. Nothing in the type system says so, so it was written anyway;
nothing will tell a future reader either.

This is the concrete answer to *"why did we end up with a pile of near-identical signatures and a wall of
`is not None`"*: every function taking `ParseRule` receives 2³ = 8 possible shapes (three optional blocks),
of which the validators permit fewer, and **each consumer must re-derive which one it got**. The
signatures look identical because they are — the discrimination happens in the bodies.

**Bound cleared:** these are not guard clauses. `if not values: return None` asks *what happened*;
`if rule.fragments is not None` asks *which kind of rule is this*, and the arms do different work.

### Remedy — the polymorphism

Falls out of F2 with no separate design. The document is built into a conversion once, at the top; after
that every step is a call on a type that was chosen at construction time:

```python
def convert_table(df, rule: ParseRule, *, strict: bool = False) -> ConversionPieces:
    conversion = make_conversion(rule)            # the only place a tag or an absent block is read
    df = conversion.modifications.apply(df)        # NoModifications.apply returns df unchanged
    df = conversion.fragments.explode(df)          # NoFragments.explode returns df unchanged
    df = conversion.materialize_columns(df)
    pieces = conversion.convert(df)
    check_layer_occupancy(pieces.layers, x_layer=conversion.axis.x_layer, strict=strict)
    return pieces
```

Whether `make_conversion` is called here or once per rule at load time is an ordinary caching question,
not a design one — and building once per rule is the version that stops recompiling the same regexes on
every file.

`_columns_needed_for_long` becomes a field of the conversion — the set of columns a rule reads is knowable
at construction time and does not depend on the DataFrame — so the "are there fragments" question is answered by
which class the factory picked, and the dead branch has nowhere to be written.

**One caveat to record honestly:** the `_modifications_consumed(rule)` guard at line 46 is a genuine
optimization — a rule that inherits a `[modifications]` block with no consuming compute skips the per-row
tokenization. It is not lost, it *moves*: the factory decides once whether any compute consumes the
modification output, and hands back `NoModifications` when none does. Branching on *what happened* is still
correct; doing it once at construction time instead of on every table is strictly better.

---

## Finding 4 — `ColumnCompute.how`: one branch set, three modules

**Shape:** P2.3 + P2.6 + P2.2. **Class: evidence.**

`ColumnCompute` (`rules/rule_components.py:51`) has `how: ColumnComputeMode` and `separator: str | None`.
The six modes are enumerated in **three separate modules**:

| Module | Function | Line | What it does with `how` |
| --- | --- | --- | --- |
| `rules/rule_components.py` | `_validate_generic_compute` | 57 | rejects `separator` unless `how == "join_nonempty"` |
| `rules/parse_rule.py` | `_validate_computed_column` | 269–283 | per-mode validation, four arms |
| `converters/assemble.py` | `_compute_column` | 204–226 | per-mode computation, five arms |

The validator is the rank-1 shape verbatim:

```python
if self.how == "join_nonempty":
    if self.separator is None or not self.separator:
        raise ValueError("how='join_nonempty' requires a non-empty separator.")
elif self.separator is not None:
    raise ValueError("separator is valid only for how='join_nonempty'.")
```

And it produces exactly the dead re-check F3 describes, one module away:

```python
if column.how == "coalesce":                              # assemble.py:189
    return _coalesce_columns(df, sources)
if column.separator is None:                              # :191 — unreachable
    raise ValueError(f"cannot compute column {column.name!r}; how={column.how!r} requires a separator")
return _join_nonempty_columns(df, sources, column.separator)
```

The validator has already guaranteed `separator` is a non-empty `str` whenever `how == "join_nonempty"` —
but a validator cannot tell a type checker anything, so the consumer re-checks, and the error message
describes a state the model refuses to construct.

Adding a seventh compute mode means editing three modules in two packages. Nothing links them.

### Remedy — the polymorphism

**Document side** — all six modes, each declaring only its own fields. Every shape rule that
`_validate_generic_compute` and `_validate_computed_column` police from the outside becomes a field
declaration, including the name the mode must have:

```python
class CoalesceDocument(RuleModel):
    how: Literal["coalesce"] = "coalesce"
    name: str
    from_: list[str] = Field(alias="from", min_length=2)     # no separator field exists here

class JoinNonEmptyDocument(RuleModel):
    how: Literal["join_nonempty"] = "join_nonempty"
    name: str
    from_: list[str] = Field(alias="from", min_length=2)
    separator: str = Field(min_length=1)                     # required: assemble.py:191 becomes unwriteable

class StrippedSequenceDocument(RuleModel):
    how: Literal["stripped_sequence"] = "stripped_sequence"
    name: Literal["ProForma_peptide"] = "ProForma_peptide"   # replaces _PROFORMA_COMPUTE_NAME
    from_: list[str] = Field(alias="from", min_length=1, max_length=1)

class ProformaSequenceDocument(RuleModel):
    how: Literal["proforma_sequence"] = "proforma_sequence"
    name: Literal["ProForma_peptidoform"] = "ProForma_peptidoform"
    from_: list[str] = Field(alias="from", min_length=1, max_length=1)

class ProformaIonDocument(RuleModel):
    how: Literal["proforma_ion"] = "proforma_ion"
    name: Literal["ProForma_ion"] = "ProForma_ion"
    from_: list[str] = Field(alias="from", min_length=2, max_length=2)   # (sequence, charge)

class ProformaFragmentDocument(RuleModel):
    how: Literal["proforma_fragment"] = "proforma_fragment"
    name: Literal["ProForma_fragment"] = "ProForma_fragment"
    from_: list[str] = Field(alias="from", min_length=2, max_length=2)   # (ion, label)

type ColumnComputeDocument = Annotated[
    CoalesceDocument | JoinNonEmptyDocument | StrippedSequenceDocument
    | ProformaSequenceDocument | ProformaIonDocument | ProformaFragmentDocument,
    Field(discriminator="how"),
]
```

**Runtime side** — five computers, not six. `stripped_sequence` and `proforma_sequence` differ only in which
APB-derived column they read, so one runtime class covers both:

```python
@dataclass(frozen=True, slots=True)
class CoalesceColumn:
    name: str
    sources: tuple[str, ...]
    def compute(self, df: pd.DataFrame) -> pd.Series: ...     # first non-null in declaration order

@dataclass(frozen=True, slots=True)
class JoinNonEmptyColumn:
    name: str
    sources: tuple[str, ...]
    separator: str                                            # a str, never None
    def compute(self, df: pd.DataFrame) -> pd.Series: ...

@dataclass(frozen=True, slots=True)
class DerivedSequenceColumn:
    name: str
    source_key: str                                           # "stripped_sequence" | "proforma_sequence"
    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df[self.source_key]

@dataclass(frozen=True, slots=True)
class ProformaIonColumn:
    name: str
    sequence_key: str
    charge_key: str
    def compute(self, df: pd.DataFrame) -> pd.Series: ...

@dataclass(frozen=True, slots=True)
class ProformaFragmentColumn:
    name: str
    ion_key: str
    label_key: str
    def compute(self, df: pd.DataFrame) -> pd.Series: ...

type ColumnComputer = (
    CoalesceColumn | JoinNonEmptyColumn | DerivedSequenceColumn
    | ProformaIonColumn | ProformaFragmentColumn
)
```

**Factory** — the last place `how` is read, and where the checks that need the *whole rule* live:

```python
def make_computer(document: ColumnComputeDocument, rule: ParseRule) -> ColumnComputer: ...
```

Then `_compute_column`'s five-arm chain and `_compute_generic_column`'s two-arm tail both collapse to
`computer.compute(df)`.

**Note the mapping is not 1:1, and that is the point.** Six document types, five runtime types. The document
splits by what a user writes in TOML; the runtime splits by what actually differs at compute time. A factory
is a *mapping*, not a mirror — the moment it is forced to be a mirror it stops being able to absorb
differences that exist only in the file format.

**Where each check ends up.** Three destinations, and knowing which is which is most of the work:

| Check | Goes to | Why |
| --- | --- | --- |
| "join_nonempty requires a separator", "coalesce needs two sources", "must be named `ProForma_ion`" | **field declarations** | They constrain one column in isolation |
| "proforma_ion is valid only for ion or fragment rules", "its charge source must declare `type='integer'`", "must be used in `axis.var_keys`" | **the factory** | They need the rule, not the column — and the factory is the single dispatch point the bounds already allow |
| "source column(s) missing", "every source is an absent `optional_select`" | **stays in `compute(df)`** | It depends on *this input file's* headers, not on the rule. Branching on what happened — correct, and it stays |

That last row is worth stating explicitly because it is the trap: not everything moves to construction time.
`allow_missing` is per-input, so resolving sources against the frame cannot happen when the rule is built.

**What this buys, precisely.** `_validate_generic_compute` disappears entirely — every rule it enforced is
now a field declaration. `_validate_computed_column`'s four-arm chain disappears; its per-mode bodies become
factory cases. `_PROFORMA_COMPUTE_NAME` and its "must be named X" error become six `Literal`s.
`assemble.py:191`'s dead re-check cannot be written, because `JoinNonEmptyColumn.separator` is a `str`.

Adding a seventh mode becomes: **one document class, one computer class, one factory case** — three adjacent
edits the type checker enforces, instead of three modules in two packages with nothing linking them.

---

## Finding 5 — three unions are already split, and every consumer discriminates anyway

**Shape:** P2.1 + P2.3. **Class: evidence.** *This is the shape the first pass missed the significance of,
and it is the most common one in APB.*

APB models three of its variant concepts **correctly** — as discriminated unions of separate classes:

```python
type ValuePattern  = Annotated[NoValuePattern | RegexValuePattern,          Field(discriminator="mode")]
type Fragments     = Annotated[PositionalFragments | ColumnLabeledFragments,
                                                          Field(discriminator="label_strategy")]
type ModificationLocation = (ResidueLocation | TerminalLocation
                             | TerminalOnlyLocation | UnlocalizedLocation)
```

`NO_VALUE_PATTERN` is even instantiated as a module-level identity value — the Null Object, already there.
**The modelling is done. The behaviour was never moved onto it**, so every consumer still asks which one it
has:

| Union | Consumers that discriminate |
| --- | --- |
| `ValuePattern` | `converters/wide.py:94`, `converters/long.py:135` — `isinstance(…, RegexValuePattern)` |
| `Fragments` | `converters/_fragments.py:58` and `:73` (twice in one function), `converters/assemble.py:101`, `rules/parse_rule.py:413`, `rules/parse_rule.py:804-806` |
| `ModificationLocation` | `modifications/apply_rules.py` `_location_position:171`, `_adjacent_residue:177`, `_modification_occurrence:358`, `_record_unknown_token:399` |

`explode_fragments` is the clearest single example — it branches on `label_strategy` **twice inside one
function**, once to build `packed_columns` and again to explode:

```python
if fragments.label_strategy == "column":        # _fragments.py:58
    packed_columns = [fragments.label_column, *value_columns]
else:
    packed_columns = list(value_columns)
...
if fragments.label_strategy == "positional":    # :73
    ... positional explode ...
else:
    ... column-labelled explode ...
```

`ModificationLocation` is the same disease at four-way width: four functions each ask *where does this
modification sit?* and answer it per type. Adding a fifth location kind means finding four functions, with
nothing forcing you to find the fourth.

**Bound cleared decisively:** these are APB's own classes, in APB's own modules — for
`ModificationLocation`, in the *same file* as the functions branching on it. Polymorphism is fully
available; it was simply not used.

### Remedy — the polymorphism

**Name the question each branch set asks, and answer it once, on each type.** Two of the three unions are
pydantic documents, so their behaviour goes on the runtime twin the factory produces; the third is already
a runtime type, so it just gets a method.

```python
# ValuePattern — document classes stay as they are; the factory produces these.
@dataclass(frozen=True, slots=True)
class PlainNumericValues:
    missing_values: tuple[float, ...]
    def coerce(self, series: pd.Series) -> pd.Series:
        return coerce_numeric(series, self.missing_values)     # identity arm, finally given behaviour

@dataclass(frozen=True, slots=True)
class RegexNumericValues:
    missing_values: tuple[float, ...]
    pattern: re.Pattern[str]                                   # compiled at construction time, not per column
    def coerce(self, series: pd.Series) -> pd.Series:
        return coerce_regex_numeric(series, self.missing_values, self.pattern)
```

That also removes the `pattern: re.Pattern[str] | None` that F1's sketch left open — the optional field was
the branch, and two types replace it.

`ModificationLocation` needs no factory: these are already plain dataclasses in
`modifications/apply_rules.py`, in the same file as the four functions branching on them. **This is the
cleanest case in the codebase and the one the skill should lead with**, precisely because no architecture is
involved — a method, and the branch is gone.

```python
# ModificationLocation — the question is "which token index is this?"
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

# call site, no branch
unknown_tokens[location.token_index(sequence_length)] = raw_token
```

`Fragments` asks two questions, so its runtime twins get two methods — *which columns are packed*, and
*how are labels assigned*:

```python
@dataclass(frozen=True, slots=True)
class ColumnLabeledExploder:
    def packed_columns(self) -> tuple[str, ...]: ...
    def assign_labels(self, work: pd.DataFrame) -> pd.DataFrame: ...

@dataclass(frozen=True, slots=True)
class PositionalExploder:
    def packed_columns(self) -> tuple[str, ...]: ...
    def assign_labels(self, work: pd.DataFrame) -> pd.DataFrame: ...

@dataclass(frozen=True, slots=True)
class NoFragments:
    def packed_columns(self) -> tuple[str, ...]:
        return ()
    def explode(self, work: pd.DataFrame) -> pd.DataFrame:
        return work                                       # identity arm — F3's branch at :51 disappears
```

`explode_fragments` keeps only the steps common to all three — the missing-column check, the per-column
split, the numeric coercion — and its two branches become `fragments.packed_columns()` and
`fragments.assign_labels(work)`.

**The lesson to carry into the skill, stated plainly:** *splitting the type is step one, not the goal.*
APB proves you can do the modelling perfectly — discriminator field, separate classes, even a Null Object
constant — and still write every branch you were trying to avoid. AGENTS.md's ordered remedies say "split
the type"; **they must also say what to do next**, or the split lands and the `isinstance` chain survives
it. `NO_VALUE_PATTERN` exists and `converters/wide.py:94` still asks `isinstance(…, RegexValuePattern)`.

And this finding is why the document/runtime separation is not optional decoration. A pydantic model
*cannot* be the place the behaviour goes without dragging computation into the file-format layer — so an
agent that splits the type and then has nowhere legitimate to put the method stops at the split. **That is
the observed outcome in three of APB's unions.** The factory is what gives the behaviour somewhere to live.

---

## Finding 6 — the file-extension branch set appears three times in one module

**Shape:** P2.3 + P2.4. **Class: evidence.** Carried forward from the first pass, unchanged.

`readers/dispatch.py` — a module whose docstring is *"Dispatch by file extension to the right tabular
reader"* — expresses the set `{.csv, .tsv, .txt, .parquet}` three ways:

1. `EXTENSION_TO_READER` — a registry dict over all four.
2. `EXTENSION_TO_STRING_PRESERVING_READER` — a registry over three, with `.parquet` special-cased by an
   `if suffix == ".parquet"` above the lookup.
3. `read_table_columns` — the set re-implemented as a hand-written `if/elif` chain.

Adding `.feather` means editing three places in one file. The third form has drifted furthest: its error
message reports `sorted(EXTENSION_TO_READER)`, a set it does not itself use.

**And the set is enumerated a fourth time, in `readers/tabular.py`.** The real implementations there are two
functions that take a delimiter — `_read_delimited(path, delimiter)` and
`_read_delimited_preserving_strings(path, delimiter, string_columns)`. Above them sit **six public wrappers
whose entire body binds a delimiter**:

```python
def read_csv(path):                      return _read_delimited(path, ",")
def read_tsv(path):                      return _read_delimited(path, "\t")
def read_detected_text(path):            return _read_delimited(path, detect_text_delimiter(path))
def read_csv_preserving_strings(path, c):           return _read_delimited_preserving_strings(path, ",", c)
def read_tsv_preserving_strings(path, c):           return _read_delimited_preserving_strings(path, "\t", c)
def read_detected_text_preserving_strings(path, c): ...
```

2 operations × 3 delimiters = 6 frozen compositions. **This is the cross-product carpet AGENTS.md names by
name** — *"Prefer X + Y + Z composable pieces the caller composes over X × Y × Z frozen compositions; a
saved composition that spares the caller from composing is a carpet."* The six exist because the delimiter
is not a value anybody holds; it is baked into function names, so the only way to select one is to select a
function. That is what forces the dispatch tables in `dispatch.py` to be keyed on functions in the first
place.

**Bound cleared:** this is not "a single dispatch point at a composition root". The module *has* the
registry pattern and leaks the same set past it twice — and the layer beneath it duplicates the set a
fourth time as a naming convention.

### Remedy — the polymorphism

The extension is a `str` off a `Path` — foreign, so `isinstance` is not the tool and the third bound
applies. The polymorphism is **making the format a type**, and the thing that varies inside it — the
delimiter — a type too. Two format classes, not four, because CSV/TSV/TXT differ only in how the delimiter
is obtained:

```python
# What varies within delimited text: how you get the delimiter.
@dataclass(frozen=True, slots=True)
class FixedDelimiter:
    value: str
    def for_path(self, path: Path) -> str:
        return self.value

@dataclass(frozen=True, slots=True)
class SniffedDelimiter:
    def for_path(self, path: Path) -> str:
        return detect_text_delimiter(path)

type Delimiter = FixedDelimiter | SniffedDelimiter


# The formats.
@dataclass(frozen=True, slots=True)
class DelimitedText:
    delimiter: Delimiter

    def read(self, path: Path) -> pd.DataFrame:
        return _read_delimited(path, self.delimiter.for_path(path))

    def read_preserving_strings(self, path: Path, string_columns: frozenset[str]) -> pd.DataFrame:
        return _read_delimited_preserving_strings(path, self.delimiter.for_path(path), string_columns)

    def columns(self, path: Path) -> list[str]:
        return read_delimited_columns(path, delimiter=self.delimiter.for_path(path))

@dataclass(frozen=True, slots=True)
class Parquet:
    def read(self, path: Path) -> pd.DataFrame:
        return pd.read_parquet(path)

    def read_preserving_strings(self, path: Path, string_columns: frozenset[str]) -> pd.DataFrame:
        return self.read(path)          # a physical schema already preserves exact text

    def columns(self, path: Path) -> list[str]:
        return list(pq.read_schema(path).names)

type TabularFormat = DelimitedText | Parquet


_BY_EXTENSION: dict[str, TabularFormat] = {
    ".csv":     DelimitedText(FixedDelimiter(",")),
    ".tsv":     DelimitedText(FixedDelimiter("\t")),
    ".txt":     DelimitedText(SniffedDelimiter()),
    ".parquet": Parquet(),
}


def format_for(path: Path) -> TabularFormat:
    """Return the tabular format for one path's extension."""
    fmt = _BY_EXTENSION.get(path.suffix.lower())
    if fmt is None:
        raise UnknownFormat(
            f"unsupported extension {path.suffix!r} for {path}; known: {sorted(_BY_EXTENSION)}"
        )
    return fmt
```

**What this deletes.** All six `read_csv` / `read_tsv` / `read_detected_text` wrappers and their
`_preserving_strings` twins — the cross-product collapses to two methods, because the thing that varied was
data, not behaviour. Both dispatch dicts in `dispatch.py` go, `read_table_columns`'s `if/elif` chain goes,
and `.parquet` stops being a special case: it is a format whose `read_preserving_strings` satisfies the
contract without doing anything, which is an identity behaviour, not an exception. **Adding `.feather`
becomes one dict entry.**

**On `format_for` being a free function, not the `TabularFormat.build` classmethod proposed earlier.**
Once the format is a real union there is no class to hang the constructor on — the rule stated below bites
the example that produced it. Named constructor when the return type *is* the class; free function when it
is a union of several. `make_conversion` (F2) and `make_computer` (F4) are free for the same reason.

**On `_BY_EXTENSION` being module-level rather than inside `format_for`.** It could live inside; the
reason not to is allocation, not style — a dict literal in the body reconstructs four format objects on
every call. It is private data next to its only reader, which is where a lookup table belongs.

---

## Finding 7 — records passed whole where one field is used

**Shape:** P1.1/P1.2. **Class: judgement for the 53 sites** — but working the clearest one turned up an
**evidence-class P2.3 finding underneath it** (`duplicates.mode`, three functions, two modules). That
inversion is the finding's real content.

An AST scan found **53 functions** that take an APB-defined class and read exactly one attribute from it
(excluding 7 that call `.model_dump()`/`.as_dict()` and so consume the whole object).

| Type | Functions using exactly one of its fields |
| --- | --- |
| `ParseRule` | 10 |
| `ConversionContext` | 4 |
| `ParseRuleDocument` | 4 |
| `RuleFragment` | 4 |

**Bound honestly applied — and this is why it is judgement, not evidence.** AGENTS.md endorses passing "a
small typed record that represents one invariant". Whether a function should take `axis` instead of `rule`
is a per-site call. The scan proves the **shape** is pervasive; it does not prove 53 defects, and this
review does not claim it does.

### The worked site — and what it turns out to be

The clearest `ParseRule` site is `_aggfunc_for`, and following it produced the most useful result in this
finding: **it is not a P1 problem at all.** Several functions take the whole rule to reach
`rule.axis.duplicates.mode`, and each branches on the same four-member set:

```python
def _aggfunc_for(rule: ParseRule) -> str:                          # converters/long.py:36
    mode = rule.axis.duplicates.mode
    if mode == "aggregate":
        return "sum"
    if mode == "keep_all_as_raw_table":
        raise NotImplementedError("duplicates.mode='keep_all_as_raw_table' is not yet supported")
    return "first"

def _raise_on_duplicate_cells(df, rule: ParseRule) -> None:        # converters/long.py:45
    if rule.axis.duplicates.mode != "error":
        return
    ...

def _raise_on_duplicate_features(df, rule: ParseRule) -> None:     # converters/wide.py:104
    if rule.axis.duplicates.mode != "error":
        return
    ...                                                            # near-identical body
```

`DuplicateMode = Literal["error", "aggregate", "keep_first", "keep_all_as_raw_table"]`
(`rule_components.py:23`) — four members. **That is P2.3, rank 2, evidence class**, and the first pass
missed it because the branch is spelled `!= "error"` rather than `isinstance`.

**Six sites, not three**, once `wide.py` is read properly — the wide converter branches on the mode three
times inside one function:

| Site | Branch |
| --- | --- |
| `long.py:36` | `_aggfunc_for` — three arms |
| `long.py:47` | `_raise_on_duplicate_cells` — `!= "error"` |
| `wide.py:69` | reject when a sample has more than one column for a layer |
| `wide.py:77` | `combined.sum(axis=1)` vs `combined.bfill(axis=1).iloc[:, 0]` |
| `wide.py:83` | `grouped.sum()` vs `grouped.first()` |
| `wide.py:104` | `_raise_on_duplicate_features` — `!= "error"`, near-identical to `long.py:47` |

### And a seventh, which is its own shape: the discriminator laundered through a string

`_aggfunc_for` does not act on the mode. It **translates it into a string** and hands that string across a
function boundary, where a *second* dispatch converts it back into behaviour:

```python
aggfunc = _aggfunc_for(rule)                        # long.py:115 — mode → "sum" | "first"
...
def _build_matrix(..., aggfunc: str) -> DenseLayerMatrix:      # long.py:70 — a str parameter
    if aggfunc == "sum":                                       # long.py:81 — string → behaviour
        ...
    else:  # "first" non-null
        ...
```

Two translations that exist only because the policy has no type. The string is not data anyone needs; it is
a discriminator in disguise, and `aggfunc: str` is the parameter that carries it. **Worth naming as a
separate tell**: when a function's job is to turn a mode into a string that another function branches on,
both functions are the same missing polymorphism, split across a boundary.

### Remedy — the polymorphism

The question all six sites ask is *how do several values that land in one cell become one value?* — so
that is the method. **The policy performs the combination; it does not return a token naming one.**

```python
@dataclass(frozen=True, slots=True)
class ErrorOnDuplicates:
    """Repeated keys are a rule error: combining is never permitted."""

    def combine_cells(self, cells: CellContributions) -> DenseLayerMatrix:
        cells.raise_if_any_repeated()          # absorbs _raise_on_duplicate_cells (long.py:45)
        return cells.single()

    def combine_columns(self, columns: pd.DataFrame, layer: str, sample: str) -> pd.Series:
        if columns.shape[1] > 1:               # absorbs wide.py:69, with its message
            raise ValueError(
                "duplicate observation-feature keys are not allowed when "
                f"axis.duplicates.mode='error'; layer {layer!r} has multiple "
                f"columns for sample {sample!r}: {list(columns)}"
            )
        return columns.iloc[:, 0]

@dataclass(frozen=True, slots=True)
class SumDuplicates:                            # mode = "aggregate"
    def combine_cells(self, cells: CellContributions) -> DenseLayerMatrix:
        ...                                     # the `if aggfunc == "sum"` arm, long.py:81-87
    def combine_columns(self, columns: pd.DataFrame, layer: str, sample: str) -> pd.Series:
        return columns.sum(axis=1)              # the wide.py:77 / :83 "aggregate" arms

@dataclass(frozen=True, slots=True)
class KeepFirstDuplicate:
    def combine_cells(self, cells: CellContributions) -> DenseLayerMatrix:
        ...                                     # the `else: # "first" non-null` arm, long.py:88-94
    def combine_columns(self, columns: pd.DataFrame, layer: str, sample: str) -> pd.Series:
        return columns.bfill(axis=1).iloc[:, 0]

type DuplicatePolicy = ErrorOnDuplicates | SumDuplicates | KeepFirstDuplicate


_BY_MODE: dict[DuplicateMode, DuplicatePolicy] = {      # stateless singletons
    "error":      ErrorOnDuplicates(),
    "aggregate":  SumDuplicates(),
    "keep_first": KeepFirstDuplicate(),
}                                                        # "keep_all_as_raw_table": absent on purpose


def policy_for(duplicates: Duplicates) -> DuplicatePolicy:
    """Turn the declared duplicate mode into the policy that carries it out."""
    policy = _BY_MODE.get(duplicates.mode)
    if policy is None:
        raise NotImplementedError(f"duplicates.mode={duplicates.mode!r} is not yet supported")
    return policy
```

**This is where `keep_all_as_raw_table` fails, and it is the whole point of having a factory.** The mode is
declared in `DuplicateMode` but has no policy class, so the missing entry in `_BY_MODE` *is* the
`NotImplementedError` — raised once, at construction time, naming the mode. Today the same error is raised from
inside `_aggfunc_for`, which runs partway through a conversion, after the file has been read and the
modifications applied.

It wires in through `make_axis_plan`, since `duplicates` lives under `rule.axis`:

```python
def make_axis_plan(axis: Axis, columns: Columns) -> AxisPlan:
    return AxisPlan(
        obs_keys=tuple(axis.obs_keys),
        var_keys=tuple(axis.var_keys),
        x_layer=axis.x_layer,
        duplicates=policy_for(axis.duplicates),
    )
```

and both converters then call `conversion.axis.duplicates.combine_cells(...)` /
`.combine_columns(...)`.

**No method returns `"sum"` or `"first"`.** An earlier draft of this remedy had `aggfunc() -> str`, which
recreated the exact defect the finding is about: a type converted into a string, passed across a boundary
as `aggfunc: str`, and branched on again at the far end. If a polymorphic method's return value is a token
the caller must dispatch on, the polymorphism has not happened — it has been moved one call deeper.
**Return the result, not the name of the operation.**

**`ErrorOnDuplicates` raises, and that is its whole implementation.** It has no aggregation because "error"
*means* combining is not permitted — so the error belongs inside `combine`, at the moment a second
contributor is found, not in a separate pre-pass. That collapses `_raise_on_duplicate_cells` and
`_raise_on_duplicate_features` (near-identical bodies in two modules) into one arm each.

**One behaviour change to declare, not hide.** The current pre-pass raises whenever duplicate *keys* exist,
even if the duplicate rows are all-null and would never have combined. Raising from inside `combine` fires
on duplicate *contributing values*. That is arguably the better rule — it is what the mode means — but it
is a change, and a refactor claiming to be behaviour-preserving must say so and cover it with a test.

`CellContributions` is the record `_build_matrix` already takes apart as six positional arguments
(`obs_codes, var_codes, values, key_ok, n_obs, n_var`); giving it a name is what lets `aggfunc: str` leave
the signature rather than be replaced by a policy parameter.

And the P1 shape resolves as a side effect: the six sites stop taking `ParseRule` to reach three levels
down, because the policy object is what they needed.

**This is the finding's actual result.** `ParseRule`'s 10 single-attribute sites are not ten judgement
calls about parameter width — several are P2 findings wearing a P1 costume. A function reaches for the
whole rule *because the thing it actually wants has no type yet*. Splitting the type gives it one, and the
wide parameter narrows on its own.

**So: run the detector top-down, and treat P1 hits as a queue of P2 candidates**, not as a list of
signatures to narrow. Narrowing `_aggfunc_for(rule)` to `_aggfunc_for(duplicates: Duplicates)` would have
been the cosmetic fix — six branch sites still there, the string still laundered through `aggfunc: str`,
and the `NotImplementedError` still buried in a chain.

---

## Not a finding — `MassTolerance`, and the test that decides it

**Shape:** P2.6 (rank 1). **Verdict: withdrawn — it is not one of the seven.** Recorded rather than
deleted, because the detector did fire here and *why it should not have* is the most portable thing in this
review. It sits with the other non-findings below, not in the numbered sequence.

`params/model.py:126` — one `MassTolerance` model carries a mode flag and two fields that belong to one
mode, with a validator rejecting all four illegal combinations. (`_Strict` is just APB's private pydantic
base — `class _Strict(BaseModel): model_config = ConfigDict(extra="forbid")` at `params/model.py:91`, the
same role `RuleModel` plays in `rules/`. Nothing about the finding turns on it; the two packages simply
spell the same base differently, one private and one not.)

```python
class MassTolerance(_Strict):
    value: NonNegativeFloat | None = None
    unit: ToleranceUnit | None = None
    mode: ToleranceMode
    label: str | None = None

    @model_validator(mode="after")
    def _validate_shape(self) -> MassTolerance:
        if self.mode == "absolute":
            if self.value is None:
                raise ValueError("absolute tolerance requires value")
            if self.unit is None:
                raise ValueError("absolute tolerance requires unit")
        else:
            if self.unit is not None:
                raise ValueError("automatic tolerance cannot define unit")
            if self.value is not None:
                raise ValueError("automatic tolerance cannot define numeric bounds")
        return self
```

Every message is the rank-1 tell verbatim: *"absolute tolerance requires value"*, *"automatic tolerance
cannot define unit"*. On the text test alone this is indistinguishable from F1, F2 and F4.

### Why it is not a finding

**The parse-boundary bound does not save it.** `MassTolerance` is populated from vendor files, so the reflex
is to file it under bound three. That is wrong: the boundary is `MassTolerance.parse(value: object)` at
`:157`, which is *correctly* where the foreign coercion happens. Past that line the type is APB's own.

**Bound four's second qualifier does.** `MassTolerance` is a DTO. `self.mode` is branched on in exactly one
place in the entire package — that validator. Nothing computes with a tolerance; `_legacy_value` serializes
it wholesale with `value.model_dump(exclude_none=True, mode="json")` and it goes to a CSV column. The
validator is validating a parsed vendor value, which is its job.

### The test, and it is mechanical

Writing the remedy is what proved it. The split is easy to write:

```python
class AbsoluteTolerance(_Strict):
    mode: Literal["absolute"] = "absolute"
    value: NonNegativeFloat                    # required — no validator needed to say so
    unit: ToleranceUnit                        # required
    label: str | None = None

class AutomaticTolerance(_Strict):
    mode: Literal["automatic"] = "automatic"   # no value, no unit — unrepresentable
    label: str | None = None

type MassTolerance = Annotated[AbsoluteTolerance | AutomaticTolerance, Field(discriminator="mode")]
```

**And then there is no method to put on either class.** Every other remedy in this review ends in a
behaviour — `coerce`, `convert`, `compute`, `explode`, `token_index`, `resolve`. Here the classes are
empty. That is the diagnostic:

> **If you cannot name the method that would go on the split types, you are looking at a DTO, and the
> validator is doing its job.** A missing polymorphism is missing *behaviour*. Two record shapes with no
> behaviour between them is a schema, and splitting it buys nothing but a second name.

This is a cheaper test than "is this the computational model?", because it needs no knowledge of the
architecture — just an attempt to finish the sentence *"and then each type would implement …"*.

**What is left is a small liability, not a finding.** `value: NonNegativeFloat | None` means the first
consumer that ever uses a tolerance numerically must re-check for `None`. The moment that consumer is
written, the split above becomes worth doing — and at that point there *will* be a method to name. Recorded
as a watch item; not work.

**One correction while checking this.** An earlier draft claimed `label` is never read. It is never read by
attribute access — `grep -rn "\.label\b" params/` returns nothing — but `model_dump` carries it into the
CSV, so it is live data, not a dead field. The wholesale-serialization path is exactly what makes this a
DTO.

---

## Non-findings — where the bounds fired

As important as the findings, because they show the detector discriminates rather than flagging everything.

- **`params/registry.py` — exemplary.** Twelve vendors in one `_REGISTRY: dict[str, ParseFn]` with a single
  `get_parser` lookup. Precisely the "single dispatch point at a factory" bound. This is what F6's remedy
  is trying to become.
- **`params/parsers/fragpipe.py` — not a violation.** Its `elif`s branch on *input text content*
  (`line.startswith("# DIA-NN version")`). That is "what happened", not "what something is".
- **`params/model.py` (29 `isinstance`) — not a violation.** Pydantic validators coercing `value: object`
  from vendor files into typed fields.
- **`adapters/anndata/summary_hdf5.py` (11 `isinstance`) — not a violation.** Narrowing untyped
  `h5py.Group`/`h5py.Dataset` nodes while walking an HDF5 tree.
- **43 of 47 validators — not violations.** See the fourth bound below.

### Bound three (confirmed): coercion at a parse boundary

> **Coercion at a parse boundary, where the incoming type is not yours to control, is not a missing
> polymorphism.** You cannot add a method to `str`, to `h5py.Group`, or to a dict from a vendor config.
> Polymorphism requires owning the types; where you do not own them, `isinstance` narrowing is correct and
> the branch belongs at the boundary that produces your own types.

Confirmed again this pass, and **sharpened by the withdrawn `MassTolerance` candidate**: the bound is
about *where the foreign value is*, not
about which package handles vendor data. `MassTolerance.parse(value: object)` is the boundary; everything
past it is APB's own type and gets no protection.

### Bound four (new): not every combination-rejecting validator is a discriminator

P2.6 as written in step 1 — *"a validator that rejects combinations of fields"* — flags all 47 validators
in APB. It should flag four. The missing qualifier:

> **The shape is a validator in which one field is a *mode, kind, or strategy* and the others are that
> mode's payload.** A validator enforcing *ordering* (`min > max`), *uniqueness* (`species_mapper values
> must be unique`), *set equality* (`mapper values must equal ratio keys`), or *non-emptiness* is ordinary
> cross-field validation and correct. It rejects a bad *value*, not an impossible *type*.

Worked contrast, both from this codebase:

| Validator | Verdict |
| --- | --- |
| `Layer._validate_encoding` — *"missing_values is only valid for numeric layers"* | **Finding.** `encoding_mode` is a kind; `missing_values` is one kind's payload. |
| `Parameters._validate_ranges` — *"min_precursor_charge must not exceed max"* | **Not a finding.** No field is a kind. Two values in a bad relation. |
| `ModuleSettings._validate_design` — *"species_mapper values must be unique"* | **Not a finding.** A collection-level invariant. |

**The tell in one sentence:** if the error message reads *"X is only valid when Y is Z"*, Y is a type
discriminator. If it reads *"X must not exceed Y"*, it is validation. This is a mechanical test on the
message text and it separates the four findings from the forty-three cleanly.

**Second qualifier, from the remedy architecture: *where* the validated type sits decides the verdict.**
A combination-rejecting validator on a **document schema** — a type whose only job is to describe a file —
is correct and stays. Somebody can write that combination in a TOML file and must be told. The same
validator becomes a missing polymorphism only when the validated type is **also the computational model**,
because then the combination it polices is visible to every consumer downstream, and each one re-derives
it. All four findings here are the second case, and they stop being findings the moment a factory stands
between the document and the computation — not because the validator changed, but because it no longer
guards anything that computes.

**This is the payoff of running the review before writing the skill.** Bound four was not visible from the
principle alone, and without it the rank-1 shape — the highest-yield shape in this codebase — has a 91%
false-positive rate and the review is worthless.

---

## What carries back into step 1

The review changed the instrument. Four amendments belong in
[skill_principle.md](skill_principle.md) before step 3 is rewritten:

1. **New violation shape — the split that stopped halfway.** *A discriminated union of your own types
   where consumers still `isinstance` / compare the discriminator.* This is the most common shape in APB
   (F5: three unions, nine consumer sites) and step 1 does not name it. It matters because it is the shape
   an agent produces when told "split the type" without being told what happens next.
2. **P2.6 needs bound four** — one field is a *kind*, the others its payload. Without it the rank-1 shape
   flags every validator in the codebase.
3. **The remedy is a method. Move the code to the type; do not route around the current layout.** An
   earlier draft of this review argued that four findings had to use `functools.singledispatch` because
   `converters/` imports `rules/` and a method would cycle. That reasoning was wrong twice over, and the
   error is worth recording because it is exactly what an agent will produce:
   - **It treated the existing module layout as a constraint.** This is a refactor. If an operation is a
     type's behaviour, the type and the operation belong in one module — and moving them there is part of
     the remedy, not an obstacle to it. A cycle is a signal that code is in the wrong file, not that the
     design is wrong.
   - **It invented a rule.** "`rules/` must not import pandas" appears nowhere in AGENTS.md, which forbids
     computation importing **adapters, `anndata`, `mudata`** — pandas is the computation layer's ordinary
     currency. `rules/` merely happens not to import it today; the review promoted an observation into a
     prohibition and then reasoned from it.

   Every remedy in this document is now a method on the type. `singledispatch` remains a legitimate
   encoding of the same polymorphism — reach for it when the operation genuinely is not the type's
   behaviour, e.g. a second backend wanting a different conversion of the same rule. That is a reason to
   revisit if it happens, not to pre-empt.
4. **Persistence schemas are not the computational model — and this is where the method goes.** The
   correction above is only half the story. A first draft put the behaviour on APB's *pydantic* models,
   which is the deeper version of the same error: pydantic is how rules are **stored**, and hanging
   conversion logic on it fuses the file format with the computation. That is the rule AGENTS.md already
   states for AnnData, applied one level up. The instrument needs to ask, after "is the branch on what
   something *is*?", a second question: **is the type I am about to put this method on a description of
   stored data?** If yes, the behaviour belongs on a runtime type a factory produces from it — see
   [The remedy architecture](#the-remedy-architecture--stated-once-used-by-every-finding-below).

   This is also the mechanical explanation for shape 1 above. An agent that splits a pydantic union and
   then finds nowhere legitimate to put the method **stops at the split** — which is exactly the state
   three of APB's unions are in.

## What carries into the skill

1. **The worked example is F5's `ModificationLocation`** — four functions, one question, APB's own types
   in the same file, and a three-line fix. Real, Python, from this codebase.
2. **The rank-1 trigger is the error message**: *"X is only valid when Y is Z"* → you have a discriminator,
   not a validator. Mechanical, cheap, and it fires at the moment the developer is writing the validator —
   which is before the branch set has spread to three modules.
3. **The counter-example is `params/registry.py`** — a dispatch dict is the destination, not a defect.
4. **Four bounds, not two.** Guard clauses; foreign-type coercion; ordering/uniqueness validators; and
   two arms that will never grow.
5. **Show the identity value, not only the split.** F2's `sample_name_cleanup` is the smallest complete
   example: the branch body was already `return samples`, so the whole remedy is moving that line onto
   `NoCleanup.apply`. The split is not the point — it is where the identity behaviour goes.
6. **Ask whether the type is a storage schema before putting a method on it.** If it is — pydantic model,
   TOML/JSON shape, a row of a table — the behaviour goes on a runtime type built from it, and the factory
   is the one legitimate place a tag is read. Without this the skill teaches an agent to fuse the file
   format with the computation, which is how APB arrived at six of these seven findings.
7. **Teach that the remedy may move code between modules, and that this is allowed.** The failure mode is
   an agent that keeps every file where it is, discovers the method would cycle, and reaches for a
   mechanism that routes around the layout — or worse, declines the remedy and leaves the branch. The
   instruction has to be explicit: *the type and its behaviour belong together; relocating them is part of
   the fix.* This review made that mistake itself before it was caught.
8. **Do not replace `| None` with `| NoThing`.** The absent case is a **member of the union**, not a
   second union wrapped around it. `Fragments | NoFragments` is `is None` under a new name — three members
   spelled as two, and every consumer still discriminating. APB's `NoValuePattern` shows the right form.
9. **P1 stays advisory, and P1 hits are a queue of P2 candidates.** F7 is the proof: working the clearest
   "passes the whole record for one field" site turned up an evidence-class P2.3 finding underneath it —
   three functions branching on `duplicates.mode`. A function reaches for the whole record *because the
   thing it actually wants has no type yet*. Narrowing the signature is the cosmetic fix; giving the thing
   a type narrows it for free. Teach the P2 question first and most P1 hits answer themselves.
