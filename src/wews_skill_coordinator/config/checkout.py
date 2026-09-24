"""Where the working copies behind local sources live."""

from __future__ import annotations

from pathlib import Path

from wews_skill_coordinator import paths
from wews_skill_coordinator.config.schema import LocalSource, SkillsConfig


def source_root(source: LocalSource) -> Path:
    return (paths.ROOT / source.path).resolve(strict=False)


def source_roots(config: SkillsConfig) -> tuple[Path, ...]:
    """Every directory a coordinator-installed symlink may point into."""
    return (
        paths.ROOT.resolve(strict=False),
        *(source_root(source) for source in config.local_sources.values()),
    )
