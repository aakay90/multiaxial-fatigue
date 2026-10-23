"""BP (Boehme & Papuga 2024, doi:10.1111/ffe.14281) and CAIM (Boehme, Papuga & Lange 2026,
doi:10.1111/ffe.70244), checked against the PDFs (GCDJT3CQ p.11; 5T8PJV87 pp.3-9).

BP Eq. (16) (2024) carries 1/(4 pi); the 2026 restatement Eq. (6), and CAIM Eq. (7), print the
integral without it. With the printed coefficients only the sphere average reproduces the uniaxial
limits and the paper's own closed forms Eqs. (17)-(18), so the 2026 omission is a paper misprint.
Table 4 (p.8) statistics for the 18 Table 2 cases are reproduced from 17 computable cases; its
PM10 = 79.0 % is not a multiple of 1/18 (paper misprint; 83.3 % follows from its other values).
"""

import numpy as np
import pytest
from _paper import load_table

from multifat.models.registry import get_models

Z = np.zeros((3, 3))
BP, CAIM = get_models(["BP", "CAIM"])


def _fi(model, mean, sin, params, cos=Z):
    return model.evaluate_case(
        S0=mean + sin,
        S1=mean - sin,
        E0=Z,
        E1=Z,
        params=params,
        harmonics={"S_mean": mean, "S_sin": sin, "S_cos": cos},
    ).values[""]


def _params(kappa, s=300.0):
    return dict(Sigm1=s, Taum1=s / kappa, Sig0=1.6 * s, Tau0=1.8 * s / kappa)


@pytest.mark.parametrize("kappa", [1.0, 1.2, 1.4, 1.6, 1.7])
def test_eq17_bp_closed_forms(kappa):
    p, sa = _params(kappa), 100.0
    bi, tri = np.diag([sa, sa, 0.0]), np.diag([sa, sa, sa])
    assert _fi(BP, Z, bi, p) * p["Sigm1"] == pytest.approx(
        2 * sa * np.sqrt(1 - kappa**2 / 4), rel=1e-10
    )
    assert _fi(BP, Z, tri, p) * p["Sigm1"] == pytest.approx(
        3 * sa * np.sqrt(1 - kappa**2 / 3), rel=1e-10
    )


@pytest.mark.parametrize("kappa", [1.0, 1.3, np.sqrt(2.0), 1.6, 1.9])
def test_eq18_caim_closed_forms(kappa):
    p, sa = _params(kappa), 100.0
    bi, tri = np.diag([sa, sa, 0.0]), np.diag([sa, sa, sa])
    assert _fi(CAIM, Z, bi, p) * p["Sigm1"] == pytest.approx(sa, rel=1e-6)
    expected_tri = sa if kappa < np.sqrt(2) else kappa * sa * np.sqrt(1 - kappa**2 / 4)
    assert _fi(CAIM, Z, tri, p) * p["Sigm1"] == pytest.approx(expected_tri, rel=1e-10)


def _table2_errors(model):
    rows = load_table("bohme2026_table2")
    out = []
    for r in rows.itertuples():
        if np.isnan(r.s_0):
            out.append(np.nan)
            continue
        p = dict(Sigm1=r.s_m1, Taum1=r.t_m1, Sig0=r.s_0)
        if not np.isnan(r.t_0):
            p["Tau0"] = r.t_0
        mean, sin = Z.copy(), Z.copy()
        mean[0, 0] = r.sigma_xm
        sin[0, 1] = sin[1, 0] = r.tau_xya
        out.append(100 * (_fi(model, mean, sin, p) - 1))  # Eq. (9), percent
    return np.array(out)


def test_table4_statistics_reproduced():
    bp, caim = _table2_errors(BP), _table2_errors(CAIM)
    np.testing.assert_allclose(bp, caim, rtol=1e-9, equal_nan=True)  # "identical" (p.8)
    v = bp[np.isfinite(bp)]
    assert len(v) == 17
    assert v.min() == pytest.approx(-8.0, abs=0.05)  # Table 4 Min
    assert v.max() == pytest.approx(16.2, abs=0.15)  # Table 4 Max (quadrature, rounding)
    se = 18 * 1.8 - v.sum()  # SE implied by the printed mean
    full = np.append(v, se)
    assert full.std() == pytest.approx(7.8, abs=0.06)  # Table 4 SD (population)
    assert full.max() - full.min() == pytest.approx(24.2, abs=0.2)  # Table 4 Range
    assert 100 * np.mean(abs(full) <= 10) == pytest.approx(100 * 15 / 18)
    assert all(abs(100 * k / 18 - 79.0) > 1 for k in range(19))  # printed PM10 impossible
