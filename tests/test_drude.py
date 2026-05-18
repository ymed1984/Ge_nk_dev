"""Tests for Drude free-carrier dielectric contribution."""

import numpy as np
import pytest

from nkcalc.constants import CM2_PER_VS_TO_M2_PER_VS, CM3_TO_M3_DENSITY
from nkcalc.core.nk import epsilon_to_nk
from nkcalc.models.drude import DrudeModel


def test_zero_carrier_returns_exact_zero_delta_eps() -> None:
    """Zero carrier densities return exactly zero complex delta epsilon."""
    model = DrudeModel(
        electron_cm3=0.0,
        hole_cm3=0.0,
        electron_effective_mass_rel=0.1,
        hole_effective_mass_rel=0.2,
        electron_mobility_cm2_Vs=1000.0,
        hole_mobility_cm2_Vs=500.0,
    )
    delta = model.epsilon(np.array([1.55, 3.0]))
    assert np.array_equal(delta, np.zeros(2, dtype=complex))


def test_nonzero_carrier_changes_eps_and_long_wavelength_loss_more() -> None:
    """Nonzero carriers change epsilon and increase loss more at longer wavelength."""
    model = DrudeModel(
        electron_cm3=1.0e18,
        hole_cm3=0.0,
        electron_effective_mass_rel=0.12,
        hole_effective_mass_rel=0.3,
        electron_mobility_cm2_Vs=1000.0,
        hole_mobility_cm2_Vs=500.0,
    )

    lambda_um = np.array([1.55, 5.0])
    delta = model.epsilon(lambda_um)
    assert np.any(delta != 0.0)
    n, k = epsilon_to_nk(16.0 + delta)
    assert n.shape == lambda_um.shape
    assert k[1] > k[0]


def test_unit_conversions() -> None:
    """Carrier density and mobility conversions use SI factors."""
    model = DrudeModel(
        electron_cm3=2.0e17,
        hole_cm3=3.0e17,
        electron_effective_mass_rel=0.12,
        hole_effective_mass_rel=0.3,
        electron_mobility_cm2_Vs=1500.0,
        hole_mobility_cm2_Vs=450.0,
    )
    assert model.electron_density_m3() == 2.0e17 * CM3_TO_M3_DENSITY
    assert model.hole_density_m3() == 3.0e17 * CM3_TO_M3_DENSITY
    assert model.electron_mobility_m2_Vs() == 1500.0 * CM2_PER_VS_TO_M2_PER_VS
    assert model.hole_mobility_m2_Vs() == 450.0 * CM2_PER_VS_TO_M2_PER_VS


def test_yaml_loader_marks_placeholder_parameters() -> None:
    """Bundled YAML loads and records placeholder provenance."""
    model = DrudeModel.from_yaml("data/params/ge_drude.yml")
    assert model.material == "Ge"
    assert model.model == "Drude"
    assert model.parameter_provenance == "placeholder"
    assert "Placeholder" in model.source_notes
    assert np.array_equal(model.epsilon([1.55]), np.zeros(1, dtype=complex))


def test_negative_density_and_nonpositive_parameters_raise() -> None:
    """Invalid carrier parameters raise ValueError once a carrier is present."""
    with pytest.raises(ValueError, match="nonnegative"):
        DrudeModel(
            electron_cm3=-1.0,
            electron_effective_mass_rel=0.12,
            hole_effective_mass_rel=0.3,
            electron_mobility_cm2_Vs=1000.0,
            hole_mobility_cm2_Vs=500.0,
        ).epsilon([1.55])

    with pytest.raises(ValueError, match="effective mass"):
        DrudeModel(
            electron_cm3=1.0,
            electron_effective_mass_rel=0.0,
            hole_effective_mass_rel=0.3,
            electron_mobility_cm2_Vs=1000.0,
            hole_mobility_cm2_Vs=500.0,
        ).epsilon([1.55])

    with pytest.raises(ValueError, match="mobility"):
        DrudeModel(
            electron_cm3=1.0,
            electron_effective_mass_rel=0.12,
            hole_effective_mass_rel=0.3,
            electron_mobility_cm2_Vs=0.0,
            hole_mobility_cm2_Vs=500.0,
        ).epsilon([1.55])


def test_frequency_must_be_positive() -> None:
    """Angular frequency must be finite and positive."""
    with pytest.raises(ValueError, match="positive"):
        DrudeModel().delta_epsilon_omega_rad_s([0.0])
