"""MWCM (roadmap N04): Susmel & Lazzarin (2002) Fatigue Fract Engng Mater Struct 25:63-78,
doi:10.1046/j.1460-2695.2002.00462.x (Zotero S9FH4PEP); Eqs. (5), (8)-(13) pp.68-72 (crops
_audit-trail/phase2/crops/S9FH4PEP/p8_*.png, p10_*.png).

The paper lists series constants only (Table 1, smooth specimens) and states error bands: about
+-20 % in phase and +-30 % out of phase (p.73). Several series coincide with the Papadopoulos et al.
(1997) Table 1 tests (same f_-1, t_-1). On those 43 tests the result depends on the unspecified tie
rule between planes of equal maximum tau_a (two planes in phase with mean stress, a continuum for
the degenerate sigma_a = 2 tau_a out-of-phase cases): the larger damage (repository convention)
gives 12/16 in-phase rows within +-20 % and 24/27 out-of-phase rows within +-30 % (row 30: +173 %);
the smaller damage 14/16 and 20/27. Unresolved; not a test oracle.
"""

import numpy as np
import pytest
from _paper import bending_torsion

from multifat.eval.evaluator import best_cp_for_case
from multifat.models.cp_methods.mwcm import MWCM, mwcm_damage, mwcm_reference_shear
from multifat.models.registry import get_models
from multifat.planes.sampling import build_R_list

Z = np.zeros((3, 3))
S_A, T_A = 313.9, 196.2


def _best(sigma, tau, mean=(0.0, 0.0)):
    S, M = bending_torsion(sigma, tau), bending_torsion(*mean)
    return best_cp_for_case(
        S0=M + S,
        S1=M - S,
        E0=Z,
        E1=Z,
        R_list=build_R_list(),
        method=MWCM(),
        params={"Sigm1": S_A, "Taum1": T_A},
    )


def test_eq8_reference_points():
    assert mwcm_reference_shear(0.0, S_A, T_A) == pytest.approx(T_A)
    assert mwcm_reference_shear(1.0, S_A, T_A) == pytest.approx(S_A / 2)


def test_calibration_and_no_ext():
    """Reversed torsion (rho = 0) and reversed axial (rho = 1) sit on the limit, Eq. (11)."""
    assert _best(0.0, T_A).by_metric == pytest.approx(1.0, rel=1e-9)
    assert _best(S_A, 0.0).by_metric == pytest.approx(1.0, rel=1e-9)
    (model,) = get_models(["MWCM"])
    S = bending_torsion(S_A, 0.0)
    assert set(
        model.evaluate_case(
            S0=S, S1=-S, E0=Z, E1=Z, params={"Sigm1": S_A, "Taum1": T_A}, R_list=build_R_list()
        ).values
    ) == {""}


def test_eq13_is_damage_minus_one():
    """E = X/(beta - alpha Y) - 1 with X = tau_a, Y = rho, alpha = tau_A - sigma_A/2, beta = tau_A."""
    tau_a, sigma = 150.0, 90.0
    alpha, beta = T_A - S_A / 2, T_A
    E = tau_a / (beta - alpha * sigma / tau_a) - 1
    assert mwcm_damage(tau_a, sigma, S_A, T_A) - 1 == pytest.approx(E, rel=1e-12)


def test_mean_normal_stress_and_cutoff():
    """In-phase bending sigma with mean m: tau_a = sigma/2, sigma_n,max = (sigma + m)/2."""
    sigma, m = 200.0, 100.0
    rho = (sigma + m) / sigma
    expected = (sigma / 2) / mwcm_reference_shear(rho, S_A, T_A)
    assert _best(sigma, 0.0, mean=(m, 0.0)).by_metric == pytest.approx(expected, rel=1e-9)
    rho_cut = T_A / (T_A - S_A / 2)
    assert mwcm_damage(100.0, 100.0 * (rho_cut + 0.1), S_A, T_A) == np.inf
    assert mwcm_damage(0.0, -50.0, S_A, T_A) == 0.0


def test_ties_resolve_to_larger_normal_stress():
    """Torsion amplitude with an axial mean: the x- and y-faces tie in tau_a; the x-face carries
    sigma_n,max = m (repository tie rule; the paper gives none)."""
    t, m = 120.0, 150.0
    expected = t / mwcm_reference_shear(m / t, S_A, T_A)
    assert _best(0.0, t, mean=(m, 0.0)).by_metric == pytest.approx(expected, rel=1e-9)
