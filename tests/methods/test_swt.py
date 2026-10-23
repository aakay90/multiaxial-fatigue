"""SWT, Smith, Watson & Topper (1970), J. Mater. 5:767-778 (no DOI; Zotero NARDSIKJ, image scan).

p.2 (printed 769): "the function is sigma_max eps_a where sigma_max is the maximum tensile stress
and eps_a is the strain amplitude", applied as sqrt(sigma_max eps_a E). The repository uses the
product sigma_max eps_a (a monotone transform: Basquin-fitted lives are unchanged, log-damage
errors are doubled) on the plane of maximum normal strain range (critical-plane extension, not in
the 1970 paper).
"""

import numpy as np
import pytest

from multifat.eval.evaluator import best_cp_for_case
from multifat.models.cp_methods.swt import SWT
from multifat.planes.sampling import build_R_list

E, NU = 200000.0, 0.3


def _uniaxial(s_mean, s_amp):
    def strain(s):
        return np.diag([s, -NU * s, -NU * s]) / E

    smax, smin = s_mean + s_amp, s_mean - s_amp
    return np.diag([smax, 0, 0]), np.diag([smin, 0, 0]), strain(smax), strain(smin)


@pytest.mark.parametrize("s_mean,s_amp", [(0.0, 300.0), (150.0, 200.0), (-100.0, 250.0)])
def test_uniaxial_product(s_mean, s_amp):
    S0, S1, E0, E1 = _uniaxial(s_mean, s_amp)
    expected = max(s_mean + s_amp, 0.0) * (s_amp / E)
    r = SWT().evaluate_on_plane(
        S0r=S0[[1, 2, 0]][:, [1, 2, 0]],
        S1r=S1[[1, 2, 0]][:, [1, 2, 0]],
        E0r=E0[[1, 2, 0]][:, [1, 2, 0]],
        E1r=E1[[1, 2, 0]][:, [1, 2, 0]],
        params={},
    )
    assert r.damage == pytest.approx(expected, rel=1e-13)
    best = best_cp_for_case(
        S0=S0, S1=S1, E0=E0, E1=E1, R_list=build_R_list(), method=SWT(), params={}
    )
    assert best.by_metric == pytest.approx(expected, rel=1e-3)


def test_compressive_cycle_has_zero_parameter():
    """sigma_max is the maximum *tensile* stress: a fully compressive cycle gives zero."""
    S0, S1, E0, E1 = _uniaxial(-400.0, 100.0)
    best = best_cp_for_case(
        S0=S0, S1=S1, E0=E0, E1=E1, R_list=build_R_list(), method=SWT(), params={}
    )
    assert best.by_metric == 0.0
