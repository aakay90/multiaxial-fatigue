"""ZHU_EDP kernel, Zhu et al. (2019) Int J Fatigue 121:1-8, doi:10.1016/j.ijfatigue.2018.11.025
(Zotero 26XCQ9S3, accepted manuscript; folio = PDF page - 1).

Eqs. (19)-(23), pp.13-14 (crops _audit-trail/phase2/crops/26XCQ9S3/p14.png, p15.png). The paper
prints no psi values (Fig. 6a only) and F_NP needs measured stress amplitudes, so the checks are
the special cases stated on p.14: uniaxial dW_eq = dW_0, pure shear xi dW_0, and case IX (45 deg
proportional) (1 + xi) dW_0 with I_XX = I_YY = D^2/12. The last one is a misprint: a straight
45 deg path of enclosing diameter D has I_XX = I_YY = D^2/24, so F_1 = (1 + xi)/sqrt(2).
"""

import numpy as np
import pytest

from multifat.models.energy_based_methods.zhu_edp import (
    delta_w0,
    f_np,
    moi_factor,
    strain_path,
    zhu_edp,
)

XI = 0.15  # 316L, p.14
Z = np.zeros((3, 3))


def _tt(eps, gam):
    """Tension-torsion strain tensor, axial yy (workbook convention), engineering gamma_xy."""
    e = np.zeros((3, 3))
    e[1, 1] = eps
    e[0, 1] = e[1, 0] = gam / 2
    return e


def _f1(E_mean, E_sin, E_cos):
    return moi_factor(*strain_path(E_mean, E_sin, E_cos), XI)


def test_uniaxial_gives_dw0():
    F1, D = _f1(Z, _tt(0.004, 0), Z)
    assert F1 == pytest.approx(1.0, abs=1e-5)
    assert D == pytest.approx(2 * 0.004 * 1.5, rel=1e-6)


def test_pure_shear_gives_xi():
    assert _f1(Z, _tt(0, 0.006), Z)[0] == pytest.approx(XI, abs=1e-5)


def test_case_ix_45deg_proportional():
    g = 0.004 * np.sqrt(3)  # equal axes in the (eps, gamma/sqrt3) diagram
    assert _f1(Z, _tt(0.004, g), Z)[0] == pytest.approx((1 + XI) / np.sqrt(2), abs=1e-5)


@pytest.mark.xfail(strict=True, reason="p.14 prints (1 + xi) dW_0 with I = D^2/12 (misprint)")
def test_case_ix_as_printed():
    g = 0.004 * np.sqrt(3)
    assert _f1(Z, _tt(0.004, g), Z)[0] == pytest.approx(1 + XI, abs=1e-3)


def test_circle_path():
    """Circle of diameter D: I_XX = I_YY = D^2/8, F_1 = (1 + xi) sqrt(3/2)."""
    g = 0.004 * np.sqrt(3)
    F1, _ = _f1(Z, _tt(0.004, 0), _tt(0, g))
    assert F1 == pytest.approx((1 + XI) * np.sqrt(1.5), rel=1e-5)


def test_mean_strain_does_not_enter_f1():
    a = _f1(Z, _tt(0.003, 0.004), _tt(0, 0.002))[0]
    b = _f1(_tt(0.002, -0.001), _tt(0.003, 0.004), _tt(0, 0.002))[0]
    assert b == pytest.approx(a, rel=1e-12)


def test_f_np_limits():
    assert f_np(300.0, 300.0, 420.0) == 0.0
    assert f_np(420.0, 300.0, 420.0) == pytest.approx(1.0)


def test_delta_w0_elastic_limit_and_eq23():
    E = 193000.0
    assert delta_w0(0.001, E, H_c=1e12, h_c=0.123) == pytest.approx(E * 0.001**2 / 2, rel=1e-6)
    w = delta_w0(0.004, E, H_c=1660.0, h_c=0.123)
    assert w > E * 0.004**2 / 2 * 0.1
    assert zhu_edp(1.0, 0.0, w, 0.38) == w
    assert zhu_edp(XI, 1.0, w, 0.38) == pytest.approx(XI * 1.38 * w)
