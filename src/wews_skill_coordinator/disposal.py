"""Ask what to do with paths about to go, then keep, back up, or delete them."""

from __future__ import annotations

import datetime as dt
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePath

from wews_skill_coordinator import paths


@dataclass(frozen=True, slots=True)
class Removal:
    """A path to remove, and where it lands inside a backup folder."""

    path: Path
    relative: PurePath


class Keep:
    def dispose(self, removals: list[Removal]) -> None:
        print("  kept everything")


class Delete:
    def dispose(self, removals: list[Removal]) -> None:
        for removal in removals:
            _delete(removal.path)
            print(f"  deleted        {removal.path}")


@dataclass(frozen=True, slots=True)
class Backup:
    folder: Path

    def dispose(self, removals: list[Removal]) -> None:
        batch = self.folder / dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
        for removal in removals:
            destination = batch / removal.relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(removal.path, destination)
            print(f"  moved          {removal.path} -> {destination}")


def _delete(path: Path) -> None:
    """Remove a link or a file itself, and a real directory with its contents."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)


def ask(count: int) -> Keep | Backup | Delete:
    """n (default) keeps, b moves to a backup folder, y deletes permanently."""
    try:
        answer = input(f"Remove these {count}? [n]o / [b]ackup / [y]es delete (default n): ")
        answer = answer.strip().lower()
        if answer == "y":
            return Delete()
        if answer == "b":
            folder = input(f"Back up to [{paths.BACKUP_DIR}]: ").strip()
            return Backup(Path(folder).expanduser() if folder else paths.BACKUP_DIR)
    except EOFError:
        print()
    return Keep()


def confirm_and_dispose(removals: list[Removal], *, dry_run: bool) -> None:
    """Ask once for everything listed; a dry run only lists."""
    if not removals:
        print("  nothing found")
    elif not dry_run:
        ask(len(removals)).dispose(removals)
