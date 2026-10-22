"""Robert, Fogue and Bahuaud (1994), ASTM STP 1231:369-387, doi:10.1520/STP13959S (roadmap G41).

Damage measure on the plane whose normal is h, Eq. (15) with c = 0 (Eq. 25):

    E_h = a max_psi tau_h psi,a + b sigma_hh,a + d sigma_hh,m

together with the failure condition of Eqs. (8) and (16):

    E = (1/s_-1) sqrt( 1/(4 pi) int_S E_h^2 dS ) = 1.

Here E denotes the validity parameter I of Eq. (27) (E depends linearly on the stresses).
The coefficients a, b and d are determined from reversed tension, pulsating tension and
reversed torsion, Eqs. (20), (21), (24); after defining k = s_-1^2 / t_-1^2 (Appendix),
they read:

    b^2 = (15 - sqrt(D))/2,  D = 225 (1 - 8 (k - 3)^2 / 25),   a^2 = (12 k - 21 + b^2)/2,
    d = (-(3b + 2a) + sqrt((3b + 2a)^2 + 3 (60 s_-1^2/s_0^2 - 15)))/3

and the result is valid for 0.577 < t_-1/s_-1 < 0.866. Problems in the source: Eq. (16)
shows 1/pi although Eqs. (8) and (18)-(24) call for 1/(4 pi) (S = 4 pi); the Appendix
gives a without the factor 1/2 under the root, which Eqs. (20) and (24) require; and
Eq. (18) displays E where E^2 is intended. The quantity max_psi tau_h psi,a is the largest
half-projection of the shear path onto a line in the plane and, for a single harmonic,
equals the radius of the minimum circumscribed circle. The paper uses strengths at a
given life N; this repository instead uses the fatigue limits (Sigm1, Taum1, Sig0, or
the Boehme et al. 2026 Eq. (1) estimate of s_0 from Su).
"""

from __future__ import annotations

from typing import Mapping

import numpy as np

from ..base import CaseResult
from ..invariant_methods.stress_invariants import harmonic_parts
from .bohme_papuga import _plane_amplitudes, _sphere_grid, _strengths

GRID = (48, 192)


def rfb_parameters(f_m1: float, t_m1: float, f_0: float) -> tuple[float, float, float]:
    k = (f_m1 / t_m1) ** 2
    D = 225.0 * (1.0 - 8.0 * (k - 3.0) ** 2 / 25.0)
    if not (4.0 / 3.0 < k < 3.0) or D < 0.0:
        raise ValueError(
            f"RFB requires 0.577 < t_-1/s_-1 < 0.866 (received {t_m1 / f_m1:.3f}); "
            "see the Appendix of Robert et al."
        )
    b = np.sqrt((15.0 - np.sqrt(D)) / 2.0)
    a = np.sqrt((12.0 * k - 21.0 + b**2) / 2.0)
    combined = 3.0 * b + 2.0 * a
    d = (-combined + np.sqrt(combined**2 + 3.0 * (60.0 * f_m1**2 / f_0**2 - 15.0))) / 3.0
    return float(a), float(b), float(d)


def rfb_index(
    S_mean,
    S_sin,
    S_cos,
    f_m1: float,
    t_m1: float,
    f_0: float,
) -> float:
    a, b, d = rfb_parameters(f_m1, t_m1, f_0)
    normals, weights = _sphere_grid(*GRID)
    sigma_a, sigma_m, tau_a, _ = _plane_amplitudes(S_mean, S_sin, S_cos, normals)
    E_h = a * tau_a + b * sigma_a + d * sigma_m
    return float(np.sqrt(np.sum(weights * E_h**2)) / f_m1)


class RobertFogueBahuaud:
    """Eq. (16) with the 1/(4 pi) normalization taken from Eq. (8), returned as E (= I, Eq. 27)."""

    name = "RFB"
    optional_params = {
        "Sig0": "estimated from Su and Sigm1 by Eq. (1) of Boehme et al. 2026",
        "Su": "used only to estimate Sig0",
    }

    def required_params(self) -> set[str]:
        return {"Sigm1", "Taum1"}

    def evaluate_case(
        self,
        *,
        S0,
        E0,
        S1,
        E1,
        params: Mapping[str, float],
        R_list=None,
        harmonics=None,
    ) -> CaseResult:
        f_m1, t_m1, f_0, _ = _strengths(params, name="RFB")
        S_mean, S_sin, S_cos = harmonic_parts(S0, S1, harmonics)
        return CaseResult(values={"": rfb_index(S_mean, S_sin, S_cos, f_m1, t_m1, f_0)})
