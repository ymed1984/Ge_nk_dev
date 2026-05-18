"""Export helpers for Lumerical sampled-data material files."""

from pathlib import Path

import numpy as np
import pandas as pd

from nkcalc.io.csv_io import ensure_required_columns

_LUMERICAL_COLUMNS = ["lambda_um", "n", "k"]


def export_lumerical_nk_txt(
    df: pd.DataFrame,
    path: str | Path,
    wavelength_unit: str = "um",
    header: bool = False,
    allow_negative_k: bool = False,
) -> None:
    """Write wavelength, n, k columns for Lumerical Sampled Data Material import.

    Parameters
    ----------
    df:
        Input table containing ``lambda_um``, ``n``, and ``k`` columns. ``lambda_um`` is
        always interpreted as wavelength in microns.
    path:
        Output text file path.
    wavelength_unit:
        Output wavelength unit. Must be ``"um"`` or ``"nm"``.
    header:
        If true, write a header line ``wavelength n k``. The default is no header.
    allow_negative_k:
        If false, reject negative extinction coefficients. Passive materials should use
        ``k >= 0``.

    Raises
    ------
    ValueError
        If required columns are missing, values are not finite, ``wavelength_unit`` is
        unsupported, or negative ``k`` is present without explicit permission.
    """
    ensure_required_columns(df, _LUMERICAL_COLUMNS)

    if wavelength_unit not in {"um", "nm"}:
        raise ValueError('wavelength_unit must be "um" or "nm"')

    lambda_um = np.asarray(df["lambda_um"], dtype=float)
    n = np.asarray(df["n"], dtype=float)
    k = np.asarray(df["k"], dtype=float)

    values = np.column_stack([lambda_um, n, k])
    if not np.all(np.isfinite(values)):
        raise ValueError("Lumerical export requires finite lambda_um, n, and k values")

    if not allow_negative_k and np.any(k < 0.0):
        raise ValueError("Lumerical export rejected negative k values")

    wavelength = lambda_um if wavelength_unit == "um" else lambda_um * 1000.0
    output = np.column_stack([wavelength, n, k])
    header_text = "wavelength n k" if header else ""
    np.savetxt(path, output, fmt="%.12g", delimiter="\t", header=header_text, comments="")
