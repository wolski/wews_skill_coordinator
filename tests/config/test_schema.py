from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest
from pydantic import ValidationError

from wews_skill_coordinator.config.load import load_config
from wews_skill_coordinator.config.schema import (
    BaseProfile,
    Composition,
    LocalSource,
    NpxSource,
    PluginSource,
    SkillReference,
    SkillsConfig,
)

NPX = {"a": NpxSource(repo="a/a")}


def base(*skills: str, source: str = "a") -> BaseProfile:
    return BaseProfile(description="Base", skills={source: list(skills)})


def test_models():
    assert PluginSource(names=["p"]).names == ["p"]
    assert Composition(description="C", includes=["x"]).includes == ["x"]
    local = LocalSource(repo="o/r", path="skills")
    assert not local.owned
    assert local.git_url is None
    assert not NpxSource(repo="o/r").full_depth


def test_a_base_profile_needs_skills():
    with pytest.raises(ValidationError):
        BaseProfile(description="Empty", skills={})


def test_a_composition_needs_includes():
    with pytest.raises(ValidationError):
        Composition(description="Empty", includes=[])


def test_load(configured: Path):
    config = load_config()
    assert config.active == "python"
    assert set(config.compositions) == {"full", "python"}
    assert set(config.base_profiles) == {"python-style", "r", "architecture"}
    assert config.npx_sources["public"].full_depth
    assert config.local_sources["local"].owned
    assert config.skill_names() == {"python-style", "r-style", "clean-architecture"}
    assert config.local_skill_names() == {"python-style", "r-style"}
    assert config.npx_skill_names() == {"clean-architecture"}


def test_composition_references_are_its_base_profiles_skills(configured: Path):
    config = load_config()
    assert [r.name for r in config.profile_references("python")] == [
        "python-style",
        "clean-architecture",
    ]
    assert config.included_profiles("full") == ("python-style", "r", "architecture")


def test_duplicate_skill_in_a_profile_rejected():
    with pytest.raises(ValidationError, match="duplicate skills of 'a'"):
        SkillsConfig(active="bad", sources=NPX, profiles={"bad": base("same", "same")})


def test_a_skill_in_two_base_profiles_rejected():
    with pytest.raises(ValidationError, match="in base profiles 'one' and 'two'"):
        SkillsConfig(
            active="one",
            sources=NPX,
            profiles={"one": base("same"), "two": base("same")},
        )


@pytest.mark.parametrize("selector", ["", "nested/skill", "has space", r"back\slash"])
def test_malformed_npx_skill_rejected(selector: str):
    with pytest.raises(ValidationError, match="invalid npx skill"):
        SkillsConfig(active="bad", sources=NPX, profiles={"bad": base(selector)})


@pytest.mark.parametrize(
    "selector",
    ["one", "/domain/one", "domain/..", "domain/skills/one", r"domain\one", "domain/"],
)
def test_local_skill_requires_category_and_name(selector: str):
    with pytest.raises(ValidationError, match="invalid local skill"):
        SkillsConfig(
            active="one",
            sources={"a": LocalSource(repo="a/a", path="skills")},
            profiles={"one": base(selector)},
        )


def test_same_skill_name_from_different_sources_rejected():
    with pytest.raises(ValidationError, match="referenced from both"):
        SkillsConfig(
            active="one",
            sources={"a": NpxSource(repo="a/a"), "b": NpxSource(repo="b/b")},
            profiles={"one": base("same"), "two": base("same", source="b")},
        )


def test_same_runtime_name_in_different_categories_rejected():
    with pytest.raises(ValidationError, match="referenced from both"):
        SkillsConfig(
            active="one",
            sources={"a": LocalSource(repo="a/a", path="skills")},
            profiles={"one": base("first/same"), "two": base("second/same")},
        )


@pytest.mark.parametrize(
    "source", [NpxSource(repo="a/a"), LocalSource(repo="a/a", path="skills")]
)
def test_unused_source_rejected(source: LocalSource | NpxSource):
    with pytest.raises(ValidationError, match="sources no profile uses"):
        SkillsConfig(
            active="one",
            sources={"a": source, "b": NpxSource(repo="b/b")},
            profiles={"one": base("x", source="b")},
        )


def test_profile_naming_an_unknown_source_rejected():
    with pytest.raises(ValidationError, match="unknown source 'missing'"):
        SkillsConfig(active="one", profiles={"one": base("x", source="missing")})


def test_source_named_like_a_profile_field_rejected():
    with pytest.raises(ValidationError, match="clash with profile fields"):
        SkillsConfig(
            active="one",
            sources={"includes": NpxSource(repo="a/a")},
            profiles={"one": base("x", source="includes")},
        )


def test_a_composition_may_not_include_a_composition():
    with pytest.raises(ValidationError, match="include their base profiles instead"):
        SkillsConfig(
            active="outer",
            sources=NPX,
            profiles={
                "one": base("x"),
                "inner": Composition(description="Inner", includes=["one"]),
                "outer": Composition(description="Outer", includes=["inner"]),
            },
        )


def test_unknown_included_profile_rejected():
    with pytest.raises(ValidationError, match="includes unknown profiles"):
        SkillsConfig(
            active="bad",
            profiles={"bad": Composition(description="Invalid", includes=["missing"])},
        )


def test_wildcard_include_must_be_alone():
    with pytest.raises(ValidationError, match="use '\\*' alone for includes"):
        SkillsConfig(
            active="one",
            sources=NPX,
            profiles={
                "one": base("x"),
                "full": Composition(description="All", includes=["*", "one"]),
            },
        )


def test_only_full_may_include_every_profile():
    with pytest.raises(ValidationError, match="only the 'full' profile"):
        SkillsConfig(
            active="one",
            sources=NPX,
            profiles={
                "one": base("x"),
                "everything": Composition(description="All", includes=["*"]),
            },
        )


def test_full_must_be_a_wildcard_composition():
    with pytest.raises(ValidationError, match="'full' must be a composition"):
        SkillsConfig(active="full", sources=NPX, profiles={"full": base("x")})


def test_active_profile_must_be_configured():
    with pytest.raises(ValidationError, match="active profile 'missing'"):
        SkillsConfig(active="missing", sources=NPX, profiles={"one": base("x")})


def test_skill_reference():
    npx = SkillReference("public", "one")
    assert npx.name == "one"
    assert npx.identifier == "public:one"

    local = SkillReference("local", "domain/local")
    assert local.name == "local"
    assert local.source_path == PurePosixPath("domain/skills/local")
