"""Tests for skill_coordinator — config loading, validation, and dry-run commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from skill_coordinator import (
    ConfEntry,
    PluginSource,
    RepoSkills,
    SkillsConfig,
    load_config,
    parse_conf,
)


# ── Fixtures ─────────────────────────────────────────────────────────


MINIMAL_TOML = """\
[repos]
my-repo = "https://github.com/example/my-repo.git"

[plugins.test-marketplace]
names = ["plugin-a", "plugin-b"]

[skills.my-repo]
paths = ["skill-one", "nested/skill-two"]
agents = ["agents/my-agent.md"]
"""

MULTI_REPO_TOML = """\
[repos]
repo-a = "https://github.com/example/repo-a.git"
repo-b = "https://github.com/example/repo-b.git"

[plugins.marketplace-1]
names = ["p1"]

[plugins.marketplace-2]
names = ["p2", "p3"]

[skills.repo-a]
paths = ["s1", "s2"]

[skills.repo-b]
paths = ["s3"]
agents = ["agents/a1.md"]
"""


@pytest.fixture
def toml_file(tmp_path: Path) -> Path:
    p = tmp_path / "skills.toml"
    p.write_text(MINIMAL_TOML)
    return p


@pytest.fixture
def multi_toml_file(tmp_path: Path) -> Path:
    p = tmp_path / "skills.toml"
    p.write_text(MULTI_REPO_TOML)
    return p


# ── Pydantic model unit tests ───────────────────────────────────────


class TestPluginSource:
    def test_basic(self):
        ps = PluginSource(names=["a", "b"])
        assert ps.names == ["a", "b"]

    def test_empty(self):
        ps = PluginSource(names=[])
        assert ps.names == []


class TestRepoSkills:
    def test_defaults(self):
        rs = RepoSkills()
        assert rs.paths == []
        assert rs.agents == []

    def test_paths_only(self):
        rs = RepoSkills(paths=["x", "y"])
        assert rs.paths == ["x", "y"]
        assert rs.agents == []

    def test_paths_and_agents(self):
        rs = RepoSkills(paths=["x"], agents=["agents/a.md"])
        assert rs.paths == ["x"]
        assert rs.agents == ["agents/a.md"]


class TestSkillsConfig:
    def test_valid(self):
        cfg = SkillsConfig(
            repos={"r": "https://example.com/r.git"},
            plugins={"mp": PluginSource(names=["p"])},
            skills={"r": RepoSkills(paths=["s"])},
        )
        assert "r" in cfg.repos
        assert cfg.skills["r"].paths == ["s"]

    def test_unknown_repo_in_skills_raises(self):
        with pytest.raises(ValidationError, match="unknown repos"):
            SkillsConfig(
                repos={"r": "https://example.com/r.git"},
                plugins={},
                skills={"nonexistent": RepoSkills(paths=["s"])},
            )

    def test_extra_repos_ok(self):
        cfg = SkillsConfig(
            repos={
                "r1": "https://example.com/r1.git",
                "r2": "https://example.com/r2.git",
            },
            plugins={},
            skills={"r1": RepoSkills(paths=["s"])},
        )
        assert "r2" in cfg.repos
        assert "r2" not in cfg.skills

    def test_empty_skills_ok(self):
        cfg = SkillsConfig(
            repos={"r": "https://example.com/r.git"},
            plugins={},
            skills={},
        )
        assert cfg.skills == {}

    def test_multiple_marketplaces(self):
        cfg = SkillsConfig(
            repos={},
            plugins={
                "mp1": PluginSource(names=["a"]),
                "mp2": PluginSource(names=["b", "c"]),
            },
            skills={},
        )
        assert len(cfg.plugins) == 2
        assert cfg.plugins["mp2"].names == ["b", "c"]


# ── TOML loading tests ──────────────────────────────────────────────


class TestLoadConfig:
    def test_load_minimal(self, toml_file: Path, monkeypatch):
        import skill_coordinator

        monkeypatch.setattr(skill_coordinator, "CONF_TOML", toml_file)
        cfg = load_config()
        assert cfg.repos["my-repo"] == "https://github.com/example/my-repo.git"
        assert cfg.plugins["test-marketplace"].names == ["plugin-a", "plugin-b"]
        assert cfg.skills["my-repo"].paths == ["skill-one", "nested/skill-two"]
        assert cfg.skills["my-repo"].agents == ["agents/my-agent.md"]

    def test_load_multi_repo(self, multi_toml_file: Path, monkeypatch):
        import skill_coordinator

        monkeypatch.setattr(skill_coordinator, "CONF_TOML", multi_toml_file)
        cfg = load_config()
        assert len(cfg.repos) == 2
        assert len(cfg.plugins) == 2
        assert cfg.skills["repo-a"].paths == ["s1", "s2"]
        assert cfg.skills["repo-b"].agents == ["agents/a1.md"]

    def test_load_invalid_repo_ref(self, tmp_path: Path, monkeypatch):
        import skill_coordinator

        bad = tmp_path / "skills.toml"
        bad.write_text(
            '[repos]\nr = "url"\n\n[plugins]\n\n[skills.unknown]\npaths = ["x"]\n'
        )
        monkeypatch.setattr(skill_coordinator, "CONF_TOML", bad)
        with pytest.raises(ValidationError, match="unknown repos"):
            load_config()

    def test_load_missing_file(self, tmp_path: Path, monkeypatch):
        import skill_coordinator

        monkeypatch.setattr(skill_coordinator, "CONF_TOML", tmp_path / "nope.toml")
        with pytest.raises(FileNotFoundError):
            load_config()


# ── parse_conf tests ─────────────────────────────────────────────────


class TestParseConf:
    def test_entries_from_minimal(self, toml_file: Path, tmp_path: Path, monkeypatch):
        import skill_coordinator

        monkeypatch.setattr(skill_coordinator, "CONF_TOML", toml_file)
        monkeypatch.setattr(skill_coordinator, "REPOS_DIR", tmp_path / "repos")
        entries = parse_conf()
        assert len(entries) == 3

        skills = [e for e in entries if not e.is_agent]
        agents = [e for e in entries if e.is_agent]
        assert len(skills) == 2
        assert len(agents) == 1

    def test_skill_entry_fields(self, toml_file: Path, tmp_path: Path, monkeypatch):
        import skill_coordinator

        repos_dir = tmp_path / "repos"
        monkeypatch.setattr(skill_coordinator, "CONF_TOML", toml_file)
        monkeypatch.setattr(skill_coordinator, "REPOS_DIR", repos_dir)
        entries = parse_conf()

        skill = entries[0]
        assert skill.repo == "my-repo"
        assert skill.skill_path == "skill-one"
        assert skill.entry_type == "skill"
        assert skill.name == "skill-one"
        assert skill.source == repos_dir / "my-repo" / "skill-one"
        assert not skill.is_agent

    def test_nested_skill_basename(self, toml_file: Path, tmp_path: Path, monkeypatch):
        import skill_coordinator

        monkeypatch.setattr(skill_coordinator, "CONF_TOML", toml_file)
        monkeypatch.setattr(skill_coordinator, "REPOS_DIR", tmp_path / "repos")
        entries = parse_conf()
        nested = entries[1]
        assert nested.skill_path == "nested/skill-two"
        assert nested.name == "skill-two"

    def test_agent_entry_fields(self, toml_file: Path, tmp_path: Path, monkeypatch):
        import skill_coordinator

        repos_dir = tmp_path / "repos"
        monkeypatch.setattr(skill_coordinator, "CONF_TOML", toml_file)
        monkeypatch.setattr(skill_coordinator, "REPOS_DIR", repos_dir)
        entries = parse_conf()

        agent = [e for e in entries if e.is_agent][0]
        assert agent.repo == "my-repo"
        assert agent.skill_path == "agents/my-agent.md"
        assert agent.entry_type == "agent"
        assert agent.name == "my-agent.md"
        assert agent.source == repos_dir / "my-repo" / "agents" / "my-agent.md"
        assert agent.is_agent

    def test_multi_repo_ordering(self, multi_toml_file: Path, tmp_path: Path, monkeypatch):
        import skill_coordinator

        monkeypatch.setattr(skill_coordinator, "CONF_TOML", multi_toml_file)
        monkeypatch.setattr(skill_coordinator, "REPOS_DIR", tmp_path / "repos")
        entries = parse_conf()
        assert len(entries) == 4
        repos_seen = [e.repo for e in entries]
        assert repos_seen == ["repo-a", "repo-a", "repo-b", "repo-b"]


# ── ConfEntry unit tests ────────────────────────────────────────────


class TestConfEntry:
    def test_is_agent_true(self):
        e = ConfEntry("r", "agents/x.md", "agent", "x.md", Path("/tmp/x.md"))
        assert e.is_agent

    def test_is_agent_false(self):
        e = ConfEntry("r", "my-skill", "skill", "my-skill", Path("/tmp/s"))
        assert not e.is_agent


# ── Dry-run CLI tests ───────────────────────────────────────────────


class TestDryRunClone:
    def test_clone_dry_run_existing(self, toml_file: Path, tmp_path: Path, monkeypatch, capsys):
        import skill_coordinator

        repos_dir = tmp_path / "repos"
        repos_dir.mkdir()
        (repos_dir / "my-repo").mkdir()
        monkeypatch.setattr(skill_coordinator, "CONF_TOML", toml_file)
        monkeypatch.setattr(skill_coordinator, "REPOS_DIR", repos_dir)

        from skill_coordinator import clone

        clone(dry_run=True)
        out = capsys.readouterr().out
        assert "exists" in out
        assert "would clone" not in out

    def test_clone_dry_run_missing(self, toml_file: Path, tmp_path: Path, monkeypatch, capsys):
        import skill_coordinator

        repos_dir = tmp_path / "repos"
        repos_dir.mkdir()
        monkeypatch.setattr(skill_coordinator, "CONF_TOML", toml_file)
        monkeypatch.setattr(skill_coordinator, "REPOS_DIR", repos_dir)

        from skill_coordinator import clone

        clone(dry_run=True)
        out = capsys.readouterr().out
        assert "would clone" in out
        assert "my-repo" in out
        assert not (repos_dir / "my-repo").exists()


class TestDryRunInstall:
    def test_install_dry_run(self, toml_file: Path, tmp_path: Path, monkeypatch, capsys):
        import skill_coordinator

        repos_dir = tmp_path / "repos"
        repo = repos_dir / "my-repo"
        (repo / "skill-one").mkdir(parents=True)
        (repo / "nested" / "skill-two").mkdir(parents=True)
        (repo / "agents" / "my-agent.md").parent.mkdir(parents=True)
        (repo / "agents" / "my-agent.md").touch()

        skills_dir = tmp_path / "skills"
        agents_dir = tmp_path / "agents"
        codex_dir = tmp_path / "codex"
        for d in (skills_dir, agents_dir, codex_dir):
            d.mkdir()

        monkeypatch.setattr(skill_coordinator, "CONF_TOML", toml_file)
        monkeypatch.setattr(skill_coordinator, "REPOS_DIR", repos_dir)
        monkeypatch.setattr(skill_coordinator, "SKILLS_DIR", skills_dir)
        monkeypatch.setattr(skill_coordinator, "AGENTS_DIR", agents_dir)
        monkeypatch.setattr(skill_coordinator, "CODEX_SKILLS_DIR", codex_dir)

        from skill_coordinator import install

        install(dry_run=True)
        out = capsys.readouterr().out
        assert "would link" in out
        assert list(skills_dir.iterdir()) == []
        assert list(agents_dir.iterdir()) == []


class TestDryRunPlugins:
    def test_plugins_install_dry_run(self, toml_file: Path, monkeypatch, capsys):
        import skill_coordinator

        monkeypatch.setattr(skill_coordinator, "CONF_TOML", toml_file)

        from skill_coordinator import install_plugins

        install_plugins(dry_run=True)
        out = capsys.readouterr().out
        assert "would install" in out
        assert "plugin-a" in out
        assert "plugin-b" in out

    def test_plugins_remove_dry_run(self, toml_file: Path, monkeypatch, capsys):
        import skill_coordinator

        monkeypatch.setattr(skill_coordinator, "CONF_TOML", toml_file)

        from skill_coordinator import remove

        remove(dry_run=True)
        out = capsys.readouterr().out
        assert "would remove" in out
        assert "plugin-a" in out


# ── Production config smoke test ────────────────────────────────────


class TestProductionConfig:
    def test_real_toml_loads(self):
        cfg = load_config()
        assert len(cfg.repos) >= 5
        assert len(cfg.skills) >= 5
        assert any("claude-kaiser-skills" in r for r in cfg.repos)

    def test_real_toml_all_skills_have_repos(self):
        cfg = load_config()
        for repo_name in cfg.skills:
            assert repo_name in cfg.repos, f"{repo_name} in skills but not in repos"

    def test_real_parse_conf_entries(self):
        entries = parse_conf()
        names = [e.name for e in entries]
        assert "r-development" in names
        assert "python-style-guide" in names
        agents = [e for e in entries if e.is_agent]
        assert len(agents) >= 3
        assert any("dry-audit" in a.name for a in agents)
