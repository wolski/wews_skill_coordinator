"""Fixture: rules.json is authoritative for every APB-owned table."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ColumnRoles:
    protein_accessions: str | None = None


@dataclass(frozen=True)
class Rule:
    software: str
    column_roles: ColumnRoles | None = None


def resolve_protein_accessions(
    table: pd.DataFrame,
    rule: Rule | None,
    requested: str | None = None,
) -> str | None:
    """Resolve a protein-accession column for an APB-owned table."""
    if requested is not None:
        return requested
    if rule is not None and rule.column_roles is not None:
        declared = rule.column_roles.protein_accessions
        if declared is not None and declared in table.columns:
            return declared
    for candidate in ("Protein.Ids", "Proteins", "Accession", "protein_group"):
        if candidate in table.columns:
            return candidate
    return None
