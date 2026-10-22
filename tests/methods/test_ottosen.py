"""OTT, reduced Ottosen et al. (2008) criterion of Tveit, Reyes & Erduran (2024) Results in
Engineering 22:102171, doi:10.1016/j.rineng.2024.102171 (Zotero X2KSARTZ).

Eqs. (11)-(17) p.6 (crop _audit-trail/phase2/crops/X2KSARTZ/p6.png). Table A.1 pp.9-10 gives the
error index Err = (1 - f_a) 100 % (Eq. 19), f_a = amplitude scale factor to the endurance limit,
for the modified (m) and original (m = 2) models. In-phase rows use the closed form, out-of-phase
rows the incremental model (Runge-Kutta, p.8), so only the in-phase rows are exact targets.
"""

import numpy as np
import pytest

from multifat.models.invariant_methods.ottosen import (
    M_CAP,
    OttosenReduced,
    hershey_hosford,
    kappa_of_m,
    m_of_kappa,
    ott_parameter,
)
from _paper import load_table

TABLE = load_table("tveit2024_tableA1")


def _cycle(r):
    """Eq. (18): sxx = sxx_m + sxx_a sin wt, sxy = sxy_m + sxy_a sin(wt - phi)."""
    ph = np.radians(r.phi)

    def t(xx, xy):
        return np.array([[xx, xy, 0.0], [xy, 0.0, 0.0], [0.0, 0.0, 0.0]])

    return t(r.sxx_m, r.sxy_m), t(r.sxx_a, r.sxy_a * np.cos(ph)), t(0.0, -r.sxy_a * np.sin(ph))


def _err(r, m):
    mean, sin, cos = _cycle(r)
    A = 0.0 if np.isnan(r.A) else r.A
    sea = ott_parameter(np.zeros((3, 3)), sin, cos, m, 0.0)
    return (1.0 - (r.S0 - A * np.trace(mean)) / sea) * 100.0


IN_PHASE = [r for r in TABLE.itertuples() if r.phi == 0]
OUT_OF_PHASE = [
    (
        pytest.param(
            r,
            marks=pytest.mark.xfail(
                strict=True,
                reason="30NCD16 phi = 90: both models print 0.00; reduced form gives -26 to -34 %",
            ),
        )
        if r.material == "30NCD16"
        else r
    )
    for r in TABLE.itertuples()
    if r.phi != 0
]


def _tol(r, err, m):
    """Err printed to 0.01 % (0.1 % at or above 10 %); A printed to 1e-4 (times I1,m)."""
    _, sin, cos = _cycle(r)
    sea = ott_parameter(np.zeros((3, 3)), sin, cos, m, 0.0)
    a_round = 0.0 if np.isnan(r.A) else 100 * 5e-5 * abs(r.sxx_m) / sea
    return (0.05 if abs(err) >= 10 else 0.005) + a_round + 1e-3


@pytest.mark.parametrize("r", IN_PHASE)
def test_in_phase_error_index(r):
    assert _err(r, r.m) == pytest.approx(r.err_mod, abs=_tol(r, r.err_mod, r.m))
    assert _err(r, 2.0) == pytest.approx(r.err_orig, abs=_tol(r, r.err_orig, 2.0))


@pytest.mark.parametrize("r", OUT_OF_PHASE)
def test_out_of_phase_close_to_incremental_model(r):
    """Minimum circumscribed Hershey-Hosford ball vs Tveit's incremental steady state."""
    assert _err(r, r.m) == pytest.approx(r.err_mod, abs=0.8)
    assert _err(r, 2.0) == pytest.approx(r.err_orig, abs=0.8)


@pytest.mark.parametrize("mat", TABLE.material.unique())
def test_m_from_kappa(mat):
    """kappa is printed to 1e-4, which moves m by up to 4e-3 near the peak: test Eq. (17) forward.
    kappa above 0.5852 is outside the calibrated range and printed with the cap m = 2.7670."""
    r = TABLE[TABLE.material == mat].iloc[0]
    if r.kappa >= 0.5852:
        assert r.m == M_CAP and m_of_kappa(r.kappa) == M_CAP
    else:
        assert kappa_of_m(r.m) == pytest.approx(r.kappa, abs=5.1e-5)
        assert m_of_kappa(kappa_of_m(r.m)) == pytest.approx(r.m, abs=1e-9)


def test_kappa_branch_and_limits():
    assert kappa_of_m(1.0) == pytest.approx(0.5)
    assert kappa_of_m(2.0) == pytest.approx(1 / np.sqrt(3))
    assert kappa_of_m(4.0) == pytest.approx(1 / np.sqrt(3))
    assert kappa_of_m(M_CAP) == pytest.approx(0.58524, abs=1e-5)
    # the previous bracket [1, 5] lost the root for 0.5675 < kappa < 0.5852
    assert m_of_kappa(kappa_of_m(2.3445)) == pytest.approx(2.3445, abs=1e-9)
    assert m_of_kappa(0.45) == 1.0
    assert m_of_kappa(0.8) == M_CAP


@pytest.mark.parametrize("m", [1.0, 1.5, 2.0, 2.767])
def test_bending_torsion_calibration(m):
    """Eqs. (14), (16): sigma_e,a = b for bending and t (1 + 2^(m-1))^(1/m) for torsion."""
    b, t = 300.0, 170.0
    assert hershey_hosford(np.diag([b, 0, 0]), m) == pytest.approx(b, rel=1e-12)
    S = np.array([[0, t, 0], [t, 0, 0], [0, 0, 0.0]])
    assert hershey_hosford(S, m) == pytest.approx(t * (1 + 2 ** (m - 1)) ** (1 / m), rel=1e-12)


def test_repeated_bending_gives_A():
    """Eq. (15): b_0 (1 + sin)/2 on the endurance limit S0 = b_-1 gives A = 2 b_-1/b_0 - 1."""
    s, s0 = 433.0, 700.0
    A = 2 * s / s0 - 1
    h = dict(S_mean=np.diag([s0 / 2, 0, 0]), S_sin=np.diag([s0 / 2, 0, 0]), S_cos=np.zeros((3, 3)))
    params = {"Sigm1": s, "Taum1": 250.0, "Sig0": s0}
    z = np.zeros((3, 3))
    v = OttosenReduced().evaluate_case(S0=z, E0=z, S1=z, E1=z, params=params, harmonics=h)
    assert v.values[""] == pytest.approx(s, rel=1e-12)
    assert A == pytest.approx(2 * s / s0 - 1)


def test_phase_origin_invariance():
    r = next(r for r in TABLE.itertuples() if r.phi == 90 and r.material == "Mild steel")
    mean, sin, cos = _cycle(r)
    phi = 0.4
    c, s = np.cos(phi), np.sin(phi)
    a = ott_parameter(mean, sin, cos, r.m, 0.2)
    b = ott_parameter(mean, sin * c - cos * s, sin * s + cos * c, r.m, 0.2)
    assert b == pytest.approx(a, rel=1e-4)
