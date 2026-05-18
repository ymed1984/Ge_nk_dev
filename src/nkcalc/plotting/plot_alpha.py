"""Plot absorption coefficient versus wavelength."""

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/nkcalc-matplotlib")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from nkcalc.io.csv_io import ensure_required_columns


def plot_alpha(df: pd.DataFrame, path: str | Path | None = None) -> Figure:
    """Plot absorption coefficient in cm^-1 versus wavelength in microns.

    Parameters
    ----------
    df:
        Table with ``lambda_um`` and ``alpha_cm_inv`` columns.
    path:
        Optional output image path. If provided, the figure is saved without displaying GUI.

    Returns
    -------
    matplotlib.figure.Figure
        The generated figure.
    """
    ensure_required_columns(df, ["lambda_um", "alpha_cm_inv"])
    fig, ax = plt.subplots()
    ax.plot(df["lambda_um"], df["alpha_cm_inv"], color="tab:green", label="alpha")
    ax.set_xlabel("Wavelength (um)")
    ax.set_ylabel("alpha (cm^-1)")
    ax.legend(loc="best")
    fig.tight_layout()

    if path is not None:
        fig.savefig(path)
    return fig
