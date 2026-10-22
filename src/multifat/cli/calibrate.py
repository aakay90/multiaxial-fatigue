# calibrate_cp_params.py
"""Calibration tool for critical-plane and model constants.

Historically this module calibrated:
- k_FS for the Fatemi–Socie (FS) criterion
- k_FI for the Findley (FIN) criterion

It was later extended to cover further material constants:
- L_LI (Li 2021 CP method)
- k_MGSE (MGSE_ZHU CP method)
- a_MSWT (MSWT CP method)
ZHU_EDP calibration was dropped after the numerical audit; see docs/method-audit.md.

Project layout (v6)
-------------------
- Experimental data importer: multifat.imp.experimental_data
- Plane sampling: multifat.planes.sampling (dcmesh_xyz, gentang)
- Critical-plane evaluation: multifat.eval.evaluator.best_cp_for_case
- CP methods: multifat.models.cp_methods

Calibration target
------------------
For every candidate parameter value (or set of values), evaluate the model scalar
(CP/DP) on each selected case, fit a power law in log-space:

    CP = A * N^b

and minimise the fatigue scatter, defined as the STD of the residuals in ln(N),
through the project helper multifat.eval.fitting.fit_power_law_with_survival_std.

Datasets
--------
- FS, FIN, LI, MGSE_ZHU, MSWT:
    uniaxial axial + uniaxial torsion points are used (target R=-1, with fallbacks).

Notes
-----
- The workbook is never written back to Excel; the script prints the calibrated
  constants and returns a nested dictionary for programmatic use.
- SciPy is not used: a grid-refinement search is implemented instead.
"""

from __future__ import annotations

import traceback
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from multifat.imp import experimental_data as exp
from multifat.planes.sampling import dcmesh_xyz, gentang
from multifat.eval.evaluator import (
    NEEDS_TAU_MAX,
    PlaneSet,
    best_from_pool,
    prepare_planes,
    refined_best,
    shear_rule_of,
)
from multifat.eval.findley_calibration import (
    amplitude_identity,
    findley_method,
    require_stress_harmonics,
)
from multifat.eval.fitting import fit_power_law_with_survival_std
from multifat.eval.plane_search import frames_from_normals

from multifat.models.cp_methods.fs import FatemiSocie
from multifat.models.cp_methods.li import LI
from multifat.models.cp_methods.mgse_zhu import MGSE_Zhu
from multifat.models.cp_methods.mswt import MSWT


# -----------------------------
# Lightweight minimisers (SciPy-free)
# -----------------------------


class CalibrationInfeasible(ValueError):
    """A calibration search found no finite objective anywhere in its bounds.

    Raised below the per-block fit, which fills ``block``; ``parameter``, ``bounds`` and the
    one-line ``diagnostic`` describe the search that failed. The message keeps the historical
    "No finite calibration objective" prefix and appends the diagnostic.
    """

    def __init__(
        self,
        message: str,
        *,
        block: Optional[str] = None,
        parameter: Optional[str] = None,
        bounds: Optional[Tuple[float, float]] = None,
        diagnostic: str = "",
    ) -> None:
        super().__init__(message)
        self.block = block
        self.parameter = parameter
        self.bounds = bounds
        self.diagnostic = diagnostic


def minimize_1d_grid_refine(
    objective: Callable[[float], float],
    bounds: Tuple[float, float],
    *,
    n_grid: int = 41,
    n_refine: int = 6,
    parameter: Optional[str] = None,
    diagnose: Optional[Callable[[np.ndarray], str]] = None,
) -> Tuple[float, float]:
    """Search [lo, hi] for the minimum of objective(x) by iterated grid refinement."""
    lo, hi = float(bounds[0]), float(bounds[1])
    if n_grid < 2 or n_refine < 1:
        raise ValueError("Calibration requires n_grid >= 2 and n_refine >= 1")
    if not (hi > lo):
        raise ValueError("bounds must satisfy hi > lo")

    x_best = np.nan
    f_best = np.inf

    for _ in range(int(n_refine)):
        xs = np.linspace(lo, hi, int(n_grid))
        fs = np.array([objective(float(x)) for x in xs], dtype=float)

        if not np.any(np.isfinite(fs)):
            diagnostic = "" if diagnose is None else diagnose(xs)
            message = "No finite calibration objective: check design data and master-curve slope"
            if diagnostic:
                message = f"{message}; {diagnostic}"
            raise CalibrationInfeasible(
                message,
                parameter=parameter,
                bounds=(float(bounds[0]), float(bounds[1])),
                diagnostic=diagnostic,
            )
        j = int(np.argmin(np.where(np.isfinite(fs), fs, np.inf)))
        x_best = float(xs[j])
        f_best = float(fs[j])

        step = (hi - lo) / max(1, (len(xs) - 1))
        lo = max(bounds[0], x_best - 2.0 * step)
        hi = min(bounds[1], x_best + 2.0 * step)

        if hi - lo < 1e-10:
            break

    return x_best, f_best


def minimize_1d_smallest(
    objective: Callable[[float], float],
    bounds: Tuple[float, float],
    *,
    n_grid: int = 41,
    n_refine: int = 6,
    rtol: float = 1e-6,
    parameter: Optional[str] = None,
    diagnose: Optional[Callable[[np.ndarray], str]] = None,
) -> Tuple[float, float, Tuple[float, float]]:
    """Like minimize_1d_grid_refine, but a flat minimum is reported at its lowest point.

    A full-interval grid scan flags every point within rtol of the refined minimum; if more
    than one grid point lies on that plateau, its lower edge is found by bisection. The result
    is (x, f(x), (plateau_lo, plateau_hi)), with the plateau collapsing to (x, x) when the
    minimum is isolated (finding F4: on uniaxial + torsion data, k_MGSE and a_MSWT minimise on
    a plateau where the normal term dominates both loadings).
    """
    x_best, f_best = minimize_1d_grid_refine(
        objective,
        bounds,
        n_grid=n_grid,
        n_refine=n_refine,
        parameter=parameter,
        diagnose=diagnose,
    )
    thr = f_best * (1.0 + rtol) + 1e-12
    xs = np.linspace(float(bounds[0]), float(bounds[1]), int(n_grid))
    fs = np.array([objective(float(x)) for x in xs], dtype=float)
    flat = np.flatnonzero(np.isfinite(fs) & (fs <= thr))
    if flat.size < 2:
        return x_best, f_best, (x_best, x_best)
    j = int(flat[0])
    lo_edge = float(xs[j])
    if j > 0:
        a, b = float(xs[j - 1]), float(xs[j])
        for _ in range(40):
            m = 0.5 * (a + b)
            if objective(m) <= thr:
                b = m
            else:
                a = m
        lo_edge = b
    return lo_edge, float(objective(lo_edge)), (lo_edge, float(xs[int(flat[-1])]))


def _is_negligible(side_max: float, main_max: float, *, atol: float, rtol: float) -> bool:
    return side_max <= (rtol * abs(main_max) + atol)


def _case_extrema_tensors(case: Dict[str, Any], node: int = 1) -> Tuple[np.ndarray, np.ndarray]:
    S0 = np.asarray(case[node][1]["stress"], dtype=float)
    S1 = np.asarray(case[node][2]["stress"], dtype=float)
    return S0, S1


def _is_axial_tension_case(
    case: Dict[str, Any],
    *,
    node: int = 1,
    r_target: Optional[float] = -1.0,
    rtol_R: float = 0.02,
    atol_R: float = 1e-6,
    rtol_uniax: float = 1e-3,
    atol_uniax: float = 1e-6,
) -> Tuple[bool, float]:
    S0, S1 = _case_extrema_tensors(case, node=node)

    s0 = float(S0[1, 1])
    s1 = float(S1[1, 1])
    smax = max(s0, s1)
    smin = min(s0, s1)

    if abs(smax) < atol_R:
        return False, np.nan

    R = smin / smax

    if smax <= 0.0:
        return False, R

    S_rest = S0.copy()
    S_rest[1, 1] = 0.0
    rest_max = float(np.max(np.abs(S_rest)))
    if not _is_negligible(rest_max, smax, atol=atol_uniax, rtol=rtol_uniax):
        return False, R

    if r_target is not None:
        if not np.isclose(R, r_target, rtol=rtol_R, atol=atol_R):
            return False, R

    return True, R


def _is_axial_torsion_case(
    case: Dict[str, Any],
    *,
    node: int = 1,
    r_target: Optional[float] = -1.0,
    rtol_R: float = 0.02,
    atol_R: float = 1e-6,
    rtol_uniax: float = 1e-3,
    atol_uniax: float = 1e-6,
) -> Tuple[bool, float]:
    S0, S1 = _case_extrema_tensors(case, node=node)

    t0 = float(S0[0, 1])
    t1 = float(S1[0, 1])
    tmax = max(t0, t1)
    tmin = min(t0, t1)

    if abs(tmax) < atol_R:
        return False, np.nan

    R = tmin / tmax

    if tmax <= 0.0:
        return False, R

    S_rest = S0.copy()
    S_rest[0, 1] = 0.0
    S_rest[1, 0] = 0.0
    rest_max = float(np.max(np.abs(S_rest)))
    if not _is_negligible(rest_max, tmax, atol=atol_uniax, rtol=rtol_uniax):
        return False, R

    if r_target is not None:
        if not np.isclose(R, r_target, rtol=rtol_R, atol=atol_R):
            return False, R

    return True, R


def _pick_cases_with_relaxation(
    cases: Dict[int, Dict[str, Any]],
    selector: Callable[..., Tuple[bool, float]],
    *,
    selector_kwargs: Dict[str, Any],
    fallback_rtol_list: Sequence[float] = (0.02, 0.05, 0.1, 0.2, 0.5),
    allow_any_R_fallback: bool = True,
    name_for_warnings: str = "dataset",
) -> Tuple[List[int], Dict[str, Any]]:
    info: Dict[str, Any] = {
        "fallback_used": False,
        "rtol_R_used": None,
        "any_R_used": False,
    }

    selected: List[int] = []
    for cid, case in cases.items():
        ok, _R = selector(case, **selector_kwargs)
        if ok:
            selected.append(int(cid))

    if selected:
        info["rtol_R_used"] = selector_kwargs.get("rtol_R", None)
        return selected, info

    relaxed_kwargs = dict(selector_kwargs)
    for rtol_R in fallback_rtol_list:
        relaxed_kwargs["rtol_R"] = float(rtol_R)
        selected = []
        for cid, case in cases.items():
            ok, _R = selector(case, **relaxed_kwargs)
            if ok:
                selected.append(int(cid))
        if selected:
            warnings.warn(
                f"[{name_for_warnings}] No points found for target R with initial tolerance; using relaxed rtol_R={rtol_R}.",
                RuntimeWarning,
            )
            info.update({"fallback_used": True, "rtol_R_used": rtol_R})
            return selected, info

    if allow_any_R_fallback:
        anyR_kwargs = dict(selector_kwargs)
        anyR_kwargs["r_target"] = None
        selected = []
        for cid, case in cases.items():
            ok, _R = selector(case, **anyR_kwargs)
            if ok:
                selected.append(int(cid))
        if selected:
            warnings.warn(
                f"[{name_for_warnings}] No points found for target R even after relaxing; falling back to ANY R.",
                RuntimeWarning,
            )
            info.update({"fallback_used": True, "any_R_used": True})
            return selected, info

    warnings.warn(f"[{name_for_warnings}] No usable points found.", RuntimeWarning)
    info.update({"fallback_used": True})
    return [], info


# -----------------------------
# Calibration machinery
# -----------------------------


@dataclass(frozen=True)
class CalibrationResult1D:
    param_name: str
    p_opt: float
    scatter_STD: float
    fit: Dict[str, float]
    series: Dict[str, np.ndarray]
    plateau: Tuple[float, float] = (np.nan, np.nan)


def _make_plane_frames(*, n_theta: int = 20, n_phi: int = 40) -> np.ndarray:
    xyz = dcmesh_xyz(a1=np.pi, n1=int(n_theta), a2=2 * np.pi, n2=int(n_phi))
    xyz = np.unique(np.round(xyz, 12), axis=0)
    R = gentang(xyz, return_matrices=True)
    return np.asarray(R)


def _build_R_list(*, n1: int = 20, n2: int = 40) -> np.ndarray:
    return _make_plane_frames(n_theta=n1, n_phi=n2)


def _fit_single_param(
    *,
    cases_data: List[Dict[str, Any]],
    damage_fn: Callable[[Dict[str, Any], float], float],
    bounds: Tuple[float, float],
    stdnum: float,
    n_grid: int,
    n_refine: int,
    param_name: str,
    block: str,
) -> CalibrationResult1D:
    N = np.array([c["Nf"] for c in cases_data], dtype=float)

    def objective(p: float) -> float:
        DP = np.array([damage_fn(c, float(p)) for c in cases_data], dtype=float)
        fit = fit_power_law_with_survival_std(N, DP, stdnum=stdnum)
        return float(fit["STD"]) if np.isfinite(fit["STD"]) else np.inf

    def diagnose(xs: np.ndarray) -> str:
        # Only reached when no grid point has a finite objective (evaluated once, not per fit).
        slopes = []
        for value in np.asarray(xs, dtype=float):
            DP = np.array([damage_fn(c, float(value)) for c in cases_data], dtype=float)
            fit = fit_power_law_with_survival_std(N, DP, stdnum=stdnum)
            if np.isfinite(fit["b"]):
                slopes.append(float(fit["b"]))
        span = f"[{xs[0]:g}, {xs[-1]:g}]"
        if not slopes:
            return f"no case pair gives a finite slope for any {param_name} in {span}"
        low, high = min(slopes), max(slopes)
        if low > 0:
            trend = "DP increases with life"
        elif low >= 0:
            trend = "DP does not decrease with life"
        elif high < 0:
            trend = "DP decreases with life but the objective stays undefined"
        else:
            trend = "the DP slope changes sign"
        return f"{trend} for all {param_name} in {span} (slope {low:+.2f} to {high:+.2f})"

    try:
        p_best, std_best, plateau = minimize_1d_smallest(
            objective,
            bounds,
            n_grid=n_grid,
            n_refine=n_refine,
            parameter=param_name,
            diagnose=diagnose,
        )
    except CalibrationInfeasible as exc:
        exc.block = block
        raise

    DP_best = np.array([damage_fn(c, float(p_best)) for c in cases_data], dtype=float)
    fit = fit_power_law_with_survival_std(N, DP_best, stdnum=stdnum)

    return CalibrationResult1D(
        param_name=str(param_name),
        p_opt=float(p_best),
        scatter_STD=float(std_best),
        fit=dict(fit),
        series={"N": N, "DP": DP_best},
        plateau=(float(plateau[0]), float(plateau[1])),
    )


# -----------------------------
# Public API
# -----------------------------


def calibrate_material_params(
    *,
    data: Dict[str, Any],
    material_name: str,
    R_list: Optional[np.ndarray] = None,
    stdnum: float = 2.0,
    node: int = 1,
    # selection tolerances
    r_target: float = -1.0,
    rtol_R_init: float = 0.02,
    rtol_uniax: float = 1e-3,
    # speed
    plane_stride: int = 1,
    # search tuning
    n_grid_1d: int = 41,
    n_refine_1d: int = 6,
    # bounds
    # constants to calibrate (names from the CALIBRATED block); None = all
    blocks: Optional[Iterable[str]] = None,
    bounds_k_FS: Tuple[float, float] = (0.0, 3.0),
    bounds_k_FI: Tuple[float, float] = (0.0, 3.0),
    bounds_L_LI: Tuple[float, float] = (0.0, 5.0),
    bounds_k_MGSE: Tuple[float, float] = (0.0, 5.0),
    bounds_a_MSWT: Tuple[float, float] = (0.0, 1.0),
    shear_amplitude_algorithm: str = "method_default",
) -> Dict[str, Any]:
    """Calibrate FS/FIN and the remaining constants for a single material.

    ``shear_amplitude_algorithm`` (method_default, mce_harmonic, rss, mcc_harmonic) controls
    the shear amplitude used by the Findley criterion during the k_FI calibration only
    (A. Chiocca, 36ff0a1); the default preserves the established path. Production runs
    evaluate Findley with MCE.
    """

    if material_name not in data:
        raise KeyError(f"Material '{material_name}' not found. Available: {list(data.keys())}")

    amplitude = amplitude_identity(shear_amplitude_algorithm)  # validates the selection

    if R_list is None:
        R_list = _make_plane_frames()

    if plane_stride is not None and int(plane_stride) > 1:
        R_use = np.asarray(R_list)[:: int(plane_stride)]
    else:
        R_use = np.asarray(R_list)

    material = data[material_name]
    material_props = material.get("material", {})
    cases = material.get("cases", {})

    sigma_y = material_props.get("Yield_strength_MPa", None)
    if sigma_y is not None and not np.isfinite(sigma_y):
        sigma_y = None
    if sigma_y is None:
        warnings.warn(
            f"[{material_name}] no yield strength: k_FS is not calibrated",
            RuntimeWarning,
        )

    selector_kwargs = dict(
        node=node,
        r_target=r_target,
        rtol_R=rtol_R_init,
        atol_R=1e-6,
        rtol_uniax=rtol_uniax,
        atol_uniax=1e-6,
    )

    tension_ids, tension_info = _pick_cases_with_relaxation(
        cases,
        _is_axial_tension_case,
        selector_kwargs=selector_kwargs,
        name_for_warnings=f"{material_name}/uniaxial_tension",
    )
    torsion_ids, torsion_info = _pick_cases_with_relaxation(
        cases,
        _is_axial_torsion_case,
        selector_kwargs=selector_kwargs,
        name_for_warnings=f"{material_name}/uniaxial_torsion",
    )

    if len(tension_ids) == 0 or len(torsion_ids) == 0:
        warnings.warn(
            f"[{material_name}] Uniaxial dataset may be incomplete: tension={len(tension_ids)} torsion={len(torsion_ids)}.",
            RuntimeWarning,
        )

    combined_ids = tension_ids + torsion_ids
    requested_blocks = set(CALIBRATED) if blocks is None else set(blocks)

    uniax_cases: List[Dict[str, Any]] = []
    for cid in combined_ids:
        c = cases[int(cid)]
        Nf = float(c["meta"]["Nf_cycles"])
        if shear_amplitude_algorithm != "method_default" and "FI" in requested_blocks:
            require_stress_harmonics(c, material_name, int(cid))
        S0, E0, S1, E1, H = exp.extract_tensor(
            data, material_name, int(cid), node=node, include_harmonics=True
        )
        uniax_cases.append(
            {
                "case_id": int(cid),
                "Nf": Nf,
                "S0": S0,
                "E0": E0,
                "S1": S1,
                "E1": E1,
                "H": H,
            }
        )

    if len(uniax_cases) < 2:
        raise RuntimeError(f"[{material_name}] Not enough uniaxial cases to calibrate (need >= 2).")

    # ------------------
    # Build the criteria
    # ------------------
    fs_method = FatemiSocie()
    fin_method = findley_method(shear_amplitude_algorithm)
    li_method = LI()
    mgse_method = MGSE_Zhu()
    mswt_method = MSWT()

    # The critical plane depends on the case and, for some criteria, on the parameter
    # being calibrated. For every case/method pair a plane pool is assembled once from
    # refined searches at a few parameter values spanning the bounds (grid, analytical
    # seeds and converged points); each subsequent objective evaluation only re-scores
    # that pool. Criteria driven by a parameter-independent metric (FS: dgamma, LI: shear
    # term) reproduce the refined result exactly; maximum-damage criteria (FIN,
    # MGSE_ZHU, MSWT) carry only a second-order error between pool planes.
    param_sweep = {
        "FS": ("k_FS", bounds_k_FS),
        "FIN": ("k_FI", bounds_k_FI),
        "LI": ("L_LI", bounds_L_LI),
        "MGSE_ZHU": ("k_MGSE", bounds_k_MGSE),
        "MSWT": ("a_MSWT", bounds_a_MSWT),
    }
    plane_pool_cache: Dict[Tuple[int, str], Tuple[Dict[str, Any], PlaneSet]] = {}

    def _pick_best_plane(case_dict: Dict[str, Any], method, params: Dict[str, float]):
        key = (id(case_dict), method.name)
        if key not in plane_pool_cache:
            H = case_dict["H"]
            tensors = dict(
                S0=case_dict["S0"],
                E0=case_dict["E0"],
                S1=case_dict["S1"],
                E1=case_dict["E1"],
                S_sin=H.get("S_sin"),
                S_cos=H.get("S_cos"),
                E_sin=H.get("E_sin"),
                E_cos=H.get("E_cos"),
            )
            flags = dict(tau_max=method.name in NEEDS_TAU_MAX, shear_rule=shear_rule_of(method))
            grid = prepare_planes(**tensors, R_list=R_use, **flags)
            name, (lo, hi) = param_sweep[method.name]
            normals = []
            for value in np.linspace(lo, hi, 5):
                _, n = refined_best(
                    method,
                    {**params, name: float(value)},
                    {**tensors, "shear_rule": flags["shear_rule"]},
                    grid,
                    R_use,
                    return_normals=True,
                )
                normals.append(n)
            pool = prepare_planes(
                **tensors, R_list=frames_from_normals(np.concatenate(normals)), **flags
            )
            plane_pool_cache[key] = (case_dict, pool)
        return best_from_pool(method, params, plane_pool_cache[key][1])

    # ------------------
    # 1D CP parameter evaluations
    # ------------------
    def fs_eval(case_dict: Dict[str, Any], k: float) -> float:
        best = _pick_best_plane(case_dict, fs_method, {"k_FS": float(k), "Sy": float(sigma_y)})
        return float(best.by_metric)  # plane maximizing Δγ

    def fin_eval(case_dict: Dict[str, Any], k: float) -> float:
        best = _pick_best_plane(case_dict, fin_method, {"k_FI": float(k)})
        return float(best.ext)  # maximize Findley scalar

    def li_eval(case_dict: Dict[str, Any], L: float) -> float:
        best = _pick_best_plane(case_dict, li_method, {"L_LI": float(L)})
        # Li's criterion is shear-driven; its scalar is built to select that plane,
        # hence by_metric is the quantity to use here.
        return float(best.by_metric)

    def mgse_eval(case_dict: Dict[str, Any], k: float) -> float:
        best = _pick_best_plane(case_dict, mgse_method, {"k_MGSE": float(k)})
        return float(best.ext)

    def mswt_eval(case_dict: Dict[str, Any], a: float) -> float:
        best = _pick_best_plane(case_dict, mswt_method, {"a_MSWT": float(a)})
        return float(best.ext)

    # ------------------
    # Fit the 1D parameters on the uniaxial dataset
    # ------------------
    FS_cal = FI_cal = LI_cal = MGSE_cal = MSWT_cal = None
    if sigma_y is not None and "FS" in requested_blocks:
        FS_cal = _fit_single_param(
            cases_data=uniax_cases,
            damage_fn=fs_eval,
            bounds=bounds_k_FS,
            stdnum=stdnum,
            n_grid=n_grid_1d,
            n_refine=n_refine_1d,
            param_name="k_FS",
            block="FS",
        )
    if "FI" in requested_blocks:
        FI_cal = _fit_single_param(
            cases_data=uniax_cases,
            damage_fn=fin_eval,
            bounds=bounds_k_FI,
            stdnum=stdnum,
            n_grid=n_grid_1d,
            n_refine=n_refine_1d,
            param_name="k_FI",
            block="FI",
        )
    if "LI" in requested_blocks:
        LI_cal = _fit_single_param(
            cases_data=uniax_cases,
            damage_fn=li_eval,
            bounds=bounds_L_LI,
            stdnum=stdnum,
            n_grid=n_grid_1d,
            n_refine=n_refine_1d,
            param_name="L_LI",
            block="LI",
        )
    if "MGSE_ZHU" in requested_blocks:
        MGSE_cal = _fit_single_param(
            cases_data=uniax_cases,
            damage_fn=mgse_eval,
            bounds=bounds_k_MGSE,
            stdnum=stdnum,
            n_grid=n_grid_1d,
            n_refine=n_refine_1d,
            param_name="k_MGSE",
            block="MGSE_ZHU",
        )
    if "MSWT" in requested_blocks:
        MSWT_cal = _fit_single_param(
            cases_data=uniax_cases,
            damage_fn=mswt_eval,
            bounds=bounds_a_MSWT,
            stdnum=stdnum,
            n_grid=n_grid_1d,
            n_refine=n_refine_1d,
            param_name="a_MSWT",
            block="MSWT",
        )

    # ------------------
    # Assemble the result
    # ------------------
    out: Dict[str, Any] = {
        "material": material_name,
        "selection": {
            "target_R": float(r_target),
            "tension_case_ids": tension_ids,
            "torsion_case_ids": torsion_ids,
            "tension_info": tension_info,
            "torsion_info": torsion_info,
            "n_uniax": int(len(uniax_cases)),
        },
        "FS": (
            None
            if FS_cal is None
            else {
                "k_FS": FS_cal.p_opt,
                "scatter_STD": FS_cal.scatter_STD,
                "fit": FS_cal.fit,
                "plateau": FS_cal.plateau,
            }
        ),
        "FI": (
            None
            if FI_cal is None
            else {
                "k_FI": FI_cal.p_opt,
                "scatter_STD": FI_cal.scatter_STD,
                "fit": FI_cal.fit,
                "plateau": FI_cal.plateau,
            }
        ),
        "LI": (
            None
            if LI_cal is None
            else {
                "L_LI": LI_cal.p_opt,
                "scatter_STD": LI_cal.scatter_STD,
                "fit": LI_cal.fit,
                "plateau": LI_cal.plateau,
            }
        ),
        "MGSE_ZHU": (
            None
            if MGSE_cal is None
            else {
                "k_MGSE": MGSE_cal.p_opt,
                "scatter_STD": MGSE_cal.scatter_STD,
                "fit": MGSE_cal.fit,
                "plateau": MGSE_cal.plateau,
            }
        ),
        "MSWT": (
            None
            if MSWT_cal is None
            else {
                "a_MSWT": MSWT_cal.p_opt,
                "scatter_STD": MSWT_cal.scatter_STD,
                "fit": MSWT_cal.fit,
                "plateau": MSWT_cal.plateau,
            }
        ),
    }

    if "FI" in requested_blocks:
        out["amplitude_settings"] = {"FIN": amplitude}
    return out


CALIBRATED = {
    "FS": "k_FS",
    "FI": "k_FI",
    "LI": "L_LI",
    "MGSE_ZHU": "k_MGSE",
    "MSWT": "a_MSWT",
}


def _not_applicable_reason(block: Dict[str, Any]) -> str:
    """Why plane constants are not calibrated on this workbook: no plain failure rows."""
    if block.get("runouts"):
        return "fatigue-limit dataset: constants from the R = -1 limits"
    return "notched-only dataset: no plain failures to calibrate on"


def calibrate_workbook(
    fp: str | Path,
    *,
    planes: bool = True,
    constants: bool = True,
    stdnum: float = 2.0,
    plane_stride: int = 1,
) -> dict:
    """Calibrate one workbook's constants; JSON-ready, and the workbook is left untouched.

    planes: critical-plane constants k_FS, k_FI, L_LI, k_MGSE, a_MSWT (scatter minimisation
    over the uniaxial and torsion tests). constants: Basquin curves fitted on the fully
    reversed tension and torsion tests (only identifiable curves) plus uniform-material-law
    plastic strain-life terms (estimates). The returned dict is {"material", "params",
    "source": {name: how}, "design_case_ids": {param: [case ids used]}, ...}; "error"
    collects whatever failed. "status" is "calibrated", "not_applicable" (no plain failures),
    "infeasible" (no finite objective, or no usable uniaxial subset) or "error" (unexpected
    exception), with the one-line "reason"; an infeasible plane fit also records "infeasible"
    (block, parameter, diagnostic).
    """
    from multifat.eval.material_fits import basquin_fill, strain_life_fill, zhu_k_mgse

    fp = Path(fp)
    data = exp.load_material_workbook(fp)
    material = exp.material_id(fp.stem)
    requested = planes or constants
    out: Dict[str, Any] = {
        "material": material,
        "params": {},
        "source": {},
        "errors": [],
        "status": "calibrated" if requested else "not_applicable",
        "reason": "" if requested else "nothing requested: planes and constants both off",
    }
    out["design_case_ids"] = {}
    if constants:
        bf = basquin_fill(data, material)
        out["basquin"] = bf["fits"]
        for name, value in bf["params"].items():
            out["params"][name] = value
            out["source"][name] = "Basquin fit on the workbook's R = -1 tests"
        out["unidentified"] = {}
        for key, names in (
            ("tension", ("sigma_f", "b_fat")),
            ("torsion", ("tau_f", "b0")),
        ):
            for name in names:
                if key in bf["design_case_ids"]:
                    out["design_case_ids"][name] = bf["design_case_ids"][key]
                else:
                    reason = bf["fits"][key]["reason"]
                    out["unidentified"][name] = f"{key} R = -1 Basquin fit: {reason}"
        props = data[material]["material"]
        has_elastic = props["E_MPa"] is not None and props["nu"] is not None
        if has_elastic and all(k in bf["params"] for k in ("sigma_f", "b_fat", "tau_f", "b0")):
            coeffs = bf["params"]
            mgse_k = zhu_k_mgse(
                coeffs["sigma_f"],
                coeffs["b_fat"],
                coeffs["tau_f"],
                coeffs["b0"],
                props["E_MPa"],
                props["nu"],
            )
            out["params"]["k_MGSE"] = mgse_k
            out["source"]["k_MGSE"] = "Zhu 2018 Eq. (12), elastic terms, mean over N = 1e4..2e6"
        su, E = props["Tensile_strength_MPa"], props["E_MPa"]
        for name, value in (strain_life_fill(su, E) if has_elastic else {}).items():
            out["params"][name] = value
            out["source"][name] = "uniform material law estimate (steel), not identifiable"
    if planes:
        block = data[material]
        if not block["cases"]:
            # No plain failures: calibration does not apply, and it is not a failure either.
            out["status"] = "not_applicable"
            out["reason"] = _not_applicable_reason(block)
            return out
        props = block["material"]
        blocks = None
        if props["E_MPa"] is None or props["nu"] is None:
            # strains are undefined: only constants of stress-only criteria can be calibrated
            from multifat.models.registry import stress_only_models

            names = {
                "FS": "FS",
                "FI": "FIN",
                "LI": "LI",
                "MGSE_ZHU": "MGSE_ZHU",
                "MSWT": "MSWT",
            }
            blocks = {b for b, m in names.items() if m in stress_only_models()}
        try:
            cal = calibrate_material_params(
                data=data,
                material_name=material,
                R_list=_make_plane_frames(),
                stdnum=stdnum,
                plane_stride=plane_stride,
                blocks=blocks,
            )
        except CalibrationInfeasible as exc:
            out["status"] = "infeasible"
            out["reason"] = str(exc)
            out["infeasible"] = {
                "block": exc.block,
                "parameter": exc.parameter,
                "diagnostic": exc.diagnostic,
            }
            out["errors"].append(f"plane-constant calibration: {exc}")
            return out
        except RuntimeError as exc:
            out["status"] = "infeasible"
            out["reason"] = str(exc)
            out["errors"].append(f"plane-constant calibration: {exc}")
            return out
        except (KeyError, ValueError) as exc:
            out["status"] = "error"
            out["reason"] = f"{type(exc).__name__}: {exc}"
            out["errors"].append(f"plane-constant calibration: {exc}")
            return out
        out["scatter_STD"], out["plateau"] = {}, {}
        for block, name in CALIBRATED.items():
            if cal.get(block) is None:
                continue
            lo, hi = cal[block]["plateau"]
            out["scatter_STD"][name] = float(cal[block]["scatter_STD"])
            out["plateau"][name] = [float(lo), float(hi)]
            if name not in out["params"]:
                out["params"][name] = float(cal[block][name])
                note = f" (flat minimum on [{lo:.4g}, {hi:.4g}]: smallest point)" if hi > lo else ""
                out["source"][name] = "scatter minimisation on uniaxial + torsion tests" + note
        sel = cal["selection"]
        out["selection"] = {
            "tension_case_ids": [int(i) for i in sel["tension_case_ids"]],
            "torsion_case_ids": [int(i) for i in sel["torsion_case_ids"]],
            "fallback": bool(
                sel["tension_info"]["fallback_used"] or sel["torsion_info"]["fallback_used"]
            ),
        }
    return out


def calibrate_many(
    *,
    exp_folder: str | Path = "Experimental_Data",
    materials: Optional[Iterable[str]] = None,
    stdnum: float = 2.0,
    plane_stride: int = 10,
) -> Dict[str, Any]:
    """Load the data and calibrate several materials, one status per material.

    One material that cannot be calibrated no longer aborts the others: a material without
    plain failures is ``not_applicable``, a failed fit is ``infeasible`` and an unexpected
    exception is ``error``; both carry a ``reason``. Calibrated materials keep the record of
    ``calibrate_material_params`` with ``status`` "calibrated" added.
    """
    data = exp.import_experimental_data_grouped_by_material(exp_folder, verbose=True)
    mats = list(materials) if materials is not None else list(data.keys())

    R_list = _make_plane_frames()
    out: Dict[str, Any] = {}
    for m in mats:
        block = data[m]
        if not block["cases"]:
            out[m] = {
                "material": m,
                "status": "not_applicable",
                "reason": _not_applicable_reason(block),
            }
            continue
        try:
            record = calibrate_material_params(
                data=data,
                material_name=m,
                R_list=R_list,
                stdnum=stdnum,
                plane_stride=plane_stride,
            )
        except CalibrationInfeasible as exc:
            out[m] = {
                "material": m,
                "status": "infeasible",
                "reason": str(exc),
                "infeasible": {
                    "block": exc.block,
                    "parameter": exc.parameter,
                    "diagnostic": exc.diagnostic,
                },
            }
            continue
        except RuntimeError as exc:
            out[m] = {"material": m, "status": "infeasible", "reason": str(exc)}
            continue
        except (KeyError, ValueError) as exc:
            out[m] = {
                "material": m,
                "status": "error",
                "reason": f"{type(exc).__name__}: {exc}",
            }
            continue
        record["status"] = "calibrated"
        record["reason"] = ""
        out[m] = record
    return out


def main(argv=None) -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Calibrate the plane constants of every workbook.")
    ap.add_argument("--data-folder", default="Experimental_Data")
    ap.add_argument(
        "--shear-amplitude-algorithm",
        default="method_default",
        choices=("method_default", "mcc_harmonic", "mce_harmonic", "rss"),
        help="Findley k_FI calibration only; method_default keeps the established MCE (RSS) "
        "amplitude. Production runs still use MCE: do not feed an MCC k_FI to multifat-pipeline",
    )
    ap.add_argument(
        "--no-overlay",
        action="store_true",
        help="use the workbooks as supplied, without the overlays",
    )
    args = ap.parse_args(argv)
    exp.OVERLAYS_ENABLED = not args.no_overlay
    data = exp.import_experimental_data_grouped_by_material(args.data_folder, verbose=True)

    mats = list(data.keys())
    if not mats:
        raise SystemExit(f"No materials found in {args.data_folder}")

    R_list = _make_plane_frames()

    summary: List[Tuple[str, str, str]] = []
    exit_code = 0

    for material_name in mats:
        block = data[material_name]
        if not block["cases"]:
            print(
                f"\n{material_name}: no plain failures, skipped (fatigue-limit or notched-only set)"
            )
            summary.append((material_name, "not_applicable", _not_applicable_reason(block)))
            continue
        try:
            cal = calibrate_material_params(
                data=data,
                material_name=material_name,
                R_list=R_list,
                stdnum=2.0,
                plane_stride=1,
                shear_amplitude_algorithm=args.shear_amplitude_algorithm,
            )
        except CalibrationInfeasible as exc:
            reason = str(exc)
            print(f"\n{material_name}: infeasible at {exc.block}: {reason}")
            summary.append((material_name, "infeasible", reason))
            exit_code = 1
            continue
        except RuntimeError as exc:
            reason = str(exc)
            print(f"\n{material_name}: infeasible: {reason}")
            summary.append((material_name, "infeasible", reason))
            exit_code = 1
            continue
        except Exception as exc:  # one broken material must not stop the others
            reason = f"{type(exc).__name__}: {exc}"
            print(f"\n{material_name}: error: {reason}")
            traceback.print_exc()
            summary.append((material_name, "error", reason))
            exit_code = 1
            continue

        print("\n" + "=" * 72)
        print("Material:", cal["material"])
        sel = cal["selection"]
        print(
            f"Uniaxial cases: tension={len(sel['tension_case_ids'])} torsion={len(sel['torsion_case_ids'])} (total={sel['n_uniax']})"
        )

        print("\nCalibrated parameters")
        if cal["FS"] is not None:
            print(f"  k_FS     = {cal['FS']['k_FS']:.6g}")
        print(f"  k_FI     = {cal['FI']['k_FI']:.6g}")
        print(f"  (Findley amplitude: {cal['amplitude_settings']['FIN']['algorithm']})")
        print(f"  L_LI     = {cal['LI']['L_LI']:.6g}")
        print(f"  k_MGSE   = {cal['MGSE_ZHU']['k_MGSE']:.6g}")
        print(f"  a_MSWT   = {cal['MSWT']['a_MSWT']:.6g}")
        for block, name in CALIBRATED.items():
            if cal[block] is not None and cal[block]["plateau"][1] > cal[block]["plateau"][0]:
                lo, hi = cal[block]["plateau"]
                print(f"  {name}: flat minimum on [{lo:.4g}, {hi:.4g}] (not identifiable)")
        # Scatter summary
        print("\nScatter STD (lnN residuals)")
        if cal["FS"] is not None:
            print(f"  FS      STD = {cal['FS']['scatter_STD']:.6g}")
        print(f"  FI      STD = {cal['FI']['scatter_STD']:.6g}")
        print(f"  LI      STD = {cal['LI']['scatter_STD']:.6g}")
        print(f"  MGSE    STD = {cal['MGSE_ZHU']['scatter_STD']:.6g}")
        print(f"  MSWT    STD = {cal['MSWT']['scatter_STD']:.6g}")
        summary.append((material_name, "calibrated", ""))

    print("\n" + "=" * 72)
    print("Calibration summary")
    print(f"{'material':<22} {'status':<14} reason")
    for material_name, status, reason in summary:
        print(f"{material_name:<22} {status:<14} {reason}")
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
