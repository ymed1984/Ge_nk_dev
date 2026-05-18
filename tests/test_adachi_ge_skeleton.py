"""Tests for the Ge Adachi-style critical-point scaffold."""

import numpy as np
import pandas as pd
import pytest
import yaml

from nkcalc.models.adachi_ge import AdachiGeModel
from nkcalc.models.critical_point import CriticalPoint


def _synthetic_yaml(path) -> None:
    params = {
        "eps_inf": 2.0,
        "validity": {"wavelength_um": [0.6, 5.0], "energy_eV": [0.25, 2.2]},
        "implemented_terms": ["eps_inf", "generic_lorentz_placeholder"],
        "source_notes": "synthetic placeholder test data, not literature values",
        "critical_points": [
            {
                "name": "placeholder_E0_to_be_fitted",
                "energy_eV": 1.0,
                "amplitude": 0.5,
                "gamma_eV": 0.1,
                "phase": 0.0,
                "kind": "generic_lorentz",
                "provenance": "placeholder_to_be_fitted",
            }
        ],
    }
    path.write_text(yaml.safe_dump(params), encoding="utf-8")


def test_critical_point_contribution_shape_and_complex() -> None:
    """Generic critical-point terms return complex arrays with input shape."""
    critical_point = CriticalPoint(
        name="placeholder_E0_to_be_fitted",
        energy_eV=1.0,
        amplitude=0.5,
        gamma_eV=0.1,
    )
    contribution = critical_point.contribution(np.array([0.8, 1.2]))
    assert contribution.shape == (2,)
    assert np.iscomplexobj(contribution)


def test_adachi_ge_yaml_loader(tmp_path) -> None:
    """YAML loader builds the Ge scaffold and preserves metadata."""
    path = tmp_path / "ge_adachi.yml"
    _synthetic_yaml(path)

    model = AdachiGeModel.from_yaml(path)

    assert model.material == "Ge"
    assert model.model == "AdachiGeSkeleton"
    assert model.eps_inf == 2.0 + 0.0j
    assert model.implemented_terms == ["eps_inf", "generic_lorentz_placeholder"]
    assert "not literature" in model.source_notes
    assert model.critical_points[0].provenance == "placeholder_to_be_fitted"


def test_epsilon_returns_complex_ndarray(tmp_path) -> None:
    """epsilon(lambda_um) returns complex ndarray."""
    path = tmp_path / "ge_adachi.yml"
    _synthetic_yaml(path)
    model = AdachiGeModel.from_yaml(path)

    eps = model.epsilon(np.array([1.0, 2.0]))

    assert eps.shape == (2,)
    assert np.iscomplexobj(eps)


def test_validity_ranges_raise(tmp_path) -> None:
    """Wavelength and energy validity ranges reject out-of-range inputs."""
    path = tmp_path / "ge_adachi.yml"
    _synthetic_yaml(path)
    model = AdachiGeModel.from_yaml(path)

    with pytest.raises(ValueError, match="lambda_um"):
        model.epsilon([0.5])
    with pytest.raises(ValueError, match="energy_eV"):
        model.epsilon([5.0])


def test_table_contains_standard_columns(tmp_path) -> None:
    """table() exposes n, k, and alpha columns through BaseOpticalModel."""
    path = tmp_path / "ge_adachi.yml"
    _synthetic_yaml(path)
    model = AdachiGeModel.from_yaml(path)

    table = model.table(np.array([1.0, 2.0]))

    expected_columns = [
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
    assert list(table.columns) == expected_columns
    assert table["material"].tolist() == ["Ge", "Ge"]
    assert table["model"].tolist() == ["AdachiGeSkeleton", "AdachiGeSkeleton"]


def test_bundled_yaml_marks_placeholders() -> None:
    """Bundled initial YAML is explicitly placeholder/to_be_fitted."""
    model = AdachiGeModel.from_yaml("data/params/ge_adachi_initial.yml")

    assert "generic_lorentz_placeholder" in model.implemented_terms
    assert all("placeholder" in point.name for point in model.critical_points)
    assert all("placeholder" in point.provenance for point in model.critical_points)
    assert "not a faithful full Adachi implementation" in model.source_notes
    table = model.table(np.array([1.0, 2.0]))
    assert isinstance(table, pd.DataFrame)
