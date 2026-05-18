"""Plot n and k versus wavelength."""

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/nkcalc-matplotlib")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from nkcalc.io.csv_io import ensure_required_columns


def plot_nk(df: pd.DataFrame, path: str | Path | None = None) -> Figure:
    """Plot refractive index n and extinction coefficient k versus wavelength.

    Parameters
    ----------
    df:
        Table with ``lambda_um``, ``n``, and ``k`` columns.
    path:
        Optional output image path. If provided, the figure is saved without displaying GUI.

    Returns
    -------
    matplotlib.figure.Figure
        The generated figure.
    """
    ensure_required_columns(df, ["lambda_um", "n", "k"])
    fig, ax_n = plt.subplots()
    ax_k = ax_n.twinx()

    n_line = ax_n.plot(df["lambda_um"], df["n"], color="tab:blue", label="n")
    k_line = ax_k.plot(df["lambda_um"], df["k"], color="tab:red", label="k")

    ax_n.set_xlabel("Wavelength (um)")
    ax_n.set_ylabel("n")
    ax_k.set_ylabel("k")
    lines = n_line + k_line
    labels = [line.get_label() for line in lines]
    ax_n.legend(lines, labels, loc="best")
    fig.tight_layout()

    if path is not None:
        fig.savefig(path)
    return fig
