"""Manage switchable skill profiles with the upstream npx skills CLI."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

import cyclopts
from pydantic import BaseModel, Field, model_validator

app = cyclopts.App(
    name="skill-coordinator",
    help="Install npx skills, switch profiles, and manage agents/plugins.",
)

ROOT = Path(__file__).resolve().parent
CONF_TOML = ROOT / "skills.toml"
REPOS_DIR = ROOT / "repos"
NPX_SKILLS_VERSION = "1.5.23"
NPX_LOCK = Path.home() / ".agents" / ".skill-lock.json"
CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"
CODEX_SKILLS_DIR = Path.home() / ".codex" / "skills"
AGENTS_DIR = Path.home() / ".claude" / "agents"
KAIROS_KNOW_DIR = ROOT / ".kairos" / "knowledge"


class PluginSource(BaseModel):
    names: list[str]


class PackageOptions(BaseModel):
    full_depth: bool = False


class AgentSource(BaseModel):
    repository: str
    agents: list[str] = Field(default_factory=list)


class Profile(BaseModel):
    description: str
    includes: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)


class SkillsConfig(BaseModel):
    plugins: dict[str, PluginSource] = Field(default_factory=dict)
    package_options: dict[str, PackageOptions] = Field(default_factory=dict)
    agent_sources: dict[str, AgentSource] = Field(default_factory=dict)
    profiles: dict[str, Profile] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_names(self) -> SkillsConfig:
        agent_names = [
            Path(agent).name
            for source in self.agent_sources.values()
            for agent in source.agents
        ]
        self._reject_duplicates("agent", agent_names)
        package_by_skill: dict[str, str] = {}
        referenced_packages: set[str] = set()
        for profile_name, profile in self.profiles.items():
            self._validate_includes(profile_name, profile.includes)
            self._reject_duplicates(
                f"skill references in profile {profile_name!r}", profile.skills
            )
            for value in profile.skills:
                reference = SkillReference.parse(value)
                referenced_packages.add(reference.package)
                previous_package = package_by_skill.setdefault(
                    reference.name, reference.package
                )
                if previous_package != reference.package:
                    raise ValueError(
                        f"skill {reference.name!r} is referenced from both "
                        f"{previous_package!r} and {reference.package!r}"
                    )
            self._validate_agents(profile_name, profile.agents, set(agent_names))
        self._validate_composition_graph()
        unknown_options = set(self.package_options) - referenced_packages
        if unknown_options:
            raise ValueError(
                f"package options reference unused packages: {unknown_options}"
            )
        if "full" in self.profiles:
            full_profile = self.profiles["full"]
            if full_profile.includes != ["*"] or full_profile.skills:
                raise ValueError(
                    "profile 'full' must use includes = ['*'] and declare no skills"
                )
            full_references = {
                reference.identifier
                for reference in profile_skill_references("full", self)
            }
            outside_full = {
                reference.identifier
                for reference in all_skill_references(self)
                if reference.identifier not in full_references
            }
            if outside_full:
                raise ValueError(
                    f"profiles reference skills absent from the full profile: {outside_full}"
                )
        return self

    def _validate_includes(self, profile_name: str, includes: list[str]) -> None:
        self._reject_duplicates(
            f"included profiles in profile {profile_name!r}", includes
        )
        if "*" in includes and includes != ["*"]:
            raise ValueError(
                f"profile {profile_name!r} must use '*' alone for includes"
            )
        if includes == ["*"] and profile_name != "full":
            raise ValueError("only the 'full' profile may include '*'")
        unknown = set(includes) - set(self.profiles) - {"*"}
        if unknown:
            raise ValueError(
                f"profile {profile_name!r} includes unknown profiles: {unknown}"
            )
        if profile_name in includes:
            raise ValueError(f"profile {profile_name!r} cannot include itself")

    def _validate_composition_graph(self) -> None:
        def visit(profile_name: str, trail: tuple[str, ...]) -> None:
            if profile_name in trail:
                cycle = " -> ".join((*trail, profile_name))
                raise ValueError(f"profile inclusion cycle: {cycle}")
            for included in included_profile_names(profile_name, self):
                visit(included, (*trail, profile_name))

        for profile_name in self.profiles:
            visit(profile_name, ())

    @staticmethod
    def _reject_duplicates(kind: str, names: list[str]) -> None:
        duplicates = {name for name in names if names.count(name) > 1}
        if duplicates:
            raise ValueError(f"duplicate {kind} names: {duplicates}")

    @staticmethod
    def _validate_agents(
        profile_name: str,
        members: list[str],
        known: set[str],
    ) -> None:
        if "*" in members and members != ["*"]:
            raise ValueError(f"profile {profile_name!r} must use '*' alone for agents")
        unknown = set(members) - known - {"*"}
        if unknown:
            raise ValueError(
                f"profile {profile_name!r} references unknown agents: {unknown}"
            )


@dataclass(frozen=True, slots=True)
class SkillReference:
    package: str
    name: str

    @classmethod
    def parse(cls, value: str) -> SkillReference:
        """Parse the coordinator's owner/repository@skill notation."""
        if value.count("@") != 1:
            raise ValueError(
                f"invalid skill reference {value!r}; expected owner/repository@skill"
            )
        package, name = value.split("@")
        if (
            package.count("/") != 1
            or not all(package.split("/"))
            or not name
            or "/" in name
            or any(character.isspace() for character in value)
        ):
            raise ValueError(
                f"invalid skill reference {value!r}; expected owner/repository@skill"
            )
        return cls(package=package, name=name)

    @property
    def identifier(self) -> str:
        return f"{self.package}@{self.name}"


@dataclass(frozen=True, slots=True)
class PackageSelection:
    package: str
    skills: tuple[str, ...]
    full_depth: bool

    def add_command(self) -> list[str]:
        command = npx_command(
            "add",
            self.package,
            "--skill",
            *self.skills,
            "--agent",
            "claude-code",
            "codex",
            "--global",
            "--yes",
        )
        if self.full_depth:
            command.append("--full-depth")
        return command


@dataclass(frozen=True, slots=True)
class AgentEntry:
    source_name: str
    relative_path: str
    source: Path

    @property
    def name(self) -> str:
        return Path(self.relative_path).name


@dataclass(frozen=True, slots=True)
class ProfileSelection:
    packages: tuple[PackageSelection, ...]
    skill_names: frozenset[str]
    agents: tuple[AgentEntry, ...]


def load_config() -> SkillsConfig:
    with CONF_TOML.open("rb") as stream:
        return SkillsConfig(**tomllib.load(stream))


def npx_command(*arguments: str) -> list[str]:
    return ["npx", "--yes", f"skills@{NPX_SKILLS_VERSION}", *arguments]


def all_skill_references(config: SkillsConfig) -> tuple[SkillReference, ...]:
    unique = {
        reference.identifier: reference
        for profile in config.profiles.values()
        for reference in map(SkillReference.parse, profile.skills)
    }
    return tuple(unique.values())


def included_profile_names(profile_name: str, config: SkillsConfig) -> tuple[str, ...]:
    includes = config.profiles[profile_name].includes
    if includes == ["*"]:
        return tuple(name for name in config.profiles if name != profile_name)
    return tuple(includes)


def profile_skill_references(
    profile_name: str, config: SkillsConfig
) -> tuple[SkillReference, ...]:
    unique: dict[str, SkillReference] = {}
    for included in included_profile_names(profile_name, config):
        for reference in profile_skill_references(included, config):
            unique.setdefault(reference.identifier, reference)
    for reference in map(SkillReference.parse, config.profiles[profile_name].skills):
        unique.setdefault(reference.identifier, reference)
    return tuple(unique.values())


def all_skill_names(config: SkillsConfig) -> frozenset[str]:
    return frozenset(reference.name for reference in all_skill_references(config))


def all_agent_entries(config: SkillsConfig) -> tuple[AgentEntry, ...]:
    return tuple(
        AgentEntry(source_name, path, REPOS_DIR / source_name / path)
        for source_name, source in config.agent_sources.items()
        for path in source.agents
    )


def profile_agent_names(profile_name: str, config: SkillsConfig) -> frozenset[str]:
    names: set[str] = set()
    for included in included_profile_names(profile_name, config):
        names.update(profile_agent_names(included, config))
    agents = config.profiles[profile_name].agents
    if agents == ["*"]:
        names.update(entry.name for entry in all_agent_entries(config))
    else:
        names.update(agents)
    return frozenset(names)


def resolve_profile(
    profile_name: str, config: SkillsConfig | None = None
) -> ProfileSelection:
    config = config or load_config()
    if profile_name not in config.profiles:
        available = ", ".join(sorted(config.profiles)) or "none"
        raise ValueError(
            f"unknown profile {profile_name!r}; available profiles: {available}"
        )
    references = profile_skill_references(profile_name, config)
    references_by_package: dict[str, list[SkillReference]] = {}
    for reference in references:
        references_by_package.setdefault(reference.package, []).append(reference)
    packages = tuple(
        PackageSelection(
            package=package,
            skills=tuple(reference.name for reference in package_references),
            full_depth=config.package_options.get(package, PackageOptions()).full_depth,
        )
        for package, package_references in references_by_package.items()
    )
    entries = all_agent_entries(config)
    selected_agent_names = profile_agent_names(profile_name, config)
    return ProfileSelection(
        packages=packages,
        skill_names=frozenset(reference.name for reference in references),
        agents=tuple(entry for entry in entries if entry.name in selected_agent_names),
    )


def _show_command(command: list[str]) -> str:
    return " ".join(command)


def _run_npx(
    command: list[str], *, dry_run: bool
) -> subprocess.CompletedProcess[str] | None:
    if dry_run:
        print(f"  would run  {_show_command(command)}")
        return None
    return subprocess.run(command, check=True, text=True)


def _ensure_agent_repositories(
    config: SkillsConfig, selected_agents: tuple[AgentEntry, ...], *, dry_run: bool
) -> None:
    selected_sources = {entry.source_name for entry in selected_agents}
    for source_name in selected_sources:
        destination = REPOS_DIR / source_name
        if destination.exists():
            continue
        repository = config.agent_sources[source_name].repository
        command = ["git", "clone", "--depth", "1", repository, str(destination)]
        if dry_run:
            print(f"  would run  {_show_command(command)}")
        else:
            REPOS_DIR.mkdir(parents=True, exist_ok=True)
            subprocess.run(command, check=True)


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _remove_links_to_repositories(directory: Path, *, dry_run: bool) -> None:
    if not directory.exists():
        return
    for path in directory.iterdir():
        if path.is_symlink() and _is_under(path, REPOS_DIR):
            tag = "would remove" if dry_run else "removed"
            print(f"  {tag:12s} legacy link {path}")
            if not dry_run:
                path.unlink()


def _install_agents(entries: tuple[AgentEntry, ...], *, dry_run: bool) -> None:
    _remove_links_to_repositories(AGENTS_DIR, dry_run=dry_run)
    if not dry_run:
        AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        if not entry.source.exists() and not dry_run:
            raise FileNotFoundError(f"missing agent source: {entry.source}")
        destination = AGENTS_DIR / entry.name
        if destination.exists() or destination.is_symlink():
            managed_link_pending_removal = (
                dry_run
                and destination.is_symlink()
                and _is_under(destination, REPOS_DIR)
            )
            if not managed_link_pending_removal:
                raise FileExistsError(
                    f"agent destination already exists: {destination}"
                )
        tag = "would link" if dry_run else "linked"
        print(f"  {tag:12s} {entry.name} -> {entry.source}")
        if not dry_run:
            destination.symlink_to(entry.source)


def _remove_skills(skill_names: frozenset[str], *, dry_run: bool) -> None:
    if not skill_names:
        return
    _run_npx(
        npx_command("remove", *sorted(skill_names), "--global", "--yes"),
        dry_run=dry_run,
    )


def _switch(profile: str, *, dry_run: bool) -> None:
    config = load_config()
    selection = resolve_profile(profile, config)
    _ensure_agent_repositories(config, selection.agents, dry_run=dry_run)

    # Installation is deliberately first: a failed source leaves the active set intact.
    for package in selection.packages:
        _run_npx(package.add_command(), dry_run=dry_run)

    _remove_skills(all_skill_names(config) - selection.skill_names, dry_run=dry_run)
    for directory in (CLAUDE_SKILLS_DIR, CODEX_SKILLS_DIR):
        _remove_links_to_repositories(directory, dry_run=dry_run)
    _install_agents(selection.agents, dry_run=dry_run)
    print(f"  active profile: {profile}")


@app.command
def switch(*, profile: str = "full", dry_run: bool = False) -> None:
    """Install and activate exactly one configured skill profile."""
    _switch(profile, dry_run=dry_run)


@app.command
def install(*, profile: str = "full", dry_run: bool = False) -> None:
    """Install a profile (compatibility alias for switch)."""
    _switch(profile, dry_run=dry_run)


@app.command
def update(*, dry_run: bool = False) -> None:
    """Update globally installed npx skills and standalone agent sources."""
    _run_npx(npx_command("update", "--global", "--yes"), dry_run=dry_run)
    for source_name in load_config().agent_sources:
        repository = REPOS_DIR / source_name
        if not (repository / ".git").is_dir():
            continue
        command = ["git", "-C", str(repository), "pull", "--ff-only"]
        if dry_run:
            print(f"  would run  {_show_command(command)}")
        else:
            subprocess.run(command, check=True)


@app.command
def clean(*, dry_run: bool = False) -> None:
    """Remove configured npx skills and managed standalone agents."""
    _remove_skills(all_skill_names(load_config()), dry_run=dry_run)
    for directory in (CLAUDE_SKILLS_DIR, CODEX_SKILLS_DIR, AGENTS_DIR):
        _remove_links_to_repositories(directory, dry_run=dry_run)


def _parse_npx_list(output: str) -> list[dict[str, object]]:
    start = output.find("[\n")
    if start < 0:
        start = output.find("[")
    if start < 0:
        raise ValueError("npx skills list did not return a JSON array")
    records = json.loads(output[start:])
    if not isinstance(records, list):
        raise TypeError("npx skills list returned unexpected JSON")
    return records


def installed_skills() -> list[dict[str, object]]:
    result = subprocess.run(
        npx_command("list", "--global", "--json"),
        check=True,
        capture_output=True,
        text=True,
    )
    return _parse_npx_list(result.stdout)


@app.command(name="list")
def list_installed() -> None:
    """List global npx skills, managed agents, and matching profiles."""
    records = installed_skills()
    names = {str(record["name"]) for record in records}
    for record in records:
        agent_values = record.get("agents", [])
        agents = (
            ", ".join(str(agent) for agent in agent_values)
            if isinstance(agent_values, list)
            else ""
        )
        name = str(record["name"])
        print(f"  {name:45s} {agents}")
    configured_installed = names & all_skill_names(load_config())
    matches = [
        name
        for name in load_config().profiles
        if resolve_profile(name).skill_names == configured_installed
    ]
    print()
    print(f"  matching profile: {', '.join(matches) if matches else 'none'}")
    print("  managed agents:")
    for entry in all_agent_entries(load_config()):
        destination = AGENTS_DIR / entry.name
        if destination.is_symlink() and _is_under(destination, REPOS_DIR):
            print(f"    {entry.name}")


@app.command
def profiles() -> None:
    """List configured skill profiles."""
    config = load_config()
    for name, profile in config.profiles.items():
        resolved = resolve_profile(name, config)
        includes = ", ".join(profile.includes) if profile.includes else "none"
        print(f"  {name}")
        print(f"    {profile.description}")
        print(
            f"    skills={len(resolved.skill_names)} (direct={len(profile.skills)}), "
            f"agents={len(resolved.agents)}, includes={includes}"
        )


@app.command
def status() -> None:
    """Show the Git status of standalone agent repositories."""
    for source_name in load_config().agent_sources:
        repository = REPOS_DIR / source_name
        print(f"=== {source_name} ===")
        if not (repository / ".git").is_dir():
            print("  not cloned")
            continue
        subprocess.run(
            ["git", "-C", str(repository), "status", "--short", "--branch"], check=False
        )


def _installed_hashes() -> dict[str, str]:
    if not NPX_LOCK.exists():
        return {}
    lock = json.loads(NPX_LOCK.read_text())
    return {
        name: str(record.get("skillFolderHash", ""))
        for name, record in lock.get("skills", {}).items()
    }


@app.command
def audit() -> None:
    """Report configured skills whose installed content changed since review."""
    hashes = _installed_hashes()
    ok = drift = unreviewed = missing = 0
    for name in sorted(all_skill_names(load_config())):
        current = hashes.get(name, "")
        if not current:
            print(f"  NOT-INSTALLED  {name}")
            missing += 1
            continue
        slug = f"skill_{name.replace('-', '_')}"
        knowledge = KAIROS_KNOW_DIR / slug / f"{slug}.md"
        reviewed = ""
        if knowledge.exists():
            for line in knowledge.read_text().splitlines():
                if line.startswith("last_reviewed_sha:"):
                    reviewed = line.split(":", 1)[1].strip()
                    break
        if not reviewed:
            print(f"  UNREVIEWED     {name}  (current {current[:8]})")
            unreviewed += 1
        elif reviewed != current:
            print(f"  DRIFT          {name}  {reviewed[:8]} -> {current[:8]}")
            drift += 1
        else:
            ok += 1
    print(
        f"\n  Summary: {ok} ok, {drift} drift, {unreviewed} unreviewed, {missing} not installed"
    )


plugins_app = cyclopts.App(name="plugins", help="Manage Claude Code plugins.")
app.command(plugins_app)


@plugins_app.command
def install_plugins(*, dry_run: bool = False) -> None:
    """Install all configured Claude Code plugins."""
    for marketplace, source in load_config().plugins.items():
        for plugin in source.names:
            command = ["claude", "plugin", "install", f"{plugin}@{marketplace}"]
            if dry_run:
                print(f"  would run  {_show_command(command)}")
            else:
                subprocess.run(command, check=True)


@plugins_app.command
def remove(*, dry_run: bool = False) -> None:
    """Uninstall all configured Claude Code plugins."""
    for source in load_config().plugins.values():
        for plugin in source.names:
            command = ["claude", "plugin", "uninstall", plugin]
            if dry_run:
                print(f"  would run  {_show_command(command)}")
            else:
                subprocess.run(command, check=True)


@plugins_app.command(name="list")
def list_plugins() -> None:
    """List installed Claude Code plugins."""
    subprocess.run(["claude", "plugin", "list"], check=False)


if __name__ == "__main__":
    app()
