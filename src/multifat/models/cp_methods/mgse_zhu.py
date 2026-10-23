"""MGSE (Zhu et al.) critical-plane damage parameter with material constant.

Zhu et al. (Int. J. Fatigue 2018) propose a modified generalized strain
energy (MGSE) criterion with an additional material constant k_MGSE:

    MGSE = τ_max * (Δγ/2) + k_MGSE * σ_{n,max} * (Δε_n/2)

The left-hand damage parameter is returned for calibration and assessment.

Without k_MGSE in the workbook, the paper's practical recommendation applies:
k_MGSE = 1, with a warning.
"""

from __future__ import annotations

from typing import Mapping
import numpy as np
from multifat.models.utils.tensors import as33 as _as33
from multifat.models.utils.batch import check_planes, tau_max_planes as _tau_max_planes

from ..base import CPPlaneResult
from ..utils.param_utils import get_param


class MGSE_Zhu:
    name = "MGSE_ZHU"
    optional_params = {"k_MGSE": "1.0"}

    def required_params(self) -> set[str]:
        # k_MGSE is optional (default 1.0)
        return set()

    def evaluate_on_plane(
        self, *, S0r, E0r, S1r, E1r, params: Mapping[str, float]
    ) -> CPPlaneResult:
        S0r = _as33("S0r", S0r)
        S1r = _as33("S1r", S1r)
        E0r = _as33("E0r", E0r)
        E1r = _as33("E1r", E1r)

        k_mgse = get_param(params, "k_MGSE", default=1.0, context=self.name)

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

        damage = float(tau_max * (0.5 * d_gam) + float(k_mgse) * sigma_n_max * (0.5 * d_eps))
        metric = damage
        return CPPlaneResult(damage=damage, metric=metric)

    def evaluate_on_planes(
        self, *, S0r, E0r, S1r, E1r, params: Mapping[str, float], tau_max=None, strain_ranges=None
    ):
        """All planes at once; bit-identical to ``evaluate_on_plane`` per plane."""
        check_planes(S0r, E0r, S1r, E1r)
        k_mgse = get_param(params, "k_MGSE", default=1.0, context=self.name)
        sigma_n_max = np.maximum(np.maximum(S0r[:, 2, 2], 0.0), np.maximum(S1r[:, 2, 2], 0.0))
        tau_max_plane = _tau_max_planes(S0r, S1r, params, tau_max)
        d_eps = np.abs(E0r[:, 2, 2] - E1r[:, 2, 2])
        d_gam = 2.0 * np.hypot(E0r[:, 0, 2] - E1r[:, 0, 2], E0r[:, 1, 2] - E1r[:, 1, 2])
        damage = tau_max_plane * (0.5 * d_gam) + float(k_mgse) * sigma_n_max * (0.5 * d_eps)
        return damage, damage
