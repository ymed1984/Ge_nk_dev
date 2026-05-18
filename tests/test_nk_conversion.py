"""Tests for epsilon and n/k conversion helpers."""

import numpy as np

from nkcalc.core.nk import epsilon_to_nk, nk_to_epsilon


def test_nk_to_epsilon_formula() -> None:
    """epsilon equals (n + 1j*k)^2."""
    eps = nk_to_epsilon(np.array([4.0]), np.array([0.1]))
    assert np.allclose(eps.real, [15.99])
    assert np.allclose(eps.imag, [0.8])


def test_epsilon_nk_round_trip_absorbing_and_transparent() -> None:
    """n,k -> eps -> n,k round trips for passive transparent and absorbing cases."""
    n = np.array([1.0, 3.5, 4.2])
    k = np.array([0.0, 0.0, 0.35])
    eps = nk_to_epsilon(n, k)
    n_out, k_out = epsilon_to_nk(eps)
    assert np.allclose(n_out, n)
    assert np.allclose(k_out, k)


def test_epsilon_to_nk_selects_passive_branch() -> None:
    """The selected square-root branch has k >= 0 for passive media."""
    eps = np.array([4.0 + 0.0j, 15.99 + 0.8j])
    n, k = epsilon_to_nk(eps)
    assert np.all(n >= 0.0)
    assert np.all(k >= 0.0)
