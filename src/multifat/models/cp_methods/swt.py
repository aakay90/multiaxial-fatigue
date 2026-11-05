"""Smith, Watson & Topper (1970), J. Mater. 5:767-778: SWT parameter, critical-plane extension.

p. 769: the damage function is sigma_max eps_a, used as sqrt(sigma_max eps_a E)::

    sigma_max eps_a = constant at a given life        sigma_max > 0

On each candidate plane DP = sigma_max d_eps / 2 (MPa), with sigma_max the largest normal stress
over the cycle and d_eps the normal strain range; the selection metric is d_eps (plane of maximum
normal strain range) and SWT_ext takes the largest DP over the planes.

Repository choices:
  - the product sigma_max eps_a, not its square root (monotone: fitted lives are unchanged);
  - sigma_max is clipped at zero, so a fully compressive cycle gives DP = 0;
  - the critical-plane extension is not in the 1970 paper; strains are linear-elastic; life from
    the shared master curve DP = A N^b.

User guide: docs/method-guides/SWT.md.
"""

from __future__ import annotations
from typing import Mapping
import numpy as np
from multifat.models.utils.tensors import as33 as _as33
from multifat.models.utils.batch import check_planes
from ..base import CPPlaneResult


class SWT:
    name = "SWT"

    def required_params(self) -> set[str]:
        return set()

    def evaluate_on_plane(
        self,
        *,
        S0r,
        E0r,
        S1r,
        E1r,
        params: Mapping[str, float],
    ) -> CPPlaneResult:
        """Smith-Watson-Topper DP for one candidate plane.

        Plane normal is local z; normal stress uses Szz (clipped at 0) with
        sigma_max = max(Szz at step 0, Szz at step 1); the normal strain range is
        |Ezz(step 0) - Ezz(step 1)|.

        Returns DP and the plane-selection metric (d_eps).
        """
        S0r = _as33("S0r", S0r)
        E0r = _as33("E0r", E0r)
        S1r = _as33("S1r", S1r)
        E1r = _as33("E1r", E1r)

        # sigma_nn = Szz (clipped at 0)
        sigma_z0 = max(float(S0r[2, 2]), 0.0)
        sigma_z1 = max(float(S1r[2, 2]), 0.0)
        sigma_max = max(sigma_z0, sigma_z1)

        # eps_nn = Ezz
        d_eps = abs(float(E0r[2, 2] - E1r[2, 2]))

        DP = float(d_eps * sigma_max / 2.0)
        metric = float(d_eps)
        return CPPlaneResult(damage=float(DP), metric=float(metric))

    def evaluate_on_planes(
        self, *, S0r, E0r, S1r, E1r, params: Mapping[str, float], tau_max=None, strain_ranges=None
    ):
        """All planes at once; bit-identical to ``evaluate_on_plane`` per plane."""
        check_planes(S0r, E0r, S1r, E1r)
        sigma_max = np.maximum(np.maximum(S0r[:, 2, 2], 0.0), np.maximum(S1r[:, 2, 2], 0.0))
        d_eps = np.abs(E0r[:, 2, 2] - E1r[:, 2, 2])
        return d_eps * sigma_max / 2.0, d_eps
