"""Liu et al. (2021) critical-plane model (TNP family) – damage parameter.

From Liu et al. (Int. J. Pressure Vessels and Piping 194 (2021) 104532),
Eq. (27) defines a modified shear strain amplitude on the critical plane:

    γ*_max / 2 = (Δγ_max / 2) * ( 1 + σ_{n,max} * sqrt(σ_{n,max} E Δε)
                                      / (2 G Δγ_max τ'_f) )

γ*_max/2 is returned as the damage parameter.

Repository choices:
  - Δγ_max is the shear strain range on the candidate plane.
  - Δε is taken here as the normal strain range on the same plane.
  - τ'_f is the shear fatigue strength coefficient. If not provided, it is
    derived from axial fatigue properties using von Mises relations.
  - Plane selection follows the paper's definition: maximum shear strain plane.
"""

from __future__ import annotations

from typing import Mapping
import math
import numpy as np
from multifat.models.utils.tensors import as33 as _as33
from multifat.models.utils.batch import check_planes

from ..base import CPPlaneResult
from ..utils.fatigue_estimation import ensure_shear_fatigue_props


class Liu2021:
    name = "LIU2021"
    optional_params = {"tau_f": "uniform material law from Su and E"}
    # Source defines the plane shear range over the cycle (longest chord), see SHEAR_RULES.
    np_shear_rule = "longest_chord"

    def required_params(self) -> set[str]:
        # Need E and nu to compute G; Su is used for estimating fatigue props if needed.
        return {"E", "nu", "Su"}

    def evaluate_on_plane(
        self, *, S0r, E0r, S1r, E1r, params: Mapping[str, float]
    ) -> CPPlaneResult:
        S0r = _as33("S0r", S0r)
        S1r = _as33("S1r", S1r)
        E0r = _as33("E0r", E0r)
        E1r = _as33("E1r", E1r)

        E = float(params["E"])  # MPa
        nu = float(params["nu"])
        if E <= 0:
            raise ValueError(f"E must be > 0. Got E={E}")
        if not (-1.0 < nu < 0.5):
            raise ValueError(f"nu not plausible. Got nu={nu}")
        G = E / (2.0 * (1.0 + nu))

        tau_f = params.get("tau_f")
        if tau_f is None:
            tau_f = ensure_shear_fatigue_props(params).tau_f
        tau_f = float(tau_f)
        if tau_f <= 0:
            raise ValueError(f"tau_f must be > 0. Got tau_f={tau_f}")

        # Normal stress max (tensile only)
        sigma_z0 = max(float(S0r[2, 2]), 0.0)
        sigma_z1 = max(float(S1r[2, 2]), 0.0)
        sigma_n_max = max(sigma_z0, sigma_z1)

        # Normal strain range (used as Δε)
        d_eps = abs(float(E0r[2, 2] - E1r[2, 2]))

        # Shear strain range Δγ
        d_gam_xz = float(E0r[0, 2] - E1r[0, 2])
        d_gam_yz = float(E0r[1, 2] - E1r[1, 2])
        d_gam = 2.0 * float(np.hypot(d_gam_xz, d_gam_yz))

        # Algebraically expanded Eq. (27), including its zero-shear limit.
        radicand = max(sigma_n_max * E * d_eps, 0.0)
        gamma_star_half = 0.5 * d_gam + sigma_n_max * math.sqrt(radicand) / (4.0 * G * tau_f)

        return CPPlaneResult(damage=float(gamma_star_half), metric=float(d_gam))

    def evaluate_on_planes(
        self, *, S0r, E0r, S1r, E1r, params: Mapping[str, float], tau_max=None, strain_ranges=None
    ):
        """All planes at once; bit-identical to ``evaluate_on_plane`` per plane."""
        check_planes(S0r, E0r, S1r, E1r)
        E, nu = float(params["E"]), float(params["nu"])
        if E <= 0:
            raise ValueError(f"E must be > 0. Got E={E}")
        if not (-1.0 < nu < 0.5):
            raise ValueError(f"nu not plausible. Got nu={nu}")
        G = E / (2.0 * (1.0 + nu))
        tau_f = params.get("tau_f")
        if tau_f is None:
            tau_f = ensure_shear_fatigue_props(params).tau_f
        tau_f = float(tau_f)
        if tau_f <= 0:
            raise ValueError(f"tau_f must be > 0. Got tau_f={tau_f}")
        sigma_n_max = np.maximum(np.maximum(S0r[:, 2, 2], 0.0), np.maximum(S1r[:, 2, 2], 0.0))
        d_eps = np.abs(E0r[:, 2, 2] - E1r[:, 2, 2])
        d_gam = 2.0 * np.hypot(E0r[:, 0, 2] - E1r[:, 0, 2], E0r[:, 1, 2] - E1r[:, 1, 2])
        radicand = np.maximum(sigma_n_max * E * d_eps, 0.0)
        return 0.5 * d_gam + sigma_n_max * np.sqrt(radicand) / (4.0 * G * tau_f), d_gam
