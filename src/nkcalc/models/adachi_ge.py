"""Ge critical-point scaffold inspired by Adachi-style modeling."""

from pathlib import Path

import yaml

from nkcalc.models.critical_point import CriticalPoint, CriticalPointModel


class AdachiGeModel(CriticalPointModel):
    """Ge critical-point dielectric scaffold.

    This is not a full Adachi implementation. It currently loads placeholder/generic
    oscillator terms from YAML so later analytical terms can be added and tested.
    """

    def __init__(
        self,
        *,
        eps_inf: complex,
        critical_points: list[CriticalPoint],
        wavelength_range_um: tuple[float, float] | None = None,
        energy_range_eV: tuple[float, float] | None = None,
        implemented_terms: list[str] | None = None,
        source_notes: str = "",
    ) -> None:
        """Create a Ge critical-point scaffold."""
        super().__init__(
            eps_inf=eps_inf,
            critical_points=critical_points,
            wavelength_range_um=wavelength_range_um,
            energy_range_eV=energy_range_eV,
            material="Ge",
            model="AdachiGeSkeleton",
            implemented_terms=implemented_terms,
            source_notes=source_notes,
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AdachiGeModel":
        """Load a Ge critical-point scaffold from YAML."""
        with Path(path).open(encoding="utf-8") as stream:
            params = yaml.safe_load(stream)

        if not isinstance(params, dict):
            raise ValueError("Adachi Ge YAML must contain a mapping")

        validity = params.get("validity", {})
        wavelength_range_um = _optional_range(validity.get("wavelength_um"))
        energy_range_eV = _optional_range(validity.get("energy_eV"))
        critical_points = [
            CriticalPoint(
                name=item["name"],
                energy_eV=float(item["energy_eV"]),
                amplitude=float(item["amplitude"]),
                gamma_eV=float(item["gamma_eV"]),
                phase=float(item.get("phase", 0.0)),
                kind=item.get("kind", "generic_lorentz"),
                provenance=item.get("provenance", "placeholder"),
            )
            for item in params.get("critical_points", [])
        ]

        return cls(
            eps_inf=complex(params.get("eps_inf", 1.0)),
            critical_points=critical_points,
            wavelength_range_um=wavelength_range_um,
            energy_range_eV=energy_range_eV,
            implemented_terms=list(params.get("implemented_terms", ["eps_inf", "generic_lorentz"])),
            source_notes=params.get("source_notes", ""),
        )


def _optional_range(values: list[float] | tuple[float, float] | None) -> tuple[float, float] | None:
    """Return optional numeric inclusive range."""
    if values is None:
        return None
    if len(values) != 2:
        raise ValueError("validity ranges must contain exactly two values")
    return float(values[0]), float(values[1])
