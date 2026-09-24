"""Clone and fast-forward the working copies behind local sources."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from wews_skill_coordinator.config.checkout import source_root
from wews_skill_coordinator.config.schema import LocalSource, SkillsConfig
from wews_skill_coordinator.console import report


@dataclass(frozen=True, slots=True)
class SourceStatus:
    present: bool
    branch: str
    head: str
    behind: str


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def source_status(source: LocalSource) -> SourceStatus:
    root = source_root(source)
    if not root.is_dir():
        return SourceStatus(False, "", "", "")
    return SourceStatus(
        present=True,
        branch=git(root, "rev-parse", "--abbrev-ref", "HEAD") or "unknown",
        head=git(root, "rev-parse", "--short", "HEAD") or "unknown",
        behind=git(root, "rev-list", "--count", "HEAD..@{upstream}") or "?",
    )


def clone(config: SkillsConfig, *, dry_run: bool) -> None:
    """Clone every missing checkout that declares a git_url."""
    for source_name, source in config.local_sources.items():
        root = source_root(source)
        if root.is_dir():
            print(f"  exists         {source_name}  ({source.path})")
            continue
        if source.git_url is None:
            print(f"  NO-URL         {source_name}  ({source.path})")
            continue
        report("clone", "cloned", f"{source_name} -> {source.path}", dry_run=dry_run)
        if not dry_run:
            subprocess.run(["git", "clone", source.git_url, str(root)], check=True)


def pull(config: SkillsConfig, *, dry_run: bool) -> None:
    """Fast-forward every present checkout that declares a git_url."""
    for source_name, source in config.local_sources.items():
        root = source_root(source)
        if source.git_url is None or not root.is_dir():
            continue
        report("pull", "pulling", source_name, dry_run=dry_run)
        if dry_run:
            continue
        result = subprocess.run(
            ["git", "-C", str(root), "pull", "--ff-only"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            print(f"  WARNING: pull failed for {source_name} (check it manually)")
        else:
            print(f"  {'pulled':14s} {source_name}")
