"""Papadopoulos criteria evaluated on the resolved shear stress amplitude T_a(phi, theta, chi).

Formulation from the roadmap (N03) of Papadopoulos (2001), doi:10.1016/S0142-1123(01)00059-7:

    generalised shear amplitude  T_a(n)^2 = (1/pi) int_0^2pi tau_a(n, chi)^2 dchi    (Eq. 10)
    fatigue limit                max_n T_a + alpha sigma_H,max <= gamma              (Eqs. 1, 25)
    multiaxial S-N curve         (max_n T_a + alpha sigma_H,a) / (1 - (alpha/gamma) sigma_H,m)
                                 = gamma_N                                           (Eqs. 40-41)

where gamma = t_-1 and alpha = 3 (t_-1/f_-1 - 1/2) (Eqs. 16, 24). The quantity gamma_N is the
equivalent fully reversed torsion amplitude (Eq. 42), hence gamma_N / t_-1 = 1 on the fatigue
limit; with sigma_H,m = 0 it coincides with the index of Eq. (25). Eq. (40) writes T_a without the
max of Eqs. (39) and (41) (a notational slip). Along a single-harmonic path the shear traction on
plane n reads t_s sin wt + t_c cos wt, the resolved amplitude along a line m is
sqrt((m.t_s)^2 + (m.t_c)^2), and Eq. (10) integrates exactly to T_a^2 = |t_s|^2 + |t_c|^2. The
maximisation over planes relies on the BP sphere grid together with its pattern-search refinement.

Volumetric form, Papadopoulos (1999, CISM Courses 392, doi:10.1007/978-3-7091-2474-1_3):

    sqrt(<T_a^2>) + alpha sigma_H,max <= beta,  sqrt(<T_a^2>) = sqrt(5/(8 pi^2) int int int
    T_a^2 dchi sin(theta) dtheta dphi)   (Eqs. 4.11-4.12),  beta = t_-1, alpha = 3 t_-1/s_-1 - sqrt(3)
    (Eqs. 5.21-5.22). Averaging (m.A.n)^2 over all planes and lines yields J2(A)/5, so that
    sqrt(<T_a^2>) = sqrt(J2(A) + J2(B)) for S(t) = M + A sin wt + B cos wt: Eq. (5.20) in phase,
    Eq. (5.46) out of phase. Eq. (5.19) prints 1/(4 pi) whereas integrating cos^2(chi) in Eq. (5.18)
    yields 1/(8 pi); only the latter recovers Eq. (5.20).
"""

from __future__ import annotations

from typing import Mapping

import numpy as np

from ..base import CaseResult
from ..invariant_methods.stress_invariants import (
    _deviatoric,
    harmonic_parts,
    hydrostatic_amplitude_mean,
)
from .bohme_papuga import _plane_components, _sphere_grid, refine_plane_max


def generalised_shear_amplitude(S_sin, S_cos, normals: np.ndarray) -> np.ndarray:
    """Evaluate Eq. (10) of the 2001 paper on every plane listed as a row of ``normals``, single harmonic."""
    _, shear_sin = _plane_components(np.asarray(S_sin, dtype=float), normals)
    _, shear_cos = _plane_components(np.asarray(S_cos, dtype=float), normals)
    return np.sqrt(np.sum(shear_sin * shear_sin, axis=1) + np.sum(shear_cos * shear_cos, axis=1))


def max_generalised_shear_amplitude(S_sin, S_cos) -> float:
    normals, _ = _sphere_grid()

    def shear_on(grid):
        return generalised_shear_amplitude(S_sin, S_cos, grid)

    return refine_plane_max(shear_on, normals, shear_on(normals))


def papadopoulos_2001_index(S_mean, S_sin, S_cos, f_m1: float, t_m1: float) -> float:
    """Return gamma_N / t_-1 from Eq. (41); becomes infinite once sigma_H,m reaches gamma/alpha."""
    alpha = 3.0 * (t_m1 / f_m1 - 0.5)
    sigma_H_a, sigma_H_m = hydrostatic_amplitude_mean(S_mean, S_sin, S_cos)
    denominator = 1.0 - alpha / t_m1 * sigma_H_m
    if denominator <= 0.0:
        return float("inf")
    return (max_generalised_shear_amplitude(S_sin, S_cos) + alpha * sigma_H_a) / denominator / t_m1


def rms_shear_amplitude(S_sin, S_cos) -> float:
    """sqrt(<T_a^2>) of the 1999 criterion, see Eqs. (4.12), (5.20) and (5.46)."""
    S_sin_dev, S_cos_dev = _deviatoric(S_sin), _deviatoric(S_cos)
    return float(np.sqrt(0.5 * (np.sum(S_sin_dev * S_sin_dev) + np.sum(S_cos_dev * S_cos_dev))))


def papadopoulos_1999_index(S_mean, S_sin, S_cos, f_m1: float, t_m1: float) -> float:
    """(sqrt(<T_a^2>) + alpha sigma_H,max) / beta, per Eqs. (4.11) and (5.21)-(5.22)."""
    alpha = 3.0 * t_m1 / f_m1 - np.sqrt(3.0)
    sigma_H_a, sigma_H_m = hydrostatic_amplitude_mean(S_mean, S_sin, S_cos)
    return (rms_shear_amplitude(S_sin, S_cos) + alpha * (sigma_H_a + sigma_H_m)) / t_m1


class Papadopoulos:
    """Multiaxial S-N form of Papadopoulos (2001), Eq. (41), returned as gamma_N / t_-1."""

    name = "PAPADOPOULOS"

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
        f_m1, t_m1 = float(params["Sigm1"]), float(params["Taum1"])
        if not (np.isfinite(f_m1) and np.isfinite(t_m1) and f_m1 > 0 and t_m1 > 0):
            raise ValueError(
                "PAPADOPOULOS needs Sigm1 and Taum1 to be strictly positive and finite"
            )
        S_mean, S_sin, S_cos = harmonic_parts(S0, S1, harmonics)
        return CaseResult(values={"": papadopoulos_2001_index(S_mean, S_sin, S_cos, f_m1, t_m1)})
