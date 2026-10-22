"""SWTD, Kujawski (2014) Int J Fatigue, doi:10.1016/j.ijfatigue.2013.12.002 (Zotero RKWHX6W4).

Eq. (25) p.7: SWTD = MAX{S_max,i |e_a,i|, S_min,i |e_a,i|}, deviatoric stresses of the maximum and
minimum states and principal deviatoric strain amplitudes, index i = the same principal direction
(Eqs. 23-24 are written in one frame). nu_eff = 0.5 - (0.5 - nu) dsigma_eq / (E deps_eq) (p.6).

Paper checks (crop _audit-trail/phase2/crops/RKWHX6W4/p6.png):
- Table 2 (uniaxial compression-compression): Eq. (25) with nu_eff (nu = 0.3, E = 71.7 GPa)
  reproduces 10 of 11 rows within 0.7 %; the last row is 3.4 % high in print (misprint).
- Table 3 path A (torsion): the printed values are tau_a gamma_a / sqrt(3), i.e. the paper uses the
  equivalent strain gamma/sqrt(3) (its Fig. 11 axes) where Eq. (25) gives the principal deviatoric
  strain gamma/2: a constant factor 2/sqrt(3). Row 10 (0.58 printed, 0.61 computed) is off.
- Paths B, C, D are not acceptance targets: B matches only independently sorted eigenvalues (which
  contradicts Table 2), C and D match no single reading; the paper gives no NP procedure.
"""

import numpy as np
import pytest

from multifat.models.energy_based_methods.swtd import SWTD, swtd_eq25, swtd_single_harmonic

from _paper import load_table

E_AL = 71700.0


def _tens(s, t=0.0):
    return np.array([[s, t, 0.0], [t, 0.0, 0.0], [0.0, 0.0, 0.0]])


def _strain(e, g=0.0, nu=0.3):
    return np.array([[e, g / 2, 0.0], [g / 2, -nu * e, 0.0], [0.0, 0.0, -nu * e]])


def _rows(name, mark_rows):
    t = load_table(name)
    return [
        (
            pytest.param(r, marks=pytest.mark.xfail(strict=True, reason=mark_rows[i]))
            if i in mark_rows
            else r
        )
        for i, r in enumerate(t.itertuples())
    ]


@pytest.mark.parametrize(
    "row", _rows("kujawski2014_table2", {10: "printed 0.335, Eq. (25) gives 0.324 (misprint)"})
)
def test_table2_uniaxial_compression(row):
    ea = row.eps_a_pct / 100
    nu_eff = 0.5 - 0.2 * row.sigma_a / (E_AL * ea)
    smax, smin = row.sigma_m + row.sigma_a, row.sigma_m - row.sigma_a
    v = swtd_eq25(_tens(smax), _tens(smin), _strain(ea, nu=nu_eff))
    # eps_a is printed to 0.01 %: up to 1.4 % of the value; SWTD to 0.001
    tol = 0.005 / row.eps_a_pct + 0.0005 / row.swtd
    assert v == pytest.approx(row.swtd, rel=tol)
    if not np.isnan(row.swt):
        assert smax * ea == pytest.approx(row.swt, abs=6e-4)


def _path(p, bad):
    t = load_table("kujawski2014_table3")
    t = t[t.path == p].reset_index(drop=True)
    return [
        pytest.param(r, marks=pytest.mark.xfail(strict=True, reason=bad[i])) if i in bad else r
        for i, r in enumerate(t.itertuples())
    ]


@pytest.mark.parametrize(
    "row", _path("A", {9: "printed 0.58; tau gamma/sqrt3 = 0.61 (row inconsistent)"})
)
def test_table3_torsion_uses_gamma_over_sqrt3(row):
    g = row.gamma_a_pct / 100
    v = swtd_eq25(_tens(0, row.tau_a), _tens(0, -row.tau_a), _strain(0, g))
    assert v == pytest.approx(row.tau_a * g / 2, rel=1e-12)
    tol = 0.005 / row.gamma_a_pct + 0.005 / row.swtd
    assert v * 2 / np.sqrt(3) == pytest.approx(row.swtd, rel=tol)


def test_shared_frame_not_sorted_pairing():
    """Compressive uniaxial minimum: the transverse deviatoric stress -s_min/3 pairs with the
    transverse strain (1+nu) e/3, not with the axial (2/3)(1+nu) e (sorted pairing doubles it)."""
    e, nu, smin = 0.004, 0.3, -600.0
    v = swtd_eq25(_tens(10.0), _tens(smin), _strain(e, nu=nu))
    assert v == pytest.approx(-smin / 3 * (1 + nu) * e / 3, rel=1e-12)


@pytest.mark.parametrize("seed", range(5))
def test_rotation_invariance(seed):
    rng = np.random.default_rng(seed)
    Q, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    S0, S1 = _tens(300.0, 120.0), _tens(-100.0, -120.0)
    Ea = _strain(0.002, 0.003)
    rot = lambda A: Q @ A @ Q.T  # noqa: E731
    assert swtd_eq25(rot(S0), rot(S1), rot(Ea)) == pytest.approx(swtd_eq25(S0, S1, Ea), rel=1e-10)


def test_in_phase_harmonics_equal_two_step():
    S0, S1, E0, E1 = (
        _tens(400.0, 150.0),
        _tens(-200.0, -150.0),
        _strain(0.003, 0.002),
        _strain(-0.001, -0.002),
    )
    z = np.zeros((3, 3))
    h = dict(S_mean=(S0 + S1) / 2, S_sin=(S0 - S1) / 2, S_cos=z, E_mean=(E0 + E1) / 2)
    h.update(E_sin=(E0 - E1) / 2, E_cos=z)
    two_step = SWTD().evaluate_case(S0=S0, E0=E0, S1=S1, E1=E1, params={}).values[""]
    assert SWTD().evaluate_case(S0=S0, E0=E0, S1=S1, E1=E1, params={}, harmonics=h).values[
        ""
    ] == pytest.approx(two_step, rel=1e-12)
    assert swtd_single_harmonic(h) >= two_step * (1 - 1e-12)


def test_out_of_phase_phase_origin_invariance():
    """Shifting the time origin of a 90-degree history must not change the chord maximum."""
    z = np.zeros((3, 3))
    A_s, A_c, B_s, B_c = _tens(300.0), _tens(0, 180.0), _strain(0.002), _strain(0, 0.004)
    base = swtd_single_harmonic(
        dict(S_mean=z, S_sin=A_s, S_cos=A_c, E_mean=z, E_sin=B_s, E_cos=B_c)
    )
    phi = 0.37
    c, s = np.cos(phi), np.sin(phi)
    shifted = dict(
        S_mean=z, S_sin=A_s * c - A_c * s, S_cos=A_s * s + A_c * c, E_mean=z,
        E_sin=B_s * c - B_c * s, E_cos=B_s * s + B_c * c,
    )  # fmt: skip
    assert swtd_single_harmonic(shifted) == pytest.approx(base, rel=2e-4)
