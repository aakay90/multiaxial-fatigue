"""Equivalent stress amplitude of the COIN LiWI criterion, after Schmidt & Kraft (2023),
Int J Fatigue 168:107474, doi:10.1016/j.ijfatigue.2022.107474 (roadmap entry G08),
in the single-frequency variant, Eqs. (21)-(32):

    sigma_eq,ka^2 = I1^2 - k_a^2 I2  (Eq. 21, Mertens),  k_a = sigma_w / tau_w (Eq. 22)
    Hermitian magnitude  H  = |tr Z|^2 - k_a^2 (|tr Z|^2 - tr(Z conj(Z)))/2         (Eqs. 24-27)
    complex square       C  = (tr Z)^2 - k_a^2 ((tr Z)^2 - tr(Z Z))/2               (Eqs. 28-30)
    sigma_COIN = sqrt(k_phi H + (1 - k_phi) |C|)                                     (Eqs. 31-32)

Here Z denotes the complex amplitude tensor of sigma(t) = Re(Z e^{j w t}) (Eq. 23, stated
for plane stress; the invariants carry over to 3-D without modification). Writing Q(t) for
the time-domain quadratic form of Eq. (21), one has H = 2 mean(Q) and |C| = 2 (max Q -
mean Q), so k_phi = 1 gives the RMS of the invariants, k_phi = 0.5 the static maximum, and
k_phi = 0 discards invariants shifted by 90 deg (p.6). No prescription for k_phi is offered
in the paper (it is fitted per material, Table 3: 0.85-1.10); this repository takes the
parameter ``k_phi`` when it is given and falls back to 1 otherwise. No mean-stress term is
included in the amplitude (the paper accounts for mean stress through the damage parameters
PRAM/PRAJ). The result is returned as sigma_COIN / s_-1.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np

from ..base import CaseResult
from .stress_invariants import harmonic_parts


def coin_amplitude(S_sin, S_cos, k_a: float, k_phi: float = 1.0) -> float:
    Z = np.asarray(S_cos, dtype=float) - 1j * np.asarray(S_sin, dtype=float)
    tr_Z = np.trace(Z)
    H = abs(tr_Z) ** 2 - 0.5 * k_a**2 * (abs(tr_Z) ** 2 - np.real(np.trace(Z @ Z.conj().T)))
    C = tr_Z**2 - 0.5 * k_a**2 * (tr_Z**2 - np.trace(Z @ Z))
    return float(np.sqrt(max(k_phi * H + (1.0 - k_phi) * abs(C), 0.0)))


class CoinLiwi:
    """COIN LiWI amplitude sigma_COIN / s_-1, with k_a = s_-1/t_-1 (Eq. 22)."""

    name = "COIN"
    optional_params = {"k_phi": "1.0 (RMS formulation)"}

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
            raise ValueError("COIN needs Sigm1 and Taum1 to be positive and finite")
        k_phi = params.get("k_phi")
        k_phi = 1.0 if k_phi is None else float(k_phi)
        _, S_sin, S_cos = harmonic_parts(S0, S1, harmonics)
        return CaseResult(values={"": coin_amplitude(S_sin, S_cos, f_m1 / t_m1, k_phi) / f_m1})
