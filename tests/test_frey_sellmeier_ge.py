"""Tests for the Ge Frey-style Sellmeier model."""

import numpy as np
import pytest

from nkcalc.materials.ge import ge_frey_sellmeier
from nkcalc.models.sellmeier import FreySellmeierModel, SellmeierTerm


def _synthetic_model(temperature_K: float = 100.0) -> FreySellmeierModel:
    return FreySellmeierModel(
        [
            SellmeierTerm(
                strength_coefficients=(2.0, 1.0e-3),
                resonance_um_coefficients=(0.5, 1.0e-4),
            )
        ],
        temperature_K=temperature_K,
        wavelength_range_um=(1.9, 5.5),
        temperature_range_K=(20.0, 300.0),
        coefficient_provenance="synthetic",
        source="unit-test synthetic coefficients",
    )


def test_synthetic_sellmeier_formula() -> None:
    """Synthetic coefficients evaluate the expected Sellmeier formula."""
    model = _synthetic_model(temperature_K=100.0)
    lambda_um = np.array([2.0, 3.0])
    eps = model.epsilon(lambda_um)

    strength = 2.0 + 1.0e-3 * 100.0
    resonance_um = 0.5 + 1.0e-4 * 100.0
    expected_n_squared = 1.0 + strength * lambda_um**2 / (lambda_um**2 - resonance_um**2)
    assert np.allclose(eps.real, expected_n_squared)
    assert np.allclose(eps.imag, 0.0)


def test_temperature_changes_shape_but_not_output_shape() -> None:
    """Temperature-dependent coefficients affect output while preserving shape."""
    lambda_um = np.array([2.0, 3.0, 4.0])
    low_temperature = _synthetic_model(temperature_K=50.0).epsilon(lambda_um)
    high_temperature = _synthetic_model(temperature_K=250.0).epsilon(lambda_um)
    assert low_temperature.shape == lambda_um.shape
    assert high_temperature.shape == lambda_um.shape
    assert not np.allclose(low_temperature, high_temperature)


def test_validity_range_is_enforced() -> None:
    """Default Ge validity ranges reject temperatures and wavelengths outside scope."""
    with pytest.raises(ValueError, match="temperature_K"):
        _synthetic_model(temperature_K=10.0)

    model = _synthetic_model()
    with pytest.raises(ValueError, match="lambda_um"):
        model.epsilon([1.8])
    with pytest.raises(ValueError, match="lambda_um"):
        model.epsilon([5.6])


def test_table_returns_expected_columns_and_k_zero() -> None:
    """Transparent-side model table includes standard columns and k=0."""
    model = _synthetic_model()
    lambda_um = np.array([2.0, 3.0])
    table = model.table(lambda_um)

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
    assert np.allclose(table["k"], 0.0)
    assert np.allclose(table["alpha_m_inv"], 0.0)
    assert table["model"].tolist() == ["FreySellmeier", "FreySellmeier"]


def test_yaml_loader_records_placeholder_provenance() -> None:
    """Bundled YAML loads and marks coefficients as placeholders."""
    model = ge_frey_sellmeier(temperature_K=295.0)
    assert model.material == "Ge"
    assert model.model == "FreySellmeier"
    assert model.coefficient_provenance == "placeholder"
    assert "placeholder" in model.source
    eps = model.epsilon(np.array([1.9, 5.5]))
    assert eps.shape == (2,)
