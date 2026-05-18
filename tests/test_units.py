"""Tests for spectral unit conversions."""

import numpy as np

from nkcalc.constants import ELEMENTARY_CHARGE_C, HBAR_J_S, HC_EV_UM
from nkcalc.spectrum import (
    energy_ev_to_omega_rad_s,
    energy_ev_to_wavelength_um,
    wavelength_um_to_energy_ev,
)


def test_wavelength_um_to_energy_ev_uses_hc_ev_um() -> None:
    """Wavelength in microns converts to energy in eV with HC_EV_UM."""
    assert np.allclose(wavelength_um_to_energy_ev(1.0), HC_EV_UM)


def test_wavelength_energy_round_trip() -> None:
    """lambda_um -> energy_eV -> lambda_um round trips."""
    lambda_um = np.array([0.8, 1.31, 1.55, 5.5])
    energy_eV = wavelength_um_to_energy_ev(lambda_um)
    assert np.allclose(energy_ev_to_wavelength_um(energy_eV), lambda_um, rtol=1e-12)


def test_energy_ev_to_omega_rad_s() -> None:
    """Energy in eV converts to angular frequency in rad/s."""
    energy_eV = np.array([1.0, 2.0])
    expected = energy_eV * ELEMENTARY_CHARGE_C / HBAR_J_S
    assert np.allclose(energy_ev_to_omega_rad_s(energy_eV), expected)
