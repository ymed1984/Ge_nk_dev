"""CSV output helpers for nkcalc tables."""

from collections.abc import Iterable
from pathlib import Path

import pandas as pd


def ensure_required_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    """Validate that a DataFrame contains required columns.

    Parameters
    ----------
    df:
        Input table.
    columns:
        Required column names. Names are matched exactly.

    Raises
    ------
    ValueError
        If one or more required columns are missing.
    """
    missing = [column for column in columns if column not in df.columns]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"Missing required column(s): {missing_text}")


def export_table_csv(df: pd.DataFrame, path: str | Path) -> None:
    """Write a table to CSV with no index column.

    Parameters
    ----------
    df:
        Table to write.
    path:
        Output CSV path.
    """
    df.to_csv(path, index=False)
