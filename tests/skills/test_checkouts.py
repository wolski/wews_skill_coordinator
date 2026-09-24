from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.helpers import point_paths_at
from wews_skill_coordinator.config.load import load_config
from wews_skill_coordinator.skills.checkouts import clone, pull, source_status

REMOTE_SOURCE_TOML = (
    'active = "one"\n\n'
    "[sources.a]\n"
    'repo = "a/a"\n'
    'path = "checkout"\n'
    'git_url = "https://example.invalid/a.git"\n\n'
    "[profiles.one]\n"
    'description = "One"\n'
    'a = ["domain/one"]\n'
)


@pytest.fixture
def remote_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    config = tmp_path / "skills.toml"
    config.write_text(REMOTE_SOURCE_TOML)
    point_paths_at(tmp_path, config, monkeypatch)
    return tmp_path


def test_clone_reports_an_existing_checkout(
    configured: Path, capsys: pytest.CaptureFixture[str]
):
    clone(load_config(), dry_run=False)
    assert "exists         local" in capsys.readouterr().out


def test_clone_fetches_a_missing_checkout(
    remote_source: Path, record_run: list[list[str]]
):
    clone(load_config(), dry_run=False)
    assert record_run == [
        ["git", "clone", "https://example.invalid/a.git", str(remote_source / "checkout")]
    ]


def test_clone_reports_a_source_without_a_url(
    configured: Path, capsys: pytest.CaptureFixture[str]
):
    (configured / "skills").rename(configured / "hidden")
    clone(load_config(), dry_run=False)
    assert "NO-URL         local" in capsys.readouterr().out


def test_pull_skips_sources_without_a_url(configured: Path, record_run: list[list[str]]):
    pull(load_config(), dry_run=False)
    assert record_run == []


def test_failed_pull_is_not_reported_as_pulled(
    remote_source: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    (remote_source / "checkout").mkdir()
    monkeypatch.setattr(
        subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, 1)
    )
    pull(load_config(), dry_run=False)
    output = capsys.readouterr().out
    assert "pulling        a" in output
    assert "WARNING: pull failed for a" in output
    assert "pulled         a" not in output


def test_source_status_of_a_non_repository(configured: Path):
    status = source_status(load_config().local_sources["local"])
    assert status.present
    assert status.branch == "unknown"
