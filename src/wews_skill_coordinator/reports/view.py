"""Build the bookkeeping scan's view of skills.toml and the live install state.

The scan itself imports nothing from this repository; this module feeds it.
"""

from __future__ import annotations

from pathlib import Path

from wews_skill_coordinator import paths
from wews_skill_coordinator.config.checkout import source_root
from wews_skill_coordinator.config.schema import SkillsConfig
from wews_skill_coordinator.reports.bookkeeping import Coordinator


def read_coordinator(config: SkillsConfig) -> Coordinator:
    profiles: dict[str, set[str]] = {}
    packages: dict[str, str] = {}
    for profile_name in config.profiles:
        for reference in config.profile_references(profile_name):
            profiles.setdefault(reference.name, set()).add(profile_name)
            packages[reference.name] = config.sources[reference.source].repo

    owned: list[Path] = []
    checkouts: list[Path] = []
    for source in config.local_sources.values():
        (owned if source.owned else checkouts).append(source_root(source))
        packages.setdefault(source.repo, source.repo)

    installed: dict[str, str] = {}
    targets: dict[str, Path] = {}
    store = paths.AGENTS_SKILLS_DIR
    if store.is_dir():
        for entry in store.iterdir():
            if entry.is_symlink():
                installed[entry.name] = "symlink"
                targets[entry.name] = entry.resolve()
            elif entry.is_dir():
                installed[entry.name] = "npx-copy"
                targets[entry.name] = entry
    claude_dir = paths.CLAUDE_SKILLS_DIR
    claude = (
        frozenset(entry.name for entry in claude_dir.iterdir())
        if claude_dir.is_dir()
        else frozenset[str]()
    )
    return Coordinator(
        profiles={name: frozenset(values) for name, values in profiles.items()},
        packages=packages,
        owned_roots=tuple(owned),
        checkout_roots=tuple(checkouts),
        installed=installed,
        install_targets=targets,
        claude_links=claude,
        store=store,
    )
