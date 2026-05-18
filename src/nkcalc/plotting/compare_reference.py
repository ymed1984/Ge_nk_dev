"""Plot model tables against reference optical data."""

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/nkcalc-matplotlib")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from nkcalc.core.validation import compare_tables


def plot_model_vs_reference(
    model_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    path: str | Path,
    *,
    interpolate: bool = False,
) -> Figure:
    """Plot model and reference ``n``, ``k``, and ``alpha`` versus wavelength.

    Parameters
    ----------
    model_df:
        Model table with ``lambda_um``, ``n``, and ``k`` columns.
    reference_df:
        Reference table with ``lambda_um``, ``n``, and ``k`` columns.
    path:
        Output image path. The figure is saved without requiring a GUI backend.
    interpolate:
        If ``True``, interpolate reference data onto the model wavelength grid.

    Returns
    -------
    matplotlib.figure.Figure
        The generated comparison figure.
    """
    comparison = compare_tables(model_df, reference_df, interpolate=interpolate)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(6.5, 7.0))
    lambda_um = comparison["lambda_um"]

    axes[0].plot(lambda_um, comparison["model_n"], label="model n", color="tab:blue")
    axes[0].plot(lambda_um, comparison["reference_n"], label="reference n", color="tab:blue", ls="--")
    axes[0].set_ylabel("n")

    axes[1].plot(lambda_um, comparison["model_k"], label="model k", color="tab:red")
    axes[1].plot(lambda_um, comparison["reference_k"], label="reference k", color="tab:red", ls="--")
    axes[1].set_ylabel("k")

    axes[2].plot(
        lambda_um,
        comparison["model_alpha_cm_inv"],
        label="model alpha",
        color="tab:green",
    )
    axes[2].plot(
        lambda_um,
        comparison["reference_alpha_cm_inv"],
        label="reference alpha",
        color="tab:green",
        ls="--",
    )
    axes[2].set_ylabel("alpha (cm^-1)")
    axes[2].set_xlabel("Wavelength (um)")

    for ax in axes:
        ax.legend(loc="best")
        ax.grid(True, alpha=0.25)

    fig.tight_layout()
    fig.savefig(output_path)
    return fig
