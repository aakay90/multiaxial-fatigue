"""Controlled Findley damage evaluation, separate from calibrated life prediction.

Explicit harmonic amplitudes use the shared MCC/MCE library (Cizova, 2021).
The production Findley implementation, adapter and registry remain unchanged.
"""
from __future__ import annotations

import math
from typing import Mapping

import numpy as np

from fatigue.eval.evaluator import cp_rot, _override_plane_normal_scalar
from fatigue.models.base import CaseResult
from fatigue.models.cp_adapter import CPModelAdapter
from fatigue.models.cp_methods.fin import Findley
from fatigue.models.utils.shear_amplitude import shear_amplitude
from fatigue.models.utils.tensors import as33


def _finite_stress(name, value):
    """Validate one finite real stress tensor without imposing a physical scale."""
    raw = np.asarray(value)
    if raw.dtype.kind not in 'biuf':
        raise TypeError(f'{name} must contain real numeric coefficients')
    with np.errstate(over='ignore', under='ignore', invalid='ignore'):
        tensor = as33(name, raw)
    if not np.isfinite(tensor).all() or np.any((raw != 0) & (tensor == 0)):
        raise ValueError(f'{name} must be finite and nonzero values must survive float64 conversion')
    return tensor


def evaluate_findley(
    *, S0, E0, S1, E1, params: Mapping[str, float], R_list=None,
    harmonics: Mapping[str, np.ndarray] | None = None,
    shear_amplitude_algorithm: str | None = None,
) -> CaseResult:
    """Return Findley damage parameters on a supplied discrete plane set.

    With no algorithm selection, delegate exactly to the existing FIN adapter,
    including its MCE/RSS harmonic convention and two-endpoint fallback.
    Explicit ``mcc_harmonic``, ``mce_harmonic`` and ``rss`` selections require
    complete single-harmonic ``S_sin`` and ``S_cos`` tensors in ``harmonics``.
    Each tensor has shape (3, 3), in the same global basis as S0/S1. Plane
    rotations use columns as local axes, with local z as the plane normal.

    S0/S1 must be opposite endpoint tensors whose midpoint is the mean stress,
    as in the existing adapter. They need not be simultaneous component extrema
    of the non-proportional history. E0/E1 are retained for interface consistency
    and shape validation; Findley uses no strain. ``params['k_FI']`` is finite
    and nonnegative. No algorithm identifier is stored in the material mapping.

    On every candidate plane, compute the selected amplitude from the actual
    rotated shear coefficients and retain the existing signed harmonic maximum
    normal stress. Maximise their Findley combination, not shear alone. Both
    result keys, ``''`` (FIN) and ``'_ext'`` (FIN_ext), hold this maximum because
    Findley uses damage itself as the selection metric. Values have stress units.

    Explicit selections return numerical damage parameters only, not calibrated
    life. This function is deliberately absent from the production registry and
    numbered scripts. No curve lookup, calibration or configuration is added.
    See docs/shear-amplitude.md for definitions and calibration limitations.
    """
    if shear_amplitude_algorithm is None:
        return CPModelAdapter(Findley()).evaluate_case(
            S0=S0, E0=E0, S1=S1, E1=E1, params=params,
            R_list=R_list, harmonics=harmonics)

    # Use the library's identifier validation, including its single RSS alias.
    shear_amplitude([0., 0.], [0., 0.], algorithm=shear_amplitude_algorithm)
    if harmonics is None or any(harmonics.get(key) is None for key in ('S_sin', 'S_cos')):
        raise ValueError('Explicit Findley amplitude selection requires both S_sin and S_cos')
    if R_list is None or len(R_list) == 0:
        raise ValueError('Findley evaluation requires at least one candidate plane')
    k = float(params['k_FI'])
    if not math.isfinite(k) or k < 0.:
        raise ValueError('k_FI must be finite and >= 0')
    S0, S1 = _finite_stress('S0', S0), _finite_stress('S1', S1)
    sine = _finite_stress('S_sin', harmonics['S_sin'])
    cosine = _finite_stress('S_cos', harmonics['S_cos'])

    best = -math.inf
    for rotation in R_list:
        # cp_rot preserves the established tensor and orthonormality checks.
        S0r, _, S1r, _ = cp_rot(S0, E0, S1, E1, rotation)
        r = np.asarray(rotation, dtype=float)
        a, b = r.T @ sine @ r, r.T @ cosine @ r
        amplitude = shear_amplitude(a[:2, 2], b[:2, 2], algorithm=shear_amplitude_algorithm)
        # Reuse the normal extrema verbatim, including signed compression.
        S0r, S1r = _override_plane_normal_scalar(S0r, S1r, T_sin_r=a, T_cos_r=b)
        normal_maximum = max(float(S0r[2, 2]), float(S1r[2, 2]))
        damage = amplitude + k * normal_maximum
        if not math.isfinite(damage):
            raise ValueError('FIN: nonfinite plane damage')
        best = max(best, damage)

    return CaseResult(values={'': float(best), '_ext': float(best)})
