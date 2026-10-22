"""Probabilistic volume model proposed by Flacelière and Morel (2004), Fatigue Fract Engng Mater
Struct 27:1123-1135, doi:10.1111/j.1460-2695.2004.00823.x (roadmap item G24), supplied here as
point kernels rather than a registered model: it requires the stressed volume V and the scale
parameter V0 sigma_u^m, and the paper does not give these for its test geometries.

Equation (13): P_F = 1 - exp(-(V / (V0 sigma_u^m)) sigma_eq,max^m H_m),
Equation (12): H_m = (1 / (V sigma_eq,max^m)) int_V sigma_eq^m dV, whose closed forms (Eq. 14)
are 1 for tension, 1/(m+1) for four-point plane bending of a square section, 2/(m+2) for
four-point rotating bending of a round section, 1/(m+1)^2 for three-point plane bending and
2/((m+1)(m+2)) for three-point rotating bending. Under rotating bending every point experiences
the cycle maximum sigma r/R, which is where the round-section factors originate.
sigma_eq = M_sigma + p H_max (Eq. 3), with M_sigma the quadratic mean of the resolved shear
amplitude (t_-1 under torsion, s_-1/sqrt(3) under tension).
"""

from __future__ import annotations

import numpy as np

_H_FACTORS = {
    "tension": lambda m: 1.0,
    "four_point_plane": lambda m: 1.0 / (m + 1.0),
    "four_point_rotating": lambda m: 2.0 / (m + 2.0),
    "three_point_plane": lambda m: 1.0 / (m + 1.0) ** 2,
    "three_point_rotating": lambda m: 2.0 / ((m + 1.0) * (m + 2.0)),
}


def heterogeneity_factor(case: str, m: float) -> float:
    """H_m of Eq. (14)."""
    return float(_H_FACTORS[case](m))


def failure_probability(sigma_eq_max: float, m: float, volume: float, v0_su_m: float, h_m: float):
    """P_F of Eq. (13)."""
    return float(1.0 - np.exp(-(volume / v0_su_m) * sigma_eq_max**m * h_m))


def median_strength(m: float, volume: float, v0_su_m: float, h_m: float) -> float:
    """sigma_eq,max evaluated at P_F = 50 %."""
    return float((np.log(2.0) * v0_su_m / (volume * h_m)) ** (1.0 / m))
