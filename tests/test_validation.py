"""Tests for validation metrics, reports, and reference comparison plots."""

import json

import numpy as np
import pandas as pd
import pytest

from nkcalc.core.validation import (
    compare_tables,
    compute_error_metrics,
    load_lumerical_ge_crc_csv,
    save_validation_report,
)
from nkcalc.plotting.compare_reference import plot_model_vs_reference


def _reference_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "lambda_um": [1.0, 1.5, 2.0],
            "n": [4.0, 4.1, 4.2],
            "k": [0.01, 0.02, 0.04],
            "material": ["Ge", "Ge", "Ge"],
            "source": ["synthetic reference"] * 3,
            "temperature_K": [300.0, 300.0, 300.0],
            "notes": ["unit test fixture"] * 3,
        }
    )


def _model_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "lambda_um": [1.0, 1.5, 2.0],
            "n": [4.1, 4.0, 4.3],
            "k": [0.02, 0.01, 0.05],
            "material": ["Ge", "Ge", "Ge"],
            "model": ["synthetic"] * 3,
        }
    )


def test_compare_tables_requires_matching_grid_without_interpolation() -> None:
    """Grid alignment is explicit unless interpolation is requested."""
    reference = _reference_table()
    model = _model_table()
    model["lambda_um"] = [1.0, 1.25, 2.0]

    with pytest.raises(ValueError, match="interpolate=True"):
        compare_tables(model, reference)


def test_compare_tables_can_interpolate_reference_when_requested() -> None:
    """Reference data can be interpolated onto the model wavelength grid explicitly."""
    reference = _reference_table()
    model = _model_table()
    model["lambda_um"] = [1.0, 1.25, 2.0]

    comparison = compare_tables(model, reference, interpolate=True)

    assert comparison["lambda_um"].tolist() == [1.0, 1.25, 2.0]
    assert np.allclose(comparison["reference_n"], [4.0, 4.05, 4.2])
    assert "reference_source" in comparison.attrs["reference_metadata"]


def test_compare_tables_aligns_same_grid_when_rows_are_unordered() -> None:
    """Tables are aligned by lambda_um, not by original row position."""
    reference = _reference_table().iloc[[2, 0, 1]].reset_index(drop=True)
    model = _model_table().iloc[[1, 2, 0]].reset_index(drop=True)

    comparison = compare_tables(model, reference)

    assert comparison["lambda_um"].tolist() == [1.0, 1.5, 2.0]
    assert np.allclose(comparison["error_n"], [0.1, -0.1, 0.1])


def test_compute_error_metrics_includes_required_metrics_and_metadata() -> None:
    """Validation metrics include n/k/alpha errors and reference metadata."""
    metrics = compute_error_metrics(_model_table(), _reference_table(), k_weight=2.0)

    assert metrics["RMSE_n"] == pytest.approx(0.1)
    assert metrics["RMSE_k"] == pytest.approx(0.01)
    assert metrics["MAE_n"] == pytest.approx(0.1)
    assert metrics["MAE_k"] == pytest.approx(0.01)
    assert metrics["weighted_RMSE_k"] == pytest.approx(0.02)
    assert metrics["max_abs_error_n"] == pytest.approx(0.1)
    assert metrics["max_abs_error_k"] == pytest.approx(0.01)
    assert metrics["RMSE_log_alpha"] > 0.0
    assert metrics["reference_metadata"]["reference_source"] == "synthetic reference"
    assert metrics["reference_metadata"]["reference_temperature_K"] == 300.0


def test_save_validation_report_writes_json_and_csv(tmp_path) -> None:
    """Validation reports can be written as structured JSON or one-row CSV."""
    metrics = compute_error_metrics(_model_table(), _reference_table())
    json_path = tmp_path / "validation.json"
    csv_path = tmp_path / "validation.csv"

    save_validation_report(metrics, json_path)
    save_validation_report(metrics, csv_path)

    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded["RMSE_n"] == pytest.approx(0.1)
    csv_report = pd.read_csv(csv_path)
    assert csv_report.loc[0, "RMSE_k"] == pytest.approx(0.01)


def test_plot_model_vs_reference_saves_non_gui_figure(tmp_path) -> None:
    """Comparison plot is saved without requiring a GUI backend."""
    output = tmp_path / "comparison.png"

    fig = plot_model_vs_reference(_model_table(), _reference_table(), output)

    assert output.exists()
    assert output.stat().st_size > 0
    assert len(fig.axes) == 3


def test_load_lumerical_ge_crc_csv_maps_columns_and_metadata(tmp_path) -> None:
    """Lumerical CRC CSV loader uses explicit unit and column mapping."""
    path = tmp_path / "Ge CRC.csv"
    pd.DataFrame(
        {
            "wavelength(m)": [2.0e-6, 3.0e-6],
            " Re(n_xx)": [4.0, 4.1],
            " Im(n_xx)": [0.01, 0.02],
        }
    ).to_csv(path, index=False)

    table = load_lumerical_ge_crc_csv(path)

    assert np.allclose(table["lambda_um"], [2.0, 3.0])
    assert table["source"].tolist() == ["Lumerical standard Ge CRC"] * 2
    assert table["strain_state"].tolist() == ["unstrained", "unstrained"]
    assert table.attrs["source"] == "Lumerical standard Ge CRC"
