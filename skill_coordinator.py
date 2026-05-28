#!/usr/bin/env python3
"""Claude Code Skills Coordinator — manage skills, agents, and plugins."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

import cyclopts
from pydantic import BaseModel, model_validator

app = cyclopts.App(
    name="skill-coordinator",
    help="Clone repos, symlink skills/agents, manage plugins.",
)

ROOT = Path(__file__).resolve().parent
REPOS_DIR = ROOT / "repos"
CONF_TOML = ROOT / "skills.toml"

SKILLS_DIR = Path.home() / ".claude" / "skills"
AGENTS_DIR = Path.home() / ".claude" / "agents"
CODEX_SKILLS_DIR = Path.home() / ".codex" / "skills"
KAIROS_KNOW_DIR = ROOT / ".kairos" / "knowledge"

DRY_RUN = False


# ── Config models ────────────────────────────────────────────────────


class PluginSource(BaseModel):
    names: list[str]


class RepoSkills(BaseModel):
    paths: list[str] = []
    agents: list[str] = []


class SkillsConfig(BaseModel):
    repos: dict[str, str]
    plugins: dict[str, PluginSource]
    skills: dict[str, RepoSkills]

    @model_validator(mode="after")
    def check_repo_keys(self) -> SkillsConfig:
        unknown = set(self.skills) - set(self.repos)
        if unknown:
            raise ValueError(f"skills sections reference unknown repos: {unknown}")
        return self


def load_config() -> SkillsConfig:
    with open(CONF_TOML, "rb") as f:
        raw = tomllib.load(f)
    return SkillsConfig(**raw)


# ── Shared types ─────────────────────────────────────────────────────


@dataclass
class ConfEntry:
    repo: str
    skill_path: str
    entry_type: str  # "skill" or "agent"
    name: str
    source: Path

    @property
    def is_agent(self) -> bool:
        return self.entry_type == "agent"


def parse_conf() -> list[ConfEntry]:
    cfg = load_config()
    entries: list[ConfEntry] = []
    for repo_name, repo_skills in cfg.skills.items():
        for skill_path in repo_skills.paths:
            name = Path(skill_path).name
            source = REPOS_DIR / repo_name / skill_path
            entries.append(ConfEntry(repo_name, skill_path, "skill", name, source))
        for agent_path in repo_skills.agents:
            name = Path(agent_path).name
            source = REPOS_DIR / repo_name / agent_path
            entries.append(ConfEntry(repo_name, agent_path, "agent", name, source))
    return entries


def _remove_managed_symlinks(*dirs: Path) -> None:
    for d in dirs:
        if not d.exists():
            continue
        for link in d.iterdir():
            if link.is_symlink():
                target = link.resolve()
                try:
                    target.relative_to(REPOS_DIR)
                    tag = "would remove" if DRY_RUN else "removed"
                    print(f"  {tag:14s} {link.name}")
                    if not DRY_RUN:
                        link.unlink()
                except ValueError:
                    pass


def _list_dir(label: str, d: Path) -> None:
    print(f"{label}:")
    print()
    if not d.exists():
        print("  (directory does not exist)")
        print()
        return
    found = False
    for item in sorted(d.iterdir()):
        found = True
        name = item.name
        if item.is_symlink():
            target = item.readlink()
            try:
                rel = target.relative_to(REPOS_DIR)
                print(f"  {name} -> {rel}")
            except ValueError:
                print(f"  {name} -> {target} (external)")
        elif item.is_dir():
            print(f"  {name} (directory, not managed)")
        elif item.is_file():
            print(f"  {name} (file, not managed)")
    if not found:
        print("  (empty)")
    print()


# ── Commands ──────────────────────────────────────────────────────────


@app.command
def clone(*, dry_run: bool = False) -> None:
    """Clone all upstream repos into repos/ (skip if exists)."""
    global DRY_RUN
    DRY_RUN = dry_run
    if not DRY_RUN:
        REPOS_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in load_config().repos.items():
        dest = REPOS_DIR / name
        if dest.exists():
            print(f"  exists   {name}")
        else:
            tag = "would clone" if DRY_RUN else "cloning"
            print(f"  {tag:14s} {name}  ({url})")
            if not DRY_RUN:
                subprocess.run(
                    ["git", "clone", "--depth", "1", url, str(dest)], check=True
                )


@app.command
def update() -> None:
    """Pull latest from all repos."""
    for repo in sorted(REPOS_DIR.iterdir()):
        if not (repo / ".git").is_dir():
            continue
        print(f"  pulling  {repo.name}")
        result = subprocess.run(
            ["git", "-C", str(repo), "pull", "--ff-only"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  WARNING: pull failed for {repo.name} (check manually)")


@app.command
def install(*, dry_run: bool = False) -> None:
    """Symlink skills and agents from skills.toml."""
    global DRY_RUN
    DRY_RUN = dry_run
    if not DRY_RUN:
        for d in (SKILLS_DIR, AGENTS_DIR, CODEX_SKILLS_DIR):
            d.mkdir(parents=True, exist_ok=True)

    _remove_managed_symlinks(SKILLS_DIR, AGENTS_DIR, CODEX_SKILLS_DIR)

    for entry in parse_conf():
        if not entry.source.exists():
            print(f"  MISSING  {entry.repo}/{entry.skill_path}")
            continue

        dest_dir = AGENTS_DIR if entry.is_agent else SKILLS_DIR
        target = dest_dir / entry.name

        if not DRY_RUN and target.exists():
            print(f"  CONFLICT {entry.name} (already exists, skipping)")
            continue

        tag = "would link" if DRY_RUN else "linked"
        print(f"  {tag:14s} {entry.name} -> {entry.repo}/{entry.skill_path} ({dest_dir})")
        if not DRY_RUN:
            target.symlink_to(entry.source)

        if not entry.is_agent:
            codex_target = CODEX_SKILLS_DIR / entry.name
            if not DRY_RUN and codex_target.exists():
                print(f"  CONFLICT {entry.name} (codex, already exists, skipping)")
            else:
                print(f"  {tag:14s} {entry.name} -> {entry.repo}/{entry.skill_path} ({CODEX_SKILLS_DIR})")
                if not DRY_RUN:
                    codex_target.symlink_to(entry.source)


@app.command
def clean(*, dry_run: bool = False) -> None:
    """Remove all managed symlinks."""
    global DRY_RUN
    DRY_RUN = dry_run
    _remove_managed_symlinks(SKILLS_DIR, AGENTS_DIR, CODEX_SKILLS_DIR)


@app.command(name="list")
def list_installed() -> None:
    """Show currently installed skills and agents."""
    _list_dir(f"Installed skills in {SKILLS_DIR}", SKILLS_DIR)
    _list_dir(f"Installed agents in {AGENTS_DIR}", AGENTS_DIR)
    _list_dir(f"Installed skills in {CODEX_SKILLS_DIR}", CODEX_SKILLS_DIR)


@app.command
def status() -> None:
    """Show git status of each repo."""
    for repo in sorted(REPOS_DIR.iterdir()):
        if not (repo / ".git").is_dir():
            continue
        print(f"=== {repo.name} ===")
        subprocess.run(
            ["git", "-C", str(repo), "log", "--oneline", "-1"],
        )
        print()


@app.command
def audit() -> None:
    """Report skills with upstream drift since last review."""
    ok = drift = unrev = missing = 0
    for entry in parse_conf():
        if entry.is_agent:
            prefix = "agent"
            name_clean = entry.name.removesuffix(".md")
        else:
            prefix = "skill"
            name_clean = entry.name
        slug = f"{prefix}_{name_clean.replace('-', '_')}"
        knowledge_file = KAIROS_KNOW_DIR / slug / f"{slug}.md"

        result = subprocess.run(
            ["git", "-C", str(REPOS_DIR / entry.repo), "log", "-1", "--format=%H", "--", entry.skill_path],
            capture_output=True,
            text=True,
        )
        cur_sha = result.stdout.strip()

        if not knowledge_file.exists():
            print(f"  MISSING-ENTRY  {entry.name}")
            missing += 1
            continue

        rev_sha = ""
        for line in knowledge_file.read_text().splitlines():
            if line.startswith("last_reviewed_sha:"):
                rev_sha = line.split(":", 1)[1].strip()
                break

        if not rev_sha:
            print(f"  UNREVIEWED     {entry.name}  (current {cur_sha[:8]})")
            unrev += 1
        elif rev_sha != cur_sha:
            print(f"  DRIFT          {entry.name}  {rev_sha[:8]} -> {cur_sha[:8]}")
            drift += 1
        else:
            ok += 1

    print()
    print(f"  Summary: {ok} ok, {drift} drift, {unrev} unreviewed, {missing} missing-entry")


# ── Plugin subcommands ────────────────────────────────────────────────

plugins_app = cyclopts.App(name="plugins", help="Manage Claude Code plugins.")
app.command(plugins_app)


@plugins_app.command
def install_plugins(*, dry_run: bool = False) -> None:
    """Install all managed plugins from marketplace."""
    for marketplace, source in load_config().plugins.items():
        for p in source.names:
            if dry_run:
                print(f"  would install {p} ({marketplace})")
            else:
                print(f"  installing {p} ({marketplace})")
                result = subprocess.run(
                    ["claude", "plugin", "install", f"{p}@{marketplace}"],
                    capture_output=True,
                    text=True,
                )
                for line in (result.stdout + result.stderr).splitlines():
                    print(f"    {line}")


@plugins_app.command
def remove(*, dry_run: bool = False) -> None:
    """Uninstall all managed plugins."""
    for _marketplace, source in load_config().plugins.items():
        for p in source.names:
            if dry_run:
                print(f"  would remove {p}")
            else:
                print(f"  removing {p}")
                result = subprocess.run(
                    ["claude", "plugin", "uninstall", p],
                    capture_output=True,
                    text=True,
                )
                for line in (result.stdout + result.stderr).splitlines():
                    print(f"    {line}")


@plugins_app.command(name="list")
def list_plugins() -> None:
    """List installed plugins."""
    subprocess.run(["claude", "plugin", "list"])


if __name__ == "__main__":
    app()
