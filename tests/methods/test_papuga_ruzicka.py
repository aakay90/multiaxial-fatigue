"""PCR (roadmap G01) and PI (G02): Papuga & Růžička (2008) Int J Fatigue 30:58-66,
doi:10.1016/j.ijfatigue.2007.02.015 (Zotero VEW9699S); Eqs. (16), (17) p.62 and Appendices A, B
pp.64-66 (crop _audit-trail/phase2/crops/VEW9699S/p5_*.png).

The paper prints no per-test values (its 119 tests are listed in Papuga's thesis [7]), only group
statistics (Table 2); the tests are therefore the calibrations of Appendices A and B.

- PCr: both kappa branches of Eq. (17) return f_-1 in fully reversed axial loading and in fully
  reversed torsion (maximum-damage plane).
- PI: Appendix A integrates N_a = t_-1 sin(2 phi) sin^2(psi) as a signed quantity in torsion
  (Eq. A.2, integral 0). An amplitude is non-negative; with |N_a| the torsion calibration fails by
  sqrt(1 + (3 - kappa^2) 4/(3 pi kappa)) - 1 (+5.6 % at kappa = 1.6). Eq. (16) is implemented as
  printed with N_a >= 0; the axial calibration (Eq. A.5) holds.
- Eq. (A.17) prints sin(2 phi_t) as the common factor of Eq. (A.16), which factors as
  sin(2 psi_t) (crop p8_*.png); the roots (A.18) are labelled (I), (III), (III) for (I)-(III).
"""

import numpy as np
import pytest

from multifat.models.integral_methods.bohme_papuga import _plane_amplitudes, _sphere_grid
from multifat.models.integral_methods.papuga_ruzicka import (
    PI_GRID,
    pcr_index,
    pcr_parameters,
    pi_index,
    pi_parameters,
)
from multifat.models.registry import get_models

Z = np.zeros((3, 3))


def _axial(s):
    A = np.zeros((3, 3))
    A[0, 0] = s
    return A


def _shear(t):
    A = np.zeros((3, 3))
    A[0, 1] = A[1, 0] = t
    return A


def _rotation(seed):
    q, _ = np.linalg.qr(np.random.default_rng(seed).normal(size=(3, 3)))
    return q


@pytest.mark.parametrize("f,t", [(313.9, 196.2), (398.0, 260.0), (300.0, 280.0), (300.0, 265.0)])
def test_pcr_calibration_both_branches(f, t):
    """kappa = 1.60, 1.53 (second branch), 1.07, 1.13 (first branch of Eq. 17)."""
    assert pcr_index(Z, _axial(f), Z, f, t, 1.5 * f) == pytest.approx(1.0, rel=1e-9)
    assert pcr_index(Z, _shear(t), Z, f, t, 1.5 * f) == pytest.approx(1.0, rel=1e-9)


def test_pcr_branches_meet_at_sqrt_4_over_3():
    f = 300.0
    lo = pcr_parameters(f, f / (np.sqrt(4 / 3) - 1e-12))
    hi = pcr_parameters(f, f / np.sqrt(4 / 3))
    assert lo == pytest.approx(hi, rel=1e-6)


def test_eq16_parameters():
    a, b = pi_parameters(313.9, 196.2)
    k2 = (313.9 / 196.2) ** 2
    assert (a, b) == pytest.approx((2.5 * k2, 313.9 * (3 - k2)), rel=1e-12)


def test_appendix_a_sphere_averages():
    """1/(4 pi) int int C_a^2 sin psi = (2/5) t^2 in torsion (A.2) and (2/15) f^2 in axial loading (A.5);
    1/(4 pi) int int N_a sin psi = f/3 (A.5) in axial loading."""
    normals, w = _sphere_grid(*PI_GRID)
    n_a, _, c_a, _ = _plane_amplitudes(Z, _shear(1.0), Z, normals)
    assert np.sum(w * c_a**2) == pytest.approx(2 / 5, rel=1e-6)
    assert np.sum(w * n_a) == pytest.approx(4 / (3 * np.pi), rel=1e-3)  # |N_a|; signed: 0
    n_a, _, c_a, _ = _plane_amplitudes(Z, _axial(1.0), Z, normals)
    assert np.sum(w * c_a**2) == pytest.approx(2 / 15, rel=1e-6)
    assert np.sum(w * n_a) == pytest.approx(1 / 3, rel=1e-6)


@pytest.mark.parametrize("f,t", [(313.9, 196.2), (398.0, 260.0), (660.0, 410.0)])
def test_pi_axial_calibration_and_torsion_inconsistency(f, t):
    assert pi_index(Z, _axial(f), Z, f, t) == pytest.approx(1.0, rel=1e-6)
    k = f / t
    expected = np.sqrt(1 + (3 - k**2) * 4 / (3 * np.pi * k))
    assert pi_index(Z, _shear(t), Z, f, t) == pytest.approx(expected, rel=1e-3)


def test_pi_mean_term_is_hydrostatic():
    """1/(4 pi) int int N_m sin psi = sigma_H,m, so the mean enters as b_I kappa sigma_H,m."""
    f, t = 398.0, 260.0
    a, b = pi_parameters(f, t)
    M = np.diag([120.0, -30.0, 60.0])
    base = (pi_index(Z, _axial(250.0), Z, f, t) * f) ** 2
    with_mean = (pi_index(M, _axial(250.0), Z, f, t) * f) ** 2
    assert with_mean - base == pytest.approx(b * f / t * np.trace(M) / 3, rel=1e-9)


@pytest.mark.parametrize("seed", range(3))
def test_rotation_invariance(seed):
    R = _rotation(seed)
    A, B = _axial(300.0) + _shear(80.0), _shear(150.0)
    M = np.diag([100.0, 0.0, 0.0])
    rot = [R @ X @ R.T for X in (M, A, B)]
    assert pi_index(*rot, 398.0, 260.0) == pytest.approx(pi_index(M, A, B, 398.0, 260.0), rel=1e-3)
    assert pcr_index(*rot, 398.0, 260.0, 620.5) == pytest.approx(
        pcr_index(M, A, B, 398.0, 260.0, 620.5), rel=1e-7
    )


def test_pcr_out_of_phase_against_dense_sweep():
    f, t, f0 = 398.0, 260.0, 620.5
    M, A, B = np.diag([80.0, 0, 0]), _axial(280.0), _shear(-140.0)
    a, b = pcr_parameters(f, t)
    th, ph = np.meshgrid(np.linspace(0, np.pi, 721), np.linspace(0, 2 * np.pi, 1441))
    n = np.stack([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)], -1).reshape(-1, 3)
    n_a, n_m, c_a, _ = _plane_amplitudes(M, A, B, n)
    brute = np.sqrt(np.max(a * c_a**2 + b * (n_a + t / f0 * n_m))) / f
    found = pcr_index(M, A, B, f, t, f0)
    assert brute <= found * (1 + 1e-9)
    assert found == pytest.approx(brute, rel=2e-5)


def test_registry_and_f0_fallback():
    pcr, pi = get_models(["PCR", "PI"])
    S = _axial(200.0) + _shear(120.0)
    p = {"Sigm1": 398.0, "Taum1": 260.0, "Sig0": 620.5}
    assert pcr.evaluate_case(S0=S, S1=-S, E0=Z, E1=Z, params=p).values[""] == pytest.approx(
        pcr_index(Z, S, Z, 398.0, 260.0, 620.5), rel=1e-12
    )
    assert pi.evaluate_case(S0=S, S1=-S, E0=Z, E1=Z, params=p).values[""] == pytest.approx(
        pi_index(Z, S, Z, 398.0, 260.0), rel=1e-12
    )
    with pytest.raises(ValueError):
        pcr.evaluate_case(S0=S, S1=-S, E0=Z, E1=Z, params={"Sigm1": 398.0, "Taum1": 260.0})
