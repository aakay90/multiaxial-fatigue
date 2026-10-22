"""MMCCM (roadmap G22): Wang & Susmel (2016) Int J Fatigue, doi:10.1016/j.ijfatigue.2015.10.005
(Zotero HRGQVPB3); Eqs. (1)-(8) pp.5-6 (crops _audit-trail/phase2/crops/HRGQVPB3/p5.png, p6.png).
Per-test predictions are figures only (Figs. 6-11), so the tests check the formulation: Eq. (2)
reduces to Eqs. (3) and (4) at rho = 1 and 0, Eqs. (5)-(8) interpolate, the life inversion, the
plane search with the largest-rho tie rule (p.5), and the printed Eq. (25) estimate of Table 1.
"""

import numpy as np
import pytest
from _paper import bending_torsion

from multifat.eval.evaluator import best_cp_for_case
from multifat.models.cp_methods.mmccm import MMCCM, _validated_constants, mmccm_curve, mmccm_life
from multifat.planes.sampling import build_R_list

P = dict(
    E=200000.0,
    nu=0.3,
    sigma_f=900.0,
    epsilon_f=0.4,
    b_fat=-0.09,
    c_fat=-0.6,
    tau_f=520.0,
    gamma_f=0.69,
    b0=-0.08,
    c0=-0.55,
)
K = _validated_constants(P)
G = P["E"] / (2 * (1 + P["nu"]))


def _strain(S):
    return ((1 + P["nu"]) * S - P["nu"] * np.trace(S) * np.eye(3)) / P["E"]


def _best(S_amp, S_mean=None):
    S_mean = np.zeros((3, 3)) if S_mean is None else S_mean
    return best_cp_for_case(
        S0=S_mean + S_amp,
        S1=S_mean - S_amp,
        E0=_strain(S_mean + S_amp),
        E1=_strain(S_mean - S_amp),
        R_list=build_R_list(),
        method=MMCCM(),
        params=P,
    )


@pytest.mark.parametrize("N", [1e3, 1e5, 1e7])
def test_eqs_3_and_4_limits(N):
    x = 2 * N
    eq3 = (1 + P["nu"]) * P["sigma_f"] / P["E"] * x ** P["b_fat"] + 1.5 * P["epsilon_f"] * x ** P[
        "c_fat"
    ]
    eq4 = P["tau_f"] / G * x ** P["b0"] + P["gamma_f"] * x ** P["c0"]
    for rho, expected in ((1.0, eq3), (0.0, eq4)):
        A, b, B, c = mmccm_curve(rho, K)
        assert A * x**b + B * x**c == pytest.approx(expected, rel=1e-12)
        assert mmccm_life(expected, rho, K) == pytest.approx(N, rel=1e-9)


def test_eqs_7_8_harmonic_interpolation():
    _, b, _, c = mmccm_curve(0.5, K)
    assert 1 / b == pytest.approx(0.5 / P["b_fat"] + 0.5 / P["b0"], rel=1e-12)
    assert 1 / c == pytest.approx(0.5 / P["c_fat"] + 0.5 / P["c0"], rel=1e-12)


def test_plane_search_uniaxial_and_torsion():
    s, t = 400.0, 250.0
    gamma_ax = (1 + P["nu"]) * s / P["E"]  # max engineering shear strain amplitude, rho = 1
    assert 1 / _best(bending_torsion(s, 0.0)).by_metric == pytest.approx(
        mmccm_life(gamma_ax, 1.0, K), rel=1e-8
    )
    assert 1 / _best(bending_torsion(0.0, t)).by_metric == pytest.approx(
        mmccm_life(t / G, 0.0, K), rel=1e-8
    )


def test_ties_take_the_largest_rho():
    """Torsion amplitude t with an axial mean m: the x- and y-faces tie in gamma_a; the x-face
    has rho = m/t (p.5: the critical plane is the one with the largest rho)."""
    t, m = 200.0, 150.0
    life = 1 / _best(bending_torsion(0.0, t), bending_torsion(m, 0.0)).by_metric
    assert life == pytest.approx(mmccm_life(t / G, m / t, K), rel=1e-8)


def test_run_out_and_invalid_curve():
    A, b, B, c = mmccm_curve(0.0, K)
    tiny = 0.5 * (A * 2e12**b + B * 2e12**c)
    assert mmccm_life(tiny, 0.0, K) == np.inf
    rho_pole = P["b_fat"] / (P["b_fat"] - P["b0"])  # Eq. (7) denominator vanishes
    assert mmccm_life(0.01, rho_pole + 0.5, K) == 0.0


def test_table1_eq25_estimate():
    """Al5083 row: tau'_f = sigma'_f / sqrt(3) = 450.3 MPa, printed 451 (Eq. 25)."""
    assert 780.0 / np.sqrt(3) == pytest.approx(451.0, abs=1.0)
    assert np.sqrt(3) * 1.153 == pytest.approx(1.997, abs=5e-4)
