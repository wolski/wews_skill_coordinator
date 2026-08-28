"""Inventory Claude Code's per-project memory store so stale entries can go.

Claude Code keeps memory under ``~/.claude/projects/<slug>/memory/``: one
``MEMORY.md`` index plus one file per remembered fact. The slug is the project's
absolute path with every separator flattened to ``-``, which also swallows any
``_``, ``.`` and ``-`` already in the name, so it cannot be inverted by string
substitution. This module resolves each slug against the filesystem instead, and
reports which stores belong to a directory that no longer exists.

The scan reads. Removal happens only when explicitly asked for, and only for a
store whose project directory could not be found.
"""

from __future__ import annotations

import csv
import datetime as dt
import re
import shutil
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

MEMORY_DIR_NAME = "memory"
INDEX_NAME = "MEMORY.md"
MAX_SLUG_TOKENS = 24

# How deep to look for a project that moved rather than disappeared, and what to
# refuse to walk into while looking.
RELOCATION_DEPTH = 4
SKIPPED_DIRS = frozenset({"node_modules", "__pycache__", "venv", "Library"})
MIN_LEAF_TOKEN = 4

# A slug flattens these to "-", so resolving one has to try each of them back.
SEPARATORS = ("-", "_", ".", " ")

FRONTMATTER_NAME = re.compile(r"^name:[ \t]*(.+?)[ \t]*$", re.MULTILINE)
FRONTMATTER_DESCRIPTION = re.compile(r"^description:[ \t]*(.+?)[ \t]*$", re.MULTILINE)
FRONTMATTER_TYPE = re.compile(r"^[ \t]+type:[ \t]*(.+?)[ \t]*$", re.MULTILINE)
WIKI_LINK = re.compile(r"\[\[([^\]]+)\]\]")
INDEX_LINK = re.compile(r"\]\(([^)]+\.md)\)")


@dataclass
class MemoryRow:
    """One memory file, annotated. Field order is the CSV column order."""

    verdict: str = ""
    slug: str = ""
    project_path: str = ""
    project_exists: str = ""
    role: str = ""
    name: str = ""
    memory_type: str = ""
    indexed: str = ""
    links: str = ""
    dangling_links: str = ""
    facts_in_store: int = 0
    store_bytes: int = 0
    lines: int = 0
    bytes: int = 0
    modified: str = ""
    age_days: int = 0
    path: str = ""
    action: str = ""
    description: str = ""


@dataclass
class Store:
    """One ``<slug>/memory/`` directory and what resolving its slug found."""

    slug: str
    directory: Path
    project: Path | None
    index: Path | None
    facts: list[Path] = field(default_factory=list)
    dangling_index_entries: list[str] = field(default_factory=list)
    moved_to: list[Path] = field(default_factory=list)

    @property
    def exists(self) -> bool:
        return self.project is not None

    @property
    def removable(self) -> bool:
        """Nothing claims this memory: the slug is dead and no move explains it."""
        return self.project is None and not self.moved_to


# ── Slug resolution ──────────────────────────────────────────────────


def resolve_slug(slug: str, *, base: Path = Path("/")) -> Path | None:
    """Find the directory a store slug was built from, or ``None``.

    The slug is lossy, so this searches rather than substitutes: at each level it
    tries joining one or more leading tokens with each separator a slug flattens,
    and keeps the branch the filesystem confirms. Directory existence prunes almost
    every branch immediately.
    """
    tokens = [token for token in slug.split("-") if token]
    if not tokens or len(tokens) > MAX_SLUG_TOKENS:
        return None
    return _descend(tuple(tokens), base)


def _descend(tokens: tuple[str, ...], base: Path) -> Path | None:
    if not tokens:
        return base
    for take in range(1, len(tokens) + 1):
        head = tokens[:take]
        for separator in SEPARATORS:
            candidate = base / separator.join(head)
            if not candidate.is_dir():
                continue
            found = _descend(tokens[take:], candidate)
            if found is not None:
                return found
    return None


def index_directories(root: Path, depth: int = RELOCATION_DEPTH) -> dict[str, list[Path]]:
    """Map directory name to every place it occurs under ``root``, to a bounded depth."""
    found: dict[str, list[Path]] = {}
    stack = [(root, 0)]
    while stack:
        directory, level = stack.pop()
        if level >= depth:
            continue
        try:
            entries = list(directory.iterdir())
        except OSError:
            continue
        for entry in entries:
            if not entry.is_dir() or entry.is_symlink():
                continue
            # A dot-directory holds caches and agent scratch, never a project, and
            # matching one would make a deleted project look merely moved.
            if entry.name.startswith(".") or entry.name in SKIPPED_DIRS:
                continue
            found.setdefault(entry.name, []).append(entry)
            stack.append((entry, level + 1))
    return found


def find_relocation(slug: str, names: dict[str, list[Path]]) -> list[Path]:
    """Find directories that look like the project this slug named, moved elsewhere.

    A slug stops resolving both when a project is deleted and when it is merely
    moved. Only the first is safe to remove, so the trailing tokens are matched
    against directory names seen elsewhere. The longest tail wins; a single short
    token is ignored because it matches too much to mean anything.
    """
    tokens = [token for token in slug.split("-") if token]
    for size in range(min(3, len(tokens)), 0, -1):
        tail = tokens[-size:]
        if size == 1 and len(tail[0]) < MIN_LEAF_TOKEN:
            continue
        hits = [
            path
            for separator in SEPARATORS
            for path in names.get(separator.join(tail), ())
        ]
        if hits:
            return sorted(set(hits))
    return []


# ── Discovery ────────────────────────────────────────────────────────


def find_stores(root: Path, search_root: Path | None = None) -> list[Store]:
    """Collect every ``memory/`` directory under ``root``, resolved and read."""
    names: dict[str, list[Path]] | None = None
    stores: list[Store] = []
    for directory in sorted(root.rglob(MEMORY_DIR_NAME)):
        if not directory.is_dir():
            continue
        slug = directory.parent.name
        index = directory / INDEX_NAME
        facts = sorted(
            path
            for path in directory.glob("*.md")
            if path.name != INDEX_NAME and path.is_file()
        )
        store = Store(
            slug=slug,
            directory=directory,
            project=resolve_slug(slug),
            index=index if index.is_file() else None,
            facts=facts,
        )
        if store.project is None:
            if names is None:
                names = index_directories(search_root or Path.home())
            # The store's own slug directory lives under the memory root and would
            # otherwise match its own name, making a dead store look moved.
            store.moved_to = [
                path
                for path in find_relocation(slug, names)
                if not path.is_relative_to(root)
            ]
        if store.index is not None:
            named = {path.name for path in facts}
            store.dangling_index_entries = sorted(
                {
                    target
                    for target in INDEX_LINK.findall(
                        store.index.read_text(errors="replace")
                    )
                    if target not in named
                }
            )
        stores.append(store)
    return stores


def read_metadata(text: str) -> tuple[str, str, str]:
    """Return ``(name, description, type)`` from a memory file's frontmatter."""
    if not text.startswith("---"):
        return "", "", ""
    end = text.find("\n---", 3)
    block = text[: end if end > 0 else 2000]
    name = FRONTMATTER_NAME.search(block)
    description = FRONTMATTER_DESCRIPTION.search(block)
    kind = FRONTMATTER_TYPE.search(block)
    return (
        name.group(1).strip().strip("\"'") if name else "",
        " ".join((description.group(1) if description else "").split())[:200],
        kind.group(1).strip().strip("\"'") if kind else "",
    )


# ── Annotation ───────────────────────────────────────────────────────


def _verdict(store: Store, row: MemoryRow, stale_days: int) -> tuple[str, str]:
    if store.removable:
        return (
            "PROJECT-GONE",
            "no directory matches this slug — the whole store can go",
        )
    if not store.exists:
        moved = ", ".join(str(path) for path in store.moved_to)
        return (
            "PROJECT-MOVED",
            f"the slug path is gone but the project looks moved to {moved}; kept",
        )
    if row.role == "index" and not store.facts:
        return "INDEX-WITHOUT-FACTS", "an index listing nothing; the store is empty"
    if row.role == "fact" and row.indexed == "no":
        return "UNINDEXED-FACT", "not listed in MEMORY.md, so it is never recalled"
    if row.dangling_links:
        return "DANGLING-LINKS", f"links to files that do not exist: {row.dangling_links}"
    if row.age_days > stale_days:
        return "STALE", f"untouched for {row.age_days} days"
    return "ACTIVE", "current"


def annotate(stores: list[Store], today: dt.date, stale_days: int) -> list[MemoryRow]:
    """Build one row per memory file across every store."""
    rows: list[MemoryRow] = []
    for store in stores:
        index_text = (
            store.index.read_text(errors="replace") if store.index is not None else ""
        )
        indexed_names = set(INDEX_LINK.findall(index_text))
        fact_names = {path.stem for path in store.facts}
        store_bytes = sum(path.stat().st_size for path in [*store.facts, *(
            [store.index] if store.index is not None else []
        )])

        for path in ([store.index] if store.index is not None else []) + store.facts:
            text = path.read_text(errors="replace")
            name, description, memory_type = read_metadata(text)
            role = "index" if path.name == INDEX_NAME else "fact"
            dangling = (
                store.dangling_index_entries
                if role == "index"
                else sorted(set(WIKI_LINK.findall(text)) - fact_names)
            )
            stat = path.stat()
            modified = dt.datetime.fromtimestamp(
                stat.st_mtime, tz=dt.timezone.utc
            ).astimezone()
            row = MemoryRow(
                slug=store.slug,
                project_path=str(store.project) if store.project else "",
                project_exists="yes" if store.exists else "no",
                role=role,
                name=name or path.stem,
                memory_type=memory_type,
                indexed=(
                    "n/a" if role == "index"
                    else ("yes" if path.name in indexed_names else "no")
                ),
                links=";".join(sorted(set(WIKI_LINK.findall(text)))),
                dangling_links=";".join(dangling),
                facts_in_store=len(store.facts),
                store_bytes=store_bytes,
                lines=text.count("\n") + 1,
                bytes=stat.st_size,
                modified=modified.strftime("%Y-%m-%d"),
                age_days=(today - modified.date()).days,
                path=str(path),
                description=description,
            )
            row.verdict, row.action = _verdict(store, row, stale_days)
            rows.append(row)
    rows.sort(key=lambda item: (item.verdict, item.slug, item.role != "index", item.name))
    return rows


# ── Output ───────────────────────────────────────────────────────────


def write_csv(rows: list[MemoryRow], destination: Path) -> None:
    """Write one row per memory file, with the dataclass field order as the header."""
    columns = [item.name for item in fields(MemoryRow)]
    with destination.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _table(rows: list[MemoryRow], columns: tuple[tuple[str, str], ...]) -> list[str]:
    header = [label for _, label in columns]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                str(getattr(row, key) or "—").replace("|", "\\|") for key, _ in columns
            )
            + " |"
        )
    return lines


STORE_COLUMNS = (
    ("slug", "Slug"),
    ("facts_in_store", "Facts"),
    ("store_bytes", "Bytes"),
    ("modified", "Newest"),
    ("path", "Path"),
)

FILE_COLUMNS = (
    ("slug", "Slug"),
    ("role", "Role"),
    ("name", "Name"),
    ("memory_type", "Type"),
    ("indexed", "Indexed"),
    ("age_days", "Age"),
    ("path", "Path"),
)

SECTIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "Unindexed facts",
        "On disk but absent from MEMORY.md, so nothing will ever recall them.",
        ("UNINDEXED-FACT",),
    ),
    (
        "Dangling links",
        "An index entry or a [[link]] pointing at a file that is not there.",
        ("DANGLING-LINKS",),
    ),
    (
        "Empty stores",
        "An index with no facts beside it.",
        ("INDEX-WITHOUT-FACTS",),
    ),
    ("Stale", "Untouched for longer than the staleness threshold.", ("STALE",)),
    ("Active", "Current memory.", ("ACTIVE",)),
)


def render_markdown(
    rows: list[MemoryRow], stores: list[Store], root: Path, generated: str
) -> str:
    """Render the annotated rows as a Markdown report, removable stores first."""
    gone = [store for store in stores if store.removable]
    moved = [store for store in stores if not store.exists and store.moved_to]
    gone_rows = [row for row in rows if row.verdict == "PROJECT-GONE"]
    reclaimed = sum(row.bytes for row in gone_rows)

    tally: dict[str, int] = {}
    for row in rows:
        tally[row.verdict] = tally.get(row.verdict, 0) + 1

    out = [
        "# Claude memory bookkeeping",
        "",
        f"Store root: `{root}`  ",
        f"Generated: {generated}  ",
        f"Stores: **{len(stores)}** — files: **{len(rows)}**",
        "",
        "## Verdict",
        "",
        "| Value | Files |",
        "| --- | ---: |",
        *(
            f"| `{verdict}` | {count} |"
            for verdict, count in sorted(tally.items(), key=lambda i: (-i[1], i[0]))
        ),
        "",
    ]

    out += [
        "## Removable — nothing claims this memory",
        "",
        "The slug resolves to no directory, and no directory of that name exists",
        "elsewhere. Remove with `--prune`; preview with `--prune --dry-run`.",
        "",
    ]
    if gone:
        out += [
            f"{len(gone)} stores, {len(gone_rows)} files, {reclaimed:,} bytes.",
            "",
            "| Slug | Facts | Bytes | Directory |",
            "| --- | ---: | ---: | --- |",
            *(
                f"| `{store.slug}` | {len(store.facts)} | "
                f"{sum(path.stat().st_size for path in store.facts):,} | "
                f"`{store.directory}` |"
                for store in sorted(gone, key=lambda item: item.slug)
            ),
            "",
        ]
    else:
        out += ["None — every slug resolved, or looks moved rather than deleted.", ""]

    if moved:
        out += [
            "## Kept — the project looks moved, not deleted",
            "",
            "The slug path is gone, but a directory with the same name exists",
            "elsewhere. `--prune` leaves these alone; decide each one yourself.",
            "",
            "| Slug | Facts | Now probably at |",
            "| --- | ---: | --- |",
            *(
                f"| `{store.slug}` | {len(store.facts)} | "
                + ", ".join(f"`{path}`" for path in store.moved_to)
                + " |"
                for store in sorted(moved, key=lambda item: item.slug)
            ),
            "",
        ]

    live = [store for store in stores if store.exists]
    if live:
        out += [
            "## Stores with a live project",
            "",
            "| Slug | Project | Facts |",
            "| --- | --- | ---: |",
            *(
                f"| `{store.slug}` | `{store.project}` | {len(store.facts)} |"
                for store in sorted(live, key=lambda item: item.slug)
            ),
            "",
        ]

    for title, blurb, verdicts in SECTIONS:
        section = [row for row in rows if row.verdict in verdicts]
        if not section:
            continue
        out += [f"## {title}", "", blurb, "", f"{len(section)} files.", ""]
        out += _table(section, FILE_COLUMNS)
        out += [""]
    return "\n".join(out) + "\n"


HTML_STYLE = """
:root { color-scheme: light dark; --fg:#1a1a1a; --bg:#fff; --muted:#666;
  --line:#e0e0e0; --head:#f6f6f6; --accent:#7a3b8f; }
@media (prefers-color-scheme: dark) { :root { --fg:#e6e6e6; --bg:#161616;
  --muted:#9a9a9a; --line:#333; --head:#1f1f1f; --accent:#c48bd8; } }
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
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f"<title>{title}</title>\n<style>{HTML_STYLE}</style>\n"
        f"</head>\n<body>\n{body}\n</body>\n</html>\n"
    )


# ── Pruning ──────────────────────────────────────────────────────────


def prune(stores: list[Store], *, dry_run: bool) -> tuple[int, int]:
    """Delete every store nothing can claim. Returns ``(stores, bytes)``.

    Removes only a store whose slug resolves nowhere *and* whose project name turns
    up nowhere else. A store whose project still exists, or merely looks moved, is
    left alone — as is a stale one, because staleness is a judgement this scan is
    not entitled to make.
    """
    removed = reclaimed = 0
    for store in sorted(stores, key=lambda item: item.slug):
        if not store.removable:
            continue
        size = sum(
            path.stat().st_size for path in store.directory.rglob("*") if path.is_file()
        )
        print(f"  {'would remove' if dry_run else 'removed'}  {store.directory}")
        if not dry_run:
            shutil.rmtree(store.directory)
        removed += 1
        reclaimed += size
    return removed, reclaimed


# ── Entry point ──────────────────────────────────────────────────────


def run(
    root: Path,
    out: Path,
    *,
    stale_days: int = 90,
    html: bool = True,
    prune_missing: bool = False,
    dry_run: bool = False,
) -> list[MemoryRow]:
    """Scan ``root``, write the reports, optionally prune unresolvable stores."""
    stores = find_stores(root)
    today = dt.datetime.now(tz=dt.timezone.utc).astimezone().date()
    rows = annotate(stores, today, stale_days)
    generated = today.strftime("%Y-%m-%d")

    csv_path = out.with_suffix(".csv")
    write_csv(rows, csv_path)
    print(f"  wrote {csv_path}  ({len(rows)} rows)")

    markdown_text = render_markdown(rows, stores, root, generated)
    markdown_path = out.with_suffix(".md")
    markdown_path.write_text(markdown_text)
    print(f"  wrote {markdown_path}")

    if html:
        html_path = out.with_suffix(".html")
        html_path.write_text(render_html(markdown_text, "Claude memory bookkeeping"))
        print(f"  wrote {html_path}")

    tally: dict[str, int] = {}
    for row in rows:
        tally[row.verdict] = tally.get(row.verdict, 0) + 1
    print()
    for verdict, count in sorted(tally.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {count:4d}  {verdict}")

    if prune_missing:
        print()
        removed, reclaimed = prune(stores, dry_run=dry_run)
        verb = "would free" if dry_run else "freed"
        print(f"  {removed} stores, {verb} {reclaimed:,} bytes")
    return rows
