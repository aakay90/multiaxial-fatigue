"""Independent amplitudes of complete single-harmonic two-component paths.

For tau(t) = mean + sine*sin(t) + cosine*cos(t), MCC is the major semiaxis
and MCE is the quadratic combination of both semiaxes (Cizova, 2021).
This module is deliberately unused by the production fatigue criteria.
"""
from __future__ import annotations

import numpy as np

DEFINITION_VERSION = 'harmonic-shear-v1'
ALGORITHMS = ('mcc_harmonic', 'mce_harmonic')


def _coefficients(sine, cosine):
    """Validate real coefficients and scale each vector pair by its largest entry."""
    arrays = []
    for value in (sine, cosine):
        raw = np.asarray(value)
        if raw.dtype.kind not in 'biuf':
            raise TypeError('Harmonic coefficients must be real numeric arrays')
        with np.errstate(over='ignore', invalid='ignore'):
            array = np.asarray(raw, dtype=np.float64)
        if array.ndim < 1 or array.shape[-1] != 2:
            raise ValueError('Each coefficient array must have shape (..., 2)')
        if not np.isfinite(array).all():
            raise ValueError('Harmonic coefficients must be finite in float64')
        arrays.append(array)
    a, b = arrays
    if a.shape != b.shape:
        raise ValueError('Sine and cosine coefficient arrays must have identical shapes')
    scale = np.maximum(np.max(np.abs(a), axis=-1), np.max(np.abs(b), axis=-1))
    # Exact zero is the only degeneracy threshold. Scaling protects small paths.
    divisor = np.where(scale == 0, 1., scale)
    with np.errstate(under='ignore'):
        return a / divisor[..., None], b / divisor[..., None], scale


def shear_amplitude(sine, cosine, *, algorithm='mcc_harmonic'):
    """Return an amplitude in the coefficient units, with no temporal sampling.

    Inputs are two real finite vectors of shape (2,), or identically shaped
    batches (..., 2), containing sine and cosine coefficients in a common tangent
    basis. A scalar input pair returns float; batches return an ndarray with the
    trailing component axis removed. Broadcasting between input shapes is rejected.

    ``mcc_harmonic`` gives the major singular value of [sine cosine].
    ``mce_harmonic`` gives sqrt(||sine||**2 + ||cosine||**2); ``rss`` is its alias.
    For a complete harmonic ellipse MCC also equals half the longest chord.

    Mean traction is deliberately not an input. These are translation-invariant
    amplitudes, not ranges or maxima of the total instantaneous traction magnitude.
    Tensorial versus engineering shear strain conventions belong to the caller.
    ``method_default`` requires future method-specific resolution and is rejected.

    Calculations use scaled float64 coefficients. A genuinely unrepresentable
    output raises OverflowError; subnormal outputs retain float64 rounding.
    The routine does not enclose arbitrary sampled or multi-frequency paths.
    """
    if not isinstance(algorithm, str) or algorithm not in (*ALGORITHMS, 'rss'):
        raise ValueError(f'Unknown shear amplitude algorithm {algorithm!r}; choose {ALGORITHMS} or rss')
    a, b, scale = _coefficients(sine, cosine)
    # Values omitted by underflow after scaling cannot affect the leading norm
    # at float64 precision. No absolute physical-amplitude cutoff is introduced.
    with np.errstate(under='ignore'):
        aa, bb = np.sum(a * a, axis=-1), np.sum(b * b, axis=-1)
        if algorithm == 'mcc_harmonic':
            ab = np.sum(a * b, axis=-1)
            radius = np.sqrt(0.5 * (aa + bb + np.hypot(aa - bb, 2 * ab)))
        else:
            radius = np.sqrt(aa + bb)
    try:
        with np.errstate(over='raise', invalid='raise', under='ignore'):
            result = scale * radius
    except FloatingPointError as exc:
        raise OverflowError('Shear amplitude exceeds the finite float64 range') from exc
    return float(result) if result.ndim == 0 else result
