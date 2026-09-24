from __future__ import annotations

import pytest

from wews_skill_coordinator.skills.npx import InstalledSkill, parse_npx_list


def test_warning_before_json_is_accepted():
    records = parse_npx_list('warning about manifest\n[\n  {"name": "one", "agents": []}\n]\n')
    assert records == [InstalledSkill("one", ())]


def test_non_json_is_rejected():
    with pytest.raises(ValueError, match="JSON array"):
        parse_npx_list("warning only")
