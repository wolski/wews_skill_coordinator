"""The coord command. The only module that knows command names."""

from __future__ import annotations

from pathlib import Path

import cyclopts
from pydantic import ValidationError

from wews_skill_coordinator import paths
from wews_skill_coordinator.agent_config import links as agent_config
from wews_skill_coordinator.config.load import load_config
from wews_skill_coordinator.config.schema import SkillsConfig
from wews_skill_coordinator.memory import cleanup as memory_cleanup
from wews_skill_coordinator.memory import store as memory_store
from wews_skill_coordinator.plugins import marketplace
from wews_skill_coordinator.reports import bookkeeping as skill_bookkeeping
from wews_skill_coordinator.reports.view import read_coordinator
from wews_skill_coordinator.skills import checkouts, install, inventory, sweep
from wews_skill_coordinator.skills.audit import audit
from wews_skill_coordinator.skills.npx import update_npx_skills

app = cyclopts.App(
    name="coord",
    help="Install, switch, and inspect skill profiles for Claude Code and Codex.",
)

install_app = cyclopts.App(
    name="install",
    help="Install the active profile's skills, the Claude plugins, and the agent config links.\n\n"
    "With no command, installs all three.",
)
clean_app = cyclopts.App(
    name="clean",
    help="Remove installed skills, plugins, or stale memory. Name what to remove.",
)
list_app = cyclopts.App(
    name="list",
    help="Show installed skills, profiles, and plugins.\n\nWith no command, shows all three.",
)
report_app = cyclopts.App(
    name="report",
    help="Write read-only reports: review drift, SKILL.md bookkeeping, Claude memory.\n\n"
    "With no command, writes all three.",
)
for group in (install_app, clean_app, list_app, report_app):
    app.command(group)

clean_skills_app = cyclopts.App(
    name="skills",
    help="Remove installed skills, or with `all PATH` every skill folder under PATH.",
)
clean_memory_app = cyclopts.App(
    name="memory",
    help="Remove Claude memory stores: those no project claims, or with `all` every one.",
)
clean_app.command(clean_skills_app)
clean_app.command(clean_memory_app)


def _section(title: str) -> None:
    print(f"\n{title}")


def _config() -> SkillsConfig:
    """Load skills.toml, reporting a problem in it as a message rather than a traceback."""
    try:
        return load_config()
    except ValidationError as error:
        raise SystemExit(f"skills.toml: {_problems(error)}") from None
    except ValueError as error:
        raise SystemExit(f"skills.toml: {error}") from None


def _problems(error: ValidationError) -> str:
    messages: list[str] = []
    for problem in error.errors():
        location = ".".join(map(str, problem["loc"]))
        message = problem["msg"].removeprefix("Value error, ")
        messages.append(f"{location}: {message}" if location else message)
    return "; ".join(messages)


def _existing_directory(root: Path) -> Path:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"not a directory: {root}")
    return root


def _output_prefix(out: Path) -> Path:
    out = out.expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    return out



@install_app.default
def install_everything(*, dry_run: bool = False) -> None:
    """Install the active profile's skills, the plugins, and the agent config links.

    Args:
        dry_run: Show what would change without changing anything.
    """
    config = _config()
    _section("Skills")
    install.install_profile(config, None, dry_run=dry_run)
    _section("Plugins")
    marketplace.install(config, dry_run=dry_run)
    _section("Agent config")
    agent_config.install(dry_run=dry_run)


@install_app.command(name="skills")
def install_skills(*, profile: str | None = None, dry_run: bool = False) -> None:
    """Install a profile's skills. Removes nothing; switch with `coord clean skills` first.

    Args:
        profile: Profile to install instead of the active one in skills.toml.
        dry_run: Show what would change without changing anything.
    """
    install.install_profile(_config(), profile, dry_run=dry_run)


@install_app.command(name="plugins")
def install_plugins(*, dry_run: bool = False) -> None:
    """Install the Claude plugins listed in skills.toml.

    Args:
        dry_run: Show the commands without running them.
    """
    marketplace.install(_config(), dry_run=dry_run)


@install_app.command(name="config")
def install_agent_config(*, dry_run: bool = False) -> None:
    """Link the global AGENTS.md and the output styles from agent-config/.

    Args:
        dry_run: Show the links without creating them.
    """
    agent_config.install(dry_run=dry_run)



@clean_skills_app.default
def clean_installed_skills(*, dry_run: bool = False) -> None:
    """Remove every installed skill: all symlinks in ~/.agents/skills and all npx skills.

    Does not read skills.toml, so it works even when the file is broken. Hand-made
    skill folders in ~/.claude/skills stay.

    Args:
        dry_run: Show what would be removed without removing it.
    """
    install.clean(dry_run=dry_run)


@clean_skills_app.command(name="all")
def clean_skill_folders(path: Path = Path("."), *, dry_run: bool = False) -> None:
    """Find every folder holding a SKILL.md under PATH, recursively, and offer to remove them.

    Lists what it found, then asks once: n keeps everything (the default), b moves it
    to a backup folder (~/.coord_trash suggested), y deletes it. A symlinked skill
    folder loses only its link. Skips .git, .venv, node_modules, and PATH itself.

    Args:
        path: Folder to search.
        dry_run: List without asking.
    """
    sweep.clean_skill_folders(_existing_directory(path), dry_run=dry_run)


@clean_app.command(name="plugins")
def clean_plugins(*, dry_run: bool = False) -> None:
    """Uninstall the Claude plugins listed in skills.toml.

    Args:
        dry_run: Show the commands without running them.
    """
    marketplace.remove(_config(), dry_run=dry_run)


@clean_memory_app.default
def clean_unclaimed_memory(root: Path = paths.MEMORY_ROOT, *, dry_run: bool = False) -> None:
    """Offer to remove memory stores whose project exists nowhere, not even moved.

    Lists what it found, then asks once: n keeps everything (the default), b moves it
    to a backup folder (~/.coord_trash suggested), y deletes it.

    Args:
        root: Memory store to scan, one directory per project slug.
        dry_run: List without asking.
    """
    memory_cleanup.clean_unclaimed_stores(_existing_directory(root), dry_run=dry_run)


@clean_memory_app.command(name="all")
def clean_all_memory(root: Path = paths.MEMORY_ROOT, *, dry_run: bool = False) -> None:
    """Offer to remove every memory store, claimed or not.

    Lists what it found, then asks once: n keeps everything (the default), b moves it
    to a backup folder (~/.coord_trash suggested), y deletes it.

    Args:
        root: Memory store to scan, one directory per project slug.
        dry_run: List without asking.
    """
    memory_cleanup.clean_every_store(_existing_directory(root), dry_run=dry_run)


@list_app.default
def list_everything() -> None:
    """Show installed skills, profiles, and plugins."""
    config = _config()
    inventory.list_skills(config)
    print()
    inventory.list_profiles(config)
    _section("Plugins")
    marketplace.list_installed()


@list_app.command(name="skills")
def list_skills() -> None:
    """Show local sources, installed skills by kind, and the matching profile."""
    inventory.list_skills(_config())


@list_app.command(name="profiles")
def list_profiles() -> None:
    """Show every profile with its size, includes, and description."""
    inventory.list_profiles(_config())


@list_app.command(name="plugins")
def list_plugins() -> None:
    """Show the installed Claude plugins."""
    marketplace.list_installed()



@app.command
def update(*, dry_run: bool = False) -> None:
    """Clone missing checkouts, fast-forward the others, and update npx skills.

    Args:
        dry_run: Show what would change without changing anything.
    """
    config = _config()
    checkouts.clone(config, dry_run=dry_run)
    checkouts.pull(config, dry_run=dry_run)
    update_npx_skills(dry_run=dry_run)



@report_app.default
def report_everything() -> None:
    """Write all three reports with their default locations."""
    report_audit()
    report_bookkeeping()
    report_memory()


@report_app.command(name="audit")
def report_audit() -> None:
    """Show configured skills whose content changed since their last review."""
    audit(_config())


@report_app.command(name="bookkeeping")
def report_bookkeeping(
    root: Path = paths.SCAN_ROOT,
    *,
    out: Path = paths.BOOKKEEPING_OUT,
    html: bool = True,
) -> None:
    """Inventory every SKILL.md under ROOT and report how each one is held.

    Writes a CSV to filter, a Markdown report grouped by verdict, and an HTML
    rendering of that Markdown. Installs and moves nothing.

    Args:
        root: Folder to scan. A symlinked directory is recorded, not descended into.
        out: Report path without a suffix; .csv, .md and .html are added.
        html: Render the Markdown report to HTML.
    """
    skill_bookkeeping.run(
        _existing_directory(root),
        _output_prefix(out),
        read_coordinator(_config()),
        html=html,
    )


@report_app.command(name="memory")
def report_memory(
    root: Path = paths.MEMORY_ROOT,
    *,
    out: Path = paths.MEMORY_OUT,
    stale_days: int = 90,
    html: bool = True,
) -> None:
    """Inventory Claude Code's per-project memory store and flag what can go.

    Resolves each store's slug back to a real directory, so a store left behind by
    a renamed, moved, or deleted project is named exactly. Deletes nothing; use
    `coord clean memory` for that.

    Args:
        root: Memory store to scan, one directory per project slug.
        out: Report path without a suffix; .csv, .md and .html are added.
        stale_days: Age in days past which an untouched memory is called stale.
        html: Render the Markdown report to HTML.
    """
    memory_store.run(
        _existing_directory(root),
        _output_prefix(out),
        stale_days=stale_days,
        html=html,
    )
