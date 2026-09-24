from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers import write_skill
from wews_skill_coordinator.skills.sweep import clean_skill_folders, find_skill_folders


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    write_skill(root / "repo-a", "domain", "alpha")
    write_skill(root / "repo-b" / "deep" / "er", "domain", "beta")
    write_skill(root / "repo-a" / ".git", "domain", "hidden")
    write_skill(root / "repo-a" / ".venv", "domain", "hidden-too")
    nested = write_skill(root / "repo-c", "domain", "gamma")
    (nested / "evals" / "inner").mkdir(parents=True)
    (nested / "evals" / "inner" / "SKILL.md").write_text("---\nname: inner\n---\n")
    source = write_skill(tmp_path / "elsewhere", "domain", "linked")
    (root / "store").mkdir()
    (root / "store" / "linked").symlink_to(source)
    return root


def names(root: Path) -> list[tuple[str, bool]]:
    return [(skill.directory.name, skill.linked) for skill in find_skill_folders(root)]


def test_finds_every_skill_folder_once(tree: Path):
    assert sorted(names(tree)) == [
        ("alpha", False),
        ("beta", False),
        ("gamma", False),
        ("linked", True),
    ]


def test_the_search_root_itself_is_never_offered(tree: Path):
    write_skill(tree.parent, "x", "root-skill")
    assert all(skill.directory != tree.parent for skill in find_skill_folders(tree.parent))


def test_a_dry_run_lists_without_asking(
    tree: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setattr("builtins.input", lambda prompt="": pytest.fail("dry run asked"))
    clean_skill_folders(tree, dry_run=True)
    output = capsys.readouterr().out
    assert "alpha" in output and "link" in output
    assert (tree / "repo-a" / "domain" / "skills" / "alpha").is_dir()


@pytest.mark.parametrize("reply", ["", "n", "no", "anything"])
def test_anything_but_b_or_y_keeps_everything(
    tree: Path, monkeypatch: pytest.MonkeyPatch, reply: str
):
    monkeypatch.setattr("builtins.input", lambda prompt="": reply)
    clean_skill_folders(tree, dry_run=False)
    assert len(find_skill_folders(tree)) == 4


def test_y_deletes_folders_and_only_the_link_of_a_linked_one(
    tree: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
    clean_skill_folders(tree, dry_run=False)
    assert find_skill_folders(tree) == []
    assert (tree.parent / "elsewhere" / "domain" / "skills" / "linked" / "SKILL.md").is_file()
    assert (tree / "repo-a" / ".git" / "domain" / "skills" / "hidden").is_dir()


def test_b_moves_everything_under_the_suggested_backup_folder(
    tree: Path, monkeypatch: pytest.MonkeyPatch
):
    backup = tree.parent / "coord_trash"
    monkeypatch.setattr("wews_skill_coordinator.paths.BACKUP_DIR", backup)
    replies = iter(["b", ""])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(replies))
    clean_skill_folders(tree, dry_run=False)
    assert find_skill_folders(tree) == []
    (batch,) = backup.iterdir()
    assert (batch / "repo-a" / "domain" / "skills" / "alpha" / "SKILL.md").is_file()
    assert (batch / "store" / "linked").is_symlink()
