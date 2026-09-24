from __future__ import annotations

from pathlib import Path

import pytest

from wews_skill_coordinator.config.load import load_config
from wews_skill_coordinator.config.schema import BaseProfile, LocalSource, SkillsConfig
from wews_skill_coordinator.skills.npx import NPX_SKILLS_VERSION, PackageSelection
from wews_skill_coordinator.skills.profiles import resolve_profile


def test_full_selects_everything(configured: Path):
    selection = resolve_profile("full", load_config())
    assert selection.skill_names == {"python-style", "r-style", "clean-architecture"}


def test_selection_splits_local_from_npx(configured: Path):
    selection = resolve_profile("python", load_config())
    assert [(item.package, item.skills, item.full_depth) for item in selection.packages] == [
        ("owner/public", ("clean-architecture",), True)
    ]
    assert [skill.name for skill in selection.local] == ["python-style"]
    assert selection.missing == ()


def test_local_skill_absent_from_checkout_is_reported_missing(configured: Path):
    moved = configured / "skills" / "science" / "skills" / "r-style"
    moved.parent.mkdir(parents=True)
    (configured / "skills" / "engineering" / "skills" / "r-style").rename(moved)
    config = SkillsConfig(
        active="one",
        sources={"local": LocalSource(repo="owner/local", path="skills")},
        profiles={"one": BaseProfile(description="One", skills={"local": ["engineering/r-style"]})},
    )
    selection = resolve_profile("one", config)
    assert selection.missing == ("local:engineering/r-style",)
    assert selection.local == ()


def test_composition_deduplicates_references(configured: Path):
    selection = resolve_profile("full", load_config())
    assert len(selection.skill_names) == 3
    assert sorted(skill.name for skill in selection.local) == ["python-style", "r-style"]


def test_unknown_profile(configured: Path):
    with pytest.raises(ValueError, match="unknown profile"):
        resolve_profile("missing", load_config())


def test_package_command_targets_both_agents():
    command = PackageSelection("owner/repo", ("a", "b"), True).add_command()
    assert command[:3] == ["npx", "--yes", f"skills@{NPX_SKILLS_VERSION}"]
    assert command[3:8] == ["add", "owner/repo", "--skill", "a", "b"]
    assert command[-1] == "--full-depth"
    assert command[command.index("--agent") + 1 : command.index("--global")] == [
        "claude-code",
        "codex",
    ]
