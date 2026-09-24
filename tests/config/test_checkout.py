from __future__ import annotations

from pathlib import Path

import pytest

from wews_skill_coordinator import paths
from wews_skill_coordinator.config.checkout import source_root, source_roots
from wews_skill_coordinator.config.load import load_config
from wews_skill_coordinator.config.schema import LocalSource


def test_a_skill_on_disk_but_not_in_skills_toml_is_ignored(configured: Path):
    extra = configured / "skills" / "engineering" / "skills" / "extra"
    extra.mkdir()
    (extra / "SKILL.md").write_text("---\nname: extra\ndescription: T.\n---\n")
    stray = configured / "skills" / "loose"
    stray.mkdir()
    (stray / "SKILL.md").write_text("---\nname: loose\ndescription: T.\n---\n")
    assert "extra" not in load_config().skill_names()


def test_source_roots_are_the_checkout_and_every_local_source(configured: Path):
    assert source_roots(load_config()) == (configured, configured / "skills")


def test_relative_source_path_resolves_outside_the_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(paths, "ROOT", tmp_path / "coordinator")
    assert source_root(LocalSource(repo="a/a", path="../external")) == tmp_path / "external"
