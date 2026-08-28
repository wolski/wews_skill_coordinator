# Mixed install: npx for remote packages, Python symlinks for local sources

Status: implemented 2026-08-27
Date: 2026-08-27

## Goal

Third-party skill packages keep installing through the pinned `npx skills` CLI.
Skills whose source lives on this machine — this repo's `skills/` tree and any
checkout under `repos/` — are installed by the Python coordinator as symlinks, so
editing the source is immediately live for both Claude Code and Codex, with no
reinstall step.

## Prior implementation

The working symlink installer is commit `1c96e16` (`skill_coordinator.py`, 341
lines), the commit immediately before `b3ca9e2 refactor: install composable skill
profiles with npx`. The mixed implementation reuses its mechanics rather than
reinventing them:

- `_remove_managed_symlinks(*dirs)` — sweep a directory, unlink only symlinks that
  resolve inside the coordinator's own tree. Ownership is structural, no state file.
- `install` CONFLICT rule — if the target exists and is not a managed symlink,
  print `CONFLICT` and skip rather than clobber.
- `MISSING` per configured skill whose source path does not exist.
- `audit` drift per skill from `git log -1 --format=%H -- <skill_path>` inside the
  source repo, compared with `last_reviewed_sha:` in
  `.kairos/knowledge/<slug>/<slug>.md`.
- `update` pulls every repo with `git pull --ff-only` and **warns** on failure
  instead of raising, so one dirty checkout cannot block the rest.
- `status` prints `git log --oneline -1` per repo.
- `DRY_RUN` as a module global — this is the one thing not to carry over; the
  npx-era code threads `dry_run` as a parameter and that is better.

Two things from `1c96e16` are deliberately **not** restored:

- **Agent symlinking.** It linked `agents/*.md` into `~/.claude/agents/`, but those
  files came from the external `claude-kaiser-skills` checkout. Agent files are now
  skill-owned (`skills/review/skills/multiagent-review/agents/*.md`), per AGENTS.md.
  There is no top-level `agents/` tree left to link.
- **`git clone --depth 1`.** A shallow clone breaks `audit`'s per-skill
  `git log -1 -- <path>` and is wrong for a repository the user commits to. Clone full.

## Established facts

1. `~/.agents/skills/<name>` is the shared store both agents read. Codex is a
   *universal* agent in the CLI's registry (`skillsDir == ".agents/skills"`), so it
   reads that path directly and nothing is ever written to `~/.codex/skills`.
2. Claude Code gets a per-agent symlink `~/.claude/skills/<name>` ->
   `../../.agents/skills/<name>`. Verified in the live install.
3. `npx skills add` accepts only a GitHub package/URL. There is no local-path
   source, and the store copy is always a physical git fetch. `--copy` only
   controls the per-agent link, not the store.
4. `repos/fgcz-skills` is a live clone of `https://github.com/fgcz/skills.git`.
   The GitHub API returns 404 unauthenticated for `fgcz/skills`, so the repository
   is private (inferred from 404 + a working local clone); npx would need git
   credentials to fetch it. The user has commit rights, so this checkout is also
   the contribution path — the coordinator must not fight it.
5. The checkout is on branch `feat/ptm-pipeline-run-skill`, not `main`, and that
   branch is 17 commits behind `origin/main`. A `git pull --ff-only` on
   2026-08-27 fast-forwarded it 9892857 -> bcd27cb, which brought in
   `3e5dce0 feat(proteomics-data-analysis): add supporting prolfqua skills`.
6. All 20 configured `fgcz/skills@` skills — including `prolfquapp-dea`,
   `adding-models-to-prolfqua` and `phosphoproteomics-ptm-analysis`, which were
   absent before that pull — now exist both on the checked-out branch and on
   `origin/main`. `skills.toml` needs no change.
7. Consequence for the design: with symlinks, the installed content is whatever
   branch each source checkout happens to be on. That state must be visible.
8. Measured: a **symlink** placed at `~/.agents/skills/plotly` pointing into this
   repository is picked up by Codex — `codex debug prompt-input` listed
   `plotly: ... (file: /Users/wolski/.agents/skills/plotly/SKILL.md)`. Codex follows
   symlinks in the shared store. Probe symlink removed afterwards.
9. Measured: the two-hop chain `~/.claude/skills/plotly ->
   ../../.agents/skills/plotly -> <repo>/skills/scientific-python/skills/plotly`
   resolves and `SKILL.md` reads through it. Probe symlink removed afterwards.

## Design

### Config — new `[sources]` table

A package listed under `[sources]` is locally managed; every other package goes to
npx. Nothing else in the `owner/repository@skill` reference notation changes.

```toml
[sources."wolski/wews_skill_coordinator"]
path = "skills"          # relative to the repository root
owned = true             # inventory must match skills.toml exactly

[sources."fgcz/skills"]
path = "repos/fgcz-skills"
git_url = "https://github.com/fgcz/skills.git"
```

- `path`: root under which skills are discovered with the uniform
  `<category>/skills/<name>/SKILL.md` layout, the same layout both trees already
  use. Frontmatter `name:` must equal the directory name (existing rule).
- `owned = true` (default `false`): the source is exhaustive — every discovered
  skill must be configured and every configured skill must exist. Non-owned
  sources only require configured skills to be a subset of the checkout, because
  `repos/fgcz-skills` carries 78 `SKILL.md` files (77 on the pattern plus one
  off it) of which 20 are configured.
- `git_url` (optional): enables `clone` and `update` for that source.

Adding another folder is then one `[sources]` block plus profile entries.

### Install layout

For each local skill:
- `~/.agents/skills/<name>` -> symlink to the absolute source directory.
- `~/.claude/skills/<name>` -> symlink to `../../.agents/skills/<name>`.

This is byte-for-byte the layout npx produces, so Codex picks the skills up from
the shared store and Claude Code from its own directory. It supersedes `1c96e16`,
which wrote directly to `~/.claude/skills/<name>` and `~/.codex/skills/<name>`:
npx no longer writes to `~/.codex/skills` at all, and one uniform store keeps
`list`, removal, and conflict detection identical for both install kinds. Facts 8
and 9 confirm both agents resolve the symlinked form. `~/.agents/.skill-lock.json`
stays npx-owned and is not written by the coordinator; a coordinator-managed entry
is identified structurally — a symlink under `~/.agents/skills` resolving inside
this repository.

### Reconciliation in `switch` / `install`

1. Resolve the profile, split its packages into npx packages and local sources.
2. Remove entries whose *kind* flips: a name now local but currently an npx
   directory is `npx remove`d first; a name now remote but currently a managed
   symlink is unlinked first.
3. `npx add` the remote packages (unchanged; failures leave the active set intact).
4. Symlink the local skills; report `MISSING` per skill absent from its checkout.
5. Remove what the profile drops: `npx remove` for npx names, unlink for managed
   symlinks.

### Command surface

| command | change |
|---|---|
| `switch` / `install` | mixed reconciliation above |
| `update` | `npx update --global` **plus** `git pull --ff-only` per source with a `git_url`, warning rather than raising on failure as `1c96e16` did |
| `clean` | `npx remove` **plus** unlink managed symlinks |
| `list` | mark each installed skill `npx` or `local -> <path>`; print per-source branch/HEAD/behind-count |
| `clone` | restored from `1c96e16`, minus `--depth 1`; clones missing sources that declare `git_url` |
| `audit` | npx skills keep the lock-hash comparison; local skills use `1c96e16`'s per-skill `git log -1 --format=%H -- <path>` against `last_reviewed_sha:`, which is strictly better than reporting them uninstalled |

`status` from `1c96e16` is not restored as a separate command; its information
(branch, HEAD, behind-count) is folded into `list`. No other commands added.

### Files touched

- `skill_coordinator.py` — `Source` model, generalized inventory validation,
  symlink installer, mixed reconciliation, `clone`, extended `update`/`clean`/`list`/`audit`.
- `skills.toml` — `[sources]` blocks.
- `test_skill_coordinator.py` — source parsing/validation, symlink install and
  removal against `tmp_path` roots, kind-flip reconciliation, MISSING reporting.
- `Makefile` — `clone` target, help text.
- `README.md`, `AGENTS.md` — mixed model, how to add a folder source.

## Resolved

The three configured-but-absent `fgcz/skills` skills were a stale checkout, not a
config error (facts 5-6). They stay in `skills.toml`.

The coordinator never switches or resets a source branch — the user works on
feature branches there and commits upstream. It reports the state instead:
`list` prints each local source's branch, short HEAD, and behind-count versus its
remote tracking branch, so a checkout parked on a feature branch is visible rather
than silent. (`install` does not; the command table is the normative statement.)

## Verification

- `make test`
- `uvx ruff check skill_coordinator.py test_skill_coordinator.py`
- `uv run --with cyclopts --with pydantic --with tomli --with pytest --with pyright pyright skill_coordinator.py test_skill_coordinator.py`
- `make dry-run PROFILE=python-design` and `make dry-run PROFILE=full`
- A real `make switch PROFILE=python-design`, then confirm the symlink chain and
  that `codex debug prompt-input` lists the local skills.

## Implementation notes

Two things the plan got wrong, corrected while building:

1. `validate_sources` originally raised on any configured skill absent from its
   checkout. That blocked `load_config()`, and therefore `clone` -- the command
   that fixes an absent checkout. A missing skill now raises only for an `owned`
   source; for a third-party checkout it is reported by `install` as `MISSING`
   and turns into a non-zero exit at the end of the switch.
2. A dry run cannot perform the kind-flip `npx remove`, so the store still held a
   real directory when the link step ran and every flip printed a stale
   `CONFLICT`. `install_local_skill` now takes `replacing`, the set of entries the
   caller has already removed, so a dry run reports the same action a real run takes.

Verified on the live system:

- `make test` 65 passed; `ruff check` clean; `pyright` 0 errors.
- `make dry-run PROFILE=python-design` and `PROFILE=full`: exit 0, no MISSING,
  all 39 local skills resolve (19 owned + 20 from `repos/fgcz-skills`).
- `make switch PROFILE=python-design` executed for real. `~/.agents/skills` now
  holds four symlinks into this repository plus the npx directory
  `clean-architecture`; `~/.claude/skills` holds the matching two-hop links. The
  unmanaged `~/.claude/skills/commit` directory and the stray
  `~/.agents/skills/directed-folder-imports.skill` file were untouched.
- `codex debug prompt-input` lists all five skills from `~/.agents/skills`.
- Live-edit proof: reading `~/.agents/skills/directed-folder-imports/SKILL.md`
  returns the uncommitted working-tree version (68 insertions ahead of HEAD), and
  Claude Code loaded that revised description in-session without a reinstall.
- `make list` reports both sources with branch, HEAD and behind-count, and still
  identifies the active profile.
- `make audit` compares local skills by git SHA again. `python-style-guide` shows
  DRIFT `49acfd07 -> 19c92c78`: the recorded SHA predates the move of personal
  skills into this repository, so it is a genuine re-review signal rather than a
  bug. The other three owned skills have no `.kairos/knowledge` record yet.

## Adversarial review outcome

A 38-agent review of this plan against the working tree ran after implementation
(26 agents completed, 12 stalled and were not retried further). Four defects
survived refutation; three were real in the shipped code and are fixed:

1. **Ordering (high).** The kind-flip `npx remove` ran before `npx add`, so the
   claim "a failed source leaves the active set intact" was false for exactly the
   migration this change performs. A verifier reproduced it: with a flip pending
   and the fetch failing, all four owned skills ended up uninstalled and did not
   come back on a re-run. Fixed by splitting the two flip directions. The
   local -> npx unlink still runs first, because npx needs the store path free;
   failed fetches restore any removed local link whose npx replacement does not
   exist. The npx -> local removal runs only after every fetch has succeeded.
   Regression tests cover failed flips in both directions.
2. **Source paths outside the repository (high).** `_is_managed` tested
   `ROOT in target.parents` and the link report called
   `directory.relative_to(ROOT)`, so a source outside this repository would never
   be recognised as coordinator-managed and would crash on install. Since the
   point of `[sources]` is to point at an arbitrary folder, configured source
   roots are normalized before ownership tests and paths outside the repository
   print absolute.
3. **Double npx spawn (low).** `list` called `npx skills list --global --json`
   twice per invocation with nothing between the two. Now once.
4. **The off-pattern fgcz `SKILL.md` (high as planned, already handled).**
   `repos/fgcz-skills/meta-skills/fgcz-devday3-unified-bioinformatics/SKILL.md`
   sits at `<category>/<name>/SKILL.md`. The plan's claim of a uniform layout
   across both trees was wrong, and `1c96e16`'s discovery raised on such a path,
   which would have killed every command at `load_config()`. The implementation
   already skips off-pattern paths in a non-owned source and raises only for an
   owned one, so no change was needed.

Automated verification after the follow-up fixes: 69 tests pass, ruff and
pyright are clean, and the `python-design` dry run orders `add` before removal.
The earlier live repeated switch was a no-op that left the four symlinks and the
npx directory intact.

Follow-up verification on 2026-08-28 also corrected pull reporting: `update`
prints `pulled` only after a successful `git pull`, while a failed pull prints
the in-progress action and warning without claiming success.
