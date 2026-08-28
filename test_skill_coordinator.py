"""Tests for the mixed npx and local-checkout skills coordinator."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

import skill_coordinator
from skill_coordinator import (
    LocalSkill,
    PackageOptions,
    PackageSelection,
    PluginSource,
    Profile,
    SkillReference,
    SkillsConfig,
    Source,
    all_skill_names,
    all_skill_references,
    install_local_skill,
    load_config,
    local_skill_names,
    managed_links,
    npx_skill_names,
    npx_store_names,
    read_coordinator,
    remove_local_skill,
    resolve_profile,
    source_inventory,
    source_roots,
    validate_sources,
)

CONFIG_TOML = """\
[plugins.market]
names = ["plugin-a"]

[package_options."owner/public"]
full_depth = true

[sources."owner/local"]
path = "skills"
owned = true

[profiles.full]
description = "Everything"
includes = ["*"]

[profiles.python-style]
description = "Python style"
skills = ["owner/local@python-style"]

[profiles.r]
description = "R tools"
skills = ["owner/local@r-style"]

[profiles.python]
description = "Python tools"
includes = ["python-style"]
skills = ["owner/public@clean-architecture"]
"""

LOCAL_SKILL_NAMES = ("python-style", "r-style")


def write_skill(
    root: Path, category: str, name: str, frontmatter_name: str = ""
) -> Path:
    directory = root / category / "skills" / name
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {frontmatter_name or name}\ndescription: Test.\n---\n"
    )
    return directory


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    path = tmp_path / "skills.toml"
    path.write_text(CONFIG_TOML)
    return path


@pytest.fixture
def configured(config_file: Path, tmp_path: Path, monkeypatch) -> Path:
    """A coordinator rooted at tmp_path with both local skills on disk."""
    monkeypatch.setattr(skill_coordinator, "ROOT", tmp_path)
    monkeypatch.setattr(skill_coordinator, "CONF_TOML", config_file)
    monkeypatch.setattr(skill_coordinator, "AGENTS_SKILLS_DIR", tmp_path / "store")
    monkeypatch.setattr(skill_coordinator, "CLAUDE_SKILLS_DIR", tmp_path / "claude")
    for name in LOCAL_SKILL_NAMES:
        write_skill(tmp_path / "skills", "engineering", name)
    (tmp_path / "store").mkdir()
    (tmp_path / "claude").mkdir()
    return tmp_path


@pytest.fixture
def record_run(monkeypatch) -> list[list[str]]:
    calls: list[list[str]] = []

    def record(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(skill_coordinator.subprocess, "run", record)
    return calls


class TestConfig:
    def test_models(self):
        options = PackageOptions()
        assert not options.full_depth
        assert PluginSource(names=["p"]).names == ["p"]
        assert Profile(description="Test profile").skills == []
        source = Source(path="skills")
        assert not source.owned
        assert source.git_url is None

    def test_load(self, configured: Path):
        config = load_config()
        assert config.package_options["owner/public"].full_depth
        assert config.sources["owner/local"].owned
        assert all_skill_names(config) == {
            "python-style",
            "r-style",
            "clean-architecture",
        }

    def test_duplicate_skill_reference_in_profile_rejected(self):
        with pytest.raises(ValidationError, match="duplicate skill references"):
            SkillsConfig(
                profiles={
                    "bad": Profile(
                        description="Invalid",
                        skills=["a/a@same", "a/a@same"],
                    )
                }
            )

    @pytest.mark.parametrize(
        "value",
        [
            "missing",
            "owner/repo",
            "owner/repo@",
            "owner/repo/path@skill",
            "owner/repo@nested/skill",
        ],
    )
    def test_malformed_skill_reference_rejected(self, value: str):
        with pytest.raises(ValidationError, match="invalid skill reference"):
            SkillsConfig(
                profiles={"bad": Profile(description="Invalid", skills=[value])}
            )

    def test_same_skill_name_from_different_packages_rejected(self):
        with pytest.raises(ValidationError, match="referenced from both"):
            SkillsConfig(
                profiles={
                    "one": Profile(description="One", skills=["a/a@same"]),
                    "two": Profile(description="Two", skills=["b/b@same"]),
                }
            )

    def test_unused_package_options_rejected(self):
        with pytest.raises(ValidationError, match="unused packages"):
            SkillsConfig(package_options={"a/a": PackageOptions(full_depth=True)})

    def test_unused_source_rejected(self):
        with pytest.raises(ValidationError, match="sources reference unused packages"):
            SkillsConfig(sources={"a/a": Source(path="skills")})

    def test_source_and_package_options_are_exclusive(self):
        with pytest.raises(ValidationError, match="package options do not apply"):
            SkillsConfig(
                sources={"a/a": Source(path="skills")},
                package_options={"a/a": PackageOptions(full_depth=True)},
                profiles={"one": Profile(description="One", skills=["a/a@one"])},
            )

    def test_unknown_included_profile_rejected(self):
        with pytest.raises(ValidationError, match="includes unknown profiles"):
            SkillsConfig(
                profiles={
                    "bad": Profile(description="Invalid", includes=["missing"]),
                }
            )

    def test_wildcard_include_must_be_alone(self):
        with pytest.raises(ValidationError, match="use '\\*' alone for includes"):
            SkillsConfig(
                profiles={
                    "one": Profile(description="One"),
                    "bad": Profile(description="Invalid", includes=["*", "one"]),
                }
            )

    def test_self_include_rejected(self):
        with pytest.raises(ValidationError, match="cannot include itself"):
            SkillsConfig(
                profiles={
                    "bad": Profile(description="Invalid", includes=["bad"]),
                }
            )

    def test_only_full_may_include_every_profile(self):
        with pytest.raises(ValidationError, match="only the 'full' profile"):
            SkillsConfig(
                profiles={
                    "one": Profile(description="One"),
                    "everything": Profile(description="All", includes=["*"]),
                }
            )

    def test_full_must_be_compositional(self):
        with pytest.raises(ValidationError, match="declare no skills"):
            SkillsConfig(
                profiles={
                    "full": Profile(
                        description="Everything",
                        includes=["*"],
                        skills=["a/a@one"],
                    ),
                    "one": Profile(description="One", skills=["a/a@one"]),
                }
            )

    def test_composition_cycle_rejected(self):
        with pytest.raises(ValidationError, match="inclusion cycle"):
            SkillsConfig(
                profiles={
                    "one": Profile(description="One", includes=["two"]),
                    "two": Profile(description="Two", includes=["one"]),
                }
            )

    def test_skill_reference(self):
        reference = SkillReference.parse("owner/repo@one")
        assert reference.package == "owner/repo"
        assert reference.name == "one"
        assert reference.identifier == "owner/repo@one"


class TestSourceInventory:
    def test_owned_source_matches_config(self, configured: Path):
        config = load_config()
        inventory = source_inventory(config.sources["owner/local"])
        assert sorted(inventory) == ["python-style", "r-style"]
        assert inventory["r-style"].name == "r-style"
        validate_sources(config)

    def test_owned_source_rejects_unconfigured_skill(self, configured: Path):
        write_skill(configured / "skills", "engineering", "extra")
        with pytest.raises(ValueError, match=r"unconfigured=\['extra'\]"):
            load_config()

    def test_owned_source_rejects_configured_skill_absent_from_tree(
        self, configured: Path
    ):
        (
            configured / "skills" / "engineering" / "skills" / "r-style" / "SKILL.md"
        ).unlink()
        with pytest.raises(ValueError, match=r"missing=\['r-style'\]"):
            load_config()

    def test_owned_source_rejects_off_pattern_skill(self, configured: Path):
        stray = configured / "skills" / "loose"
        stray.mkdir()
        (stray / "SKILL.md").write_text("---\nname: loose\ndescription: T.\n---\n")
        with pytest.raises(ValueError, match="<category>/skills/<name>/SKILL.md"):
            load_config()

    def test_third_party_source_ignores_off_pattern_and_extra_skills(
        self, tmp_path: Path
    ):
        root = tmp_path / "checkout"
        write_skill(root, "domain", "wanted")
        write_skill(root, "domain", "not-configured")
        stray = root / "loose"
        stray.mkdir(parents=True)
        (stray / "SKILL.md").write_text("---\nname: loose\ndescription: T.\n---\n")
        mismatched = root / "domain" / "skills" / "renamed"
        mismatched.mkdir(parents=True)
        (mismatched / "SKILL.md").write_text("---\nname: other\ndescription: T.\n---\n")
        source = Source(path="checkout")
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(skill_coordinator, "ROOT", tmp_path)
            assert sorted(source_inventory(source)) == ["not-configured", "wanted"]

    def test_absent_checkout_is_not_validated(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(skill_coordinator, "ROOT", tmp_path)
        config = SkillsConfig(
            sources={"a/a": Source(path="never-cloned")},
            profiles={"one": Profile(description="One", skills=["a/a@one"])},
        )
        validate_sources(config)

    def test_skill_names_split_by_install_kind(self, configured: Path):
        config = load_config()
        assert local_skill_names(config) == {"python-style", "r-style"}
        assert npx_skill_names(config) == {"clean-architecture"}


class TestProfiles:
    def test_full_selects_everything(self, configured: Path):
        selection = resolve_profile("full")
        assert selection.skill_names == {
            "python-style",
            "r-style",
            "clean-architecture",
        }

    def test_selection_splits_local_from_npx(self, configured: Path):
        selection = resolve_profile("python")
        assert [(item.package, item.skills) for item in selection.packages] == [
            ("owner/public", ("clean-architecture",))
        ]
        assert [skill.name for skill in selection.local] == ["python-style"]
        assert selection.missing == ()

    def test_local_skill_absent_from_checkout_is_reported_missing(
        self, configured: Path
    ):
        (configured / "skills" / "engineering" / "skills" / "r-style").rename(
            configured / "skills" / "engineering" / "skills" / "moved-away"
        )
        config = SkillsConfig(
            sources={"owner/local": Source(path="skills", owned=False)},
            profiles={
                "one": Profile(description="One", skills=["owner/local@r-style"])
            },
        )
        selection = resolve_profile("one", config)
        assert selection.missing == ("r-style",)
        assert selection.local == ()

    def test_composition_deduplicates_references(self, configured: Path):
        selection = resolve_profile("full")
        assert len(selection.skill_names) == 3
        assert sorted(skill.name for skill in selection.local) == [
            "python-style",
            "r-style",
        ]

    def test_unknown_profile(self, configured: Path):
        with pytest.raises(ValueError, match="unknown profile"):
            resolve_profile("missing")

    def test_package_command_targets_both_agents(self):
        selection = PackageSelection("owner/repo", ("a", "b"), True)
        command = selection.add_command()
        assert command[:3] == [
            "npx",
            "--yes",
            f"skills@{skill_coordinator.NPX_SKILLS_VERSION}",
        ]
        assert command[3:8] == ["add", "owner/repo", "--skill", "a", "b"]
        assert command[-1] == "--full-depth"
        assert command[command.index("--agent") + 1 : command.index("--global")] == [
            "claude-code",
            "codex",
        ]

    def test_profiles_lists_descriptions(self, configured: Path, capsys):
        skill_coordinator.profiles()
        output = capsys.readouterr().out
        assert "full\n    Everything" in output
        assert "python\n    Python tools" in output
        assert "skills=3 (direct=0)" in output
        assert "includes=*" in output


class TestSymlinkInstall:
    def roots(self, root: Path) -> tuple[Path, ...]:
        return (root, root / "skills")

    def local_skill(self, root: Path, name: str) -> LocalSkill:
        return LocalSkill(
            name=name,
            package="owner/local",
            directory=root / "skills" / "engineering" / "skills" / name,
        )

    def test_install_creates_store_and_agent_links(self, configured: Path):
        skill = self.local_skill(configured, "r-style")
        install_local_skill(skill, self.roots(configured), dry_run=False)
        store = configured / "store" / "r-style"
        agent_link = configured / "claude" / "r-style"
        assert store.is_symlink()
        assert store.resolve() == skill.directory
        assert agent_link.readlink() == Path("../../.agents/skills/r-style")
        assert managed_links(self.roots(configured)) == {"r-style": skill.directory}

    def test_install_is_idempotent(self, configured: Path, capsys):
        skill = self.local_skill(configured, "r-style")
        install_local_skill(skill, self.roots(configured), dry_run=False)
        capsys.readouterr()
        install_local_skill(skill, self.roots(configured), dry_run=False)
        assert capsys.readouterr().out == ""
        assert managed_links(self.roots(configured)) == {"r-style": skill.directory}

    def test_install_relinks_a_moved_source(self, configured: Path):
        skill = self.local_skill(configured, "r-style")
        install_local_skill(skill, self.roots(configured), dry_run=False)
        moved = write_skill(configured / "skills", "science", "r-style")
        install_local_skill(
            LocalSkill(name="r-style", package="owner/local", directory=moved),
            self.roots(configured),
            dry_run=False,
        )
        assert (configured / "store" / "r-style").resolve() == moved

    def test_install_refuses_to_clobber_an_npx_directory(
        self, configured: Path, capsys
    ):
        (configured / "store" / "r-style").mkdir()
        install_local_skill(
            self.local_skill(configured, "r-style"),
            self.roots(configured),
            dry_run=False,
        )
        assert "CONFLICT" in capsys.readouterr().out
        assert not (configured / "store" / "r-style").is_symlink()

    def test_install_refuses_to_clobber_a_foreign_symlink(
        self, configured: Path, capsys
    ):
        outside = configured.parent / "elsewhere"
        outside.mkdir()
        (configured / "store" / "r-style").symlink_to(outside)
        install_local_skill(
            self.local_skill(configured, "r-style"),
            self.roots(configured),
            dry_run=False,
        )
        assert "CONFLICT" in capsys.readouterr().out
        assert (configured / "store" / "r-style").resolve() == outside

    def test_install_reports_an_unmanaged_agent_entry(self, configured: Path, capsys):
        (configured / "claude" / "r-style").mkdir()
        install_local_skill(
            self.local_skill(configured, "r-style"),
            self.roots(configured),
            dry_run=False,
        )
        output = capsys.readouterr().out
        assert "CONFLICT" in output
        assert (configured / "store" / "r-style").is_symlink()
        assert (configured / "claude" / "r-style").is_dir()

    def test_dry_run_writes_nothing(self, configured: Path, capsys):
        install_local_skill(
            self.local_skill(configured, "r-style"),
            self.roots(configured),
            dry_run=True,
        )
        assert "would link" in capsys.readouterr().out
        assert not (configured / "store" / "r-style").exists()
        assert not (configured / "claude" / "r-style").exists()

    def test_remove_drops_both_links(self, configured: Path):
        skill = self.local_skill(configured, "r-style")
        install_local_skill(skill, self.roots(configured), dry_run=False)
        remove_local_skill("r-style", self.roots(configured), dry_run=False)
        assert not (configured / "store" / "r-style").is_symlink()
        assert not (configured / "claude" / "r-style").is_symlink()
        assert managed_links(self.roots(configured)) == {}

    def test_remove_survives_a_dangling_source(self, configured: Path):
        skill = self.local_skill(configured, "r-style")
        install_local_skill(skill, self.roots(configured), dry_run=False)
        for child in sorted(skill.directory.iterdir()):
            child.unlink()
        skill.directory.rmdir()
        assert managed_links(self.roots(configured)) == {"r-style": skill.directory}
        remove_local_skill("r-style", self.roots(configured), dry_run=False)
        assert not (configured / "store" / "r-style").is_symlink()

    def test_remove_leaves_unmanaged_entries_alone(self, configured: Path):
        (configured / "store" / "clean-architecture").mkdir()
        (configured / "claude" / "commit").mkdir()
        remove_local_skill("clean-architecture", self.roots(configured), dry_run=False)
        remove_local_skill("commit", self.roots(configured), dry_run=False)
        assert (configured / "store" / "clean-architecture").is_dir()
        assert (configured / "claude" / "commit").is_dir()

    def test_store_classification_ignores_stray_files(self, configured: Path):
        install_local_skill(
            self.local_skill(configured, "r-style"),
            self.roots(configured),
            dry_run=False,
        )
        (configured / "store" / "clean-architecture").mkdir()
        (configured / "store" / "python-style.skill").write_text("stray")
        assert npx_store_names() == {"clean-architecture"}
        assert sorted(managed_links(self.roots(configured))) == ["r-style"]

    def test_relative_external_source_is_managed_and_cleaned(
        self, tmp_path: Path, monkeypatch, capsys
    ):
        root = tmp_path / "coordinator"
        root.mkdir()
        external = tmp_path / "external"
        write_skill(external, "engineering", "outside")
        config = root / "skills.toml"
        config.write_text(
            '[sources."owner/local"]\n'
            'path = "../external"\n'
            "owned = true\n\n"
            "[profiles.local]\n"
            'description = "Local"\n'
            'skills = ["owner/local@outside"]\n'
        )
        monkeypatch.setattr(skill_coordinator, "ROOT", root)
        monkeypatch.setattr(skill_coordinator, "CONF_TOML", config)
        monkeypatch.setattr(skill_coordinator, "AGENTS_SKILLS_DIR", root / "store")
        monkeypatch.setattr(skill_coordinator, "CLAUDE_SKILLS_DIR", root / "claude")

        skill_coordinator.switch(profile="local")
        output = capsys.readouterr().out
        roots = source_roots(load_config())
        assert skill_coordinator.source_root(Source(path="../external")) == external
        assert f"outside -> {external / 'engineering' / 'skills' / 'outside'}" in output
        assert set(managed_links(roots)) == {"outside"}

        skill_coordinator.clean()
        assert not (root / "store" / "outside").is_symlink()
        assert not (root / "claude" / "outside").is_symlink()


class TestSwitch:
    def test_dry_run_has_no_side_effects(self, configured: Path, monkeypatch, capsys):
        def unexpected_run(*args, **kwargs):
            raise AssertionError("dry run executed a command")

        monkeypatch.setattr(skill_coordinator.subprocess, "run", unexpected_run)
        skill_coordinator.switch(profile="python", dry_run=True)
        output = capsys.readouterr().out
        assert "owner/public --skill clean-architecture" in output
        assert "would link     python-style ->" in output
        assert "remove" not in output  # r-style is local, so npx is never asked
        assert "active profile: python" in output
        assert not (configured / "store" / "python-style").exists()

    def test_add_failure_happens_before_local_links(
        self, configured: Path, monkeypatch
    ):
        calls: list[list[str]] = []

        def fail_first(command, **kwargs):
            calls.append(command)
            raise subprocess.CalledProcessError(1, command)

        monkeypatch.setattr(skill_coordinator.subprocess, "run", fail_first)
        with pytest.raises(subprocess.CalledProcessError):
            skill_coordinator.switch(profile="python")
        assert len(calls) == 1
        assert calls[0][3] == "add"
        assert not (configured / "store" / "python-style").exists()

    def test_local_skills_are_linked_and_dropped_by_profile(
        self, configured: Path, record_run
    ):
        skill_coordinator.switch(profile="full")
        assert sorted(managed_links(source_roots(load_config()))) == [
            "python-style",
            "r-style",
        ]
        skill_coordinator.switch(profile="python")
        assert sorted(managed_links(source_roots(load_config()))) == ["python-style"]

    def test_dropped_local_skill_is_never_sent_to_npx(
        self, configured: Path, record_run
    ):
        skill_coordinator.switch(profile="python")
        assert all("remove" not in command for command in record_run)

    def test_kind_flip_to_local_removes_the_npx_entry_after_a_successful_add(
        self, configured: Path, monkeypatch
    ):
        (configured / "store" / "python-style").mkdir()
        calls: list[list[str]] = []

        def npx(command, **kwargs):
            calls.append(command)
            if command[3] == "remove":  # stand in for what the real CLI deletes
                for name in command[4:]:
                    entry = configured / "store" / name
                    if entry.is_dir():
                        entry.rmdir()
            return subprocess.CompletedProcess(command, 0)

        monkeypatch.setattr(skill_coordinator.subprocess, "run", npx)
        skill_coordinator.switch(profile="python")
        assert calls[0][3] == "add"
        assert calls[1][3:] == ["remove", "python-style", "--global", "--yes"]
        assert (configured / "store" / "python-style").is_symlink()

    def test_a_failed_add_keeps_a_flipping_skill_installed(
        self, configured: Path, monkeypatch
    ):
        """The npx entry may only go once the fetch that could replace it worked."""
        (configured / "store" / "python-style").mkdir()

        def fail_add(command, **kwargs):
            assert command[3] != "remove", "removed an npx skill before the fetch"
            raise subprocess.CalledProcessError(1, command)

        monkeypatch.setattr(skill_coordinator.subprocess, "run", fail_add)
        with pytest.raises(subprocess.CalledProcessError):
            skill_coordinator.switch(profile="python")
        assert (configured / "store" / "python-style").is_dir()

    def test_dry_run_of_a_kind_flip_reports_a_link_not_a_conflict(
        self, configured: Path, monkeypatch, capsys
    ):
        (configured / "store" / "python-style").mkdir()
        monkeypatch.setattr(
            skill_coordinator.subprocess,
            "run",
            lambda *a, **k: pytest.fail("dry run executed a command"),
        )
        skill_coordinator.switch(profile="python", dry_run=True)
        output = capsys.readouterr().out
        assert "would link     python-style ->" in output
        assert "CONFLICT" not in output
        assert (configured / "store" / "python-style").is_dir()

    def test_kind_flip_to_npx_unlinks_first(self, configured: Path, monkeypatch):
        install_local_skill(
            LocalSkill(
                name="clean-architecture",
                package="owner/local",
                directory=configured / "skills" / "engineering" / "skills" / "r-style",
            ),
            source_roots(load_config()),
            dry_run=False,
        )
        calls: list[list[str]] = []

        def record(command, **kwargs):
            calls.append(command)
            assert not (configured / "store" / "clean-architecture").is_symlink()
            return subprocess.CompletedProcess(command, 0)

        monkeypatch.setattr(skill_coordinator.subprocess, "run", record)
        skill_coordinator.switch(profile="python")
        assert calls[0][3] == "add"

    def test_failed_kind_flip_to_npx_restores_local_links(
        self, configured: Path, monkeypatch
    ):
        directory = configured / "skills" / "engineering" / "skills" / "r-style"
        install_local_skill(
            LocalSkill(
                name="clean-architecture",
                package="owner/local",
                directory=directory,
            ),
            source_roots(load_config()),
            dry_run=False,
        )

        def fail_add(command, **kwargs):
            assert not (configured / "store" / "clean-architecture").is_symlink()
            raise subprocess.CalledProcessError(1, command)

        monkeypatch.setattr(skill_coordinator.subprocess, "run", fail_add)
        with pytest.raises(subprocess.CalledProcessError):
            skill_coordinator.switch(profile="python")

        store = configured / "store" / "clean-architecture"
        claude = configured / "claude" / "clean-architecture"
        assert store.is_symlink()
        assert store.resolve() == directory
        assert claude.readlink() == Path("../../.agents/skills/clean-architecture")

    def test_missing_local_skill_fails_the_switch_after_the_rest(
        self, configured: Path, record_run, capsys
    ):
        (configured / "skills" / "engineering" / "skills" / "python-style").rename(
            configured / "skills" / "engineering" / "skills" / "renamed"
        )
        (
            configured / "skills" / "engineering" / "skills" / "renamed" / "SKILL.md"
        ).write_text("---\nname: renamed\ndescription: T.\n---\n")
        config_text = (
            (configured / "skills.toml")
            .read_text()
            .replace("owned = true", "owned = false")
        )
        (configured / "skills.toml").write_text(config_text)
        with pytest.raises(SystemExit, match="absent from their checkout"):
            skill_coordinator.switch(profile="python")
        output = capsys.readouterr().out
        assert "MISSING        python-style" in output
        assert any(command[3] == "add" for command in record_run)


class TestNpxList:
    def test_warning_before_json_is_accepted(self):
        records = skill_coordinator._parse_npx_list(
            'warning about manifest\n[\n  {"name": "one", "agents": []}\n]\n'
        )
        assert records[0]["name"] == "one"

    def test_non_json_is_rejected(self):
        with pytest.raises(ValueError, match="JSON array"):
            skill_coordinator._parse_npx_list("warning only")


class TestClean:
    def test_clean_removes_npx_names_and_every_managed_link(
        self, configured: Path, record_run
    ):
        skill_coordinator.switch(profile="full")
        record_run.clear()
        skill_coordinator.clean()
        assert record_run == [
            skill_coordinator.npx_command(
                "remove", "clean-architecture", "--global", "--yes"
            )
        ]
        assert managed_links(source_roots(load_config())) == {}
        assert not (configured / "claude" / "r-style").is_symlink()


class TestSourceCheckouts:
    def test_clone_reports_an_existing_checkout(self, configured: Path, capsys):
        skill_coordinator.clone()
        assert "exists         owner/local" in capsys.readouterr().out

    def test_clone_fetches_a_missing_checkout(
        self, tmp_path: Path, monkeypatch, capsys
    ):
        config = tmp_path / "skills.toml"
        config.write_text(
            '[sources."a/a"]\npath = "checkout"\ngit_url = "https://example.invalid/a.git"\n\n'
            '[profiles.one]\ndescription = "One"\nskills = ["a/a@one"]\n'
        )
        monkeypatch.setattr(skill_coordinator, "ROOT", tmp_path)
        monkeypatch.setattr(skill_coordinator, "CONF_TOML", config)
        calls: list[list[str]] = []
        monkeypatch.setattr(
            skill_coordinator.subprocess,
            "run",
            lambda command, **kwargs: (
                calls.append(command) or subprocess.CompletedProcess(command, 0)
            ),
        )
        skill_coordinator.clone()
        assert calls == [
            [
                "git",
                "clone",
                "https://example.invalid/a.git",
                str(tmp_path / "checkout"),
            ]
        ]
        assert "--depth" not in " ".join(calls[0])

    def test_clone_reports_a_source_without_a_url(self, configured: Path, capsys):
        (configured / "skills").rename(configured / "hidden")
        skill_coordinator.clone()
        assert "NO-URL         owner/local" in capsys.readouterr().out

    def test_update_skips_sources_without_a_url(self, configured: Path, record_run):
        skill_coordinator.update()
        assert record_run == [
            skill_coordinator.npx_command("update", "--global", "--yes")
        ]

    def test_failed_pull_is_not_reported_as_pulled(
        self, tmp_path: Path, monkeypatch, capsys
    ):
        config = tmp_path / "skills.toml"
        config.write_text(
            '[sources."a/a"]\n'
            'path = "checkout"\n'
            'git_url = "https://example.invalid/a.git"\n\n'
            "[profiles.one]\n"
            'description = "One"\n'
            'skills = ["a/a@one"]\n'
        )
        (tmp_path / "checkout").mkdir()
        monkeypatch.setattr(skill_coordinator, "ROOT", tmp_path)
        monkeypatch.setattr(skill_coordinator, "CONF_TOML", config)
        calls = 0

        def fail_pull(command, **kwargs):
            nonlocal calls
            calls += 1
            return subprocess.CompletedProcess(command, 0 if calls == 1 else 1)

        monkeypatch.setattr(skill_coordinator.subprocess, "run", fail_pull)
        skill_coordinator.update()
        output = capsys.readouterr().out
        assert "pulling        a/a" in output
        assert "WARNING: pull failed for a/a" in output
        assert "pulled         a/a" not in output

    def test_source_status_of_a_non_repository(self, configured: Path, capsys):
        skill_coordinator.print_source_status(load_config())
        assert "unknown" in capsys.readouterr().out


class TestPlugins:
    def test_dry_run(self, configured: Path, monkeypatch, capsys):
        def unexpected_run(*args, **kwargs):
            raise AssertionError("dry run executed a command")

        monkeypatch.setattr(skill_coordinator.subprocess, "run", unexpected_run)
        skill_coordinator.install_plugins(dry_run=True)
        assert "plugin-a@market" in capsys.readouterr().out


class TestReadCoordinator:
    def test_the_scan_view_carries_profiles_sources_and_the_store(
        self, configured: Path, tmp_path: Path
    ) -> None:
        view = read_coordinator(load_config())

        assert view.profiles["python-style"] == frozenset({"full", "python", "python-style"})
        assert view.packages["python-style"] == "owner/local"
        assert view.owned_roots == (tmp_path / "skills",)
        assert view.checkout_roots == ()
        assert view.store == tmp_path / "store"

    def test_an_installed_symlink_is_reported_with_its_resolved_target(
        self, configured: Path, tmp_path: Path
    ) -> None:
        target = tmp_path / "skills" / "engineering" / "skills" / "python-style"
        (tmp_path / "store" / "python-style").symlink_to(target)
        (tmp_path / "store" / "clean-architecture").mkdir()

        view = read_coordinator(load_config())

        assert view.installed == {
            "python-style": "symlink",
            "clean-architecture": "npx-copy",
        }
        assert view.install_targets["python-style"] == target.resolve()


class TestProductionConfig:
    def test_real_config_loads(self):
        config = load_config()
        assert config.profiles["full"].skills == []
        assert config.profiles["full"].includes == ["*"]
        assert len(all_skill_references(config)) == 71
        assert len(resolve_profile("full", config).skill_names) == 71
        assert "python-design-patterns" in all_skill_names(config)
        assert "clean-architecture" in all_skill_names(config)
        assert "adding-models-to-prolfqua" in all_skill_names(config)
        assert "prolfqua-adding-models" not in all_skill_names(config)
        assert "apb-toml-level-design" not in all_skill_names(config)
        assert "bfabricpy" not in all_skill_names(config)
        assert "directed-folder-imports" in all_skill_names(config)

    def test_local_sources_are_declared_and_exhaustive(self):
        config = load_config()
        assert set(config.sources) == {"wolski/wews_skill_coordinator", "fgcz/skills"}
        assert config.sources["wolski/wews_skill_coordinator"].owned
        assert not config.sources["fgcz/skills"].owned
        assert set(
            source_inventory(config.sources["wolski/wews_skill_coordinator"])
        ) == {
            reference.name
            for reference in all_skill_references(config)
            if reference.package == "wolski/wews_skill_coordinator"
        }

    def test_every_configured_local_skill_resolves_to_a_directory(self):
        config = load_config()
        selection = resolve_profile("full", config)
        assert selection.missing == ()
        assert {skill.name for skill in selection.local} == local_skill_names(config)
        for skill in selection.local:
            assert (skill.directory / "SKILL.md").is_file()

    def test_every_profile_resolves(self):
        for profile in load_config().profiles:
            resolve_profile(profile)
