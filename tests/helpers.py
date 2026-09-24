"""A small coordinator on disk: one owned local source and one npx package."""

from __future__ import annotations

from pathlib import Path

import pytest

from wews_skill_coordinator import paths

CONFIG_TOML = """\
active = "python"

[plugins.market]
names = ["plugin-a"]

[sources.local]
repo = "owner/local"
path = "skills"
owned = true

[sources.public]
repo = "owner/public"
full_depth = true

[profiles.full]
description = "Everything"
includes = ["*"]

[profiles.python]
description = "Python tools"
includes = ["python-style", "architecture"]

[profiles.python-style]
description = "Python style"
local = ["engineering/python-style"]

[profiles.r]
description = "R tools"
local = ["engineering/r-style"]

[profiles.architecture]
description = "Architecture"
public = ["clean-architecture"]
"""

LOCAL_SKILL_NAMES = ("python-style", "r-style")


def write_skill(root: Path, category: str, name: str, frontmatter_name: str = "") -> Path:
    directory = root / category / "skills" / name
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {frontmatter_name or name}\ndescription: Test.\n---\n"
    )
    return directory


def point_paths_at(root: Path, config: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths, "ROOT", root)
    monkeypatch.setattr(paths, "CONF_TOML", config)
    monkeypatch.setattr(paths, "AGENTS_SKILLS_DIR", root / "store")
    monkeypatch.setattr(paths, "CLAUDE_SKILLS_DIR", root / "claude")
