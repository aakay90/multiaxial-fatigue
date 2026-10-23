"""MCD, McDiarmid (1991), doi:10.1111/j.1460-2695.1991.tb00673.x, checked against PDF
(9FG5X4ZG p.9, printed 437): Eq. (7)/(8) tau_a/t_AB + sigma_n,max/(2 sigma_T) = 1 on the plane of
maximum shear stress amplitude, sigma_n,max = amplitude + mean, sigma_T = ultimate tensile
strength. The repository implements case A (t_A = t, combined bending and twisting); case B
(t_B) and the validity range 0 <= sigma_n,max <= sigma_T are not enforced (adaptation).
"""

import numpy as np
import pytest
from _paper import bending_torsion

from multifat.eval.evaluator import best_cp_for_case
from multifat.models.cp_methods.mcdiarmid import McDiarmid
from multifat.planes.sampling import build_R_list

T, SU = 280.0, 900.0
Z = np.zeros((3, 3))


def _damage(sigma, tau, mean=(0.0, 0.0)):
    S_a, S_m = bending_torsion(sigma, tau), bending_torsion(*mean)
    best = best_cp_for_case(
        S0=S_m + S_a,
        S1=S_m - S_a,
        E0=Z,
        E1=Z,
        R_list=build_R_list(),
        method=McDiarmid(),
        params={"Su": SU, "Taum1": T},
    )
    return best.by_metric


def test_reversed_torsion_gives_t():
    assert _damage(0.0, T) == pytest.approx(T, rel=1e-8)


def test_eq8_line_in_bending():
    """Reversed bending sigma: tau_a = sigma_n,max = sigma/2; Eq. (8) => sigma = 2t/(1 + t/(2 sT))."""
    sigma = 2 * T / (1 + T / (2 * SU))
    assert _damage(sigma, 0.0) == pytest.approx(T, rel=1e-8)


def test_mean_normal_stress_enters_sigma_n_max():
    """Torsion amplitude t/2 with axial mean m: the x-face (a maximum-shear-amplitude plane,
    tied with the y-face; ties resolve to the larger damage) carries sigma_n,max = m."""
    m = 300.0
    assert _damage(0.0, T / 2, mean=(m, 0.0)) == pytest.approx(T / 2 + T / (2 * SU) * m, rel=1e-8)
