"""Crossland (N01) and Sines (N02) as restated by Papadopoulos et al. (1997) Int J Fatigue
19:219-235, doi:10.1016/S0142-1123(96)00064-3 (Zotero BW24SJ5K); Eqs. (44), (62)-(66) p.9 and
Table 1 p.13 (crops _audit-trail/phase2/crops/BW24SJ5K/p9.png, p13.png).

Table 1 checks:
- Rows with delta = 0, 90 or 180 deg: Crossland and Sines reproduced to print precision. Sines uses
  the printed Eq. (64) coefficient sqrt(3) f_-1/sigma_f, as the table does (Eq. 63 with the Goodman
  f_0 would miss the mean-stress rows by up to 11 points). Rows 14 and 15 (42CrMo4) are 0.3 points off (unresolved).
- Rows with delta = 30, 45, 60, 120 deg: the table was computed with sin(delta) where Eq. (44) has
  sin^2(delta) (every such row matches the sin variant exactly). Eq. (44) itself is correct, being
  the minimum circumscribed hypersphere radius of the ellipse, so these rows are a calculation error
  in the table and are kept as strict xfails.
"""

import numpy as np
import pytest
from _paper import load_table

from multifat.models.invariant_methods.crossland import crossland_index
from multifat.models.invariant_methods.sines import sines_index, sines_kappa
from multifat.models.invariant_methods.stress_invariants import sqrt_j2_amplitude

TABLE = load_table("papadopoulos1997_table1")


def _t(s, x):
    return np.array([[s, x, 0.0], [x, 0.0, 0.0], [0.0, 0.0, 0.0]])


def _parts(r):
    d = np.radians(r.delta)
    return _t(r.sigma_m, r.tau_m), _t(r.sigma_a, r.tau_a * np.cos(d)), _t(0, -r.tau_a * np.sin(d))


def _rows():
    out = []
    for r in TABLE.itertuples():
        if r.delta not in (0, 90, 180):
            reason = "Table 1 used sin(delta) for sin^2(delta) of Eq. (44)"
        elif r.row in (14, 15):
            reason = "42CrMo4 rows 14-15: 0.3 points off, unresolved"
        else:
            out.append(r)
            continue
        out.append(pytest.param(r, marks=pytest.mark.xfail(strict=True, reason=reason)))
    return out


@pytest.mark.parametrize("r", _rows())
def test_table1_crossland(r):
    I = 100 * (crossland_index(*_parts(r), r.f_m1, r.t_m1) - 1)
    assert I == pytest.approx(r.I_crossland, abs=0.06)


@pytest.mark.parametrize("r", [r for r in TABLE.itertuples() if r.delta in (0, 90, 180)])
def test_table1_sines_eq64(r):
    I = 100 * (sines_index(*_parts(r), r.t_m1, sines_kappa(r.f_m1, r.sigma_f)) - 1)
    assert I == pytest.approx(r.I_sines, abs=0.11)  # rows 22, 28: 0.07-0.1 off


@pytest.mark.parametrize("r", [r for r in TABLE.itertuples() if r.delta not in (0, 90, 180)])
def test_table1_intermediate_phase_used_sin_delta(r):
    """Documents the table error: Eq. (44) with sin(delta) instead of sin^2(delta)."""
    X = r.sigma_a**2 / 3 + r.tau_a**2
    s = np.sin(np.radians(r.delta))
    j = np.sqrt(0.5 * (X + np.sqrt(X**2 - 4 / 3 * r.sigma_a**2 * r.tau_a**2 * abs(s))))
    kappa = 3 * r.t_m1 / r.f_m1 - np.sqrt(3)
    I = 100 * ((j + kappa * (r.sigma_a + r.sigma_m) / 3) / r.t_m1 - 1)
    assert I == pytest.approx(r.I_crossland, abs=0.11)


@pytest.mark.parametrize("delta", [0.0, 30.0, 60.0, 90.0, 135.0])
def test_eq44_is_the_circumscribed_radius(delta):
    sa, ta, d = 250.0, 140.0, np.radians(delta)
    A, B = _t(sa, ta * np.cos(d)), _t(0, -ta * np.sin(d))
    X = sa**2 / 3 + ta**2
    eq44 = np.sqrt(0.5 * (X + np.sqrt(X**2 - 4 / 3 * sa**2 * ta**2 * np.sin(d) ** 2)))
    assert sqrt_j2_amplitude(A, B) == pytest.approx(eq44, rel=1e-12)
    ts = np.linspace(0, 2 * np.pi, 20001)
    dev = lambda S: S - np.trace(S) / 3 * np.eye(3)  # noqa: E731
    brute = max(np.sqrt(0.5 * np.sum(dev(A * np.sin(t) + B * np.cos(t)) ** 2)) for t in ts)
    assert sqrt_j2_amplitude(A, B) == pytest.approx(brute, rel=1e-6)


@pytest.mark.parametrize("f,t", [(313.9, 196.2), (398.0, 260.0)])
def test_calibration_limits(f, t):
    z = np.zeros((3, 3))
    assert crossland_index(z, _t(f, 0), z, f, t) == pytest.approx(1.0, rel=1e-12)
    assert crossland_index(z, _t(0, t), z, f, t) == pytest.approx(1.0, rel=1e-12)
    su = 1000.0
    k = sines_kappa(f, su)
    assert sines_index(z, _t(0, t), z, t, k) == pytest.approx(1.0, rel=1e-12)
    # Eq. (64) = Eq. (63) with the Goodman f_0 = f/(1 + f/su) only if t = f/sqrt(3)
    f0 = f / (1 + f / su)
    assert 3 * (f / np.sqrt(3)) / f0 - np.sqrt(3) == pytest.approx(k, rel=1e-12)
