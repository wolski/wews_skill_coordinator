"""Show what is configured and what is installed."""

from __future__ import annotations

from wews_skill_coordinator import paths
from wews_skill_coordinator.config.checkout import source_roots
from wews_skill_coordinator.config.schema import SkillsConfig
from wews_skill_coordinator.console import print_table
from wews_skill_coordinator.skills.checkouts import source_status
from wews_skill_coordinator.skills.links import managed_links
from wews_skill_coordinator.skills.npx import installed_skills
from wews_skill_coordinator.skills.profiles import resolve_profile


def list_sources(config: SkillsConfig) -> None:
    rows: list[tuple[str, ...]] = []
    for name, source in config.local_sources.items():
        status = source_status(source)
        if status.present:
            rows.append(
                (name, source.repo, source.path, status.branch, status.head, status.behind)
            )
        else:
            rows.append((name, source.repo, source.path, "MISSING CHECKOUT", "", ""))
    print_table(
        "Local sources", ("Source", "Repository", "Path", "Branch", "Head", "Behind"), rows
    )


def list_skills(config: SkillsConfig) -> None:
    """Installed skills by kind, and which profile they match."""
    list_sources(config)
    links = managed_links(source_roots(config))
    records = installed_skills()
    rows: list[tuple[str, str, str]] = []
    for record in records:
        if record.name in links:
            continue  # a coordinator symlink, listed below with its target
        rows.append((record.name, "npx", ", ".join(record.agents)))
    rows.extend((name, "local", paths.display(target)) for name, target in links.items())
    print_table("Installed skills", ("Skill", "Kind", "Agents or source"), rows)

    installed = frozenset(record.name for record in records) | frozenset(links)
    active = installed & config.skill_names()
    matches = [
        name
        for name in config.profiles
        if resolve_profile(name, config).skill_names == active
    ]
    print(f"  configured active profile: {config.active}")
    print(f"  installed profile match: {', '.join(matches) if matches else 'none'}")
    if config.active not in matches:
        print("  WARNING: installed skills do not match the configured active profile")


def list_profiles(config: SkillsConfig) -> None:
    """Compositions with the base profiles they include, then every base profile."""
    print(f"  active: {config.active}")

    def label(name: str) -> str:
        return f"{name} *" if name == config.active else name

    print_table(
        "Compositions",
        ("Profile", "Skills", "Includes", "Description"),
        (
            (
                label(name),
                str(len(config.profile_references(name))),
                ", ".join(composition.includes),
                composition.description,
            )
            for name, composition in config.compositions.items()
        ),
    )
    print_table(
        "Base profiles",
        ("Profile", "Skills", "Description"),
        (
            (label(name), str(len(profile.references())), profile.description)
            for name, profile in config.base_profiles.items()
        ),
    )
