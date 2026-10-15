# WG4.3 — Multiaxial fatigue assessment

Research Python application for implementing, comparing and progressively validating multiaxial fatigue criteria. The working scope is constant-amplitude high-cycle fatigue, including proportional and phase-shifted non-proportional loading. Critical-plane, invariant, integral, energy, mesoscopic, probabilistic and nonlocal candidates are tracked without treating every publication as a distinct method.

The current workflow imports material workbooks, builds physical single-frequency stress/elastic-strain harmonics, evaluates 13 critical-plane and two direct integral/hybrid models, calibrates damage curves and exports comparisons. General sampled periodic paths, constitutive plasticity, FE spatial processing and spectral fatigue are future infrastructure, not current capabilities.

## Methods and contribution opportunities

- [Full method catalogue](METHODS.md): scoped completeness, independent validation status, references, source/tests and missing tasks.
- [Suggested roadmap](ROADMAP.md): a diverse implementation sequence and exact papers to retrieve.
- [Contributing](CONTRIBUTING.md): interfaces, scientific evidence and completion checklist.
- [Prepared Issue briefs](docs/contribution-issues/README.md): actionable repairs, source checks and initial additions.
- [Structured catalogue JSON](docs/catalogue/methods.json) and [generated CSV](docs/catalogue/methods.csv).
- [Research provenance and all 51 review publications](docs/research/README.md).

<!-- METHOD_PROGRESS_START -->

| Primary family | Fully implemented¹ | Partial | Missing | Requires review | Total |
| --- | --- | --- | --- | --- | --- |
| Critical plane | 3 | 1 | 14 | 0 | 18 |
| Energy based | 3 | 2 | 15 | 3 | 23 |
| Integral and hybrid | 2 | 0 | 7 | 0 | 9 |
| Invariant based | 0 | 1 | 12 | 0 | 13 |
| Mesoscopic and damage | 0 | 1 | 7 | 0 | 8 |
| Nonlocal and gradient | 0 | 0 | 7 | 0 | 7 |
| Probabilistic | 0 | 0 | 5 | 0 | 5 |
| Specialized | 0 | 0 | 3 | 0 | 3 |
| Strain based | 2 | 0 | 11 | 2 | 15 |
| Stress based | 0 | 0 | 13 | 0 | 13 |
| Tensor and path based | 0 | 0 | 3 | 0 | 3 |
| **TOTAL** | 10 | 5 | 97 | 5 | 117 |

<!-- METHOD_PROGRESS_END -->

“Fully implemented” applies only to the named **repository scope**, including explicitly documented adaptations. It is independent of scientific validation. “Requires review” records active code whose original-formulation completeness is not established. Counts use one primary family per identifiable method/scoped candidate; bundles, unresolved overlaps and research workstreams remain searchable but are excluded from totals. They are not counts of independent fatigue theories.

No method is currently labelled independently validated against published or experimental datasets. Analytical limits, regression tests and CAIM's separate angular calculation are described in the catalogue. Five flawed archived implementations remain disabled. Existing `_ext` variants are documented within each method and are not counted again.

## Setup

Use Python 3.10 or newer from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Run

1. Edit `MATERIAL_NAME` and `MODEL_NAME` near the top of `1_run_material.py`.
2. Run `python 1_run_material.py`. It reads a workbook in `Experimental_Data/` and writes a CSV in `Results/`.
3. Run `python 2_compare_results.py` to compare CSV results and generate figures and tables in `Results/Comparison/`.
4. Optionally run `python 0_calibrate_material_params.py` to print suggested material parameters. This does not modify the workbooks.

The existing CSV files in `Results/` are historical outputs from the supplied archive. They predate the numerical audit and are excluded from current comparisons by default; `--include-legacy` explicitly includes retained methods' historical outputs. `Results/Comparison/` contains generated plots and is excluded from Git.

## Add a fatigue method

Implement a method in `fatigue/models/cp_methods/`, `fatigue/models/invariant_methods/`, `fatigue/models/energy_based_methods/`, or `fatigue/models/integral_methods/`, then register it in `fatigue/models/registry.py`. See [adding a method](docs/adding-methods.md) for the expected interfaces and naming conventions. The [architecture notes](docs/architecture.md) describe the data flow and CSV fields.

### Böhme–Papuga (BP) and CAIM

Set `MODEL_NAME = "BP"` or `MODEL_NAME = "CAIM"` in `1_run_material.py`. Both use `Sigm1` and `Taum1` (the R=−1 tensile and torsional fatigue limits). If available, add `Tensile fatigue strength R=0` and `Torsional fatigue strength R=0` columns to the workbook `Summary` sheet. These are **maximum** stresses for zero-to-maximum loading. When absent, the runner uses the estimates in Eqs. (1)–(2) of [Böhme, Papuga & Lange (2026)](https://doi.org/10.1111/ffe.70244), based on tensile strength and the R=−1 limits, and prints the resulting values. The BP damage parameter is dimensionless and uses a sphere integral of shear and normal amplitudes and mean stresses. CAIM is a newer, distinct hybrid formulation from the same paper: its amplitude term uses a critical-plane maximum with different coefficients, while its mean-stress term remains a sphere integral. Both are retained for comparison; neither needs an `_ext` suffix. CAIM follows the supplied `damage_criteria_CAIM.m` equations, including the piecewise normal-amplitude coefficient and clipping negative squared damage to zero.

Both implementations support single-harmonic stress histories and compute shear amplitude as the major semi-axis of the shear ellipse. Sphere integration uses 24 × 48 Gauss–Legendre/azimuth samples. CAIM refines multiple sampled maxima numerically; it does not reproduce the MATLAB angular grid exactly or guarantee an exact global maximum. The focused tests cover analytical loading limits and comparison with an independent dense angular evaluation of the supplied equations.

## Layout

| Path | Purpose |
| --- | --- |
| `fatigue/imp/` | Excel data import |
| `fatigue/planes/` | Critical-plane sampling |
| `fatigue/models/` | Method implementations, adapters, and registry |
| `fatigue/eval/` | Calibration and evaluation |
| `fatigue/report/` | CSV export |
| `Experimental_Data/` | Supplied material workbooks |
| `Results/` | Supplied result CSVs and new output |

The experimental workbooks and historical CSVs are preserved. Numerical corrections and disabled-method decisions are recorded in the [method audit](docs/method-audit.md); original articles are mapped in the [bibliography](docs/bibliography.md).

## Audited runs and damage-space comparison

The default model is `FS_ext`. `CARSPA`, `DANGVAN`, `OTT`, `SWTD`, and `ZHU_EDP` are disabled with reasons in the audit. Each retained model has an original-source reference, and generated CSVs record its source and implementation revision.

```bash
python 1_run_material.py --model CAIM --material AISI316L --results-dir Results/current --no-plots
python 1_run_material.py --model BP --material AISI316L --results-dir Results/current --no-plots
python 2_compare_results.py --results_dir Results/current --out_dir Results/Comparison
python -m unittest discover -s tests -v
# Optional full material sweep (64 runs; writes into a separate directory):
python tests/run_material_validation.py /tmp/fatigue-audit
```

Every run includes `Error_log10_dp = log10(DP_e/DP)`, including flat and shallow master curves. Here `DP_e` is `DP_fit`, the fitted curve evaluated at the experimental life. Damage-space plots and statistics now include all slopes. Life predictions remain suppressed where curve inversion is unreliable. Legacy natural-log columns retain their previous definitions.

Recalibrate model constants affected by equation corrections before interpreting new method rankings. The audit identifies provisional source checks and the limits of the elastic/harmonic workflow.
