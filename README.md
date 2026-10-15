# FABER WG4.3 — Help build a traceable multiaxial fatigue library

## About the Project — FABER WG4.3

This work is developed in the context of **FABER Working Group 4.3 (WG4.3)** to support the **preparation of a scientific review article on multiaxial fatigue assessment methods**. The article is not presented here as already published. See the [official WG4.3 activities](https://faber-cost.eu/wg4-fatigue-estimation-categories/wg4-3-multiaxial-high-cycle-fatigue/).

The repository combines two purposes: **scientific review and comparison**—identify, classify, document, implement and compare published criteria—and **open collaborative development**, where researchers contribute implementations, numerical benchmarks and independent validation. We invite **missing criteria, source-faithful repairs and validation cases** across all methodological families.

Multiaxial fatigue depends on interacting stress/strain components, phase shifts, mean stresses and material response. Published methods use different physical assumptions, plane rules, amplitude definitions and fatigue-life relations. A shared collection makes those differences explicit and helps researchers compare results without treating one numerical convention as universal.

**Present scientific scope:** constant-amplitude multiaxial fatigue, principally HCF, of **plain/smooth geometries**—without explicit geometrical stress concentrations, notches, cracks or significant stress gradients. Both proportional and non-proportional loading are relevant where supported by each method, irrespective of whether its formulation is stress-, strain-, energy-, plane-, invariant- or otherwise based.

**Current software:** single-frequency harmonic stress cycles, elastic strains inferred from stress, damage-parameter assessment, empirical life fitting where valid, and CSV/plot comparisons. **Potential future extensions**, not existing capabilities or formal commitments, include variable-amplitude and richer periodic histories, notches/gradients, complex geometries, structural applications and additional fatigue phenomena. Wider methods remain catalogued but are marked separately from the current phase.

## Help us implement missing fatigue methods

Before starting from scratch, consult the [external source-code inventory](docs/EXTERNAL_IMPLEMENTATIONS.md). It distinguishes inspected source, related/unverified leads and cases with no accessible source identified. A public repository is not automatically licensed for reuse; external code is neither integrated nor scientifically validated merely by being linked here.

Start with the [contribution index](docs/METHOD_INDEX.md), which lists every missing candidate by family, references, loading scope and development disposition. You can implement a criterion, complete a disabled formulation, review equations, supply a missing original reference, improve numerical robustness or validate an existing implementation.

<!-- METHOD_NAVIGATION_START -->

**97 missing method candidates** are available to explore: 85 have preliminary A/B feasibility (a new criterion or manageable extensions). Pick by scientific interest and available references/data; an off-roadmap proposal is welcome.

Browse contribution opportunities by family: [Critical plane](docs/METHOD_INDEX.md#family-critical-plane) · [Energy based](docs/METHOD_INDEX.md#family-energy-based) · [Integral and hybrid](docs/METHOD_INDEX.md#family-integral-and-hybrid) · [Invariant based](docs/METHOD_INDEX.md#family-invariant-based) · [Mesoscopic and damage](docs/METHOD_INDEX.md#family-mesoscopic-and-damage) · [Nonlocal and gradient](docs/METHOD_INDEX.md#family-nonlocal-and-gradient) · [Probabilistic](docs/METHOD_INDEX.md#family-probabilistic) · [Specialized](docs/METHOD_INDEX.md#family-specialized) · [Strain based](docs/METHOD_INDEX.md#family-strain-based) · [Stress based](docs/METHOD_INDEX.md#family-stress-based) · [Tensor and path based](docs/METHOD_INDEX.md#family-tensor-and-path-based).

**Available in the current API:** [FS](METHODS.md#i_fs), [FIN](METHODS.md#i_fin), [SWT](METHODS.md#i_swt), [MATAKE](METHODS.md#i_matake), [MCD](METHODS.md#i_mcd), [MGSE_YU](METHODS.md#i_mgse_yu), [MGSE_ZHU](METHODS.md#i_mgse_zhu), [MSWT](METHODS.md#i_mswt), [MKBM](METHODS.md#i_mkbm), [LIU2021](METHODS.md#i_liu2021), [LI](METHODS.md#i_li), [GSE](METHODS.md#i_gse), [GSA](METHODS.md#i_gsa), [BP](METHODS.md#i_bp), [CAIM](METHODS.md#i_caim). Each link states the implemented scope and evidence; active does not automatically mean source completeness is established.

<!-- METHOD_NAVIGATION_END -->

**Choose a method → Read its original reference → Inspect requirements → Find or propose an Issue → Implement → Test and validate → Submit a PR.**

1. Select a permanent method ID in the [complete catalogue](METHODS.md) or [suggested roadmap](ROADMAP.md). Off-roadmap methods are welcome.
2. Follow its DOI or traceable citation; check the exact formulation, version and errata. Unverified references are labelled explicitly.
3. Read its inputs, missing components, reusable code and validation needs. Obtain the original full text and suitable numerical data before coding.
4. Use its **Search Issues** link to avoid duplication, then **Propose task** or use an existing [prepared brief](docs/contribution-issues/README.md). Prepared briefs are documents, not open Issues.
5. Follow the [ten-step contribution guide](CONTRIBUTING.md), implement the bounded formulation, add independent checks and submit a PR linked to the method ID.

## Current implementation coverage

[**Complete method catalogue**](METHODS.md) · [**All contribution opportunities**](docs/METHOD_INDEX.md) · [**Prioritized roadmap**](ROADMAP.md) · [**Count reconciliation**](docs/COUNT_RECONCILIATION.md)

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

**Complete** means essential components are implemented and tested for the explicitly named **repository scope**, which may include documented adaptations. **Partial** means known essential gaps; those archived methods are disabled. **Requires review** means active code exists but source completeness is not established. **Validation is independent:** no method is currently claimed independently validated against published or experimental datasets merely because its tests pass.

Each record has one primary family for counting and may have secondary classifications. For example, an energy criterion can also use a critical plane. The [catalogue](METHODS.md) records those overlaps, original versus adapted formulations, `_ext` variants, code, tests and missing work.

These counts cover the complete catalogue, including potential future geometry/loading tracks. Check each record’s **current FABER phase** before proposing near-term work; catalogue inclusion is not a claim of present plain-geometry compatibility.

## Why are there about 100 candidates but only about 20 roadmap entries?

<!-- METHOD_RECONCILIATION_START -->

The catalogue contains **97 missing method/scoped candidates**; the roadmap selects **22** for an initial, dependency-aware programme. The other **75 remain available for proposals**. The complete index retains **161 research records**, including **117 identifiable method/scoped records** and **44 bundles, related sources, unresolved overlaps/leads and wider workstreams** outside that progress denominator. These are not 161 independent fatigue theories.

<!-- METHOD_RECONCILIATION_END -->

The 51-publication FABER review and extended searches contain original criteria, modifications, comparisons and duplicate/related papers. An exact final count of independent theories remains unresolved where original sources or equivalence checks are missing. The [reconciliation](docs/COUNT_RECONCILIATION.md) accounts for every ID and its selection, deferral or relationship; no candidate disappears because it is difficult or outside the critical-plane family.

## Browse methods and evidence

Use the [method index](docs/METHOD_INDEX.md) to browse **available API methods**, **repairs**, **source reviews**, **missing methods by family**, **validation evidence** and **loading scope**. The [full catalogue](METHODS.md) provides authors, references/DOIs, principles, material parameters, outputs and known limitations without requiring source-code browsing. The [structured CSV](docs/catalogue/methods.csv) supports sorting/filtering; [JSON](docs/catalogue/methods.json) is the maintained source of truth.

The [roadmap](ROADMAP.md) explains its selection criteria, dependencies and how to propose another method. The [research provenance](docs/research/README.md) preserves the original review, 51/51 publication dispositions, assessment and saved bibliographic evidence. A matching DOI identifies a publication; it does not establish a complete reproducible algorithm.

## Quick start

Use Python 3.10+ from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python 1_run_material.py --model BP --material AISI316L --results-dir Results/current --no-plots
MPLBACKEND=Agg python -m unittest discover -s tests -v
```

The workbook run writes a new result under `Results/current/`. It reports when optional material properties are estimated. For a minimal direct calculation using the current API, run:

```python
import numpy as np
from fatigue.models.registry import get_models

model = get_models(["BP"])[0]
zero = np.zeros((3, 3))
axial_amplitude = np.diag([240.0, 0.0, 0.0])
result = model.evaluate_case(
    S0=axial_amplitude, S1=-axial_amplitude, E0=zero, E1=zero,
    params={"Sigm1": 240.0, "Taum1": 145.0, "Sig0": 400.0, "Tau0": 265.0},
    harmonics={"S_mean": zero, "S_sin": axial_amplitude, "S_cos": zero},
)
print(f"BP utilization: {result.values['']:.6f}")  # 1.000000
```

These illustrative strengths are in MPa: reversed strengths are amplitudes; R=0 strengths are maximum stresses. BP is stress based; the strain arguments are unused here. This calculation is an analytical fatigue-limit check, not an experimental life prediction. See [BP/CAIM usage and conventions](docs/bp-caim-usage.md) for parameter estimates and integration details.

## Software map

| Component | Responsibility |
|---|---|
| `0_calibrate_material_params.py`, `1_run_material.py`, `2_compare_results.py` | Calibrate the selected model, run workbook cases, compare exported results |
| `fatigue/imp/`, `fatigue/planes/` | Import loading/material data and sample candidate planes |
| `fatigue/models/` | Criterion implementations, plane adapter, registry and source metadata |
| `fatigue/eval/`, `fatigue/report/` | Evaluate/calibrate damage curves and export results |
| `tests/` | Analytical/regression cases and optional material sweep |

A physical harmonic cycle is represented by mean, sine and cosine **3×3 tensors**. The workbook importer derives isotropic elastic strains. Plane methods return damage and a selection metric; case-level methods can use the full harmonic tensors directly. Reuse projections, plane searches and sphere quadrature only when they match the original criterion. Details are in [architecture](docs/architecture.md) and [adding methods](docs/adding-methods.md).

## Scope and maturity

General nonsinusoidal periodic paths, constitutive plasticity, mesh/control-volume processing and probabilistic calibration are future work. Legacy CP shear amplitudes use an RSS ellipse convention; BP/CAIM use the major semi-axis. Material fallbacks and repository adaptations are explicit in the [method audit](docs/method-audit.md). Keep these differences when reproducing a paper.

Historical `Results/*.csv` predate the numerical audit and are excluded from current comparisons by default. Recalibrate affected parameters before ranking methods. Current exports preserve `log10(DP_e/DP)` for all slopes; unreliable life inversions remain suppressed. Run `python 2_compare_results.py --results_dir Results/current --out_dir Results/Comparison` to compare fresh runs.

The repository is public and welcomes scientific contributions. A software license has not yet been selected, so reuse terms still need a maintainer decision. No copyrighted article PDFs are distributed here.
