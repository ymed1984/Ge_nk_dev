"""Conversions between complex dielectric function, n/k, and absorption."""

import numpy as np

from nkcalc.constants import M_TO_CM, UM_TO_M


def epsilon_to_nk(eps_complex: complex | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert complex dielectric function to refractive index n and extinction k.

    Parameters
    ----------
    eps_complex:
        Complex dielectric function, ``eps = eps1 + 1j * eps2``.

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray]
        Refractive index ``n`` and extinction coefficient ``k``. The passive branch is
        selected so that ``k >= 0``.
    """
    eps_array = np.asarray(eps_complex, dtype=complex)
    n_complex = np.sqrt(eps_array)
    n_complex = np.where(np.imag(n_complex) < 0.0, -n_complex, n_complex)
    return np.real(n_complex), np.imag(n_complex)


def nk_to_epsilon(n: float | np.ndarray, k: float | np.ndarray) -> np.ndarray:
    """Convert refractive index n and extinction coefficient k to epsilon.

    Parameters
    ----------
    n:
        Refractive index, dimensionless.
    k:
        Extinction coefficient, dimensionless.

    Returns
    -------
    numpy.ndarray
        Complex dielectric function ``eps = (n + 1j * k)**2``.
    """
    n_array = np.asarray(n, dtype=float)
    k_array = np.asarray(k, dtype=float)
    return (n_array + 1j * k_array) ** 2


def k_to_alpha_m_inv(k: float | np.ndarray, lambda_um: float | np.ndarray) -> np.ndarray:
    """Convert extinction coefficient k to absorption coefficient in m^-1.

    Parameters
    ----------
    k:
        Extinction coefficient, dimensionless.
    lambda_um:
        Wavelength in microns.

    Returns
    -------
    numpy.ndarray
        Absorption coefficient in m^-1 using ``alpha = 4*pi*k/lambda``.
    """
    k_array = np.asarray(k, dtype=float)
    lambda_m = np.asarray(lambda_um, dtype=float) * UM_TO_M
    return 4.0 * np.pi * k_array / lambda_m


def k_to_alpha_cm_inv(k: float | np.ndarray, lambda_um: float | np.ndarray) -> np.ndarray:
    """Convert extinction coefficient k to absorption coefficient in cm^-1.

    Parameters
    ----------
    k:
        Extinction coefficient, dimensionless.
    lambda_um:
        Wavelength in microns.

    Returns
    -------
    numpy.ndarray
        Absorption coefficient in cm^-1.
    """
    return k_to_alpha_m_inv(k, lambda_um) / M_TO_CM


def alpha_cm_inv_to_k(
    alpha_cm_inv: float | np.ndarray,
    lambda_um: float | np.ndarray,
) -> np.ndarray:
    """Convert absorption coefficient in cm^-1 to extinction coefficient k.

    Parameters
    ----------
    alpha_cm_inv:
        Absorption coefficient in cm^-1.
    lambda_um:
        Wavelength in microns.

    Returns
    -------
    numpy.ndarray
        Extinction coefficient, dimensionless.
    """
    alpha_m_inv = np.asarray(alpha_cm_inv, dtype=float) * M_TO_CM
    lambda_m = np.asarray(lambda_um, dtype=float) * UM_TO_M
    return alpha_m_inv * lambda_m / (4.0 * np.pi)
