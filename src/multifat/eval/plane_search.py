"""Continuous critical-plane search: grid, analytical seed planes, and local refinement.

A finite grid of planes only slightly underestimates the maximum damage, yet the damage
computed on the plane that maximises the selection metric carries a first-order error: the
metric is stationary at its peak while the damage is not (finding F2). The search therefore

1. evaluates the global grid;
2. adds analytical candidate planes following Chiocca et al. (2023, IJMS 242:107974;
   2024, IJF 182:108191): principal and conjugate (±45 deg) directions of the stress/strain
   range tensors on all three Mohr circles, sweeps along the largest Mohr circles of the
   range and load-step tensors and, for single-harmonic loading, the same eigen-planes of
   2 (S cos phi - C sin phi), whose maximum over phi is the longest-chord range of any plane;
3. refines the strongest candidates (ranked by metric and by damage) with a pattern search on
   the plane normal, starting from the best few planes and from the best planes of further
   distinct basins (planes separated by at least ``_BASIN_SEP_DEG``), so that each of several
   tied maxima gets refined, not just the one the grid happens to sample best.

The damage on the critical plane is the largest damage among planes whose metric matches the
maximum within the relative tolerance ``TIE_RTOL``: the conjugate critical planes of Chiocca
et al. (2023), Eq. (12), share the same metric but have different normal stress.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np

TIE_RTOL = 1e-8
_N_SEEDS = 4
_N_BASINS = 4
_BASIN_SEP_DEG = 10.0
_N_ITER = 26
_STEP0, _SHRINK = 0.06, 0.55
_PHI = np.linspace(0.0, np.pi, 24, endpoint=False)
_OMEGA = np.linspace(0.0, np.pi, 36, endpoint=False)
_OFFSETS = np.concatenate([np.eye(3), -np.eye(3)])


def frames_from_normals(normals: np.ndarray) -> np.ndarray:
    """Orthonormal frames (P, 3, 3) whose third column is the plane normal.

    The in-plane axes are arbitrary: every critical-plane method uses only the plane-normal
    component and the magnitude of the in-plane shear vector.
    """
    normals = np.asarray(normals, dtype=float)
    normals = normals / np.linalg.norm(normals, axis=1, keepdims=True)
    ref = np.where((np.abs(normals[:, 0]) < 0.9)[:, None], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0])
    e1 = np.cross(normals, ref)
    e1 /= np.linalg.norm(e1, axis=1, keepdims=True)
    return np.stack([e1, np.cross(normals, e1), normals], axis=2)


def _principal_and_conjugate_normals(tensor: np.ndarray) -> list[np.ndarray]:
    """Principal directions plus the six ±45 deg conjugate directions of a symmetric tensor."""
    _, evecs = np.linalg.eigh(0.5 * (tensor + tensor.T))
    normals = [evecs[:, 0], evecs[:, 1], evecs[:, 2]]
    for p, q in ((2, 0), (2, 1), (1, 0)):
        normals += [
            (evecs[:, p] + evecs[:, q]) / np.sqrt(2.0),
            (evecs[:, p] - evecs[:, q]) / np.sqrt(2.0),
        ]
    return normals


def _mohr_circle_normals(tensor: np.ndarray) -> np.ndarray:
    """Normals along the largest Mohr circle of ``tensor`` (rotation about its middle eigenvector)."""
    _, evecs = np.linalg.eigh(0.5 * (tensor + tensor.T))
    cos_w, sin_w = np.cos(_OMEGA)[:, None], np.sin(_OMEGA)[:, None]
    return cos_w * evecs[:, 2] + sin_w * evecs[:, 0]


def seed_normals(*, S0, E0, S1, E1, S_sin=None, S_cos=None, E_sin=None, E_cos=None) -> np.ndarray:
    """Analytical candidate plane normals for one load case (see the module docstring)."""
    s0, s1, e0, e1 = (np.asarray(x, dtype=float) for x in (S0, S1, E0, E1))
    candidates = []
    # Undefined strains (no E or nu) yield no seeds.
    valid = [t for t in (s0 - s1, e0 - e1, s0, s1) if np.isfinite(t).all()]
    for t in valid:
        candidates += _principal_and_conjugate_normals(t)
    for t in valid:
        candidates += list(_mohr_circle_normals(t))
    for sine, cosine in ((S_sin, S_cos), (E_sin, E_cos)):
        if sine is None or cosine is None:
            continue
        sine, cosine = np.asarray(sine, dtype=float), np.asarray(cosine, dtype=float)
        if not np.any(cosine) or not (np.isfinite(sine).all() and np.isfinite(cosine).all()):
            continue
        for phi in _PHI:
            candidates += _principal_and_conjugate_normals(
                2.0 * (sine * np.cos(phi) - cosine * np.sin(phi))
            )
    normals = np.asarray(candidates)
    nonzero = np.linalg.norm(normals, axis=1) > 1e-12
    return normals[nonzero] / np.linalg.norm(normals[nonzero], axis=1, keepdims=True)


def _best_per_basin(normals, values, count, blocked):
    """Indices of the best planes from up to ``count`` separate basins (n and -n denote the
    same plane) lying outside the neighbourhoods of the planes listed in ``blocked``."""
    cos_min_sep = np.cos(np.radians(_BASIN_SEP_DEG))
    available = np.ones(len(values), dtype=bool)
    for b in blocked:
        available &= np.abs(normals @ normals[b]) < cos_min_sep
    chosen = []
    for _ in range(count):
        if not available.any():
            break
        idx = int(np.flatnonzero(available)[np.argmax(values[available])])
        chosen.append(idx)
        available &= np.abs(normals @ normals[idx]) < cos_min_sep
    return chosen


def search(evaluate_normals, grid_normals, grid_damage, grid_metric, seed_normals):
    """Grid, seeds, and pattern-search refinement.

    ``evaluate_normals(normals) -> (damage, metric)``. Returns ``(all_damage, all_metric,
    selection_damage, selection_metric, selection_normals)``: the first pair spans every evaluated plane (for
    the overall maximum damage) and the rest spans the selectable planes (grid, seeds,
    converged refinement points). Planes visited midway through the pattern search are kept
    out of the selection: near the flat metric maximum they would enter the tie set while
    carrying a first-order damage error.
    """
    seed_damage, seed_metric = evaluate_normals(seed_normals)
    normals = np.concatenate([grid_normals, seed_normals])
    damage = np.concatenate([grid_damage, seed_damage])
    metric = np.concatenate([grid_metric, seed_metric])

    unit = normals / np.linalg.norm(normals, axis=1, keepdims=True)
    starts, kinds = [], []
    for kind, values in enumerate((metric, damage)):  # 0: maximise metric, 1: maximise damage
        top = list(np.argsort(values, kind="stable")[-_N_SEEDS:])
        picked = top + _best_per_basin(unit, values, _N_BASINS, top)
        starts.append(normals[picked])
        kinds += [kind] * len(picked)
    cur = np.concatenate(starts)
    cur = cur / np.linalg.norm(cur, axis=1, keepdims=True)
    kinds = np.asarray(kinds)
    cur_damage, cur_metric = evaluate_normals(cur)
    best = np.where(kinds == 0, cur_metric, cur_damage)
    step = _STEP0
    pool_damage, pool_metric = [damage, cur_damage], [metric, cur_metric]
    for _ in range(_N_ITER):
        trial = (cur[:, None, :] + step * _OFFSETS[None]).reshape(-1, 3)
        trial /= np.linalg.norm(trial, axis=1, keepdims=True)
        trial_damage, trial_metric = evaluate_normals(trial)
        pool_damage.append(trial_damage)
        pool_metric.append(trial_metric)
        values = np.where(np.repeat(kinds, len(_OFFSETS)) == 0, trial_metric, trial_damage).reshape(
            len(cur), -1
        )
        pick = np.argmax(values, axis=1)
        improved = values[np.arange(len(cur)), pick] > best
        trial = trial.reshape(len(cur), -1, 3)
        cur = np.where(improved[:, None], trial[np.arange(len(cur)), pick], cur)
        best = np.where(improved, values[np.arange(len(cur)), pick], best)
        step *= _SHRINK
    fin_damage, fin_metric = evaluate_normals(cur)
    selection_damage = np.concatenate([damage, fin_damage])
    selection_metric = np.concatenate([metric, fin_metric])
    selection_normals = np.concatenate([normals, cur])
    return (
        np.concatenate(pool_damage + [fin_damage]),
        np.concatenate(pool_metric + [fin_metric]),
        selection_damage,
        selection_metric,
        selection_normals,
    )


def critical_only(method) -> bool:
    """True for methods whose damage is defined only on the critical plane (no ``_ext``)."""
    return not getattr(method, "ext_variant", True)


def select_with_ties(
    name: str,
    all_damage,
    all_metric,
    selection_damage,
    selection_metric,
    BestCP,
    critical_only=False,
):
    """Largest damage overall; among the selectable planes, the largest damage among those
    tying the maximum metric (``TIE_RTOL``). With ``critical_only`` (methods defining damage
    only on the selected plane, ``ext_variant = False``) the damage may be +inf away from it
    and ``ext`` repeats ``by_metric``."""
    if critical_only:
        if not np.all(np.isfinite(all_metric)) or np.any(np.isnan(all_damage)):
            raise ValueError(f"{name}: nonfinite selection metric or NaN plane damage")
    else:
        for values in (all_damage, all_metric):
            if not np.all(np.isfinite(values)):
                raise ValueError(f"{name}: nonfinite plane damage or selection metric")
    peak = float(np.max(selection_metric))
    tied = selection_metric >= peak - TIE_RTOL * abs(peak) - 1e-14
    at_peak = float(np.max(selection_damage[tied]))
    ext = at_peak if critical_only else float(np.max(all_damage))
    return BestCP(ext=ext, by_metric=at_peak)


def refined_best(
    method,
    params: Mapping[str, float],
    case: Mapping,
    grid,
    R_list,
    prepare,
    evaluate,
    BestCP,
    return_normals: bool = False,
):
    """Refined critical-plane values; ``grid`` is the prepared grid PlaneSet of the case."""
    grid_damage, grid_metric = evaluate(method, grid, params)
    options = dict(
        tau_max=grid.tau_max is not None,
        strain_ranges=grid.strain_ranges is not None,
        shear_rule=case["shear_rule"],
        E=params.get("E"),
        nu=params.get("nu"),
    )
    tensors = {k: case[k] for k in ("S0", "E0", "S1", "E1", "S_sin", "S_cos", "E_sin", "E_cos")}

    def evaluate_normals(normals):
        planes = prepare(R_list=frames_from_normals(normals), **tensors, **options)
        return evaluate(method, planes, params)

    seeds = seed_normals(**tensors)
    grid_normals = np.asarray(R_list, dtype=float)[:, :, 2]
    *pooled, selection_normals = search(
        evaluate_normals, grid_normals, grid_damage, grid_metric, seeds
    )
    best = select_with_ties(method.name, *pooled, BestCP, critical_only=critical_only(method))
    if return_normals:
        return best, selection_normals
    return best
