"""Remove Claude memory stores, after listing them and asking."""

from __future__ import annotations

from pathlib import Path

from wews_skill_coordinator.console import print_table
from wews_skill_coordinator.disposal import Removal, confirm_and_dispose
from wews_skill_coordinator.memory.store import Store, find_stores


def clean_unclaimed_stores(
    root: Path, *, dry_run: bool, search_root: Path | None = None
) -> None:
    """Stores whose project exists nowhere, not even moved."""
    stores = find_stores(root, search_root=search_root)
    _clean([store for store in stores if store.removable], root, dry_run=dry_run)


def clean_every_store(root: Path, *, dry_run: bool, search_root: Path | None = None) -> None:
    _clean(find_stores(root, search_root=search_root), root, dry_run=dry_run)


def _clean(stores: list[Store], root: Path, *, dry_run: bool) -> None:
    print_table(
        f"Memory stores under {root}",
        ("Store", "Facts", "Project"),
        (
            (store.slug, str(len(store.facts)), str(store.project or "not found"))
            for store in stores
        ),
    )
    confirm_and_dispose(
        [Removal(store.directory, store.directory.relative_to(root)) for store in stores],
        dry_run=dry_run,
    )
