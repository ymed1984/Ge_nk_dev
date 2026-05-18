"""Germanium optical model helpers."""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from nkcalc.models.base import BaseOpticalModel
from nkcalc.models.sellmeier import FreySellmeierModel
from nkcalc.models.tabulated import TabulatedModel

_DEFAULT_FREY_PARAMS = Path(__file__).resolve().parents[3] / "data" / "params" / "ge_frey_sellmeier.yml"
_DEFAULT_LUMERICAL_CRC = Path(__file__).resolve().parents[3] / "bgdata" / "Ge (Germanium) - CRC.csv"


@dataclass
class GeState:
    """State metadata for Ge optical models."""

    temperature_K: float | None = None
    strain_xx: float = 0.0
    strain_yy: float = 0.0
    strain_zz: float = 0.0
    electron_cm3: float = 0.0
    hole_cm3: float = 0.0
    strain_state: str = "unstrained"
    source: str | None = None
    reference: str | None = None
    extra: dict[str, object] = field(default_factory=dict)


class GeOpticalModel(BaseOpticalModel):
    """Facade over Ge optical model backends."""

    material: str = "Ge"

    def __init__(self, backend: BaseOpticalModel, state: GeState | dict[str, object] | None = None) -> None:
        """Create a Ge facade from a backend model.

        Parameters
        ----------
        backend:
            Backend implementing the ``BaseOpticalModel`` interface.
        state:
            Optional Ge state metadata. A plain dictionary is accepted for convenience.
        """
        self.backend = backend
        self.state = _coerce_state(state)
        self.model = getattr(backend, "model", "unknown")

    @classmethod
    def from_backend(
        cls,
        backend: BaseOpticalModel,
        state: GeState | dict[str, object] | None = None,
    ) -> "GeOpticalModel":
        """Create a Ge facade from an existing backend model."""
        return cls(backend, state=state)

    @classmethod
    def tabulated_from_csv(
        cls,
        path: str | Path,
        wavelength_unit: str = "um",
        *,
        state: GeState | dict[str, object] | None = None,
        source: str | None = None,
        reference: str | None = None,
    ) -> "GeOpticalModel":
        """Create a Ge facade from a user-provided n/k CSV.

        Parameters
        ----------
        path:
            CSV path containing wavelength, ``n``, and ``k`` columns.
        wavelength_unit:
            Wavelength unit hint passed to ``TabulatedModel``.
        state:
            Optional Ge state metadata.
        source:
            Optional source metadata.
        reference:
            Optional reference metadata.
        """
        backend = TabulatedModel.from_nk_csv(
            path,
            wavelength_unit=wavelength_unit,
            material="Ge",
            model="tabulated",
        )
        ge_state = _coerce_state(state)
        ge_state.source = source if source is not None else ge_state.source
        ge_state.reference = reference if reference is not None else ge_state.reference
        return cls.from_backend(backend, state=ge_state)

    @classmethod
    def frey_sellmeier(
        cls,
        temperature_K: float = 295.0,
        params_path: str | Path | None = None,
    ) -> "GeOpticalModel":
        """Create a Ge facade using the transparent-side Frey-style Sellmeier backend."""
        backend = ge_frey_sellmeier(temperature_K=temperature_K, params_path=params_path)
        return cls.from_backend(
            backend,
            state=GeState(
                temperature_K=temperature_K,
                source=getattr(backend, "source", None),
                reference=getattr(backend, "coefficient_provenance", None),
            ),
        )

    @classmethod
    def lumerical_crc_from_csv(
        cls,
        path: str | Path = _DEFAULT_LUMERICAL_CRC,
    ) -> "GeOpticalModel":
        """Create a Ge facade from local Lumerical/CRC unstrained benchmark CSV.

        The CSV is expected to contain ``wavelength(m)``, ``Re(n_xx)``, and ``Im(n_xx)``.
        The data are treated as local reference data, not model coefficients.
        """
        csv_path = Path(path)
        df = pd.read_csv(csv_path)
        df = df.rename(columns=lambda column: str(column).strip())
        required = ["wavelength(m)", "Re(n_xx)", "Im(n_xx)"]
        missing = [column for column in required if column not in df.columns]
        if missing:
            raise ValueError(f"Missing required Lumerical CRC column(s): {', '.join(missing)}")

        converted = pd.DataFrame(
            {
                "lambda_um": df["wavelength(m)"].to_numpy(dtype=float) * 1.0e6,
                "n": df["Re(n_xx)"].to_numpy(dtype=float),
                "k": df["Im(n_xx)"].to_numpy(dtype=float),
            }
        )
        backend = TabulatedModel(
            converted["lambda_um"].to_numpy(),
            converted["n"].to_numpy(),
            converted["k"].to_numpy(),
            "nk",
            material="Ge",
            model="LumericalCRC",
        )
        return cls.from_backend(
            backend,
            state=GeState(
                strain_state="unstrained",
                source="Lumerical standard Ge CRC",
                reference=str(csv_path),
            ),
        )

    def epsilon(self, lambda_um: float | np.ndarray) -> np.ndarray:
        """Return complex dielectric function at wavelength in microns."""
        return self.backend.epsilon(lambda_um)

    def nk(self, lambda_um: float | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return refractive index n and extinction coefficient k."""
        return self.backend.nk(lambda_um)

    def table(self, lambda_um: float | np.ndarray) -> pd.DataFrame:
        """Return a Ge optical table with state metadata columns."""
        table = self.backend.table(lambda_um)
        table["material"] = "Ge"
        table["model"] = self.model
        table["temperature_K"] = self.state.temperature_K
        table["strain_xx"] = self.state.strain_xx
        table["strain_yy"] = self.state.strain_yy
        table["strain_zz"] = self.state.strain_zz
        table["electron_cm3"] = self.state.electron_cm3
        table["hole_cm3"] = self.state.hole_cm3
        table["strain_state"] = self.state.strain_state
        table["source"] = self.state.source
        table["reference"] = self.state.reference
        for key, value in self.state.extra.items():
            table[key] = value
        return table


def ge_frey_sellmeier(
    temperature_K: float = 295.0,
    params_path: str | Path | None = None,
) -> FreySellmeierModel:
    """Return a Ge transparent-side Frey-style Sellmeier model.

    Parameters
    ----------
    temperature_K:
        Temperature in kelvin.
    params_path:
        Optional YAML parameter path. If omitted, the bundled placeholder YAML schema is used.

    Returns
    -------
    FreySellmeierModel
        Loaded Ge Sellmeier model.
    """
    path = Path(params_path) if params_path is not None else _DEFAULT_FREY_PARAMS
    return FreySellmeierModel.from_yaml(path, temperature_K=temperature_K)


def _coerce_state(state: GeState | dict[str, object] | None) -> GeState:
    """Return GeState from optional user state metadata."""
    if state is None:
        return GeState()
    if isinstance(state, GeState):
        return state

    known_fields = {
        "temperature_K",
        "strain_xx",
        "strain_yy",
        "strain_zz",
        "electron_cm3",
        "hole_cm3",
        "strain_state",
        "source",
        "reference",
    }
    kwargs = {key: value for key, value in state.items() if key in known_fields}
    extra = {key: value for key, value in state.items() if key not in known_fields}
    return GeState(**kwargs, extra=extra)
