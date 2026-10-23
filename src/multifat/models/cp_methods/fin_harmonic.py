"""Standalone Findley damage assessment, kept apart from calibrated life prediction.

Taken over from upstream (A. Chiocca, 176ce53, 50dabaf); only the imports differ.

Explicit harmonic amplitudes go through the common MCC/MCE routines (Cizova, 2021).
The production Findley model, its adapter and the registry stay untouched.
"""

from __future__ import annotations

import math
from typing import Mapping

import numpy as np

from multifat.eval.evaluator import cp_rot, _replace_normal_component
from multifat.models.base import CaseResult
from multifat.models.cp_adapter import CPModelAdapter
from multifat.models.cp_methods.fin import Findley
from multifat.models.utils.shear_amplitude import shear_amplitude
from multifat.models.utils.tensors import as33


def _validated_stress_tensor(label, raw_value):
    """Check a single real stress tensor is finite, without assuming any physical scale."""
    array = np.asarray(raw_value)
    if array.dtype.kind not in "biuf":
        raise TypeError(f"{label} must hold real numeric coefficients")
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        tensor = as33(label, array)
    if not np.isfinite(tensor).all() or np.any((array != 0) & (tensor == 0)):
        raise ValueError(
            f"{label} must be finite, and nonzero entries must survive float64 conversion"
        )
    return tensor


def evaluate_findley(
    *,
    S0,
    E0,
    S1,
    E1,
    params: Mapping[str, float],
    R_list=None,
    harmonics: Mapping[str, np.ndarray] | None = None,
    shear_amplitude_algorithm: str | None = None,
) -> CaseResult:
    """Return Findley damage parameters on a caller-supplied discrete plane set.

    Without an algorithm choice, the call is handed straight to the existing FIN
    adapter, keeping its MCE/RSS harmonic convention and its two-endpoint fallback.
    Explicit ``mcc_harmonic``, ``mce_harmonic`` and ``rss`` choices demand complete
    single-harmonic ``S_sin`` and ``S_cos`` tensors inside ``harmonics``. Every
    tensor is (3, 3) in the same global basis as S0/S1. Plane rotations take their
    columns as local axes, with local z as the plane normal.

    S0/S1 must be opposite endpoint tensors whose midpoint is the mean stress, the
    same convention as the existing adapter. They need not be simultaneous
    component extrema of the non-proportional history. E0/E1 are kept for interface
    consistency and shape validation; Findley uses no strain. ``params['k_FI']`` is
    finite and nonnegative. No algorithm identifier is stored in the material mapping.

    On each candidate plane, the chosen amplitude is computed from the actually
    rotated shear coefficients, while the existing signed harmonic maximum normal
    stress is retained. Their Findley combination is maximised, not shear alone.
    Both result keys, ``''`` (FIN) and ``'_ext'`` (FIN_ext), carry this maximum,
    because Findley uses damage itself as the selection metric. Values are in
    stress units.

    Explicit choices return numerical damage parameters only, not calibrated life.
    This function is deliberately left out of the production registry and the
    numbered scripts. No curve lookup, calibration or configuration is introduced.
    See docs/shear-amplitude.md for the definitions and the calibration limits.
    """
    if shear_amplitude_algorithm is None:
        return CPModelAdapter(Findley()).evaluate_case(
            S0=S0, E0=E0, S1=S1, E1=E1, params=params, R_list=R_list, harmonics=harmonics
        )

    # Lean on the library's identifier check, including its single RSS alias.
    shear_amplitude([0.0, 0.0], [0.0, 0.0], algorithm=shear_amplitude_algorithm)
    if harmonics is None or any(harmonics.get(key) is None for key in ("S_sin", "S_cos")):
        raise ValueError("Explicit Findley amplitude selection needs both S_sin and S_cos")
    if R_list is None or len(R_list) == 0:
        raise ValueError("Findley evaluation needs at least one candidate plane")
    k_FI = float(params["k_FI"])
    if not math.isfinite(k_FI) or k_FI < 0.0:
        raise ValueError("k_FI must be finite and >= 0")
    S0_checked = _validated_stress_tensor("S0", S0)
    S1_checked = _validated_stress_tensor("S1", S1)
    S_sin = _validated_stress_tensor("S_sin", harmonics["S_sin"])
    S_cos = _validated_stress_tensor("S_cos", harmonics["S_cos"])

    best_damage = -math.inf
    for R in R_list:
        # cp_rot keeps the established tensor and orthonormality checks.
        S0_rotated, _, S1_rotated, _ = cp_rot(S0_checked, E0, S1_checked, E1, R)
        axes = np.asarray(R, dtype=float)
        S_sin_rotated = axes.T @ S_sin @ axes
        S_cos_rotated = axes.T @ S_cos @ axes
        tau_a = shear_amplitude(
            S_sin_rotated[:2, 2],
            S_cos_rotated[:2, 2],
            algorithm=shear_amplitude_algorithm,
        )
        # Reuse the normal extrema verbatim, signed compression included.
        S0_rotated, S1_rotated = _replace_normal_component(
            S0_rotated, S1_rotated, T_sin_r=S_sin_rotated, T_cos_r=S_cos_rotated
        )
        sigma_max = max(float(S0_rotated[2, 2]), float(S1_rotated[2, 2]))
        DP = tau_a + k_FI * sigma_max
        if not math.isfinite(DP):
            raise ValueError("FIN: nonfinite plane damage")
        best_damage = max(best_damage, DP)

    return CaseResult(values={"": float(best_damage), "_ext": float(best_damage)})
