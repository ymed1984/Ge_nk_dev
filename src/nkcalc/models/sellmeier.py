"""Sellmeier optical models."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from nkcalc.core.validation import ensure_within_range
from nkcalc.models.base import BaseOpticalModel


@dataclass(frozen=True)
class SellmeierTerm:
    """One temperature-dependent Sellmeier term."""

    strength_coefficients: tuple[float, ...]
    resonance_um_coefficients: tuple[float, ...]

    def strength(self, temperature_K: float) -> float:
        """Return dimensionless oscillator strength at temperature in kelvin."""
        return _evaluate_polynomial(self.strength_coefficients, temperature_K)

    def resonance_um(self, temperature_K: float) -> float:
        """Return resonance wavelength in microns at temperature in kelvin."""
        return _evaluate_polynomial(self.resonance_um_coefficients, temperature_K)


class FreySellmeierModel(BaseOpticalModel):
    """Temperature-dependent transparent-side Sellmeier model.

    The model evaluates
    ``n(lambda,T)^2 - 1 = sum_i S_i(T) lambda^2 / (lambda^2 - lambda_i(T)^2)``,
    with wavelength in microns and temperature in kelvin.
    """

    material: str = "Ge"
    model: str = "FreySellmeier"

    def __init__(
        self,
        terms: list[SellmeierTerm],
        *,
        temperature_K: float,
        wavelength_range_um: tuple[float, float] = (1.9, 5.5),
        temperature_range_K: tuple[float, float] = (20.0, 300.0),
        material: str = "Ge",
        model: str = "FreySellmeier",
        coefficient_provenance: str = "placeholder",
        source: str = "user-provided-or-placeholder",
    ) -> None:
        """Initialize a Frey-style Sellmeier model.

        Parameters
        ----------
        terms:
            Sellmeier terms with polynomial coefficients in ascending powers of
            temperature_K.
        temperature_K:
            Temperature in kelvin.
        wavelength_range_um:
            Inclusive validity range for wavelength in microns.
        temperature_range_K:
            Inclusive validity range for temperature in kelvin.
        material:
            Material metadata.
        model:
            Model metadata.
        coefficient_provenance:
            Provenance label such as ``placeholder``, ``synthetic``, ``user_provided``, or
            ``literature_checked``.
        source:
            Human-readable source note for the coefficients.
        """
        if not terms:
            raise ValueError("FreySellmeierModel requires at least one Sellmeier term")

        self.terms = terms
        self.temperature_range_K = temperature_range_K
        self.wavelength_range_um = wavelength_range_um
        self.temperature_K = float(
            ensure_within_range(
                temperature_K,
                minimum=temperature_range_K[0],
                maximum=temperature_range_K[1],
                name="temperature_K",
            )
        )
        self.material = material
        self.model = model
        self.coefficient_provenance = coefficient_provenance
        self.source = source

    @classmethod
    def from_yaml(
        cls,
        path: str | Path,
        *,
        temperature_K: float | None = None,
    ) -> "FreySellmeierModel":
        """Load a temperature-dependent Sellmeier model from YAML.

        Parameters
        ----------
        path:
            YAML parameter path.
        temperature_K:
            Optional temperature in kelvin. If omitted, ``default_temperature_K`` from the
            YAML file is used.

        Returns
        -------
        FreySellmeierModel
            Loaded model instance.
        """
        with Path(path).open(encoding="utf-8") as stream:
            params = yaml.safe_load(stream)

        if not isinstance(params, dict):
            raise ValueError("Sellmeier YAML must contain a mapping")

        terms = [
            SellmeierTerm(
                strength_coefficients=tuple(term["strength_coefficients"]),
                resonance_um_coefficients=tuple(term["resonance_um_coefficients"]),
            )
            for term in params["terms"]
        ]
        validity = params.get("validity", {})
        wavelength_range_um = tuple(validity.get("wavelength_um", [1.9, 5.5]))
        temperature_range_K = tuple(validity.get("temperature_K", [20.0, 300.0]))
        selected_temperature_K = temperature_K
        if selected_temperature_K is None:
            selected_temperature_K = params.get("default_temperature_K")
        if selected_temperature_K is None:
            raise ValueError("temperature_K must be provided or default_temperature_K set")

        return cls(
            terms,
            temperature_K=selected_temperature_K,
            wavelength_range_um=(float(wavelength_range_um[0]), float(wavelength_range_um[1])),
            temperature_range_K=(float(temperature_range_K[0]), float(temperature_range_K[1])),
            material=params.get("material", "Ge"),
            model=params.get("model", "FreySellmeier"),
            coefficient_provenance=params.get("coefficient_provenance", "placeholder"),
            source=params.get("source", "user-provided-or-placeholder"),
        )

    def epsilon(self, lambda_um: float | np.ndarray) -> np.ndarray:
        """Return complex dielectric function at wavelength in microns.

        This transparent-side Sellmeier model returns real epsilon with ``k = 0``. Values
        outside the configured wavelength validity range raise ``ValueError``.
        """
        lambda_um_array = ensure_within_range(
            lambda_um,
            minimum=self.wavelength_range_um[0],
            maximum=self.wavelength_range_um[1],
            name="lambda_um",
        )
        lambda_um_squared = lambda_um_array**2
        n_squared = np.ones_like(lambda_um_array, dtype=float)

        for term in self.terms:
            resonance_um = term.resonance_um(self.temperature_K)
            denominator = lambda_um_squared - resonance_um**2
            if np.any(np.isclose(denominator, 0.0)):
                raise ValueError("lambda_um is too close to a Sellmeier resonance")
            n_squared = n_squared + term.strength(self.temperature_K) * lambda_um_squared / denominator

        if np.any(n_squared < 0.0):
            raise ValueError("Sellmeier model produced negative n^2")
        return n_squared.astype(complex)


def _evaluate_polynomial(coefficients: tuple[float, ...], temperature_K: float) -> float:
    """Evaluate coefficients in ascending powers of temperature_K."""
    total = 0.0
    for power, coefficient in enumerate(coefficients):
        total += float(coefficient) * temperature_K**power
    return total
