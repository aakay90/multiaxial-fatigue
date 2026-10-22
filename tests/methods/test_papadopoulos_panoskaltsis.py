"""Papadopoulos & Panoskaltsis (1996) gradient kernel (roadmap G29): Eng Fract Mech 55:513-528,
doi:10.1016/S0013-7944(96)00047-1 (Zotero 8USVNF2C); Eqs. (11)-(37) pp.520-527 (crops
_audit-trail/phase2/crops/8USVNF2C/p9_*, p10_*, p11_*, p13_*). The paper has no tables; its closed
forms are the oracles: constant-moment bending Eqs. (20)-(24), cantilever Eqs. (25)-(28), combined
bending-torsion Eqs. (31)-(37) (the f-t ellipse) and tension-torsion Eq. (30) (no gradient).
"""

import numpy as np
import pytest

from multifat.models.invariant_methods.papadopoulos_panoskaltsis import pp_beta, pp_index

S, T, N = 300.0, 200.0, 0.5
R0, F = 5.0, 360.0  # bending limit at radius R0 defines beta (Eq. 23)
BETA = pp_beta(S, T, F, R0, N)
KAPPA = BETA * (1 - S / (np.sqrt(3) * T))
Z = np.zeros((3, 3))


def _bt(s, t):
    return np.array([[s, t, 0.0], [t, 0.0, 0.0], [0.0, 0.0, 0.0]])


def test_calibration_tension_torsion_no_gradient():
    assert pp_index(Z, _bt(S, 0.0), 0.0, S, T, BETA, N) == pytest.approx(1.0, rel=1e-12)
    assert pp_index(Z, _bt(0.0, T), 0.0, S, T, BETA, N) == pytest.approx(1.0, rel=1e-12)


@pytest.mark.parametrize("R", [2.0, 5.0, 12.0, 30.0])
def test_eq24_constant_moment_bending(R):
    f = S / (1 - KAPPA / R**N)
    assert pp_index(Z, _bt(f, 0.0), f / (3 * R), S, T, BETA, N) == pytest.approx(1.0, rel=1e-12)


@pytest.mark.parametrize("R,L", [(3.0, 20.0), (5.0, 8.0), (10.0, 10.0)])
def test_eq28_cantilever(R, L):
    f = S / (1 - KAPPA / R**N * (1 + R**2 / L**2) ** (N / 2))
    G = f / 3 * np.sqrt(1 / L**2 + 1 / R**2)  # Eq. (27)
    assert pp_index(Z, _bt(f, 0.0), G, S, T, BETA, N) == pytest.approx(1.0, rel=1e-12)


@pytest.mark.parametrize("ratio", [0.2, 0.5, 0.8])
def test_eqs_31_37_bending_torsion_follows_f_t_ellipse(ratio):
    """At the surface of the bent and twisted bar of radius R0, G = sigma_a/(3 R0) (Eq. 33), and
    Eq. (17) with beta from Eq. (23) reproduces the f-t ellipse arc Eq. (31)."""
    sigma = ratio * F
    a, b = 2 * F / (np.sqrt(3) * T) - 1, 2 - 2 * F / (np.sqrt(3) * T)
    tau = T * np.sqrt(1 - a * ratio**2 - b * ratio)
    assert pp_index(Z, _bt(sigma, tau), sigma / (3 * R0), S, T, BETA, N) == pytest.approx(
        1.0, rel=1e-12
    )


def test_eq30_tension_torsion_s_t_ellipse():
    ratio = 0.6
    a, b = 2 * S / (np.sqrt(3) * T) - 1, 2 - 2 * S / (np.sqrt(3) * T)
    tau = T * np.sqrt(1 - a * ratio**2 - b * ratio)
    assert pp_index(Z, _bt(ratio * S, tau), 0.0, S, T, BETA, N) == pytest.approx(1.0, rel=1e-12)


def test_eq14_needs_s_over_sqrt3():
    """Reversed tension at s: sqrt(J2,a) = s/sqrt(3) (the text prints s sqrt(3)), P_max = s/3, and
    s/sqrt(3) + alpha s/3 = t only with alpha = 3t/s - sqrt(3)."""
    alpha = 3 * T / S - np.sqrt(3)
    assert S / np.sqrt(3) + alpha * S / 3 == pytest.approx(T, rel=1e-12)
    assert S * np.sqrt(3) + alpha * S / 3 != pytest.approx(T, rel=1e-3)


def test_compressive_p_max_ignores_gradient():
    M = np.diag([-400.0, 0.0, 0.0])
    with_g = pp_index(M, _bt(100.0, 50.0), 50.0, S, T, BETA, N)
    assert with_g == pytest.approx(pp_index(M, _bt(100.0, 50.0), 0.0, S, T, BETA, N), rel=1e-12)
