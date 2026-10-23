# multifat/models/energy_based_methods/swtd.py
# SWTD model: deviatoric counterpart of SWT, after Kujawski (2014) http://dx.doi.org/10.1016/j.ijfatigue.2013.12.002

from __future__ import annotations

from typing import Mapping

import numpy as np
from ..base import CaseResult

_CHORD_ANGLES = np.linspace(0.0, np.pi, 360, endpoint=False)


def _deviator(A: np.ndarray) -> np.ndarray:
    sym = 0.5 * (np.asarray(A, dtype=float) + np.asarray(A, dtype=float).T)
    return sym - np.trace(sym) / 3.0 * np.eye(3)


def swtd_eq25(S_max: np.ndarray, S_min: np.ndarray, E_amp: np.ndarray) -> float:
    """Kujawski (2014) Eq. (25): the MAX over i of S_max,i |e_a,i| and S_min,i |e_a,i|.

    Here e_a,i denote the principal deviatoric strain amplitudes, while S_max,i and S_min,i are the
    deviatoric stresses of the maximum and minimum states resolved along the SAME principal
    directions (the normal components expressed in the principal frame of the strain amplitude).
    When the states are coaxial this coincides with the index pairing of Eqs. (23)-(24) in the
    paper; sorting the two spectra separately would instead pair physically distinct directions.
    """
    eigvals, eigvecs = np.linalg.eigh(_deviator(E_amp))
    E_a = np.abs(eigvals)
    S_peak = np.einsum("ji,jk,ki->i", eigvecs, _deviator(S_max), eigvecs)
    S_trough = np.einsum("ji,jk,ki->i", eigvecs, _deviator(S_min), eigvecs)
    return float(max(np.max(S_peak * E_a), np.max(S_trough * E_a)))


class SWTD:
    """Kujawski (2014) SWTD, Eq. (25).

    For proportional cycles the two load steps are used (step 0 = maximum, step 1 = minimum) along
    with the strain amplitude (E0 - E1)/2. The paper prescribes no procedure for non-proportional
    histories; for a single-harmonic history S(t) = M + S_s sin t + S_c cos t this repository
    evaluates every diametral chord of the path, i.e. the states M +/- A(psi) with
    A(psi) = S_s cos psi - S_c sin psi (and likewise for strain), and returns the largest Eq. (25)
    value (documented adaptation).
    """

    name = "SWTD"

    def required_params(self) -> set[str]:
        return set()

    def evaluate_case(
        self,
        *,
        S0: np.ndarray,
        E0: np.ndarray,
        S1: np.ndarray,
        E1: np.ndarray,
        params: Mapping[str, float],
        R_list=None,
        harmonics=None,
    ) -> CaseResult:
        has_cos_component = harmonics is not None and (
            np.any(np.asarray(harmonics["S_cos"]) != 0.0)
            or np.any(np.asarray(harmonics["E_cos"]) != 0.0)
        )
        if has_cos_component:
            return CaseResult(values={"": swtd_single_harmonic(harmonics)})
        E_a = 0.5 * (np.asarray(E0) - np.asarray(E1))
        return CaseResult(values={"": swtd_eq25(S0, S1, E_a)})


def swtd_single_harmonic(h: Mapping[str, np.ndarray], psi: np.ndarray = _CHORD_ANGLES) -> float:
    """Highest Eq. (25) value among the diametral chords of a single-harmonic history."""
    S_mean, S_sin, S_cos = (np.asarray(h[k], dtype=float) for k in ("S_mean", "S_sin", "S_cos"))
    E_sin, E_cos = (np.asarray(h[k], dtype=float) for k in ("E_sin", "E_cos"))
    largest = -np.inf
    for angle in psi:
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        A_S = S_sin * cos_a - S_cos * sin_a
        A_E = E_sin * cos_a - E_cos * sin_a
        largest = max(largest, swtd_eq25(S_mean + A_S, S_mean - A_S, A_E))
    return float(largest)
