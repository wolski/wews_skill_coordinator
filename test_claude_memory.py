"""Tests for the Claude memory store inventory."""

from __future__ import annotations

import csv
import datetime as dt
from dataclasses import fields
from pathlib import Path

from claude_memory import (
    MemoryRow,
    Store,
    annotate,
    find_relocation,
    find_stores,
    index_directories,
    prune,
    read_metadata,
    render_markdown,
    resolve_slug,
    write_csv,
)

TODAY = dt.date(2026, 8, 28)

FACT = """\
---
name: {name}
description: {description}
metadata:
  type: {kind}
---

Body. {links}
"""


def slug_of(path: Path) -> str:
    return str(path).replace("/", "-").replace("_", "-").replace(".", "-")


def make_store(
    root: Path, slug: str, *, index: str | None = "", facts: dict[str, str] | None = None
) -> Path:
    directory = root / slug / "memory"
    directory.mkdir(parents=True)
    if index is not None:
        (directory / "MEMORY.md").write_text(index)
    for name, body in (facts or {}).items():
        (directory / f"{name}.md").write_text(body)
    return directory


def fact(name: str, kind: str = "project", links: str = "") -> str:
    return FACT.format(name=name, description=f"About {name}.", kind=kind, links=links)


class TestResolveSlug:
    def test_an_underscore_flattened_to_a_dash_is_recovered(
        self, tmp_path: Path
    ) -> None:
        target = tmp_path / "projects" / "wews_skill_coordinator"
        target.mkdir(parents=True)
        slug = "projects-wews-skill-coordinator"
        assert resolve_slug(slug, base=tmp_path) == target

    def test_a_nested_path_with_mixed_separators_is_recovered(
        self, tmp_path: Path
    ) -> None:
        target = tmp_path / "data_analysis" / "o41874_Frida"
        target.mkdir(parents=True)
        assert resolve_slug("data-analysis-o41874-Frida", base=tmp_path) == target

    def test_a_real_dash_in_a_directory_name_is_recovered(self, tmp_path: Path) -> None:
        target = tmp_path / "projects" / "ptm-pipeline"
        target.mkdir(parents=True)
        assert resolve_slug("projects-ptm-pipeline", base=tmp_path) == target

    def test_a_slug_naming_nothing_resolves_to_none(self, tmp_path: Path) -> None:
        (tmp_path / "projects").mkdir()
        assert resolve_slug("projects-absent", base=tmp_path) is None

    def test_a_prefix_match_is_not_accepted_as_the_whole_slug(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "projects" / "prolfqua_fml").mkdir(parents=True)
        assert resolve_slug("projects-prolfqua", base=tmp_path) is None

    def test_an_absurdly_long_slug_is_refused(self, tmp_path: Path) -> None:
        assert resolve_slug("-".join(["a"] * 40), base=tmp_path) is None


class TestRelocation:
    def test_a_moved_project_is_found_by_its_leaf_name(self, tmp_path: Path) -> None:
        moved = tmp_path / "projects" / "gstore" / "diann_runner"
        moved.mkdir(parents=True)
        names = index_directories(tmp_path)
        assert find_relocation("projects-diann-runner", names) == [moved]

    def test_a_dot_directory_is_never_offered_as_a_relocation(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / ".gemini" / "tmp" / "qg-dump").mkdir(parents=True)
        names = index_directories(tmp_path)
        assert find_relocation("projects-qg-dump", names) == []

    def test_a_short_single_token_tail_is_too_generic_to_match(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "src").mkdir()
        names = index_directories(tmp_path)
        assert find_relocation("projects-src", names) == []

    def test_the_longest_matching_tail_wins(self, tmp_path: Path) -> None:
        (tmp_path / "Frida").mkdir()
        specific = tmp_path / "o41874_Frida_Nilsson"
        specific.mkdir()
        names = index_directories(tmp_path)
        assert find_relocation("data-o41874-Frida-Nilsson", names) == [specific]


class TestMetadata:
    def test_name_description_and_type_are_read(self) -> None:
        assert read_metadata(fact("alpha", "feedback")) == (
            "alpha",
            "About alpha.",
            "feedback",
        )

    def test_a_file_without_frontmatter_yields_empty_fields(self) -> None:
        assert read_metadata("plain text\n") == ("", "", "")


class TestFindStores:
    def test_an_index_and_its_facts_are_collected(self, tmp_path: Path) -> None:
        target = tmp_path / "live"
        target.mkdir()
        make_store(
            tmp_path / "store",
            slug_of(target).lstrip("-"),
            index="- [A](a.md)\n",
            facts={"a": fact("a")},
        )
        stores = find_stores(tmp_path / "store", search_root=tmp_path)
        assert len(stores) == 1
        assert stores[0].index is not None
        assert [path.stem for path in stores[0].facts] == ["a"]

    def test_an_index_entry_with_no_file_is_recorded_as_dangling(
        self, tmp_path: Path
    ) -> None:
        make_store(tmp_path / "store", "absent-xyz", index="- [Gone](gone.md)\n")
        stores = find_stores(tmp_path / "store", search_root=tmp_path)
        assert stores[0].dangling_index_entries == ["gone.md"]


class TestAnnotate:
    def _store(self, tmp_path: Path, **kwargs: object) -> list[Store]:
        make_store(tmp_path / "store", "absent-xyz", **kwargs)  # type: ignore[arg-type]
        return find_stores(tmp_path / "store", search_root=tmp_path)

    def test_a_store_nothing_claims_is_removable(self, tmp_path: Path) -> None:
        stores = self._store(tmp_path, index="", facts={"a": fact("a")})
        rows = annotate(stores, TODAY, 90)
        assert stores[0].removable is True
        assert {row.verdict for row in rows} == {"PROJECT-GONE"}

    def test_a_moved_project_is_kept_not_marked_removable(self, tmp_path: Path) -> None:
        (tmp_path / "elsewhere" / "absent-xyz").mkdir(parents=True)
        stores = self._store(tmp_path, index="", facts={"a": fact("a")})
        rows = annotate(stores, TODAY, 90)
        assert stores[0].removable is False
        assert {row.verdict for row in rows} == {"PROJECT-MOVED"}

    def test_a_fact_missing_from_the_index_is_flagged(self, tmp_path: Path) -> None:
        target = tmp_path / "live"
        target.mkdir()
        make_store(
            tmp_path / "store",
            slug_of(target).lstrip("-"),
            index="- [A](a.md)\n",
            facts={"a": fact("a"), "b": fact("b")},
        )
        stores = find_stores(tmp_path / "store", search_root=tmp_path)
        rows = {row.name: row for row in annotate(stores, TODAY, 90)}
        assert rows["a"].indexed == "yes"
        assert rows["b"].indexed == "no"
        assert rows["b"].verdict == "UNINDEXED-FACT"

    def test_a_wiki_link_to_a_missing_fact_is_dangling(self, tmp_path: Path) -> None:
        target = tmp_path / "live"
        target.mkdir()
        make_store(
            tmp_path / "store",
            slug_of(target).lstrip("-"),
            index="- [A](a.md)\n",
            facts={"a": fact("a", links="[[nowhere]]")},
        )
        stores = find_stores(tmp_path / "store", search_root=tmp_path)
        row = next(row for row in annotate(stores, TODAY, 90) if row.role == "fact")
        assert row.dangling_links == "nowhere"
        assert row.verdict == "DANGLING-LINKS"

    def test_an_index_with_no_facts_is_flagged(self, tmp_path: Path) -> None:
        target = tmp_path / "live"
        target.mkdir()
        make_store(tmp_path / "store", slug_of(target).lstrip("-"), index="")
        stores = find_stores(tmp_path / "store", search_root=tmp_path)
        assert annotate(stores, TODAY, 90)[0].verdict == "INDEX-WITHOUT-FACTS"

    def test_an_old_file_is_stale_against_the_threshold(self, tmp_path: Path) -> None:
        target = tmp_path / "live"
        target.mkdir()
        make_store(
            tmp_path / "store",
            slug_of(target).lstrip("-"),
            index="- [A](a.md)\n",
            facts={"a": fact("a")},
        )
        stores = find_stores(tmp_path / "store", search_root=tmp_path)
        far_future = TODAY + dt.timedelta(days=400)
        assert {row.verdict for row in annotate(stores, far_future, 90)} == {"STALE"}


class TestPrune:
    def _two_stores(self, tmp_path: Path) -> list[Store]:
        target = tmp_path / "live"
        target.mkdir()
        make_store(tmp_path / "store", slug_of(target).lstrip("-"), facts={"a": fact("a")})
        make_store(tmp_path / "store", "absent-xyz", facts={"b": fact("b")})
        return find_stores(tmp_path / "store", search_root=tmp_path)

    def test_a_dry_run_deletes_nothing(self, tmp_path: Path) -> None:
        stores = self._two_stores(tmp_path)
        removed, reclaimed = prune(stores, dry_run=True)
        assert removed == 1
        assert reclaimed > 0
        assert all(store.directory.is_dir() for store in stores)

    def test_only_the_unclaimed_store_is_removed(self, tmp_path: Path) -> None:
        stores = self._two_stores(tmp_path)
        prune(stores, dry_run=False)
        surviving = [store for store in stores if store.directory.is_dir()]
        assert [store.removable for store in surviving] == [False]

    def test_a_moved_project_survives_a_prune(self, tmp_path: Path) -> None:
        (tmp_path / "elsewhere" / "absent-xyz").mkdir(parents=True)
        make_store(tmp_path / "store", "absent-xyz", facts={"b": fact("b")})
        stores = find_stores(tmp_path / "store", search_root=tmp_path)
        removed, _ = prune(stores, dry_run=False)
        assert removed == 0
        assert stores[0].directory.is_dir()


class TestOutputs:
    def test_the_csv_header_is_the_row_field_order(self, tmp_path: Path) -> None:
        destination = tmp_path / "out.csv"
        write_csv([MemoryRow(slug="s", verdict="ACTIVE")], destination)
        with destination.open() as handle:
            reader = csv.reader(handle)
            header = next(reader)
            body = next(reader)
        assert header == [item.name for item in fields(MemoryRow)]
        assert body[header.index("slug")] == "s"

    def test_an_empty_store_root_still_renders(self) -> None:
        text = render_markdown([], [], Path("/root"), "2026-08-28")
        assert "Stores: **0**" in text
        assert "None — every slug resolved" in text

    def test_a_pipe_in_a_value_does_not_break_the_table(self, tmp_path: Path) -> None:
        target = tmp_path / "live"
        target.mkdir()
        make_store(
            tmp_path / "store",
            slug_of(target).lstrip("-"),
            index="- [A](a.md)\n",
            facts={"a": fact("a|b")},
        )
        stores = find_stores(tmp_path / "store", search_root=tmp_path)
        text = render_markdown(annotate(stores, TODAY, 90), stores, tmp_path, "now")
        assert "a\\|b" in text
