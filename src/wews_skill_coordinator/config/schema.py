"""The skills.toml model: sources, profiles, and the skill references between them.

A source with a ``path`` is a working copy whose skills are symlinked; a source
without one is installed with the pinned npx CLI.

A base profile lists skills under the short name of the source that provides
them, and every skill has exactly one base profile. A composition lists base
profiles and nothing else, so a profile's skills are never more than one
lookup away.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, model_validator

PROFILE_FIELDS = frozenset({"description", "includes"})


class PluginSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    names: list[str]


class LocalSource(BaseModel):
    """A package installed from a working copy as symlinks.

    ``owned`` marks skills this repository authors; the bookkeeping report treats
    that checkout as the authoritative copy.
    """

    model_config = ConfigDict(extra="forbid")

    repo: str
    path: str
    owned: bool = False
    git_url: str | None = None


class NpxSource(BaseModel):
    """A package installed with the pinned npx skills CLI."""

    model_config = ConfigDict(extra="forbid")

    repo: str
    full_depth: bool = False


class BaseProfile(BaseModel):
    """Concrete skills, listed under the name of the source that provides them."""

    model_config = ConfigDict(extra="forbid")

    description: str
    skills: dict[str, list[str]] = Field(min_length=1)

    def references(self) -> list[SkillReference]:
        return [
            SkillReference(source_name, selector)
            for source_name, selectors in self.skills.items()
            for selector in selectors
        ]


class Composition(BaseModel):
    """Base profiles installed together; ``["*"]`` means every base profile."""

    model_config = ConfigDict(extra="forbid")

    description: str
    includes: list[str] = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class SkillReference:
    """One skill as a profile names it: a source name plus that source's selector.

    An npx selector is the skill name; a local selector is ``<category>/<name>``.
    """

    source: str
    selector: str

    @property
    def name(self) -> str:
        return PurePosixPath(self.selector).name

    @property
    def identifier(self) -> str:
        return f"{self.source}:{self.selector}"

    @property
    def source_path(self) -> PurePosixPath:
        """Where a local skill lives under its source root."""
        category, name = self.selector.split("/")
        return PurePosixPath(category, "skills", name)


class SkillsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: str
    plugins: dict[str, PluginSource] = Field(default_factory=dict)
    sources: dict[str, LocalSource | NpxSource] = Field(default_factory=dict)
    profiles: dict[str, BaseProfile | Composition] = Field(default_factory=dict)

    @property
    def local_sources(self) -> dict[str, LocalSource]:
        return {
            name: source
            for name, source in self.sources.items()
            if isinstance(source, LocalSource)
        }

    @property
    def npx_sources(self) -> dict[str, NpxSource]:
        return {
            name: source
            for name, source in self.sources.items()
            if isinstance(source, NpxSource)
        }

    @property
    def base_profiles(self) -> dict[str, BaseProfile]:
        return {
            name: profile
            for name, profile in self.profiles.items()
            if isinstance(profile, BaseProfile)
        }

    @property
    def compositions(self) -> dict[str, Composition]:
        return {
            name: profile
            for name, profile in self.profiles.items()
            if isinstance(profile, Composition)
        }

    def references(self) -> tuple[SkillReference, ...]:
        """Every configured skill once, in base-profile order."""
        return tuple(
            reference
            for profile in self.base_profiles.values()
            for reference in profile.references()
        )

    def included_profiles(self, composition_name: str) -> tuple[str, ...]:
        includes = self.compositions[composition_name].includes
        if includes == ["*"]:
            return tuple(self.base_profiles)
        return tuple(includes)

    def profile_references(self, profile_name: str) -> tuple[SkillReference, ...]:
        """A profile's skills: its own, or those of the base profiles it includes."""
        base_profiles = self.base_profiles
        if profile_name in base_profiles:
            return tuple(base_profiles[profile_name].references())
        return tuple(
            reference
            for included in self.included_profiles(profile_name)
            for reference in base_profiles[included].references()
        )

    def skill_names(self) -> frozenset[str]:
        return frozenset(reference.name for reference in self.references())

    def local_skill_names(self) -> frozenset[str]:
        local = self.local_sources
        return frozenset(
            reference.name
            for reference in self.references()
            if reference.source in local
        )

    def npx_skill_names(self) -> frozenset[str]:
        return self.skill_names() - self.local_skill_names()

    @model_validator(mode="after")
    def validate_names(self) -> SkillsConfig:
        if self.active not in self.profiles:
            raise ValueError(f"active profile {self.active!r} is not configured")
        reserved = PROFILE_FIELDS & set(self.sources)
        if reserved:
            raise ValueError(f"source names clash with profile fields: {reserved}")
        for profile_name, profile in self.base_profiles.items():
            for source_name, selectors in profile.skills.items():
                self._validate_source_list(profile_name, source_name, selectors)
        self._validate_one_home_per_skill()
        for composition_name, composition in self.compositions.items():
            self._validate_includes(composition_name, composition.includes)
        full = self.profiles.get("full")
        if full is not None and (not isinstance(full, Composition) or full.includes != ["*"]):
            raise ValueError("profile 'full' must be a composition with includes = ['*']")
        self._validate_sources_are_used()
        return self

    def _validate_source_list(
        self, profile_name: str, source_name: str, selectors: list[str]
    ) -> None:
        if source_name not in self.sources:
            raise ValueError(
                f"profile {profile_name!r} lists skills of unknown source {source_name!r}"
            )
        _reject_duplicates(
            f"skills of {source_name!r} in profile {profile_name!r}", selectors
        )
        source = self.sources[source_name]
        for selector in selectors:
            reference = SkillReference(source_name, selector)
            if isinstance(source, LocalSource):
                _validate_local_selector(reference)
            else:
                _validate_npx_selector(reference)

    def _validate_one_home_per_skill(self) -> None:
        home_by_name: dict[str, tuple[str, str]] = {}
        for profile_name, profile in self.base_profiles.items():
            for reference in profile.references():
                previous = home_by_name.setdefault(
                    reference.name, (profile_name, reference.identifier)
                )
                if previous[1] != reference.identifier:
                    raise ValueError(
                        f"skill {reference.name!r} is referenced from both "
                        f"{previous[1]!r} and {reference.identifier!r}"
                    )
                if previous[0] != profile_name:
                    raise ValueError(
                        f"skill {reference.name!r} is in base profiles "
                        f"{previous[0]!r} and {profile_name!r}; give it one home"
                    )

    def _validate_includes(self, composition_name: str, includes: list[str]) -> None:
        _reject_duplicates(f"included profiles in {composition_name!r}", includes)
        if "*" in includes and includes != ["*"]:
            raise ValueError(f"profile {composition_name!r} must use '*' alone for includes")
        if includes == ["*"] and composition_name != "full":
            raise ValueError("only the 'full' profile may include '*'")
        if includes == ["*"]:
            return
        unknown = set(includes) - set(self.profiles)
        if unknown:
            raise ValueError(
                f"profile {composition_name!r} includes unknown profiles: {unknown}"
            )
        nested = set(includes) & set(self.compositions)
        if nested:
            raise ValueError(
                f"composition {composition_name!r} includes compositions {nested}; "
                "include their base profiles instead"
            )

    def _validate_sources_are_used(self) -> None:
        used = {reference.source for reference in self.references()}
        unused = set(self.sources) - used
        if unused:
            raise ValueError(f"sources no profile uses: {unused}")


def _validate_npx_selector(reference: SkillReference) -> None:
    selector = reference.selector
    if (
        not selector
        or "/" in selector
        or "\\" in selector
        or any(character.isspace() for character in selector)
    ):
        raise ValueError(
            f"invalid npx skill {reference.identifier!r}; expected a skill name"
        )


def _validate_local_selector(reference: SkillReference) -> None:
    selector = reference.selector
    parts = selector.split("/")
    if (
        len(parts) != 2
        or any(part in {"", ".", ".."} for part in parts)
        or "\\" in selector
        or any(character.isspace() for character in selector)
    ):
        raise ValueError(
            f"invalid local skill {reference.identifier!r}; expected <category>/<name>"
        )


def _reject_duplicates(kind: str, names: list[str]) -> None:
    duplicates = {name for name in names if names.count(name) > 1}
    if duplicates:
        raise ValueError(f"duplicate {kind}: {duplicates}")
