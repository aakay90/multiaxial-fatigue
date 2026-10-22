"""Doudard, Hild & Calloch (2007) kernel (roadmap N34): Fatigue Fract Engng Mater Struct 30:107-114,
doi:10.1111/j.1460-2695.2006.01087.x (Zotero 35U2IMK5); Eqs. (15)-(22), (26), (27)-(36) and Table 1
(crops _audit-trail/phase2/crops/35U2IMK5/p3, p4, p6).

Tension: 2 T_a / Sigma0 = |sin(2 zeta) cos(chi)|, so kappa = 2 pi 2^m B((m+1)/2, m/2+1)
int_0^2pi |cos chi|^m dchi. Table 1 (Sigma_T mean fatigue limit in tension, m = 16): 30NiCrMo16
S0 (V0/V)^(1/m) = 632, mean 560 MPa; C20 302, 273 MPa.
"""

from math import gamma, pi, sqrt

import numpy as np
import pytest

from multifat.models.integral_methods.doudard import (
    failure_probability,
    fatigue_limit,
    fatigue_limit_sd,
    kappa,
    mean_fatigue_limit,
    stromeyer_life,
    tension_torsion_amplitudes,
    tresca_amplitude,
)


def _beta(a, b):
    return gamma(a) * gamma(b) / gamma(a + b)


def _kappa(m, sigma0, t0, delta):
    A, B = tension_torsion_amplitudes(sigma0, t0, delta)
    return kappa(m, A, B, tresca_amplitude(sigma0, t0, delta))


@pytest.mark.parametrize("m", [0.0, 2.0, 7.3, 16.0])
def test_kappa_tension_closed_form(m):
    chi = 2 * sqrt(pi) * gamma((m + 1) / 2) / gamma(m / 2 + 1)
    exact = 2 * pi * 2**m * _beta((m + 1) / 2, m / 2 + 1) * chi
    assert _kappa(m, 1.0, 0.0, 0.0) == pytest.approx(exact, rel=1e-8)
    if m == 0.0:
        assert exact == pytest.approx(8 * pi**2)


def test_kappa_is_invariant_under_rotation():
    A, B = tension_torsion_amplitudes(2.0, 1.0, pi / 3)
    st = tresca_amplitude(2.0, 1.0, pi / 3)
    q, _ = np.linalg.qr(np.random.default_rng(0).normal(size=(3, 3)))
    assert kappa(16, q @ A @ q.T, q @ B @ q.T, st) == pytest.approx(kappa(16, A, B, st), rel=1e-9)


def test_eq26_tresca_amplitude():
    assert tresca_amplitude(300.0, 0.0, 0.0) == pytest.approx(300.0)
    assert tresca_amplitude(0.0, 150.0, 0.0) == pytest.approx(300.0)
    assert tresca_amplitude(2.0, 1.0, pi / 2) == pytest.approx(2.0)
    assert tresca_amplitude(2.0, 1.0, 0.0) == pytest.approx(sqrt(8.0))


@pytest.mark.xfail(
    strict=True,
    reason="unresolved: printed kappa(16) 3.6 / 1.0 / 1.6 / 9.6 are 5-10 % above Eq. (36) "
    "(3.357 / 0.9415 / 1.459 / 9.137), no common factor",
)
def test_printed_kappa_16():
    printed = [3.6, 1.0, 1.6, 9.6]
    cases = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (2.0, 1.0, 0.0), (2.0, 1.0, pi / 2)]
    assert [_kappa(16, *c) for c in cases] == pytest.approx(printed, rel=0.02)


@pytest.mark.parametrize("a,mean", [(632.0, 560.0), (302.0, 273.0)])
def test_table1_tension_mean_fatigue_limit(a, mean):
    """Eq. (19) with V_eff = V kappa_tension(16): 567.6 and 271.2 MPa (printed kappa 3.6: 564.5,
    269.7)."""
    k = _kappa(16, 1.0, 0.0, 0.0)
    assert mean_fatigue_limit(16, a, k) == pytest.approx(mean, rel=0.015)


def test_eqs_15_19_20_22_consistency():
    m, s0, v = 16.0, 600.0, 3.4
    s = np.linspace(0.0, 2000.0, 400001)
    survival = 1.0 - np.array([failure_probability(x, m, s0, v) for x in s])
    mean = np.trapezoid(survival, s)
    second = np.trapezoid(2 * s * survival, s)
    assert mean_fatigue_limit(m, s0, v) == pytest.approx(mean, rel=1e-8)
    assert fatigue_limit_sd(m, s0, v) == pytest.approx(sqrt(second - mean**2), rel=1e-5)
    s50 = fatigue_limit(0.5, m, s0, v)
    assert failure_probability(s50, m, s0, v) == pytest.approx(0.5, rel=1e-12)
    assert stromeyer_life(s50, s50, 1e6) == float("inf")
    assert stromeyer_life(s50 + 10.0, s50, 1e6) == pytest.approx(1e6 / (10.0 * s50))
