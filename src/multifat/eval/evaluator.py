# multifat/eval/evaluator.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Tuple
import numpy as np
from multifat.models.utils.tensors import as33 as _as33
import math
from multifat.models.base import CriticalPlaneMethod


def cp_rot(
    S0: np.ndarray,
    E0: np.ndarray,
    S1: np.ndarray,
    E1: np.ndarray,
    R: np.ndarray,
    *,
    check_orthonormal: bool = True,
    atol: float = 1e-8,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Express stress/strain tensors in the frame described by R.

    The change of basis is passive:
        T_rot = R.T @ T @ R
    """

    S0 = _as33("S0", S0)
    E0 = _as33("E0", E0)
    S1 = _as33("S1", S1)
    E1 = _as33("E1", E1)
    R = _as33("R", R)

    if check_orthonormal:
        ident = np.eye(3)
        gram = R.T @ R
        if not np.allclose(gram, ident, atol=atol):
            raise ValueError("R is not orthonormal within tolerance (R.T @ R != I).")

    def to_rotated(T: np.ndarray) -> np.ndarray:
        return R.T @ T @ R

    return to_rotated(S0), to_rotated(E0), to_rotated(S1), to_rotated(E1)


@dataclass(frozen=True)
class BestCP:
    ext: float  # largest damage across all candidate planes
    by_metric: float  # damage on the plane with the greatest selection metric


def best_cp_for_case(
    *,
    S0: np.ndarray,
    E0: np.ndarray,
    S1: np.ndarray,
    E1: np.ndarray,
    R_list: np.ndarray,
    method: CriticalPlaneMethod,
    params: Mapping[str, float],
    S_sin: np.ndarray | None = None,
    S_cos: np.ndarray | None = None,
    E_sin: np.ndarray | None = None,
    E_cos: np.ndarray | None = None,
    refine: bool = True,
) -> BestCP:
    """Critical-plane values for a single load case.

    Every grid plane is prepared in one go (rotation, harmonic overrides, path data).
    Methods exposing ``evaluate_on_planes`` are evaluated in a single call; the others
    fall back to one ``evaluate_on_plane`` call per plane (bit-identical results).
    With ``refine`` (the default) the grid is augmented by analytical seed planes and a
    local refinement, and the reported critical-plane damage is the largest one among the
    planes tied on the metric (``plane_search``). ``refine=False`` reproduces the earlier
    grid-only result with its sequential tie rule.
    """
    rule = shear_rule_of(method)
    plane_data = prepare_planes(
        S0=S0,
        E0=E0,
        S1=S1,
        E1=E1,
        R_list=R_list,
        S_sin=S_sin,
        S_cos=S_cos,
        E_sin=E_sin,
        E_cos=E_cos,
        tau_max=method.name in NEEDS_TAU_MAX,
        strain_ranges=method.name in NEEDS_STRAIN_RANGES,
        shear_rule=rule,
        E=params.get("E"),
        nu=params.get("nu"),
    )
    if not refine:
        damage, metric = evaluate_planes(method, plane_data, params)
        if not getattr(method, "ext_variant", True):
            from multifat.eval import plane_search

            return plane_search.select_with_ties(
                method.name,
                damage,
                metric,
                damage,
                metric,
                BestCP,
                critical_only=True,
            )
        return select_plane(method.name, damage, metric)
    case_data = dict(
        S0=S0,
        E0=E0,
        S1=S1,
        E1=E1,
        S_sin=S_sin,
        S_cos=S_cos,
        E_sin=E_sin,
        E_cos=E_cos,
        shear_rule=rule,
    )
    return refined_best(method, params, case_data, plane_data, R_list)


def refined_best(method, params, case, grid: "PlaneSet", R_list, return_normals: bool = False):
    """Refined search starting from an already prepared grid (see ``plane_search``); when
    requested, also returns the normals of the selectable planes (grid, seeds, converged
    points)."""
    from multifat.eval import plane_search

    return plane_search.refined_best(
        method,
        params,
        case,
        grid,
        R_list,
        prepare_planes,
        evaluate_planes,
        BestCP,
        return_normals=return_normals,
    )


def best_from_pool(method, params, pool: "PlaneSet") -> BestCP:
    """Critical-plane values over a fixed, already prepared pool of planes (no refinement)."""
    from multifat.eval import plane_search

    damage, metric = evaluate_planes(method, pool, params)
    return plane_search.select_with_ties(
        method.name,
        damage,
        metric,
        damage,
        metric,
        BestCP,
        critical_only=plane_search.critical_only(method),
    )


# Only criteria that require full-path quantities read this internal data. Shear peaks and
# elastic/plastic strain spans must never be reconstructed from independently synthesized
# normal/shear extrema: such combinations do not describe a physical tensor.
NEEDS_TAU_MAX = {"MGSE_YU", "MGSE_ZHU", "GSE", "GSA"}
NEEDS_STRAIN_RANGES = {"GSE", "GSA"}


@dataclass(frozen=True)
class PlaneSet:
    """Load-step tensors rotated onto every plane (P, 3, 3), plus per-plane path data
    for one case."""

    S0r: np.ndarray
    E0r: np.ndarray
    S1r: np.ndarray
    E1r: np.ndarray
    tau_max: np.ndarray | None = None
    strain_ranges: tuple[np.ndarray, ...] | None = None


def _rotate_each(T: np.ndarray, R: np.ndarray, Rt: np.ndarray) -> np.ndarray:
    """R.T @ T @ R applied to every plane; the stacked matmul is bit-identical to the
    2-D product."""
    return Rt @ T @ R


def _rowwise_dot(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Row-wise dot product of 2-vectors, bit-identical to ``u_i @ v_i`` (same BLAS
    kernel)."""
    return (u[:, None, :] @ v[:, :, None])[:, 0, 0]


def prepare_planes(
    *,
    S0: np.ndarray,
    E0: np.ndarray,
    S1: np.ndarray,
    E1: np.ndarray,
    R_list: np.ndarray,
    S_sin: np.ndarray | None = None,
    S_cos: np.ndarray | None = None,
    E_sin: np.ndarray | None = None,
    E_cos: np.ndarray | None = None,
    tau_max: bool = False,
    strain_ranges: bool = False,
    E: float | None = None,
    nu: float | None = None,
    shear_rule: str = "rss",
    atol: float = 1e-8,
) -> PlaneSet:
    """Rotate a case onto every candidate plane and apply the harmonic overrides.

    When harmonic coefficients are supplied, the shear components on each plane are
    replaced by an ellipse-aware equivalent range (``shear_rule``, see ``SHEAR_RULES``)
    and the plane-normal extrema by their harmonic amplitude; see
    ``_apply_harmonic_overrides``.
    """
    if len(R_list) == 0:
        raise ValueError("Critical-plane evaluation needs at least one plane")
    S0, E0, S1, E1 = (_as33(n, x) for n, x in (("S0", S0), ("E0", E0), ("S1", S1), ("E1", E1)))
    rots = np.asarray(R_list, dtype=float)
    if rots.ndim != 3 or rots.shape[1:] != (3, 3):
        raise ValueError(f"R_list must have shape (P, 3, 3); got {rots.shape}")
    rots_t = np.transpose(rots, (0, 2, 1))
    ident = np.eye(3)
    if not np.all(np.abs(rots_t @ rots - ident) <= atol + 1e-5 * ident):
        raise ValueError("R is not orthonormal within tolerance (R.T @ R != I).")

    S0r, S1r = _rotate_each(S0, rots, rots_t), _rotate_each(S1, rots, rots_t)
    E0r, E1r = _rotate_each(E0, rots, rots_t), _rotate_each(E1, rots, rots_t)

    S_sin_rot = S_cos_rot = E_sin_rot = E_cos_rot = None
    if S_sin is not None and S_cos is not None:
        S_sin_rot = _rotate_each(np.asarray(S_sin, dtype=float), rots, rots_t)
        S_cos_rot = _rotate_each(np.asarray(S_cos, dtype=float), rots, rots_t)
        S0r, S1r = _apply_harmonic_overrides(S0r, S1r, S_sin_rot, S_cos_rot, shear_rule)
    # Strains that are undefined (no E or nu) remain NaN on every plane, which is what
    # stress-only criteria expect.
    if (
        E_sin is not None
        and E_cos is not None
        and np.isfinite(E_sin).all()
        and np.isfinite(E_cos).all()
    ):
        E_sin_rot = _rotate_each(np.asarray(E_sin, dtype=float), rots, rots_t)
        E_cos_rot = _rotate_each(np.asarray(E_cos, dtype=float), rots, rots_t)
        E0r, E1r = _apply_harmonic_overrides(E0r, E1r, E_sin_rot, E_cos_rot, shear_rule)

    shear_peak = None
    if tau_max and S_sin_rot is not None:
        mid_stress = _rotate_each(0.5 * (np.asarray(S0) + np.asarray(S1)), rots, rots_t)
        shear_peak = _plane_shear_peaks(mid_stress, S_sin_rot, S_cos_rot)
    strain_span = None
    if strain_ranges and S_sin_rot is not None and E_sin_rot is not None:
        strain_span = _plane_strain_ranges(
            S_sin_rot, S_cos_rot, E_sin_rot, E_cos_rot, float(E), float(nu)
        )
    return PlaneSet(S0r, E0r, S1r, E1r, shear_peak, strain_span)


SHEAR_RULES = {
    # Legacy convention of this repository: root-sum-square of the shear-ellipse semi-axes.
    "rss": "2 sqrt(a^2 + b^2)",
    # The shear range on the plane over one cycle, i.e. the longest chord of the shear
    # path (2 x major semi-axis for a single-harmonic ellipse); e.g. Li et al. (2011)
    # Eq. (19), and the max-minus-min plane ranges of FS (1988), Li et al. (2021), Liu et
    # al. (2021), whose maximum over in-plane directions is the path diameter.
    "longest_chord": "2 a",
}


def shear_rule_of(method) -> str:
    rule = getattr(method, "np_shear_rule", "rss")
    if rule not in SHEAR_RULES:
        raise ValueError(f"{method.name}: unknown non-proportional shear rule {rule!r}")
    return rule


def _apply_harmonic_overrides(
    T0r, T1r, T_sin_r, T_cos_r, shear_rule: str = "rss", eps: float = 1e-14
):
    """Vectorized counterpart of ``_replace_shear_components`` +
    ``_replace_normal_component``."""
    T0r, T1r = T0r.copy(), T1r.copy()
    sin_vec = np.stack([T_sin_r[:, 0, 2], T_sin_r[:, 1, 2]], axis=1)
    cos_vec = np.stack([T_cos_r[:, 0, 2], T_cos_r[:, 1, 2]], axis=1)
    if shear_rule == "longest_chord":
        aa, bb, ab = (
            _rowwise_dot(sin_vec, sin_vec),
            _rowwise_dot(cos_vec, cos_vec),
            _rowwise_dot(sin_vec, cos_vec),
        )
        span = 2.0 * np.sqrt(np.maximum(0.0, 0.5 * (aa + bb + np.hypot(aa - bb, 2.0 * ab))))
    else:
        span = 2.0 * np.sqrt(_rowwise_dot(sin_vec, sin_vec) + _rowwise_dot(cos_vec, cos_vec))
    if not np.all(np.isfinite(span)):
        raise ValueError("Nonfinite harmonic shear range")

    zero = np.abs(span) <= eps
    len_sin = np.sqrt(_rowwise_dot(sin_vec, sin_vec))
    len_cos = np.sqrt(_rowwise_dot(cos_vec, cos_vec))
    pick_sin = len_sin > eps
    direction = np.where(pick_sin[:, None], sin_vec, cos_vec)
    dir_norm = np.where(pick_sin, len_sin, len_cos)
    active = ~zero & (dir_norm > eps)
    with np.errstate(divide="ignore", invalid="ignore"):
        halfspan = (0.5 * span)[:, None] * (direction / dir_norm[:, None])
    for col, (i, j) in enumerate(((0, 2), (1, 2))):
        mid = 0.5 * (T0r[:, i, j] + T1r[:, i, j])
        new0 = np.where(zero, mid, np.where(active, mid + halfspan[:, col], T0r[:, i, j]))
        new1 = np.where(zero, mid, np.where(active, mid - halfspan[:, col], T1r[:, i, j]))
        T0r[:, i, j] = T0r[:, j, i] = np.where(zero | active, new0, T0r[:, i, j])
        T1r[:, i, j] = T1r[:, j, i] = np.where(zero | active, new1, T1r[:, i, j])

    q_mid = 0.5 * (T0r[:, 2, 2] + T1r[:, 2, 2])
    q_sin, q_cos = T_sin_r[:, 2, 2], T_cos_r[:, 2, 2]
    q_amp = np.sqrt(q_sin * q_sin + q_cos * q_cos)
    T0r[:, 2, 2] = q_mid + q_amp
    T1r[:, 2, 2] = q_mid - q_amp
    return T0r, T1r


def _plane_shear_peaks(mid, sn, cs):
    """Vectorized counterpart of ``plane_history.shear_maximum`` (720 time samples)."""
    from multifat.models.utils.plane_history import _cycle

    sin_t, cos_t = _cycle()
    traj = mid[:, :2, 2, None] + sn[:, :2, 2, None] * sin_t + cs[:, :2, 2, None] * cos_t
    return np.sqrt(np.max(np.sum(traj * traj, axis=1), axis=1))


def _plane_strain_ranges(S_sin, S_cos, E_sin, E_cos, E, nu):
    """Vectorized counterpart of ``plane_history.split_strain_ranges``."""

    def elastic(s):
        tr = np.trace(s, axis1=1, axis2=2)
        return ((1 + nu) * s - (nu * tr)[:, None, None] * np.eye(3)) / E

    def spans(sin, cos):
        return (
            4 * np.sqrt(np.sum(sin[:, :2, 2] ** 2 + cos[:, :2, 2] ** 2, axis=1)),
            2 * np.hypot(sin[:, 2, 2], cos[:, 2, 2]),
        )

    e_sin, e_cos = elastic(S_sin), elastic(S_cos)
    gamma_el, normal_el = spans(e_sin, e_cos)
    gamma_pl, normal_pl = spans(E_sin - e_sin, E_cos - e_cos)
    return gamma_el, gamma_pl, normal_el, normal_pl


def evaluate_planes(method: CriticalPlaneMethod, planes: PlaneSet, params: Mapping[str, float]):
    """Per-plane damage and selection-metric arrays for an already prepared case."""
    batch_fn = getattr(method, "evaluate_on_planes", None)
    if batch_fn is not None:
        damage, metric = batch_fn(
            S0r=planes.S0r,
            E0r=planes.E0r,
            S1r=planes.S1r,
            E1r=planes.E1r,
            params=params,
            tau_max=planes.tau_max,
            strain_ranges=planes.strain_ranges,
        )
        return np.asarray(damage, dtype=float), np.asarray(metric, dtype=float)
    count = planes.S0r.shape[0]
    damage, metric = np.empty(count), np.empty(count)
    for k in range(count):
        local_params = dict(params)
        if planes.tau_max is not None:
            local_params["_tau_max"] = float(planes.tau_max[k])
        if planes.strain_ranges is not None:
            local_params["_strain_ranges"] = tuple(float(x[k]) for x in planes.strain_ranges)
        res = method.evaluate_on_plane(
            S0r=planes.S0r[k],
            E0r=planes.E0r[k],
            S1r=planes.S1r[k],
            E1r=planes.E1r[k],
            params=local_params,
        )
        damage[k], metric[k] = res.damage, res.metric
    return damage, metric


def select_plane(name: str, damage: np.ndarray, metric: np.ndarray) -> BestCP:
    """Largest damage, together with the damage on the plane with the largest metric
    (ties resolved toward the larger damage).

    The scan is sequential on purpose: the relative-tolerance tie rule depends on order.
    """
    if not (np.all(np.isfinite(damage)) and np.all(np.isfinite(metric))):
        raise ValueError(f"{name}: nonfinite plane damage or selection metric")
    top_metric = -np.inf
    metric_plane_damage = np.nan
    for plane_damage, plane_metric in zip(damage.tolist(), metric.tolist()):
        is_tie = math.isclose(plane_metric, top_metric, rel_tol=1e-10, abs_tol=1e-14)
        if (plane_metric > top_metric and not is_tie) or (
            is_tie and plane_damage > metric_plane_damage
        ):
            top_metric = plane_metric
            metric_plane_damage = plane_damage
    return BestCP(ext=float(np.max(damage)), by_metric=float(metric_plane_damage))


def _harmonic_equivalent_shear_range(
    T_sin_r: np.ndarray,
    T_cos_r: np.ndarray,
    *,
    a: Tuple[int, int] = (0, 2),
    b: Tuple[int, int] = (1, 2),
) -> float:
    """Equivalent shear RANGE on the candidate plane, rebuilt from single-harmonic
    coefficients.

    Once rotated, the shear traction on the plane has two components (local xz and yz).
    Under out-of-phase loading these trace an ellipse over one cycle. For single-harmonic
    loading that ellipse reads:

        τ(t) = v_sin*sin(ωt) + v_cos*cos(ωt)

    with v_sin and v_cos 2D vectors. The semi-axis lengths are the square roots of the
    eigenvalues of M M^T, where M = [v_sin v_cos]. The requested shear amplitude is the
    vector sum of the major and minor semi-axes:

        τ_a,eq = sqrt(a^2 + b^2) = sqrt(||v_sin||^2 + ||v_cos||^2)

    This routine returns the matching RANGE:

        Δτ_eq = 2 * τ_a,eq
    """
    T_sin_r = np.asarray(T_sin_r, dtype=float)
    T_cos_r = np.asarray(T_cos_r, dtype=float)

    v_sin = np.array([float(T_sin_r[a]), float(T_sin_r[b])], dtype=float)
    v_cos = np.array([float(T_cos_r[a]), float(T_cos_r[b])], dtype=float)

    amp = math.sqrt(float(v_sin @ v_sin + v_cos @ v_cos))
    return float(2.0 * amp)


def _replace_shear_components(
    T0r: np.ndarray,
    T1r: np.ndarray,
    *,
    delta_eq: float,
    T_sin_r: np.ndarray,
    T_cos_r: np.ndarray,
    a: Tuple[int, int] = (0, 2),
    b: Tuple[int, int] = (1, 2),
    eps: float = 1e-14,
) -> Tuple[np.ndarray, np.ndarray]:
    """Replace the (xz,yz) components so that the range of their 2-norm equals delta_eq.

    This keeps the two-load-step interface of the CP methods intact.
    """
    T0r = np.asarray(T0r, dtype=float).copy()
    T1r = np.asarray(T1r, dtype=float).copy()

    if not np.isfinite(delta_eq):
        raise ValueError("Nonfinite harmonic shear range")
    if abs(delta_eq) <= eps:
        # A vanishing equivalent range can go together with nonzero component-wise endpoints
        # (as with cancelling antiphase loads). The mean is encoded exactly.
        for idx in (a, b):
            mid = 0.5 * (T0r[idx] + T1r[idx])
            T0r[idx] = T1r[idx] = mid
            T0r[idx[::-1]] = T1r[idx[::-1]] = mid
        return T0r, T1r

    v_sin = np.array([float(T_sin_r[a]), float(T_sin_r[b])], dtype=float)
    v_cos = np.array([float(T_cos_r[a]), float(T_cos_r[b])], dtype=float)

    # Choose a stable direction for the shear-range vector.
    w = v_sin
    nw = float(np.linalg.norm(w))
    if nw <= eps:
        w = v_cos
        nw = float(np.linalg.norm(w))
    if nw <= eps:
        # the shear is essentially zero
        return T0r, T1r

    u = w / nw
    half = 0.5 * float(delta_eq) * u

    # Keep the mean shear level already carried by T0r/T1r.
    m_a = 0.5 * float(T0r[a] + T1r[a])
    m_b = 0.5 * float(T0r[b] + T1r[b])

    T0r[a] = m_a + half[0]
    T1r[a] = m_a - half[0]
    T0r[b] = m_b + half[1]
    T1r[b] = m_b - half[1]

    # mirror into the lower triangle
    T0r[a[1], a[0]] = T0r[a]
    T1r[a[1], a[0]] = T1r[a]
    T0r[b[1], b[0]] = T0r[b]
    T1r[b[1], b[0]] = T1r[b]

    return T0r, T1r


def _replace_normal_component(
    T0r: np.ndarray,
    T1r: np.ndarray,
    *,
    T_sin_r: np.ndarray,
    T_cos_r: np.ndarray,
    idx: tuple[int, int] = (2, 2),
) -> Tuple[np.ndarray, np.ndarray]:
    """Replace the normal (scalar) component on the plane using the harmonic extrema.

    For any scalar quantity:
        q(t) = q_mean + q_sin*sin(ωt) + q_cos*cos(ωt)
    the amplitude is:
        q_a = sqrt(q_sin^2 + q_cos^2)
    and the extrema are q_mean ± q_a.

    Here the plane-normal component is taken as T[idx] (zz in the plane frame by default).
    """
    T0r = np.asarray(T0r, dtype=float).copy()
    T1r = np.asarray(T1r, dtype=float).copy()

    i, j = idx
    q_mid = 0.5 * float(T0r[i, j] + T1r[i, j])
    q_sin = float(np.asarray(T_sin_r, dtype=float)[i, j])
    q_cos = float(np.asarray(T_cos_r, dtype=float)[i, j])
    q_amp = math.sqrt(q_sin * q_sin + q_cos * q_cos)

    T0r[i, j] = q_mid + q_amp
    T1r[i, j] = q_mid - q_amp
    return T0r, T1r
