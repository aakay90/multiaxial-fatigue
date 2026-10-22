"""Refined critical-plane search (finding F2) against closed forms and dense brute force.

Closed forms: for a single cycle between two load steps (any straight path in tensor space,
coaxial or not) the maximum shear range over all planes is the Mohr radius of the range
tensor, Chiocca et al. (2023) Eq. (6); for a single-harmonic cycle the longest-chord range is
its maximum over the mid-phase phi of 2 (S cos phi - C sin phi).
"""

import numpy as np
import pytest

from multifat.eval.evaluator import best_cp_for_case
from multifat.models.cp_methods.fin import Findley
from multifat.models.cp_methods.fs import FatemiSocie
from multifat.planes.sampling import build_R_list

rng = np.random.default_rng(11)
Z = np.zeros((3, 3))


def _sym(scale):
    a = rng.normal(size=(3, 3)) * scale
    return 0.5 * (a + a.T)


def _mohr_radius(T):
    w = np.linalg.eigvalsh(T)
    return 0.5 * (w[-1] - w[0])


@pytest.mark.parametrize("trial", range(5))
def test_two_step_shear_range_closed_form(trial):
    """FS with k = 0 returns the engineering shear amplitude = tensor shear range."""
    E0, E1 = _sym(1e-3), _sym(1e-3)  # arbitrary, non-coaxial load steps
    best = best_cp_for_case(
        S0=Z,
        S1=Z,
        E0=E0,
        E1=E1,
        R_list=build_R_list(),
        method=FatemiSocie(),
        params={"k_FS": 0.0, "Sy": 300.0},
    )
    assert best.by_metric == pytest.approx(_mohr_radius(E0 - E1), rel=1e-9)
    assert best.ext == pytest.approx(best.by_metric, rel=1e-12)


@pytest.mark.parametrize("trial", range(4))
def test_harmonic_longest_chord_closed_form(trial):
    """FS uses the longest-chord rule; out-of-phase single harmonic, max over phi."""
    mean, s, c = _sym(1e-4), _sym(1e-3), _sym(1e-3)
    best = best_cp_for_case(
        S0=Z,
        S1=Z,
        E0=mean + s,
        E1=mean - s,
        R_list=build_R_list(),
        method=FatemiSocie(),
        params={"k_FS": 0.0, "Sy": 300.0},
        S_sin=Z,
        S_cos=Z,
        E_sin=s,
        E_cos=c,
    )
    phi = np.linspace(0.0, np.pi, 20001)
    exact = max(_mohr_radius(2 * (s * np.cos(p) - c * np.sin(p))) for p in phi)
    assert best.by_metric == pytest.approx(exact, rel=1e-7)


def _findley_brute(S0, S1, k, n=300000):
    u = np.random.default_rng(0).normal(size=(n, 3))
    N = u / np.linalg.norm(u, axis=1, keepdims=True)
    t = N @ (S0 - S1)
    s = np.einsum("pi,pi->p", t, N)
    tau = np.linalg.norm(t - s[:, None] * N, axis=1)
    sn = np.maximum(np.einsum("pi,ij,pj->p", N, S0, N), np.einsum("pi,ij,pj->p", N, S1, N))
    return float(np.max(tau / 2 + k * sn))


@pytest.mark.parametrize("trial", range(4))
def test_findley_matches_dense_brute_force(trial):
    S0, S1, k = _sym(200.0), _sym(200.0), 0.3
    best = best_cp_for_case(
        S0=S0, S1=S1, E0=Z, E1=Z, R_list=build_R_list(), method=Findley(), params={"k_FI": k}
    )
    brute = _findley_brute(S0, S1, k)
    assert best.ext >= brute * (1 - 1e-9)  # never below a dense sample
    assert best.ext == pytest.approx(brute, rel=2e-4)  # dense sample resolution


def test_selected_plane_damage_independent_of_grid():
    """F2: tension-torsion with mean stress; the plane-selected FS value must not depend on
    the starting grid once refined (the 522-plane grid alone was off by ~6 %)."""
    S_a = np.array([[200.0, 120.0, 0.0], [120.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
    S_m = np.array([[150.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])

    def strain(s):
        return (1.3 * s - 0.3 * np.trace(s) * np.eye(3)) / 200000.0

    S0, S1 = S_m + S_a, S_m - S_a
    vals = [
        best_cp_for_case(
            S0=S0,
            S1=S1,
            E0=strain(S0),
            E1=strain(S1),
            R_list=build_R_list(n1=n, n2=2 * n),
            method=FatemiSocie(),
            params={"k_FS": 0.6, "Sy": 400.0},
        ).by_metric
        for n in (20, 40)
    ]
    assert vals[0] == pytest.approx(vals[1], rel=1e-8)
