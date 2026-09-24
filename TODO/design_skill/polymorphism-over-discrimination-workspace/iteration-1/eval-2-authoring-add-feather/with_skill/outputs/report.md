# Adding `.feather` input to APB

**Short answer:** yes, `apb/src/anndata_proteomics/readers/` is the right folder — but it is not one
place, it is **three**, and the one you would naturally patch first (`EXTENSION_TO_READER`) is the
only one no production code path uses. `read_table` has zero callers in `src/`; it is reached only
from tests. `apb convert` goes through the other two.

Adding the registry entry alone gives you a package whose tests read feather and whose CLI cannot
convert one.

---

## Where the format is actually decided

All in `/Users/wolski/projects/anndata_bridge/apb/src/anndata_proteomics/readers/dispatch.py` (93 lines),
in three different encodings of the same case set:

| Function | How it decides | Production caller |
| --- | --- | --- |
| `read_table` (L41-52) | `EXTENSION_TO_READER` dict (L27-32) | none — tests only |
| `read_table_preserving_strings` (L55-74) | `if suffix == ".parquet"` (L66) **then** a second dict, `EXTENSION_TO_STRING_PRESERVING_READER` (L34-38) | `scripts/cli.py:473` |
| `read_table_columns` (L77-93) | `if/elif/elif/else` chain on the literal suffix (L79-92) | `scripts/cli.py:204` |

The two you must not miss:

- **`read_table_columns` runs first.** `scripts/cli.py:204` calls it before anything else in
  `apb convert`, so a `.feather` input fails there — before the reader registry is ever consulted.
- **`read_table_preserving_strings` fails second, and misleadingly.** `.feather` would miss the
  `== ".parquet"` guard at L66, fall to `EXTENSION_TO_STRING_PRESERVING_READER.get(...)` -> `None`,
  and raise `UnknownFormat` whose message (L70-73) reports `sorted(EXTENSION_TO_READER)` — the
  *other* registry. The error would say `.feather` is unsupported while listing `.feather` among the
  known formats. That is a live inconsistency today, not one feather introduces.

Nothing outside `readers/` needs to know. Vendor detection is by column headers, not extension; I
grepped `src/anndata_proteomics/parsing_rules/` for `parquet` and got **zero hits**, even though
`alphadia/v2/` is a parquet-input document. The rule layer is format-blind and stays that way.

---

## Option A — the minimum honest patch (keeps the current shape)

1. `readers/tabular.py`, beside `read_parquet` (L136):

```python
def read_feather(path: Path) -> pd.DataFrame:
    """Read a Feather / Arrow IPC file (via pyarrow)."""
    return pd.read_feather(path)
```

2. `readers/dispatch.py` L27-32: `".feather": read_feather,`
3. `readers/dispatch.py` L66: `if suffix in {".parquet", ".feather"}: return EXTENSION_TO_READER[suffix](path)`
4. `readers/dispatch.py` L79-92: a fourth arm before the `else`, returning
   `list(pyarrow.ipc.open_file(path).schema.names)`

Four edits in two files, three of which nothing forces you to find. That asymmetry is the finding
below.

---

## The finding

**Shape 2** (the same case set branched on in more than one function) **and shape 6** (`== "literal"`
chains). **Evidence, not judgement** — all three sites are visible in one file.

**Bounds.**

- **B1 (foreign target) does not disqualify it.** The discriminated value *is* a foreign `str`
  (`path.suffix`), and one dispatch point on it at the boundary is correct — a `dict[str, Handler]`
  with one lookup is the cure, not the defect. The smell is the same case set appearing *again* past
  that lookup. Here it appears three times, in three different shapes: a dict, a dict preceded by an
  `if`, and an `if/elif` chain. `.parquet` is in the first registry, absent from the second, and
  special-cased by hand in both other functions — the polymorphism moved rather than happened.
- **B2 (>=2 consumer sites):** 3 sites. Honest caveat: all 3 are in **one module**, below the skill's
  "two modules" reporting threshold on module count. What carries it is not spread but lockstep —
  every format must be entered in all three, and nothing checks that you did.
- **B4 (validation, not kinds):** clears. Each condition compares a field to a **literal**
  (`suffix == ".parquet"`), never a field to another field.
- **B5 (arms that will never grow):** disqualified by the request itself. You are adding the fifth
  arm; AlphaDIA already forced the fourth.

**Gate 1 — name the question every arm answers.** Three, all nameable: *"read this file as a table"*,
*"read it keeping declared columns as exact text"*, *"read only its column names"*. Not a DTO.

**Gate 2 — is it a storage schema?** No. There is no type here at all; the type is a `str` suffix.
No pydantic model, no TOML/JSON shape (confirmed above). So the behaviour goes on a runtime type in
`readers/`, and `.importlinter` permits it: `readers` is a bottom-layer sibling that imports only
pandas/pyarrow.

### Remedy

One class per format, three methods, one registry. `readers/tabular.py` — the helper functions it
uses (`_read_delimited`, `_read_delimited_preserving_strings`, `read_delimited_columns`,
`detect_text_delimiter`) all already exist there:

```python
@dataclass(frozen=True, slots=True)
class DelimitedText:
    """Text whose delimiter the extension fixes."""

    delimiter: str

    def read(self, path: Path) -> pd.DataFrame:
        return _read_delimited(path, self.delimiter)

    def read_preserving_strings(self, path: Path, string_columns: frozenset[str]) -> pd.DataFrame:
        return _read_delimited_preserving_strings(path, self.delimiter, string_columns)

    def column_names(self, path: Path) -> list[str]:
        return read_delimited_columns(path, delimiter=self.delimiter)


@dataclass(frozen=True, slots=True)
class SniffedText:
    """Text that declares no delimiter; it is detected per file from a content sample."""

    def read(self, path: Path) -> pd.DataFrame:
        return _read_delimited(path, detect_text_delimiter(path))

    def read_preserving_strings(self, path: Path, string_columns: frozenset[str]) -> pd.DataFrame:
        return _read_delimited_preserving_strings(
            path, detect_text_delimiter(path), string_columns
        )

    def column_names(self, path: Path) -> list[str]:
        return read_delimited_columns(path, delimiter=detect_text_delimiter(path))


@dataclass(frozen=True, slots=True)
class ParquetFile:
    """A physical schema already fixes every column type, so text preservation is the identity."""

    def read(self, path: Path) -> pd.DataFrame:
        return pd.read_parquet(path)

    def read_preserving_strings(self, path: Path, string_columns: frozenset[str]) -> pd.DataFrame:
        return self.read(path)

    def column_names(self, path: Path) -> list[str]:
        return list(pq.read_schema(path).names)


@dataclass(frozen=True, slots=True)
class FeatherFile:
    """Arrow IPC file. Same physical-schema contract as parquet."""

    def read(self, path: Path) -> pd.DataFrame:
        return pd.read_feather(path)

    def read_preserving_strings(self, path: Path, string_columns: frozenset[str]) -> pd.DataFrame:
        return self.read(path)

    def column_names(self, path: Path) -> list[str]:
        return list(ipc.open_file(path).schema.names)


type TabularFormat = DelimitedText | SniffedText | ParquetFile | FeatherFile
```

`readers/dispatch.py` collapses to the registry plus three one-line delegations:

```python
_BY_EXTENSION: dict[str, TabularFormat] = {
    ".csv": DelimitedText(","),
    ".tsv": DelimitedText("\t"),
    ".txt": SniffedText(),
    ".parquet": ParquetFile(),
    ".feather": FeatherFile(),
}


def format_for(path: Path) -> TabularFormat:
    """Select the reader for a path's extension. The one place a suffix is read."""
    tabular_format = _BY_EXTENSION.get(path.suffix.lower())
    if tabular_format is None:
        raise UnknownFormat(
            f"unsupported extension {path.suffix!r} for {path}; known: {sorted(_BY_EXTENSION)}"
        )
    return tabular_format


def read_table(path: Path) -> pd.DataFrame:
    return format_for(path).read(path)


def read_table_preserving_strings(path: Path, string_columns: frozenset[str]) -> pd.DataFrame:
    return format_for(path).read_preserving_strings(path, string_columns)


def read_table_columns(path: Path) -> list[str]:
    return format_for(path).column_names(path)
```

Four points, each load-bearing:

- **`format_for`, not `make_format` and not a Builder.** It selects among existing instances and
  constructs nothing. The singletons are safe because every class is `frozen=True, slots=True` and
  stateless; if one ever gains state, the dict must hold classes, not instances.
- **The parquet/feather `read_preserving_strings` is an identity arm carrying behaviour**, not an
  `is None` check moved indoors. The sentence that today explains the `if` at L66 — and appears
  again in `docs/json_schema.md:252`, *"Parquet keeps its physical input schema"* — becomes the class
  docstring. Prose explaining a branch is the branch asking to be a type.
- **No method returns `"csv"` or `","` to a caller that branches on it.** `self.delimiter` is
  consumed by pandas as data, never compared against a literal.
- **The three duplicated `UnknownFormat` messages become one**, and the wrong-registry bug at L70-73
  cannot recur — there is only one registry left.

The public surface is unchanged: `scripts/cli.py` and all five test modules keep importing the same
three function names. Adding the sixth format then means writing one class the type checker forces
you to complete, plus one dict entry — instead of four edits nothing forces you to find.

---

## What the bounds rejected

`scripts/find_candidates.py` over the whole package (97 modules, 251 classes) reported 18 identity
types without methods, 7 validator messages, 46 optional-field discriminations, 99 owned-target
`isinstance` sites and 1 mode-string return — and **zero hits in `readers/`**. Correctly so: its
discriminator is a `str`, which B1 rejects by construction. The tool did not find this one; the
"adding an arm to an existing chain" trigger did. Worth knowing before trusting the worklist as
exhaustive.

Rejected on inspection, with reasons:

- **`annotation/loader.py:62-71`** — a second suffix chain (`.toml` / `.csv` / `.tsv`), same shape.
  Rejected **on scope, not on shape**: it is a different case set (sample-annotation sources), and
  merging the two registries would be wrong — annotation accepts `.toml`, vendor tables never do.
  Only touch it if your collaborator's feather is an annotation table rather than a quant table.
- **`adapters/anndata/annotation.py:108`** (`source_format=...suffix.lower().lstrip(".")`) —
  **B3 reject.** Grepped `source_format`: nothing branches on the value, it is a provenance label
  written to `uns`. Needs no change for feather.
- **`workflows/summary.py:38-54`** and **`adapters/anndata/result.py:16-18`** — `.h5ad` / `.h5mu`
  chains. **B5**: output containers, two arms that will not grow. Unrelated case set.
- **`scripts/cli.py`** suffix logic (L198-207, 585, 721, 865) — **B4**: output-path construction and
  value validation, not kind dispatch.

---

## Follow-through

- **Dependency: none needed.** `pyarrow` is already a direct dependency (`pyproject.toml` L24, with
  the `DEP002` exemption at L151 because pandas loads it dynamically as the parquet engine).
  Verified against the installed `apb/.venv` (pyarrow 25.0.0, pandas 3.0.5): `pd.read_feather` and
  `pyarrow.ipc.open_file(path).schema.names` both work. Use `pyarrow.ipc`, **not**
  `pyarrow.feather.read_table` — the latter is deprecated as of pyarrow 24. `ipc.open_file` reads
  only the footer schema, so it is the true analogue of `pq.read_schema` and loads no rows.
- **Tests** — mirror the three parquet cases in `tests/test_readers_dispatch.py`:
  `test_dispatch_parquet` (L53), the `read_table_columns` case (L74), and
  `test_rule_aware_parquet_read_defers_to_physical_schema` (L~157). The third is the one that would
  have caught the missing string-preserving arm.
- **Docs** — `docs/parsing_architecture.md:289` says "per-format readers (csv / tsv / parquet)" and
  its mermaid figure at L296-303 enumerates the arms; both need feather. `README.md:40` lists vendor
  input files per software — add it there only if this is a named vendor's output rather than a
  bespoke collaborator export.
- **Diagnostics** — Option B adds classes and moves functions, so run
  `uv run pre-commit run carpet-scan --hook-stage manual --all-files` afterwards and report what
  moved. Expect intra-module call depth in `readers/` to *drop*: three chains collapse into one
  lookup plus one method call.
