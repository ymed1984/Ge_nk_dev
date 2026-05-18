"""Tabulated optical model with no implicit extrapolation."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator

from nkcalc.core.nk import epsilon_to_nk, nk_to_epsilon
from nkcalc.core.validation import ensure_within_range
from nkcalc.io.csv_io import ensure_required_columns
from nkcalc.models.base import BaseOpticalModel

_WAVELENGTH_COLUMNS = ("lambda_um", "wavelength_um", "lambda_nm", "wavelength_nm")


@dataclass
class TabulatedModel(BaseOpticalModel):
    """Optical model backed by user-provided tabulated n/k or epsilon data."""

    lambda_um_data: np.ndarray
    first_data: np.ndarray
    second_data: np.ndarray
    data_kind: Literal["nk", "eps"]
    material: str = "unknown"
    model: str = "tabulated"

    def __post_init__(self) -> None:
        """Validate and prepare monotonic interpolation data."""
        lambda_um = np.asarray(self.lambda_um_data, dtype=float)
        first = np.asarray(self.first_data, dtype=float)
        second = np.asarray(self.second_data, dtype=float)

        if not (lambda_um.shape == first.shape == second.shape):
            raise ValueError("tabulated arrays must have identical shapes")
        if lambda_um.ndim != 1:
            raise ValueError("tabulated arrays must be one-dimensional")
        if len(lambda_um) < 2:
            raise ValueError("at least two tabulated wavelength points are required")
        if not np.all(np.isfinite(lambda_um)) or not np.all(np.isfinite(first + second)):
            raise ValueError("tabulated data must contain only finite values")

        order = np.argsort(lambda_um)
        self.lambda_um_data = lambda_um[order]
        self.first_data = first[order]
        self.second_data = second[order]

        if np.any(np.diff(self.lambda_um_data) <= 0.0):
            raise ValueError("tabulated wavelengths must be unique")
        if self.data_kind not in {"nk", "eps"}:
            raise ValueError('data_kind must be "nk" or "eps"')

        self._first_interp = PchipInterpolator(self.lambda_um_data, self.first_data, extrapolate=False)
        self._second_interp = PchipInterpolator(
            self.lambda_um_data,
            self.second_data,
            extrapolate=False,
        )

    @classmethod
    def from_nk_csv(
        cls,
        path: str | Path,
        wavelength_unit: str = "um",
        material: str = "unknown",
        model: str = "tabulated",
    ) -> "TabulatedModel":
        """Build a tabulated model from a CSV containing wavelength, n, and k.

        Parameters
        ----------
        path:
            CSV path.
        wavelength_unit:
            Expected wavelength unit for compatibility with future ambiguous schemas. Current
            accepted wavelength column names are explicit: ``lambda_um``, ``wavelength_um``,
            ``lambda_nm``, or ``wavelength_nm``.
        material:
            Material metadata.
        model:
            Model metadata.

        Returns
        -------
        TabulatedModel
            Model interpolating tabulated ``n`` and ``k`` data.
        """
        _validate_wavelength_unit(wavelength_unit)
        df = pd.read_csv(path)
        lambda_um = _extract_lambda_um(df)
        ensure_required_columns(df, ["n", "k"])
        return cls(
            lambda_um,
            df["n"].to_numpy(dtype=float),
            df["k"].to_numpy(dtype=float),
            "nk",
            material,
            model,
        )

    @classmethod
    def from_eps_csv(
        cls,
        path: str | Path,
        wavelength_unit: str = "um",
        material: str = "unknown",
        model: str = "tabulated",
    ) -> "TabulatedModel":
        """Build a tabulated model from a CSV containing wavelength, eps1, and eps2.

        Parameters
        ----------
        path:
            CSV path.
        wavelength_unit:
            Expected wavelength unit for compatibility with future ambiguous schemas. Current
            accepted wavelength column names are explicit: ``lambda_um``, ``wavelength_um``,
            ``lambda_nm``, or ``wavelength_nm``.
        material:
            Material metadata.
        model:
            Model metadata.

        Returns
        -------
        TabulatedModel
            Model interpolating tabulated ``eps1`` and ``eps2`` data.
        """
        _validate_wavelength_unit(wavelength_unit)
        df = pd.read_csv(path)
        lambda_um = _extract_lambda_um(df)
        ensure_required_columns(df, ["eps1", "eps2"])
        return cls(
            lambda_um,
            df["eps1"].to_numpy(dtype=float),
            df["eps2"].to_numpy(dtype=float),
            "eps",
            material,
            model,
        )

    def epsilon(self, lambda_um: float | np.ndarray) -> np.ndarray:
        """Return complex dielectric function for wavelength in microns.

        Parameters
        ----------
        lambda_um:
            Wavelength in microns. Values outside the tabulated range raise ``ValueError``.

        Returns
        -------
        numpy.ndarray
            Complex dielectric function.
        """
        lambda_um_array = self._validate_lambda_um(lambda_um)
        first = self._first_interp(lambda_um_array)
        second = self._second_interp(lambda_um_array)
        if self.data_kind == "eps":
            return first + 1j * second
        return nk_to_epsilon(first, second)

    def nk(self, lambda_um: float | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return n and k for wavelength in microns.

        For models loaded from n/k CSV, n and k are interpolated directly. For models loaded
        from epsilon CSV, n and k are derived from interpolated epsilon.
        """
        lambda_um_array = self._validate_lambda_um(lambda_um)
        first = self._first_interp(lambda_um_array)
        second = self._second_interp(lambda_um_array)
        if self.data_kind == "nk":
            return first, second
        return epsilon_to_nk(first + 1j * second)

    def _validate_lambda_um(self, lambda_um: float | np.ndarray) -> np.ndarray:
        """Validate wavelength in microns against this model's tabulated range."""
        return ensure_within_range(
            lambda_um,
            minimum=float(self.lambda_um_data[0]),
            maximum=float(self.lambda_um_data[-1]),
            name="lambda_um",
        )


def _validate_wavelength_unit(wavelength_unit: str) -> None:
    """Validate accepted wavelength unit names."""
    if wavelength_unit not in {"um", "nm"}:
        raise ValueError('wavelength_unit must be "um" or "nm"')


def _extract_lambda_um(df: pd.DataFrame) -> np.ndarray:
    """Extract an unambiguous wavelength column and return wavelength in microns."""
    present = [column for column in _WAVELENGTH_COLUMNS if column in df.columns]
    if not present:
        expected = ", ".join(_WAVELENGTH_COLUMNS)
        raise ValueError(f"CSV must contain one wavelength column: {expected}")
    if len(present) > 1:
        present_text = ", ".join(present)
        raise ValueError(f"CSV has ambiguous wavelength columns: {present_text}")

    column = present[0]
    values = df[column].to_numpy(dtype=float)
    if column.endswith("_nm"):
        return values / 1000.0
    return values
