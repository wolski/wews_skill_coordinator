"""The pinned ``npx skills`` CLI, which installs every package without a local checkout."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import cast

from wews_skill_coordinator.console import show_command

NPX_SKILLS_VERSION = "1.5.23"


def npx_command(*arguments: str) -> list[str]:
    return ["npx", "--yes", f"skills@{NPX_SKILLS_VERSION}", *arguments]


@dataclass(frozen=True, slots=True)
class PackageSelection:
    """The skills one npx package contributes to a profile."""

    package: str
    skills: tuple[str, ...]
    full_depth: bool

    def add_command(self) -> list[str]:
        command = npx_command(
            "add",
            self.package,
            "--skill",
            *self.skills,
            "--agent",
            "claude-code",
            "codex",
            "--global",
            "--yes",
        )
        if self.full_depth:
            command.append("--full-depth")
        return command


def run_npx(command: list[str], *, dry_run: bool) -> None:
    if dry_run:
        print(f"  would run  {show_command(command)}")
        return
    subprocess.run(command, check=True, text=True)


def remove_npx_skills(skill_names: frozenset[str], *, dry_run: bool) -> None:
    if skill_names:
        run_npx(
            npx_command("remove", *sorted(skill_names), "--global", "--yes"),
            dry_run=dry_run,
        )


def update_npx_skills(*, dry_run: bool) -> None:
    run_npx(npx_command("update", "--global", "--yes"), dry_run=dry_run)


@dataclass(frozen=True, slots=True)
class InstalledSkill:
    """One entry of ``npx skills list``."""

    name: str
    agents: tuple[str, ...]


def parse_npx_list(output: str) -> list[InstalledSkill]:
    start = output.find("[\n")
    if start < 0:
        start = output.find("[")
    if start < 0:
        raise ValueError("npx skills list did not return a JSON array")
    records: object = json.loads(output[start:])
    if not isinstance(records, list):
        raise TypeError("npx skills list returned unexpected JSON")
    return [_installed_skill(record) for record in cast(list[object], records)]


def _installed_skill(record: object) -> InstalledSkill:
    if not isinstance(record, dict):
        raise TypeError("npx skills list returned a non-object entry")
    fields = cast(dict[str, object], record)
    agents = fields.get("agents", [])
    return InstalledSkill(
        name=str(fields["name"]),
        agents=tuple(map(str, cast(list[object], agents))) if isinstance(agents, list) else (),
    )


def installed_skills() -> list[InstalledSkill]:
    result = subprocess.run(
        npx_command("list", "--global", "--json"),
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_npx_list(result.stdout)
