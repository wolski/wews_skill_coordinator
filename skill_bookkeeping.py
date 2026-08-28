"""Inventory every ``SKILL.md`` under a folder and report how each one is held.

The scan answers three questions per file: is it a real file, a symlink, or an
alias reached through a symlinked directory; does this repository manage it, does
another tool manage it, or does nobody; and where a skill exists more than once,
which copy is authoritative and how far the others have drifted.

Outputs a CSV of one row per file, a Markdown report grouped by verdict, and a
self-contained HTML rendering of that report.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import os
import re
import subprocess
from collections import defaultdict
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

SKILL_FILE = "SKILL.md"
PRUNED_DIRS = frozenset({".git", ".hg", ".svn", "__pycache__", ".mypy_cache"})
VENDOR_MARKERS = ("/site-packages/", "/node_modules/", "/dist-packages/")

# Skills whose upstream name changed. Name matching alone would miss the pair.
ALIASES = {"fgcz-quarto-reports": "fgcz-quarto-report-template"}

FRONTMATTER_NAME = re.compile(r"^name:[ \t]*(.+?)[ \t]*$", re.MULTILINE)
FRONTMATTER_DESCRIPTION = re.compile(r"^description:[ \t]*(.*)$", re.MULTILINE)


# ── Records ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GitFacts:
    """What the enclosing repository, if any, says about a skill directory."""

    repo: str = "no-repo"
    origin: str = ""
    tracked: str = "no-repo"
    dir_state: str = ""
    last_author: str = ""
    last_commit: str = ""


@dataclass
class Row:
    """One ``SKILL.md``, annotated. Field order is the CSV column order."""

    status: str = ""
    skill_name: str = ""
    held_as: str = ""
    managed_by: str = ""
    location_kind: str = ""
    in_config: str = ""
    config_package: str = ""
    profiles: str = ""
    installed: str = ""
    install_kind: str = ""
    install_points_here: str = ""
    claude_link: str = ""
    link_target: str = ""
    real_path: str = ""
    copies_of_this_skill: int = 0
    content_vs_reference: str = ""
    drift_direction: str = ""
    diff_lines: str = ""
    reference_copy: str = ""
    git_repo: str = ""
    git_origin: str = ""
    git_tracked: str = ""
    git_dir_state: str = ""
    last_author: str = ""
    last_commit: str = ""
    modified: str = ""
    lines: int = 0
    bytes: int = 0
    md5: str = ""
    path: str = ""
    action: str = ""
    description: str = ""


@dataclass
class Found:
    """A ``SKILL.md`` located on disk, before annotation."""

    path: Path
    held_as: str
    link_target: str = ""
    real_path: Path = field(default_factory=Path)


@dataclass
class Discovery:
    """Everything the walk found, including the links it refused to follow."""

    files: list[Found] = field(default_factory=list)
    skipped_links: list[tuple[str, str, str]] = field(default_factory=list)
    unreadable: list[tuple[str, str]] = field(default_factory=list)


# ── Discovery ────────────────────────────────────────────────────────


def _expandable(link: Path, target: Path, root: Path) -> str:
    """Return why a symlinked directory must not be expanded, or an empty string.

    A link to the home directory or to an ancestor of the scan root would pull an
    arbitrarily large tree into the report, so it is named and left unfollowed.
    """
    if not target.is_dir():
        return "target is not a directory"
    if target == Path(target.anchor) or target == Path.home():
        return "target is the home directory or filesystem root"
    if root == target or root.is_relative_to(target):
        return "target contains the scan root"
    if link.resolve() != target:
        return "link does not resolve"
    return ""


def discover(root: Path) -> Discovery:
    """Walk ``root`` without following symlinks, recording how each file is held.

    Symlinked directories are not descended into, because their contents belong to
    the target. Each is expanded once as an alias, so the report can say a project
    reaches a skill through a link rather than holding its own copy.
    """
    result = Discovery()
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        here = Path(current)
        dirnames[:] = sorted(name for name in dirnames if name not in PRUNED_DIRS)
        for name in list(dirnames):
            link = here / name
            if not link.is_symlink():
                continue
            dirnames.remove(name)
            try:
                target = link.resolve()
            except OSError as error:
                result.skipped_links.append((_show(link, root), "", str(error)))
                continue
            refusal = _expandable(link, target, root)
            if refusal:
                result.skipped_links.append((_show(link, root), str(target), refusal))
                continue
            for aliased in sorted(target.rglob(SKILL_FILE)):
                result.files.append(
                    Found(
                        path=link / aliased.relative_to(target),
                        held_as="via-symlinked-dir",
                        link_target=str(target),
                        real_path=aliased,
                    )
                )
        if SKILL_FILE not in filenames:
            continue
        skill = here / SKILL_FILE
        if skill.is_symlink():
            result.files.append(
                Found(
                    path=skill,
                    held_as="symlinked-file",
                    link_target=os.readlink(skill),
                    real_path=skill.resolve(),
                )
            )
        else:
            result.files.append(Found(path=skill, held_as="real-file", real_path=skill))
    result.files.sort(key=lambda item: str(item.path))
    return result


def _show(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


BLOCK_INDICATOR = re.compile(r"^[>|][+-]?$")


def _description(block: str) -> str:
    """Read ``description``, joining a folded or literal block into one line."""
    match = FRONTMATTER_DESCRIPTION.search(block)
    if match is None:
        return ""
    value = match.group(1).strip()
    if BLOCK_INDICATOR.match(value):
        value = " ".join(
            line.strip()
            for line in block[match.end() :].splitlines()
            if line.startswith((" ", "\t")) or not line.strip()
        )
    return " ".join(value.strip("\"'").split())[:200]


def read_frontmatter(text: str) -> tuple[str, str]:
    """Return the ``name`` and ``description`` fields of a YAML frontmatter block.

    A description may be a plain scalar or a folded/literal block. Both collapse to
    a single line, because the report and the CSV want one cell either way.
    """
    if not text.startswith("---"):
        return "", ""
    end = text.find("\n---", 3)
    block = text[: end if end > 0 else 4000]
    name = FRONTMATTER_NAME.search(block)
    return name.group(1).strip().strip("\"'") if name else "", _description(block)


# ── Git ──────────────────────────────────────────────────────────────


def _local(timestamp: float | None) -> dt.datetime:
    """A timezone-aware local datetime, for a POSIX timestamp or for now."""
    if timestamp is None:
        return dt.datetime.now(tz=dt.timezone.utc).astimezone()
    return dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).astimezone()


def _git(cwd: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


class GitCache:
    """One ``git`` invocation per repository instead of per file."""

    def __init__(self) -> None:
        self._top: dict[Path, Path | None] = {}
        self._tracked: dict[Path, frozenset[str]] = {}
        self._dirty: dict[Path, dict[str, str]] = {}
        self._origin: dict[Path, str] = {}

    def _repository(self, directory: Path) -> Path | None:
        if directory not in self._top:
            top = _git(directory, "rev-parse", "--show-toplevel")
            self._top[directory] = Path(top) if top else None
        return self._top[directory]

    def _load(self, repository: Path) -> None:
        if repository in self._tracked:
            return
        listing = _git(repository, "ls-files", "-z")
        self._tracked[repository] = frozenset(listing.split("\0")) - {""}
        status = _git(repository, "status", "--porcelain", "-z", "--untracked-files=all")
        dirty: dict[str, str] = {}
        for entry in status.split("\0"):
            if len(entry) > 3:
                dirty[entry[3:]] = entry[:2].strip()
        self._dirty[repository] = dirty
        self._origin[repository] = _git(repository, "config", "--get", "remote.origin.url")

    def facts(self, skill_file: Path) -> GitFacts:
        directory = skill_file.parent
        repository = self._repository(directory)
        if repository is None:
            return GitFacts()
        self._load(repository)
        try:
            relative_file = skill_file.relative_to(repository).as_posix()
        except ValueError:
            return GitFacts()
        relative_dir = directory.relative_to(repository).as_posix()
        states = {
            state
            for path, state in self._dirty[repository].items()
            if path == relative_dir or path.startswith(f"{relative_dir}/")
        }
        return GitFacts(
            repo=repository.name,
            origin=self._origin[repository],
            tracked=(
                "tracked" if relative_file in self._tracked[repository] else "untracked"
            ),
            dir_state=",".join(sorted(states)) or "clean",
            last_author=_git(repository, "log", "-1", "--format=%an", "--", relative_dir),
            last_commit=_git(
                repository, "log", "-1", "--format=%h %ad", "--date=short", "--",
                relative_dir,
            ),
        )


# ── Coordinator view ─────────────────────────────────────────────────


@dataclass(frozen=True)
class Coordinator:
    """What ``skills.toml`` declares and what is currently installed."""

    profiles: dict[str, frozenset[str]]
    packages: dict[str, str]
    owned_roots: tuple[Path, ...]
    checkout_roots: tuple[Path, ...]
    installed: dict[str, str]
    install_targets: dict[str, Path]
    claude_links: frozenset[str]
    store: Path

    def profiles_of(self, name: str) -> str:
        return ",".join(sorted(self.profiles.get(name, frozenset()))) or ""


def _under(path: Path, roots: tuple[Path, ...]) -> bool:
    return any(path == root or path.is_relative_to(root) for root in roots)


# A project's own agent stores. A skill here was written by whatever tool owns the
# project's SkillSets, not copied there by hand.
PROJECTION_DIRS = ("/.agents/skills/", "/.claude/skills/", "/.codex/skills/")


def kairos_projections(root: Path) -> frozenset[tuple[Path, str]]:
    """Find ``(project, skill name)`` pairs that KairosChain projects into a store.

    A SkillSet at ``<project>/.kairos/skillsets/<name>/`` is projected by the
    ``plugin_projector`` into that project's ``.agents``/``.claude`` skill stores.
    Those copies are generated output, not something this repository installs.
    """
    pairs: set[tuple[Path, str]] = set()
    for skillsets in root.rglob(".kairos/skillsets"):
        if not skillsets.is_dir():
            continue
        project = skillsets.parent.parent
        for entry in skillsets.iterdir():
            if entry.is_dir():
                pairs.add((project, entry.name))
    return frozenset(pairs)


def locate(
    real_path: Path,
    skill_name: str,
    tracked: str,
    coordinator: Coordinator,
    projections: frozenset[tuple[Path, str]],
) -> tuple[str, str]:
    """Return the ``(location_kind, managed_by)`` pair for a resolved path.

    A project's ``.claude/skills/`` serves two masters: people author skills there
    and tools project them there. Version control separates the two — a committed
    file is project source, an untracked one is generated or installed output.
    """
    text = real_path.as_posix()
    if any(marker in text for marker in VENDOR_MARKERS):
        return "vendored-dependency", "python package"
    if _under(real_path, coordinator.owned_roots):
        return "coordinator-source-owned", "this repository"
    if _under(real_path, coordinator.checkout_roots):
        return "coordinator-source-checkout", "upstream checkout"
    if "/.kairos/skillsets/" in text:
        return "kairos-skillset-source", "KairosChain plugin_projector"
    in_store = any(marker in text for marker in PROJECTION_DIRS)
    if in_store and any(
        skill_name == name and real_path.is_relative_to(project)
        for project, name in projections
    ):
        return "kairos-projected", "KairosChain plugin_projector"
    if in_store and tracked != "tracked":
        return "agent-store", "an agent tool, not this repository"
    if "/TODO/" in text or "/skill-snapshot/" in text or "/design_skill/" in text:
        return "draft-workspace", "nobody"
    if "/.claude/skills/" in text:
        return "project-local-claude", "project repository"
    if "/skills/" in text:
        return "project-local-skills-dir", "project repository"
    return "project-local-other", "project repository"


# ── Annotation ───────────────────────────────────────────────────────


def _diff_line_count(left: Path, right: Path) -> int:
    result = subprocess.run(
        ["diff", str(left), str(right)], capture_output=True, text=True, check=False
    )
    return result.stdout.count("\n")


def _verdict(row: Row, reference: Row | None) -> tuple[str, str]:
    """Return the ``(status, action)`` pair for an annotated row."""
    if row.held_as != "real-file":
        return (
            "ALIAS-OF-MANAGED-SOURCE",
            f"not a copy — reached through a symlink to {row.link_target}",
        )
    if row.location_kind == "vendored-dependency":
        return "VENDORED-DEP", "ships inside an installed package; never manage"
    if row.location_kind == "coordinator-source-owned":
        if row.git_dir_state not in ("clean", ""):
            return "MANAGED-OWNED-DIRTY", "uncommitted edits in the managed source"
        if row.installed == "yes":
            return "MANAGED-OWNED", "installed and committed"
        return "MANAGED-OWNED", "configured, but not in the installed profile"
    if row.location_kind == "coordinator-source-checkout":
        if row.profiles:
            return "MANAGED-UPSTREAM", "in a profile; source is the upstream checkout"
        return (
            "AVAILABLE-NOT-CONFIGURED",
            "present in the checkout but named by no profile",
        )
    if row.location_kind in (
        "kairos-skillset-source",
        "kairos-projected",
        "agent-store",
    ):
        return "OTHER-TOOL", f"managed by {row.managed_by}, not this repository"
    if row.location_kind == "draft-workspace":
        if row.drift_direction == "reference-newer":
            return "DRAFT-SUPERSEDED", "authoring workspace; the managed copy is newer"
        return "DRAFT-UNMANAGED", "draft with no newer managed counterpart"
    if reference is not None and row.content_vs_reference == "differs":
        return (
            "DUPLICATE-DRIFTED",
            f"differs from {reference.path} ({row.drift_direction})",
        )
    if reference is not None:
        return "DUPLICATE-IN-SYNC", f"byte-identical to {reference.path}"
    return "UNMANAGED-PROJECT-LOCAL", "project-scoped; this repository does not install it"


def annotate(
    root: Path, coordinator: Coordinator, discovery: Discovery
) -> list[Row]:
    """Build one annotated row per discovered ``SKILL.md``."""
    cache = GitCache()
    projections = kairos_projections(root)
    rows: list[Row] = []
    for item in discovery.files:
        try:
            text = item.real_path.read_text(errors="replace")
        except OSError as error:
            discovery.unreadable.append((_show(item.path, root), str(error)))
            continue
        name, description = read_frontmatter(text)
        name = name or item.path.parent.name
        stat = item.real_path.stat()
        facts = cache.facts(item.real_path)
        location, managed_by = locate(
            item.real_path, name, facts.tracked, coordinator, projections
        )
        install_kind = coordinator.installed.get(name, "")
        target = coordinator.install_targets.get(name)
        rows.append(
            Row(
                skill_name=name,
                held_as=item.held_as,
                managed_by=managed_by,
                location_kind=location,
                in_config="yes" if name in coordinator.profiles else "no",
                config_package=coordinator.packages.get(name, ""),
                profiles=coordinator.profiles_of(name),
                installed="yes" if install_kind else "no",
                install_kind=install_kind or "not-installed",
                install_points_here=(
                    "yes" if target is not None and target == item.real_path.parent
                    else "no"
                ),
                claude_link="yes" if name in coordinator.claude_links else "no",
                link_target=item.link_target,
                real_path=item.real_path.as_posix(),
                git_repo=facts.repo,
                git_origin=facts.origin,
                git_tracked=facts.tracked,
                git_dir_state=facts.dir_state,
                last_author=facts.last_author,
                last_commit=facts.last_commit,
                modified=_local(stat.st_mtime).strftime("%Y-%m-%d"),
                lines=text.count("\n") + 1,
                bytes=stat.st_size,
                md5=hashlib.md5(text.encode()).hexdigest(),
                path=_show(item.path, root),
                description=description,
            )
        )
    _compare(rows, root)
    for row in rows:
        reference = next(
            (other for other in rows if other.path == row.reference_copy), None
        )
        row.status, row.action = _verdict(row, reference)
        if row.git_tracked == "no-repo" and row.status.startswith(
            ("UNMANAGED", "DRAFT")
        ):
            row.action += "; not in any git repository"
    rows.sort(key=lambda item: (item.status, item.skill_name, item.path))
    return rows


# Which copy of a skill is treated as authoritative, lowest rank first. A copy
# outside this table is only a reference when no ranked copy exists.
AUTHORITY = {
    "coordinator-source-owned": 0,
    "coordinator-source-checkout": 1,
    "kairos-skillset-source": 2,
}


def _compare(rows: list[Row], root: Path) -> None:
    """Pick a reference copy per skill and measure every other copy against it."""
    groups: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        if row.location_kind == "vendored-dependency" or row.held_as != "real-file":
            continue
        groups[ALIASES.get(row.skill_name, row.skill_name)].append(row)

    for members in groups.values():
        for row in members:
            row.copies_of_this_skill = len(members)
        if len(members) < 2:
            continue
        reference = min(
            members,
            key=lambda item: (AUTHORITY.get(item.location_kind, 9), item.modified),
        )
        if AUTHORITY.get(reference.location_kind, 9) == 9:
            reference = max(members, key=lambda item: item.modified)
        reference.content_vs_reference = "reference"
        for row in members:
            if row is reference:
                continue
            row.reference_copy = reference.path
            if row.md5 == reference.md5:
                row.content_vs_reference = "identical"
                row.drift_direction = "in-sync"
                row.diff_lines = "0"
                continue
            row.content_vs_reference = "differs"
            row.diff_lines = str(
                _diff_line_count(root / reference.path, root / row.path)
            )
            row.drift_direction = (
                "this-copy-newer" if row.modified > reference.modified
                else "reference-newer"
            )


# ── Output ───────────────────────────────────────────────────────────


def write_csv(rows: list[Row], destination: Path) -> None:
    """Write one row per file, with the dataclass field order as the header."""
    columns = [item.name for item in fields(Row)]
    with destination.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


REPORT_SECTIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "Needs a decision",
        "Drift, uncommitted work, and copies that will keep diverging.",
        ("MANAGED-OWNED-DIRTY", "DUPLICATE-DRIFTED", "DRAFT-UNMANAGED"),
    ),
    (
        "Managed by this repository",
        "Owned source and upstream checkouts named by a profile.",
        ("MANAGED-OWNED", "MANAGED-UPSTREAM"),
    ),
    (
        "Available but not configured",
        "Present in a source checkout, named by no profile.",
        ("AVAILABLE-NOT-CONFIGURED",),
    ),
    (
        "Managed by another tool",
        "Written by something other than this coordinator.",
        ("OTHER-TOOL",),
    ),
    (
        "Unmanaged",
        "Project-scoped skills and superseded drafts.",
        ("UNMANAGED-PROJECT-LOCAL", "DRAFT-SUPERSEDED", "DUPLICATE-IN-SYNC"),
    ),
    (
        "Aliases and vendored copies",
        "Symlinked views of a managed source, and skills shipped inside packages.",
        ("ALIAS-OF-MANAGED-SOURCE", "VENDORED-DEP"),
    ),
)

DETAIL_COLUMNS = (
    ("skill_name", "Skill"),
    ("held_as", "Held as"),
    ("profiles", "Profiles"),
    ("installed", "Installed"),
    ("content_vs_reference", "Vs reference"),
    ("diff_lines", "Diff"),
    ("git_repo", "Repo"),
    ("git_dir_state", "Git state"),
    ("modified", "Modified"),
    ("path", "Path"),
)


def _table(rows: list[Row], columns: tuple[tuple[str, str], ...]) -> list[str]:
    header = [label for _, label in columns]
    lines = ["| " + " | ".join(header) + " |",
             "| " + " | ".join("---" for _ in header) + " |"]
    for row in rows:
        values = [str(getattr(row, key) or "—").replace("|", "\\|") for key, _ in columns]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def _counts(rows: list[Row], key: str) -> list[str]:
    tally: dict[str, int] = defaultdict(int)
    for row in rows:
        tally[str(getattr(row, key))] += 1
    lines = ["| Value | Files |", "| --- | ---: |"]
    for value, count in sorted(tally.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| `{value}` | {count} |")
    return lines


def render_store(store: Path) -> list[str]:
    """Describe the shared agent store, where the symlink-or-copy split is visible.

    The scan root holds sources; the store holds what the agents actually read. An
    entry there is either a symlink into a source checkout or a physical npx copy.
    """
    if not store.is_dir():
        return []
    lines = [
        "## Installed store",
        "",
        f"`{store}` — what Claude Code and Codex read. A symlink entry",
        "is live against its source; a directory entry is a copy fetched by npx.",
        "",
        "| Entry | Held as | Points at |",
        "| --- | --- | --- |",
    ]
    for entry in sorted(store.iterdir(), key=lambda item: item.name):
        if entry.is_symlink():
            held, target = "symlink", os.readlink(entry)
        elif entry.is_dir():
            held, target = "npx copy", "—"
        else:
            held, target = "loose file", "—"
        lines.append(f"| `{entry.name}` | {held} | `{target}` |")
    return [*lines, ""]


def render_markdown(
    rows: list[Row],
    root: Path,
    generated: str,
    discovery: Discovery,
    store: Path | None = None,
) -> str:
    """Render the annotated rows as a Markdown report grouped by verdict."""
    out: list[str] = [
        "# Skill bookkeeping",
        "",
        f"Scan root: `{root}`  ",
        f"Generated: {generated}  ",
        f"Files annotated: **{len(rows)}**",
        "",
        "## How each file is held",
        "",
        "`real-file` is a copy this folder owns. `symlinked-file` and",
        "`via-symlinked-dir` are views of a source held elsewhere, not copies.",
        "",
        *_counts(rows, "held_as"),
        "",
        "## Verdict",
        "",
        *_counts(rows, "status"),
        "",
        *(render_store(store) if store else []),
    ]
    if discovery.skipped_links or discovery.unreadable:
        out += ["## Not covered by this scan", ""]
    if discovery.skipped_links:
        out += [
            "Symlinked directories left unfollowed. Their contents are absent from",
            "every table above.",
            "",
            "| Link | Target | Reason |",
            "| --- | --- | --- |",
            *(
                f"| `{link}` | `{target or '—'}` | {reason} |"
                for link, target, reason in discovery.skipped_links
            ),
            "",
        ]
    if discovery.unreadable:
        out += [
            "Files found but not read. Not a negative result — their status is unknown.",
            "",
            "| Path | Error |",
            "| --- | --- |",
            *(f"| `{path}` | {error} |" for path, error in discovery.unreadable),
            "",
        ]
    duplicated = sorted(
        {row.skill_name for row in rows if row.copies_of_this_skill > 1}
    )
    if duplicated:
        out += [
            "## Skills held in more than one place",
            "",
            *_table(
                [row for row in rows if row.copies_of_this_skill > 1],
                (
                    ("skill_name", "Skill"),
                    ("content_vs_reference", "Vs reference"),
                    ("drift_direction", "Direction"),
                    ("diff_lines", "Diff"),
                    ("reference_copy", "Reference copy"),
                    ("path", "Path"),
                ),
            ),
            "",
        ]
    for title, blurb, statuses in REPORT_SECTIONS:
        section = [row for row in rows if row.status in statuses]
        if not section:
            continue
        out += [f"## {title}", "", blurb, "", f"{len(section)} files.", ""]
        out += _table(section, DETAIL_COLUMNS)
        out += [""]
    return "\n".join(out) + "\n"


HTML_STYLE = """
:root { color-scheme: light dark; --fg:#1a1a1a; --bg:#fff; --muted:#666;
  --line:#e0e0e0; --head:#f6f6f6; --accent:#2b5797; }
@media (prefers-color-scheme: dark) { :root { --fg:#e6e6e6; --bg:#161616;
  --muted:#9a9a9a; --line:#333; --head:#1f1f1f; --accent:#7ba7e8; } }
body { margin:0 auto; max-width:1200px; padding:2rem 1.25rem;
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,sans-serif;
  color:var(--fg); background:var(--bg); }
h1 { font-size:1.7rem; margin:0 0 .4rem; }
h2 { font-size:1.15rem; margin:2.2rem 0 .6rem; padding-bottom:.3rem;
  border-bottom:2px solid var(--accent); }
table { border-collapse:collapse; width:100%; margin:.6rem 0 1.2rem;
  font-size:13px; display:block; overflow-x:auto; }
th,td { border:1px solid var(--line); padding:.35rem .55rem; text-align:left;
  vertical-align:top; white-space:nowrap; }
th { background:var(--head); position:sticky; top:0; }
tr:hover td { background:var(--head); }
code { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.92em; }
p { color:var(--muted); }
"""


def render_html(markdown_text: str, title: str) -> str:
    """Convert the Markdown report to a self-contained HTML page."""
    import markdown

    body = markdown.markdown(markdown_text, extensions=["tables", "sane_lists"])
    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f"<title>{title}</title>\n<style>{HTML_STYLE}</style>\n"
        f"</head>\n<body>\n{body}\n</body>\n</html>\n"
    )


# ── Entry point ──────────────────────────────────────────────────────


def run(
    root: Path, out: Path, coordinator: Coordinator, *, html: bool = True
) -> list[Row]:
    """Scan ``root``, write the CSV, Markdown and HTML reports, and return the rows."""
    discovery = discover(root)
    rows = annotate(root, coordinator, discovery)
    generated = _local(None).strftime("%Y-%m-%d %H:%M")

    csv_path = out.with_suffix(".csv")
    write_csv(rows, csv_path)
    print(f"  wrote {csv_path}  ({len(rows)} rows)")

    markdown_text = render_markdown(rows, root, generated, discovery, coordinator.store)
    markdown_path = out.with_suffix(".md")
    markdown_path.write_text(markdown_text)
    print(f"  wrote {markdown_path}")

    if html:
        html_path = out.with_suffix(".html")
        html_path.write_text(render_html(markdown_text, "Skill bookkeeping"))
        print(f"  wrote {html_path}")

    tally: dict[str, int] = defaultdict(int)
    for row in rows:
        tally[row.status] += 1
    print()
    for status, count in sorted(tally.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {count:4d}  {status}")
    for link, _, reason in discovery.skipped_links:
        print(f"  SKIPPED LINK  {link}  ({reason})")
    for path, error in discovery.unreadable:
        print(f"  UNREADABLE    {path}  ({error})")
    return rows
