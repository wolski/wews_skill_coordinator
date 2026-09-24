"""Compare installed skill content with the recorded review of each skill."""

from __future__ import annotations

import json
from pathlib import Path

from wews_skill_coordinator import paths
from wews_skill_coordinator.config.checkout import source_roots
from wews_skill_coordinator.config.schema import SkillsConfig
from wews_skill_coordinator.console import print_table
from wews_skill_coordinator.skills.checkouts import git
from wews_skill_coordinator.skills.links import managed_links


def _installed_hashes() -> dict[str, str]:
    if not paths.NPX_LOCK.exists():
        return {}
    lock = json.loads(paths.NPX_LOCK.read_text())
    return {
        name: str(record.get("skillFolderHash", ""))
        for name, record in lock.get("skills", {}).items()
    }


def _reviewed_sha(name: str) -> str:
    slug = f"skill_{name.replace('-', '_')}"
    knowledge = paths.KAIROS_KNOW_DIR / slug / f"{slug}.md"
    if not knowledge.exists():
        return ""
    for line in knowledge.read_text().splitlines():
        if line.startswith("last_reviewed_sha:"):
            return line.split(":", 1)[1].strip()
    return ""


def _local_content_sha(directory: Path) -> str:
    """Last commit touching this skill, in whichever repository holds it."""
    top_level = git(directory, "rev-parse", "--show-toplevel")
    if not top_level:
        return ""
    repository = Path(top_level)
    relative = directory.relative_to(repository)
    return git(repository, "log", "-1", "--format=%H", "--", str(relative))


def _current_shas(config: SkillsConfig) -> dict[str, str]:
    current = _installed_hashes()
    for name, target in managed_links(source_roots(config)).items():
        current[name] = _local_content_sha(target)
    return current


def audit(config: SkillsConfig) -> None:
    """Report configured skills whose content changed since review."""
    current_by_name = _current_shas(config)
    counts = {"ok": 0, "drift": 0, "unreviewed": 0, "not installed": 0}
    rows: list[tuple[str, str, str]] = []
    for name in sorted(config.skill_names()):
        current = current_by_name.get(name, "")
        reviewed = _reviewed_sha(name)
        if not current:
            counts["not installed"] += 1
            rows.append(("NOT-INSTALLED", name, ""))
        elif not reviewed:
            counts["unreviewed"] += 1
            rows.append(("UNREVIEWED", name, f"current {current[:8]}"))
        elif reviewed != current:
            counts["drift"] += 1
            rows.append(("DRIFT", name, f"{reviewed[:8]} -> {current[:8]}"))
        else:
            counts["ok"] += 1
    print_table("Skills needing review", ("Status", "Skill", "Detail"), rows)
    print("  Summary: " + ", ".join(f"{count} {label}" for label, count in counts.items()))
