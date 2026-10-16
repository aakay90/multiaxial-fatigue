"""Versioned calibration records with failure-only compatibility checks."""
from datetime import datetime, timezone
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
from uuid import uuid4

import numpy as np

from fatigue.imp.observations import failures_only, observation_counts
from fatigue.models.references import IMPLEMENTATION_REVISION, method_reference

SCHEMA_VERSION = 1
PROCEDURE_VERSION = "failure-only-json-v1"
DEFAULT_FOLDER = "Calibrations"
METHOD_PARAMETERS = {"FS": "k_FS", "FIN": "k_FI", "LI": "L_LI",
                     "MGSE_ZHU": "k_MGSE", "MSWT": "a_MSWT"}
LEGACY_PARAMETERS = (*METHOD_PARAMETERS.values(), "alpha_w", "xi_ZHU")
DAMAGE_UNITS = {name: "1" if name in {"FS", "MKBM", "LIU2021", "GSA", "BP", "CAIM"}
                else "MPa" for name in ("FS", "FIN", "SWT", "MATAKE", "MCD", "MGSE_YU",
                    "MGSE_ZHU", "MSWT", "MKBM", "LIU2021", "LI", "GSE", "GSA", "BP", "CAIM")}
PROPERTY_KEYS = {
    "Sy": "Yield_strength_MPa", "Su": "Tensile_strength_MPa", "E": "E_MPa",
    "nu": "nu", "Sigm1": "Tensile_fatigue_limit_MPa", "Taum1": "Torsional_fatigue_limit_MPa",
    "Sig0": "Tensile_fatigue_R0_MPa", "Tau0": "Torsional_fatigue_R0_MPa",
    **{k: k for k in ("sigma_f", "epsilon_f", "b_fat", "c_fat", "tau_f", "gamma_f", "b0", "c0")},
}


def material_parameters(properties, calibrated=None):
    """Map measured workbook properties and explicit JSON coefficients to models."""
    params = {k: properties.get(v) for k, v in PROPERTY_KEYS.items()}
    params.update(calibrated or {})
    return params


def json_value(value):
    """Preserve float precision; undefined optional diagnostics become JSON null."""
    if isinstance(value, np.ndarray):
        return json_value(value.tolist())
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    return value


def input_fingerprint(data, material):
    """Hash material inputs and failure histories, excluding row IDs and run-outs.

    All failed observations are included conservatively because coefficient
    selection can broaden its load-ratio tolerance. Reordering rows or adding
    run-outs does not alter compatibility. Non-fitting failure changes can
    therefore trigger recalibration as well.
    """
    block = failures_only(data)[material]
    histories = []
    for case in block["cases"].values():
        histories.append(json.dumps(json_value({
            "N": case["meta"]["Nf_cycles"], "tensors": case[1],
            "harmonics": case.get("harmonics"),
        }), sort_keys=True, allow_nan=False))
    content = {"material": material, "properties": material_parameters(block["material"]),
               "failures": sorted(histories)}
    return hashlib.sha256(json.dumps(json_value(content), sort_keys=True,
                                     allow_nan=False).encode()).hexdigest()


def curve_settings(n1=20, n2=40, stdnum=0.0):
    return {"n1": int(n1), "n2": int(n2), "stdnum": float(stdnum),
            "selection": "reversed axial failures, existing tolerances"}


def formulation_fingerprint(name):
    """Identify the criterion and shared numerical code used by a stored curve."""
    from fatigue.models.registry import get_models
    model = get_models([name])[0]
    implementation = getattr(model, "_m", model)
    root = Path(__file__).resolve().parents[2]
    paths = [Path(inspect.getfile(type(implementation)))]
    if name == "CAIM":
        paths.append(root / "fatigue/models/integral_methods/bohme_papuga.py")
    paths += [root / p for p in (
        "fatigue/eval/fitting.py", "fatigue/eval/evaluator.py", "fatigue/planes/sampling.py",
        "fatigue/models/cp_adapter.py", "fatigue/models/utils/plane_history.py",
        "fatigue/models/utils/tensors.py", "fatigue/models/utils/fatigue_estimation.py",
        "fatigue/models/utils/param_utils.py")]
    digest = hashlib.sha256()
    for path in sorted(set(paths)):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_text(encoding="utf-8").encode())
    return digest.hexdigest()


def _identity(value):
    if not isinstance(value, str) or not value or Path(value).name != value or value in {".", ".."}:
        raise ValueError(f"Invalid material/calibration identifier {value!r}")
    return value


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def compact_design_observations(curves):
    """Store specimen provenance once, with per-curve references to used rows."""
    curves, observations = json_value(curves), {}
    for curve in curves.values():
        for suffix in ("", "_ext"):
            keys = []
            for observation in curve.pop("design_observations" + suffix, []):
                row = observation.get("excel_row")
                key = f"row-{row}" if row is not None else f"case-{observation.get('case_id')}"
                observations[key] = observation
                keys.append(key)
            curve["design_observation_ids" + suffix] = keys
    return curves, observations


def validate_record(record):
    """Reject incomplete records and non-finite required calibration results."""
    try:
        if record["schema_version"] != SCHEMA_VERSION or record["status"] != "success":
            raise ValueError("unsupported schema or unsuccessful record")
        _identity(record["calibration_id"])
        _identity(record["material_id"])
        created = datetime.fromisoformat(record["created_at"])
        if created.tzinfo is None or created.utcoffset().total_seconds() != 0:
            raise ValueError("created_at must identify UTC")
        if len(record["input_fingerprint"]) != 64:
            raise ValueError("invalid input fingerprint")
        if not isinstance(record["parameters"], dict) or not isinstance(record["curves"], dict) or not record["curves"]:
            raise ValueError("parameters or curves missing")
        for key, value in record["parameters"].items():
            if key not in LEGACY_PARAMETERS or not _finite(value):
                raise ValueError(f"invalid parameter {key}")
        for name, curve in record["curves"].items():
            key = METHOD_PARAMETERS.get(name)
            if key and key not in record["parameters"]:
                raise ValueError(f"{name} requires parameter {key}")
            series = curve["series"]
            for fit_key, dp_key in [("fit", "CP"), ("fit_ext", "CP_ext")]:
                fit = curve.get(fit_key)
                if fit is None:
                    if fit_key == "fit":
                        raise ValueError(f"missing fit for {name}")
                    continue
                if not all(_finite(fit[k]) for k in ("A", "A_surv", "b")) or fit["A"] <= 0 or fit["A_surv"] <= 0:
                    raise ValueError(f"invalid master curve for {name}/{fit_key}")
                if len(series["N"]) < 2 or len(series["N"]) != len(series[dp_key]):
                    raise ValueError(f"invalid design series for {name}")
                if not all(_finite(v) and v > 0 for v in [*series["N"], *series[dp_key]]):
                    raise ValueError(f"invalid design values for {name}")
                suffix = "_ext" if fit_key == "fit_ext" else ""
                ids = curve["design_observation_ids" + suffix]
                if len(ids) != len(series["N"]) or any(key not in record["design_observations"] for key in ids):
                    raise ValueError(f"invalid design provenance for {name}")
        for key in ("curve_settings", "procedure_version", "implementation_revision", "counts", "source", "software", "formulation_fingerprints"):
            if key not in record:
                raise ValueError(f"missing {key}")
        # Includes optional diagnostics. JSON null is allowed, NaN/Infinity are not.
        json.dumps(record, allow_nan=False)
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError) as exc:
        raise ValueError(f"Invalid calibration record: {exc}") from exc


def create_record(*, data, material, parameters, curves, settings, procedure,
                  optimisation=None, parameter_origin="optimised by Script 0"):
    """Construct a record; saving is a separate atomic operation."""
    block = data[material]
    curves, design_observations = compact_design_observations(curves)
    source = dict(block.get("source", {}))
    workbook = Path(source.get("workbook", ""))
    if workbook.is_file():
        source["workbook_sha256"] = hashlib.sha256(workbook.read_bytes()).hexdigest()
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"]))
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    now = datetime.now(timezone.utc)
    counts = observation_counts(block)
    counts["failures_used_by_curve"] = {n: len(c["series"]["N"]) for n, c in curves.items()}
    if optimisation:
        counts["failures_selected_for_coefficients"] = optimisation["selection"]["n_uniax"]
        counts["failures_used_by_coefficient"] = {name: value["fit"]["n"] for name, value in optimisation.items()
                                                   if isinstance(value, dict) and "fit" in value}
    record = json_value({
        "schema_version": SCHEMA_VERSION, "status": "success",
        "calibration_id": now.strftime("%Y%m%dT%H%M%S%fZ_") + uuid4().hex[:12],
        "created_at": now.isoformat(), "material_id": material, "material_name": material,
        "material_condition": None, "procedure": procedure, "procedure_version": PROCEDURE_VERSION,
        "implementation_revision": IMPLEMENTATION_REVISION,
        "input_fingerprint": input_fingerprint(data, material), "source": source,
        "material_inputs": material_parameters(block["material"]),
        "material_input_units": {k: "MPa" if k in {"Sy", "Su", "E", "Sigm1", "Taum1", "Sig0", "Tau0", "sigma_f", "tau_f"}
                                 else "1" for k in PROPERTY_KEYS},
        "parameters": parameters, "parameter_origin": parameter_origin,
        "parameter_units": {p: "1" if p in METHOD_PARAMETERS.values() else "unverified legacy constant"
                            for p in parameters},
        "curve_units": {"N": "cycle", "DP": "criterion-dependent repository damage parameter",
                        "A": "DP * cycle**(-b)", "A_surv": "DP * cycle**(-b)", "b": "1",
                        "STD": "1 (ln cycle residual)", "STD_ln_DP": "1", "R2_log": "1"},
        "damage_parameter_units": {name: DAMAGE_UNITS[name] for name in curves},
        "nonfinite_diagnostics": "Undefined optional scatter or R2 values are null; required fits must be finite.",
        "curve_settings": settings, "curves": curves, "optimisation": optimisation,
        "design_observations": design_observations,
        "counts": counts, "references": {n: method_reference(n) for n in curves},
        "formulation_fingerprints": {n: formulation_fingerprint(n) for n in curves},
        "software": {"git_commit": commit, "tracked_worktree_dirty": dirty,
                     "numpy": np.__version__},
    })
    validate_record(record)
    return record


def calibration_signature(record):
    """Identify equivalent numerical results without timestamp or row provenance.

    Keep inputs, fitting options, formulations, computed values and NumPy version.
    Source paths, workbook formatting, censored counts and Git working state do
    not change the calibration. Reuse retains the original record's provenance.
    """
    keys = ("schema_version", "material_id", "input_fingerprint", "procedure_version",
            "implementation_revision", "parameters", "curve_settings", "formulation_fingerprints",
            "curves", "optimisation", "parameter_origin", "procedure", "material_inputs",
            "parameter_units", "curve_units", "damage_parameter_units")
    content = json_value({key: record.get(key) for key in keys})
    for curve in content["curves"].values():
        for suffix in ("", "_ext"):
            curve.pop("design_observation_ids" + suffix, None)
    optimisation = content.get("optimisation")
    if optimisation:
        selection = optimisation.get("selection", {})
        selection.pop("tension_case_ids", None)
        selection.pop("torsion_case_ids", None)
    content["software"] = {key: value for key, value in record["software"].items()
                           if key not in {"git_commit", "tracked_worktree_dirty"}}
    return hashlib.sha256(json.dumps(content, sort_keys=True, allow_nan=False).encode()).hexdigest()


def read_record(path):
    """Read and validate a complete historical JSON record."""
    try:
        record = json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=_reject_json_number)
        validate_record(record)
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read calibration {path}: {exc}") from exc
    return record


def save_record(record, folder=DEFAULT_FOLDER):
    """Publish a complete JSON file atomically, without replacing prior history."""
    validate_record(record)
    directory = Path(folder) / _identity(record["material_id"])
    directory.mkdir(parents=True, exist_ok=True)
    final = directory / (_identity(record["calibration_id"]) + ".json")
    if final.exists():
        raise FileExistsError(f"Calibration ID already exists: {final}")
    signature = calibration_signature(record)
    for path in sorted(directory.glob("*.json")):
        if calibration_signature(read_record(path)) == signature:
            return path
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory,
                                         suffix=".tmp", delete=False) as handle:
            temp = Path(handle.name)
            json.dump(record, handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp, final)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return final


def _reject_json_number(value):
    raise ValueError(f"Non-finite JSON numeric constant {value}")


def load_calibration(*, data, material, model, settings, folder=DEFAULT_FOLDER, calibration_id=None):
    """Select by declared UTC creation time and ID, never by file mtime."""
    directory = Path(folder) / _identity(material)
    paths = [directory / (_identity(calibration_id) + ".json")] if calibration_id else sorted(directory.glob("*.json"))
    compatible = []
    fingerprint = input_fingerprint(data, material)
    for path in paths:
        record = read_record(path)
        matches = (record["material_id"] == material and record["input_fingerprint"] == fingerprint
                   and record["procedure_version"] == PROCEDURE_VERSION
                   and record["implementation_revision"] == IMPLEMENTATION_REVISION
                   and record["formulation_fingerprints"].get(model) == formulation_fingerprint(model)
                   and record["curve_settings"] == settings and model in record["curves"])
        if matches:
            compatible.append((record["created_at"], record["calibration_id"], record, path))
        elif calibration_id:
            raise ValueError(f"Calibration {calibration_id} is incompatible with {material}/{model}, inputs or curve settings")
    if not compatible:
        parameter = METHOD_PARAMETERS.get(model)
        raise ValueError(f"No compatible calibration for {material}/{model}"
                         f" (coefficient {parameter or 'none'} and master curve required). "
                         f"Run python 0_calibrate_material_params.py --material '{material}' --models {model}. "
                         "Changed failure data, properties or fitting settings require a new record.")
    _, _, record, path = max(compatible, key=lambda item: (item[0], item[1]))
    curve = record["curves"][model]
    curve = {**curve, "series": {k: np.asarray(v, dtype=float) for k, v in curve["series"].items()}}
    for suffix in ("", "_ext"):
        curve["design_observations" + suffix] = [record["design_observations"][key]
            for key in curve.get("design_observation_ids" + suffix, [])]
    return record, curve, path
