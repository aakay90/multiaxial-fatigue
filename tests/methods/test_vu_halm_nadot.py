"""VHN (roadmap N20): Vu, Halm & Nadot (2010) Int J Fatigue 32:1004-1014,
doi:10.1016/j.ijfatigue.2009.11.006 (Zotero 2J7T4PF3); Eqs. (6)-(21) pp.1005-1007 (crops
_audit-trail/phase2/crops/2J7T4PF3/p3.png, p4_*.png), Tables 1-12 pp.1008-1012 (Haiku transcription,
verified by reproduction). Tables 13-14 (different frequencies) are outside the single-harmonic scope.

The I^e column (proposed criterion) is reproduced on 117 of 119 rows within 0.06 points. Two rows are
printed inconsistently with their own error indices: Table 2 row 9 prints delta_xy = 0, but every
index of the row (and Papadopoulos et al. 1997 Table 1 row 19) corresponds to 90 deg; Table 11 row 1
prints Sigma_xx,a = 52.90, while I^a and I^e both correspond to 552.90.

The other columns cross-check repository methods on the same inputs: I^a (Crossland) 116/117 rows within 0.1
(Table 1 row 10 prints the I^c value under I^a; Papadopoulos 1997 gives -3.0), I^b (Dang Van in the
Papuga form, as DANGVAN) 115/117 within 0.15 (Table 4 rows 5, 8 off by 0.2-0.3), I^c (Papadopoulos,
the 1999 volumetric form) 117/117.
"""

import re

import numpy as np
import pytest
from _paper import DATA, load_table

from multifat.models.cp_methods.dangvan import dang_van_equivalent
from multifat.models.integral_methods.papadopoulos import papadopoulos_1999_index
from multifat.models.invariant_methods.crossland import crossland_index
from multifat.models.invariant_methods.vu_halm_nadot import (
    _elliptic_second_kind,
    j2_alternating,
    vhn_index,
    vhn_parameters,
)
from multifat.models.registry import get_models

Z = np.zeros((3, 3))
TABLES = range(1, 13)
MISPRINTS = {
    (2, 9): ("delta_xy", 90.0, "printed delta_xy = 0; all indices of the row correspond to 90 deg"),
    (11, 1): ("sigma_xx_a", 552.90, "printed Sigma_xx,a = 52.90; I^a and I^e correspond to 552.90"),
}


def _constants(k):
    txt = (DATA / f"vu2010_table{k}.csv").read_text(encoding="utf-8")
    pats = (r"f_-1\s*=\s*([\d.]+)", r"t_-1\s*=\s*([\d.]+)", r"R_m\s*=\s*([\d.]+)")
    return [float(re.search(p, txt).group(1)) for p in pats]


def _parts(d):
    """Sigma_ij(t) = Sigma_ij,m + Sigma_ij,a sin(wt - delta_ij) -> mean, sin and cos parts."""

    def g(key):
        v = d.get(key, 0.0)
        return 0.0 if v is None or v != v else float(v)

    M, A, B = np.zeros((3, 3)), np.zeros((3, 3)), np.zeros((3, 3))
    M[0, 0], M[1, 1] = g("sigma_xx_m"), g("sigma_yy_m")
    M[0, 1] = M[1, 0] = g("sigma_xy_m")
    A[0, 0] = g("sigma_xx_a")
    shear_phase = "delta_xy" if "delta_xy" in d else "delta_x"
    for (i, j), amp, ph in (
        ((1, 1), "sigma_yy_a", "delta_yy"),
        ((0, 1), "sigma_xy_a", shear_phase),
    ):
        x, p = g(amp), np.radians(g(ph))
        A[i, j] = A[j, i] = x * np.cos(p)
        B[i, j] = B[j, i] = -x * np.sin(p)
    return M, A, B


def _rows(skip_misprints=False):
    for k in TABLES:
        for r in load_table(f"vu2010_table{k}").itertuples():
            if (k, r.row) in MISPRINTS:
                if skip_misprints:
                    continue
                mark = pytest.mark.xfail(strict=True, reason=MISPRINTS[(k, r.row)][2])
                yield pytest.param(k, r._asdict(), id=f"T{k}r{r.row}", marks=mark)
            else:
                yield pytest.param(k, r._asdict(), id=f"T{k}r{r.row}")


@pytest.mark.parametrize("k,d", list(_rows()))
def test_tables_error_index(k, d):
    f, t, rm = _constants(k)
    assert 100 * (vhn_index(*_parts(d), f, t, rm) - 1) == pytest.approx(d["I_e"], abs=0.06)


@pytest.mark.parametrize("k,row", sorted(MISPRINTS))
def test_misprinted_rows_with_the_implied_value(k, row):
    key, value, _ = MISPRINTS[(k, row)]
    d = next(r._asdict() for r in load_table(f"vu2010_table{k}").itertuples() if r.row == row)
    d[key] = value
    f, t, rm = _constants(k)
    assert 100 * (vhn_index(*_parts(d), f, t, rm) - 1) == pytest.approx(d["I_e"], abs=0.06)
    assert 100 * (crossland_index(*_parts(d), f, t) - 1) == pytest.approx(d["I_a"], abs=0.1)


@pytest.mark.parametrize("k,d", list(_rows(skip_misprints=True)))
def test_cross_check_other_columns(k, d):
    f, t, _ = _constants(k)
    parts = _parts(d)
    if d.get("I_c") == d.get("I_c") and "I_c" in d:
        assert 100 * (papadopoulos_1999_index(*parts, f, t) - 1) == pytest.approx(d["I_c"], abs=0.1)
    if "I_a" in d and (k, d["row"]) != (1, 10):  # Table 1 row 10 prints I^c under I^a
        assert 100 * (crossland_index(*parts, f, t) - 1) == pytest.approx(d["I_a"], abs=0.1)
    if "I_b" in d and (k, d["row"]) not in ((4, 5), (4, 8)):
        assert 100 * (dang_van_equivalent(*parts, f, t) / f - 1) == pytest.approx(
            d["I_b"], abs=0.15
        )


@pytest.mark.parametrize("f,t,rm", [(313.9, 196.2, 680.0), (398.0, 260.0, 1025.0)])
def test_calibration_eqs_11_to_15(f, t, rm):
    """Reversed torsion and tension sit on the limit; the residual 3e-6 is the printed rounding of
    gamma2 (gamma1 + 4 gamma2/pi^2 = 1.000006, Eq. 13)."""
    g1, g2, _, _ = vhn_parameters(f, t, rm)
    assert g1 + 4 * g2 / np.pi**2 == pytest.approx(1.0, abs=1e-5)
    ax, to = np.diag([f, 0.0, 0.0]), np.zeros((3, 3))
    to[0, 1] = to[1, 0] = t
    assert vhn_index(Z, ax, Z, f, t, rm) == pytest.approx(1.0, abs=1e-5)
    assert vhn_index(Z, to, Z, f, t, rm) == pytest.approx(1.0, abs=1e-5)


def test_j2_mean_closed_form_and_ellipe():
    assert _elliptic_second_kind(0.0) == pytest.approx(np.pi / 2, rel=1e-15)
    assert _elliptic_second_kind(0.5) == pytest.approx(1.3506438810476755, rel=1e-14)
    A, B = np.diag([300.0, 0.0, 0.0]), np.zeros((3, 3))
    A[0, 1] = A[1, 0] = 100.0
    B[0, 1] = B[1, 0] = -150.0
    w = np.linspace(0, 2 * np.pi, 40001)[:-1]
    S = A[None] * np.sin(w)[:, None, None] + B[None] * np.cos(w)[:, None, None]
    D = S - np.trace(S, axis1=1, axis2=2)[:, None, None] / 3 * np.eye(3)
    j2 = np.sqrt(0.5 * np.sum(D * D, axis=(1, 2)))
    jmax, jmean = j2_alternating(A, B)
    assert jmax == pytest.approx(j2.max(), rel=1e-8)
    assert jmean == pytest.approx(j2.mean(), rel=1e-10)


def test_registry_case_model():
    (model,) = get_models(["VHN"])
    S = np.diag([250.0, 0.0, 0.0])
    p = {"Sigm1": 398.0, "Taum1": 260.0, "Su": 1025.0}
    assert model.evaluate_case(S0=S, S1=-S, E0=Z, E1=Z, params=p).values[""] == pytest.approx(
        vhn_index(Z, S, Z, 398.0, 260.0, 1025.0), rel=1e-12
    )
