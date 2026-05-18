"""Command-line interface for nkcalc."""

from pathlib import Path

import numpy as np

import typer

from nkcalc.io.csv_io import export_table_csv
from nkcalc.io.lumerical import export_lumerical_nk_txt
from nkcalc.materials.ge import GeOpticalModel
from nkcalc.plotting.plot_nk import plot_nk

app = typer.Typer(help="Optical n,k calculation tools for Ge, SiGe, and Si.")
ge_app = typer.Typer(help="Germanium model commands.")
table_app = typer.Typer(help="Tabulated data commands.")
app.add_typer(ge_app, name="ge")
app.add_typer(table_app, name="table")


@app.callback()
def main() -> None:
    """Run the nkcalc command-line interface."""


@ge_app.command("frey")
def ge_frey(
    lambda_min: float = typer.Option(1.9, "--lambda-min", help="Minimum wavelength in um."),
    lambda_max: float = typer.Option(5.5, "--lambda-max", help="Maximum wavelength in um."),
    num: int = typer.Option(301, "--num", help="Number of wavelength points."),
    temperature: float = typer.Option(295.0, "--temperature", help="Temperature in K."),
    params: Path | None = typer.Option(None, "--params", help="Sellmeier YAML parameter path."),
    output: Path | None = typer.Option(None, "--output", help="Output CSV path."),
    lumerical: Path | None = typer.Option(None, "--lumerical", help="Lumerical n/k txt path."),
    plot: Path | None = typer.Option(None, "--plot", help="Plot image path."),
) -> None:
    """Generate a Ge Frey-style Sellmeier table."""
    lambda_um = _wavelength_grid(lambda_min, lambda_max, num)
    model = GeOpticalModel.frey_sellmeier(temperature_K=temperature, params_path=params)
    _write_outputs(model.table(lambda_um), output=output, lumerical=lumerical, plot=plot)


@table_app.command("from-nk-csv")
def table_from_nk_csv(
    path: Path = typer.Argument(..., help="Input n/k CSV path."),
    lambda_min: float | None = typer.Option(None, "--lambda-min", help="Minimum wavelength in um."),
    lambda_max: float | None = typer.Option(None, "--lambda-max", help="Maximum wavelength in um."),
    num: int = typer.Option(301, "--num", help="Number of wavelength points."),
    output: Path | None = typer.Option(None, "--output", help="Output CSV path."),
    lumerical: Path | None = typer.Option(None, "--lumerical", help="Lumerical n/k txt path."),
    plot: Path | None = typer.Option(None, "--plot", help="Plot image path."),
) -> None:
    """Generate a table from a user-provided n/k CSV."""
    model = GeOpticalModel.tabulated_from_csv(path)
    backend = model.backend
    start = float(backend.lambda_um_data[0]) if lambda_min is None else lambda_min
    stop = float(backend.lambda_um_data[-1]) if lambda_max is None else lambda_max
    lambda_um = _wavelength_grid(start, stop, num)
    _write_outputs(model.table(lambda_um), output=output, lumerical=lumerical, plot=plot)


@table_app.command("from-lumerical-csv")
def table_from_lumerical_csv(
    path: Path = typer.Argument(..., help="Input Lumerical/CRC Ge CSV path."),
    output: Path | None = typer.Option(None, "--output", help="Output CSV path."),
    lumerical: Path | None = typer.Option(None, "--lumerical", help="Lumerical n/k txt path."),
    plot: Path | None = typer.Option(None, "--plot", help="Plot image path."),
) -> None:
    """Generate a table from local Lumerical/CRC Ge CSV reference data."""
    model = GeOpticalModel.lumerical_crc_from_csv(path)
    lambda_um = model.backend.lambda_um_data
    _write_outputs(model.table(lambda_um), output=output, lumerical=lumerical, plot=plot)


def _wavelength_grid(lambda_min: float, lambda_max: float, num: int) -> np.ndarray:
    """Return a wavelength grid in microns."""
    if num < 2:
        raise typer.BadParameter("num must be at least 2")
    if lambda_min >= lambda_max:
        raise typer.BadParameter("lambda-min must be smaller than lambda-max")
    return np.linspace(lambda_min, lambda_max, num)


def _write_outputs(
    df,
    *,
    output: Path | None,
    lumerical: Path | None,
    plot: Path | None,
) -> None:
    """Write requested table, Lumerical, and plot outputs."""
    if output is not None:
        export_table_csv(df, output)
    if lumerical is not None:
        export_lumerical_nk_txt(df, lumerical)
    if plot is not None:
        fig = plot_nk(df, plot)
        import matplotlib.pyplot as plt

        plt.close(fig)
