"""Tier 3 point kernels (decision D1):

G26 Banvillet, Palin-Luc & Lasserre (2003), doi:10.1016/S0142-1123(03)00048-3 (Zotero Z2S5IDBQ),
Eqs. (3)-(9), (29), Tables 1-2 (crops _audit-trail/phase2/crops/Z2S5IDBQ/p6_*, p9_*, p12_*): the
uniaxial rows 1-3 of Table 2 (30NiCrMo16, s_Ten = 560, s_RB = 658 MPa) give REP = 10.4, 11.3, 2.4 %
at fixed mean against the printed 10.2, 11.1, 2.3 % (the print is consistent with s_Ten ~ 560.6).

G24 Flacelière & Morel (2004), doi:10.1111/j.1460-2695.2004.00823.x (Zotero 9P275RIJ), Eqs. (12)-(14)
(crop .../9P275RIJ/p10.png): H_m closed forms against numerical integration of the cycle-maximum
stress over the section (rotating bending: sigma r/R at every point).
"""

import numpy as np
import pytest

from multifat.models.energy_based_methods.banvillet import (
    banvillet_thresholds,
    rotating_bending_gbar,
    uniaxial_limit_amplitude,
    uniaxial_work,
)
from multifat.models.integral_methods.flaceliere_morel import (
    failure_probability,
    heterogeneity_factor,
    median_strength,
)

E = 200000.0
S_TEN, S_RB = 560.0, 658.0


@pytest.mark.parametrize(
    "sa,sm,rep", [(235.0, 745.0, 10.2), (251.0, 704.0, 11.1), (527.0, 222.0, 2.3)]
)
def test_banvillet_table2_uniaxial_rows(sa, sm, rep):
    predicted = uniaxial_limit_amplitude(sm, S_TEN)
    assert uniaxial_work(sm, predicted, E) == pytest.approx(S_TEN**2 / E, rel=1e-12)
    assert 100 * (sa - predicted) / sa == pytest.approx(rep, abs=0.25)


def test_banvillet_eqs_7_8_9_rotating_bending():
    """The rotating-bending endurance limit satisfies Eq. (5) with Eqs. (7)-(9); the annulus
    average equals the numerical one."""
    sigma_star, w_star, g_d = banvillet_thresholds(S_TEN, S_RB, E)
    assert rotating_bending_gbar(S_RB, sigma_star, E) == pytest.approx(g_d, rel=1e-12)
    sa = 700.0
    r = np.linspace(sigma_star / sa, 1, 200001)  # V*: W_g = (sa r)^2 / E >= W*
    num = np.trapezoid(((sa * r) ** 2 / E - w_star) * r, r) / np.trapezoid(r, r)
    assert rotating_bending_gbar(sa, sigma_star, E) == pytest.approx(num, rel=1e-6)


@pytest.mark.parametrize("m", [2.0, 7.3, 16.8])
def test_flaceliere_eq14_heterogeneity_factors(m):
    y = np.linspace(-1, 1, 400001)  # across the section; the span x runs 0..1 (moment ~ x)
    depth = np.trapezoid(np.abs(y) ** m, y) / 2
    assert heterogeneity_factor("four_point_plane", m) == pytest.approx(depth, rel=1e-6)
    r = np.linspace(0, 1, 400001)
    disk = np.trapezoid(r**m * 2 * r, r)  # rotating: cycle maximum sigma r/R at every point
    assert heterogeneity_factor("four_point_rotating", m) == pytest.approx(disk, rel=1e-6)
    x = np.linspace(0, 1, 400001)
    span = np.trapezoid(x**m, x)
    assert heterogeneity_factor("three_point_plane", m) == pytest.approx(depth * span, rel=1e-6)
    assert heterogeneity_factor("three_point_rotating", m) == pytest.approx(disk * span, rel=1e-6)
    assert heterogeneity_factor("tension", m) == 1.0


def test_flaceliere_eq13_median():
    m, v, v0 = 16.8, 100.0, 3.07e39
    s50 = median_strength(m, v, v0, 1.0)
    assert failure_probability(s50, m, v, v0, 1.0) == pytest.approx(0.5, rel=1e-12)
