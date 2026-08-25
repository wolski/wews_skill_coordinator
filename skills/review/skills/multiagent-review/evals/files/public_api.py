"""Fixture: a public API whose contract and configuration are underspecified."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FastaSource:
    path: str


@dataclass(frozen=True)
class FastaConfig:
    decoy_pattern: str | None = None
    contaminant_pattern: str | None = None


@dataclass(frozen=True)
class ResolvedFastaConfig:
    decoy_pattern: str
    contaminant_pattern: str


def validate_peptides_against_fasta(  # noqa: PLR0913
    obj: Any,
    fasta_sources: FastaSource | Iterable[FastaSource],
    *,
    sequence_field: str = "sequence",
    backend: str = "auto",
    fasta_config: FastaConfig | ResolvedFastaConfig | None = None,
    decoy_pattern: str | None = None,
    contaminant_pattern: str | None = None,
    leading_protein_field: str | None = None,
    protein_match_on: str | None = None,
    il_equivalent: bool = False,
    is_uniprot: bool = True,
    modality: str | None = None,
    store: bool = True,
) -> dict[str, Any]:
    """Validate one of several container shapes and optionally mutate it."""
    table = obj.mod[modality] if hasattr(obj, "mod") else obj
    sequences = table.var[sequence_field]
    result = {
        "count": len(sequences),
        "backend": backend,
        "sources": list(fasta_sources)
        if not isinstance(fasta_sources, FastaSource)
        else [fasta_sources],
    }
    if store:
        obj.uns["fasta_validation"] = result
    return result
