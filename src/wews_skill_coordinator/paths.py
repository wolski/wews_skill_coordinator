"""Where the coordinator reads and writes: this checkout and the agents' stores.

Modules read these as ``paths.NAME`` at call time, so tests can repoint them.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONF_TOML = ROOT / "skills.toml"
AGENT_CONFIG_DIR = ROOT / "agent-config"
KAIROS_KNOW_DIR = ROOT / ".kairos" / "knowledge"
BOOKKEEPING_OUT = ROOT / "TODO" / "skill_bookkeeping"
MEMORY_OUT = ROOT / "TODO" / "claude_memory"

AGENTS_SKILLS_DIR = Path.home() / ".agents" / "skills"
CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"
NPX_LOCK = Path.home() / ".agents" / ".skill-lock.json"
AGENTS_MD_LINK = Path.home() / ".agents" / "AGENTS.md"
OUTPUT_STYLES_DIR = Path.home() / ".claude" / "output-styles"
SCAN_ROOT = Path.home() / "projects"
MEMORY_ROOT = Path.home() / ".claude" / "projects"
BACKUP_DIR = Path.home() / ".coord_trash"


def display(path: Path) -> str:
    """Show a path relative to this checkout when it lives inside it."""
    try:
        return str(path.relative_to(ROOT.resolve(strict=False)))
    except ValueError:
        return str(path)
