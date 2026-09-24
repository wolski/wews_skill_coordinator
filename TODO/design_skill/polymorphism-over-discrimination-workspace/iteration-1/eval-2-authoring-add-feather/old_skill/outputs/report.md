# Adding `.feather` support to APB

**Short answer:** yes, `apb/src/anndata_proteomics/readers/` is the right folder — nothing outside it
needs to change. But the format is not one place today: the extension case set is spelled out in
**three functions** in `readers/dispatch.py`, and **the one the CLI actually uses is not
`read_table`**. Adding feather to `EXTENSION_TO_READER` alone will make the reader tests pass and
leave `apb convert` failing.

Nothing was modified. This is the written answer only.

---

## 1. What feather needs today, exactly

All three sites are in `/Users/wolski/projects/anndata_bridge/apb/src/anndata_proteomics/readers/dispatch.py`.

| # | Site | What feather needs there |
| --- | --- | --- |
| 1 | `EXTENSION_TO_READER` (line 27) | `".feather": read_feather` — plus a new `read_feather` in `tabular.py` |
| 2 | `read_table_preserving_strings` (line 66) | the `.parquet` bypass has to become `if suffix in {".parquet", ".feather"}` — feather carries a physical schema, so `string_columns` is a no-op exactly as for parquet |
| 3 | `read_table_columns` (line 79) | a fourth arm: a schema-only read, the feather counterpart of `pq.read_schema` |

**The trap.** `read_table` has *no production caller at all* — I grepped `apb/src` and
`apb_studio/src`; the only `read_table(` outside its own definition is in `tests/`. The conversion
path is sites 2 and 3:

- `scripts/cli.py:204` → `read_table_columns(data)` (header recognition, runs first)
- `scripts/cli.py:473` → `read_table_preserving_strings(data_path, string_sources)` (the actual read)
- `apb_studio` also calls `read_table_columns` (`capabilities.py:199`, `testdata.py:132`)

So a feather file added only to `EXTENSION_TO_READER` dies at `UnknownFormat` during recognition,
before any of the new code runs. Nothing in the type checker tells you sites 2 and 3 exist.

**One behavioural consequence to be aware of, not a bug.** Feather inherits parquet's contract: the
rule-derived `string_columns` set is ignored, because the file's physical schema is authoritative.
If your collaborator writes an identifier column as `int64`, APB will not restore it to text at read
time — the logical contract is applied later during conversion. That is the intended design (see the
`read_table_preserving_strings` docstring), but it is worth telling the collaborator, since with a
`.tsv` the same column would have been protected.

---

## 2. Why there are three sites, and what I would do instead

Every one of those three functions decides what to do by asking **which format is this** — a format
discriminator, not a check on what happened. Same case set, branched in three functions, two of them
by hand: `read_table` uses a dict, `read_table_preserving_strings` uses an `if` plus a *second,
smaller* dict, and `read_table_columns` is a four-arm `if`/`elif` chain that re-derives the
delimiters `read_table` already knows.

The evidence that this is worth restructuring is moderate, and I want to be straight about that: it
is three call sites in **one module** — a dispatch module is *supposed* to contain one dispatch
point. A single lookup at a factory is the cure, not the disease. What makes it actionable is that
the same case set appears three times *past* that lookup, the registries have already drifted apart
(4 keys vs. 3 keys vs. 4 hand-written arms), and you are about to add a fourth format — which is the
cheapest moment there will ever be to fix it, and the moment at which the three-place edit is most
likely to be done in two places.

### The shape I would move to

Make the format a type with the three operations on it, and let a single registry map suffix → format.
The question each arm answers is nameable three ways, which is the test for whether this is real
polymorphism and not a split for its own sake:

- *how do I get this file's column names without reading rows?* → `column_names(path)`
- *how do I get a frame typed the way the file itself types it?* → `read(path)`
- *how do I get a frame with these columns kept as exact text?* → `read_preserving_strings(path, cols)`

All three already have callers; none is invented to justify the split.

```python
# readers/dispatch.py — sketch, not a patch

class TabularFormat(Protocol):
    def read(self, path: Path) -> pd.DataFrame: ...
    def read_preserving_strings(self, path: Path, string_columns: frozenset[str]) -> pd.DataFrame: ...
    def column_names(self, path: Path) -> list[str]: ...


@dataclass(frozen=True, slots=True)
class FixedDelimiterText:
    delimiter: str
    def read(self, path): return _read_delimited(path, self.delimiter)
    def read_preserving_strings(self, path, string_columns):
        return _read_delimited_preserving_strings(path, self.delimiter, string_columns)
    def column_names(self, path): return read_delimited_columns(path, delimiter=self.delimiter)


@dataclass(frozen=True, slots=True)
class SniffedDelimiterText:
    """Delimiter is a property of the file's content, not of the extension."""
    def read(self, path): return _read_delimited(path, detect_text_delimiter(path))
    ...  # same three operations, resolving the delimiter per path


@dataclass(frozen=True, slots=True)
class ParquetFormat:
    def read(self, path): return pd.read_parquet(path)
    def read_preserving_strings(self, path, string_columns): return pd.read_parquet(path)
    def column_names(self, path): return list(pq.read_schema(path).names)


@dataclass(frozen=True, slots=True)
class FeatherFormat:                                   # the whole feature, in one class
    def read(self, path): return pd.read_feather(path)
    def read_preserving_strings(self, path, string_columns): return pd.read_feather(path)
    def column_names(self, path): return list(pa.ipc.open_file(path).schema.names)


_BY_SUFFIX: dict[str, TabularFormat] = {
    ".csv": FixedDelimiterText(","),
    ".tsv": FixedDelimiterText("\t"),
    ".txt": SniffedDelimiterText(),
    ".parquet": ParquetFormat(),
    ".feather": FeatherFormat(),
}


def format_for_path(path: Path) -> TabularFormat:
    """The one place a file extension is read."""
    fmt = _BY_SUFFIX.get(path.suffix.lower())
    if fmt is None:
        raise UnknownFormat(
            f"unsupported extension {path.suffix!r} for {path}; known: {sorted(_BY_SUFFIX)}"
        )
    return fmt
```

The three public functions **keep their exact signatures** — there are ~30 call sites across the
tests, the CLI and `apb_studio`, and none of them should move — and each becomes one line:

```python
def read_table(path: Path) -> pd.DataFrame:
    return format_for_path(path).read(path)

def read_table_preserving_strings(path: Path, string_columns: frozenset[str]) -> pd.DataFrame:
    return format_for_path(path).read_preserving_strings(path, string_columns)

def read_table_columns(path: Path) -> list[str]:
    return format_for_path(path).column_names(path)
```

Both `if suffix == ".parquet"` bypasses and the four-arm `elif` chain disappear, the two registries
collapse into one, and the `UnknownFormat` message becomes correct by construction in all three
functions instead of by the coincidence that `EXTENSION_TO_READER` happened to be the superset.
After this, **feather is one class plus one registry line**, and Pyright forces the class to
implement all three operations — which is the actual win: the compiler, not a grep, tells the next
person about site 2 and site 3.

Placement notes: keep this in `readers/`. `tabular.py` stays exactly as it is — it holds the
mechanics (delimiter sniffing, decimal detection, the pandas calls) and gains only `read_feather`;
the classes go in `dispatch.py`, which is 94 lines and is the natural home. Do **not** create a new
module for four small classes; `readers` is a leaf layer in `.importlinter`, so nothing here creates
a layering or cycle problem.

### Things I deliberately did *not* flag

- `FixedDelimiterText.delimiter` holding `","` is **not** a stringly-typed dispatch. Nothing compares
  it against literals; it is passed to `pd.read_csv(sep=...)` as a value. Leave it.
- `detect_text_delimiter` and `detect_decimal_separator` in `tabular.py` are content inference —
  *what this file contains*, not *what kind of thing it is*. Correct as written; do not touch them.
- `annotation/loader.py:62-71` has its own extension chain (`.toml` / `.csv` / `.tsv`). Different
  case set, different concern (sample-annotation input), one site. Out of scope — do not unify it
  with this registry.

---

## 3. Feather specifics worth knowing before you write it

- **No dependency change.** `pyarrow` is already a direct dependency (`pyproject.toml:24`), and
  `pandas.read_feather` is pyarrow-backed. Verified in the apb env: pyarrow 25.0.0, pandas 3.0.5.
- **Schema-only header read** (the `read_table_columns` arm): use
  `pyarrow.ipc.open_file(path).schema.names`. Verified working. Do **not** use
  `pyarrow.feather.read_table` — it is deprecated as of pyarrow 24.0.0, and the deprecation warning
  itself points at `pyarrow.ipc.open_file`.
- **The one real caveat: Feather V1.** `pa.ipc.open_file` raises `ArrowInvalid` on a V1 file (I
  verified this); `pd.read_feather` reads both versions fine. V1 is still writable from R
  (`arrow::write_feather(version = 1)`) and from the old `feather` package, so a collaborator file
  is not guaranteed to be V2. My recommendation: write the IPC schema read, and if a V1 file ever
  actually turns up, change `column_names` to `list(pd.read_feather(path).columns)` — one behaviour
  that is correct for both versions at the cost of a full read. Do not add `FeatherV1` /
  `FeatherV2` classes or a try/except version branch speculatively; you have no V1 file today.
- `.arrow` / `.ipc` are the same container under other names. If those show up later it is one more
  registry line pointing at the same instance — no new class.

---

## 4. Nothing else in APB needs to know

I checked the places that plausibly encode "which formats are supported":

- **Parsing rules:** vendor rule documents match on **column headers**, not filenames or extensions
  (`converters/recognize.py`, `pipeline._rule_matches_headers`). No `rules.json` change, no schema
  change. If the feather file carries a known vendor's columns, recognition works the moment the
  reader does.
- **CLI:** `scripts/cli.py` derives only the *output* suffix (`.h5ad` / `.h5mu`); it never validates
  the input extension. No change.
- **`apb_studio`:** consumes `read_table_columns` and gets feather for free.

### To update alongside the code

- `tests/test_readers_dispatch.py` and `tests/test_readers_tabular.py` — mirror the existing parquet
  cases, including `test_rule_aware_parquet_read_defers_to_physical_schema` (the feather twin of
  that test is the one that pins the `string_columns` no-op contract).
- `docs/parsing_architecture.md:296-305` — the mermaid dispatch figure lists `.csv / .tsv / .parquet`
  and would become wrong.
- `CHANGES.md` — one dated line, per the workspace convention.
- Run `uv run pre-commit run carpet-scan --hook-stage manual --all-files` afterwards and report what
  moved: the restructure adds four classes to `dispatch.py` and removes two branch chains, so the
  numbers will shift. Read it, do not act on it.

---

## 5. If you want the smallest possible change instead

Perfectly defensible if feather is a one-off favour for one collaborator rather than a format APB
now supports. In that case: add `read_feather` to `tabular.py`, add the `EXTENSION_TO_READER` entry,
widen the `.parquet` condition at `dispatch.py:66` to a two-element set, and add the fourth arm at
`dispatch.py:79`. Three sites, ~15 lines, no restructure. Just do all three — site 3 is the one that
runs first, and skipping it fails before anything you wrote gets a chance to run.
