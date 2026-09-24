"""The real skills.toml in this checkout."""

from __future__ import annotations

from wews_skill_coordinator.config.checkout import source_root
from wews_skill_coordinator.config.load import load_config
from wews_skill_coordinator.skills.profiles import resolve_profile

FGCZ_FOLDER_PROFILES = [
    "fgcz-bfabric-lims",
    "fgcz-communication",
    "fgcz-infrastructure",
    "fgcz-meta-skills",
    "fgcz-proteomics-data-analysis",
]


def test_real_config_loads():
    config = load_config()
    assert config.compositions["full"].includes == ["*"]
    assert len(resolve_profile("full", config).skill_names) == len(config.references())
    names = config.skill_names()
    assert "python-design-patterns" in names
    assert "adding-models-to-prolfqua" in names
    assert "directed-folder-imports" in names
    assert "general-agentic" not in names
    assert "clean-architecture" not in names
    assert "prolfqua-adding-models" not in names
    assert "apb-toml-level-design" not in names
    assert "bfabricpy" not in names


def test_local_sources_are_declared():
    config = load_config()
    assert set(config.local_sources) == {"wews", "fgcz"}
    assert config.local_sources["wews"].owned
    assert not config.local_sources["fgcz"].owned


def test_fgcz_profiles_mirror_configured_source_folders():
    config = load_config()
    assert config.compositions["fgcz"].includes == FGCZ_FOLDER_PROFILES
    grouped = {
        selector
        for profile_name in FGCZ_FOLDER_PROFILES
        for selector in config.base_profiles[profile_name].skills.get("fgcz", [])
    }
    configured = {
        reference.selector for reference in config.references() if reference.source == "fgcz"
    }
    assert grouped == configured
    assert len(resolve_profile("fgcz", config).skill_names) == 17


def test_every_configured_skill_resolves_in_each_present_checkout():
    """fgcz/skills is private, so CI has no checkout of it; the owned source is always here."""
    config = load_config()
    present = {
        name for name, source in config.local_sources.items() if source_root(source).is_dir()
    }
    assert "wews" in present
    selection = resolve_profile("full", config)
    assert [miss for miss in selection.missing if miss.split(":")[0] in present] == []
    expected = {r.name for r in config.references() if r.source in present}
    assert {skill.name for skill in selection.local} == expected
    for skill in selection.local:
        assert (skill.directory / "SKILL.md").is_file()


def test_every_profile_resolves():
    config = load_config()
    for profile in config.profiles:
        resolve_profile(profile, config)


def test_active_profile_leaves_out_marimo_and_review():
    config = load_config()
    active = resolve_profile(config.active, config).skill_names
    assert not active & {r.name for r in config.profile_references("marimo")}
    assert not active & {r.name for r in config.profile_references("review")}
