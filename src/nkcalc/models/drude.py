"""Drude free-carrier dielectric contribution."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from nkcalc.constants import (
    CM2_PER_VS_TO_M2_PER_VS,
    CM3_TO_M3_DENSITY,
    ELECTRON_MASS_KG,
    ELEMENTARY_CHARGE_C,
    EPSILON_0_F_M,
)
from nkcalc.models.base import BaseOpticalModel
from nkcalc.spectrum import wavelength_um_to_energy_ev, energy_ev_to_omega_rad_s


@dataclass
class DrudeModel(BaseOpticalModel):
    """Standalone Drude free-carrier contribution model.

    ``epsilon(lambda_um)`` returns only ``Delta eps_Drude``. Add it to a host dielectric
    model explicitly when needed.
    """

    electron_cm3: float = 0.0
    hole_cm3: float = 0.0
    electron_effective_mass_rel: float = 1.0
    hole_effective_mass_rel: float = 1.0
    electron_mobility_cm2_Vs: float = 1.0
    hole_mobility_cm2_Vs: float = 1.0
    material: str = "Ge"
    model: str = "Drude"
    parameter_provenance: str = "placeholder"
    source_notes: str = "placeholder parameters; user should provide material-specific values"

    @classmethod
    def from_yaml(cls, path: str | Path) -> "DrudeModel":
        """Load Drude parameters from YAML."""
        with Path(path).open(encoding="utf-8") as stream:
            params = yaml.safe_load(stream)

        if not isinstance(params, dict):
            raise ValueError("Drude YAML must contain a mapping")

        carriers = params.get("carriers", {})
        electron = carriers.get("electron", {})
        hole = carriers.get("hole", {})
        provenance = params.get("parameter_provenance", "placeholder")
        return cls(
            electron_cm3=float(electron.get("density_cm3", 0.0)),
            hole_cm3=float(hole.get("density_cm3", 0.0)),
            electron_effective_mass_rel=float(electron["effective_mass_rel"]),
            hole_effective_mass_rel=float(hole["effective_mass_rel"]),
            electron_mobility_cm2_Vs=float(electron["mobility_cm2_Vs"]),
            hole_mobility_cm2_Vs=float(hole["mobility_cm2_Vs"]),
            material=params.get("material", "Ge"),
            model=params.get("model", "Drude"),
            parameter_provenance=provenance,
            source_notes=params.get("source_notes", ""),
        )

    def epsilon(self, lambda_um: float | np.ndarray) -> np.ndarray:
        """Return Drude ``Delta eps`` at wavelength in microns."""
        omega_rad_s = energy_ev_to_omega_rad_s(wavelength_um_to_energy_ev(lambda_um))
        return self.delta_epsilon_omega_rad_s(omega_rad_s)

    def delta_epsilon_omega_rad_s(self, omega_rad_s: float | np.ndarray) -> np.ndarray:
        """Return Drude ``Delta eps`` at angular frequency in rad/s."""
        omega = np.asarray(omega_rad_s, dtype=float)
        if not np.all(np.isfinite(omega)):
            raise ValueError("omega_rad_s must contain only finite values")
        if np.any(omega <= 0.0):
            raise ValueError("omega_rad_s must be positive")

        delta = np.zeros_like(omega, dtype=complex)
        delta += _carrier_delta_epsilon(
            omega,
            density_cm3=self.electron_cm3,
            effective_mass_rel=self.electron_effective_mass_rel,
            mobility_cm2_Vs=self.electron_mobility_cm2_Vs,
        )
        delta += _carrier_delta_epsilon(
            omega,
            density_cm3=self.hole_cm3,
            effective_mass_rel=self.hole_effective_mass_rel,
            mobility_cm2_Vs=self.hole_mobility_cm2_Vs,
        )
        return delta

    def electron_density_m3(self) -> float:
        """Return electron density in m^-3."""
        return _density_cm3_to_m3(self.electron_cm3)

    def hole_density_m3(self) -> float:
        """Return hole density in m^-3."""
        return _density_cm3_to_m3(self.hole_cm3)

    def electron_mobility_m2_Vs(self) -> float:
        """Return electron mobility in m^2/(V s)."""
        return _mobility_cm2_Vs_to_m2_Vs(self.electron_mobility_cm2_Vs)

    def hole_mobility_m2_Vs(self) -> float:
        """Return hole mobility in m^2/(V s)."""
        return _mobility_cm2_Vs_to_m2_Vs(self.hole_mobility_cm2_Vs)


def _carrier_delta_epsilon(
    omega_rad_s: np.ndarray,
    *,
    density_cm3: float,
    effective_mass_rel: float,
    mobility_cm2_Vs: float,
) -> np.ndarray:
    """Return one carrier species' Drude contribution."""
    if density_cm3 == 0.0:
        return np.zeros_like(omega_rad_s, dtype=complex)
    if density_cm3 < 0.0:
        raise ValueError("carrier density in cm^-3 must be nonnegative")
    if effective_mass_rel <= 0.0:
        raise ValueError("effective mass ratio must be positive")
    if mobility_cm2_Vs <= 0.0:
        raise ValueError("mobility_cm2_Vs must be positive")

    density_m3 = _density_cm3_to_m3(density_cm3)
    effective_mass_kg = effective_mass_rel * ELECTRON_MASS_KG
    mobility_m2_Vs = _mobility_cm2_Vs_to_m2_Vs(mobility_cm2_Vs)
    omega_p_squared = density_m3 * ELEMENTARY_CHARGE_C**2 / (EPSILON_0_F_M * effective_mass_kg)
    gamma_rad_s = ELEMENTARY_CHARGE_C / (effective_mass_kg * mobility_m2_Vs)
    return -omega_p_squared / (omega_rad_s * (omega_rad_s + 1j * gamma_rad_s))


def _density_cm3_to_m3(density_cm3: float) -> float:
    """Convert carrier density from cm^-3 to m^-3."""
    return float(density_cm3) * CM3_TO_M3_DENSITY


def _mobility_cm2_Vs_to_m2_Vs(mobility_cm2_Vs: float) -> float:
    """Convert mobility from cm^2/(V s) to m^2/(V s)."""
    return float(mobility_cm2_Vs) * CM2_PER_VS_TO_M2_PER_VS
