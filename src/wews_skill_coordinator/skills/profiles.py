"""Resolve a profile into npx packages to add and local skills to link."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from wews_skill_coordinator.config.checkout import source_root
from wews_skill_coordinator.config.schema import SkillReference, SkillsConfig
from wews_skill_coordinator.skills.npx import PackageSelection


@dataclass(frozen=True, slots=True)
class LocalSkill:
    name: str
    source: str
    source_path: PurePosixPath
    directory: Path


@dataclass(frozen=True, slots=True)
class ProfileSelection:
    packages: tuple[PackageSelection, ...]
    local: tuple[LocalSkill, ...]
    missing: tuple[str, ...]
    skill_names: frozenset[str]


def resolve_profile(profile_name: str, config: SkillsConfig) -> ProfileSelection:
    if profile_name not in config.profiles:
        available = ", ".join(sorted(config.profiles)) or "none"
        raise ValueError(
            f"unknown profile {profile_name!r}; available profiles: {available}"
        )
    references = config.profile_references(profile_name)
    local_sources = config.local_sources
    npx_references: dict[str, list[SkillReference]] = {}
    local: list[LocalSkill] = []
    missing: list[str] = []
    for reference in references:
        if reference.source not in local_sources:
            npx_references.setdefault(reference.source, []).append(reference)
            continue
        directory = source_root(local_sources[reference.source]) / reference.source_path
        if (directory / "SKILL.md").is_file():
            local.append(
                LocalSkill(reference.name, reference.source, reference.source_path, directory)
            )
        else:
            missing.append(reference.identifier)
    npx_sources = config.npx_sources
    packages = tuple(
        PackageSelection(
            package=npx_sources[source_name].repo,
            skills=tuple(reference.name for reference in source_references),
            full_depth=npx_sources[source_name].full_depth,
        )
        for source_name, source_references in npx_references.items()
    )
    return ProfileSelection(
        packages=packages,
        local=tuple(local),
        missing=tuple(missing),
        skill_names=frozenset(reference.name for reference in references),
    )
