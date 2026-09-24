"""Read skills.toml into a validated SkillsConfig."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from wews_skill_coordinator import paths
from wews_skill_coordinator.config.schema import PROFILE_FIELDS, SkillsConfig


def load_config(path: Path | None = None) -> SkillsConfig:
    with (path or paths.CONF_TOML).open("rb") as stream:
        return parse_config(tomllib.load(stream))


def parse_config(document: dict[str, Any]) -> SkillsConfig:
    """A profile table with ``includes`` is a composition; any other key names a source."""
    profiles = {
        name: _profile_fields(name, table)
        for name, table in document.get("profiles", {}).items()
    }
    return SkillsConfig.model_validate({**document, "profiles": profiles})


def _profile_fields(name: str, table: dict[str, Any]) -> dict[str, Any]:
    fields = {key: value for key, value in table.items() if key in PROFILE_FIELDS}
    skills = {key: value for key, value in table.items() if key not in PROFILE_FIELDS}
    if "includes" not in fields:
        return {**fields, "skills": skills}
    if skills:
        raise ValueError(
            f"profile {name!r} has both includes and skills; a composition lists "
            f"base profiles only, so move {sorted(skills)} into a base profile"
        )
    return fields
