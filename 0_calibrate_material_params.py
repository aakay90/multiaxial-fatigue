# calibrate_cp_params.py
"""Calibration utility for critical-plane / model parameters.

Originally used to calibrate:
- k_FS for Fatemi–Socie (FS)
- k_FI for Findley (FIN)

Extended (per your request) to also calibrate additional material parameters:
- L_LI     (Li 2021 CP method)
- k_MGSE   (MGSE_ZHU CP method)
- a_MSWT   (MSWT CP method)
ZHU_EDP calibration was removed by the numerical audit; see docs/method-audit.md.

Repository conventions (v6)
--------------------------
- Experimental data importer: fatigue.imp.experimental_data
- Plane sampling: fatigue.planes.sampling (dcmesh_xyz, gentang)
- Critical-plane evaluation: fatigue.eval.evaluator.best_cp_for_case
- CP methods: fatigue.models.cp_methods

Calibration objective
---------------------
For each candidate parameter value(s), compute the model scalar (CP/DP) for each
selected case, fit a power law in log-space:

    CP = A * N^b

and minimize fatigue scatter defined as the STD of residuals in ln(N) using the
project's helper: fatigue.eval.fitting.fit_power_law_with_survival_std.

Datasets
--------
- FS, FIN, LI, MGSE_ZHU, MSWT:
    use uniaxial axial + uniaxial torsion points (target R=-1 with fallbacks).
    This matches the legacy calibration intent.

Notes
-----
- This script writes JSON calibration records without editing Excel. It reports parameters and
  returns a nested dictionary for programmatic use.
- No SciPy is used: a grid-refine search is implemented.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from fatigue.imp import experimental_data as exp
from fatigue.planes.sampling import dcmesh_xyz, gentang
from fatigue.eval.evaluator import best_cp_for_case
from fatigue.eval.fitting import fit_power_law_with_survival_std
from fatigue.eval.findley_calibration import (
    FindleyCalibrationModel, amplitude_identity, check_amplitude_methods,
    require_stress_harmonics,
)

from fatigue.imp.observations import failures_only, observation_counts
from fatigue.models.cp_methods.fs import FatemiSocie
from fatigue.models.cp_methods.fin import Findley
from fatigue.models.cp_methods.li import LI
from fatigue.models.cp_methods.mgse_zhu import MGSE_Zhu
from fatigue.models.cp_methods.mswt import MSWT



# -----------------------------
# Simple minimizers (no SciPy)
# -----------------------------

def minimize_1d_grid_refine(
    objective: Callable[[float], float],
    bounds: Tuple[float, float],
    *,
    n_grid: int = 41,
    n_refine: int = 6,
) -> Tuple[float, float]:
    """Minimize objective(x) over [lo, hi] via repeated grid search."""
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
            raise ValueError("No finite calibration objective: check design data and master-curve slope")
        j = int(np.argmin(np.where(np.isfinite(fs), fs, np.inf)))
        x_best = float(xs[j])
        f_best = float(fs[j])

        step = (hi - lo) / max(1, (len(xs) - 1))
        lo = max(bounds[0], x_best - 2.0 * step)
        hi = min(bounds[1], x_best + 2.0 * step)

        if hi - lo < 1e-10:
            break

    return x_best, f_best



def _dominance_ratio(other_max: float, main_max: float, *, atol: float, rtol: float) -> bool:
    return other_max <= (rtol * abs(main_max) + atol)


def _case_get_Smax_Smin(case: Dict[str, Any], node: int = 1) -> Tuple[np.ndarray, np.ndarray]:
    S0 = np.asarray(case[node][1]["stress"], dtype=float)
    S1 = np.asarray(case[node][2]["stress"], dtype=float)
    return S0, S1


def _uniaxial_tension_filter(
    case: Dict[str, Any],
    *,
    node: int = 1,
    r_target: Optional[float] = -1.0,
    rtol_R: float = 0.02,
    atol_R: float = 1e-6,
    rtol_uniax: float = 1e-3,
    atol_uniax: float = 1e-6,
) -> Tuple[bool, float]:
    S0, S1 = _case_get_Smax_Smin(case, node=node)

    s0 = float(S0[1, 1])
    s1 = float(S1[1, 1])
    smax = max(s0, s1)
    smin = min(s0, s1)

    if abs(smax) < atol_R:
        return False, np.nan

    R = smin / smax

    if smax <= 0.0:
        return False, R

    S_other = S0.copy()
    S_other[1, 1] = 0.0
    other_max = float(np.max(np.abs(S_other)))
    if not _dominance_ratio(other_max, smax, atol=atol_uniax, rtol=rtol_uniax):
        return False, R

    if r_target is not None:
        if not np.isclose(R, r_target, rtol=rtol_R, atol=atol_R):
            return False, R

    return True, R


def _uniaxial_torsion_filter(
    case: Dict[str, Any],
    *,
    node: int = 1,
    r_target: Optional[float] = -1.0,
    rtol_R: float = 0.02,
    atol_R: float = 1e-6,
    rtol_uniax: float = 1e-3,
    atol_uniax: float = 1e-6,
) -> Tuple[bool, float]:
    S0, S1 = _case_get_Smax_Smin(case, node=node)

    t0 = float(S0[0, 1])
    t1 = float(S1[0, 1])
    tmax = max(t0, t1)
    tmin = min(t0, t1)

    if abs(tmax) < atol_R:
        return False, np.nan

    R = tmin / tmax

    if tmax <= 0.0:
        return False, R

    S_other = S0.copy()
    S_other[0, 1] = 0.0
    S_other[1, 0] = 0.0
    other_max = float(np.max(np.abs(S_other)))
    if not _dominance_ratio(other_max, tmax, atol=atol_uniax, rtol=rtol_uniax):
        return False, R

    if r_target is not None:
        if not np.isclose(R, r_target, rtol=rtol_R, atol=atol_R):
            return False, R

    return True, R


def _select_cases_with_fallback(
    cases: Dict[int, Dict[str, Any]],
    selector: Callable[..., Tuple[bool, float]],
    *,
    selector_kwargs: Dict[str, Any],
    fallback_rtol_list: Sequence[float] = (0.02, 0.05, 0.1, 0.2, 0.5),
    allow_any_R_fallback: bool = True,
    name_for_warnings: str = "dataset",
) -> Tuple[List[int], Dict[str, Any]]:
    info: Dict[str, Any] = {"fallback_used": False, "rtol_R_used": None, "any_R_used": False}

    selected: List[int] = []
    for cid, case in cases.items():
        ok, _R = selector(case, **selector_kwargs)
        if ok:
            selected.append(int(cid))

    if selected:
        info["rtol_R_used"] = selector_kwargs.get("rtol_R", None)
        return selected, info

    base_kwargs = dict(selector_kwargs)
    for rtol_R in fallback_rtol_list:
        base_kwargs["rtol_R"] = float(rtol_R)
        selected = []
        for cid, case in cases.items():
            ok, _R = selector(case, **base_kwargs)
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
# Calibration helpers
# -----------------------------

@dataclass(frozen=True)
class CalibrationResult1D:
    param_name: str
    p_opt: float
    scatter_STD: float
    fit: Dict[str, float]
    series: Dict[str, np.ndarray]


def _build_R_list(*, n1: int = 20, n2: int = 40) -> np.ndarray:
    xyz = dcmesh_xyz(a1=np.pi, n1=int(n1), a2=2 * np.pi, n2=int(n2))
    xyz = np.unique(np.round(xyz, 12), axis=0)
    R = gentang(xyz, return_matrices=True)
    return np.asarray(R)


def _calibrate_1d(
    *,
    cases_data: List[Dict[str, Any]],
    dp_eval: Callable[[Dict[str, Any], float], float],
    bounds: Tuple[float, float],
    stdnum: float,
    n_grid: int,
    n_refine: int,
    param_name: str,
) -> CalibrationResult1D:
    N = np.array([c["Nf"] for c in cases_data], dtype=float)

    def objective(p: float) -> float:
        DP = np.array([dp_eval(c, float(p)) for c in cases_data], dtype=float)
        fit = fit_power_law_with_survival_std(N, DP, stdnum=stdnum)
        return float(fit["STD"]) if np.isfinite(fit["STD"]) else np.inf

    p_best, std_best = minimize_1d_grid_refine(objective, bounds, n_grid=n_grid, n_refine=n_refine)

    DP_best = np.array([dp_eval(c, float(p_best)) for c in cases_data], dtype=float)
    fit = fit_power_law_with_survival_std(N, DP_best, stdnum=stdnum)

    return CalibrationResult1D(
        param_name=str(param_name),
        p_opt=float(p_best),
        scatter_STD=float(std_best),
        fit=dict(fit),
        series={"N": N, "DP": DP_best},
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
    bounds_k_FS: Tuple[float, float] = (0.0, 3.0),
    bounds_k_FI: Tuple[float, float] = (0.0, 3.0),
    bounds_L_LI: Tuple[float, float] = (0.0, 5.0),
    bounds_k_MGSE: Tuple[float, float] = (0.0, 5.0),
    bounds_a_MSWT: Tuple[float, float] = (0.0, 1.0),
    methods: Optional[Sequence[str]] = None,
    shear_amplitude_algorithm: str = "method_default",
) -> Dict[str, Any]:
    """Calibrate FS/FIN + additional parameters for one material."""

    if material_name not in data:
        raise KeyError(f"Material '{material_name}' not found. Available: {list(data.keys())}")

    methods = set(methods if methods is not None else ("FS", "FIN", "LI", "MGSE_ZHU", "MSWT"))
    check_amplitude_methods(methods, shear_amplitude_algorithm)
    data = failures_only(data)
    if R_list is None:
        R_list = _build_R_list()

    if plane_stride is not None and int(plane_stride) > 1:
        R_use = np.asarray(R_list)[:: int(plane_stride)]
    else:
        R_use = np.asarray(R_list)

    mat = data[material_name]
    mat_prop = mat.get("material", {})
    cases = mat.get("cases", {})

    Sy = mat_prop.get("Yield_strength_MPa", None)
    if "FS" in methods and (Sy is None or not np.isfinite(Sy)):
        raise ValueError(f"Yield strength not found/invalid for material '{material_name}'. Needed for FS.")

    selector_kwargs = dict(
        node=node,
        r_target=r_target,
        rtol_R=rtol_R_init,
        atol_R=1e-6,
        rtol_uniax=rtol_uniax,
        atol_uniax=1e-6,
    )

    tension_ids, tension_info = _select_cases_with_fallback(
        cases,
        _uniaxial_tension_filter,
        selector_kwargs=selector_kwargs,
        name_for_warnings=f"{material_name}/uniaxial_tension",
    )
    torsion_ids, torsion_info = _select_cases_with_fallback(
        cases,
        _uniaxial_torsion_filter,
        selector_kwargs=selector_kwargs,
        name_for_warnings=f"{material_name}/uniaxial_torsion",
    )

    if len(tension_ids) == 0 or len(torsion_ids) == 0:
        warnings.warn(
            f"[{material_name}] Uniaxial dataset may be incomplete: tension={len(tension_ids)} torsion={len(torsion_ids)}.",
            RuntimeWarning,
        )

    combined_ids = tension_ids + torsion_ids

    uniax_cases: List[Dict[str, Any]] = []
    for cid in combined_ids:
        c = cases[int(cid)]
        if "FIN" in methods and shear_amplitude_algorithm != "method_default":
            require_stress_harmonics(c, material_name, int(cid))
        Nf = float(c["meta"]["Nf_cycles"])
        S0, E0, S1, E1, H = exp.extract_tensor(data, material_name, int(cid), node=node, include_harmonics=True)
        uniax_cases.append({"case_id": int(cid), "Nf": Nf, "S0": S0, "E0": E0, "S1": S1, "E1": E1, "H": H})

    if len(uniax_cases) < 2:
        raise RuntimeError(f"[{material_name}] Not enough uniaxial cases to calibrate (need >= 2).")

    # ------------------
    # Instantiate methods
    # ------------------
    fs_method = FatemiSocie()
    fin_method = Findley()
    configured_findley = FindleyCalibrationModel(shear_amplitude_algorithm)
    li_method = LI()
    mgse_method = MGSE_Zhu()
    mswt_method = MSWT()

    # ------------------
    # 1D CP parameter evals
    # ------------------
    def fs_eval(case_dict: Dict[str, Any], k: float) -> float:
        best = best_cp_for_case(
            S0=case_dict["S0"],
            E0=case_dict["E0"],
            S1=case_dict["S1"],
            E1=case_dict["E1"],
            R_list=R_use,
            method=fs_method,
            params={"k_FS": float(k), "Sy": float(Sy)},
            S_sin=case_dict["H"].get("S_sin"),
            S_cos=case_dict["H"].get("S_cos"),
            E_sin=case_dict["H"].get("E_sin"),
            E_cos=case_dict["H"].get("E_cos"),
        )
        return float(best.by_metric)  # plane maximizing Δγ

    def fin_eval(case_dict: Dict[str, Any], k: float) -> float:
        if shear_amplitude_algorithm != "method_default":
            result = configured_findley.evaluate_case(
                S0=case_dict["S0"], E0=case_dict["E0"], S1=case_dict["S1"], E1=case_dict["E1"],
                R_list=R_use, params={"k_FI": float(k)}, harmonics=case_dict["H"])
            return float(result.values["_ext"])
        best = best_cp_for_case(
            S0=case_dict["S0"],
            E0=case_dict["E0"],
            S1=case_dict["S1"],
            E1=case_dict["E1"],
            R_list=R_use,
            method=fin_method,
            params={"k_FI": float(k)},
            S_sin=case_dict["H"].get("S_sin"),
            S_cos=case_dict["H"].get("S_cos"),
            E_sin=case_dict["H"].get("E_sin"),
            E_cos=case_dict["H"].get("E_cos"),
        )
        return float(best.ext)  # maximize Findley scalar

    def li_eval(case_dict: Dict[str, Any], L: float) -> float:
        best = best_cp_for_case(
            S0=case_dict["S0"],
            E0=case_dict["E0"],
            S1=case_dict["S1"],
            E1=case_dict["E1"],
            R_list=R_use,
            method=li_method,
            params={"L_LI": float(L)},
            S_sin=case_dict["H"].get("S_sin"),
            S_cos=case_dict["H"].get("S_cos"),
            E_sin=case_dict["H"].get("E_sin"),
            E_cos=case_dict["H"].get("E_cos"),
        )
        # Li defines a shear-driven plane criterion; the CP method's metric
        # is designed to select that plane -> use by_metric.
        return float(best.by_metric)

    def mgse_eval(case_dict: Dict[str, Any], k: float) -> float:
        best = best_cp_for_case(
            S0=case_dict["S0"],
            E0=case_dict["E0"],
            S1=case_dict["S1"],
            E1=case_dict["E1"],
            R_list=R_use,
            method=mgse_method,
            params={"k_MGSE": float(k)},
            S_sin=case_dict["H"].get("S_sin"),
            S_cos=case_dict["H"].get("S_cos"),
            E_sin=case_dict["H"].get("E_sin"),
            E_cos=case_dict["H"].get("E_cos"),
        )
        return float(best.ext)

    def mswt_eval(case_dict: Dict[str, Any], a: float) -> float:
        best = best_cp_for_case(
            S0=case_dict["S0"],
            E0=case_dict["E0"],
            S1=case_dict["S1"],
            E1=case_dict["E1"],
            R_list=R_use,
            method=mswt_method,
            params={"a_MSWT": float(a)},
            S_sin=case_dict["H"].get("S_sin"),
            S_cos=case_dict["H"].get("S_cos"),
            E_sin=case_dict["H"].get("E_sin"),
            E_cos=case_dict["H"].get("E_cos"),
        )
        return float(best.ext)

    # ------------------
    # Calibrate 1D params on uniaxial dataset
    # ------------------
    FS_cal = _calibrate_1d(
        cases_data=uniax_cases,
        dp_eval=fs_eval,
        bounds=bounds_k_FS,
        stdnum=stdnum,
        n_grid=n_grid_1d,
        n_refine=n_refine_1d,
        param_name="k_FS",
    ) if "FS" in methods else None
    FI_cal = _calibrate_1d(
        cases_data=uniax_cases,
        dp_eval=fin_eval,
        bounds=bounds_k_FI,
        stdnum=stdnum,
        n_grid=n_grid_1d,
        n_refine=n_refine_1d,
        param_name="k_FI",
    ) if "FIN" in methods else None
    LI_cal = _calibrate_1d(
        cases_data=uniax_cases,
        dp_eval=li_eval,
        bounds=bounds_L_LI,
        stdnum=stdnum,
        n_grid=n_grid_1d,
        n_refine=n_refine_1d,
        param_name="L_LI",
    ) if "LI" in methods else None
    MGSE_cal = _calibrate_1d(
        cases_data=uniax_cases,
        dp_eval=mgse_eval,
        bounds=bounds_k_MGSE,
        stdnum=stdnum,
        n_grid=n_grid_1d,
        n_refine=n_refine_1d,
        param_name="k_MGSE",
    ) if "MGSE_ZHU" in methods else None
    MSWT_cal = _calibrate_1d(
        cases_data=uniax_cases,
        dp_eval=mswt_eval,
        bounds=bounds_a_MSWT,
        stdnum=stdnum,
        n_grid=n_grid_1d,
        n_refine=n_refine_1d,
        param_name="a_MSWT",
    ) if "MSWT" in methods else None

    # ------------------
    # Pack output
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
    }
    for name, result in [("FS", FS_cal), ("FI", FI_cal), ("LI", LI_cal),
                         ("MGSE_ZHU", MGSE_cal), ("MSWT", MSWT_cal)]:
        if result is not None:
            out[name] = {result.param_name: result.p_opt,
                         "scatter_STD": result.scatter_STD, "fit": result.fit}

    if "FIN" in methods:
        out["amplitude_settings"] = {"FIN": amplitude_identity(shear_amplitude_algorithm)}

    return out


def calibrate_many(
    *,
    exp_folder: str | Path = "Experimental_Data",
    materials: Optional[Iterable[str]] = None,
    stdnum: float = 2.0,
    plane_stride: int = 10,
) -> Dict[str, Any]:
    """Import data and calibrate multiple materials."""
    data = exp.import_experimental_data_grouped_by_material(exp_folder, verbose=True)
    mats = list(materials) if materials is not None else list(data.keys())

    R_list = _build_R_list()
    out: Dict[str, Any] = {}
    for m in mats:
        out[m] = calibrate_material_params(
            data=data,
            material_name=m,
            R_list=R_list,
            stdnum=stdnum,
            plane_stride=plane_stride,
        )
    return out


def main(argv=None):
    """Export fitted coefficients and selected master curves with provenance."""
    import argparse
    from fatigue.models.registry import _available_cp_methods, _available_direct_models
    from fatigue.eval.calibration import export_calibration
    from fatigue.eval.calibration_store import METHOD_PARAMETERS, curve_settings, load_calibration
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-folder", default="Experimental_Data")
    parser.add_argument("--calibrations-dir", default="Calibrations")
    parser.add_argument("--material", help="Workbook stem; omitted selects all materials")
    parser.add_argument("--models", nargs="+", default=list(_available_cp_methods()) + list(_available_direct_models()))
    parser.add_argument("--n1", type=int, default=20)
    parser.add_argument("--n2", type=int, default=40)
    parser.add_argument("--stdnum", type=float, default=0.0, help="Master-curve damage-space shift")
    parser.add_argument("--parameter-stdnum", type=float, default=2.0)
    parser.add_argument("--plane-stride", type=int, default=10)
    parser.add_argument("--n-grid", type=int, default=41)
    parser.add_argument("--n-refine", type=int, default=6)
    parser.add_argument("--status-file", help="Write per-method calibration outcomes as JSON")
    parser.add_argument("--reuse-calibration", help="Explicit compatible JSON ID supplying coefficients")
    parser.add_argument("--shear-amplitude-algorithm", default="method_default",
                        choices=("method_default", "mcc_harmonic", "mce_harmonic", "rss"),
                        help="Findley calibration only; method_default preserves historical MCE/RSS")
    args = parser.parse_args(argv)
    data = exp.import_experimental_data_grouped_by_material(args.data_folder)
    materials = [args.material] if args.material else list(data)
    models = list(dict.fromkeys(m.removesuffix("_ext") for m in args.models))
    settings = curve_settings(args.n1, args.n2, args.stdnum)
    paths = []
    from fatigue.eval.eligibility import calibration_readiness, warn_unavailable
    from fatigue.eval.calibration_store import json_value
    import json
    outcomes = []
    for material in materials:
        for method in models:
            readiness = calibration_readiness(data, material, method,
                shear_amplitude_algorithm=args.shear_amplitude_algorithm)
            status = {'material': material, 'method': method, **readiness}
            if not readiness['can_calibrate'] and not args.reuse_calibration:
                status['reasons'] += ['Missing or invalid inputs: ' + ', '.join(readiness['missing_properties'])]
                warn_unavailable(status, 'calibration')
                outcomes.append({**status, 'status': 'skipped'})
                continue
            try:
                check_amplitude_methods([method], args.shear_amplitude_algorithm)
                needed = [method] if method in METHOD_PARAMETERS else []
                optimisation = None
                params = {}
                origin = "No method coefficients required"
                if args.reuse_calibration:
                    previous, _, path = load_calibration(data=data, material=material, model=method,
                        settings=settings, folder=args.calibrations_dir, calibration_id=args.reuse_calibration,
                        shear_amplitude_algorithm=args.shear_amplitude_algorithm)
                    params = previous["parameters"]
                    origin = f"Explicit reuse of {previous['calibration_id']}"
                    print(f"Coefficient source {path}")
                elif needed:
                    optimisation = calibrate_material_params(
                        data=data, material_name=material, R_list=_build_R_list(n1=args.n1, n2=args.n2),
                        stdnum=args.parameter_stdnum, plane_stride=args.plane_stride,
                        n_grid_1d=args.n_grid, n_refine_1d=args.n_refine, methods=needed,
                        shear_amplitude_algorithm=args.shear_amplitude_algorithm)
                    params = {METHOD_PARAMETERS[m]: optimisation["FI" if m == "FIN" else m][METHOD_PARAMETERS[m]] for m in needed}
                    origin = "Optimised by Script 0 on uniaxial tension/torsion failures"
                missing = [METHOD_PARAMETERS[m] for m in needed if METHOD_PARAMETERS[m] not in params]
                if missing:
                    raise ValueError(f"Missing calibrated coefficients {missing}")
                if optimisation is not None:
                    optimisation["settings"] = {"stdnum": args.parameter_stdnum, "plane_stride": args.plane_stride,
                        "n_grid": args.n_grid, "n_refine": args.n_refine, "n1": args.n1, "n2": args.n2,
                        "bounds": {"k_FS": [0, 3], "k_FI": [0, 3], "L_LI": [0, 5], "k_MGSE": [0, 5], "a_MSWT": [0, 1]}}
                record, path = export_calibration(data=data, material=material, models=[method], parameters=params,
                    settings=settings, folder=args.calibrations_dir, optimisation=optimisation, parameter_origin=origin,
                    shear_amplitude_algorithm=args.shear_amplitude_algorithm)
                print(f"Saved or reused calibration {path}; current observations {observation_counts(data[material])}; "
                      f"stored observations {record['counts']}")
                paths.append(path)
                outcomes.append({**status, 'status': 'saved', 'calibration_id': record['calibration_id']})
            except (ValueError, KeyError, RuntimeError) as exc:
                status['reasons'] = [str(exc)]
                warn_unavailable(status, 'calibration')
                outcomes.append({**status, 'status': 'failed'})
    if args.status_file:
        Path(args.status_file).parent.mkdir(parents=True, exist_ok=True)
        Path(args.status_file).write_text(json.dumps(json_value(outcomes), indent=2, allow_nan=False) + '\n')
    print(f"Calibration summary: {sum(o['status'] == 'saved' for o in outcomes)} saved/reused; "
          f"{sum(o['status'] != 'saved' for o in outcomes)} skipped/failed")
    return paths


if __name__ == "__main__":
    main()
