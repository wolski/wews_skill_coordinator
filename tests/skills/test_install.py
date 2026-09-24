from __future__ import annotations

import subprocess
from pathlib import Path, PurePosixPath

import pytest

from tests.helpers import point_paths_at, write_skill
from wews_skill_coordinator.config.checkout import source_roots
from wews_skill_coordinator.config.load import load_config
from wews_skill_coordinator.skills.install import clean, install_profile
from wews_skill_coordinator.skills.links import install_local_skill, managed_links
from wews_skill_coordinator.skills.npx import npx_command
from wews_skill_coordinator.skills.profiles import LocalSkill


def linked() -> list[str]:
    return sorted(managed_links(source_roots(load_config())))


def install_as(configured: Path, name: str) -> Path:
    """Link the r-style directory under another name, as an earlier local install would."""
    directory = configured / "skills" / "engineering" / "skills" / "r-style"
    install_local_skill(
        LocalSkill(name, "local", PurePosixPath("engineering/skills/r-style"), directory),
        source_roots(load_config()),
        dry_run=False,
    )
    return directory


def test_uses_configured_active_profile_by_default(
    configured: Path, record_run: list[list[str]], capsys: pytest.CaptureFixture[str]
):
    install_profile(load_config(), None, dry_run=False)
    assert "installed profile: python" in capsys.readouterr().out
    assert linked() == ["python-style"]


def test_dry_run_has_no_side_effects(
    configured: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: pytest.fail("dry run executed a command")
    )
    install_profile(load_config(), "python", dry_run=True)
    output = capsys.readouterr().out
    assert "owner/public --skill clean-architecture" in output
    assert "would link     python-style ->" in output
    assert "remove" not in output  # r-style is local, so npx is never asked
    assert "installed profile: python" in output
    assert not (configured / "store" / "python-style").exists()


def test_add_failure_happens_before_local_links(
    configured: Path, monkeypatch: pytest.MonkeyPatch
):
    calls: list[list[str]] = []

    def fail_first(command: list[str], **kwargs: object) -> None:
        calls.append(command)
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(subprocess, "run", fail_first)
    with pytest.raises(subprocess.CalledProcessError):
        install_profile(load_config(), "python", dry_run=False)
    assert len(calls) == 1
    assert calls[0][3] == "add"
    assert not (configured / "store" / "python-style").exists()


def test_install_adds_and_never_removes(configured: Path, record_run: list[list[str]]):
    install_profile(load_config(), "full", dry_run=False)
    assert linked() == ["python-style", "r-style"]
    install_profile(load_config(), "python", dry_run=False)
    assert linked() == ["python-style", "r-style"]
    assert all(command[3] != "remove" for command in record_run)


def test_dropped_local_skill_is_never_sent_to_npx(
    configured: Path, record_run: list[list[str]]
):
    install_profile(load_config(), "python", dry_run=False)
    assert all("remove" not in command for command in record_run)


def test_kind_flip_to_local_removes_the_npx_entry_after_a_successful_add(
    configured: Path, monkeypatch: pytest.MonkeyPatch
):
    (configured / "store" / "python-style").mkdir()
    calls: list[list[str]] = []

    def npx(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[3] == "remove":  # stand in for what the real CLI deletes
            for name in command[4:]:
                entry = configured / "store" / name
                if entry.is_dir():
                    entry.rmdir()
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", npx)
    install_profile(load_config(), "python", dry_run=False)
    assert calls[0][3] == "add"
    assert calls[1][3:] == ["remove", "python-style", "--global", "--yes"]
    assert (configured / "store" / "python-style").is_symlink()


def test_a_failed_add_keeps_a_flipping_skill_installed(
    configured: Path, monkeypatch: pytest.MonkeyPatch
):
    """The npx entry may only go once the fetch that could replace it worked."""
    (configured / "store" / "python-style").mkdir()

    def fail_add(command: list[str], **kwargs: object) -> None:
        assert command[3] != "remove", "removed an npx skill before the fetch"
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(subprocess, "run", fail_add)
    with pytest.raises(subprocess.CalledProcessError):
        install_profile(load_config(), "python", dry_run=False)
    assert (configured / "store" / "python-style").is_dir()


def test_dry_run_of_a_kind_flip_reports_a_link_not_a_conflict(
    configured: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    (configured / "store" / "python-style").mkdir()
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: pytest.fail("dry run executed a command")
    )
    install_profile(load_config(), "python", dry_run=True)
    output = capsys.readouterr().out
    assert "would link     python-style ->" in output
    assert "CONFLICT" not in output
    assert (configured / "store" / "python-style").is_dir()


def test_kind_flip_to_npx_unlinks_first(configured: Path, monkeypatch: pytest.MonkeyPatch):
    install_as(configured, "clean-architecture")
    calls: list[list[str]] = []

    def record(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert not (configured / "store" / "clean-architecture").is_symlink()
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", record)
    install_profile(load_config(), "python", dry_run=False)
    assert calls[0][3] == "add"


def test_failed_kind_flip_to_npx_restores_local_links(
    configured: Path, monkeypatch: pytest.MonkeyPatch
):
    directory = install_as(configured, "clean-architecture")

    def fail_add(command: list[str], **kwargs: object) -> None:
        assert not (configured / "store" / "clean-architecture").is_symlink()
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(subprocess, "run", fail_add)
    with pytest.raises(subprocess.CalledProcessError):
        install_profile(load_config(), "python", dry_run=False)

    store = configured / "store" / "clean-architecture"
    assert store.is_symlink()
    assert store.resolve() == directory
    assert (configured / "claude" / "clean-architecture").readlink() == Path(
        "../../.agents/skills/clean-architecture"
    )


def test_missing_local_skill_fails_the_install_after_the_rest(
    configured: Path, record_run: list[list[str]], capsys: pytest.CaptureFixture[str]
):
    skills = configured / "skills" / "engineering" / "skills"
    (skills / "python-style").rename(skills / "renamed")
    (skills / "renamed" / "SKILL.md").write_text("---\nname: renamed\ndescription: T.\n---\n")
    with pytest.raises(SystemExit, match="absent from their checkout"):
        install_profile(load_config(), "python", dry_run=False)
    assert "MISSING        local:engineering/python-style" in capsys.readouterr().out
    assert any(command[3] == "add" for command in record_run)


def test_clean_removes_every_link_and_every_npx_skill(
    configured: Path, record_run: list[list[str]]
):
    install_profile(load_config(), "full", dry_run=False)
    (configured / "store" / "clean-architecture").mkdir()  # what the npx add left behind
    record_run.clear()
    clean(dry_run=False)
    assert record_run == [npx_command("remove", "clean-architecture", "--global", "--yes")]
    assert linked() == []
    assert not (configured / "claude" / "r-style").is_symlink()


def test_clean_needs_no_valid_skills_toml(configured: Path, record_run: list[list[str]]):
    install_profile(load_config(), "full", dry_run=False)
    (configured / "skills.toml").write_text("this is not toml [")
    clean(dry_run=False)
    assert list((configured / "store").iterdir()) == []


def test_clean_removes_a_link_skills_toml_no_longer_names(
    configured: Path, record_run: list[list[str]]
):
    target = configured / "no-longer-configured"
    target.mkdir()
    (configured / "store" / "forgotten").symlink_to(target)
    clean(dry_run=False)
    assert not (configured / "store" / "forgotten").is_symlink()
    assert target.is_dir()


def test_clean_keeps_hand_made_claude_skills(configured: Path, record_run: list[list[str]]):
    (configured / "claude" / "commit").mkdir()
    clean(dry_run=False)
    assert (configured / "claude" / "commit").is_dir()


def test_clean_dry_run_changes_nothing(
    configured: Path, record_run: list[list[str]], capsys: pytest.CaptureFixture[str]
):
    install_profile(load_config(), "full", dry_run=False)
    record_run.clear()
    clean(dry_run=True)
    assert "would unlink" in capsys.readouterr().out
    assert record_run == []
    assert linked() == ["python-style", "r-style"]


def test_relative_external_source_is_managed_and_cleaned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    root = tmp_path / "coordinator"
    root.mkdir()
    external = tmp_path / "external"
    write_skill(external, "engineering", "outside")
    config = root / "skills.toml"
    config.write_text(
        'active = "local"\n\n'
        "[sources.local]\n"
        'repo = "owner/local"\n'
        'path = "../external"\n'
        "owned = true\n\n"
        "[profiles.local]\n"
        'description = "Local"\n'
        'local = ["engineering/outside"]\n'
    )
    point_paths_at(root, config, monkeypatch)

    install_profile(load_config(), "local", dry_run=False)
    assert f"outside -> {external / 'engineering' / 'skills' / 'outside'}" in capsys.readouterr().out
    assert linked() == ["outside"]

    clean(dry_run=False)
    assert not (root / "store" / "outside").is_symlink()
    assert not (root / "claude" / "outside").is_symlink()
