"""RFB (roadmap G41): Robert, Fogue & Bahuaud (1994) ASTM STP 1231:369-387, doi:10.1520/STP13959S
(Zotero 2XJVX5XJ); Eqs. (15)-(25) pp.379-381, Appendix p.386, Tables 1-3 pp.383-385 (crops
_audit-trail/phase2/crops/2XJVX5XJ/p11_*, p12_*, p18_*, p15-p17).

Source issues confirmed here: Eq. (16) prints 1/pi where Eqs. (8) and (18)-(24) need 1/(4 pi);
the Appendix omits the 1/2 under the root of a (Eqs. 20 and 24 require it); Eq. (18) prints E
for E^2.

Tables 1-3 (59 tests, Haiku transcription verified by reproduction): the validity parameter I = E
(Eq. 27) is reproduced to print rounding (0.006) on 52 rows. Table 1 rows 1, 2, 5, 6, 7, 12 are
0.006-0.015 off (unresolved; biaxial tension-pressure rows); Table 3 row 11 (delta = 45, printed
1.04, Eq. 16 gives 1.073) breaks its own phase series (rows 10, 12, 13 match; 1.04 needs delta near
80 deg).
"""

import numpy as np
import pytest
from _paper import load_table

from multifat.models.integral_methods.robert_fogue_bahuaud import rfb_index, rfb_parameters
from multifat.models.registry import get_models

Z = np.zeros((3, 3))
MATERIALS = [(423.0, 287.0, 712.0), (361.0, 228.0, 600.0), (695.0, 415.0, 1040.0)]


def _axial(s):
    A = np.zeros((3, 3))
    A[0, 0] = s
    return A


def _shear(t):
    A = np.zeros((3, 3))
    A[0, 1] = A[1, 0] = t
    return A


@pytest.mark.parametrize("s,t,s0", MATERIALS)
def test_appendix_solves_eqs_20_21_24(s, t, s0):
    a, b, d = rfb_parameters(s, t, s0)
    assert 2 * a**2 + 3 * b**2 + 4 * a * b == pytest.approx(15.0, rel=1e-12)
    assert 6 * a**2 + 4 * b**2 + 7 * a * b == pytest.approx(15 * s**2 / t**2, rel=1e-12)
    assert 15 + 3 * d**2 + 6 * b * d + 4 * a * d == pytest.approx(60 * s**2 / s0**2, rel=1e-12)
    # the printed a, without the 1/2 under the root, violates Eq. (20)
    a_printed = np.sqrt(12 * s**2 / t**2 - 21 + b**2)
    assert 2 * a_printed**2 + 3 * b**2 + 4 * a_printed * b != pytest.approx(15.0, rel=1e-2)


@pytest.mark.parametrize("s,t,s0", MATERIALS)
def test_calibration_points(s, t, s0):
    """Reversed tension, pulsating tension (sigma_M = sigma_A = s_0/2) and reversed torsion."""
    assert rfb_index(Z, _axial(s), Z, s, t, s0) == pytest.approx(1.0, rel=2e-4)
    assert rfb_index(_axial(s0 / 2), _axial(s0 / 2), Z, s, t, s0) == pytest.approx(1.0, rel=2e-4)
    assert rfb_index(Z, _shear(t), Z, s, t, s0) == pytest.approx(1.0, rel=2e-4)


@pytest.mark.parametrize("s,t,s0", MATERIALS)
def test_eq19_tension_haigh_curve(s, t, s0):
    """Eq. (19) with c = 0: 15 s^2 E^2 = (2a^2+3b^2+4ab) sA^2 + 3 d^2 sM^2 + 2d(3b+2a) sA sM."""
    a, b, d = rfb_parameters(s, t, s0)
    sA, sM = 0.6 * s, 0.3 * s
    e2 = (15 * sA**2 + 3 * d**2 * sM**2 + 2 * d * (3 * b + 2 * a) * sA * sM) / (15 * s**2)
    assert rfb_index(_axial(sM), _axial(sA), Z, s, t, s0) ** 2 == pytest.approx(e2, rel=4e-4)


@pytest.mark.parametrize("s,t,s0", MATERIALS)
def test_eq23_torsion_haigh_curve(s, t, s0):
    """Eq. (23) with c = 0: 15 s^2 E^2 = (6a^2+4b^2+7ab) tA^2 + 4 d^2 tM^2 (mean shear acts only
    through the normal stresses of oblique planes)."""
    a, b, d = rfb_parameters(s, t, s0)
    tA, tM = 0.8 * t, 0.4 * t
    e2 = ((6 * a**2 + 4 * b**2 + 7 * a * b) * tA**2 + 4 * d**2 * tM**2) / (15 * s**2)
    assert rfb_index(_shear(tM), _shear(tA), Z, s, t, s0) ** 2 == pytest.approx(e2, rel=4e-4)


def test_validity_range():
    with pytest.raises(ValueError):
        rfb_parameters(400.0, 380.0, 700.0)  # t/s = 0.95
    with pytest.raises(ValueError):
        rfb_parameters(400.0, 200.0, 700.0)  # t/s = 0.5


def test_registry_case_model():
    (model,) = get_models(["RFB"])
    S = _axial(250.0) + _shear(120.0)
    p = {"Sigm1": 361.0, "Taum1": 228.0, "Sig0": 600.0}
    assert model.evaluate_case(S0=S, S1=-S, E0=Z, E1=Z, params=p).values[""] == pytest.approx(
        rfb_index(Z, S, Z, 361.0, 228.0, 600.0), rel=1e-12
    )


TABLES = {1: (423.0, 287.0, 712.0), 2: (361.0, 228.0, 600.0), 3: (695.0, 415.0, 1040.0)}
UNRESOLVED = {(1, 1), (1, 2), (1, 5), (1, 6), (1, 7), (1, 12), (3, 11)}


def _value(d, key):
    v = d.get(key, 0.0)
    return 0.0 if v != v else float(v)


def _history(d):
    """sigma_ij(t) = sigma_ij,m + sigma_ij,a sin(wt + delta) -> mean, sin and cos parts."""
    M, A, B = np.zeros((3, 3)), np.zeros((3, 3)), np.zeros((3, 3))
    M[0, 0], M[1, 1] = _value(d, "sigma_11m"), _value(d, "sigma_22m")
    M[0, 1] = M[1, 0] = _value(d, "sigma_12m")
    A[0, 0] = _value(d, "sigma_11a")
    for (i, j), amp, phase in (((1, 1), "sigma_22a", "delta_2"), ((0, 1), "sigma_12a", "delta_12")):
        x, p = _value(d, amp), np.radians(_value(d, phase))
        A[i, j] = A[j, i] = x * np.cos(p)
        B[i, j] = B[j, i] = x * np.sin(p)
    return M, A, B


def _table_rows():
    for k in TABLES:
        for r in load_table(f"robert1994_table{k}").itertuples():
            marks = ()
            if (k, r.row) in UNRESOLVED:
                marks = pytest.mark.xfail(strict=True, reason="unresolved, see module docstring")
            yield pytest.param(k, r._asdict(), id=f"T{k}r{r.row}", marks=marks)


@pytest.mark.parametrize("k,d", list(_table_rows()))
def test_tables_validity_parameter(k, d):
    assert rfb_index(*_history(d), *TABLES[k]) == pytest.approx(d["I"], abs=0.006)
