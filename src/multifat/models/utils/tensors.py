"""Shared tensor input validation; no constitutive or fatigue assumptions."""

import numpy as np


def as33(name: str, A: np.ndarray) -> np.ndarray:
    """Convert a single 3×3 tensor to floating point, preserving shape checks."""
    A = np.asarray(A, dtype=float)
    if A.shape != (3, 3):
        raise ValueError(f"{name} must be shape (3,3); got {A.shape}.")
    return A
