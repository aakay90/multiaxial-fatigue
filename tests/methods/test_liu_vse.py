"""VSE (roadmap G15): Liu (1993) ASTM STP 1191:67-84, doi:10.1520/STP24796S (Zotero
2RICPREE); Eqs. (7)-(11) pp.70-73 (crops _audit-trail/phase2/crops/2RICPREE/p4.png, p7.png). The
paper's results are figures only (its one printed curve, Fig. 9, has coefficients 34 435 and 1 126
that do not match the plot; 344.35 and 11.26 do), so the tests check the stated identities on elastic
strains: Eq. (11) uniaxial, equal modes in torsion (p.73), and Eq. (7) >= Eq. (8).
"""

import numpy as np
import pytest
from _paper import bending_torsion

from multifat.eval.evaluator import best_cp_for_case
from multifat.models.cp_methods.liu_vse import LiuVSE
from multifat.planes.sampling import build_R_list

E, NU = 200000.0, 0.3


def _strain(S):
    return ((1 + NU) * S - NU * np.trace(S) * np.eye(3)) / E


def _best(mode, S):
    return best_cp_for_case(
        S0=S,
        S1=-S,
        E0=_strain(S),
        E1=_strain(-S),
        R_list=build_R_list(),
        method=LiuVSE(),
        params={"vse_mode": mode},
    )


def test_eq11_uniaxial():
    """Mode I plane normal to the load: Delta W_I = (2 sigma)(2 eps); Mode II at 45 deg:
    4 sigma eps ((1 + nu)/4 + (1 - nu)/4) = half of it (elastic strains)."""
    s = 300.0
    w = (2 * s) * (2 * s / E)
    assert _best(1, bending_torsion(s, 0.0)).by_metric == pytest.approx(w, rel=1e-9)
    assert _best(2, bending_torsion(s, 0.0)).by_metric == pytest.approx(w / 2, rel=1e-9)


def test_torsion_modes_coincide():
    t = 180.0
    expected = 4 * t**2 * (1 + NU) / E
    for mode in (1, 2):
        assert _best(mode, bending_torsion(0.0, t)).by_metric == pytest.approx(expected, rel=1e-9)


@pytest.mark.parametrize("s,t", [(300.0, 100.0), (150.0, 200.0)])
def test_eq7_total_maximum_bounds_eq8(s, t):
    best = _best(1, bending_torsion(s, t))
    assert best.ext >= best.by_metric * (1 - 1e-12)
