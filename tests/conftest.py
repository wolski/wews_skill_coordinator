from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.helpers import CONFIG_TOML, LOCAL_SKILL_NAMES, point_paths_at, write_skill


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    path = tmp_path / "skills.toml"
    path.write_text(CONFIG_TOML)
    return path


@pytest.fixture
def configured(config_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A coordinator rooted at tmp_path with both local skills on disk."""
    point_paths_at(tmp_path, config_file, monkeypatch)
    for name in LOCAL_SKILL_NAMES:
        write_skill(tmp_path / "skills", "engineering", name)
    (tmp_path / "store").mkdir()
    (tmp_path / "claude").mkdir()
    return tmp_path


@pytest.fixture
def record_run(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []

    def record(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", record)
    return calls
