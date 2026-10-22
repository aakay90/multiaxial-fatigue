"""Crossland (1956) fatigue criterion in the form restated by Papadopoulos et al. (1997),
Eqs. (65)-(66) on p. 9:

    sqrt(J2,a) + kappa * sigma_H,max <= lambda,   kappa = 3 t_-1/f_-1 - sqrt(3),   lambda = t_-1

where sigma_H,max = sigma_H,a + sigma_H,m (Eq. 45). The returned fatigue index is LHS / lambda
(equal to 1 on the fatigue limit; Papadopoulos' error index is I = 100 (index - 1), Eq. 85).
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


def crossland_index(S_mean, S_sin, S_cos, f_m1: float, t_m1: float) -> float:
    kappa = 3.0 * t_m1 / f_m1 - np.sqrt(3.0)
    sigma_H_a, sigma_H_m = hydrostatic_amplitude_mean(S_mean, S_sin, S_cos)
    return (sqrt_j2_amplitude(S_sin, S_cos) + kappa * (sigma_H_a + sigma_H_m)) / t_m1


class Crossland:
    name = "CROSSLAND"

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
        S_mean, S_sin, S_cos = harmonic_parts(S0, S1, harmonics)
        return CaseResult(
            values={
                "": crossland_index(
                    S_mean,
                    S_sin,
                    S_cos,
                    float(params["Sigm1"]),
                    float(params["Taum1"]),
                )
            }
        )
