# Architecture and data flow

`0_calibrate_material_params.py` reads material/experimental inputs, optimises the
requested method coefficients and fits the corresponding master curves using
failures only. It writes a new JSON record under `Calibrations/<material>/`.
`1_run_material.py` selects a compatible record, evaluates workbook cases and
writes `Results/<METHOD>_<MATERIAL>.csv`. It does not fit curves or read calibrated
coefficients from Excel. `2_compare_results.py` generates comparison plots and
failure-only error statistics. The [calibration workflow](calibration-workflow.md)
documents record selection, historical coefficients and run-out conventions.

| Path | Role |
| --- | --- |
| `fatigue/imp/experimental_data.py` | Workbook import, material properties, stress/strain tensors and harmonics |
| `fatigue/planes/sampling.py` | Candidate plane rotations; each plane normal is the third column of its rotation matrix |
| `fatigue/models/base.py` | Model interfaces and result types |
| `fatigue/models/cp_adapter.py` | Case-level wrapper around critical-plane methods |
| `fatigue/models/registry.py` | Names exposed to the runner |
| `fatigue/models/utils/tensors.py` | Shared 3×3 input conversion/shape checks; existing private aliases retained |
| `fatigue/models/integral_methods/` | Integral BP and hybrid critical-amplitude/integral-mean CAIM criteria |
| `fatigue/eval/` | Critical-plane evaluation, calibration and fitting |
| `fatigue/eval/calibration_store.py` | JSON validation, immutable history and input/formulation compatibility |
| `fatigue/imp/observations.py`, `fatigue/report/observations.py` | Failure-only selection and run-out plotting/error conventions |
| `fatigue/report/export_csv.py` | Per-method CSV output |

The importer reads material properties from `Summary` and observations from
`Dataset`. It excludes notched and numerically invalid cases, retains run-outs
and records explicit failure/run-out/unknown status. Only failures enter fitting.
Optional radial and torsional phases produce stress and strain harmonics (`mean`,
`sin`, `cos`) for single-frequency loading. The critical-plane evaluator retains
the existing two-loadstep interface (`S0`/`E0`, `S1`/`E1`). Direct methods must use
the supplied harmonics explicitly when required by their formulation.

The main CSV fields include `Material`, `Method`, `Method_family`, `Loading_type`, `Flag`, `Metric_mode`, `Nf_exp`, `Nf_expected`, `CP_value`, `DP_fit`, `Error_ln`, and `Error_ln_dp`. `Flag=0` marks calibration points. `Metric_mode=Nf` compares predicted and experimental cycles; `DP_DIFF` compares damage parameters when the calibration slope is nearly flat (the runner switches when its slope parameter exceeds 15). Preserve these field names when extending reporting.

New exports additionally contain `Error_log10_dp`, `Implementation_revision`, and `Method_reference`. Damage-space comparisons use `log10(DP_fit/CP_value)` for every slope. See [method-audit.md](method-audit.md) for the harmonic conventions, corrected methods, and excluded historical results.

JSON-based exports also identify `Test_status`, `Specimen_id`, `Calibration_id`
and `Calibration_file`. For run-outs, `Nf_exp` is a recorded lower bound. Ordinary
error fields and `DP_fit` remain undefined; comparison readers preserve that rule.
