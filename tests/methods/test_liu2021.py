"""LIU2021 (TNP), Liu et al. (2021), doi:10.1016/j.ijpvp.2021.104532, checked against PDF (6HHMUTFN).

Eq. (27), p.7: gamma*/2 = dgamma/2 (1 + sigma_n,max sqrt(sigma_n,max E de) / (2 G dgamma tau'_f)),
i.e. Eq. (19) with k' from Eq. (23), p.5. tau'_f = sigma'_f/sqrt(3), G = E/(2(1+nu)) (Eq. 18).
Unresolved: Eq. (23)/(27) print an unsubscripted d(epsilon); the repository uses the normal strain
range on the critical plane. Paper inconsistencies (not used by the code): Eq. (3) prints
tau_xy/2 sin 2theta (standard transform has tau_xy sin 2theta); Eq. (6) writes the range dgamma
with the loading amplitude eps_a in front, half of Li et al. (2011) Eq. (15).
"""

import math

import numpy as np
import pytest

from multifat.models.cp_methods.liu2021 import Liu2021

GH4169 = dict(E=182000.0, nu=0.325, Su=1400.0, tau_f=1565.2 / math.sqrt(3))  # Table 2, p.7


def _plane(sig_n, d_eps_n, d_gam_eng):
    """Fully reversed plane state: normal stress amplitude, normal and engineering shear ranges."""
    s0 = np.diag([0.0, 0.0, sig_n])
    e0 = np.zeros((3, 3))
    e0[2, 2] = d_eps_n / 2
    e0[0, 2] = e0[2, 0] = d_gam_eng / 4  # tensor amplitude = engineering range / 4
    return s0, e0


@pytest.mark.parametrize("sig_n,d_eps_n,d_gam", [(200.0, 0.004, 0.012), (650.0, 0.008, 0.005)])
def test_eq27_equals_eq19_with_eq23(sig_n, d_eps_n, d_gam):
    s0, e0 = _plane(sig_n, d_eps_n, d_gam)
    r = Liu2021().evaluate_on_plane(S0r=s0, S1r=-s0, E0r=e0, E1r=-e0, params=GH4169)
    G = GH4169["E"] / (2 * (1 + GH4169["nu"]))
    k_prime = math.sqrt(sig_n * GH4169["E"] * d_eps_n) / (2 * G * d_gam)  # Eq. (23)
    eq19 = d_gam / 2 * (1 + k_prime * sig_n / GH4169["tau_f"])
    assert r.damage == pytest.approx(eq19, rel=1e-13)
    assert r.metric == pytest.approx(d_gam, rel=1e-13)


def test_zero_normal_stress_and_zero_shear_limits():
    s0, e0 = _plane(0.0, 0.004, 0.01)
    r = Liu2021().evaluate_on_plane(S0r=s0, S1r=-s0, E0r=e0, E1r=-e0, params=GH4169)
    assert r.damage == pytest.approx(0.005, rel=1e-13)  # gamma*/2 = dgamma/2
    s0, e0 = _plane(300.0, 0.004, 0.0)  # removable 1/dgamma in Eq. (27): finite limit
    r = Liu2021().evaluate_on_plane(S0r=s0, S1r=-s0, E0r=e0, E1r=-e0, params=GH4169)
    G = GH4169["E"] / (2 * (1 + GH4169["nu"]))
    expected = 300.0 * math.sqrt(300.0 * GH4169["E"] * 0.004) / (4 * G * GH4169["tau_f"])
    assert r.damage == pytest.approx(expected, rel=1e-13)


def test_tau_f_default_is_eq18():
    params = {k: v for k, v in GH4169.items() if k != "tau_f"}
    params.update(sigma_f=1565.2, epsilon_f=0.162, b_fat=-0.086, c_fat=-0.580)
    s0, e0 = _plane(200.0, 0.004, 0.012)
    with pytest.warns(RuntimeWarning):
        r = Liu2021().evaluate_on_plane(S0r=s0, S1r=-s0, E0r=e0, E1r=-e0, params=params)
    r_ref = Liu2021().evaluate_on_plane(S0r=s0, S1r=-s0, E0r=e0, E1r=-e0, params=GH4169)
    assert r.damage == pytest.approx(r_ref.damage, rel=1e-13)
