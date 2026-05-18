"""Tests for CSV and Lumerical n/k exports."""

import numpy as np
import pandas as pd
import pytest

from nkcalc.io.csv_io import ensure_required_columns, export_table_csv
from nkcalc.io.lumerical import export_lumerical_nk_txt


def _sample_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "lambda_um": [1.31, 1.55],
            "n": [4.0, 4.1],
            "k": [0.0, 0.01],
        }
    )


def test_ensure_required_columns_accepts_exact_columns() -> None:
    """Required columns are matched by exact name."""
    ensure_required_columns(_sample_table(), ["lambda_um", "n", "k"])


def test_ensure_required_columns_rejects_missing_columns() -> None:
    """Missing columns raise ValueError instead of silent renaming."""
    with pytest.raises(ValueError, match="lambda_um"):
        ensure_required_columns(pd.DataFrame({"wavelength_um": [1.55], "n": [4.0]}), ["lambda_um"])


def test_export_table_csv_writes_without_index(tmp_path) -> None:
    """CSV table export writes DataFrame columns without an index column."""
    path = tmp_path / "table.csv"
    export_table_csv(_sample_table(), path)
    loaded = pd.read_csv(path)
    assert list(loaded.columns) == ["lambda_um", "n", "k"]
    assert np.allclose(loaded["lambda_um"], [1.31, 1.55])


def test_lumerical_export_default_no_header_um(tmp_path) -> None:
    """Default Lumerical export writes headerless wavelength/n/k in microns."""
    path = tmp_path / "ge.txt"
    export_lumerical_nk_txt(_sample_table(), path)
    lines = path.read_text().splitlines()
    assert lines == ["1.31\t4\t0", "1.55\t4.1\t0.01"]


def test_lumerical_export_header_option(tmp_path) -> None:
    """Header option writes the expected first line."""
    path = tmp_path / "ge_header.txt"
    export_lumerical_nk_txt(_sample_table(), path, header=True)
    lines = path.read_text().splitlines()
    assert lines[0] == "wavelength n k"
    assert lines[1] == "1.31\t4\t0"


def test_lumerical_export_nm_unit(tmp_path) -> None:
    """wavelength_unit='nm' converts lambda_um to nanometers on output."""
    path = tmp_path / "ge_nm.txt"
    export_lumerical_nk_txt(_sample_table(), path, wavelength_unit="nm")
    lines = path.read_text().splitlines()
    assert lines == ["1310\t4\t0", "1550\t4.1\t0.01"]


def test_lumerical_export_rejects_unknown_unit(tmp_path) -> None:
    """Only microns and nanometers are accepted output wavelength units."""
    with pytest.raises(ValueError, match="wavelength_unit"):
        export_lumerical_nk_txt(_sample_table(), tmp_path / "bad.txt", wavelength_unit="m")


def test_lumerical_export_rejects_nan_and_inf(tmp_path) -> None:
    """NaN and inf values are rejected."""
    table = _sample_table()
    table.loc[0, "n"] = np.nan
    with pytest.raises(ValueError, match="finite"):
        export_lumerical_nk_txt(table, tmp_path / "nan.txt")


def test_lumerical_export_rejects_negative_k_by_default(tmp_path) -> None:
    """Negative k values are rejected unless explicitly allowed."""
    table = _sample_table()
    table.loc[0, "k"] = -0.01
    with pytest.raises(ValueError, match="negative k"):
        export_lumerical_nk_txt(table, tmp_path / "negative.txt")


def test_lumerical_export_can_allow_negative_k(tmp_path) -> None:
    """Negative k can be exported only with explicit permission."""
    table = _sample_table()
    table.loc[0, "k"] = -0.01
    path = tmp_path / "negative_allowed.txt"
    export_lumerical_nk_txt(table, path, allow_negative_k=True)
    assert path.read_text().splitlines()[0] == "1.31\t4\t-0.01"


def test_lumerical_export_requires_lambda_um_name(tmp_path) -> None:
    """The exporter does not silently rename wavelength columns."""
    table = pd.DataFrame({"wavelength_um": [1.55], "n": [4.0], "k": [0.0]})
    with pytest.raises(ValueError, match="lambda_um"):
        export_lumerical_nk_txt(table, tmp_path / "missing.txt")
