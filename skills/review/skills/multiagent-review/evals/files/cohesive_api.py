"""Fixture: cohesive guards and optionality that should not be over-flagged."""

import pandas as pd


def clip_column(
    frame: pd.DataFrame,
    *,
    column: str,
    lower: float | None = None,
) -> pd.Series:
    """Return one numeric column, optionally clipped at a lower bound."""
    if column not in frame.columns:
        raise KeyError(column)
    values = frame[column]
    if not pd.api.types.is_numeric_dtype(values):
        raise TypeError(f"{column!r} is not numeric")
    if lower is not None:
        values = values.clip(lower=lower)
    return values
