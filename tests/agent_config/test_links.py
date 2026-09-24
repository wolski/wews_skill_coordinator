from __future__ import annotations

from pathlib import Path

import pytest

from wews_skill_coordinator import paths
from wews_skill_coordinator.agent_config.links import install


@pytest.fixture
def agent_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source = tmp_path / "agent-config"
    (source / "output-styles").mkdir(parents=True)
    (source / "AGENTS.md").write_text("# rules\n")
    (source / "output-styles" / "answer-first.md").write_text("# style\n")
    monkeypatch.setattr(paths, "AGENT_CONFIG_DIR", source)
    monkeypatch.setattr(paths, "AGENTS_MD_LINK", tmp_path / "home" / ".agents" / "AGENTS.md")
    monkeypatch.setattr(paths, "OUTPUT_STYLES_DIR", tmp_path / "home" / "output-styles")
    return tmp_path


def test_dry_run_creates_nothing(agent_config: Path, capsys: pytest.CaptureFixture[str]):
    install(dry_run=True)
    assert capsys.readouterr().out.count("would link") == 2
    assert not (agent_config / "home").exists()


def test_install_links_agents_md_and_every_style(agent_config: Path):
    install(dry_run=False)
    assert paths.AGENTS_MD_LINK.resolve() == agent_config / "agent-config" / "AGENTS.md"
    style = paths.OUTPUT_STYLES_DIR / "answer-first.md"
    assert style.resolve() == agent_config / "agent-config" / "output-styles" / "answer-first.md"


def test_a_second_install_changes_nothing(
    agent_config: Path, capsys: pytest.CaptureFixture[str]
):
    install(dry_run=False)
    capsys.readouterr()
    install(dry_run=False)
    assert capsys.readouterr().out == ""


def test_a_stale_symlink_is_replaced(agent_config: Path):
    paths.AGENTS_MD_LINK.parent.mkdir(parents=True)
    paths.AGENTS_MD_LINK.symlink_to(agent_config / "elsewhere.md")
    install(dry_run=False)
    assert paths.AGENTS_MD_LINK.resolve() == agent_config / "agent-config" / "AGENTS.md"


def test_a_real_file_is_never_replaced(
    agent_config: Path, capsys: pytest.CaptureFixture[str]
):
    paths.AGENTS_MD_LINK.parent.mkdir(parents=True)
    paths.AGENTS_MD_LINK.write_text("hand-written\n")
    install(dry_run=False)
    assert "CONFLICT" in capsys.readouterr().out
    assert paths.AGENTS_MD_LINK.read_text() == "hand-written\n"
