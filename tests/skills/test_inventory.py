from __future__ import annotations

from pathlib import Path

import pytest

from wews_skill_coordinator.config.checkout import source_roots
from wews_skill_coordinator.config.load import load_config
from wews_skill_coordinator.skills import inventory
from wews_skill_coordinator.skills.links import install_local_skill
from wews_skill_coordinator.skills.npx import InstalledSkill
from wews_skill_coordinator.skills.profiles import resolve_profile


def test_list_reports_configured_and_installed_profile(
    configured: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    config = load_config()
    selection = resolve_profile("python", config)
    install_local_skill(selection.local[0], source_roots(config), dry_run=False)
    monkeypatch.setattr(
        inventory, "installed_skills", lambda: [InstalledSkill("clean-architecture", ())]
    )

    inventory.list_skills(config)

    output = capsys.readouterr().out
    assert "configured active profile: python" in output
    assert "installed profile match: python" in output
    assert "WARNING" not in output


def test_profiles_lists_size_includes_and_description(
    configured: Path, capsys: pytest.CaptureFixture[str]
):
    inventory.list_profiles(load_config())
    output = capsys.readouterr().out
    assert "active: python" in output
    assert "Everything" in output
    assert "Python tools" in output
    rows = {line.split()[0]: line.split() for line in output.splitlines() if "│" in line}
    assert rows["full"][1:5] == ["│", "3", "│", "*"]
    assert rows["python"][1:3] == ["*", "│"]  # the active profile is starred
    assert rows["r"][1:4] == ["│", "1", "│"]
