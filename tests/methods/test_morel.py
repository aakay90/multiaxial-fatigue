"""Morel (1998) kernel (roadmap G23): Fatigue Fract Engng Mater Struct 21:241-256,
doi:10.1046/j.1460-2695.1998.00452.x (Zotero IJ6W3BJ6); Eqs. (10), (33)-(38) and the worked
example p.252-253 (crops _audit-trail/phase2/crops/IJ6W3BJ6/p9_*.png, p12_*.png).

Worked example (30NCD16, f = 680, t = 426 MPa; S11a = 600, S12a = 335 MPa, beta12 = 90 deg):
printed T_S = 697, C_A = 282, H = 2.47, a = 0.67, b = 775, T_Slim = 633, tau_lim = 256 MPa.
Reproduced: T_S 697.5, a 0.6725, T_Slim 633.0 (with b = sqrt(pi) t = 755 from Eq. 10; b = 775 is a
misprint and would give 650). C_A comes out 285.0 (exact semi-major axis on the critical plane), 1 %
above the printed 282 (unresolved; H and tau_lim follow from it). p, q, r are not printed, so the
life N_i = 2e5 cannot be checked.
"""

import numpy as np
import pytest

from multifat.models.integral_methods.morel import morel_life, morel_limit, morel_parameters
from multifat.models.integral_methods.papadopoulos import papadopoulos_2001_index

Z = np.zeros((3, 3))


def _example():
    A, B = np.zeros((3, 3)), np.zeros((3, 3))
    A[0, 0] = 600.0
    B[0, 1] = B[1, 0] = -335.0  # 335 sin(wt - 90 deg), Eq. (28)
    return A, B


def test_eq10_parameters_and_b_misprint():
    a, b = morel_parameters(680.0, 426.0)
    assert a == pytest.approx(0.67, abs=0.005)
    assert b == pytest.approx(755.0, abs=0.5)
    assert b != pytest.approx(775.0, abs=5.0)


def test_worked_example():
    L = morel_limit(Z, *_example(), 680.0, 426.0)
    assert L.T_S == pytest.approx(697.0, abs=0.5)
    assert L.P_a == pytest.approx(200.0) and L.P_m == 0.0
    assert L.T_Slim == pytest.approx(633.0, abs=0.5)
    assert L.C_A == pytest.approx(282.0, rel=0.011)  # 285.0, see module docstring
    assert L.tau_lim == pytest.approx(L.T_Slim / L.H, rel=1e-12)


@pytest.mark.xfail(
    strict=True, reason="printed C_A = 282 MPa; the critical-plane semi-major axis is 285.0"
)
def test_worked_example_c_a_as_printed():
    assert morel_limit(Z, *_example(), 680.0, 426.0).C_A == pytest.approx(282.0, abs=0.5)


def test_h_bounds():
    """H = sqrt(pi) for proportional loading and sqrt(2 pi) for a circular path (Eq. 35, p.251)."""
    A, _ = _example()
    assert morel_limit(Z, A, Z, 680.0, 426.0).H == pytest.approx(np.sqrt(np.pi), rel=1e-6)
    T1, T2 = np.zeros((3, 3)), np.zeros((3, 3))
    T1[0, 2] = T1[2, 0] = 100.0
    T2[1, 2] = T2[2, 1] = 100.0
    assert morel_limit(Z, T1, T2, 680.0, 426.0).H == pytest.approx(np.sqrt(2 * np.pi), rel=1e-6)


@pytest.mark.parametrize("mean", [0.0, 150.0, -80.0])
def test_limit_ratio_equals_papadopoulos_2001(mean):
    """T_S / T_Slim (Eqs. 33-37) = Papadopoulos (2001) Eq. (41) index: the same iso-life planes."""
    A, B = _example()
    M = np.diag([mean, 0.0, 0.0])
    L = morel_limit(M, A, B, 680.0, 426.0)
    assert L.T_S / L.T_Slim == pytest.approx(
        papadopoulos_2001_index(M, A, B, 680.0, 426.0), rel=1e-9
    )


def test_eq38_life():
    p, q, r = 1.0e5, 2.0e4, 3.0e6
    ca, tl = 300.0, 250.0
    expected = p * np.log(ca / (ca - tl)) + q * tl / (ca - tl) - r / ca
    assert morel_life(ca, tl, p, q, r) == pytest.approx(expected, rel=1e-12)
    assert morel_life(240.0, tl, p, q, r) == np.inf


def test_life_fit_recovers_eq38_constants():
    from multifat.models.integral_methods.morel import fit_morel_life

    rng = np.random.default_rng(3)
    tau_lim = rng.uniform(200.0, 260.0, 12)
    C_A = tau_lim * rng.uniform(1.05, 1.8, 12)
    p, q, r = 4.0e4, 2.5e4, 1.0e5
    N = morel_life(C_A, tau_lim, p, q, r)
    assert np.allclose(fit_morel_life(C_A, tau_lim, N), (p, q, r), rtol=1e-8)


def test_case_model_damage_and_native_life():
    from multifat.models.integral_methods.morel import Morel

    A, B = _example()
    res = Morel().evaluate_case(
        S0=Z,
        E0=Z,
        S1=Z,
        E1=Z,
        params={"Sigm1": 680.0, "Taum1": 426.0},
        harmonics={"S_mean": Z, "S_sin": A, "S_cos": B},
    )
    L = morel_limit(Z, A, B, 680.0, 426.0)
    assert res.values[""] == pytest.approx(L.T_S / L.T_Slim)
    fit = {"p": 4.0e4, "q": 2.5e4, "r": 1.0e5}
    assert Morel().native_life(res.aux, {}, fit) == pytest.approx(
        morel_life(L.C_A, L.tau_lim, **fit)
    )
