"""Tests for the npx-backed skills coordinator."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

import skill_coordinator
from skill_coordinator import (
    PackageOptions,
    PackageSelection,
    PluginSource,
    Profile,
    SkillReference,
    SkillsConfig,
    all_skill_names,
    all_skill_references,
    load_config,
    local_skill_inventory,
    resolve_profile,
    validate_local_inventory,
)

CONFIG_TOML = """\
[plugins.market]
names = ["plugin-a"]

[package_options."owner/local"]
full_depth = true

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


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    path = tmp_path / "skills.toml"
    path.write_text(CONFIG_TOML)
    return path


@pytest.fixture
def configured(config_file: Path, tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setattr(skill_coordinator, "CONF_TOML", config_file)
    return tmp_path


class TestConfig:
    def test_models(self):
        options = PackageOptions()
        assert not options.full_depth
        assert PluginSource(names=["p"]).names == ["p"]
        assert Profile(description="Test profile").skills == []

    def test_load(self, config_file: Path, monkeypatch):
        monkeypatch.setattr(skill_coordinator, "CONF_TOML", config_file)
        config = load_config()
        assert config.package_options["owner/local"].full_depth
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

    def test_local_inventory_matches_config(self, tmp_path: Path, monkeypatch):
        root = tmp_path / "skills"
        path = root / "engineering" / "skills" / "local-one" / "SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text("---\nname: local-one\ndescription: Test.\n---\n")
        monkeypatch.setattr(skill_coordinator, "LOCAL_SKILLS_DIR", root)
        config = SkillsConfig(
            profiles={
                "one": Profile(
                    description="One",
                    skills=[f"{skill_coordinator.LOCAL_PACKAGE}@local-one"],
                )
            }
        )
        validate_local_inventory(config)
        assert list(local_skill_inventory(root)) == ["local-one"]

    def test_local_inventory_rejects_unconfigured_skill(
        self, tmp_path: Path, monkeypatch
    ):
        root = tmp_path / "skills"
        path = root / "engineering" / "skills" / "extra" / "SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text("---\nname: extra\ndescription: Test.\n---\n")
        monkeypatch.setattr(skill_coordinator, "LOCAL_SKILLS_DIR", root)
        config = SkillsConfig(
            profiles={
                "one": Profile(
                    description="One",
                    skills=[f"{skill_coordinator.LOCAL_PACKAGE}@missing"],
                )
            }
        )
        with pytest.raises(ValueError, match=r"missing=\['missing'\].*extra"):
            validate_local_inventory(config)


class TestProfiles:
    def test_full_selects_everything(self, configured: Path):
        selection = resolve_profile("full")
        assert selection.skill_names == {
            "python-style",
            "r-style",
            "clean-architecture",
        }

    def test_subset_is_grouped_by_package(self, configured: Path):
        selection = resolve_profile("python")
        assert [(item.package, item.skills) for item in selection.packages] == [
            ("owner/local", ("python-style",)),
            ("owner/public", ("clean-architecture",)),
        ]

    def test_composition_deduplicates_references(self, configured: Path):
        selection = resolve_profile("full")
        assert len(selection.skill_names) == 3
        assert selection.packages[0].skills == ("python-style", "r-style")

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


class TestSwitch:
    def test_dry_run_has_no_side_effects(self, configured: Path, monkeypatch, capsys):
        def unexpected_run(*args, **kwargs):
            raise AssertionError("dry run executed a command")

        monkeypatch.setattr(skill_coordinator.subprocess, "run", unexpected_run)
        skill_coordinator.switch(profile="python", dry_run=True)
        output = capsys.readouterr().out
        assert "owner/local --skill python-style" in output
        assert "owner/public --skill clean-architecture" in output
        assert "remove r-style --global --yes" in output
        assert "active profile: python" in output

    def test_add_failure_happens_before_remove(self, configured: Path, monkeypatch):
        calls: list[list[str]] = []

        def fail_first(command, **kwargs):
            calls.append(command)
            raise subprocess.CalledProcessError(1, command)

        monkeypatch.setattr(skill_coordinator.subprocess, "run", fail_first)
        with pytest.raises(subprocess.CalledProcessError):
            skill_coordinator.switch(profile="python")
        assert len(calls) == 1
        assert calls[0][3] == "add"

    def test_subset_removes_only_unselected_configured_skill(
        self, configured: Path, monkeypatch
    ):
        calls: list[list[str]] = []

        def record(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0)

        monkeypatch.setattr(skill_coordinator.subprocess, "run", record)
        skill_coordinator.switch(profile="python")
        assert calls[-1][3:] == ["remove", "r-style", "--global", "--yes"]


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
    def test_clean_removes_only_configured_names(self, configured: Path, monkeypatch):
        calls: list[list[str]] = []

        def record(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0)

        monkeypatch.setattr(skill_coordinator.subprocess, "run", record)
        skill_coordinator.clean()
        assert calls == [
            skill_coordinator.npx_command(
                "remove",
                "clean-architecture",
                "python-style",
                "r-style",
                "--global",
                "--yes",
            )
        ]


class TestPlugins:
    def test_dry_run(self, configured: Path, monkeypatch, capsys):
        def unexpected_run(*args, **kwargs):
            raise AssertionError("dry run executed a command")

        monkeypatch.setattr(skill_coordinator.subprocess, "run", unexpected_run)
        skill_coordinator.install_plugins(dry_run=True)
        assert "plugin-a@market" in capsys.readouterr().out


class TestProductionConfig:
    def test_real_config_loads(self):
        config = load_config()
        assert config.package_options[skill_coordinator.LOCAL_PACKAGE].full_depth
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
        assert set(local_skill_inventory()) == {
            reference.name
            for reference in all_skill_references(config)
            if reference.package == skill_coordinator.LOCAL_PACKAGE
        }

    def test_every_profile_resolves(self):
        for profile in load_config().profiles:
            resolve_profile(profile)
