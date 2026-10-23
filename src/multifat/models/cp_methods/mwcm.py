# multifat/models/cp_methods/mwcm.py
"""Modified Wöhler Curve Method, Susmel & Lazzarin (2002), Fatigue Fract Engng Mater Struct
25:63-78, doi:10.1046/j.1460-2695.2002.00462.x (roadmap N04), high-cycle formulation, Eqs. (5)-(13):

    rho = sigma_n,max / tau_a                         evaluated on the plane where tau_a is largest (Eq. 5)
    tau_A,Ref(rho) = tau_A + rho (sigma_A/2 - tau_A)  (Eq. 8, using fatigue limits as reference values)
    tau_a <= tau_A,Ref(rho)                           (Eqs. 9-11)

Here tau_a denotes the radius of the smallest circle enclosing the shear path (p.66), which yields the
longest-chord shear rule; sigma_n,max is the mean plus amplitude of the normal stress acting on that
plane (without clipping: a compressive mean makes rho < 0). The damage measure is
tau_a / tau_A,Ref(rho) = E + 1 from the error index of Eq. (13); it becomes infinite as soon as
tau_A,Ref(rho) <= 0, i.e. for rho >= tau_A/(tau_A - sigma_A/2) (the paper applies Eq. 11 for rho > 1
without imposing a cut-off). The finite-life branch of Eq. (7) would require k_tau(rho) derived from
the two Wöhler slopes and is not implemented. Whenever the plane metric ties, the larger damage is
selected (the paper does not specify a rule).
"""

from __future__ import annotations

from typing import Mapping

import numpy as np
from multifat.models.utils.batch import check_planes, pypow2

from ..base import CPPlaneResult


def mwcm_reference_shear(rho, sigma_A: float, tau_A: float):
    """Reference shear amplitude tau_A,Ref(rho) from Eq. (8)."""
    return tau_A + np.asarray(rho, dtype=float) * (0.5 * sigma_A - tau_A)


def mwcm_damage(tau_a, sigma_n_max, sigma_A: float, tau_A: float):
    """Ratio tau_a / tau_A,Ref(rho); equals 0 when tau_a = 0 with no tension, inf beyond the cut-off."""
    tau_a = np.asarray(tau_a, dtype=float)
    sigma_n_max = np.asarray(sigma_n_max, dtype=float)
    slope_term = tau_A - 0.5 * sigma_A
    # tau_a / (tau_A - alpha sigma/tau_a) = tau_a^2 / (tau_A tau_a - alpha sigma)
    divisor = tau_A * tau_a - slope_term * sigma_n_max
    with np.errstate(divide="ignore", invalid="ignore"):
        damage = np.where(
            divisor > 0.0,
            tau_a**2 / np.where(divisor > 0.0, divisor, 1.0),
            np.inf,
        )
    return np.where((tau_a == 0.0) & (sigma_n_max <= 0.0), 0.0, damage)


class MWCM:
    """Susmel-Lazzarin MWCM, Eq. (11), expressed as the ratio tau_a / tau_A,Ref(rho)."""

    name = "MWCM"
    np_shear_rule = "longest_chord"
    ext_variant = False  # rho = sigma_n,max/tau_a blows up as tau_a -> 0 (hence no _ext)

    def required_params(self) -> set[str]:
        return {"Sigm1", "Taum1"}

    def evaluate_on_plane(self, *, S0r, E0r, S1r, E1r, params: Mapping[str, float]):
        damage, metric = self.evaluate_on_planes(
            S0r=np.asarray(S0r, float)[None],
            E0r=np.asarray(E0r, float)[None],
            S1r=np.asarray(S1r, float)[None],
            E1r=np.asarray(E1r, float)[None],
            params=params,
        )
        return CPPlaneResult(damage=float(damage[0]), metric=float(metric[0]))

    def evaluate_on_planes(
        self,
        *,
        S0r,
        E0r,
        S1r,
        E1r,
        params: Mapping[str, float],
        tau_max=None,
        strain_ranges=None,
    ):
        check_planes(S0r, E0r, S1r, E1r)
        for key in ("Sigm1", "Taum1"):
            if params.get(key, None) is None:
                raise KeyError(f"MWCM needs the parameter params['{key}']")
        sigma_A, tau_A = float(params["Sigm1"]), float(params["Taum1"])
        if sigma_A <= 0.0 or tau_A <= 0.0:
            raise ValueError("MWCM needs Sigm1 and Taum1 to be strictly positive")
        d_tau_xz = S0r[:, 0, 2] - S1r[:, 0, 2]
        d_tau_yz = S0r[:, 1, 2] - S1r[:, 1, 2]
        d_tau = np.sqrt(pypow2(d_tau_xz) + pypow2(d_tau_yz))
        sigma_n_max = np.maximum(S0r[:, 2, 2], S1r[:, 2, 2])
        return (
            mwcm_damage(0.5 * d_tau, sigma_n_max, sigma_A, tau_A),
            d_tau,
        )
