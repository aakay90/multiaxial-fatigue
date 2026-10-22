"""Matake (1977), doi:10.1299/jsme1958.20.257, checked against the PDF (Zotero E6ADU97M).

Eq. (1), p.5: tau_max = tau_0 - alpha sigma_n on the maximum-shear plane. Appendix, p.7: the line
through (0, tau_0) and (sigma_0/2, sigma_0/2) gives alpha = 2 tau_0/sigma_0 - 1. The appendix
prints alpha = (tau_0 - sigma_0)/(sigma_0/2) and then {tau_0/sigma_0 - 1}; both are misprints, as
the stated points and the right-column derivation of Gough's Eq. (2) use 2 tau_0/sigma_0 - 1.
"""

import numpy as np
import pytest
from _paper import bending_torsion, frame_with_normal, load_table, max_shear_normals, rotate

from multifat.eval.evaluator import best_cp_for_case
from multifat.models.cp_methods.matake import Matake
from multifat.planes.sampling import build_R_list

TABLE3 = load_table("matake1977_table3")
LIMITS = {
    m: dict(
        Taum1=g.loc[g.theta_deg == 0, "tau"].item(), Sigm1=g.loc[g.theta_deg == 90, "sigma"].item()
    )
    for m, g in TABLE3.groupby("material")
}
ROWS = [r for r in TABLE3.itertuples()]


def _on_max_shear_plane(row):
    S = bending_torsion(row.sigma, row.tau)
    R = frame_with_normal(max_shear_normals(S)[0])
    Sr = rotate(S, R)
    return Sr, Matake().evaluate_on_plane(
        S0r=Sr, S1r=-Sr, E0r=np.zeros((3, 3)), E1r=np.zeros((3, 3)), params=LIMITS[row.material]
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: f"{r.material}-{r.theta_deg}")
def test_table3_max_shear_plane_quantities(row):
    """Shear amplitude and normal stress on the maximum-shear plane reproduce Table 3."""
    Sr, result = _on_max_shear_plane(row)
    tau_a = np.hypot(Sr[0, 2], Sr[1, 2])
    assert tau_a == pytest.approx(row.tau_max, abs=0.05)
    assert abs(Sr[2, 2]) == pytest.approx(row.sigma_n, abs=0.05)
    assert result.metric == pytest.approx(2 * tau_a, rel=1e-12)


def test_table3_loading_ratio_exposes_steel_misprint():
    """tau/sigma = cos(theta)/(2 sin(theta)) for the grip; only the printed steel row fails."""
    combined = TABLE3[(TABLE3.theta_deg > 0) & (TABLE3.theta_deg < 90)]
    t = np.radians(combined.theta_deg)
    expected = np.cos(t) / (2 * np.sin(t))
    assert np.allclose(combined.tau / combined.sigma, expected, rtol=0.02)
    printed = combined.tau / combined.sigma_printed
    assert list(~np.isclose(printed, expected, rtol=0.02)) == [
        r.material == "high_strength_steel" and r.theta_deg == 22.5 for r in combined.itertuples()
    ]


@pytest.mark.parametrize("material", sorted(LIMITS))
def test_damage_equals_torsion_limit_at_both_limits(material):
    """Eq. (1) with alpha = 2 tau_0/sigma_0 - 1 passes through both calibration points."""
    for theta in (0, 90):
        row = TABLE3[(TABLE3.material == material) & (TABLE3.theta_deg == theta)].iloc[0]
        _, result = _on_max_shear_plane(row)
        assert result.damage == pytest.approx(LIMITS[material]["Taum1"], rel=1e-12)


@pytest.mark.parametrize("material", sorted(LIMITS))
def test_plane_search_finds_the_limits(material):
    """The 522-plane grid reaches the exact maximum-shear plane in torsion and bending."""
    R_list = build_R_list()
    for theta in (0, 90):
        row = TABLE3[(TABLE3.material == material) & (TABLE3.theta_deg == theta)].iloc[0]
        S = bending_torsion(row.sigma, row.tau)
        best = best_cp_for_case(
            S0=S,
            S1=-S,
            E0=np.zeros((3, 3)),
            E1=np.zeros((3, 3)),
            R_list=R_list,
            method=Matake(),
            params=LIMITS[material],
        )
        assert best.by_metric == pytest.approx(LIMITS[material]["Taum1"], rel=1e-8)


def test_combined_limits_within_first_approximation():
    """Validation, not verification: combined-stress limits lie within +-10% of Eq. (1)."""
    combined = [r for r in ROWS if 0 < r.theta_deg < 90]
    ratios = [_on_max_shear_plane(r)[1].damage / LIMITS[r.material]["Taum1"] for r in combined]
    assert min(ratios) > 0.90 and max(ratios) < 1.10
