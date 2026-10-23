"""Damage comparison that is independent of the master-curve slope."""

import numpy as np


def log10_dp_ratio(expected, observed):
    """Return log10(DP_e/DP); NaN when an input is nonpositive or nonfinite."""
    ref, meas = np.broadcast_arrays(
        np.asarray(expected, dtype=float), np.asarray(observed, dtype=float)
    )
    result = np.full(ref.shape, np.nan)
    usable = np.isfinite(ref) & np.isfinite(meas) & (ref > 0) & (meas > 0)
    result[usable] = np.log10(ref[usable]) - np.log10(meas[usable])
    return result
