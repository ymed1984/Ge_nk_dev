"""Tests for extinction coefficient and absorption coefficient conversions."""

import numpy as np

from nkcalc.core.nk import alpha_cm_inv_to_k, k_to_alpha_cm_inv, k_to_alpha_m_inv


def test_k_to_alpha_m_inv_formula() -> None:
    """alpha_m_inv = 4*pi*k/lambda_m."""
    k = np.array([0.1])
    lambda_um = np.array([1.0])
    expected = 4.0 * np.pi * 0.1 / 1.0e-6
    assert np.allclose(k_to_alpha_m_inv(k, lambda_um), expected)


def test_k_to_alpha_cm_inv_formula() -> None:
    """alpha_cm_inv is alpha_m_inv divided by 100."""
    k = np.array([0.1])
    lambda_um = np.array([1.0])
    assert np.allclose(k_to_alpha_cm_inv(k, lambda_um), k_to_alpha_m_inv(k, lambda_um) / 100.0)


def test_alpha_cm_inv_to_k_round_trip() -> None:
    """k -> alpha_cm_inv -> k round trips."""
    k = np.array([0.0, 1.0e-4, 0.1, 0.5])
    lambda_um = np.array([1.31, 1.55, 2.0, 5.5])
    alpha_cm_inv = k_to_alpha_cm_inv(k, lambda_um)
    assert np.allclose(alpha_cm_inv_to_k(alpha_cm_inv, lambda_um), k)
