from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest

from tests.helpers import write_skill
from wews_skill_coordinator.skills.links import (
    install_local_skill,
    managed_links,
    npx_store_names,
    remove_local_skill,
)
from wews_skill_coordinator.skills.profiles import LocalSkill


def roots(root: Path) -> tuple[Path, ...]:
    return (root, root / "skills")


def local_skill(root: Path, name: str) -> LocalSkill:
    return LocalSkill(
        name=name,
        source="local",
        source_path=PurePosixPath(f"engineering/skills/{name}"),
        directory=root / "skills" / "engineering" / "skills" / name,
    )


def test_install_creates_store_and_agent_links(configured: Path):
    skill = local_skill(configured, "r-style")
    install_local_skill(skill, roots(configured), dry_run=False)
    store = configured / "store" / "r-style"
    assert store.is_symlink()
    assert store.resolve() == skill.directory
    assert (configured / "claude" / "r-style").readlink() == Path(
        "../../.agents/skills/r-style"
    )
    assert managed_links(roots(configured)) == {"r-style": skill.directory}


def test_install_is_idempotent(configured: Path, capsys: pytest.CaptureFixture[str]):
    skill = local_skill(configured, "r-style")
    install_local_skill(skill, roots(configured), dry_run=False)
    capsys.readouterr()
    install_local_skill(skill, roots(configured), dry_run=False)
    assert capsys.readouterr().out == ""
    assert managed_links(roots(configured)) == {"r-style": skill.directory}


def test_install_relinks_a_moved_source(configured: Path):
    install_local_skill(local_skill(configured, "r-style"), roots(configured), dry_run=False)
    moved = write_skill(configured / "skills", "science", "r-style")
    install_local_skill(
        LocalSkill("r-style", "local", PurePosixPath("science/skills/r-style"), moved),
        roots(configured),
        dry_run=False,
    )
    assert (configured / "store" / "r-style").resolve() == moved


def test_install_refuses_to_clobber_an_npx_directory(
    configured: Path, capsys: pytest.CaptureFixture[str]
):
    (configured / "store" / "r-style").mkdir()
    install_local_skill(local_skill(configured, "r-style"), roots(configured), dry_run=False)
    assert "CONFLICT" in capsys.readouterr().out
    assert not (configured / "store" / "r-style").is_symlink()


def test_install_refuses_to_clobber_a_foreign_symlink(
    configured: Path, capsys: pytest.CaptureFixture[str]
):
    outside = configured.parent / "elsewhere"
    outside.mkdir()
    (configured / "store" / "r-style").symlink_to(outside)
    install_local_skill(local_skill(configured, "r-style"), roots(configured), dry_run=False)
    assert "CONFLICT" in capsys.readouterr().out
    assert (configured / "store" / "r-style").resolve() == outside


def test_install_reports_an_unmanaged_agent_entry(
    configured: Path, capsys: pytest.CaptureFixture[str]
):
    (configured / "claude" / "r-style").mkdir()
    install_local_skill(local_skill(configured, "r-style"), roots(configured), dry_run=False)
    assert "CONFLICT" in capsys.readouterr().out
    assert (configured / "store" / "r-style").is_symlink()
    assert (configured / "claude" / "r-style").is_dir()


def test_dry_run_writes_nothing(configured: Path, capsys: pytest.CaptureFixture[str]):
    install_local_skill(local_skill(configured, "r-style"), roots(configured), dry_run=True)
    assert "would link" in capsys.readouterr().out
    assert not (configured / "store" / "r-style").exists()
    assert not (configured / "claude" / "r-style").exists()


def test_remove_drops_both_links(configured: Path):
    install_local_skill(local_skill(configured, "r-style"), roots(configured), dry_run=False)
    remove_local_skill("r-style", roots(configured), dry_run=False)
    assert not (configured / "store" / "r-style").is_symlink()
    assert not (configured / "claude" / "r-style").is_symlink()
    assert managed_links(roots(configured)) == {}


def test_remove_survives_a_dangling_source(configured: Path):
    skill = local_skill(configured, "r-style")
    install_local_skill(skill, roots(configured), dry_run=False)
    for child in sorted(skill.directory.iterdir()):
        child.unlink()
    skill.directory.rmdir()
    assert managed_links(roots(configured)) == {"r-style": skill.directory}
    remove_local_skill("r-style", roots(configured), dry_run=False)
    assert not (configured / "store" / "r-style").is_symlink()


def test_remove_leaves_unmanaged_entries_alone(configured: Path):
    (configured / "store" / "clean-architecture").mkdir()
    (configured / "claude" / "commit").mkdir()
    remove_local_skill("clean-architecture", roots(configured), dry_run=False)
    remove_local_skill("commit", roots(configured), dry_run=False)
    assert (configured / "store" / "clean-architecture").is_dir()
    assert (configured / "claude" / "commit").is_dir()


def test_store_classification_ignores_stray_files(configured: Path):
    install_local_skill(local_skill(configured, "r-style"), roots(configured), dry_run=False)
    (configured / "store" / "clean-architecture").mkdir()
    (configured / "store" / "python-style.skill").write_text("stray")
    assert npx_store_names() == {"clean-architecture"}
    assert sorted(managed_links(roots(configured))) == ["r-style"]
