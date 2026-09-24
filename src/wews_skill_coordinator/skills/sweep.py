"""Find every skill folder under a directory, for removal on request."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from wews_skill_coordinator.console import print_table
from wews_skill_coordinator.disposal import Removal, confirm_and_dispose

SKIPPED_DIRECTORIES = frozenset({".git", ".venv", "node_modules", "__pycache__"})


@dataclass(frozen=True, slots=True)
class FoundSkill:
    directory: Path
    linked: bool


def find_skill_folders(root: Path) -> list[FoundSkill]:
    """Every folder below ``root`` holding a SKILL.md, without descending into one.

    A symlinked folder is reported as a link and never followed, so removing it
    removes the link and leaves its target alone.
    """
    found: list[FoundSkill] = []
    for current, directory_names, _ in os.walk(root):
        descend: list[str] = []
        for name in sorted(directory_names):
            if name in SKIPPED_DIRECTORIES:
                continue
            child = Path(current) / name
            if (child / "SKILL.md").is_file():
                found.append(FoundSkill(child, child.is_symlink()))
            elif not child.is_symlink():
                descend.append(name)
        directory_names[:] = descend
    return found


def clean_skill_folders(root: Path, *, dry_run: bool) -> None:
    """List every skill folder under ``root`` and ask whether to remove them."""
    found = find_skill_folders(root)
    print_table(
        f"Skill folders under {root}",
        ("Skill folder", "Kind"),
        ((str(skill.directory.relative_to(root)), "link" if skill.linked else "folder") for skill in found),
    )
    confirm_and_dispose(
        [Removal(skill.directory, skill.directory.relative_to(root)) for skill in found],
        dry_run=dry_run,
    )
