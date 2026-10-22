"""Sines (1959) criterion, in the form restated and applied by Papadopoulos et al. (1997),
Eqs. (62)-(64), p. 9:

    sqrt(J2,a) + kappa sigma_H,m <= t_-1,   kappa = sqrt(3) f_-1 / sigma_f                  (64)

Here sigma_f denotes the ultimate tensile strength (Su). The paper evaluates Eq. (64) in its
Table 1. This form follows from Sines' own calibration, Eq. (63),
kappa = 3 t_-1/f_0 - sqrt(3), together with the Goodman estimate
f_0 = f_-1/(1 + f_-1/sigma_f), but only when t_-1 = f_-1/sqrt(3) (the torsion-to-bending
ratio implied by Sines' criterion). The repository implementation adheres to the printed
Eq. (64), hence kappa is independent of t_-1. The fatigue index returned is LHS / t_-1.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np

from ..base import CaseResult
from .stress_invariants import (
    harmonic_parts,
    hydrostatic_amplitude_mean,
    sqrt_j2_amplitude,
)


def sines_kappa(f_m1: float, sigma_f: float) -> float:
    """kappa of Eq. (64)."""
    return np.sqrt(3.0) * f_m1 / sigma_f


def sines_index(S_mean, S_sin, S_cos, t_m1: float, kappa: float) -> float:
    _, sigma_H_m = hydrostatic_amplitude_mean(S_mean, S_sin, S_cos)
    return (sqrt_j2_amplitude(S_sin, S_cos) + kappa * sigma_H_m) / t_m1


class Sines:
    name = "SINES"

    def required_params(self) -> set[str]:
        return {"Sigm1", "Taum1", "Su"}

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
        f_m1, t_m1, su = (float(params[k]) for k in ("Sigm1", "Taum1", "Su"))
        S_mean, S_sin, S_cos = harmonic_parts(S0, S1, harmonics)
        return CaseResult(
            values={"": sines_index(S_mean, S_sin, S_cos, t_m1, sines_kappa(f_m1, su))}
        )
