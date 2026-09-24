from __future__ import annotations

from pathlib import Path

import pytest

from tests.memory.test_store import fact, make_store, slug_of
from wews_skill_coordinator.memory.cleanup import (
    clean_every_store,
    clean_unclaimed_stores,
)


def answer(monkeypatch: pytest.MonkeyPatch, *replies: str) -> None:
    queue = list(replies)
    monkeypatch.setattr("builtins.input", lambda prompt="": queue.pop(0))


@pytest.fixture
def two_stores(tmp_path: Path) -> tuple[Path, Path]:
    """One store whose project exists, one whose project exists nowhere."""
    target = tmp_path / "live"
    target.mkdir()
    live = make_store(tmp_path / "store", slug_of(target).lstrip("-"), facts={"a": fact("a")})
    gone = make_store(tmp_path / "store", "absent-xyz", facts={"b": fact("b")})
    return live, gone


def test_a_dry_run_asks_nothing_and_deletes_nothing(
    tmp_path: Path, two_stores: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("builtins.input", lambda prompt="": pytest.fail("dry run asked"))
    clean_unclaimed_stores(tmp_path / "store", dry_run=True, search_root=tmp_path)
    assert all(store.is_dir() for store in two_stores)


def test_only_the_unclaimed_store_is_offered(
    tmp_path: Path, two_stores: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
):
    live, gone = two_stores
    answer(monkeypatch, "y")
    clean_unclaimed_stores(tmp_path / "store", dry_run=False, search_root=tmp_path)
    assert live.is_dir()
    assert not gone.exists()


def test_a_moved_project_is_not_offered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "elsewhere" / "absent-xyz").mkdir(parents=True)
    store = make_store(tmp_path / "store", "absent-xyz", facts={"b": fact("b")})
    monkeypatch.setattr("builtins.input", lambda prompt="": pytest.fail("nothing to ask about"))
    clean_unclaimed_stores(tmp_path / "store", dry_run=False, search_root=tmp_path)
    assert store.is_dir()


def test_all_offers_every_store_and_backs_them_up(
    tmp_path: Path, two_stores: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
):
    backup = tmp_path / "backup"
    answer(monkeypatch, "b", str(backup))
    clean_every_store(tmp_path / "store", dry_run=False, search_root=tmp_path)
    assert not any(store.exists() for store in two_stores)
    (batch,) = backup.iterdir()
    assert sorted(path.parent.name for path in batch.glob("*/memory")) == sorted(
        store.parent.name for store in two_stores
    )
