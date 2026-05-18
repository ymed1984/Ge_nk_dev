"""Tests for user-provided tabulated optical models."""

import numpy as np
import pandas as pd
import pytest

from nkcalc.core.nk import epsilon_to_nk, nk_to_epsilon
from nkcalc.models.tabulated import TabulatedModel


def _nk_reference() -> pd.DataFrame:
    lambda_um = np.array([1.0, 1.5, 2.0])
    n = 3.0 + 0.2 * lambda_um
    k = 0.01 + 0.02 * lambda_um
    return pd.DataFrame({"lambda_um": lambda_um, "n": n, "k": k})


def test_from_nk_csv_interpolates_synthetic_data(tmp_path) -> None:
    """TabulatedModel interpolates synthetic n/k CSV data."""
    path = tmp_path / "synthetic_nk.csv"
    _nk_reference().to_csv(path, index=False)

    model = TabulatedModel.from_nk_csv(path, material="Ge", model="synthetic")
    lambda_um = np.array([1.25, 1.75])
    n, k = model.nk(lambda_um)

    assert np.allclose(n, 3.0 + 0.2 * lambda_um)
    assert np.allclose(k, 0.01 + 0.02 * lambda_um)
    assert np.allclose(model.epsilon(lambda_um), nk_to_epsilon(n, k))


def test_from_eps_csv_interpolates_synthetic_data(tmp_path) -> None:
    """TabulatedModel interpolates synthetic eps CSV data and derives n/k."""
    lambda_um = np.array([1.0, 1.5, 2.0])
    eps1 = 12.0 + lambda_um
    eps2 = 0.1 + 0.2 * lambda_um
    path = tmp_path / "synthetic_eps.csv"
    pd.DataFrame({"wavelength_um": lambda_um, "eps1": eps1, "eps2": eps2}).to_csv(
        path,
        index=False,
    )

    model = TabulatedModel.from_eps_csv(path, material="Ge", model="eps_synthetic")
    query = np.array([1.25, 1.75])
    eps = model.epsilon(query)

    assert np.allclose(eps.real, 12.0 + query)
    assert np.allclose(eps.imag, 0.1 + 0.2 * query)
    n, k = model.nk(query)
    expected_n, expected_k = epsilon_to_nk(eps)
    assert np.allclose(n, expected_n)
    assert np.allclose(k, expected_k)


def test_lambda_nm_column_converts_to_um(tmp_path) -> None:
    """Explicit nanometer wavelength columns are converted to microns."""
    path = tmp_path / "synthetic_nm.csv"
    pd.DataFrame({"lambda_nm": [1000.0, 1500.0, 2000.0], "n": [3.2, 3.3, 3.4], "k": [0, 0, 0]}).to_csv(
        path,
        index=False,
    )
    model = TabulatedModel.from_nk_csv(path)
    assert np.allclose(model.lambda_um_data, [1.0, 1.5, 2.0])


def test_ambiguous_wavelength_columns_raise(tmp_path) -> None:
    """Multiple wavelength columns are rejected instead of guessed."""
    path = tmp_path / "ambiguous.csv"
    pd.DataFrame(
        {
            "lambda_um": [1.0, 2.0],
            "wavelength_um": [1.0, 2.0],
            "n": [3.0, 3.1],
            "k": [0.0, 0.0],
        }
    ).to_csv(path, index=False)

    with pytest.raises(ValueError, match="ambiguous"):
        TabulatedModel.from_nk_csv(path)


def test_missing_wavelength_column_raises(tmp_path) -> None:
    """A recognized wavelength column is required."""
    path = tmp_path / "missing_wavelength.csv"
    pd.DataFrame({"wavelength": [1.0, 2.0], "n": [3.0, 3.1], "k": [0.0, 0.0]}).to_csv(
        path,
        index=False,
    )

    with pytest.raises(ValueError, match="wavelength column"):
        TabulatedModel.from_nk_csv(path)


def test_missing_data_columns_raise(tmp_path) -> None:
    """n/k and eps CSV loaders require their exact data columns."""
    path = tmp_path / "missing_k.csv"
    pd.DataFrame({"lambda_um": [1.0, 2.0], "n": [3.0, 3.1]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="k"):
        TabulatedModel.from_nk_csv(path)


def test_out_of_range_raises(tmp_path) -> None:
    """No extrapolation is performed outside the tabulated wavelength range."""
    path = tmp_path / "synthetic_nk.csv"
    _nk_reference().to_csv(path, index=False)
    model = TabulatedModel.from_nk_csv(path)

    with pytest.raises(ValueError, match="lambda_um"):
        model.epsilon([0.9])
    with pytest.raises(ValueError, match="lambda_um"):
        model.nk([2.1])


def test_table_columns_and_metadata(tmp_path) -> None:
    """table() returns the standard optical table columns and metadata."""
    path = tmp_path / "synthetic_nk.csv"
    _nk_reference().to_csv(path, index=False)
    model = TabulatedModel.from_nk_csv(path, material="Ge", model="synthetic")

    table = model.table(np.array([1.0, 1.5, 2.0]))

    assert list(table.columns) == [
        "lambda_um",
        "energy_eV",
        "eps1",
        "eps2",
        "n",
        "k",
        "alpha_m_inv",
        "alpha_cm_inv",
        "material",
        "model",
    ]
    assert table["material"].tolist() == ["Ge", "Ge", "Ge"]
    assert table["model"].tolist() == ["synthetic", "synthetic", "synthetic"]
    assert np.allclose(table["eps1"] + 1j * table["eps2"], nk_to_epsilon(table["n"], table["k"]))
