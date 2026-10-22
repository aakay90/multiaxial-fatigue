"""Amplitudes of stress invariants that the invariant-based criteria rely on (Papadopoulos et al. 1997).

The quantity sqrt(J2,a) gives the radius of the smallest hypersphere that encloses the deviatoric
load path when measured with the J2 norm ||s|| = sqrt(s:s / 2) (Eqs. 38-39). For a single-harmonic
history S(t) = M + A sin t + B cos t the path is a centred ellipse, hence the enclosing hypersphere
shares the centre dev(M) and its radius equals the semi-major axis, i.e. the largest eigenvalue of
the Gram matrix built from dev(A) and dev(B). In the bending-torsion case this reduces to Eq. (44).
"""

from __future__ import annotations

import numpy as np


def _deviatoric(T: np.ndarray) -> np.ndarray:
    T = np.asarray(T, dtype=float)
    return T - np.trace(T) / 3.0 * np.eye(3)


def sqrt_j2_amplitude(S_sin: np.ndarray, S_cos: np.ndarray) -> float:
    S_sin_dev, S_cos_dev = _deviatoric(S_sin), _deviatoric(S_cos)
    g_ss, g_cc, g_sc = (
        0.5 * np.sum(x * y)
        for x, y in ((S_sin_dev, S_sin_dev), (S_cos_dev, S_cos_dev), (S_sin_dev, S_cos_dev))
    )
    return float(np.sqrt(max(0.0, 0.5 * (g_ss + g_cc + np.hypot(g_ss - g_cc, 2.0 * g_sc)))))


def hydrostatic_amplitude_mean(S_mean, S_sin, S_cos) -> tuple[float, float]:
    """Return sigma_H,a and sigma_H,m for the single-harmonic history (Eq. 45: max = a + m)."""
    trace_mean = np.trace(np.asarray(S_mean, float))
    sigma_H_a = (
        np.hypot(
            np.trace(np.asarray(S_sin, float)),
            np.trace(np.asarray(S_cos, float)),
        )
        / 3.0
    )
    return float(sigma_H_a), float(trace_mean / 3.0)


def harmonic_parts(S0, S1, harmonics):
    if harmonics is None:
        start, end = np.asarray(S0, dtype=float), np.asarray(S1, dtype=float)
        return 0.5 * (start + end), 0.5 * (start - end), np.zeros((3, 3))
    return tuple(np.asarray(harmonics[key], dtype=float) for key in ("S_mean", "S_sin", "S_cos"))
