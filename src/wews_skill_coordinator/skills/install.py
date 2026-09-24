"""Install a profile's skills, or remove every installed skill."""

from __future__ import annotations

from wews_skill_coordinator.config.checkout import source_roots
from wews_skill_coordinator.config.schema import SkillsConfig
from wews_skill_coordinator.skills.links import (
    install_local_skill,
    managed_links,
    npx_store_names,
    remove_dangling_claude_links,
    remove_every_link,
    remove_local_skills,
    restore_local_links,
)
from wews_skill_coordinator.skills.npx import remove_npx_skills, run_npx
from wews_skill_coordinator.skills.profiles import resolve_profile


def install_profile(config: SkillsConfig, profile: str | None, *, dry_run: bool) -> None:
    """Install ``profile`` (default: the active one). Removes nothing else; `clean` does that."""
    selected_profile = profile or config.active
    selection = resolve_profile(selected_profile, config)
    roots = source_roots(config)
    local_names = frozenset(skill.name for skill in selection.local)
    npx_names = frozenset(
        name for package in selection.packages for name in package.skills
    )

    # A name moving from a checkout to npx must free the store path before npx
    # writes there. Preserve its target so a failed fetch can restore the active set.
    flipped_to_npx = {
        name: target
        for name, target in managed_links(roots).items()
        if name in npx_names
    }
    remove_local_skills(frozenset(flipped_to_npx), roots, dry_run=dry_run)

    # Every fallible fetch runs before anything that a fetch would be needed to
    # undo, so a failed source leaves the active set intact.
    try:
        for package in selection.packages:
            run_npx(package.add_command(), dry_run=dry_run)
    except BaseException:
        if not dry_run:
            restore_local_links(flipped_to_npx)
        raise

    # Only now discard npx directories for names that became local: until the
    # symlink replaces them they are the only copy, and restoring one costs a fetch.
    flipped_to_local = local_names & npx_store_names()
    remove_npx_skills(flipped_to_local, dry_run=dry_run)
    for skill in selection.local:
        install_local_skill(skill, roots, dry_run=dry_run, replacing=flipped_to_local)
    for identifier in selection.missing:
        print(f"  MISSING        {identifier} (not in its source checkout)")
    print(f"  installed profile: {selected_profile}")
    if selection.missing:
        raise SystemExit(
            f"{len(selection.missing)} configured skill(s) absent from their checkout"
        )


def clean(*, dry_run: bool) -> None:
    """Remove every installed skill from the shared store, without reading skills.toml.

    Symlinks go directly; npx's directories go through npx. Real directories in
    Claude Code's own skill folder are hand-made and stay.
    """
    remove_every_link(dry_run=dry_run)
    npx_names = npx_store_names()
    remove_npx_skills(npx_names, dry_run=dry_run)
    if not dry_run:
        remove_dangling_claude_links(npx_names)
