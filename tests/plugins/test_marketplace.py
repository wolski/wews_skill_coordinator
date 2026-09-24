from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from wews_skill_coordinator.config.load import load_config
from wews_skill_coordinator.plugins.marketplace import install, remove


def test_dry_run_runs_nothing(
    configured: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: pytest.fail("dry run executed a command")
    )
    install(load_config(), dry_run=True)
    assert "claude plugin install plugin-a@market" in capsys.readouterr().out


def test_remove_uninstalls_each_plugin(configured: Path, record_run: list[list[str]]):
    remove(load_config(), dry_run=False)
    assert record_run == [["claude", "plugin", "uninstall", "plugin-a"]]
