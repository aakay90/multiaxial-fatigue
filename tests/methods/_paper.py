"""Helpers for tests that reproduce numbers printed in the source publications."""

from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data" / "papers"


def load_table(name: str) -> pd.DataFrame:
    """Read tests/data/papers/<name>.csv; '#' lines hold the source citation and caveats."""
    return pd.read_csv(DATA / f"{name}.csv", comment="#")


def bending_torsion(sigma: float, tau: float) -> np.ndarray:
    """Surface stress of a round bar: axial/bending sigma_xx and torsional shear tau_xy."""
    return np.array([[sigma, tau, 0.0], [tau, 0.0, 0.0], [0.0, 0.0, 0.0]])


def frame_with_normal(n: np.ndarray) -> np.ndarray:
    """Orthonormal R whose third column is the plane normal n (repository convention)."""
    n = np.asarray(n, dtype=float) / np.linalg.norm(n)
    helper = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    a = np.cross(n, helper)
    a /= np.linalg.norm(a)
    b = np.cross(n, a)
    return np.column_stack([a, b, n])


def rotate(T: np.ndarray, R: np.ndarray) -> np.ndarray:
    """Passive change of basis used by the evaluator: R.T @ T @ R."""
    return R.T @ T @ R


def max_shear_normals(S: np.ndarray) -> list[np.ndarray]:
    """The two maximum-shear plane normals (e1 +- e3)/sqrt(2) of a symmetric tensor."""
    w, v = np.linalg.eigh(S)
    e1, e3 = v[:, 2], v[:, 0]
    return [(e1 + e3) / np.sqrt(2.0), (e1 - e3) / np.sqrt(2.0)]
