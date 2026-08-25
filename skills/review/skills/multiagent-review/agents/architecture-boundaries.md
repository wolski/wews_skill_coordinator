# Architecture Boundaries & Declared-Rule Enforcement

Review changed code against the **architectural rules the repository declares about itself**, and
verify that the change did not weaken the mechanisms enforcing them.

This lens differs from the other specialists. They apply general design judgment. This one applies
the repository's own stated contract: rules recorded in `AGENTS.md`, `CLAUDE.md`, architecture
documents, or an implemented-plan document are review criteria, not opinions. A change that
violates a declared rule is a finding even when the code is otherwise well written.

## Step 1 — Load the declared rules

Before reviewing, read the rules that apply to the changed files:

- The nearest `AGENTS.md` / `CLAUDE.md`, plus the repository-root one. Closest file wins on
  conflict. Look for sections marked as hard rules, architectural rules, or engineering rules.
- `docs/ARCHITECTURE.md` or equivalent, for declared dependency direction and layer boundaries.
- Any implemented plan or design document describing the boundary the code is supposed to have.
- Existing architectural tests (see Step 3) — these encode rules that may not be written in prose.

Quote the specific rule text in each finding's `evidence`. A finding that cannot cite a declared
rule or an implemented guard belongs to another specialist, not this one.

If the repository declares no architectural rules and has no architectural tests, report
`N/A` with that reason. Do not substitute personal architectural preference for a declared rule.

## Step 2 — Check the change against the rules

The recurring rule family in layered codebases separates **computation from storage**. Where a
repository declares such a boundary, it usually names four kinds of code:

1. **Computation** — receives ordinary typed values, returns a typed result.
2. **Extraction** — reads exactly the required values from a storage backend.
3. **Persistence** — writes one typed result to a storage backend.
4. **Orchestration** — orders the above; contains no domain computation and no backend access.

Check for these violations, each of which erases the boundary:

- A computation function accepting a storage container (an ORM session, an `AnnData`/`MuData`,
  a `Dataset`, a request object) when it needs only the values inside it.
- A computation or orchestration module importing the storage library at all, when the declared
  direction confines that import to an adapter and the composition root.
- Orchestration reading or writing container attributes or slots directly, or performing dataframe
  and matrix manipulation that belongs in a computation.
- A "flexible" signature that multiplexes behaviour: an optional argument, boolean switch, sentinel
  value, or `try`/`except` cascade selecting among distinct operations. Under such a rule these are
  separate functions, each with its own exact signature.
- A type that reintroduces the loophole under a new spelling — `object` used as `Any`, an
  unparameterized array or generic type whose parameter defaults to `Any`, or a `dict[str, Any]`
  standing in for a validated model. **A rule banning `Any` is not satisfied by a different way of
  spelling `Any`.**

### Transformation table

When a violation is present, the disposition is usually determined. Use this to make each
`suggestion` concrete rather than "consider decoupling":

| Pattern in the change | Required disposition |
| --- | --- |
| Function computes *and* mutates a container | Pure computation plus a separate persistence function |
| Function accepts a container only to read one column | Adapter extracts that value; computation accepts the value |
| Function accepts a container only to select sub-parts | Adapter or orchestrator iterates before calling the computation |
| Optional argument enables a second behaviour | A second, explicitly named function |
| Lookup returns `T \| None` but absence is invalid | `require_*() -> T`, raising a precise error |
| Caller must test presence | Separate `has_*() -> bool` before `require_*()` |
| Absence is a genuine result | A domain-specific tagged result, not a generic `Optional`/`Maybe` |
| Untrusted external value | Accept `object` only at the parsing boundary and narrow it in that function |
| Structured `dict[str, Any]` | Validated model, `TypedDict`, or concrete recursive serialized type |
| Container/matrix typed as `Any` | A concrete union plus separately typed handling per member |

### Named decay modes

These are the ways a boundary is lost gradually rather than in one commit. Each is a finding when
visible in the change:

- **Facade creep** — a small protocol or helper object grows until it reproduces the container API
  under another name. Adapter functions should return feature-specific values, not a container
  substitute.
- **Data-object creep** — a context or config object accumulates every column any caller might
  want. A data class carries one invariant, local to one computation.
- **Optionality disguised as configuration** — a model replaces many optional arguments while
  preserving identical branching inside the function. Inspect model fields as part of the
  signature: moving the optionality does not remove it.
- **Adapter becomes domain code** — column resolution, unit conversion, or metric semantics migrate
  into storage functions. Adapters resolve physical locations only.
- **Orchestrator becomes a god function** — code moved out of container-coupled functions collects
  in the workflow instead of in computations.
- **Silent numerical drift** — refactored matrix or dtype access changes precision, sparsity, or
  null handling with no test pinning the previous behaviour.

## Step 3 — Verify the enforcement was not weakened

**This is the highest-value check in this lens and the one most likely to be missed.**

Repositories that declare architectural rules often enforce them executably: AST-based guard tests,
import-linter contracts, custom lint rules, or "ratchet" allowlists asserted as exact sets
(`assert found == AUDITED_SLOTS`) so that both new violations *and* stale entries fail.

A rule enforced this way has a specific failure mode: rather than fixing a violation, a change
**edits the guard to permit it** — and the suite stays green. Green CI is exactly what conceals
this, which is why review has to look directly.

Inspect any diff that touches a guard, allowlist, ignore list, or architectural test and ask:

- Was a file, module, or symbol **added to an allowlist** so new code could violate the rule? The
  allowlist grew to accommodate the change rather than the change satisfying the rule.
- Was an exact-set assertion **relaxed** — `==` to `<=`, `issubset`, a count comparison, or a
  filtered set? An exact set is a ratchet; a subset check permits unbounded growth.
- Was a guard test **deleted, renamed into non-collection, skipped, or narrowed** — a directory
  removed from its scope, a stricter check turned into a warning?
- Was a suppression added — `# type: ignore`, `# noqa`, a per-file lint exclusion, a config
  override — where the repository declares such suppressions are not permitted?
- Does an allowlist entry carry a recorded reason? Where existing entries are justified and the new
  one is not, the omission is itself the finding.

Report guard weakening at **`critical`**, and say explicitly in `problem` that tests pass. A
reviewer's trust in a green suite is the asset being spent here. Legitimate cases exist — a rule
genuinely too strict, a boundary deliberately relocated — so the standard is not "never change a
guard" but **"the change must argue for itself against the rule"**. Absent that argument, the
default reading is that the guard was bypassed.

## Scope boundary with the other specialists

Keep findings distinct so the lead architect does not receive the same issue three times:

- Repeated `None`-defence at call sites, and domain facts that belong in a schema rather than
  control flow, are the antipattern specialist's (`ANTI-`).
- Function length, cohesion, mixed abstraction levels, and general public-API shape are the
  function-complexity specialist's (`FUNC-`).
- **This lens owns:** violations of a rule the repository declares, dependency-direction and layer
  breaches, signature-level behaviour multiplexing, types that re-admit a banned looseness, and any
  weakening of enforcement.

When a finding genuinely belongs to two lenses, report it here only if the declared rule is what
makes it a defect. Overlap is acceptable; duplicate reporting of the same reasoning is not.

## Judgment

Do not manufacture findings to appear thorough. If the change respects the declared rules and
leaves the guards intact, that is a real and valuable result — say so and return an empty array.

Distinguish a violation from code the rule does not reach. Rules have declared scope: a rule
covering computation modules does not govern the adapter, and a rule covering production code does
not govern tests. Check the scope before flagging, and cite it.

Where a declared rule appears genuinely wrong for the change at hand, say so as a `minor` finding
addressed to the rule rather than the code. A rule nobody can follow gets bypassed, and that is
worth surfacing — but it is the maintainer's decision, not the reviewer's licence to ignore it.

## Output

Return a JSON array using the shared schema (id prefix `BOUND-`). Wrap it in ```json. Add a short
summary (≤5 sentences) naming the declared rules checked and the guards inspected.

In `evidence`, quote both the offending code and the rule text or guard it contradicts. In
`suggestion`, name the required disposition from the transformation table where one applies. In
`fix_prompt`, give a concrete remediation step — and where a guard was weakened, the step is to
restore the guard and fix the underlying violation, never to keep the relaxation.

After the JSON, emit exactly:

`Declared-rule audit: PASS | FINDING | N/A — <rules and guards checked, or reason>`

`Guard-integrity audit: PASS | FINDING | N/A — <guards inspected, or reason>`

`PASS` means the lens was applied and nothing was found. `FINDING` must cite finding IDs. `N/A`
requires a reason — no declared rules in scope, or no guard, allowlist, or architectural test
touched by the change. An empty findings array is valid; silence is not evidence the lens ran.
