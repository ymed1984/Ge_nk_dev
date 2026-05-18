"""Critical-point dielectric model scaffolding."""

from dataclasses import dataclass

import numpy as np

from nkcalc.core.validation import ensure_within_range
from nkcalc.models.base import BaseOpticalModel
from nkcalc.spectrum import wavelength_um_to_energy_ev


@dataclass(frozen=True)
class CriticalPoint:
    """One placeholder critical-point-like oscillator term.

    This class is a scaffold for fitting and later analytical Adachi-style terms. The
    generic contribution is not a complete Adachi critical-point expression.
    """

    name: str
    energy_eV: float
    amplitude: float
    gamma_eV: float
    phase: float = 0.0
    kind: str = "generic_lorentz"
    provenance: str = "placeholder"

    def contribution(self, energy_eV: float | np.ndarray) -> np.ndarray:
        """Return this term's placeholder contribution at photon energy in eV."""
        if self.kind not in {"generic_lorentz", "lorentz", "damped_oscillator"}:
            raise ValueError(f"Unsupported critical point kind: {self.kind}")

        energy = np.asarray(energy_eV, dtype=float)
        complex_amplitude = self.amplitude * np.exp(1j * self.phase)
        denominator = self.energy_eV**2 - energy**2 - 1j * self.gamma_eV * energy
        if np.any(np.isclose(denominator, 0.0)):
            raise ValueError(f"Energy is too close to critical point {self.name}")
        return complex_amplitude / denominator


class CriticalPointModel(BaseOpticalModel):
    """Base model for critical-point-like dielectric scaffolds."""

    material: str = "unknown"
    model: str = "CriticalPointModel"

    def __init__(
        self,
        *,
        eps_inf: complex,
        critical_points: list[CriticalPoint],
        wavelength_range_um: tuple[float, float] | None = None,
        energy_range_eV: tuple[float, float] | None = None,
        material: str = "unknown",
        model: str = "CriticalPointModel",
        implemented_terms: list[str] | None = None,
        source_notes: str = "",
    ) -> None:
        """Create a critical-point-like dielectric model.

        Parameters
        ----------
        eps_inf:
            Background dielectric constant, dimensionless.
        critical_points:
            Placeholder oscillator terms.
        wavelength_range_um:
            Optional inclusive validity range in microns.
        energy_range_eV:
            Optional inclusive validity range in electron volts.
        material:
            Material metadata.
        model:
            Model metadata.
        implemented_terms:
            Names of terms actually implemented in this scaffold.
        source_notes:
            Human-readable source and caveat notes.
        """
        self.eps_inf = complex(eps_inf)
        self.critical_points = critical_points
        self.wavelength_range_um = wavelength_range_um
        self.energy_range_eV = energy_range_eV
        self.material = material
        self.model = model
        self.implemented_terms = implemented_terms or ["eps_inf", "generic_lorentz"]
        self.source_notes = source_notes

    def epsilon(self, lambda_um: float | np.ndarray) -> np.ndarray:
        """Return complex dielectric function at wavelength in microns."""
        lambda_um_array = np.asarray(lambda_um, dtype=float)
        if not np.all(np.isfinite(lambda_um_array)):
            raise ValueError("lambda_um must contain only finite values")
        if self.wavelength_range_um is not None:
            lambda_um_array = ensure_within_range(
                lambda_um_array,
                minimum=self.wavelength_range_um[0],
                maximum=self.wavelength_range_um[1],
                name="lambda_um",
            )

        energy_eV = wavelength_um_to_energy_ev(lambda_um_array)
        if self.energy_range_eV is not None:
            ensure_within_range(
                energy_eV,
                minimum=self.energy_range_eV[0],
                maximum=self.energy_range_eV[1],
                name="energy_eV",
            )

        eps = np.full_like(energy_eV, self.eps_inf, dtype=complex)
        for critical_point in self.critical_points:
            eps = eps + critical_point.contribution(energy_eV)
        return eps
