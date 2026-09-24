"""Terminal output shared by every command: action lines and tables."""

from __future__ import annotations

from collections.abc import Iterable

from rich.console import Console
from rich.table import Table

console = Console(highlight=False)


def report(planned: str, done: str, message: str, *, dry_run: bool) -> None:
    """Print one action, phrased as intended under a dry run and as done otherwise."""
    tag = f"would {planned}" if dry_run else done
    print(f"  {tag:14s} {message}")


def show_command(command: list[str]) -> str:
    return " ".join(command)


def print_table(title: str, columns: Iterable[str], rows: Iterable[Iterable[str]]) -> None:
    table = Table(title=title, title_justify="left", show_edge=False)
    for column in columns:
        table.add_column(column)
    for row in rows:
        table.add_row(*row)
    console.print(table)
