---
name: polars-first
description: >-
  Simplify Python pipelines that use Polars by replacing handwritten table processing with
  native expressions and deleting redundant representations. Use when reviewing or refactoring
  Polars code, reducing pipeline complexity, replacing row/column loops, or investigating repeated
  DataFrame/Series/list conversions, per-column aggregation, configuration copying, or reconstruction
  of already compiled operations. Keep custom scalar algorithms and meaningful boundaries where
  needed. Does not imply migrating another dataframe library to Polars or redesigning rule schemas.
---

# Polars First

Let Polars execute table operations. Give each decision and runtime representation one owner. Simplification should remove work or concepts while preserving the package's contract.

Keep the requested scope: a review produces findings; an implementation changes the relevant pipeline. Behavior ownership and directory dependencies remain governed by the project's existing design. No additional interfaces, policy hierarchies, or frameworks are required by this skill.

## Find the actual redundancy

Trace a representative input through selection, configuration, execution and output. Establish what counts as a complete result and where scientific interpretation ends. A structural writer should not reconstruct algorithms from stored provenance.

Look for two kinds of opportunity:

- **Table work in Python:** extract Series, convert to lists, zip rows, accumulate results, maintain a value cache, then rebuild a frame. Also inspect column-by-column validation, summaries, null counts and storage conversion.
- **Repeated representations or decisions:** records immediately copied into another record, factories reconstructing configured behavior, detection constructing objects that compilation constructs again, parallel maps joined by name, or projections subsequently overwritten.

For each candidate, name the current work, the proposed replacement, the complete code that can disappear and the behavior that must survive. Read its consumers before calling a field or wrapper redundant. A boundary isolating persisted schemas from runtime algorithms may legitimately translate information; remove unnecessary stages around it.

## Express table work in Polars

Prefer frame projections, name/dtype selectors, expressions, masks, reductions, grouping and joins over extracting values into Python. Check the installed Polars version before selecting an API.

| Existing machinery | Candidate replacement |
| --- | --- |
| Get column, transform, insert column | Named expressions in `select` or `with_columns` |
| Repeated null counts or validity scans | Frame-wide counts and expression reductions |
| Python coalesce or concatenation loops | Native coalesce and string/list expressions |
| Per-cell presence wrappers and repeated grouping | Null masking plus native aggregation under the existing presence policy |
| Reordering with temporary indices and sorting | A join with explicit ordering and cardinality requirements |
| Per-column storage conversion | A bulk conversion at the actual storage boundary |

These are candidates, not automatic substitutions. Preserve an existing lazy plan where applicable; avoid introducing eager collection or a full unpivot merely to simplify a bounded reduction. Check intermediate size and memory where the replacement changes materialization.

Loops over declared operations, headers or layers can be legitimate orchestration. Expression-building comprehensions already delegate data execution to Polars. Bounded diagnostic exports and required NumPy/Arrow/storage boundaries are also legitimate. A search hit for `get_column`, `to_list` or `for` is not itself a defect.

## Keep necessary scalar algorithms pure

Use native expressions where they preserve supported syntax and semantics. For custom scalar parsing, keep the Python function small and deterministic, returning both values and diagnostics as data. Do not mutate diagnostic accumulators inside callbacks.

For a pure, row-independent operation with repeated inputs, consider selecting distinct tuples of **all declared inputs**, mapping once per tuple with an explicit return dtype, then joining back with the original cardinality and order. Preserve the input null policy and deliberately handle null join keys. This optimization is unsuitable for stateful, random or row-dependent computations.

If diagnostics have row locations or per-row multiplicity, expand them back to the original rows at the same stage as before. Deduplication must not erase warnings from repeated inputs or from rows filtered out later.

`map_elements` still invokes Python. It does not establish native vectorization or a speedup. Keep independently declared operations independent; reuse one operation's result only when the dependency contract permits it.

## Protect semantics at the changed boundary

Choose checks from the actual contract:

- Null, NaN, blank text, missing sentinels and invalid tokens may mean different things. Preserve distinctions through masking, parsing and aggregation.
- Duplicate selection may operate per cell. Under a first-present policy, an invalid first token must not vanish through early numeric coercion; an all-missing aggregate may need to remain null rather than become zero.
- Preserve row/column order, join multiplicity, canonical keys, categorical mappings and diagnostic order. Group ordering alone does not repair an earlier unstable join or sort.
- Preserve precision. Converting an already numeric value through text can change it even when a direct numeric cast would not.
- Exercise relevant empty/all-null inputs, repeated keys, output/source name collisions, and regex or string-format differences between Python and Polars.

Shared settings do not imply interchangeable operations. Presence checking, duplicate resolution and final value parsing can share an object while retaining separate execution stages.

## Remove complete stages and verify the result

Prefer existing behavior objects owning their cohesive settings; use replacement of changed fields where it removes copying branches. Retain compiled results when their inputs remain valid. Keep explicit validation at meaningful boundaries rather than adding automatic mutation tracking.

Measure the complete replacement, including relocated and newly introduced production code. Report tests, schemas and proof scripts separately. File splitting, shorter formatting and schema flattening need an independent benefit. Arbitrary line-count targets are not evidence that a replacement can meet them.

Use focused semantic checks and the project's required gates. Where a corpus exists, compare the selected revision's actual outputs, plans and diagnostics with a recorded baseline; identify cached versus freshly executed results. Older full-corpus evidence does not cover later edits, and hashes prove only the properties included. Correctness fixes need their own expected behavior rather than parity with a known bug.

Measure runtime and memory separately before claiming performance. Keep temporary comparison machinery proportionate. Finish with what disappeared, measured net change when relevant, retained boundaries, verification scope and remaining uncertainty. If no worthwhile replacement is supported, say so without manufacturing an abstraction or a rewrite.
