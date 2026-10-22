"""G26 Banvillet, Palin-Luc & Lasserre (2003), doi:10.1016/S0142-1123(03)00048-3 (Zotero Z2S5IDBQ),
triaxiality and combined tension-torsion (Eqs. 13-28; pages 761-762, Table 1 p. 766, text p. 765,
Fig. 6 p. 762):

- Eq. (15) with Table 1 (s_RotBen,-1, t_-1, nu) gives the printed beta = 0.96 (30NiCrMo16), -1.45 (C20,
  minus sign lost in the print), 3.09 (EN-GJS800-2), and Eq. (8) the printed sigma* = 441, 230, 204 MPa.
- Fig. 6 (EN-GJS800-2): the torsion intercepts at mean shear 50, 100, 150 MPa read about 0.97, 0.90,
  0.73 t_-1 (digitised).
- Eqs. (25)-(28) are checked against the volume average of Eq. (21) over V* (Eq. 19) by quadrature.
"""

import numpy as np
import pytest

from multifat.models.energy_based_methods.banvillet import (
    beta_from_limits,
    tension_torsion_index,
    triaxiality_function,
)

# Table 1: E (MPa), nu, t_-1, s_Ten,-1, s_RotBen,-1; printed beta and sigma* (p. 765)
TABLE1 = {
    "30NiCrMo16": (200000.0, 0.29, 428.0, 560.0, 658.0, 0.96, 441.0),
    "C20": (210000.0, 0.30, 186.0, 273.0, 310.0, -1.45, 230.0),
    "EN-GJS800-2": (165000.0, 0.275, 220.0, 245.0, 280.0, 3.09, 204.0),
}


@pytest.mark.parametrize("material", TABLE1)
def test_eq15_beta_and_eq8_sigma_star(material):
    E, nu, t, s_ten, s_rb, beta_printed, sigma_star = TABLE1[material]
    assert beta_from_limits(s_rb, t, nu) == pytest.approx(beta_printed, abs=0.01)
    assert np.sqrt(2.0 * s_ten**2 - s_rb**2) == pytest.approx(sigma_star, abs=0.5)


def test_eq14_limits():
    assert triaxiality_function(0.0, 3.09) == pytest.approx(1.0)
    assert triaxiality_function(0.2, 1e-9) == pytest.approx(1.0, abs=1e-8)  # beta -> 0: F = 1


@pytest.mark.parametrize("material", TABLE1)
def test_reversed_tension_and_torsion_limits(material):
    """Eq. (28) returns s_Ten in tension; Eq. (27) returns t_-1 in torsion through Eq. (15)."""
    E, nu, t, s_ten, s_rb, _, _ = TABLE1[material]
    beta = beta_from_limits(s_rb, t, nu)
    assert tension_torsion_index(0.0, s_ten, 0.0, 0.0, s_ten, s_rb, beta, nu) == pytest.approx(1.0)
    assert tension_torsion_index(0.0, 0.0, 0.0, t, s_ten, s_rb, beta, nu) == pytest.approx(1.0)


@pytest.mark.parametrize("tau_m,read", [(50.0, 0.97), (100.0, 0.90), (150.0, 0.73)])
def test_fig6_torsion_intercepts(tau_m, read):
    E, nu, t, s_ten, s_rb, _, _ = TABLE1["EN-GJS800-2"]
    beta = beta_from_limits(s_rb, t, nu)
    index = tension_torsion_index(0.0, 0.0, tau_m, t, s_ten, s_rb, beta, nu)
    lo, hi = tau_m, t
    for _ in range(100):  # the index is not homogeneous in tau_a at fixed mean
        mid = 0.5 * (lo + hi)
        if tension_torsion_index(0.0, 0.0, tau_m, mid, s_ten, s_rb, beta, nu) > 1.0:
            hi = mid
        else:
            lo = mid
    assert index > 1.0
    assert lo / t == pytest.approx(read, abs=0.015)


@pytest.mark.parametrize("ratio", [0.3, 0.8, 1.5])
def test_eqs_25_28_against_volume_average(ratio):
    """At the limit load of Eqs. (27)/(28), the mean of W_g - W* over V* (Eqs. 19, 21) equals g^D."""
    E, nu, t_m1, s_ten, s_rb, _, _ = TABLE1["30NiCrMo16"]
    beta = beta_from_limits(s_rb, t_m1, nu)
    sigma_a, tau_a = 100.0, 100.0 * ratio
    scale = 1.0 / tension_torsion_index(0.0, sigma_a, 0.0, tau_a, s_ten, s_rb, beta, nu)
    sigma_a, tau_a = scale * sigma_a, scale * tau_a
    s, t = sigma_a**2, 2.0 * (1.0 + nu) * tau_a**2
    d_uni = (1.0 - 2.0 * nu) / 3.0
    f_ratio = triaxiality_function(d_uni * s / (s + t), beta) / triaxiality_function(d_uni, beta)
    w_star = f_ratio * (2.0 * s_ten**2 - s_rb**2) / E  # Eq. (24)
    g_d = f_ratio * (s_rb**2 - s_ten**2) / E  # Eqs. (9), (18)
    r = np.linspace(0.0, 1.0, 400001)
    w = (s + t * r**2) / E  # Eq. (21), R = 1
    weight = np.where(w >= w_star, r, 0.0)  # annulus V*, area element r dr
    g = np.sum((w - w_star) * weight) / np.sum(weight)
    assert g == pytest.approx(g_d, rel=1e-4)


def test_index_homogeneous_and_continuous():
    E, nu, t_m1, s_ten, s_rb, _, _ = TABLE1["30NiCrMo16"]
    beta = beta_from_limits(s_rb, t_m1, nu)
    base = tension_torsion_index(0.0, 300.0, 0.0, 90.0, s_ten, s_rb, beta, nu)
    for k in (0.3, 1.0, 2.5):
        scaled = tension_torsion_index(0.0, 300.0 * k, 0.0, 90.0 * k, s_ten, s_rb, beta, nu)
        assert scaled == pytest.approx(k * base, rel=1e-12)
    ratios = np.linspace(0.0, 3.0, 3001)
    values = [
        tension_torsion_index(0.0, 100.0, 0.0, 100.0 * q, s_ten, s_rb, beta, nu) for q in ratios
    ]
    assert np.max(np.abs(np.diff(values))) < 1e-3


def test_domain():
    with pytest.raises(ValueError):
        tension_torsion_index(300.0, 200.0, 0.0, 0.0, 560.0, 658.0, 0.96, 0.29)
    with pytest.raises(ValueError):
        beta_from_limits(400.0, 200.0, 0.3)
