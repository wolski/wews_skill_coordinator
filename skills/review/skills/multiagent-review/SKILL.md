---
name: multiagent-review
description: >-
  Runs a panel-style multi-agent code review. Dispatches specialists for GoF
  patterns, antipatterns and declarative boundaries, function complexity,
  mixed abstraction and public API contracts, and architecture boundaries the
  repository declares about itself; then synthesizes a balanced, prioritized
  report. Supports branch diffs, specific paths, whole codebases, and commit
  ranges. Use when the user asks for a multi-agent, panel, deep, GoF,
  antipattern, API-design, architecture-boundary, layering, whole-codebase,
  full, or multi-perspective code review, or invokes /multiagent-review.
---

# Multi-Agent Code Review

A panel of five specialists reviews changed code. The first four run in parallel and produce findings; the lead architect then synthesizes a balanced report.

## Scope selection

The skill supports four scope modes. Pick one before dispatching, based on what the user said:

1. **Diff mode (default)** — changed code on the current branch vs `main`. Use when the user just says "review this branch" or runs the skill with no argument. Run `git diff --name-only main...HEAD` for the file list; if empty, fall back to `git diff --name-only HEAD` (working-tree changes). Pass each specialist the diff *and* the full content of the changed files (context matters for mixed-abstraction and god-object judgments).

2. **Path mode** — a specific file or directory the user named. Use when the user passes a path argument or says "review src/foo.py". Review the full content of those files, not just any diff in them.

3. **Whole-codebase mode** — every source file in the repository. Use when the user says "review the entire code", "review the whole codebase", "review everything", "full review", or similar. Build the file list from `git ls-files` (so it respects `.gitignore`) and filter to source files (skip lock files, generated code, vendored dependencies, binary assets). If the result is large, see "Large scopes" below.

4. **Commit mode** — a specific commit or commit range. Use when the user names a commit (`HEAD`, a SHA, `HEAD~3..HEAD`, etc.). Use `git show` or `git diff` for that range.

If the user's intent is ambiguous (e.g., they say "review my code" in a repo with both uncommitted changes and lots of existing code), ask which scope they want rather than guessing — the modes have very different cost and signal characteristics.

### Large scopes

Whole-codebase reviews can blow past the specialists' useful context. Before dispatching, count files and approximate lines. If the codebase has more than ~50 files or ~5000 lines of source:

- Tell the user the size and propose chunking (e.g., "I'll review this module-by-module — auth/, api/, db/ — and synthesize at the end").
- Or offer to focus on the highest-risk subset (entry points, recently-touched files, files with the most LOC).
- Don't silently truncate — partial reviews that look complete are worse than an explicit narrower scope.

## Orchestration

Run the four specialists **in parallel** by issuing four `Agent` tool calls in a single message (subagent_type `general-purpose`). Wait for all four to return, then issue a fifth call to the lead architect.

For each specialist call:
- Pass the scope (file list + diff) inline in the prompt.
- Embed the specialist's instructions by reading the corresponding file under `agents/` and pasting it into the prompt. Tell the agent to return findings as a JSON array (schema below) wrapped in a single ```json fenced block, plus a short prose summary.
- Be explicit that the agent should not modify files — read-only review.

Build a **context pack** in addition to the requested files or diff. Include only the directly
relevant supporting material:

- Direct callers of changed public functions and the types, protocols, overloads, or exports that
  define their contract.
- Repository-owned rules, configuration, or schemas that describe decisions also present in the
  changed control flow.
- Existing neighboring implementations when they establish the intended API or configuration
  boundary.
- The architectural rules the repository declares about itself — the nearest and root
  `AGENTS.md`/`CLAUDE.md`, `docs/ARCHITECTURE.md`, and any implemented plan document describing the
  boundary the code is supposed to have.
- The architectural guards that enforce those rules — AST/boundary tests, import-linter contracts,
  custom lint rules, and ratchet allowlists — **including their current content**, not only whether
  the diff touched them. The architecture-boundaries specialist cannot detect a widened allowlist
  without seeing it.

Do not expand this into an unbounded repository survey. The purpose is to expose design boundaries
that a changed-file-only review cannot see.

### Mandatory coverage gates

Require these exact declarations after the relevant specialist's JSON:

- Antipattern specialist:
  `Declarative-boundary audit: PASS | FINDING | N/A — <evidence or reason>`
- Function-complexity specialist:
  `Public-API audit: PASS | FINDING | N/A — <symbols reviewed or reason>`
- Function-complexity specialist:
  `Exception-control-flow audit: PASS | FINDING | N/A — <boundaries reviewed or reason>`
- Architecture-boundaries specialist:
  `Declared-rule audit: PASS | FINDING | N/A — <rules and guards checked, or reason>`
- Architecture-boundaries specialist:
  `Guard-integrity audit: PASS | FINDING | N/A — <guards inspected, or reason>`

`PASS` means the lens was checked and no issue was found. `FINDING` must cite one or more finding
IDs. `N/A` requires a reason, such as no public callable, exception boundary, repository-owned
declarative boundary, declared architectural rule, or architectural guard in scope. If a declaration
is absent or unsupported, follow up with that specialist before synthesis. An empty findings array is
valid, but silence is not evidence that a mandatory lens was applied.

`Guard-integrity audit` is the one gate that must not be waved through on a green suite. A change
that weakens an architectural guard — widening an allowlist, relaxing an exact-set assertion,
deleting a boundary test — passes CI by construction. If this declaration is missing, do not
synthesize without it.

For the lead architect call, pass the four specialists' raw outputs verbatim and the instructions from `agents/lead-architect.md`.

### Why parallel

The four specialists are independent — they apply different lenses to the same code. Sequential dispatch would just multiply latency. The lead architect must run last because synthesis requires all four inputs.

## Finding schema

Every specialist returns findings in this shape so the lead architect can merge them mechanically:

```json
{
  "id": "GOF-001",
  "severity": "critical | major | minor",
  "location": { "file": "path/to/file.py", "lines": "45-67" },
  "problem": "Short statement of the issue",
  "evidence": "Direct quote from the code that demonstrates the issue",
  "suggestion": "What to do about it",
  "fix_prompt": "Copy-pasteable instruction Claude Code can run to apply the fix"
}
```

ID prefixes: `GOF-` for gof-patterns, `ANTI-` for antipattern-specialist, `FUNC-` for function-complexity, `BOUND-` for architecture-boundaries. Keep prefixes stable so the lead architect can attribute findings.

Severity guidance:
- **critical** — bug risk, security issue, or structural problem that will compound.
- **major** — clear design smell that hurts maintainability now.
- **minor** — style or polish; safe to defer.

## Specialist roster

Read the matching file when dispatching each agent.

| Agent | Instruction file | ID prefix |
|---|---|---|
| GoF design patterns | `agents/gof-patterns.md` | `GOF-` |
| Antipatterns & declarative boundaries | `agents/antipattern.md` | `ANTI-` |
| Function complexity, mixed abstraction & public API contracts | `agents/function-complexity.md` | `FUNC-` |
| Architecture boundaries & declared-rule enforcement | `agents/architecture-boundaries.md` | `BOUND-` |
| Lead architect (synthesis) | `agents/lead-architect.md` | — |

The architecture-boundaries specialist is the only one whose criteria come from the repository rather
than from general design judgment: it enforces rules the repository declares in `AGENTS.md`,
`CLAUDE.md`, or architecture documents, and checks that the change did not weaken the tests and
allowlists enforcing them. In a repository that declares no architectural rules and has no
architectural tests, it correctly returns `N/A` — dispatch it anyway rather than deciding in advance
that there is nothing to check.

## Output

Present the lead architect's markdown report to the user as the final answer. Include the raw specialist JSON in a collapsed section at the bottom so the user can drill in if a synthesis decision looks wrong.

Do not modify any source files. This skill is read-only review; the `fix_prompt` fields are suggestions the user can run separately.

## When in doubt

- If the diff is huge (>50 files or >2000 lines), ask the user whether to review everything or focus on a subset before spawning agents — specialists waste context on noise otherwise.
- If a specialist returns no findings, that is a valid result. Don't prompt it to invent issues.
- If specialists disagree (e.g., GoF says "apply Strategy", antipattern says "Golden Hammer"), surface the disagreement explicitly in the lead architect's report rather than silently picking a winner.
