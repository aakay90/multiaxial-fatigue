"""Findley (1959), doi:10.1115/1.4008327, checked against the PDF (Zotero GP5GUVFE).

The criterion maximises tau_thetaA + k sigma_thetaM over planes (Eqs. 2, 8-10, p.302). For in-phase
bending + torsion with proportional maximum stress the maximum is closed form: Eq. (18) combined,
Eq. (19) torsion, Eq. (24) bending; the zero-mean plane satisfies tan 2 theta = 1/k (Eq. 13), theta
being the angle between the plane normal and the greatest principal stress. The angles printed on
p.305 (torsion 42.2/40/21, bending 41.8/39/20.5 deg for k = 0.1/0.2/1.1) differ from Eq. (13)
(42.14/39.35/21.14 deg) by up to 0.65 deg and between loadings, although Eq. (13) is
loading-independent; they appear read from Fig. 4 (paper inconsistency).
"""

import numpy as np
import pytest
from _paper import bending_torsion, frame_with_normal, rotate

from multifat.eval.evaluator import best_cp_for_case
from multifat.models.cp_methods.fin import Findley
from multifat.planes.sampling import build_R_list

Z = np.zeros((3, 3))
KS = [0.1, 0.2, 0.3, 1.1]


def _sweep(S0, S1, k, n=36001):
    """Damage on planes whose normal lies in the x-y plane, angle phi from x (fine 1-D sweep)."""
    phis = np.linspace(0.0, np.pi, n)
    vals = []
    for phi in phis:
        R = frame_with_normal([np.cos(phi), np.sin(phi), 0.0])
        r = Findley().evaluate_on_plane(
            S0r=rotate(S0, R), S1r=rotate(S1, R), E0r=Z, E1r=Z, params={"k_FI": k}
        )
        vals.append(r.damage)
    i = int(np.argmax(vals))
    return vals[i], phis[i]


def _eq18(sA, tA, sM, tM, k):
    return np.sqrt((sA / 2) ** 2 + tA**2 + k**2 * ((sM / 2) ** 2 + tM**2)) + k * sM / 2


def _cycle(sA, tA, sM, tM):
    """Endpoints of an in-phase cycle with maximum (sM, tM) and amplitude (sA, tA)."""
    return bending_torsion(sM, tM), bending_torsion(sM - 2 * sA, tM - 2 * tA)


@pytest.mark.parametrize("k", KS)
@pytest.mark.parametrize(
    "sA,tA,sM,tM",
    [
        (0.0, 100.0, 0.0, 100.0),  # Eq. (19), zero mean torsion
        (0.0, 100.0, 0.0, 160.0),  # Eq. (19), mean torsion
        (200.0, 0.0, 200.0, 0.0),  # Eq. (24), zero mean bending
        (200.0, 0.0, 300.0, 0.0),  # Eq. (24), tensile mean bending
        (200.0, 0.868 * 200.0, 200.0, 0.868 * 200.0),  # Eq. (18), a = 0.868 (Fig. 3)
        (150.0, 0.868 * 150.0, 240.0, 0.868 * 240.0),  # Eq. (18), proportional mean
    ],
)
def test_closed_form_maximum(sA, tA, sM, tM, k):
    S0, S1 = _cycle(sA, tA, sM, tM)
    exact = _eq18(sA, tA, sM, tM, k)
    swept, _ = _sweep(S0, S1, k)
    assert swept == pytest.approx(exact, rel=1e-7)
    grid = best_cp_for_case(
        S0=S0, S1=S1, E0=Z, E1=Z, R_list=build_R_list(), method=Findley(), params={"k_FI": k}
    )
    # Refined search (finding F2) reaches the continuous maximum.
    assert grid.by_metric == pytest.approx(exact, rel=1e-8)
    assert grid.ext == grid.by_metric


@pytest.mark.parametrize("k", KS)
@pytest.mark.parametrize("loading", ["torsion", "bending"])
def test_zero_mean_plane_angle_eq13(k, loading):
    S0 = bending_torsion(*((0.0, 100.0) if loading == "torsion" else (200.0, 0.0)))
    _, phi = _sweep(S0, -S0, k)
    w, v = np.linalg.eigh(S0)
    e1 = v[:, 2]
    n = np.array([np.cos(phi), np.sin(phi), 0.0])
    theta = np.degrees(np.arccos(abs(n @ e1)))
    theta = min(theta, 90.0 - theta)  # p.305: "the smaller of the two possible values"
    assert theta == pytest.approx(np.degrees(0.5 * np.arctan(1.0 / k)), abs=0.01)


def test_printed_zero_mean_angles_are_rounded_figure_readings():
    """Documented inconsistency: p.305 values vs Eq. (13); within 0.65 deg, not exact."""
    eq13 = {k: np.degrees(0.5 * np.arctan(1 / k)) for k in (0.1, 0.2, 1.1)}
    printed = {"torsion": (42.2, 40.0, 21.0), "bending": (41.8, 39.0, 20.5)}
    for values in printed.values():
        dev = [abs(p - eq13[k]) for p, k in zip(values, (0.1, 0.2, 1.1))]
        assert max(dev) < 0.7 and max(dev) > 0.05


def test_limit_ratios_eq22_eq27():
    """p.303: l = (1+k^2)^1/2/k -> 10.1, 5.1, 1.35; l' = [k+(1+k^2)^1/2]/2k -> 5.5, 3.1, 1.18.

    Printed to loose rounding (10.05 -> 10.1, 3.05 -> 3.1)."""
    for k, l, lp in [(0.1, 10.1, 5.5), (0.2, 5.1, 3.1), (1.1, 1.35, 1.18)]:
        assert np.sqrt(1 + k**2) / k == pytest.approx(l, abs=0.06)
        assert (k + np.sqrt(1 + k**2)) / (2 * k) == pytest.approx(lp, abs=0.06)
