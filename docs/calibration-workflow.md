# Calibration history and experimental run-outs

Excel supplies the material and experimental inputs. Script 0 determines method
coefficients and master curves, stores them in JSON and preserves earlier records.
Equivalent reruns reuse the existing record rather than creating a duplicate.
Script 1 loads a compatible record, evaluates cases and exports results. Script 2
compares results and produces plots. No coefficient transfer through Excel is required.
This workflow retains the present FABER WG4.3 scope of constant-amplitude loading
and smooth/plain geometries. It does not introduce a new fatigue formulation or
censored-data regression.

## Calibration stages

The previous workflow had two distinct fitting stages. Script 0 optimised five
method coefficients on uniaxial tension and torsion failures, with the existing
load-ratio fallback rules. Script 1 separately fitted the selected damage–life
curve using reversed axial failures. Both stages are now initiated by Script 0.

| Quantity | Meaning and provenance | Storage |
|---|---|---|
| Elastic constants, yield/ultimate strengths, supplied fatigue strengths and strain-life properties | Material inputs, including existing optional-property estimates where explicitly reported | Excel |
| `K` | Existing ratio of fatigue strengths; not an optimisation output | Excel |
| `k_FS`, `k_FI`, `L_LI`, `k_MGSE`, `a_MSWT` | Dimensionless coefficients of the existing FS, Findley, Li, MGSE_ZHU and scalar MSWT implementations | JSON |
| `A`, `b`, `A_surv` | Master curve `DP = A*N**b` and its existing damage-space shift | JSON, separately for standard and `_ext` variants |
| `STD`, `STD_ln_DP`, `R2_log`, `n` | Fit diagnostics and number of usable failure observations | JSON |
| Plane grid, search bounds, refinement counts, selection tolerances and scatter settings | Numerical/calibration settings rather than material properties | JSON metadata and versioned procedure |
| `alpha_w`, `xi_ZHU` | Retired-model constants transferred from the former Summary; original provenance/units unverified | JSON legacy metadata; unused by active methods |

Coefficient-optimisation diagnostic curves and the downstream master curves are
different objects. They retain their own specimen populations and scatter settings.
The optimisation default is `stdnum=2`, while the analysis master-curve default is
`stdnum=0`, as before. The legacy optimisation report calls Findley `FI`; the registry
and master curves use `FIN`. `_ext` is a separate stored curve, not a new material.

```bash
# Fit the requested coefficient and both FS curve variants.
python 0_calibrate_material_params.py --material AISI316L --models FS
python 1_run_material.py --material AISI316L --model FS_ext --results-dir Results/current --plot-dir Results/current/plots

# BP/CAIM require no fitted method coefficients, but still need master curves.
python 0_calibrate_material_params.py --material AISI316L --models BP CAIM
python 1_run_material.py --material AISI316L --model BP --results-dir Results/current --no-plots
python 2_compare_results.py --results_dir Results/current --out_dir Results/Comparison
```

Omitting `--models` calibrates all active methods; omitting `--material` selects
all workbooks. Searches can be expensive. `--n1`, `--n2`, `--plane-stride`,
`--n-grid`, `--n-refine` and the two scatter settings are explicit CLI options.
Changing them is a numerical choice that must be reported. An optimisation without a finite objective, or an invalid required curve,
prevents a successful record from being written. No default coefficient is silently substituted.

## Record structure and units

Schema version 1 is checked by `validate_record` in
[`calibration_store.py`](../fatigue/eval/calibration_store.py). Files are written
through a temporary file and published atomically without replacing an existing ID.
Floating-point values retain Python/JSON round-trip precision. Required coefficients
and curve values must be finite. Undefined optional scatter or correlation diagnostics
are stored as `null`, with that convention recorded explicitly.

| Field | Content |
|---|---|
| `calibration_id`, `created_at`, `status`, `schema_version` | Unique ID, UTC timestamp, successful completion and schema identity |
| `material_id`, `material_name`, `material_condition` | Workbook-stem identity; unknown condition remains `null` |
| `source` | Workbook, Summary/Dataset sheets, workbook hash and original-archive link where applicable |
| `material_inputs`, `material_input_units` | Material inputs used by the model, separated from fitted coefficients |
| `parameters`, `parameter_units`, `parameter_origin` | Coefficients, units and whether they were optimised, explicitly reused or transferred |
| `curves` | Per-model standard/ext series, fits and references to selected observations |
| `design_observations` | Common specimen/source-row metadata stored once across methods and variants |
| `curve_units`, `damage_parameter_units` | Cycles, criterion-specific DP units and coefficient/exponent conventions |
| `optimisation` | Coefficient-search results, diagnostic fits, selected cases, fallback information and settings |
| `counts` | Available failures/run-outs/unknowns, invalid exclusions and actual observations used for fitting |
| `input_fingerprint`, `formulation_fingerprints` | Compatibility identities for material/failure inputs and numerical source |
| `procedure_version`, `implementation_revision`, `references`, `software` | Procedure and scientific/software traceability, including Git state |

The following excerpt comes from the initial AISI316L migration record. It is a
schema illustration, not a complete loadable record or a new optimisation result.
The [complete record](../Calibrations/AISI316L/20261016T112312876379Z_cee3997362e2.json)
includes all required fields, all 15 active methods and independent provenance.

```json
{
  "schema_version": 1,
  "status": "success",
  "material_id": "AISI316L",
  "parameter_origin": "Transferred legacy workbook values; original fitting settings unverified",
  "parameters": {"k_FS": 0.62, "k_FI": 0.28, "L_LI": 2.13, "k_MGSE": 0.5, "a_MSWT": 0.36, "alpha_w": 0.0, "xi_ZHU": 0.0},
  "counts": {"failure": 31, "runout": 13, "unknown": 0, "invalid_excluded": 0}
}
```

Stress inputs use MPa; strains are dimensionless with the existing tensorial versus
engineering-shear conventions. FS, MKBM, LIU2021, GSA, BP and CAIM return dimensionless
repository parameters. The other active methods return MPa-valued parameters under
these conventions. `b` is dimensionless, `N` is in cycles and `A`/`A_surv` have units
`DP * cycle**(-b)`. These are implementation units, not evidence that a repository
adaptation reproduces every component of the original publication.

## Selection and compatibility

Script 1 selects the most recent successful compatible record by declared UTC time,
then calibration ID. It does not use modification times or run Script 0 automatically.
`--calibrations-dir` selects another archive; `--calibration-id ID` selects a specific
historical record and still enforces compatibility. Script 0 can explicitly reuse
coefficients with `--reuse-calibration ID` and records the source ID. Its requested
model and settings must be present in that record.

Compatibility requires the material identity, material properties, failed-specimen
histories, model, plane grid, curve scatter setting, procedure version, implementation
revision and numerical source fingerprints to agree. Source hashes normalise line
endings and path separators. They include the selected criterion and shared numerical
helpers. Maintainers must increment the procedure version if fitting-selection rules
change. A corrupt record produces an error rather than silently selecting another file.

The input fingerprint excludes run-outs, unknown-status observations, specimen/row
IDs, workbook formatting and file timestamps. It conservatively includes all failed
observations because coefficient selection can broaden its load-ratio tolerance.
Consequently, changing a non-fitting failure may also require recalibration. Reordering
rows or adding/removing run-outs alone does not invalidate an existing record. The full
workbook hash is provenance only and is not the compatibility key.

The initial four migration records preserve the previous coefficients without claiming
their original fitting settings are known. Fresh optimisation can produce different
coefficients; that is a new calibration and must remain a separate historical record.
The transferred `alpha_w` and `xi_ZHU` values do not restore their retired models.

## Equivalent reruns

`calibration_signature()` computes a deterministic identity from the material and
failure-input fingerprint, numerical options, formulation fingerprints, fitted
values, fitting provenance and NumPy version. Timestamps, Git working state,
workbook formatting, source paths, row identifiers and censored-observation counts
do not distinguish equivalent results. Sequential reruns with equivalent content
return the existing file and its original ID. Changed numerical results or settings
create a new historical record. Existing IDs remain protected against overwriting.
No extra database or index file is used. Concurrent independent writers can still
produce equivalent records, so calibration exports should be run sequentially.

Reusing a record preserves its original source metadata and counts. Script 0
separately reports the current observation counts and those in the stored record,
so adding run-outs does not change the historical provenance or hide their current
exclusion. Compare the human-readable JSON metadata directly when reviewing two
historical calibrations. The signature is computed on demand, allowing existing
schema-version-1 files to remain readable without rewriting them.

## Run-out interpretation and plots

Only failures contribute to coefficient searches, regressions and master curves.
Central selectors and a defensive check in the generic fitting collector enforce this
policy. Run-outs retain the original loading tensors, specimen identity, source row
and recorded cycle count. Unknown status is not inferred from a large cycle count.
See [experimental inputs](../Experimental_Data/README.md) for the workbook convention.

Result CSVs add `Test_status`, `Specimen_id`, `Calibration_id` and `Calibration_file`.
The existing `Nf_exp` column contains recorded cycles; its run-out values are lower
bounds. Their ordinary life/damage errors and `DP_fit` are undefined. Script 2 also
masks these fields after reconstructing errors and excludes censored rows from
statistics, boxplots, distributions and damage-fit comparisons. CSVs without status
retain their historical failure-only interpretation; use explicit status for new data.

Run-outs appear as open circles with right-pointing arrows in damage–life and life
parity plots. The arrow indicates that the unknown failure life exceeds the recorded
abscissa. PNG and TikZ comparison exports retain this convention. These are qualitative
observations, not ordinary prediction-error measurements. `--hide-runouts` changes only
visualisation. Existing suppression of life inversion for flat, positive or excessively
shallow curves remains unchanged. Such cases retain the damage–life plot; saved parity
plots are omitted. No censored-data regression or survival-analysis model is added.

## Model output and fatigue-life comparison

The computational family does not determine the output quantity. In particular,
the current non-critical-plane BP and CAIM implementations return dimensionless
damage parameters, rather than fatigue lives. All 15 currently enabled base
methods retain their existing damage-parameter workflow.

| Model output | Pipeline behaviour | Comparison |
|---|---|---|
| `damage_parameter` (existing default) | Load the compatible JSON curve and retain the existing slope safeguard | Life parity when inversion is permitted; damage-space comparison otherwise |
| `life_cycles` | Use the predicted cycles directly, without fitting a master curve or applying its inverse | Life parity and failure-only life errors |
| `index` | Reject generic curve fitting and automatic life conversion | A separately documented relation is required before life comparison |

A cycle-valued case model declares `output_quantity = "life_cycles"` and returns
`CaseResult(values={"": N}, output_quantity="life_cycles")`, where `N` is finite,
positive and expressed in cycles, not reversals. Model and result declarations
must agree. Script 1 uses measured material inputs and does not require a damage
master-curve archive on this path. A future method requiring fitted coefficients
must first provide its own explicit, traceable calibration procedure. Those
coefficients must not be estimated by fitting predicted lives to observed lives.

CSV rows use `Metric_mode=Nf_direct`. `Nf_expected` contains the native prediction,
while `CP_value`, `DP_fit` and damage errors remain undefined. No specimens are
labelled as master-curve design points. Run-outs remain lower-bound observations
in the parity plot and contribute no ordinary error. Script 2 accepts these CSVs
alongside the existing results. This interface is tested with a synthetic model;
it does not introduce or scientifically validate a new fatigue criterion.

## Verification boundary

The test suite covers JSON precision/history, required fields, incompatible inputs,
failure-only optimisation, generic curve fitting, explicit status import, error masking,
plots and Script 0 → JSON → Script 1 integration. The pre-change optimisation fixture
uses two specified planes for a bounded software regression, not a recommended scientific
plane search. The 64-run comparison reproduces all 3,936 original failed-specimen rows
with zero observed numerical difference and adds 672 run-out rows. Calibration and
software regression remain distinct from independent scientific validation.
