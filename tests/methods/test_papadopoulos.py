"""PAPADOPOULOS (roadmap N03): Papadopoulos (2001) Int J Fatigue 23:839-849,
doi:10.1016/S0142-1123(01)00059-7 (Zotero XA37BNPK), Eqs. (10), (14)-(25), (39)-(58), crops
_audit-trail/phase2/crops/XA37BNPK/p6*.png, p7*.png; and the volumetric 1999 form, Papadopoulos
(1999) CISM Courses 392, doi:10.1007/978-3-7091-2474-1_3 (Zotero HBKMWBNC), Eqs. (4.11)-(4.13),
(5.17)-(5.22), (5.46), Tables 1-4 (crops .../HBKMWBNC/p30*, p37, p38*, p40-p50).

The 2001 paper prints no per-test values (Figs. 3, 8, 10 only): its tests are the closed forms of
Section 2.2, the coefficients of Eqs. (54), (58) and the bending S-N curve of Eq. (55). Paper
issues: Eq. (46) prints (1/2 + (alpha/3) sigma_H,m) where reversed tension needs (1/2 + alpha/3);
Eq. (5.19) of the 1999 chapter prints 1/(4 pi) where Eq. (5.18) integrates to 1/(8 pi).

The 1999 form is also the "Papadopoulos" column of Papadopoulos et al. (1997) Table 1: 36 of 43 rows
reproduced to print precision. Rows 12, 15-19 (42CrMo4) and 22 are 0.13-0.37 points off; on
in-phase row 18 the 1997 table itself prints different values for Crossland (-2.9) and Papadopoulos
(-2.7), although the two coincide exactly in phase, so the source values carry numerical scatter.
"""

import numpy as np
import pytest
from _paper import bending_torsion, load_table

from multifat.models.integral_methods.papadopoulos import (
    generalised_shear_amplitude,
    max_generalised_shear_amplitude,
    papadopoulos_1999_index,
    papadopoulos_2001_index,
    rms_shear_amplitude,
)
from multifat.models.invariant_methods.crossland import crossland_index
from multifat.models.registry import get_models

Z = np.zeros((3, 3))


def _normal(phi, theta):
    """Eq. (4): n = (sin theta cos phi, sin theta sin phi, cos theta)."""
    return np.array([np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)])


def _sym(i, j, v):
    S = np.zeros((3, 3))
    S[i, j] = S[j, i] = v
    return S


# ---------------------------------------------------------------- 2001, Section 2.2 closed forms
@pytest.mark.parametrize("phi,theta", [(0.3, 0.4), (1.2, 2.0), (2.5, 0.9), (4.0, 1.4)])
def test_eq14_torsion_and_eq20_bending_plane_amplitudes(phi, theta):
    n = _normal(phi, theta)[None]
    t, f = 196.0, 314.0
    eq14 = t * np.sqrt(
        np.cos(theta) ** 2 * np.cos(phi) ** 2 + np.cos(2 * theta) ** 2 * np.sin(phi) ** 2
    )
    assert generalised_shear_amplitude(_sym(1, 2, t), Z, n)[0] == pytest.approx(eq14, rel=1e-12)
    eq20 = f * abs(np.sin(theta) * np.cos(theta))
    assert generalised_shear_amplitude(_sym(2, 2, f), Z, n)[0] == pytest.approx(eq20, rel=1e-12)


def test_eq15_eq21_maxima_and_calibration():
    t, f = 196.2, 313.9
    assert max_generalised_shear_amplitude(_sym(1, 2, t), Z) == pytest.approx(t, rel=1e-9)
    assert max_generalised_shear_amplitude(_sym(2, 2, f), Z) == pytest.approx(f / 2, rel=1e-9)
    assert papadopoulos_2001_index(Z, _sym(1, 2, t), Z, f, t) == pytest.approx(1.0, rel=1e-9)
    assert papadopoulos_2001_index(Z, _sym(2, 2, f), Z, f, t) == pytest.approx(1.0, rel=1e-9)


@pytest.mark.parametrize("seed", range(4))
def test_eq10_chi_integral_equals_closed_form(seed):
    """Eq. (10) with tau_a from the time history (Eqs. 33-35) == |t_s|^2 + |t_c|^2."""
    rng = np.random.default_rng(seed)
    A, B = (0.5 * (X + X.T) for X in rng.normal(scale=100.0, size=(2, 3, 3)))
    n = rng.normal(size=3)
    n /= np.linalg.norm(n)
    q = np.cross(n, [1.0, 0.0, 0.0])
    q /= np.linalg.norm(q)
    r = np.cross(n, q)
    wt = np.linspace(0, 2 * np.pi, 721)[:-1]
    chi = np.linspace(0, 2 * np.pi, 721)[:-1]
    m = np.cos(chi)[:, None] * q + np.sin(chi)[:, None] * r
    tau = (m @ A @ n)[:, None] * np.sin(wt) + (m @ B @ n)[:, None] * np.cos(wt)
    tau_a = 0.5 * (tau.max(axis=1) - tau.min(axis=1))
    Ta = np.sqrt(np.sum(tau_a**2) * (2 * np.pi / len(chi)) / np.pi)
    assert generalised_shear_amplitude(A, B, n[None])[0] == pytest.approx(Ta, rel=1e-4)


@pytest.mark.parametrize("seed", range(3))
def test_plane_maximum_against_dense_sweep(seed):
    rng = np.random.default_rng(10 + seed)
    A, B = (0.5 * (X + X.T) for X in rng.normal(scale=100.0, size=(2, 3, 3)))
    th, ph = np.meshgrid(np.linspace(0, np.pi, 721), np.linspace(0, 2 * np.pi, 1441))
    n = np.stack([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)], -1)
    brute = generalised_shear_amplitude(A, B, n.reshape(-1, 3)).max()
    found = max_generalised_shear_amplitude(A, B)
    assert brute <= found * (1 + 1e-9)
    assert found == pytest.approx(brute, rel=2e-5)


# --------------------------------------------------------------------- 2001, Section 4-5 numbers
@pytest.mark.parametrize("t,f,alpha,ratio", [(311, 442, 0.61, 0.002), (137, 230, 0.29, 0.0021)])
def test_eq54_eq58_coefficients(t, f, alpha, ratio):
    a = 3 * (t / f - 0.5)
    assert a == pytest.approx(alpha, abs=0.005)
    assert a / t == pytest.approx(ratio, abs=0.00005)


@pytest.mark.parametrize("N", [1e4, 1e5, 1e6])
def test_eq55_bending_sn_curve(N):
    """Eq. (54) in reversed bending gives s = 442/(1 - 62.3 N^-0.53), Eq. (55)."""
    t, f, kappa, lam = 311.0, 442.0, 62.3, 0.53
    gamma_N = t / (1 - kappa * N**-lam)
    s = 442.0 / (1 - kappa * N**-lam)
    assert t / (0.5 + 3 * (t / f - 0.5) / 3) == pytest.approx(442.0, abs=0.05)
    assert papadopoulos_2001_index(Z, _sym(2, 2, s), Z, f, t) * t == pytest.approx(
        gamma_N, rel=1e-6
    )


def test_eq41_mean_stress_and_cutoff():
    t, f = 311.0, 442.0
    a = 3 * (t / f - 0.5)
    A, M = _sym(0, 1, 150.0), np.diag([90.0, 0.0, 0.0])
    expected = (150.0 + a * 0.0) / (1 - a / t * 30.0) / t
    assert papadopoulos_2001_index(M, A, Z, f, t) == pytest.approx(expected, rel=1e-9)
    assert papadopoulos_2001_index(np.eye(3) * (t / a), A, Z, f, t) == np.inf


def test_eq46_printed_denominator_misprint():
    """Reversed tension sigma = s: only (1/2 + alpha/3) returns s; the printed factor
    (1/2 + (alpha/3) sigma_H,m) reduces to 1/2 at sigma_H,m = 0."""
    f_m1, f_0 = 300.0, 500.0
    a = 3 * (f_m1 - f_0) / (2 * (2 * f_0 - f_m1))  # Eq. (27)
    s = 280.0
    lhs = s / 2 + a * s / 3  # max T_a + alpha sigma_H,a
    assert lhs / (0.5 + a / 3) == pytest.approx(s, rel=1e-12)
    assert lhs / (0.5 + a / 3 * 0.0) != pytest.approx(s, rel=1e-3)


def test_registry_case_model():
    (model,) = get_models(["PAPADOPOULOS"])
    S = bending_torsion(200.0, 120.0)
    val = model.evaluate_case(S0=S, S1=-S, E0=Z, E1=Z, params={"Sigm1": 313.9, "Taum1": 196.2})
    assert val.values[""] == pytest.approx(
        papadopoulos_2001_index(Z, S, Z, 313.9, 196.2), rel=1e-12
    )


# ----------------------------------------------------------------------------- 1999 CISM form
def test_eq519_normalisation_is_one_over_8pi():
    """Eq. (5.18) integrated over chi gives 1/(8 pi); with it the sphere integral equals Eq. (5.20)
    (= sqrt(J2,a)). The printed 1/(4 pi) of Eq. (5.19) is sqrt(2) too large."""
    S = np.array([[180.0, 90.0, 0.0], [90.0, -40.0, 30.0], [0.0, 30.0, 60.0]])
    z, w = np.polynomial.legendre.leggauss(60)
    ph = np.linspace(0, 2 * np.pi, 121)[:-1]
    n = np.stack(
        np.broadcast_arrays(
            np.sqrt(1 - z[:, None] ** 2) * np.cos(ph),
            np.sqrt(1 - z[:, None] ** 2) * np.sin(ph),
            z[:, None],
        ),
        -1,
    ).reshape(-1, 3)
    wts = np.repeat(w * 2 * np.pi / len(ph), len(ph))  # int sin(theta) dtheta dphi
    tr = n @ S
    Ca2 = np.sum(tr * tr, 1) - np.sum(tr * n, 1) ** 2
    integral = np.sum(wts * Ca2)
    assert np.sqrt(5 * integral / (8 * np.pi)) == pytest.approx(
        rms_shear_amplitude(S, Z), rel=1e-10
    )
    assert np.sqrt(5 * integral / (4 * np.pi)) == pytest.approx(
        np.sqrt(2) * rms_shear_amplitude(S, Z), rel=1e-10
    )


def test_in_phase_equals_crossland():
    """For proportional loading sqrt(<T_a^2>) = sqrt(J2,a) and both use alpha = 3t/f - sqrt(3)."""
    M, A = np.diag([50.0, 0, 0]), bending_torsion(210.0, 130.0)
    assert papadopoulos_1999_index(M, A, Z, 313.9, 196.2) == pytest.approx(
        crossland_index(M, A, Z, 313.9, 196.2), rel=1e-12
    )


CISM = {1: (541, 352), 2: (660, 410), 3: (660, 410), 4: (361, 228)}


def _cism_parts(r):
    d = r._asdict()
    M, A, B = np.zeros((3, 3)), np.zeros((3, 3)), np.zeros((3, 3))
    M[0, 0], M[1, 1] = d.get("sigma_xx_m", 0.0), d.get("sigma_yy_m", 0.0)
    M[0, 1] = M[1, 0] = d.get("sigma_xy_m", 0.0)
    A[0, 0] = d["sigma_xx_a"]
    if "sigma_xy_a" in d:
        g = np.radians(d.get("gamma_xy", 0.0))
        A[0, 1] = A[1, 0] = d["sigma_xy_a"] * np.cos(g)
        B[0, 1] = B[1, 0] = -d["sigma_xy_a"] * np.sin(g)
    if "sigma_yy_a" in d:
        g = np.radians(d["gamma_yy"])
        A[1, 1], B[1, 1] = d["sigma_yy_a"] * np.cos(g), -d["sigma_yy_a"] * np.sin(g)
    return M, A, B


def _cism_rows():
    for k in CISM:
        for r in load_table(f"papadopoulos1999_cism_table{k}").itertuples():
            yield pytest.param(k, r, id=f"T{k}r{r.row}")


@pytest.mark.parametrize("k,r", list(_cism_rows()))
def test_cism_tables(k, r):
    """Tables 1-3 print sqrt(<T_a^2>) and sigma_H,max to 1 MPa and I to 0.1; Table 4 prints I
    mostly to whole percent and truncates some stresses (row 2: sigma_H,max 328.8 printed 328,
    row 3: sqrt(<T_a^2>) 195.96 printed 195)."""
    s, t = CISM[k]
    M, A, B = _cism_parts(r)
    h = (np.trace(M) + np.hypot(np.trace(A), np.trace(B))) / 3
    tol_rms, tol_I = (1.0, 0.8) if k == 4 else (0.5, 0.12)
    if (k, r.row) == (3, 10):  # printed -8.0; Eq. (5.46) gives -8.15, the printed 340 gives -8.09
        tol_I = 0.2
    assert rms_shear_amplitude(A, B) == pytest.approx(r.sqrt_T_a2, abs=tol_rms)
    assert h == pytest.approx(r.sigma_H_max, abs=tol_rms)
    assert 100 * (papadopoulos_1999_index(M, A, B, s, t) - 1) == pytest.approx(r.I_pct, abs=tol_I)


def _table1997():
    out = []
    for r in load_table("papadopoulos1997_table1").itertuples():
        if r.row in (12, 15, 16, 17, 18, 19, 22):
            reason = "0.13-0.37 points off; the source carries numerical scatter (see docstring)"
            out.append(pytest.param(r, marks=pytest.mark.xfail(strict=True, reason=reason)))
        else:
            out.append(r)
    return out


@pytest.mark.parametrize("r", _table1997())
def test_papadopoulos1997_table1_column(r):
    d = np.radians(r.delta)
    parts = (
        bending_torsion(r.sigma_m, r.tau_m),
        bending_torsion(r.sigma_a, r.tau_a * np.cos(d)),
        bending_torsion(0.0, -r.tau_a * np.sin(d)),
    )
    I = 100 * (papadopoulos_1999_index(*parts, r.f_m1, r.t_m1) - 1)
    assert I == pytest.approx(r.I_papadopoulos, abs=0.06)
