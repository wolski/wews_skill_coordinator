"""Manage switchable skill profiles across npx packages and local checkouts.

Packages declared under ``[sources]`` are installed from a working copy on this
machine as symlinks, so editing the source is immediately live for both agents.
Every other package is installed with the pinned ``npx skills`` CLI.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

import cyclopts
from pydantic import BaseModel, Field, model_validator

import skill_bookkeeping

app = cyclopts.App(
    name="skill-coordinator",
    help="Install skills from npx packages and local checkouts, and switch profiles.",
)

ROOT = Path(__file__).resolve().parent
CONF_TOML = ROOT / "skills.toml"
NPX_SKILLS_VERSION = "1.5.23"
AGENTS_SKILLS_DIR = Path.home() / ".agents" / "skills"
CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"
NPX_LOCK = Path.home() / ".agents" / ".skill-lock.json"
KAIROS_KNOW_DIR = ROOT / ".kairos" / "knowledge"
SCAN_ROOT = Path.home() / "projects"
BOOKKEEPING_OUT = ROOT / "TODO" / "skill_bookkeeping"

# Claude Code reads its own directory; npx points it at the shared store with
# exactly this relative link, and locally installed skills match that layout.
CLAUDE_LINK_PREFIX = "../../.agents/skills"


class PluginSource(BaseModel):
    names: list[str]


class PackageOptions(BaseModel):
    full_depth: bool = False


class Source(BaseModel):
    """A package installed from a working copy instead of through npx."""

    path: str
    owned: bool = False
    git_url: str | None = None


class Profile(BaseModel):
    description: str
    includes: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class SkillsConfig(BaseModel):
    plugins: dict[str, PluginSource] = Field(default_factory=dict)
    package_options: dict[str, PackageOptions] = Field(default_factory=dict)
    sources: dict[str, Source] = Field(default_factory=dict)
    profiles: dict[str, Profile] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_names(self) -> SkillsConfig:
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
        self._validate_composition_graph()
        self._validate_package_tables(referenced_packages)
        self._validate_full_profile()
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

    def _validate_package_tables(self, referenced_packages: set[str]) -> None:
        unknown_options = set(self.package_options) - referenced_packages
        if unknown_options:
            raise ValueError(
                f"package options reference unused packages: {unknown_options}"
            )
        unknown_sources = set(self.sources) - referenced_packages
        if unknown_sources:
            raise ValueError(f"sources reference unused packages: {unknown_sources}")
        both = set(self.sources) & set(self.package_options)
        if both:
            raise ValueError(
                f"packages are installed locally, so npx package options do not apply: {both}"
            )

    def _validate_full_profile(self) -> None:
        if "full" not in self.profiles:
            return
        full_profile = self.profiles["full"]
        if full_profile.includes != ["*"] or full_profile.skills:
            raise ValueError(
                "profile 'full' must use includes = ['*'] and declare no skills"
            )
        full_references = {
            reference.identifier for reference in profile_skill_references("full", self)
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

    @staticmethod
    def _reject_duplicates(kind: str, names: list[str]) -> None:
        duplicates = {name for name in names if names.count(name) > 1}
        if duplicates:
            raise ValueError(f"duplicate {kind} names: {duplicates}")


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
class LocalSkill:
    name: str
    package: str
    directory: Path


@dataclass(frozen=True, slots=True)
class ProfileSelection:
    packages: tuple[PackageSelection, ...]
    local: tuple[LocalSkill, ...]
    missing: tuple[str, ...]
    skill_names: frozenset[str]


def load_config() -> SkillsConfig:
    with CONF_TOML.open("rb") as stream:
        config = SkillsConfig(**tomllib.load(stream))
    validate_sources(config)
    return config


# ── Local sources ─────────────────────────────────────────────────────


def source_root(source: Source) -> Path:
    return (ROOT / source.path).resolve(strict=False)


def _frontmatter_name(path: Path) -> str:
    lines = path.read_text().splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"skill has no YAML frontmatter: {path}")
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip().strip("'\"")
            if name:
                return name
    raise ValueError(f"skill frontmatter has no name: {path}")


def source_inventory(source: Source) -> dict[str, Path]:
    """Map skill name to source directory for one local source.

    Skills live at ``<category>/skills/<name>/SKILL.md`` under the source root.
    An owned source must contain nothing else; a third-party checkout may, and
    anything off the pattern there is simply not a skill this repository installs.
    """
    root = source_root(source)
    inventory: dict[str, Path] = {}
    for path in sorted(root.rglob("SKILL.md")):
        relative = path.relative_to(root)
        if len(relative.parts) != 4 or relative.parts[1] != "skills":
            if source.owned:
                raise ValueError(
                    f"local skill must live at <category>/skills/<name>/SKILL.md: {path}"
                )
            continue
        name = _frontmatter_name(path)
        if relative.parts[2] != name:
            if source.owned:
                raise ValueError(
                    f"skill directory {relative.parts[2]!r} disagrees with name {name!r}"
                )
            continue
        if name in inventory:
            raise ValueError(
                f"duplicate local skill name {name!r}: {inventory[name]} and {path}"
            )
        inventory[name] = path.parent
    return inventory


def validate_sources(config: SkillsConfig) -> None:
    """Check every present source checkout against the configured references."""
    seen: dict[str, str] = {}
    for package, source in config.sources.items():
        configured = {
            reference.name
            for reference in all_skill_references(config)
            if reference.package == package
        }
        if not source_root(source).is_dir():
            continue  # not cloned yet; `clone` fetches it and `install` reports it
        inventory = source_inventory(source)
        for name in inventory:
            owner = seen.setdefault(name, package)
            if owner != package and name in configured:
                raise ValueError(
                    f"skill {name!r} is provided by both {owner!r} and {package!r}"
                )
        if not source.owned:
            # A third-party checkout may sit on any branch. A configured skill it
            # does not carry is reported by `install`, not raised here, so that
            # `clone`, `list` and `profiles` keep working.
            continue
        problems: list[str] = []
        missing = configured - set(inventory)
        if missing:
            problems.append(f"missing={sorted(missing)}")
        unconfigured = set(inventory) - configured
        if unconfigured:
            problems.append(f"unconfigured={sorted(unconfigured)}")
        if problems:
            raise ValueError(
                f"source {package!r} disagrees with skills.toml: {', '.join(problems)}"
            )


def local_skill_names(config: SkillsConfig) -> frozenset[str]:
    return frozenset(
        reference.name
        for reference in all_skill_references(config)
        if reference.package in config.sources
    )


def npx_skill_names(config: SkillsConfig) -> frozenset[str]:
    return all_skill_names(config) - local_skill_names(config)


# ── Reference resolution ──────────────────────────────────────────────


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
    inventories = {
        package: source_inventory(source) if source_root(source).is_dir() else {}
        for package, source in config.sources.items()
    }
    npx_references: dict[str, list[SkillReference]] = {}
    local: list[LocalSkill] = []
    missing: list[str] = []
    for reference in references:
        if reference.package not in config.sources:
            npx_references.setdefault(reference.package, []).append(reference)
            continue
        directory = inventories[reference.package].get(reference.name)
        if directory is None:
            missing.append(reference.name)
        else:
            local.append(
                LocalSkill(
                    name=reference.name,
                    package=reference.package,
                    directory=directory,
                )
            )
    packages = tuple(
        PackageSelection(
            package=package,
            skills=tuple(reference.name for reference in package_references),
            full_depth=config.package_options.get(package, PackageOptions()).full_depth,
        )
        for package, package_references in npx_references.items()
    )
    return ProfileSelection(
        packages=packages,
        local=tuple(local),
        missing=tuple(missing),
        skill_names=frozenset(reference.name for reference in references),
    )


# ── Symlink installation ──────────────────────────────────────────────


def _real_target(link: Path) -> Path:
    """Resolve a symlink even when it dangles, so removal stays possible."""
    return Path(os.path.realpath(link))


def source_roots(config: SkillsConfig) -> tuple[Path, ...]:
    """Every directory a coordinator-installed symlink may point into."""
    return (
        ROOT.resolve(strict=False),
        *(source_root(source) for source in config.sources.values()),
    )


def _is_managed(link: Path, roots: tuple[Path, ...]) -> bool:
    if not link.is_symlink():
        return False
    target = _real_target(link)
    return any(root == target or root in target.parents for root in roots)


def managed_links(roots: tuple[Path, ...]) -> dict[str, Path]:
    """Coordinator-installed store entries, keyed by skill name."""
    if not AGENTS_SKILLS_DIR.is_dir():
        return {}
    return {
        entry.name: _real_target(entry)
        for entry in sorted(AGENTS_SKILLS_DIR.iterdir())
        if _is_managed(entry, roots)
    }


def npx_store_names() -> frozenset[str]:
    """Store entries npx owns: real directories, never symlinks."""
    if not AGENTS_SKILLS_DIR.is_dir():
        return frozenset()
    return frozenset(
        entry.name
        for entry in AGENTS_SKILLS_DIR.iterdir()
        if entry.is_dir() and not entry.is_symlink()
    )


def _report(planned: str, done: str, message: str, *, dry_run: bool) -> None:
    tag = f"would {planned}" if dry_run else done
    print(f"  {tag:14s} {message}")


def _link(link: Path, target: str | Path, *, dry_run: bool) -> None:
    if dry_run:
        return
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target)


def _unlink(link: Path, *, dry_run: bool) -> None:
    if not dry_run:
        link.unlink()


def _claude_link_is_managed(name: str) -> bool:
    link = CLAUDE_SKILLS_DIR / name
    return link.is_symlink() and link.readlink() == Path(f"{CLAUDE_LINK_PREFIX}/{name}")


def _ensure_claude_link(name: str, *, dry_run: bool) -> None:
    link = CLAUDE_SKILLS_DIR / name
    if _claude_link_is_managed(name):
        return
    if link.is_symlink() or link.exists():
        print(f"  CONFLICT       {name} (unmanaged entry in {CLAUDE_SKILLS_DIR})")
        return
    _report("link", "linked", f"{name} ({CLAUDE_SKILLS_DIR})", dry_run=dry_run)
    _link(link, f"{CLAUDE_LINK_PREFIX}/{name}", dry_run=dry_run)


def _display_path(directory: Path) -> str:
    """Show a source path relative to the repository when it lives inside it."""
    repository = ROOT.resolve(strict=False)
    try:
        return str(directory.relative_to(repository))
    except ValueError:
        return str(directory)


def install_local_skill(
    skill: LocalSkill,
    roots: tuple[Path, ...],
    *,
    dry_run: bool,
    replacing: frozenset[str] = frozenset(),
) -> None:
    """Point the shared store and Claude Code at one working-copy directory.

    ``replacing`` names store entries the caller has already removed. A dry run
    performs no removal, so without it every kind flip would report a conflict
    against an entry that a real run would have deleted first.
    """
    store = AGENTS_SKILLS_DIR / skill.name
    freed = skill.name in replacing
    if store.is_symlink() and not freed:
        if _real_target(store) == skill.directory:
            _ensure_claude_link(skill.name, dry_run=dry_run)
            return
        if not _is_managed(store, roots):
            print(f"  CONFLICT       {skill.name} (foreign symlink, skipping)")
            return
        _report("relink", "relinked", skill.name, dry_run=dry_run)
        _unlink(store, dry_run=dry_run)
    elif store.exists() and not freed:
        print(f"  CONFLICT       {skill.name} (npx-installed, skipping)")
        return
    else:
        target = _display_path(skill.directory)
        _report("link", "linked", f"{skill.name} -> {target}", dry_run=dry_run)
    _link(store, skill.directory, dry_run=dry_run)
    _ensure_claude_link(skill.name, dry_run=dry_run)


def remove_local_skill(name: str, roots: tuple[Path, ...], *, dry_run: bool) -> None:
    """Drop the agent link first so the store link stays identifiable."""
    if _claude_link_is_managed(name):
        _unlink(CLAUDE_SKILLS_DIR / name, dry_run=dry_run)
    store = AGENTS_SKILLS_DIR / name
    if _is_managed(store, roots):
        _report("unlink", "unlinked", name, dry_run=dry_run)
        _unlink(store, dry_run=dry_run)


def _remove_local_skills(
    names: frozenset[str], roots: tuple[Path, ...], *, dry_run: bool
) -> None:
    for name in sorted(names):
        remove_local_skill(name, roots, dry_run=dry_run)


def _restore_local_links(links: dict[str, Path]) -> None:
    """Restore removed local links after an npx installation fails."""
    for name, target in links.items():
        store = AGENTS_SKILLS_DIR / name
        if store.is_symlink() or store.exists():
            _ensure_claude_link(name, dry_run=False)
            continue
        _report(
            "restore",
            "restored",
            f"{name} -> {_display_path(target)}",
            dry_run=False,
        )
        _link(store, target, dry_run=False)
        _ensure_claude_link(name, dry_run=False)


# ── Source checkouts ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SourceStatus:
    package: str
    path: Path
    present: bool
    branch: str
    head: str
    behind: str


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def source_status(package: str, source: Source) -> SourceStatus:
    root = source_root(source)
    if not root.is_dir():
        return SourceStatus(package, root, False, "", "", "")
    return SourceStatus(
        package=package,
        path=root,
        present=True,
        branch=_git(root, "rev-parse", "--abbrev-ref", "HEAD") or "unknown",
        head=_git(root, "rev-parse", "--short", "HEAD") or "unknown",
        behind=_git(root, "rev-list", "--count", "HEAD..@{upstream}") or "?",
    )


def print_source_status(config: SkillsConfig) -> None:
    for package, source in config.sources.items():
        status = source_status(package, source)
        if not status.present:
            print(f"  {package:38s} MISSING CHECKOUT {source.path}")
            continue
        print(
            f"  {package:38s} {source.path}  "
            f"[{status.branch} {status.head}, {status.behind} behind upstream]"
        )


# ── Command execution ─────────────────────────────────────────────────


def _show_command(command: list[str]) -> str:
    return " ".join(command)


def _run_npx(
    command: list[str], *, dry_run: bool
) -> subprocess.CompletedProcess[str] | None:
    if dry_run:
        print(f"  would run  {_show_command(command)}")
        return None
    return subprocess.run(command, check=True, text=True)


def _remove_npx_skills(skill_names: frozenset[str], *, dry_run: bool) -> None:
    if not skill_names:
        return
    _run_npx(
        npx_command("remove", *sorted(skill_names), "--global", "--yes"),
        dry_run=dry_run,
    )


def _switch(profile: str, *, dry_run: bool) -> None:
    config = load_config()
    selection = resolve_profile(profile, config)
    roots = source_roots(config)
    local_names = frozenset(skill.name for skill in selection.local)
    npx_names = frozenset(
        name for package in selection.packages for name in package.skills
    )

    # A name moving from a checkout to npx must free the store path before npx
    # writes there. Preserve its target so a failed fetch can restore the active set.
    current_local_links = managed_links(roots)
    flipped_to_npx = {
        name: target
        for name, target in current_local_links.items()
        if name in npx_names
    }
    _remove_local_skills(frozenset(flipped_to_npx), roots, dry_run=dry_run)

    # Every fallible fetch runs before anything that a fetch would be needed to
    # undo, so a failed source leaves the active set intact.
    try:
        for package in selection.packages:
            _run_npx(package.add_command(), dry_run=dry_run)
    except BaseException:
        if not dry_run:
            _restore_local_links(flipped_to_npx)
        raise

    # Only now discard npx directories for names that became local: until the
    # symlink replaces them they are the only copy, and restoring one costs a fetch.
    flipped_to_local = local_names & npx_store_names()
    _remove_npx_skills(flipped_to_local, dry_run=dry_run)
    for skill in selection.local:
        install_local_skill(skill, roots, dry_run=dry_run, replacing=flipped_to_local)
    for name in selection.missing:
        print(f"  MISSING        {name} (not in its source checkout)")

    dropped = all_skill_names(config) - selection.skill_names
    _remove_npx_skills(dropped & npx_skill_names(config), dry_run=dry_run)
    _remove_local_skills(dropped & local_skill_names(config), roots, dry_run=dry_run)
    print(f"  active profile: {profile}")
    if selection.missing:
        raise SystemExit(
            f"{len(selection.missing)} configured skill(s) absent from their checkout"
        )


@app.command
def switch(*, profile: str = "full", dry_run: bool = False) -> None:
    """Install and activate exactly one configured skill profile."""
    _switch(profile, dry_run=dry_run)


@app.command
def install(*, profile: str = "full", dry_run: bool = False) -> None:
    """Install a profile (compatibility alias for switch)."""
    _switch(profile, dry_run=dry_run)


@app.command
def clone(*, dry_run: bool = False) -> None:
    """Clone missing source checkouts declared with a git_url."""
    for package, source in load_config().sources.items():
        root = source_root(source)
        if root.is_dir():
            print(f"  exists         {package}  ({source.path})")
            continue
        if source.git_url is None:
            print(f"  NO-URL         {package}  ({source.path})")
            continue
        _report("clone", "cloned", f"{package} -> {source.path}", dry_run=dry_run)
        if not dry_run:
            subprocess.run(["git", "clone", source.git_url, str(root)], check=True)


@app.command
def update(*, dry_run: bool = False) -> None:
    """Update npx skills and fast-forward every source checkout."""
    _run_npx(npx_command("update", "--global", "--yes"), dry_run=dry_run)
    for package, source in load_config().sources.items():
        root = source_root(source)
        if source.git_url is None or not root.is_dir():
            continue
        _report("pull", "pulling", package, dry_run=dry_run)
        if dry_run:
            continue
        result = subprocess.run(
            ["git", "-C", str(root), "pull", "--ff-only"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            print(f"  WARNING: pull failed for {package} (check it manually)")
        else:
            print(f"  {'pulled':14s} {package}")


@app.command
def clean(*, dry_run: bool = False) -> None:
    """Remove configured npx skills and every coordinator-installed symlink."""
    config = load_config()
    roots = source_roots(config)
    _remove_npx_skills(npx_skill_names(config), dry_run=dry_run)
    _remove_local_skills(frozenset(managed_links(roots)), roots, dry_run=dry_run)


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
    """List installed skills by kind and report the matching profile."""
    config = load_config()
    links = managed_links(source_roots(config))
    print("Sources:")
    print_source_status(config)
    print()
    print("Installed skills:")
    npx_records = installed_skills()
    for record in npx_records:
        name = str(record["name"])
        if name in links:
            continue  # a coordinator symlink, reported below with its target
        agent_values = record.get("agents", [])
        agents = (
            ", ".join(str(agent) for agent in agent_values)
            if isinstance(agent_values, list)
            else ""
        )
        print(f"  {name:45s} npx    {agents}")
    for name, target in links.items():
        print(f"  {name:45s} local  {_display_path(target)}")
    npx_installed = {str(record["name"]) for record in npx_records}
    active = (npx_installed | set(links)) & all_skill_names(config)
    matches = [
        name
        for name in config.profiles
        if resolve_profile(name, config).skill_names == active
    ]
    print()
    print(f"  matching profile: {', '.join(matches) if matches else 'none'}")


def read_coordinator(config: SkillsConfig) -> skill_bookkeeping.Coordinator:
    """Collect the configured inventory and the live install state for the scan."""
    profiles: dict[str, set[str]] = {}
    packages: dict[str, str] = {}
    for profile_name in config.profiles:
        for reference in profile_skill_references(profile_name, config):
            profiles.setdefault(reference.name, set()).add(profile_name)
            packages[reference.name] = reference.package

    owned: list[Path] = []
    checkouts: list[Path] = []
    for package, source in config.sources.items():
        (owned if source.owned else checkouts).append(source_root(source))
        packages.setdefault(package, package)

    installed: dict[str, str] = {}
    targets: dict[str, Path] = {}
    if AGENTS_SKILLS_DIR.is_dir():
        for entry in AGENTS_SKILLS_DIR.iterdir():
            if entry.is_symlink():
                installed[entry.name] = "symlink"
                targets[entry.name] = entry.resolve()
            elif entry.is_dir():
                installed[entry.name] = "npx-copy"
                targets[entry.name] = entry
    claude = (
        frozenset(entry.name for entry in CLAUDE_SKILLS_DIR.iterdir())
        if CLAUDE_SKILLS_DIR.is_dir()
        else frozenset()
    )
    return skill_bookkeeping.Coordinator(
        profiles={name: frozenset(values) for name, values in profiles.items()},
        packages=packages,
        owned_roots=tuple(owned),
        checkout_roots=tuple(checkouts),
        installed=installed,
        install_targets=targets,
        claude_links=claude,
        store=AGENTS_SKILLS_DIR,
    )


@app.command
def bookkeeping(
    root: Path = SCAN_ROOT,
    *,
    out: Path = BOOKKEEPING_OUT,
    html: bool = True,
) -> None:
    """Inventory every SKILL.md under ROOT and report how each one is held.

    Writes a CSV to filter, a Markdown report grouped by verdict, and an HTML
    rendering of that Markdown. Reads only; installs and moves nothing.

    Args:
        root: Folder to scan. A symlinked directory is recorded, not descended into.
        out: Output path without a suffix; .csv, .md and .html are added.
        html: Render the Markdown report to HTML. Needs the markdown package.
    """
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"not a directory: {root}")
    out = out.expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    skill_bookkeeping.run(root, out, read_coordinator(load_config()), html=html)


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
            f"includes={includes}"
        )


def _installed_hashes() -> dict[str, str]:
    if not NPX_LOCK.exists():
        return {}
    lock = json.loads(NPX_LOCK.read_text())
    return {
        name: str(record.get("skillFolderHash", ""))
        for name, record in lock.get("skills", {}).items()
    }


def _reviewed_sha(name: str) -> str:
    slug = f"skill_{name.replace('-', '_')}"
    knowledge = KAIROS_KNOW_DIR / slug / f"{slug}.md"
    if not knowledge.exists():
        return ""
    for line in knowledge.read_text().splitlines():
        if line.startswith("last_reviewed_sha:"):
            return line.split(":", 1)[1].strip()
    return ""


def _local_content_sha(directory: Path) -> str:
    """Last commit touching this skill, in whichever repository holds it."""
    top_level = _git(directory, "rev-parse", "--show-toplevel")
    if not top_level:
        return ""
    repository = Path(top_level)
    relative = directory.relative_to(repository)
    return _git(repository, "log", "-1", "--format=%H", "--", str(relative))


def _current_shas(config: SkillsConfig) -> dict[str, str]:
    current = dict(_installed_hashes())
    for name, target in managed_links(source_roots(config)).items():
        current[name] = _local_content_sha(target)
    return current


@app.command
def audit() -> None:
    """Report configured skills whose content changed since review."""
    config = load_config()
    current_by_name = _current_shas(config)
    ok = drift = unreviewed = missing = 0
    for name in sorted(all_skill_names(config)):
        current = current_by_name.get(name, "")
        if not current:
            print(f"  NOT-INSTALLED  {name}")
            missing += 1
            continue
        reviewed = _reviewed_sha(name)
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
