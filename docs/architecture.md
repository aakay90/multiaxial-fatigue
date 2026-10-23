# Data flow and architecture

Validation, calibration of missing constants, execution of every registered model and the comparison step are chained by `scripts/3_pipeline.py` (`multifat-pipeline`) for one or more workbooks (see [workbook-format.md](workbook-format.md)). A single material workbook from `Experimental_Data/` is read by `scripts/1_run_material.py`; that script chooses the uniaxial design points, fits a power-law relation only for the selected method, evaluates the remaining cases and writes `Results/<METHOD>_<MATERIAL>.csv`. The resulting CSV files are consumed by `scripts/2_compare_results.py`, which produces plots and tables under `Results/Comparison/`. Suggested material parameters are printed by `scripts/0_calibrate_material_params.py`, without any edit to the workbooks.

| Path | Role |
| --- | --- |
| `src/multifat/imp/experimental_data.py` | Workbook loading, material properties, stress/strain tensors and harmonics |
| `src/multifat/imp/schema.py` | Workbook input contract: column rules, value parsing, `WorkbookError`, validation report |
| `src/multifat/cli/pipeline.py` | Pipeline run by a single command across every registered model, with a report for each model run |
| `src/multifat/planes/sampling.py` | Candidate rotations of planes; the third column of each rotation matrix gives that plane's normal |
| `src/multifat/models/base.py` | Interfaces for models and result types |
| `src/multifat/models/cp_adapter.py` | Wrapper at case level for critical-plane methods |
| `src/multifat/models/registry.py` | Names made visible to the runner |
| `src/multifat/models/utils/tensors.py` | Shared conversion of 3×3 inputs and shape checks |
| `src/multifat/models/integral_methods/` | Integral BP methods and hybrid critical-amplitude/integral-mean CAIM criteria |
| `src/multifat/eval/` | Evaluation, calibration and fitting on critical planes |
| `src/multifat/eval/endurance.py` | Fatigue-index error on fatigue-limit datasets |
| `src/multifat/report/export_csv.py` | Per-method output in CSV format |
| `src/multifat/report/subsets.py` | Observation identities, dataset fingerprint and common subsets (from upstream 904c619) |
| `src/multifat/models/utils/shear_amplitude.py` | Harmonic MCC/MCE shear amplitudes that the criteria do not use (from upstream 88229e9) |

Material properties are obtained by the importer from the `Summary` sheet, whereas cases come from the `Dataset` sheet; there is one workbook per material ID, the material ID being the file name with its ordering number removed. Plain failures and run-outs are kept separate. Notched rows are discarded, and in the revised format rows with unknown loading are excluded (see [dataset-workflow.md](dataset-workflow.md)). Strains remain undefined when a workbook lacks E or nu, in which case only stress-only models are run. If a workbook holds fatigue-limit states only, it is routed to the fatigue index error (`eval/endurance.py`) instead of a life curve. Optional radial and torsional phase columns generate stress and strain harmonics (`mean`, `sin`, `cos`) for single-frequency sinusoidal loading. The critical-plane evaluator relies on them for non-proportional loading while retaining the legacy two-loadstep interface (`S0`/`E0` and `S1`/`E1`). Direct methods are given the harmonics, but they are required to use them explicitly. The symbols are listed in [notation.md](notation.md).

Main fields in the CSV include `Material`, `Method`, `Method_family`, `Loading_type`, `Flag`, `Metric_mode`, `Nf_exp`, `Nf_expected`, `CP_value`, `DP_fit`, `Error_ln` and `Error_ln_dp`. `Flag=0` identifies calibration points. `Metric_mode=Nf` compares predicted and experimental cycles, whereas `DP_DIFF` compares damage parameters when the calibration slope is nearly flat (the runner switches once its slope parameter exceeds 15). These field names must be preserved when reporting is extended.

New exports, in addition, contain `Error_log10_dp`, `Implementation_revision` and `Method_reference`, and end with the observation identity columns `Test_status`, `Specimen_id`, `Case_id`, `Observation_id` and `Dataset_fingerprint`. In damage space, comparisons are made through `log10(DP_fit/CP_value)` at every slope. The harmonic conventions, the corrected methods and the excluded historical results are covered in [method-audit.md](method-audit.md).

## Development conventions and possible interoperability with FatPy

The [FatPy contributing](https://faberorg.github.io/FatPy/development/contributing/), [testing](https://faberorg.github.io/FatPy/development/testing/) and [code-style](https://faberorg.github.io/FatPy/development/code_style/) guides were reviewed by upstream commit 0105b69 (PR #9); the new calibration uses typed interfaces and one function per step. Numerical theory and usage remain in their technical documents. Here, the pytest suite, the `multifat` src layout and the black/ruff checks are retained; FatPy imports, packaging changes and repository-wide typing migrations are outside this change.

Plane-based methods and structural-mechanics utilities are documented as separate elements in the current [FatPy repository](https://github.com/faberorg/FatPy). The independent harmonic amplitude function (`multifat.models.utils.shear_amplitude`), tensor transformations and the plane/method evaluation interfaces are potential components for a future WG6 exchange. The similarity is architectural; API compatibility has not been confirmed. An exchange would require agreement on tensor/component order, tangent bases, harmonic phase conventions, units, amplitude versus range, output quantities and calibration provenance. No FatPy source or dependency is introduced.