# Prompt audit — personal agent config (2026-09-24)

Six findings against Opus 5.5. The biggest: effort silently drops to `medium` on Opus 5.5, the answer-first rules reach the model three times per turn, and there are two identical `code-simplifier` agents. Proposed patch: [prompt_audit.patch](prompt_audit.patch). Nothing applied; dry run `patch -p1 --dry-run` from `~` is clean.

## Assumptions

- Target: Opus 5.5 — `"model": "opus[1m]"` resolves to it now
- Scope: always-loaded surface only
- Out of scope: repos under `~/projects`, owned skills in [skills](../skills)
- Working tree includes uncommitted edits to [AGENTS.md](../agent-config/AGENTS.md) and [answer-first.md](../agent-config/output-styles/answer-first.md)
- No API request code in scope; no non-Anthropic provider markers

## Inventory

- [~/AGENTS.md](/Users/wolski/AGENTS.md)
- [agent-config/AGENTS.md](../agent-config/AGENTS.md) via `~/.claude/CLAUDE.md`
- [answer-first.md](../agent-config/output-styles/answer-first.md) output style
- [answer_first_reminder.py](/Users/wolski/.claude/hooks/answer_first_reminder.py) + [answer-first-reminder.md](/Users/wolski/.claude/hooks/answer-first-reminder.md), every prompt
- [settings.json](/Users/wolski/.claude/settings.json)
- [~/.claude/agents](/Users/wolski/.claude/agents): 1 file, 3 symlinks

Counts: Group 1 — 3 · Group 2 — 0 · Group 3 — 0 · Group 4 — 2 · flag — 1

## Findings

### 1. Opus 5.5 has no effort entry — High · add

- Location: [settings.json](/Users/wolski/.claude/settings.json) `modelSettings`
- Evidence: `xhigh` set for `claude-opus-5`, `claude-fable-5-1` only
- Pattern: G4, thinking config sized for wrong model
- Why: Opus 5.5 defaults to `medium`, one below Opus 5's `high`; the `xhigh` preference stops applying once `opus` resolves to 5.5
- Action: add `"claude-opus-5-5": {"effortLevel": "xhigh"}`
- Caveat: assumes `modelSettings` is the key that sets effort (the key is from your file; not checked against CC docs)

### 2. Duplicate `code-simplifier` agent — High · remove

- Location: [code-simplifier.md](/Users/wolski/.claude/agents/code-simplifier.md)
- Evidence: body byte-identical to the enabled plugin `code-simplifier@claude-plugins-official`
- Pattern: G4, redundant specialist sub-agents
- Why: roster shows both `code-simplifier` and `code-simplifier:code-simplifier`; same task, prompt, tools
- Action: delete the local copy; the plugin one remains

### 3. Answer-first reminder re-injected every turn — Medium · remove

- Location: [settings.json](/Users/wolski/.claude/settings.json) `hooks.UserPromptSubmit`; [answer-first-reminder.md](/Users/wolski/.claude/hooks/answer-first-reminder.md):1-15
- Evidence: full reminder as `additionalContext` on every prompt, on top of the output style in the system prompt and the harness's own "Answer-first output style is active" after tool calls
- Pattern: G1d, instruction re-insertion; G1c, duplicates that disagree
- Why: current models keep a once-stated instruction; the copies drift — reminder says bullets "around seven words", style says "3–4 words, 7 at most"
- Action: remove the hook entry; leave the script on disk for rollback
- Side note: docstring says "only in Opus 5 sessions", but `GATE = "opus"` also fires on 5.5 and 4.x

### 4. Numeric output ceilings — Medium · rewrite

- Location: [answer-first.md](../agent-config/output-styles/answer-first.md):33, 42, 58-60, 97
- Evidence: "at most 3–4 slides", "roughly 150 to 250", "3–4 words, 7 at most", "rarely more than 5 items", "Cap a document at roughly 1000 words"
- Pattern: G1f output-shaping choreography; G1b hard word caps
- Why: caps tuned against older models' padding; the guide wants them removed together and restated as audience framing — the stated reason (terminal reader) survives, the numbers go
- Action: rewrites in the patch keep the abstract / journal-introduction anchors and drop the counts
- Weight: you added these deliberately on 2026-09-01; decline the hunk if a week of Opus 5.5 without them runs long

### 5. "No exceptions" link rule — Medium · rewrite

- Location: [answer-first.md](../agent-config/output-styles/answer-first.md):22, 29-31
- Evidence: "— no exceptions", "Each one found is a defect"
- Pattern: G1a pressure language
- Why: contradicts line 7 ("defaults, not rules"); the desktop harness already asks for markdown links; scolding over-applies on current models
- Action: plain heading; keep the reason (backticked paths cannot be clicked)

### 6. Comment rule stated three times, emphatically — Medium · rewrite

- Location: [~/AGENTS.md](/Users/wolski/AGENTS.md):12-19
- Evidence: "the absolute bare exception, never the norm"
- Pattern: G1a pressure; G1c repetition as reinforcement
- Why: three bullets say one rule; the intensifier invites over-deletion of legitimate *why* comments
- Action: one plain paragraph, same rule and reason

## Flag only

- Dangling symlinks: `dead-code-audit.md`, `dry-audit.md`, `r-development.md` in [~/.claude/agents](/Users/wolski/.claude/agents) point to missing `repos/claude-kaiser-skills` — these agents silently don't load; restore or delete

## Kept on purpose

- Markdown no-hard-wrap rule in both AGENTS.md and answer-first.md: copies agree
- Preferred-packages prohibitions: carry the reason
- Precedence, correction and verification rules: user-specific context
- Reporting-a-fix examples: pin a format-sensitive shape

## Verify

- Apply hunks singly; run a few normal sessions after each
- After 3/4: check reply length stays acceptable without the hook
- After 1: check sessions actually run at xhigh
- Audit the owned skills in a separate run
