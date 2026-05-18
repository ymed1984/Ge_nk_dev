"""Base interfaces for optical models."""

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

from nkcalc.core.nk import epsilon_to_nk, k_to_alpha_cm_inv, k_to_alpha_m_inv
from nkcalc.spectrum import wavelength_um_to_energy_ev


class BaseOpticalModel(ABC):
    """Abstract base class for optical models returning complex epsilon."""

    material: str = "unknown"
    model: str = "unknown"

    @abstractmethod
    def epsilon(self, lambda_um: float | np.ndarray) -> np.ndarray:
        """Return complex dielectric function at wavelength in microns."""

    def nk(self, lambda_um: float | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return refractive index n and extinction coefficient k.

        Parameters
        ----------
        lambda_um:
            Wavelength in microns.

        Returns
        -------
        tuple[numpy.ndarray, numpy.ndarray]
            Refractive index ``n`` and extinction coefficient ``k``.
        """
        return epsilon_to_nk(self.epsilon(lambda_um))

    def table(self, lambda_um: float | np.ndarray) -> pd.DataFrame:
        """Return a standard optical table for wavelengths in microns.

        Parameters
        ----------
        lambda_um:
            Wavelength in microns.

        Returns
        -------
        pandas.DataFrame
            Columns are ``lambda_um``, ``energy_eV``, ``eps1``, ``eps2``, ``n``, ``k``,
            ``alpha_m_inv``, ``alpha_cm_inv``, ``material``, and ``model``.
        """
        lambda_um_array = np.asarray(lambda_um, dtype=float)
        eps = self.epsilon(lambda_um_array)
        n, k = epsilon_to_nk(eps)
        return pd.DataFrame(
            {
                "lambda_um": lambda_um_array,
                "energy_eV": wavelength_um_to_energy_ev(lambda_um_array),
                "eps1": np.real(eps),
                "eps2": np.imag(eps),
                "n": n,
                "k": k,
                "alpha_m_inv": k_to_alpha_m_inv(k, lambda_um_array),
                "alpha_cm_inv": k_to_alpha_cm_inv(k, lambda_um_array),
                "material": self.material,
                "model": self.model,
            }
        )
