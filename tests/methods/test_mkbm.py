"""MKBM, Li et al. (2011), doi:10.1016/j.ijfatigue.2010.07.003, checked against the PDF (PGXCD4FP).

Eq. (27), p.95: de*/2 = dgamma_max/2 + (1 + sigma_n,max/sigma_y) de_n/2 on the maximum shear strain
range plane. Thin-walled tube, Eqs. (1)-(3), (7)-(8), (13), (15)-(16), pp.91-92. Paper misprint:
the mean-strain terms of Eqs. (9) and (10) are swapped (Eq. 9 carries the normal-strain means of
Eq. 7, Eq. 10 the shear means of Eq. 8); Eqs. (15)-(16) are consistent with (7)-(8).
For general paths Eq. (19), p.92, defines dgamma as the longest chord of the shear path, which
the repository uses for MKBM (np_shear_rule = "longest_chord", finding F3).
"""

import numpy as np
import pytest
from _paper import frame_with_normal, rotate

from multifat.eval.evaluator import best_cp_for_case
from multifat.models.cp_methods.mkbm import MKBM

Z = np.zeros((3, 3))
A = lambda nu: np.diag([1.0, -nu, -nu])  # noqa: E731  axial strain pattern, Eq. (1)
B = np.array([[0.0, 0.5, 0.0], [0.5, 0.0, 0.0], [0.0, 0.0, 0.0]])  # engineering gamma_xy -> tensor
CASES = [  # d_eps, lam = dgamma/d_eps, nu_eff, phi_deg, eps_m, gamma_m
    (0.008, 1.5, 0.30, 0.0, 0.0, 0.0),
    (0.008, 1.5, 0.30, 90.0, 0.0, 0.0),
    (0.006, 1.0, 0.42, 30.0, 0.001, 0.0),
    (0.004, 2.2, 0.50, 60.0, 0.0, 0.002),
    (0.010, 0.5, 0.35, 45.0, 0.002, -0.001),
]


def _tube(d_eps, lam, nu, phi_deg, eps_m, gam_m):
    phi = np.radians(phi_deg)
    d_gam = lam * d_eps
    mean = eps_m * A(nu) + gam_m * B
    e_sin = 0.5 * d_eps * A(nu) + 0.5 * d_gam * np.cos(phi) * B
    e_cos = -0.5 * d_gam * np.sin(phi) * B
    return mean, e_sin, e_cos


def _eq15_16(d_eps, lam, nu, phi_deg, alpha):
    phi = np.radians(phi_deg)
    c2, s2 = np.cos(2 * alpha), np.sin(2 * alpha)
    dg = d_eps * np.hypot(lam * c2 * np.cos(phi) - (1 + nu) * s2, lam * c2 * np.sin(phi))
    den = (
        0.5
        * d_eps
        * np.hypot(
            2 * (1 + nu) * np.cos(alpha) ** 2 - 2 * nu + lam * s2 * np.cos(phi),
            lam * s2 * np.sin(phi),
        )
    )
    return dg, den


@pytest.mark.parametrize("case", CASES)
def test_plane_strains_eq7_eq8(case):
    """Rotating the Eq. (1) tensor reproduces Eqs. (7)-(8) at every instant."""
    d_eps, lam, nu, phi_deg, eps_m, gam_m = case
    mean, e_sin, e_cos = _tube(*case)
    for alpha in np.radians([0.0, 17.0, 33.0, 61.0]):
        R = frame_with_normal([np.cos(alpha), np.sin(alpha), 0.0])
        t_dir = np.array([-np.sin(alpha), np.cos(alpha), 0.0])
        for wt in np.linspace(0, 2 * np.pi, 7):
            e = mean + e_sin * np.sin(wt) + e_cos * np.cos(wt)
            exx, gxy = e[0, 0], 2 * e[0, 1]
            n = R[:, 2]
            eps7 = (1 - nu) / 2 * exx + (1 + nu) / 2 * exx * np.cos(2 * alpha)
            eps7 += 0.5 * gxy * np.sin(2 * alpha)
            gam8 = -(1 + nu) * exx * np.sin(2 * alpha) + gxy * np.cos(2 * alpha)
            assert n @ e @ n == pytest.approx(eps7, abs=1e-15)
            assert 2 * (t_dir @ e @ n) == pytest.approx(gam8, abs=1e-15)
            assert rotate(e, R)[2, 2] == pytest.approx(eps7, abs=1e-15)


@pytest.mark.parametrize("case", CASES)
def test_mkbm_on_plane_reproduces_eq15_eq16(case):
    """Harmonic evaluator path + Eq. (27) with zero stress: dgamma/2 + de_n/2 from Eqs. (15)-(16)."""
    mean, e_sin, e_cos = _tube(*case)
    for alpha in np.radians([0.0, 12.0, 27.5, 45.0, 70.0]):
        R = frame_with_normal([np.cos(alpha), np.sin(alpha), 0.0])
        best = best_cp_for_case(
            S0=Z,
            S1=Z,
            E0=mean + e_sin,
            E1=mean - e_sin,
            R_list=R[None],
            refine=False,
            method=MKBM(),
            params={"Sy": 300.0},
            S_sin=Z,
            S_cos=Z,
            E_sin=e_sin,
            E_cos=e_cos,
        )
        dg, den = _eq15_16(case[0], case[1], case[2], case[3], alpha)
        assert best.by_metric == pytest.approx(0.5 * dg + 0.5 * den, rel=1e-12)


@pytest.mark.parametrize("case", CASES)
def test_critical_plane_angle_eq13(case):
    """The maximum of Eq. (15) satisfies tan 4 alpha_c = 2 lam (1+nu) cos phi / ((1+nu)^2 - lam^2)."""
    d_eps, lam, nu, phi_deg, _, _ = case
    alphas = np.linspace(0, np.pi, 200001)
    a_c = alphas[np.argmax(_eq15_16(d_eps, lam, nu, phi_deg, alphas)[0])]
    lhs = np.tan(4 * a_c) * ((1 + nu) ** 2 - lam**2)
    assert lhs == pytest.approx(2 * lam * (1 + nu) * np.cos(np.radians(phi_deg)), abs=1e-3)


def test_eq27_normal_stress_term():
    """sigma_n,max/sigma_y scales the normal-strain term; compressive maxima clip to zero."""
    e0 = np.diag([0.0, 0.0, 0.002])
    e0[0, 2] = e0[2, 0] = 0.003
    s0 = np.diag([0.0, 0.0, 150.0])
    r = MKBM().evaluate_on_plane(S0r=s0, S1r=-s0, E0r=e0, E1r=-e0, params={"Sy": 300.0})
    assert r.metric == pytest.approx(4 * 0.003)  # engineering range = 2 x tensor range
    assert r.damage == pytest.approx(0.006 + (1 + 150 / 300) * 0.002)
    r_c = MKBM().evaluate_on_plane(S0r=-s0, S1r=-s0, E0r=e0, E1r=-e0, params={"Sy": 300.0})
    assert r_c.damage == pytest.approx(0.006 + 0.002)


def test_out_of_phase_shear_range_is_longest_chord_eq19():
    """Elliptical shear path on the plane: Eq. (19) gives 2 x major semi-axis, not 2 sqrt(a^2+b^2)."""
    e_sin = np.zeros((3, 3))
    e_cos = np.zeros((3, 3))
    e_sin[0, 2] = e_sin[2, 0] = 0.002  # semi-axis a along local x
    e_cos[1, 2] = e_cos[2, 1] = 0.001  # semi-axis b along local y, 90 deg out of phase
    best = best_cp_for_case(
        S0=Z,
        S1=Z,
        E0=e_sin,
        E1=-e_sin,
        R_list=np.eye(3)[None],
        refine=False,
        method=MKBM(),
        params={"Sy": 300.0},
        S_sin=Z,
        S_cos=Z,
        E_sin=e_sin,
        E_cos=e_cos,
    )
    longest_chord = 2 * 2 * 0.002  # engineering: 2 x (tensor chord 2a)
    assert best.by_metric == pytest.approx(0.5 * longest_chord, rel=1e-12)
