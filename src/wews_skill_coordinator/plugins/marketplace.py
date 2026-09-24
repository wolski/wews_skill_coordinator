"""Install, remove, and list the Claude Code plugins named in skills.toml."""

from __future__ import annotations

import subprocess

from wews_skill_coordinator.config.schema import SkillsConfig
from wews_skill_coordinator.console import show_command


def _run(command: list[str], *, dry_run: bool) -> None:
    if dry_run:
        print(f"  would run  {show_command(command)}")
        return
    subprocess.run(command, check=True)


def install(config: SkillsConfig, *, dry_run: bool) -> None:
    for marketplace, source in config.plugins.items():
        for plugin in source.names:
            _run(["claude", "plugin", "install", f"{plugin}@{marketplace}"], dry_run=dry_run)


def remove(config: SkillsConfig, *, dry_run: bool) -> None:
    for source in config.plugins.values():
        for plugin in source.names:
            _run(["claude", "plugin", "uninstall", plugin], dry_run=dry_run)


def list_installed() -> None:
    subprocess.run(["claude", "plugin", "list"], check=False)
