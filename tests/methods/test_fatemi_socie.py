"""FS, Fatemi & Socie (1988), doi:10.1111/j.1460-2695.1988.tb01169.x, checked against PDF
(5HD8Q5JR p.12, printed 160): Eq. (8) gamma_max (1 + n sigma_n^max / sigma_y) = constant, with
gamma_max the engineering maximum shear strain amplitude (Eq. 9 starts with (1+nu_e) s'_f/E).
The repository's k_FS is n; sigma_y is the workbook yield strength; sigma_n^max is clipped at zero
(adaptation). Eq. (10) coefficients follow from n = 0.6, nu_e = 0.29, nu_p = 0.5.
"""

import numpy as np
import pytest

from multifat.eval.evaluator import best_cp_for_case
from multifat.models.cp_methods.fs import FatemiSocie
from multifat.planes.sampling import build_R_list

E, NU, SY = 200000.0, 0.3, 380.0


def _strain(s):
    return ((1 + NU) * s - NU * np.trace(s) * np.eye(3)) / E


def test_eq10_coefficients_from_eq9():
    n, ne, npl = 0.6, 0.29, 0.5
    assert [1 + ne, n / 2 * (1 + ne), 1 + npl, n / 2 * (1 + npl)] == pytest.approx(
        [1.29, 0.387, 1.50, 0.45]
    )


@pytest.mark.parametrize("k", [0.0, 0.6, 1.0])
def test_tension_with_mean(k):
    """Uniaxial: max shear plane at 45 deg, gamma_a = (1+nu) eps_a, sigma_n^max = sigma_max/2."""
    s_m, s_a = 120.0, 250.0
    S0, S1 = np.diag([s_m + s_a, 0, 0]), np.diag([s_m - s_a, 0, 0])
    expected = (1 + NU) * s_a / E * (1 + k * (s_m + s_a) / 2 / SY)
    best = best_cp_for_case(
        S0=S0,
        S1=S1,
        E0=_strain(S0),
        E1=_strain(S1),
        R_list=build_R_list(),
        method=FatemiSocie(),
        params={"k_FS": k, "Sy": SY},
    )
    assert best.by_metric == pytest.approx(expected, rel=1e-8)


def test_pure_shear_gamma_is_engineering_amplitude():
    tau = 150.0
    S0 = np.zeros((3, 3))
    S0[0, 1] = S0[1, 0] = tau
    best = best_cp_for_case(
        S0=S0,
        S1=-S0,
        E0=_strain(S0),
        E1=_strain(-S0),
        R_list=build_R_list(),
        method=FatemiSocie(),
        params={"k_FS": 0.6, "Sy": SY},
    )
    assert best.by_metric == pytest.approx(tau / (E / (2 * (1 + NU))), rel=1e-8)
