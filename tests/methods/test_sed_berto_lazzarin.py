"""Berto & Lazzarin (2011) SED kernel (roadmap G30): Int J Fatigue 33:1055-1065,
doi:10.1016/j.ijfatigue.2010.11.019 (Zotero IH7K7INH); Eqs. (7), (8a), (8b) and the AISI 416 values
on p.1063 (crop _audit-trail/phase2/crops/IH7K7INH/p9_*.png).

Printed: R1 = 0.13 mm, R3 = 0.78 mm from Delta K1A = 512 MPa mm^0.455, Delta sigma1A = 697 MPa,
Delta K3A = 891 MPa mm^0.333, Delta tau3A = 474 MPa (2 alpha = 90 deg, nu = 0.3). Recomputed 0.132 and
0.774 mm. Delta K1A = 512 is 0.5 % below 2.223 x 2 x 115.7 from Eq. (6a) and Table 1 (unresolved).
"""

import pytest

from multifat.models.energy_based_methods.sed_berto_lazzarin import averaged_sed, control_radii

L1, L3, E1, E3, NU = 0.5445, 0.6667, 0.1462, 0.3103, 0.3
INPUTS = dict(dK1A=512.0, dsigma1A=697.0, dK3A=891.0, dtau3A=474.0)


def test_eq8_printed_control_radii():
    r1, r3 = control_radii(**INPUTS, e1=E1, e3=E3, lambda1=L1, lambda3=L3, nu=NU)
    assert r1 == pytest.approx(0.13, abs=0.005)
    assert r3 == pytest.approx(0.78, abs=0.01)


def test_eq7_at_the_reference_level_recovers_the_plain_energies():
    E = 206000.0
    r1, r3 = control_radii(**INPUTS, e1=E1, e3=E3, lambda1=L1, lambda3=L3, nu=NU)
    w1 = averaged_sed(INPUTS["dK1A"], 0.0, r1, r3, E1, E3, L1, L3, E)
    w3 = averaged_sed(0.0, INPUTS["dK3A"], r1, r3, E1, E3, L1, L3, E)
    assert w1 == pytest.approx(INPUTS["dsigma1A"] ** 2 / (2 * E), rel=1e-12)
    assert w3 == pytest.approx((1 + NU) * INPUTS["dtau3A"] ** 2 / E, rel=1e-12)
    assert averaged_sed(INPUTS["dK1A"], INPUTS["dK3A"], r1, r3, E1, E3, L1, L3, E) == pytest.approx(
        w1 + w3, rel=1e-12
    )
