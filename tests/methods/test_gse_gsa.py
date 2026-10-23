"""GSE / GSA, Ince & Glinka (2014), doi:10.1016/j.ijfatigue.2013.10.007, checked against PDF
(FBXV6CQX p.35): Eq. (1) W*_gen = (tau_max dg_e/2 + dtau/2 dg_p/2 + s_n,max de_e/2
+ ds_n/2 de_p/2)_max and Eq. (5) de*/2 = (tau_max/tau'_f dg_e/2 + dg_p/2 + s_n,max/s'_f de_e/2
+ de_p/2)_max, on the plane of maximum damage parameter. Repository adaptations: s_n,max clipped
at zero; tau'_f defaults to s'_f/sqrt(3) (the paper gives no value; Yu et al. 2017 Eq. 13).
"""

import numpy as np
import pytest

from multifat.models.cp_methods.gsa import GSA
from multifat.models.cp_methods.gse import GSE

E, NU, SF, TF = 200000.0, 0.3, 1100.0, 640.0
G = E / (2 * (1 + NU))


def _plane_state():
    """Fully reversed plane state with explicit elastic and plastic strain amplitudes."""
    tau_a, sig_a = 180.0, 120.0
    gp_a, ep_a = 4e-4, 1.5e-4  # engineering plastic shear and plastic normal amplitudes
    S = np.zeros((3, 3))
    S[0, 2] = S[2, 0] = tau_a
    S[2, 2] = sig_a
    Ee = ((1 + NU) * S - NU * np.trace(S) * np.eye(3)) / E
    Ep = np.zeros((3, 3))
    Ep[0, 2] = Ep[2, 0] = gp_a / 2
    Ep[2, 2] = ep_a
    terms = dict(
        tau=tau_a, sig=sig_a, ge=2 * Ee[0, 2], gp=gp_a, ee=Ee[2, 2], ep=ep_a
    )  # amplitudes; ranges are twice these
    return S, Ee + Ep, terms


def test_eq1_gse_terms():
    S, Etot, t = _plane_state()
    r = GSE().evaluate_on_plane(S0r=S, S1r=-S, E0r=Etot, E1r=-Etot, params=dict(E=E, nu=NU))
    expected = t["tau"] * t["ge"] + t["tau"] * t["gp"] + t["sig"] * t["ee"] + t["sig"] * t["ep"]
    assert r.damage == pytest.approx(expected, rel=1e-12)
    assert r.metric == r.damage


def test_eq5_gsa_terms():
    S, Etot, t = _plane_state()
    params = dict(E=E, nu=NU, sigma_f=SF, tau_f=TF)
    r = GSA().evaluate_on_plane(S0r=S, S1r=-S, E0r=Etot, E1r=-Etot, params=params)
    expected = t["tau"] / TF * t["ge"] + t["gp"] + t["sig"] / SF * t["ee"] + t["ep"]
    assert r.damage == pytest.approx(expected, rel=1e-12)


def test_gsa_tau_f_default():
    S, Etot, _ = _plane_state()
    a = GSA().evaluate_on_plane(
        S0r=S, S1r=-S, E0r=Etot, E1r=-Etot, params=dict(E=E, nu=NU, sigma_f=SF)
    )
    b = GSA().evaluate_on_plane(
        S0r=S, S1r=-S, E0r=Etot, E1r=-Etot, params=dict(E=E, nu=NU, sigma_f=SF, tau_f=SF / 3**0.5)
    )
    assert a.damage == b.damage
