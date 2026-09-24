"""Tests for the SKILL.md bookkeeping scan."""

from __future__ import annotations

import csv
from dataclasses import fields
from pathlib import Path

import pytest

from wews_skill_coordinator.reports.bookkeeping import (
    Coordinator,
    Discovery,
    Row,
    _compare,
    annotate,
    discover,
    kairos_projections,
    locate,
    read_frontmatter,
    render_html,
    render_markdown,
    write_csv,
)

SKILL_TEXT = """\
---
name: {name}
description: {description}
---

# {name}

Body line.
"""


def write_skill(directory: Path, name: str, description: str = "Does a thing.") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "SKILL.md"
    path.write_text(SKILL_TEXT.format(name=name, description=description))
    return path


def coordinator(
    owned: tuple[Path, ...] = (),
    checkouts: tuple[Path, ...] = (),
    profiles: dict[str, frozenset[str]] | None = None,
) -> Coordinator:
    return Coordinator(
        profiles=profiles or {},
        packages={},
        owned_roots=owned,
        checkout_roots=checkouts,
        installed={},
        install_targets={},
        claude_links=frozenset(),
        store=Path("/nonexistent-store"),
    )


class TestFrontmatter:
    def test_name_and_description_are_read(self) -> None:
        name, description = read_frontmatter(
            SKILL_TEXT.format(name="alpha", description="Does alpha.")
        )
        assert (name, description) == ("alpha", "Does alpha.")

    def test_a_file_without_frontmatter_yields_empty_fields(self) -> None:
        assert read_frontmatter("# alpha\n") == ("", "")

    def test_a_folded_description_is_collapsed_to_one_line(self) -> None:
        text = "---\nname: a\ndescription: >-\n  first\n  second\n---\n"
        assert read_frontmatter(text)[1] == "first second"

    def test_a_literal_description_is_collapsed_to_one_line(self) -> None:
        text = "---\nname: a\ndescription: |\n  first\n  second\n---\n"
        assert read_frontmatter(text)[1] == "first second"

    def test_a_block_description_stops_at_the_next_key(self) -> None:
        text = "---\ndescription: >-\n  wanted\nname: a\n---\n"
        assert read_frontmatter(text) == ("a", "wanted")

    def test_a_body_heading_named_description_is_not_read(self) -> None:
        text = "---\nname: a\n---\n\ndescription: not frontmatter\n"
        assert read_frontmatter(text) == ("a", "")


class TestDiscover:
    def test_a_plain_file_is_held_as_a_real_file(self, tmp_path: Path) -> None:
        write_skill(tmp_path / "project" / "skills" / "alpha", "alpha")
        found = discover(tmp_path).files
        assert [(item.held_as, item.path.name) for item in found] == [
            ("real-file", "SKILL.md")
        ]

    def test_a_symlinked_file_is_held_as_a_link_to_its_target(
        self, tmp_path: Path
    ) -> None:
        real = write_skill(tmp_path / "source" / "alpha", "alpha")
        link_dir = tmp_path / "project" / "skills" / "alpha"
        link_dir.mkdir(parents=True)
        (link_dir / "SKILL.md").symlink_to(real)

        held = {item.held_as: item for item in discover(tmp_path).files}
        assert set(held) == {"real-file", "symlinked-file"}
        assert held["symlinked-file"].real_path == real

    def test_a_symlinked_directory_is_expanded_once_as_an_alias(
        self, tmp_path: Path
    ) -> None:
        real = write_skill(tmp_path / "source" / "alpha", "alpha")
        (tmp_path / "project").mkdir()
        (tmp_path / "project" / "linked").symlink_to(tmp_path / "source")

        alias = [
            item for item in discover(tmp_path).files if item.held_as == "via-symlinked-dir"
        ]
        assert len(alias) == 1
        assert alias[0].real_path == real
        assert alias[0].link_target == str(tmp_path / "source")

    def test_a_link_to_the_home_directory_is_named_and_not_followed(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "home").symlink_to(Path.home())

        result = discover(tmp_path)
        assert result.files == []
        assert [reason for _, _, reason in result.skipped_links] == [
            "target is the home directory or filesystem root"
        ]

    def test_a_link_containing_the_scan_root_is_not_followed(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "root"
        write_skill(root / "alpha", "alpha")
        (root / "up").symlink_to(tmp_path)

        result = discover(root)
        assert [item.held_as for item in result.files] == ["real-file"]
        assert [reason for _, _, reason in result.skipped_links] == [
            "target contains the scan root"
        ]

    def test_git_directories_are_pruned(self, tmp_path: Path) -> None:
        write_skill(tmp_path / ".git" / "hooks" / "alpha", "alpha")
        assert discover(tmp_path).files == []


class TestLocate:
    def test_a_vendored_copy_is_recognised_by_its_install_path(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / ".venv" / "lib" / "site-packages" / "x" / "SKILL.md"
        kind, _ = locate(path, "x", "untracked", coordinator(), frozenset())
        assert kind == "vendored-dependency"

    def test_a_path_under_an_owned_root_is_owned_source(self, tmp_path: Path) -> None:
        owned = tmp_path / "skills"
        path = owned / "cat" / "skills" / "alpha" / "SKILL.md"
        kind, by = locate(path, "alpha", "tracked", coordinator(owned=(owned,)), frozenset())
        assert (kind, by) == ("coordinator-source-owned", "this repository")

    def test_a_path_under_a_checkout_root_is_upstream_source(
        self, tmp_path: Path
    ) -> None:
        checkout = tmp_path / "repos" / "upstream"
        path = checkout / "cat" / "skills" / "alpha" / "SKILL.md"
        kind, _ = locate(
            path, "alpha", "tracked", coordinator(checkouts=(checkout,)), frozenset()
        )
        assert kind == "coordinator-source-checkout"

    def test_a_store_copy_matching_a_skillset_is_a_kairos_projection(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / ".claude" / "skills" / "agent" / "SKILL.md"
        kind, by = locate(
            path, "agent", "untracked", coordinator(), frozenset({(tmp_path, "agent")})
        )
        assert (kind, by) == ("kairos-projected", "KairosChain plugin_projector")

    def test_an_untracked_store_copy_belongs_to_an_agent_tool(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / ".claude" / "skills" / "alpha" / "SKILL.md"
        kind, _ = locate(path, "alpha", "untracked", coordinator(), frozenset())
        assert kind == "agent-store"

    def test_a_committed_store_copy_is_project_source(self, tmp_path: Path) -> None:
        path = tmp_path / ".claude" / "skills" / "alpha" / "SKILL.md"
        kind, _ = locate(path, "alpha", "tracked", coordinator(), frozenset())
        assert kind == "project-local-claude"


class TestKairosProjections:
    def test_each_skillset_directory_is_paired_with_its_project(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "proj" / ".kairos" / "skillsets" / "agent").mkdir(parents=True)
        (tmp_path / "proj" / ".kairos" / "skillsets" / "other").mkdir()
        assert kairos_projections(tmp_path) == frozenset(
            {(tmp_path / "proj", "agent"), (tmp_path / "proj", "other")}
        )

    def test_a_project_without_skillsets_yields_nothing(self, tmp_path: Path) -> None:
        assert kairos_projections(tmp_path) == frozenset()


class TestCompare:
    def _rows(self, tmp_path: Path, *specs: tuple[str, str, str, str]) -> list[Row]:
        rows = []
        for name, location, digest, modified in specs:
            path = f"{name}-{digest}/SKILL.md"
            (tmp_path / f"{name}-{digest}").mkdir(parents=True, exist_ok=True)
            (tmp_path / path).write_text(digest)
            rows.append(
                Row(
                    skill_name=name,
                    held_as="real-file",
                    location_kind=location,
                    md5=digest,
                    modified=modified,
                    path=path,
                )
            )
        return rows

    def test_the_owned_copy_is_the_reference_even_when_older(
        self, tmp_path: Path
    ) -> None:
        rows = self._rows(
            tmp_path,
            ("alpha", "project-local-other", "bbb", "2026-08-01"),
            ("alpha", "coordinator-source-owned", "aaa", "2026-01-01"),
        )
        _compare(rows, tmp_path)
        assert rows[1].content_vs_reference == "reference"
        assert rows[0].reference_copy == rows[1].path
        assert rows[0].drift_direction == "this-copy-newer"

    def test_an_identical_copy_reports_no_diff(self, tmp_path: Path) -> None:
        rows = self._rows(
            tmp_path,
            ("alpha", "coordinator-source-owned", "aaa", "2026-01-01"),
            ("alpha", "project-local-other", "aaa", "2026-01-01"),
        )
        rows[1].path = rows[0].path
        _compare(rows, tmp_path)
        assert rows[1].content_vs_reference == "identical"
        assert rows[1].diff_lines == "0"

    def test_a_sole_copy_has_no_reference(self, tmp_path: Path) -> None:
        rows = self._rows(tmp_path, ("alpha", "project-local-other", "aaa", "2026-01-01"))
        _compare(rows, tmp_path)
        assert rows[0].copies_of_this_skill == 1
        assert rows[0].reference_copy == ""

    def test_a_renamed_skill_is_grouped_with_its_alias(self, tmp_path: Path) -> None:
        rows = self._rows(
            tmp_path,
            ("fgcz-quarto-report-template", "coordinator-source-checkout", "aaa", "2026-08-01"),
            ("fgcz-quarto-reports", "project-local-skills-dir", "bbb", "2026-01-01"),
        )
        _compare(rows, tmp_path)
        assert rows[1].reference_copy == rows[0].path

    def test_vendored_copies_never_join_a_comparison_group(
        self, tmp_path: Path
    ) -> None:
        rows = self._rows(
            tmp_path,
            ("alpha", "coordinator-source-owned", "aaa", "2026-01-01"),
            ("alpha", "vendored-dependency", "bbb", "2026-08-01"),
        )
        _compare(rows, tmp_path)
        assert rows[0].copies_of_this_skill == 1
        assert rows[1].reference_copy == ""


class TestAnnotate:
    def test_an_unreadable_file_is_reported_rather_than_counted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write_skill(tmp_path / "alpha", "alpha")
        discovery = discover(tmp_path)

        def refuse(*_args: object, **_kwargs: object) -> str:
            raise PermissionError("Operation not permitted")

        monkeypatch.setattr(Path, "read_text", refuse)
        rows = annotate(tmp_path, coordinator(), discovery)

        assert rows == []
        assert [error for _, error in discovery.unreadable] == [
            "Operation not permitted"
        ]

    def test_a_directory_name_stands_in_for_a_missing_frontmatter_name(
        self, tmp_path: Path
    ) -> None:
        directory = tmp_path / "skills" / "alpha"
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text("# no frontmatter\n")
        rows = annotate(tmp_path, coordinator(), discover(tmp_path))
        assert [row.skill_name for row in rows] == ["alpha"]

    def test_an_owned_skill_carries_its_profiles(self, tmp_path: Path) -> None:
        owned = tmp_path / "skills"
        write_skill(owned / "cat" / "skills" / "alpha", "alpha")
        view = coordinator(owned=(owned,), profiles={"alpha": frozenset({"python"})})
        rows = annotate(tmp_path, view, discover(tmp_path))
        assert rows[0].profiles == "python"
        assert rows[0].in_config == "yes"
        assert rows[0].status == "MANAGED-OWNED"


class TestOutputs:
    def test_the_csv_header_is_the_row_field_order(self, tmp_path: Path) -> None:
        destination = tmp_path / "out.csv"
        write_csv([Row(skill_name="alpha", status="MANAGED-OWNED")], destination)
        with destination.open() as handle:
            reader = csv.reader(handle)
            header = next(reader)
            body = next(reader)
        assert header == [item.name for item in fields(Row)]
        assert body[header.index("skill_name")] == "alpha"

    def test_a_pipe_in_a_value_does_not_break_the_markdown_table(self) -> None:
        row = Row(status="UNMANAGED-PROJECT-LOCAL", skill_name="a|b", held_as="real-file")
        text = render_markdown([row], Path("/root"), "now", Discovery())
        assert "a\\|b" in text

    def test_skipped_links_are_named_in_the_report(self) -> None:
        discovery = Discovery(skipped_links=[("config/home", "/home", "too broad")])
        text = render_markdown([], Path("/root"), "now", discovery)
        assert "Not covered by this scan" in text
        assert "config/home" in text

    def test_unreadable_files_are_named_in_the_report(self) -> None:
        discovery = Discovery(unreadable=[("a/SKILL.md", "denied")])
        text = render_markdown([], Path("/root"), "now", discovery)
        assert "a/SKILL.md" in text
        assert "denied" in text

    def test_the_store_section_is_omitted_when_the_store_is_absent(self) -> None:
        text = render_markdown([], Path("/root"), "now", Discovery(), None)
        assert "Installed store" not in text

    def test_the_store_section_names_symlinks_and_copies(self, tmp_path: Path) -> None:
        (tmp_path / "copied").mkdir()
        (tmp_path / "linked").symlink_to(tmp_path / "copied")
        text = render_markdown([], Path("/root"), "now", Discovery(), tmp_path)
        assert "| `linked` | symlink |" in text
        assert "| `copied` | npx copy |" in text

    def test_the_html_page_is_self_contained(self) -> None:
        html = render_html("# Title\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n", "Report")
        assert html.startswith("<!doctype html>")
        assert "<title>Report</title>" in html
        assert "<table>" in html
        assert "http://" not in html and "https://" not in html
