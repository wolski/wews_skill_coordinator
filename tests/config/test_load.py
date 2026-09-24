from __future__ import annotations

import pytest
from pydantic import ValidationError

from wews_skill_coordinator.config.load import parse_config
from wews_skill_coordinator.config.schema import LocalSource, NpxSource


def document(**source: object) -> dict[str, object]:
    return {
        "active": "one",
        "sources": {"a": {"repo": "a/a", **source}},
        "profiles": {"one": {"description": "One", "a": ["domain/one"]}},
    }


def test_a_source_with_a_path_is_local():
    config = parse_config(document(path="skills", owned=True))
    assert isinstance(config.sources["a"], LocalSource)
    assert config.profiles["one"].skills == {"a": ["domain/one"]}


def test_a_source_without_a_path_is_npx():
    config = parse_config(
        {
            "active": "one",
            "sources": {"a": {"repo": "a/a", "full_depth": True}},
            "profiles": {"one": {"description": "One", "a": ["one"]}},
        }
    )
    assert isinstance(config.sources["a"], NpxSource)


def test_npx_options_do_not_apply_to_a_local_source():
    with pytest.raises(ValidationError):
        parse_config(document(path="skills", full_depth=True))


def test_a_misspelled_profile_key_is_an_unknown_source():
    with pytest.raises(ValidationError, match="unknown source 'descripton'"):
        parse_config(
            {
                "active": "one",
                "profiles": {"one": {"description": "One", "descripton": ["x"]}},
            }
        )


def test_a_profile_mixing_includes_and_skills_is_rejected():
    with pytest.raises(ValueError, match="both includes and skills"):
        parse_config(
            {
                "active": "one",
                "sources": {"a": {"repo": "a/a"}},
                "profiles": {"one": {"description": "One", "includes": ["b"], "a": ["x"]}},
            }
        )
