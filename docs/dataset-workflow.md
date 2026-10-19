# Revised experimental inputs and comparison subsets

The user explicitly authorised publication of the twelve supplied workbooks,
including raw observations and embedded content, on 19 October 2026. The active
collection is installed without rewriting measured cells. The installer remains
available for reproducing this migration from the original attachment.

```bash
python tools/install_revised_dataset.py exp_data.zip
python tools/install_revised_dataset.py exp_data.zip --apply
```

The October 2026 collection contains twelve revised workbooks. The active folder
also retains Al7075_T6, which was absent from that collection. Previous active
workbooks are preserved byte for byte under
`Experimental_Data/archive/pre-dataset-migration/`. The importer reads only the
active folder. Historical JSON records and reference result CSVs are unchanged.

## Import and provenance

`fatigue/imp/schema.py` contains explicit header aliases. An ordering prefix such
as `6_` is removed from a filename to obtain the stable ID `42CrMo4_QT`. Alloy,
treatment and legacy axial/bending suffixes are not merged automatically. Repeated
canonical IDs are rejected. A contradictory Summary identity blocks assessment
without rewriting the measured workbook.

Summary properties are read from the named Average cell when present, otherwise
from the row labelled Average. Source property rows and their references remain
available as `source_property_rows`. Missing properties remain `None`. Strain is
undefined when valid E and nu are unavailable; stress observations remain imported.
Only methods requiring strain or elastic constants are blocked by that condition.

Dataset columns are selected by header, independently of their positions.
Supported aliases include `Amplitute`/`Amplitude`, and the previous BENDING stress
headers for the local longitudinal surface stress. Forces in N and moments in
Nmm are retained as metadata. They are not substituted for stresses in MPa and no
new geometry conversion is introduced. This preserves the existing stress-based
reconstruction, including tensorial shear strain `epsilon_xy = tau_xy/(2G)`.

The radial and torsional phases are expressed relative to the axial phase. The
previous format defaults to zero phase where its optional columns are absent.
Different known frequencies in active components are flagged because the current
model supports a single frequency. The source frequency text is preserved, including
ranges. Unknown frequencies are not replaced with a numerical frequency.

For the revised format, a missing stress component is reported as unavailable
loading information rather than a usable zero. Legacy Null stress components
retain their former inactive-component convention. Known failures and run-outs
remain distinct; unknown status is excluded from analysis. Notched rows are
recorded in `scope_exclusions`; invalid cycles and non-finite loading inputs are
recorded separately in `excluded_observations`. Complete source workbooks remain
available even when no plain cases are eligible.

## Input issues requiring source clarification

| Material | Current restriction |
|---|---|
| CX18 | The filename conflicts with Summary entries naming 30NCD16. No XC18/30NCD16 alias is inferred. |
| Ti6Al4V | A Summary source names Ti64Al4V. Identity must be confirmed before pooling its observations. |
| AISI316L | The average axial fatigue strength combines different stress ratios. Methods requiring Sigm1 are blocked until a consistent reversed strength is supplied. Other methods can proceed if their own inputs and calibrations are available. |
| En3B and GJS600 | The revised observations are marked notched and therefore outside the present plain-specimen analysis. |
| Several added materials | nu is missing and/or all observations are run-outs. These conditions prevent strain reconstruction or ordinary master-curve fitting where required. |

The generated migration audit records comparison with the seven supplied old
workbooks, including header changes, properties, source rows and shared stresses. The detailed
source-property export is generated locally by the audit tool rather than
distributed with the workbooks.
The supplied old collection and the previous repository inputs are different
snapshots. Do not assume that the same filename gives the same calibration inputs.
The 56 shared 42CrMo4_QT and 44 shared AISI316L observations retain their supplied
stress tensors. Material properties can nevertheless differ, changing reconstructed
strains and requiring a new calibration. The previous Ti6Al4V axial and bending
files remain archived rather than being declared equivalent to the new pooled file.

## Calibration and assessment checks

`fatigue/eval/eligibility.py` centralises method-specific requirements from the
implemented model interfaces and conditional dependencies. The five fitted method
coefficients remain JSON inputs. Missing stored results are distinguished from
missing information needed to attempt calibration. `can_calibrate` indicates that
preflight requirements are satisfied; a numerical fit can still fail and must be
reported separately.

The existing Uniform Material Law approximation is allowed only for explicitly
identified steels with its required inputs. Its use is reported. Non-steels need
the fatigue properties required by the implementation. Supplied invalid parameters
are rejected rather than replaced. The BP/CAIM R=0 estimates retain their existing
formulation and are reported explicitly.

Script 0 processes each material-method combination independently and saves only
successful results. Script 1 checks the requested combination and returns an
informative warning if it is unavailable. Script 3 continues after skipped or
failed combinations and exports the reasons. Assessment never silently recalibrates.

```bash
# Inspect all current material-method combinations using the standard settings.
python 3_review_subsets.py --report-dir Results/Comparison/eligibility

# Explicitly fit the requested methods, then assess them.
python 0_calibrate_material_params.py --material 42CrMo4_QT --models BP SWT --status-file Results/Comparison/calibration-status.json
python 3_review_subsets.py --materials 42CrMo4_QT GGG60 CX18 --models BP SWT --run --results-dir Results/current --report-dir Results/Comparison/eligibility
```

Use identical plane-grid and scatter settings for calibration and assessment.
Script 3 accepts `--n1`, `--n2` and `--stdnum`; Script 1 retains its existing
configuration constants. The existing explicit `--calibration-id` selection in
Script 1 is unchanged. Renaming a workbook with an ordering prefix does not affect
calibration compatibility; changing relevant properties or failure histories does.
Adding run-outs alone does not change a failure-only input fingerprint.

Each eligibility export includes JSON detail, a long CSV, a method-material matrix
and per-method material/observation counts. `prediction_available` describes input
and stored-calibration readiness. `quantitative_comparison_available` additionally
requires failures. `life_comparison_available` requires an invertible curve under
the existing slope rule. Flat curves retain their existing damage-space comparison.
When `--run` is used, actual exported prediction and failure/run-out counts are
recorded separately. Preflight availability is not a numerical accuracy ranking.
The checked-in matrix describes the supplied revised collection using the retained standard-grid
records; regenerate it after changing that collection; example calibrations generated under temporary folders are not installed
as production calibrations.

## Common failure observations

Result CSVs add `Case_id`, `Observation_id` and `Dataset_fingerprint`. A case is
identified by its specimen/source and stress history. Observation identity also
includes the cycle count, status and replicate occurrence. Dataset fingerprints
prevent mixing changed failure histories or material inputs. Censored observations
never enter conventional error statistics.

Script 2 writes `individual_availability.csv` and `common_subsets.json` for
pairwise and selected-group overlaps, separately for life and damage metrics.
Common observations must have a finite value for the selected metric in every
method. Legacy results without usable IDs cannot be matched automatically.
Ambiguous specimen/life provenance and duplicate method-observation records cause
a controlled error rather than an inferred match.

```bash
# Compare only evaluation observations shared by the selected methods.
python 2_compare_results.py --results_dir Results/current --out_dir Results/Comparison/common --common-methods BP SWT --comparison-metric life --flag_filter other

# Use damage-space errors where life inversion is unavailable.
python 2_compare_results.py --results_dir Results/current --out_dir Results/Comparison/common-damage --common-methods BP SWT --comparison-metric damage --flag_filter other
```

The selected rows and their identities are saved in
`selected_common_observations.csv`, with the selection described in
`subset_definition.txt`. Original per-method CSVs are unchanged. Run-outs remain
available in individual plots with the existing open-marker and censoring-arrow
conventions, but the common quantitative subset contains failures only.
Design observations retain `Flag=0`; use `--flag_filter other` to exclude those
fitting observations. Neither a common subset nor a successful regression test
constitutes independent experimental validation.

## Reproducible checks

Run `MPLBACKEND=Agg python tools/run_tests.py`. The original numerical fixtures
continue to use the archived repository inputs. New tests exercise revised headers,
missing properties, status handling, conditional method requirements, compatibility
checks, batch continuation and matched observation subsets. The revised 42CrMo4_QT
example fits BP/SWT, exports 45 failures and 11 censored observations per method,
and compares the same 45 failures in both methods when design rows are included.
A reduced 3 by 6 plane grid tests execution only; it is not a converged scientific
calibration for the review paper.

Regenerate a dataset audit with
`python tools/audit_dataset_migration.py --old-dir PATH_TO_OLD_WORKBOOKS`.
Keep subsequent milestones and remaining source questions in the single
[development checkpoint](audit-checkpoint.md).

All 58 automated tests execute with the revised collection installed, including
the three full-collection checks previously skipped while its publication was
pending. These checks remain optional when a contributor works without that
collection.
