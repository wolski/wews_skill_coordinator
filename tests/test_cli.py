from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from wews_skill_coordinator.cli import app
from wews_skill_coordinator.skills.npx import npx_command


def run_coord(*tokens: str) -> None:
    with pytest.raises(SystemExit) as exit_info:
        app(list(tokens))
    assert exit_info.value.code == 0


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [
        ((), ["install", "clean", "list", "update", "report"]),
        (("install",), ["skills", "plugins", "config", "--dry-run"]),
        (("install", "skills"), ["--profile", "--dry-run"]),
        (("clean",), ["skills", "plugins", "memory"]),
        (("clean", "skills"), ["all", "--dry-run"]),
        (("clean", "skills", "all"), ["PATH", "backup", "--dry-run"]),
        (("clean", "memory"), ["all", "--dry-run"]),
        (("clean", "memory", "all"), ["ROOT", "backup", "--dry-run"]),
        (("list",), ["skills", "profiles", "plugins"]),
        (("update",), ["--dry-run"]),
        (("report",), ["audit", "bookkeeping", "memory"]),
    ],
)
def test_every_group_has_help(
    tokens: tuple[str, ...], expected: list[str], capsys: pytest.CaptureFixture[str]
):
    run_coord(*tokens, "--help")
    output = capsys.readouterr().out
    assert f"Usage: coord {' '.join(tokens)}".rstrip() in output
    for word in expected:
        assert word in output


def test_bare_clean_removes_nothing(
    configured: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("clean ran a command"))
    run_coord("clean")
    assert "Usage: coord clean" in capsys.readouterr().out


def test_a_broken_skills_toml_is_a_message_not_a_traceback(
    configured: Path, capsys: pytest.CaptureFixture[str]
):
    (configured / "skills.toml").write_text('active = "missing"\n')
    with pytest.raises(SystemExit) as exit_info:
        app(["list", "profiles"])
    assert exit_info.value.code == "skills.toml: active profile 'missing' is not configured"


def test_update_skips_sources_without_a_url(configured: Path, record_run: list[list[str]]):
    app(["update"], result_action="return_value")
    assert record_run == [npx_command("update", "--global", "--yes")]
