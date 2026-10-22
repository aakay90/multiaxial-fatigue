"""MGSE (Yu et al.) critical-plane damage parameter.

From Yu et al. (Materials 2017) a modified generalized strain energy (MGSE)
parameter on a plane close to the maximum shear strain plane:

    MGSE = τ_max * (Δγ/2) + σ_{n,max} * (Δε/2)

where Δγ is the shear strain range on the candidate plane, Δε is the normal
strain range on that plane, τ_max is the maximum shear stress magnitude on
that plane, and σ_{n,max} is the maximum normal stress on that plane.

Repository choices:
  - Candidate plane normal = local z
  - Normal stress/strain uses zz component
  - Shear components use (xz, yz)
"""

from __future__ import annotations

from typing import Mapping
import numpy as np
from multifat.models.utils.tensors import as33 as _as33
from multifat.models.utils.batch import check_planes, tau_max_planes as _tau_max_planes

from ..base import CPPlaneResult


class MGSE_Yu:
    name = "MGSE_YU"

    def required_params(self) -> set[str]:
        # No extra material constants required.
        return set()

    def evaluate_on_plane(
        self, *, S0r, E0r, S1r, E1r, params: Mapping[str, float]
    ) -> CPPlaneResult:
        S0r = _as33("S0r", S0r)
        S1r = _as33("S1r", S1r)
        E0r = _as33("E0r", E0r)
        E1r = _as33("E1r", E1r)

        # Normal stress max (tensile only)
        sigma_z0 = max(float(S0r[2, 2]), 0.0)
        sigma_z1 = max(float(S1r[2, 2]), 0.0)
        sigma_n_max = max(sigma_z0, sigma_z1)

        # Shear stress magnitude at max/min load step
        tau_0 = float(np.hypot(S0r[0, 2], S0r[1, 2]))
        tau_1 = float(np.hypot(S1r[0, 2], S1r[1, 2]))
        tau_max = float(params.get("_tau_max", max(tau_0, tau_1)))

        # Normal strain range on plane
        d_eps = abs(float(E0r[2, 2] - E1r[2, 2]))

        # Shear strain range on plane
        d_gam_xz = float(E0r[0, 2] - E1r[0, 2])
        d_gam_yz = float(E0r[1, 2] - E1r[1, 2])
        d_gam = 2.0 * float(np.hypot(d_gam_xz, d_gam_yz))

        damage = float(tau_max * (0.5 * d_gam) + sigma_n_max * (0.5 * d_eps))
        # In Yu's work the plane is chosen near maximum shear; in practice we
        # select the plane maximizing the MGSE value.
        metric = damage
        return CPPlaneResult(damage=damage, metric=metric)

    def evaluate_on_planes(
        self, *, S0r, E0r, S1r, E1r, params: Mapping[str, float], tau_max=None, strain_ranges=None
    ):
        """All planes at once; bit-identical to ``evaluate_on_plane`` per plane."""
        check_planes(S0r, E0r, S1r, E1r)
        sigma_n_max = np.maximum(np.maximum(S0r[:, 2, 2], 0.0), np.maximum(S1r[:, 2, 2], 0.0))
        tau_max_plane = _tau_max_planes(S0r, S1r, params, tau_max)
        d_eps = np.abs(E0r[:, 2, 2] - E1r[:, 2, 2])
        d_gam = 2.0 * np.hypot(E0r[:, 0, 2] - E1r[:, 0, 2], E0r[:, 1, 2] - E1r[:, 1, 2])
        damage = tau_max_plane * (0.5 * d_gam) + sigma_n_max * (0.5 * d_eps)
        return damage, damage
