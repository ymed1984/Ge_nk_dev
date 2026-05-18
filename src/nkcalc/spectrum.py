"""Spectral unit conversion helpers."""

import numpy as np

from nkcalc.constants import ELEMENTARY_CHARGE_C, HBAR_J_S, HC_EV_UM


def wavelength_um_to_energy_ev(lambda_um: float | np.ndarray) -> np.ndarray:
    """Convert wavelength in microns to photon energy in electron volts.

    Parameters
    ----------
    lambda_um:
        Wavelength in microns.

    Returns
    -------
    numpy.ndarray
        Photon energy in electron volts.
    """
    lambda_um_array = np.asarray(lambda_um, dtype=float)
    return HC_EV_UM / lambda_um_array


def energy_ev_to_wavelength_um(energy_eV: float | np.ndarray) -> np.ndarray:
    """Convert photon energy in electron volts to wavelength in microns.

    Parameters
    ----------
    energy_eV:
        Photon energy in electron volts.

    Returns
    -------
    numpy.ndarray
        Wavelength in microns.
    """
    energy_eV_array = np.asarray(energy_eV, dtype=float)
    return HC_EV_UM / energy_eV_array


def energy_ev_to_omega_rad_s(energy_eV: float | np.ndarray) -> np.ndarray:
    """Convert photon energy in electron volts to angular frequency in rad/s.

    Parameters
    ----------
    energy_eV:
        Photon energy in electron volts.

    Returns
    -------
    numpy.ndarray
        Angular frequency in radians per second.
    """
    energy_eV_array = np.asarray(energy_eV, dtype=float)
    return energy_eV_array * ELEMENTARY_CHARGE_C / HBAR_J_S
