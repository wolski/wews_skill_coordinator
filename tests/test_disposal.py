from __future__ import annotations

from pathlib import Path

import pytest

from wews_skill_coordinator import paths
from wews_skill_coordinator.disposal import Backup, Delete, Keep, ask


def replies(monkeypatch: pytest.MonkeyPatch, *answers: str) -> None:
    queue = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(queue))


@pytest.mark.parametrize("answer", ["", "n", "N", "nope", "yes please"])
def test_the_default_is_keep(monkeypatch: pytest.MonkeyPatch, answer: str):
    replies(monkeypatch, answer)
    assert isinstance(ask(3), Keep)


def test_y_deletes(monkeypatch: pytest.MonkeyPatch):
    replies(monkeypatch, " Y ")
    assert isinstance(ask(3), Delete)


def test_b_suggests_the_coord_trash(monkeypatch: pytest.MonkeyPatch):
    replies(monkeypatch, "b", "")
    assert ask(3) == Backup(paths.BACKUP_DIR)


def test_b_takes_another_folder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    replies(monkeypatch, "b", str(tmp_path / "keep-here"))
    assert ask(3) == Backup(tmp_path / "keep-here")


def test_no_terminal_means_keep(monkeypatch: pytest.MonkeyPatch):
    def closed(prompt: str = "") -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", closed)
    assert isinstance(ask(3), Keep)
