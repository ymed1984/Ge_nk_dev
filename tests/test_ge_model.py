"""Tests for the Ge optical model facade."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nkcalc.core.nk import nk_to_epsilon
from nkcalc.materials.ge import GeOpticalModel, GeState
from nkcalc.models.tabulated import TabulatedModel


def _synthetic_nk_csv(path: Path) -> None:
    pd.DataFrame(
        {
            "lambda_um": [1.0, 1.5, 2.0],
            "n": [4.0, 4.1, 4.2],
            "k": [0.01, 0.02, 0.03],
        }
    ).to_csv(path, index=False)


def test_from_backend_preserves_interface_and_metadata() -> None:
    """GeOpticalModel wraps BaseOpticalModel-compatible backends."""
    backend = TabulatedModel(
        np.array([1.0, 2.0]),
        np.array([4.0, 4.2]),
        np.array([0.01, 0.03]),
        "nk",
        material="Ge",
        model="synthetic_backend",
    )
    model = GeOpticalModel.from_backend(
        backend,
        state={
            "temperature_K": 300.0,
            "strain_xx": 0.1,
            "source": "synthetic",
            "custom_note": "kept",
        },
    )

    lambda_um = np.array([1.5])
    n, k = model.nk(lambda_um)
    assert np.allclose(model.epsilon(lambda_um), nk_to_epsilon(n, k))

    table = model.table(lambda_um)
    assert table.loc[0, "material"] == "Ge"
    assert table.loc[0, "model"] == "synthetic_backend"
    assert table.loc[0, "temperature_K"] == 300.0
    assert table.loc[0, "strain_xx"] == 0.1
    assert table.loc[0, "strain_state"] == "unstrained"
    assert table.loc[0, "source"] == "synthetic"
    assert table.loc[0, "custom_note"] == "kept"


def test_tabulated_from_csv_constructor(tmp_path) -> None:
    """tabulated_from_csv is the primary path for user/local reference data."""
    path = tmp_path / "ge_reference.csv"
    _synthetic_nk_csv(path)

    model = GeOpticalModel.tabulated_from_csv(
        path,
        state=GeState(temperature_K=295.0),
        source="unit-test local csv",
        reference="synthetic",
    )
    table = model.table(np.array([1.0, 1.5, 2.0]))

    assert table["material"].tolist() == ["Ge", "Ge", "Ge"]
    assert table["model"].tolist() == ["tabulated", "tabulated", "tabulated"]
    assert table["temperature_K"].tolist() == [295.0, 295.0, 295.0]
    assert table["source"].tolist() == ["unit-test local csv"] * 3
    assert table["reference"].tolist() == ["synthetic"] * 3


def test_frey_sellmeier_constructor() -> None:
    """frey_sellmeier returns a Ge facade over the Sellmeier backend."""
    model = GeOpticalModel.frey_sellmeier(temperature_K=295.0)
    table = model.table(np.array([1.9, 5.5]))

    assert table["material"].tolist() == ["Ge", "Ge"]
    assert table["model"].tolist() == ["FreySellmeier", "FreySellmeier"]
    assert table["temperature_K"].tolist() == [295.0, 295.0]
    assert np.allclose(table["k"], 0.0)


def test_lumerical_crc_loader_uses_explicit_column_mapping(tmp_path) -> None:
    """Local Lumerical/CRC CSV is optional reference data with explicit unit mapping."""
    path = tmp_path / "Ge CRC.csv"
    pd.DataFrame(
        {
            "wavelength(m)": [2.0e-6, 3.0e-6],
            "Re(n_xx)": [4.0, 4.1],
            "Im(n_xx)": [0.01, 0.02],
        }
    ).to_csv(path, index=False)

    model = GeOpticalModel.lumerical_crc_from_csv(path)

    assert np.allclose(model.backend.lambda_um_data, [2.0, 3.0])
    table = model.table(np.array([2.0, 3.0]))
    assert table["model"].tolist() == ["LumericalCRC", "LumericalCRC"]
    assert table["source"].tolist() == ["Lumerical standard Ge CRC"] * 2
    assert table["strain_state"].tolist() == ["unstrained", "unstrained"]
    assert table["reference"].tolist() == [str(path), str(path)]


def test_lumerical_crc_loader_rejects_missing_columns(tmp_path) -> None:
    """Lumerical/CRC CSV loader requires exact expected columns."""
    path = tmp_path / "bad_crc.csv"
    pd.DataFrame({"lambda_um": [2.0], "n": [4.0], "k": [0.01]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="wavelength"):
        GeOpticalModel.lumerical_crc_from_csv(path)
