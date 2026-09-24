"""Link the global AGENTS.md and the output styles from agent-config/ into place."""

from __future__ import annotations

from pathlib import Path

from wews_skill_coordinator import paths
from wews_skill_coordinator.console import report


def config_links() -> list[tuple[Path, Path]]:
    """Each (link, target) pair: AGENTS.md, then every output style."""
    styles = sorted((paths.AGENT_CONFIG_DIR / "output-styles").glob("*.md"))
    return [
        (paths.AGENTS_MD_LINK, paths.AGENT_CONFIG_DIR / "AGENTS.md"),
        *((paths.OUTPUT_STYLES_DIR / style.name, style) for style in styles),
    ]


def install(*, dry_run: bool) -> None:
    """Link each file, replacing an existing symlink but never a real file."""
    for link, target in config_links():
        if link.is_symlink() and link.resolve() == target.resolve():
            continue
        if link.exists() and not link.is_symlink():
            print(f"  CONFLICT       {link} (a real file, not replacing it)")
            continue
        report("link", "linked", f"{link} -> {paths.display(target)}", dry_run=dry_run)
        if dry_run:
            continue
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink():
            link.unlink()
        link.symlink_to(target)
