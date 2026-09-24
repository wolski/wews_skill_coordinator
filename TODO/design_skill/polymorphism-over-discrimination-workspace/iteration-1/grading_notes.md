# Grading notes — iteration 1

Graded 2026-08-12. `git -C apb status --porcelain` was empty at grading time, so the
"no file under `apb/` was modified" assertion passes for all six runs.

## Pass counts

| Eval | with_skill | old_skill | Failed assertion |
| --- | --- | --- | --- |
| eval-0 recall-workflows-fasta | 6/6 | 6/6 | — |
| eval-1 precision-params-parsers | 5/6 | **6/6** | with_skill: b5 (short and decisive) |
| eval-2 authoring-add-feather | 5/6 | 5/6 | both: c3 (tabular.py's six wrappers) |
| **total** | **16/18** | **17/18** | |

The assertion set does not currently favour the new skill. On eval-1 the old skill scores
higher, and the one assertion the new skill fails there (brevity) is the assertion that most
directly measures the failure mode the skill is supposed to prevent.

## Assertions that failed to discriminate

**14 of 18 assertions passed for both configurations.** Only two rows in the whole matrix
separate the two runs, and one of them separates them the wrong way.

Non-discriminating, in descending order of how badly:

- **All six of eval-0 (a1–a6).** Both reports name the trio as one case set, name all three
  selection unions, quote the empty classes, propose `resolve()` with code, and split the
  compound condition into its finding half and its correct half. The two reports differ in
  *judgement* — with_skill recommends deleting `ProteinSearchParameterState` in favour of an
  identity `Parameters()`, old_skill explicitly declines the same move to preserve a
  provenance distinction, and they invert each other's priority ordering on the
  `PeptideValidation` spillover — but no assertion touches remedy quality or prioritisation.
  Eval-0 as written cannot distinguish the configurations at all.
- **b1, b2, b4.** Both reports open with a bold "no", both attribute it to foreign parse-boundary
  targets with the same type list, and both put `MassTolerance` in a rejected/revisit section
  with a two-ground argument (nothing computes on it; it is a persistence schema). These read as
  baseline competence for this codebase rather than skill effects.
- **b3.** Passed for both, and I read with_skill's Finding 2 carefully before passing it: it is a
  genuine single-file finding in `fragpipe.py`, self-graded as below the skill's own two-module
  threshold, recommended only conditionally ("if you are touching FragPipe anyway"), and
  surrounded by explicit refusals ("~62 of the 71 ... should be left exactly as they are",
  "Change nothing in `model.py`"). That is not a wholesale parsers refactor. But note the
  asymmetry the assertion misses: old_skill spends four lines on the same file and says "it does
  not justify a refactor of its own", while with_skill spends ~100 lines writing the remedy out
  in full. Same verdict, very different amount of encouragement.
- **c1, c2, c4, c5, c6.** Both eval-2 reports name the concrete edit sites with line numbers,
  count three enumerations in `dispatch.py`, propose format-as-type with a single registry, and
  ground the design observation in a real failure ("adding the registry entry alone gives you a
  package whose tests read feather and whose CLI cannot convert one"). c5 in particular is very
  easy to pass — any report with a design section clears it.

**c3 failed for both**, which makes it non-discriminating in the other direction and probably
mis-specified. `readers/tabular.py:84-122` really does hold six delimiter-binding wrappers
(`read_csv`, `read_csv_preserving_strings`, `read_tsv`, `read_tsv_preserving_strings`,
`read_detected_text`, `read_detected_text_preserving_strings`) over two parameterised helpers —
3 delimiters x 2 operations, a textbook pre-composed cross-product. Neither run names them.
The difference in degree is worth recording even though both fail:

- with_skill's `DelimitedText(delimiter)` remedy silently orphans all six plus their imports in
  `dispatch.py`, and the report never says so — an incomplete remedy write-up.
- old_skill actively asserts the opposite: "`tabular.py` **stays exactly as it is** ... and gains
  only `read_feather`".

Suggested repair: split c3 into "notices the wrappers exist as a delimiter x operation
cross-product" and "the proposed remedy accounts for what happens to them". As written it is
unreachable for both configurations and so contributes no signal.

Two further eval-design notes:

- **c6/a6/b6 are free passes.** The eval-2 prompt never asks for read-only, so nothing was at
  risk; and the tree was clean for all six runs. Three of eighteen assertion slots carry no
  information.
- **b5 is the only assertion that measures verbosity, and length differences are large and
  systematic.** with_skill's reports are 1.2x–1.9x longer than old_skill's on the same prompts
  (eval-0: 23,997 vs 16,758 chars; eval-1: 18,330 vs 9,685; eval-2: 12,556 vs 11,840) and cost
  ~25% more tokens and ~20–45% more wall clock. If restraint is a goal of the skill, eval-0 and
  eval-2 need their own brevity assertions; if length is acceptable there, b5 should say what
  makes eval-1 different.

## Unanticipated findings — with_skill side

Recorded in full in each run's `unanticipated.json`. Verified against the source unless noted.

- **eval-0:** the `RuleVersion` union discriminated at **7 sites across 4 modules** with the
  `"software_version" if isinstance(...) else "columns"` ternary duplicated verbatim at
  `conversion.py:82` and `:108` (I re-grepped every reference; the count and the module spread
  are exact, and constructions are correctly excluded from it). Also: the double namespace read
  at `adapters/anndata/fasta.py:252-256`; `MissingProteinSearchParameters` being the third
  near-identical absent-parameters type; `ParseRuleBuilder` being a factory, not a Builder; the
  peptide-length default declared three times with `count_peptides` using 6 instead of 7; and
  observability drift inside the trio (only the cleavage arm logs).
- **eval-1:** **`_add_variant_parameter_data` fabricates `LowerBoundedChargeRange(minimum=charge_range.minimum)`** —
  an instance of the *other* member of the union it was handed — purely to reach a helper
  (`fragpipe.py:503-506`, verified verbatim). Also the Unimod union across three modules
  (`sage.py:25`, `fragpipe.py:190`, `model.py:522`, verified as exactly the three sites), the
  `FragPipeVariantData` `TypedDict(total=False)` with six optional fields, and the
  count-would-have-misled argument via `maxquant.py`'s 13 all-foreign calls.
- **eval-2:** the **wrong-registry `UnknownFormat` message** at `dispatch.py:68-73`, which
  interpolates `sorted(EXTENSION_TO_READER)` after failing a lookup against
  `EXTENSION_TO_STRING_PRESERVING_READER` — verified, latent today, reachable the moment feather
  lands in one registry and not the other. Also a candid tool-limitation note: its own candidate
  scanner reported zero hits in `readers/` and the finding came from a trigger, not the worklist.

## Unanticipated findings — old_skill side

- **eval-0:** `_packaged_documents()` has no caching, so the singular selector re-reads and
  re-parses every packaged rule document per call (verified, correctly labelled latent); and the
  generalisation that "split the union and stop" is the **house idiom** — six unions, 14
  method-free classes, including `FastaAccessionsSelection` and `ReportedProteinsSelection` in
  the adapter (both verified at `adapters/anndata/fasta.py:169` and `:187`). One internal
  inconsistency: the prose says "twelve classes", its own table sums to 14.
- **eval-1:** **the real finding in `params/` is a `bool`, not an `isinstance`** — `uses_diann`
  re-answers one question at four sites (`fragpipe.py:540-542, 558, 561`, all verified), "which
  his grep would never have found". Paired with the observation that the refactor his colleague
  wants is already done where it pays (`registry.py:98-111`, 12 vendor labels behind one lookup),
  and with a redirect to a better target outside the directory (`MissingNamespaceText`
  discriminated in four modules under `adapters/anndata/`; `description.py` holds six more
  identity types — both verified).
- **eval-2:** the **Feather V1 caveat** — `pyarrow.ipc.open_file` raises `ArrowInvalid` on a V1
  file while `pd.read_feather` reads both, and V1 is still writable from R's
  `arrow::write_feather(version = 1)`, so a collaborator's file is not guaranteed to be V2. I
  could not verify this without a V1 file; the run says it did. with_skill recommends the same
  `ipc.open_file` call and misses the risk entirely. Also the only run to check `apb_studio`
  (`capabilities.py:199`, `testdata.py:132`) and the only one to tell the user what their
  collaborator will actually experience: feather inherits parquet's contract, so `string_columns`
  is ignored and an `int64` identifier column will not be restored to text.

## Cross-run discrepancy worth knowing

Both eval-1 runs agree on the totals (71 `isinstance` calls in `params/`, 32 in `model.py` — I
reproduced both) but disagree on how many are foreign: with_skill says 47 (66%), old_skill says
51 (71%). The gap is the four `parse(value: object)` idempotency guards, which with_skill counts
as owned-then-rejected and old_skill counts as foreign. Both reject them for the same reason, so
no conclusion depends on it — but the two headline percentages are not reconcilable as stated,
and an assertion that quoted either number would be grading an artefact of classification.
