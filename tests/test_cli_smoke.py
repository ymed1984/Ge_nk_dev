"""Smoke tests for the nkcalc command-line interface."""

from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from nkcalc.cli import app

runner = CliRunner()


def test_cli_ge_frey_creates_outputs(tmp_path) -> None:
    """The ge frey command creates CSV, Lumerical txt, and plot outputs."""
    output = tmp_path / "ge_frey.csv"
    lumerical = tmp_path / "ge_frey.txt"
    plot = tmp_path / "ge_frey.png"

    result = runner.invoke(
        app,
        [
            "ge",
            "frey",
            "--lambda-min",
            "1.9",
            "--lambda-max",
            "5.5",
            "--num",
            "5",
            "--temperature",
            "295",
            "--output",
            str(output),
            "--lumerical",
            str(lumerical),
            "--plot",
            str(plot),
        ],
    )

    assert result.exit_code == 0, result.output
    assert output.exists()
    assert lumerical.exists()
    assert plot.exists()
    assert len(pd.read_csv(output)) == 5
    assert len(lumerical.read_text().splitlines()) == 5


def test_cli_table_from_nk_csv_creates_outputs(tmp_path) -> None:
    """The table from-nk-csv command creates output files from synthetic input."""
    input_csv = tmp_path / "synthetic_ge.csv"
    pd.DataFrame(
        {
            "lambda_um": [1.0, 1.5, 2.0],
            "n": [4.0, 4.1, 4.2],
            "k": [0.01, 0.02, 0.03],
        }
    ).to_csv(input_csv, index=False)
    output = tmp_path / "table.csv"
    lumerical = tmp_path / "table.txt"
    plot = tmp_path / "table.png"

    result = runner.invoke(
        app,
        [
            "table",
            "from-nk-csv",
            str(input_csv),
            "--lambda-min",
            "1.0",
            "--lambda-max",
            "2.0",
            "--num",
            "4",
            "--output",
            str(output),
            "--lumerical",
            str(lumerical),
            "--plot",
            str(plot),
        ],
    )

    assert result.exit_code == 0, result.output
    assert output.exists()
    assert lumerical.exists()
    assert plot.exists()
    table = pd.read_csv(output)
    assert table["material"].tolist() == ["Ge"] * 4
    assert len(lumerical.read_text().splitlines()) == 4


def test_cli_table_from_lumerical_csv_maps_columns(tmp_path) -> None:
    """The optional Lumerical CSV command uses explicit column and unit mapping."""
    input_csv = tmp_path / "lumerical_crc.csv"
    pd.DataFrame(
        {
            "wavelength(m)": [2.0e-6, 3.0e-6],
            " Re(n_xx)": [4.0, 4.1],
            " Im(n_xx)": [0.01, 0.02],
        }
    ).to_csv(input_csv, index=False)
    output = tmp_path / "lumerical_table.csv"

    result = runner.invoke(
        app,
        ["table", "from-lumerical-csv", str(input_csv), "--output", str(output)],
    )

    assert result.exit_code == 0, result.output
    table = pd.read_csv(output)
    assert table["lambda_um"].tolist() == [2.0, 3.0]
    assert table["source"].tolist() == ["Lumerical standard Ge CRC"] * 2
    assert table["strain_state"].tolist() == ["unstrained"] * 2


def test_cli_rejects_invalid_grid(tmp_path: Path) -> None:
    """Invalid wavelength grid options fail through Typer."""
    result = runner.invoke(
        app,
        ["ge", "frey", "--lambda-min", "2.0", "--lambda-max", "1.0", "--num", "5"],
    )

    assert result.exit_code != 0
