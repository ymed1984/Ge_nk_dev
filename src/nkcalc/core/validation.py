"""Validation helpers shared by optical models."""

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from nkcalc.core.nk import k_to_alpha_cm_inv
from nkcalc.io.csv_io import ensure_required_columns
from nkcalc.spectrum import wavelength_um_to_energy_ev

_METADATA_COLUMNS = [
    "material",
    "source",
    "reference",
    "temperature_K",
    "strain_state",
    "wavelength_range_um",
    "energy_range_eV",
    "notes",
]
_DEFAULT_LUMERICAL_GE_CRC = (
    Path(__file__).resolve().parents[3] / "bgdata" / "Ge (Germanium) - CRC.csv"
)


def ensure_within_range(
    values: float | np.ndarray,
    *,
    minimum: float,
    maximum: float,
    name: str,
) -> np.ndarray:
    """Return numeric values after checking they are finite and within range.

    Parameters
    ----------
    values:
        Numeric values to validate.
    minimum:
        Inclusive lower bound in the same units as ``values``.
    maximum:
        Inclusive upper bound in the same units as ``values``.
    name:
        Name used in error messages, including units where helpful.

    Returns
    -------
    numpy.ndarray
        Values converted to a float array.

    Raises
    ------
    ValueError
        If values are not finite or fall outside ``[minimum, maximum]``.
    """
    array = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    if np.any((array < minimum) | (array > maximum)):
        raise ValueError(f"{name} must be within [{minimum}, {maximum}]")
    return array


def compare_tables(
    model_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    *,
    interpolate: bool = False,
) -> pd.DataFrame:
    """Compare model and reference optical tables on wavelength in microns.

    Parameters
    ----------
    model_df:
        Model table with ``lambda_um``, ``n``, and ``k`` columns.
    reference_df:
        Reference table with ``lambda_um``, ``n``, and ``k`` columns.
    interpolate:
        If ``True``, interpolate the reference table onto the model ``lambda_um`` grid.
        If ``False``, both tables must already share the same grid.

    Returns
    -------
    pandas.DataFrame
        Aligned comparison table containing model/reference values and signed/absolute
        errors for ``n``, ``k``, and ``alpha_cm_inv``.
    """
    model = _sort_by_lambda(_prepare_validation_table(model_df, table_name="model_df"))
    reference = _sort_by_lambda(_prepare_validation_table(reference_df, table_name="reference_df"))

    if interpolate:
        reference = _interpolate_reference_to_model_grid(model, reference)
    elif not _same_lambda_grid(model["lambda_um"], reference["lambda_um"]):
        raise ValueError("lambda_um grids differ; pass interpolate=True to align reference data")

    comparison = pd.DataFrame(
        {
            "lambda_um": model["lambda_um"].to_numpy(dtype=float),
            "model_n": model["n"].to_numpy(dtype=float),
            "reference_n": reference["n"].to_numpy(dtype=float),
            "model_k": model["k"].to_numpy(dtype=float),
            "reference_k": reference["k"].to_numpy(dtype=float),
            "model_alpha_cm_inv": model["alpha_cm_inv"].to_numpy(dtype=float),
            "reference_alpha_cm_inv": reference["alpha_cm_inv"].to_numpy(dtype=float),
        }
    )
    comparison["error_n"] = comparison["model_n"] - comparison["reference_n"]
    comparison["error_k"] = comparison["model_k"] - comparison["reference_k"]
    comparison["error_alpha_cm_inv"] = (
        comparison["model_alpha_cm_inv"] - comparison["reference_alpha_cm_inv"]
    )
    comparison["abs_error_n"] = np.abs(comparison["error_n"])
    comparison["abs_error_k"] = np.abs(comparison["error_k"])
    comparison["abs_error_alpha_cm_inv"] = np.abs(comparison["error_alpha_cm_inv"])
    comparison.attrs["reference_metadata"] = _collect_metadata(reference_df, prefix="reference")
    comparison.attrs["model_metadata"] = _collect_metadata(model_df, prefix="model")
    return comparison


def compute_error_metrics(
    model_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    *,
    interpolate: bool = False,
    k_weight: float = 1.0,
    alpha_weight: float = 1.0,
) -> dict[str, Any]:
    """Compute validation metrics between model and reference tables.

    Parameters
    ----------
    model_df:
        Model table with ``lambda_um``, ``n``, and ``k`` columns.
    reference_df:
        Reference table with ``lambda_um``, ``n``, and ``k`` columns.
    interpolate:
        If ``True``, interpolate reference data onto the model wavelength grid.
    k_weight:
        Transparent scalar multiplier for the reported weighted ``k`` RMSE.
    alpha_weight:
        Transparent scalar multiplier for the reported weighted log-alpha RMSE.

    Returns
    -------
    dict
        Error metrics plus model/reference metadata useful for validation reports.
    """
    comparison = compare_tables(model_df, reference_df, interpolate=interpolate)
    err_n = comparison["error_n"].to_numpy(dtype=float)
    err_k = comparison["error_k"].to_numpy(dtype=float)
    model_alpha = comparison["model_alpha_cm_inv"].to_numpy(dtype=float)
    reference_alpha = comparison["reference_alpha_cm_inv"].to_numpy(dtype=float)
    alpha_mask = (model_alpha > 0.0) & (reference_alpha > 0.0)

    rmse_log_alpha = math.nan
    if np.any(alpha_mask):
        log_error = np.log10(model_alpha[alpha_mask]) - np.log10(reference_alpha[alpha_mask])
        rmse_log_alpha = _rmse(log_error)

    metrics: dict[str, Any] = {
        "RMSE_n": _rmse(err_n),
        "RMSE_k": _rmse(err_k),
        "MAE_n": float(np.mean(np.abs(err_n))),
        "MAE_k": float(np.mean(np.abs(err_k))),
        "weighted_RMSE_k": float(k_weight * _rmse(err_k)),
        "RMSE_log_alpha": rmse_log_alpha,
        "weighted_RMSE_log_alpha": (
            float(alpha_weight * rmse_log_alpha) if not math.isnan(rmse_log_alpha) else math.nan
        ),
        "max_abs_error_n": float(np.max(np.abs(err_n))),
        "max_abs_error_k": float(np.max(np.abs(err_k))),
        "k_weight": float(k_weight),
        "alpha_weight": float(alpha_weight),
        "num_points": int(len(comparison)),
        "wavelength_range_um": [
            float(comparison["lambda_um"].min()),
            float(comparison["lambda_um"].max()),
        ],
        "energy_range_eV": [
            float(wavelength_um_to_energy_ev(comparison["lambda_um"].max())),
            float(wavelength_um_to_energy_ev(comparison["lambda_um"].min())),
        ],
        "reference_metadata": comparison.attrs.get("reference_metadata", {}),
        "model_metadata": comparison.attrs.get("model_metadata", {}),
    }
    return metrics


def save_validation_report(metrics: dict[str, Any], path: str | Path) -> None:
    """Save validation metrics to JSON or one-row CSV.

    Parameters
    ----------
    metrics:
        Metrics dictionary returned by ``compute_error_metrics``.
    path:
        Output path. ``.json`` writes structured JSON; any other suffix writes CSV with
        nested metadata serialized as JSON strings.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".json":
        output_path.write_text(json.dumps(_json_ready(metrics), indent=2) + "\n", encoding="utf-8")
        return

    flat_metrics = {
        key: json.dumps(value) if isinstance(value, (dict, list, tuple)) else value
        for key, value in _json_ready(metrics).items()
    }
    pd.DataFrame([flat_metrics]).to_csv(output_path, index=False)


def load_lumerical_ge_crc_csv(path: str | Path = _DEFAULT_LUMERICAL_GE_CRC) -> pd.DataFrame:
    """Load local Lumerical standard Ge CRC n/k data as a reference table.

    Parameters
    ----------
    path:
        User/local CSV path with ``wavelength(m)``, ``Re(n_xx)``, and ``Im(n_xx)`` columns.

    Returns
    -------
    pandas.DataFrame
        Reference table with ``lambda_um``, ``n``, ``k``, ``alpha_cm_inv``, and metadata
        columns. The data are treated as benchmark data, not model coefficients.
    """
    csv_path = Path(path)
    raw = pd.read_csv(csv_path).rename(columns=lambda column: str(column).strip())
    ensure_required_columns(raw, ["wavelength(m)", "Re(n_xx)", "Im(n_xx)"])

    lambda_um = raw["wavelength(m)"].to_numpy(dtype=float) * 1.0e6
    n = raw["Re(n_xx)"].to_numpy(dtype=float)
    k = raw["Im(n_xx)"].to_numpy(dtype=float)
    _ensure_finite_columns(
        pd.DataFrame({"lambda_um": lambda_um, "n": n, "k": k}),
        ["lambda_um", "n", "k"],
        table_name="Lumerical Ge CRC CSV",
    )

    table = pd.DataFrame(
        {
            "lambda_um": lambda_um,
            "energy_eV": wavelength_um_to_energy_ev(lambda_um),
            "n": n,
            "k": k,
            "alpha_cm_inv": k_to_alpha_cm_inv(k, lambda_um),
            "material": "Ge",
            "model": "LumericalCRC",
            "source": "Lumerical standard Ge CRC",
            "strain_state": "unstrained",
            "reference": str(csv_path),
            "notes": "Local user-provided Lumerical/CRC benchmark data; not model coefficients.",
        }
    )
    table.attrs["source"] = "Lumerical standard Ge CRC"
    table.attrs["strain_state"] = "unstrained"
    table.attrs["reference"] = str(csv_path)
    return table


def _prepare_validation_table(df: pd.DataFrame, *, table_name: str) -> pd.DataFrame:
    ensure_required_columns(df, ["lambda_um", "n", "k"])
    prepared = df.copy()
    if "alpha_cm_inv" not in prepared.columns:
        prepared["alpha_cm_inv"] = k_to_alpha_cm_inv(prepared["k"], prepared["lambda_um"])
    _ensure_finite_columns(prepared, ["lambda_um", "n", "k", "alpha_cm_inv"], table_name=table_name)
    return prepared


def _sort_by_lambda(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values("lambda_um").reset_index(drop=True)


def _same_lambda_grid(model_lambda: pd.Series, reference_lambda: pd.Series) -> bool:
    if len(model_lambda) != len(reference_lambda):
        return False
    return bool(np.allclose(model_lambda.to_numpy(dtype=float), reference_lambda.to_numpy(dtype=float)))


def _interpolate_reference_to_model_grid(
    model: pd.DataFrame,
    reference: pd.DataFrame,
) -> pd.DataFrame:
    sorted_reference = reference.sort_values("lambda_um")
    reference_lambda = sorted_reference["lambda_um"].to_numpy(dtype=float)
    model_lambda = model["lambda_um"].to_numpy(dtype=float)
    if np.any(np.diff(reference_lambda) <= 0.0):
        raise ValueError("reference_df lambda_um values must be strictly increasing for interpolation")
    if model_lambda.min() < reference_lambda.min() or model_lambda.max() > reference_lambda.max():
        raise ValueError("model_df lambda_um grid extends outside reference range")

    aligned = pd.DataFrame({"lambda_um": model_lambda})
    for column in ["n", "k", "alpha_cm_inv"]:
        aligned[column] = np.interp(
            model_lambda,
            reference_lambda,
            sorted_reference[column].to_numpy(dtype=float),
        )
    return aligned


def _ensure_finite_columns(df: pd.DataFrame, columns: list[str], *, table_name: str) -> None:
    for column in columns:
        values = df[column].to_numpy(dtype=float)
        if not np.all(np.isfinite(values)):
            raise ValueError(f"{table_name} column {column!r} must contain only finite values")


def _collect_metadata(df: pd.DataFrame, *, prefix: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for key in _METADATA_COLUMNS:
        if key in df.attrs:
            metadata[key] = df.attrs[key]
        elif key in df.columns:
            metadata[key] = _first_non_null(df[key])

    if "lambda_um" in df.columns and "wavelength_range_um" not in metadata:
        wavelength = df["lambda_um"].to_numpy(dtype=float)
        metadata["wavelength_range_um"] = [float(np.min(wavelength)), float(np.max(wavelength))]
    if "lambda_um" in df.columns and "energy_range_eV" not in metadata:
        wavelength = df["lambda_um"].to_numpy(dtype=float)
        metadata["energy_range_eV"] = [
            float(wavelength_um_to_energy_ev(np.max(wavelength))),
            float(wavelength_um_to_energy_ev(np.min(wavelength))),
        ]

    return {f"{prefix}_{key}": value for key, value in metadata.items()}


def _first_non_null(series: pd.Series) -> Any:
    non_null = series.dropna()
    if non_null.empty:
        return None
    value = non_null.iloc[0]
    if isinstance(value, np.generic):
        return value.item()
    return value


def _rmse(values: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(values))))


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_json_ready(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value
