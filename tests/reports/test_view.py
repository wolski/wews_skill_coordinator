from __future__ import annotations

from pathlib import Path

from wews_skill_coordinator.config.load import load_config
from wews_skill_coordinator.reports.view import read_coordinator


def test_the_scan_view_carries_profiles_sources_and_the_store(configured: Path) -> None:
    view = read_coordinator(load_config())

    assert view.profiles["python-style"] == frozenset({"full", "python", "python-style"})
    assert view.packages["python-style"] == "owner/local"
    assert view.packages["clean-architecture"] == "owner/public"
    assert view.owned_roots == (configured / "skills",)
    assert view.checkout_roots == ()
    assert view.store == configured / "store"


def test_an_installed_symlink_is_reported_with_its_resolved_target(configured: Path) -> None:
    target = configured / "skills" / "engineering" / "skills" / "python-style"
    (configured / "store" / "python-style").symlink_to(target)
    (configured / "store" / "clean-architecture").mkdir()

    view = read_coordinator(load_config())

    assert view.installed == {"python-style": "symlink", "clean-architecture": "npx-copy"}
    assert view.install_targets["python-style"] == target.resolve()
