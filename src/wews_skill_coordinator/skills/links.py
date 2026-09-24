"""Symlinks that install local skills into the shared store and Claude Code's directory."""

from __future__ import annotations

import os
from pathlib import Path

from wews_skill_coordinator import paths
from wews_skill_coordinator.console import report
from wews_skill_coordinator.skills.profiles import LocalSkill

# Claude Code reads its own directory; npx points it at the shared store with
# exactly this relative link, and locally installed skills match that layout.
CLAUDE_LINK_PREFIX = "../../.agents/skills"


def _real_target(link: Path) -> Path:
    """Resolve a symlink even when it dangles, so removal stays possible."""
    return Path(os.path.realpath(link))


def _is_managed(link: Path, roots: tuple[Path, ...]) -> bool:
    if not link.is_symlink():
        return False
    target = _real_target(link)
    return any(root == target or root in target.parents for root in roots)


def managed_links(roots: tuple[Path, ...]) -> dict[str, Path]:
    """Coordinator-installed store entries, keyed by skill name."""
    store = paths.AGENTS_SKILLS_DIR
    if not store.is_dir():
        return {}
    return {
        entry.name: _real_target(entry)
        for entry in sorted(store.iterdir())
        if _is_managed(entry, roots)
    }


def npx_store_names() -> frozenset[str]:
    """Store entries npx owns: real directories, never symlinks."""
    store = paths.AGENTS_SKILLS_DIR
    if not store.is_dir():
        return frozenset()
    return frozenset(
        entry.name
        for entry in store.iterdir()
        if entry.is_dir() and not entry.is_symlink()
    )


def _link(link: Path, target: str | Path, *, dry_run: bool) -> None:
    if dry_run:
        return
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target)


def _unlink(link: Path, *, dry_run: bool) -> None:
    if not dry_run:
        link.unlink()


def _claude_link_is_managed(name: str) -> bool:
    link = paths.CLAUDE_SKILLS_DIR / name
    return link.is_symlink() and link.readlink() == Path(f"{CLAUDE_LINK_PREFIX}/{name}")


def _ensure_claude_link(name: str, *, dry_run: bool) -> None:
    link = paths.CLAUDE_SKILLS_DIR / name
    if _claude_link_is_managed(name):
        return
    if link.is_symlink() or link.exists():
        print(f"  CONFLICT       {name} (unmanaged entry in {paths.CLAUDE_SKILLS_DIR})")
        return
    report("link", "linked", f"{name} ({paths.CLAUDE_SKILLS_DIR})", dry_run=dry_run)
    _link(link, f"{CLAUDE_LINK_PREFIX}/{name}", dry_run=dry_run)


def install_local_skill(
    skill: LocalSkill,
    roots: tuple[Path, ...],
    *,
    dry_run: bool,
    replacing: frozenset[str] = frozenset(),
) -> None:
    """Point the shared store and Claude Code at one working-copy directory.

    ``replacing`` names store entries the caller has already removed. A dry run
    performs no removal, so without it every kind flip would report a conflict
    against an entry that a real run would have deleted first.
    """
    store = paths.AGENTS_SKILLS_DIR / skill.name
    freed = skill.name in replacing
    if store.is_symlink() and not freed:
        if _real_target(store) == skill.directory:
            _ensure_claude_link(skill.name, dry_run=dry_run)
            return
        if not _is_managed(store, roots):
            print(f"  CONFLICT       {skill.name} (foreign symlink, skipping)")
            return
        report("relink", "relinked", skill.name, dry_run=dry_run)
        _unlink(store, dry_run=dry_run)
    elif store.exists() and not freed:
        print(f"  CONFLICT       {skill.name} (npx-installed, skipping)")
        return
    else:
        target = paths.display(skill.directory)
        report("link", "linked", f"{skill.name} -> {target}", dry_run=dry_run)
    _link(store, skill.directory, dry_run=dry_run)
    _ensure_claude_link(skill.name, dry_run=dry_run)


def remove_local_skill(name: str, roots: tuple[Path, ...], *, dry_run: bool) -> None:
    """Drop the agent link first so the store link stays identifiable."""
    if _claude_link_is_managed(name):
        _unlink(paths.CLAUDE_SKILLS_DIR / name, dry_run=dry_run)
    store = paths.AGENTS_SKILLS_DIR / name
    if _is_managed(store, roots):
        report("unlink", "unlinked", name, dry_run=dry_run)
        _unlink(store, dry_run=dry_run)


def remove_local_skills(
    names: frozenset[str], roots: tuple[Path, ...], *, dry_run: bool
) -> None:
    for name in sorted(names):
        remove_local_skill(name, roots, dry_run=dry_run)


def remove_every_link(*, dry_run: bool) -> None:
    """Remove every symlink in the shared store, and its Claude link.

    npx only ever writes real directories there, so every symlink is ours or
    hand-made; removing a link never deletes the directory it points at.
    """
    store = paths.AGENTS_SKILLS_DIR
    if not store.is_dir():
        return
    for entry in sorted(store.iterdir()):
        if not entry.is_symlink():
            continue
        if _claude_link_is_managed(entry.name):
            _unlink(paths.CLAUDE_SKILLS_DIR / entry.name, dry_run=dry_run)
        report("unlink", "unlinked", entry.name, dry_run=dry_run)
        _unlink(entry, dry_run=dry_run)


def remove_dangling_claude_links(names: frozenset[str]) -> None:
    """Drop Claude links left pointing at store entries that are gone."""
    for name in sorted(names):
        if _claude_link_is_managed(name) and not (paths.AGENTS_SKILLS_DIR / name).exists():
            (paths.CLAUDE_SKILLS_DIR / name).unlink()


def restore_local_links(links: dict[str, Path]) -> None:
    """Restore removed local links after an npx installation fails."""
    for name, target in links.items():
        store = paths.AGENTS_SKILLS_DIR / name
        if store.is_symlink() or store.exists():
            _ensure_claude_link(name, dry_run=False)
            continue
        report("restore", "restored", f"{name} -> {paths.display(target)}", dry_run=False)
        _link(store, target, dry_run=False)
        _ensure_claude_link(name, dry_run=False)
