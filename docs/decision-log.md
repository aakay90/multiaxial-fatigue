# Decision Log

This log records architectural, numerical, and data decisions made during the development of
`multifat` (the carry-forward of `andreachiocca/multiaxial-fatigue`). Each decision is assigned a stable
reference identifier (`d0NN`) cited across commit messages, code docstrings, data overlays, and audit
ledgers.

---

## Decision Index

| Ref | Date | Status | Topic | Summary |
|---|---|---|---|---|
| [`d001`](#d001) | 2026-10-15 | **Active** | Fork baseline | Established `dev/tg-carry-forward` based on upstream `e70a8af`. |
| [`d011`](#d011) | 2026-10-15 | **Active** | IP boundary | Third-party GPL code (CPOpt, FS-Sol, etc.) may not be ported directly; implementations must be independently derived from papers. |
| [`d036`](#d036) | 2026-10-18 | **Active** | Provenance N1 | Corrected 42CrMo4 `Plain_multiaxial_9` torsional phase to $0^\circ$ (proportional PP loading). |
| [`d037`](#d037) | 2026-10-18 | **Active** | MSWT weighting | Converted parameter $a_{\mathrm{MSWT}}$ via $a' = a / (2 - a)$ to match Jiang (2000) / Zhu (2018) printed weighting without altering predicted lives. |
| [`d038`](#d038) | 2026-10-18 | **Active** | Provenance N6/N8 | Corrected AISI 316L non-proportional phase to $90^\circ$ and appended 8 omitted Janssens Table 4 test specimens. |
| [`d040`](#d040) | 2026-10-18 | **Active** | Reference outputs | Archived historical reference CSVs into `Results/archive/pre-audit/` rather than committing 170+ regenerated files. |
| [`d041`](#d041) | 2026-10-18 | *Reversed* | Maintenance logs | Originally deleted `docs/audit-checkpoint.md`; reversed when upstream maintainer requested tracking it. |
| [`d042`](#d042) | 2026-10-18 | *Superseded* | MMMH mean stress | Kept MMMH unregistered pending Mertens references; superseded when endurance limit formulation was verified and registered. |
| [`d043`](#d043) | 2026-10-18 | **Active** | Banvillet G26 | Implemented closed-form tension-torsion index; kept unregistered pending rotating-bending limits and specimen geometry in workbooks. |
| [`d044`](#d044) | 2026-10-18 | *Superseded* | Project licence | Held licence choice open between MIT, BSD, Apache, and GPL-3.0; superseded by `d071`. |
| [`d046`](#d046) | 2026-10-18 | **Active** | Output paths | Configured `multifat-run` default results directory to `Results/current/`. |
| [`d047`](#d047) | 2026-10-18 | **Active** | Point kernels | Retained uncalibrated models (G24, G26, G29, G30, N34) as modular functions with missing inputs recorded in the catalogue. |
| [`d050`](#d050) | 2026-10-18 | **Active** | Release readiness | Closed Phase 4 public-release preparation milestone. |
| [`d052`](#d052) | 2026-10-19 | **Active** | Pipeline design | Retained unified pipeline architecture (evaluating missing constants in one pass) rather than upstream stateful multi-script workflow. |
| [`d054`](#d054) | 2026-10-19 | **Active** | Dataset merge | Integrated upstream revised collection (`71eaac3`, 12 numbered workbooks) while retaining unnumbered `Al7075_T6.xlsx`. |
| [`d055`](#d055) | 2026-10-19 | **Active** | Batch workbooks | Created `14_42CrMo4_Reis.xlsx` and `15_Ti6Al4V_Berto.xlsx` to isolate distinct metallurgical batches and printed constants. |
| [`d056`](#d056) | 2026-10-19 | **Active** | AISI 316L data | Restored bulk $E = 193\,\mathrm{GPa}$, $\nu = 0.30$, cleared XRD lattice constants, fixed $90^\circ$ phase, and appended Table 4 tests. |
| [`d057`](#d057) | 2026-10-19 | *Refined* | Fatigue index error | Defined fatigue index error for run-out-only datasets ($FI = DP/DP_{\mathrm{ref}} - 1$, Böhme & Papuga 2024); refined by `d063`. |
| [`d058`](#d058) | 2026-10-19 | **Active** | Calibration records | Supported upstream `Calibrations/` JSON records via `--constants FILE`. |
| [`d059`](#d059) | 2026-10-19 | **Active** | Steel Poisson ratio | Set $\nu = 0.30$ (Dubbel 2004) for steels missing Poisson's ratio in Summary tables (`2_CX18`, `3_25CrMo4`, `4_30NCD16`, `7_982FA`). |
| [`d061`](#d061) | 2026-10-19 | **Active** | Braun mean stress | Restored $\sigma_m = \sigma_a$ on Braun $R = 0$ plain rows in `8_AISI316L.xlsx` to prevent exclusion under revised-format loader. |
| [`d062`](#d062) | 2026-10-19 | **Active** | Compute platform | Shifted numerical snapshot benchmarks to WorkstationUniPi due to i9-14900K hardware instability on WorkstationUniTN. |
| [`d063`](#d063) | 2026-10-19 | **Active** | Load-scaled index | Implemented load-scaled index $FI_{\mathrm{load}} = 1/s - 1$ where $DP(s \cdot \text{case}) = DP_{\mathrm{ref}}$ for quadratic/energy criteria (SWT). |
| [`d065`](#d065) | 2026-10-19 | **Active** | Branch management | Fast-forwarded main development line to `0e87e95` and pruned transient synchronization branches. |
| [`d066`](#d066) | 2026-10-19 | **Active** | Pipeline edge cases | Resolved deferred edge cases (Excel lock files `~$*`, duplicate material IDs, non-finite values). |
| [`d067`](#d067) | 2026-10-20 | **Active** | Upstream PRs #8-#9 | Integrated harmonic Findley evaluation (`fin_harmonic.py`) and configurable calibration options. |
| [`d068`](#d068) | 2026-10-20 | **Active** | Findley amplitude | Added `--shear-amplitude-algorithm` to `multifat-calibrate`; default remains legacy production MCE. |
| [`d069`](#d069) | 2026-10-20 | **Active** | MCC plane rule | Routed Findley MCC calibration through the refined plane search (`FindleyMCC`, `longest_chord` rule). |
| [`d070`](#d070) | 2026-10-20 | **Active** | Calibration guard | Enforced rejection of non-MCE calibration records when loading through `--constants` in production pipeline. |
| [`d071`](#d071) | 2026-10-22 | **Active** | MIT licensing | Formally relicensed `multifat` under the MIT License, superseding `d044`. |

---

## Detailed Records

### d001
* **Date:** 2026-10-15
* **Topic:** Carry-forward fork baseline
* **Status:** Active
* **Decision:** Establish `dev/tg-carry-forward` as an independent development branch starting from upstream commit `e70a8af`.
* **Rationale:** Preserves clean upstream provenance while restructuring into a modern `src/` layout with comprehensive method verification.

### d011
* **Date:** 2026-10-15
* **Topic:** Intellectual property and clean-room implementation
* **Status:** Active
* **Decision:** Code from GPL-3.0 repositories authored by collaborators (including CPOpt, FS-Sol, FI-Sol, SeAn-CP, and ECP) may not be ported directly into `multifat`.
* **Rationale:** Ensures clean IP provenance. All multiaxial fatigue criteria must be independently derived and verified directly from original scientific publications.

### d036
* **Date:** 2026-10-18
* **Topic:** 42CrMo4 proportional loading correction (Finding N1)
* **Status:** Active
* **Decision:** Set torsional phase to $0^\circ$ for row `Plain_multiaxial_9` in `42CrMo4_QT.xlsx`.
* **Rationale:** Anes et al. (IJF 58 Table 3, PP case) and Anes et al. (FFEMS 37 Table 2, case 1) confirm this test was proportional (in-phase). It had been erroneously tagged as $90^\circ$ out-of-phase.

### d037
* **Date:** 2026-10-18
* **Topic:** MSWT parameter weighting definition
* **Status:** Active
* **Decision:** Convert workbook parameter $a_{\mathrm{MSWT}}$ to $a' = a / (2 - a)$ to match the printed Jiang (2000) Eq. (6) and Zhu (2018) Eq. (13) weighting.
* **Rationale:** The original code implementation used twice the shear weight relative to the published formulation. The algebraic mapping $a' = a / (2 - a)$ harmonizes the definition with the published literature while leaving predicted lives exactly unchanged.

### d038
* **Date:** 2026-10-18
* **Topic:** AISI 316L audit corrections (Findings N6, N7, N8)
* **Status:** Active
* **Decision:** In `8_AISI316L.xlsx`, set torsional phase to $90^\circ$ on non-proportional rows (N6); set bulk elastic properties to $E = 193\,\mathrm{GPa}$ and $\nu = 0.30$ (N7); append the 8 missing test specimens from Janssens (2018) Table 4 (N8).
* **Rationale:** Janssens (2018) explicitly specifies $90^\circ$ phase shift for the non-proportional series. Literature values from Zhu et al. (2019) provide verified bulk elastic properties. The 8 omitted tests in Table 4 are valid fatigue specimens.

### d040
* **Date:** 2026-10-18
* **Topic:** Historical reference output preservation
* **Status:** Active
* **Decision:** Archive pre-audit CSV results into `Results/archive/pre-audit/` rather than committing 170+ regenerated CSV files to the root results folder.
* **Rationale:** Keeps git history lean, avoids massive diff noise across numerical commits, and preserves historical pre-audit outputs for audit traceability.

### d041
* **Date:** 2026-10-18
* **Topic:** Maintenance log retirement
* **Status:** Reversed
* **Decision:** Originally retired `docs/audit-checkpoint.md` as internal maintenance scratch. Reversed during upstream sync when Andrea Chiocca requested maintaining `docs/audit-checkpoint.md` as the unified progress record.

### d042
* **Date:** 2026-10-18
* **Topic:** MMMH criterion registration fallback
* **Status:** Superseded by Batch P4-2
* **Decision:** Originally deferred registering MMMH because Mertens & Liebich (2017) references [16, 23] for the Haigh diagram $M_N$ curve were not yet retrieved.
* **Outcome:** Dubbel C10 Section 10 verified the endurance limit relation $M = (\sigma_A(R=-1) - \sigma_A(R=0)) / \sigma_m(R=0)$, enabling full registration of `MMMH` in `src/multifat/models/registry.py`.

### d043
* **Date:** 2026-10-18
* **Topic:** Banvillet criterion (G26) scope
* **Status:** Active
* **Decision:** Implement Banvillet (2003) closed-form tension-torsion index with 15 verified tests, but keep the criterion unregistered in the general pipeline.
* **Rationale:** Full general evaluation requires rotating-bending fatigue limits and cross-section geometry (solid vs. thin-walled tube) not present in standard workbooks.

### d044
* **Date:** 2026-10-18
* **Topic:** Licence selection options
* **Status:** Superseded by `d071`
* **Decision:** Enumerated licence choices (MIT, BSD-3-Clause, Apache-2.0, GPL-3.0) and held decision open for author alignment. Formally superseded by `d071` selecting MIT.

### d046
* **Date:** 2026-10-18
* **Topic:** Default results output path
* **Status:** Active
* **Decision:** Set default output path for `multifat-run` and `multifat-pipeline` to `Results/current/`.

### d047
* **Date:** 2026-10-18
* **Topic:** Unregistered point kernel disposition
* **Status:** Active
* **Decision:** Retain unregistered point kernels (G24, G26, G29, G30, N34) as tested standalone modules, documenting their unresolved workbook inputs in `docs/catalogue/methods.json` rather than exposing partial criteria.

### d050
* **Date:** 2026-10-18
* **Topic:** Phase 4 milestone completion
* **Status:** Active
* **Decision:** Concluded public-release documentation restructuring and verification sweep on WorkstationUniTN.

### d052
* **Date:** 2026-10-19
* **Topic:** Pipeline architecture vs. upstream calibration store
* **Status:** Active
* **Decision:** Maintain `multifat`'s single-command pipeline architecture with inline missing-constant calibration and sidecar JSON records, declining upstream's stateful multi-script workflow (`fatigue/eval/calibration_store.py`).

### d054
* **Date:** 2026-10-19
* **Topic:** October 2026 dataset migration
* **Status:** Active
* **Decision:** Adopt upstream revised dataset collection (`71eaac3`, 12 numbered workbooks `1_`–`8_`, `10_`–`13_`), while retaining unnumbered `Al7075_T6.xlsx` which had no upstream replacement.

### d055
* **Date:** 2026-10-19
* **Topic:** Dedicated batch workbooks
* **Status:** Active
* **Decision:** Split secondary test batches into dedicated workbooks:
  - `14_42CrMo4_Reis.xlsx`: 29 Anes/Reis tests ($S_u = 1100\,\mathrm{MPa}$ batch, printed strain-life constants).
  - `15_Ti6Al4V_Berto.xlsx`: 48 Berto tests ($S_u = 978\,\mathrm{MPa}$, printed fatigue limits).
* **Rationale:** Prevents averaging static and fatigue properties across distinct heats and metallurgical conditions.

### d056
* **Date:** 2026-10-19
* **Topic:** AISI 316L data overlay
* **Status:** Active
* **Decision:** Declare corrections for `8_AISI316L.xlsx` in [`src/multifat/imp/overlay_files/8_AISI316L.overlay.json`](../src/multifat/imp/overlay_files/8_AISI316L.overlay.json):
  - Summary: Janssens $E = 193\,\mathrm{GPa}$, $\nu = 0.30$; Braun $E$ and $\nu$ set to `Null` (published values were XRD lattice constants for residual stress evaluation).
  - Dataset: 11 non-proportional cases set to $90^\circ$ phase shift; 8 omitted Table 4 cases appended.

### d057
* **Date:** 2026-10-19
* **Topic:** Fatigue index error for fatigue-limit datasets
* **Status:** Refined by `d063`
* **Decision:** Evaluate run-out-only datasets via the fatigue index error (Böhme & Papuga 2024, Eqs. 8–9):
  $$FI_{\mathrm{axial}} = \frac{DP(\text{case})}{DP(\text{axial } R=-1 \text{ at } \sigma_{-1})} - 1$$
* **Rationale:** Provides quantitative model error assessment when cycle counts are censored run-outs at the endurance limit.

### d058
* **Date:** 2026-10-19
* **Topic:** Loading external calibration records
* **Status:** Active
* **Decision:** Support upstream `Calibrations/` JSON records as an explicit pipeline input via `--constants <file>`, validating input compatibility before assessment.

### d059
* **Date:** 2026-10-19
* **Topic:** Steel Poisson's ratio fallback
* **Status:** Active
* **Decision:** Set Poisson's ratio $\nu = 0.30$ (Dubbel 2004, Part C) in Summary rows for steel workbooks lacking reported $\nu$ (`2_CX18`, `3_25CrMo4`, `4_30NCD16`, `7_982FA`).
* **Rationale:** Enables elastic strain tensor reconstruction for strain- and energy-based criteria without inventing material-specific constants.

### d061
* **Date:** 2026-10-19
* **Topic:** Braun mean stress preservation
* **Status:** Active
* **Decision:** Set mean axial stress $\sigma_m = \sigma_a$ for the 17 Braun $R = 0$ plain rows in `8_AISI316L.xlsx`.
* **Rationale:** The revised dataset loader interprets empty stress cells as unavailable loading components. Setting $\sigma_m = \sigma_a$ correctly reflects the $R = 0$ loading condition and prevents dropping all 17 tests.

### d062
* **Date:** 2026-10-19
* **Topic:** Benchmark execution host
* **Status:** Active
* **Decision:** Execute full regression snapshot sweeps on WorkstationUniPi.
* **Rationale:** Recurring Windows kernel / OpenBLAS memory faults on WorkstationUniTN (Intel Core i9-14900K Raptor Lake instability).

### d063
* **Date:** 2026-10-19
* **Topic:** Load-scaled fatigue index ($FI_{\mathrm{load}}$)
* **Status:** Active
* **Decision:** Implement load-scaled fatigue index $FI_{\mathrm{load}} = 1/s - 1$ where $DP(s \cdot \text{case}) = DP_{\mathrm{ref}}$ (via root-finding in `src/multifat/eval/endurance.py`).
* **Rationale:** Direct damage parameter ratios ($DP / DP_{\mathrm{ref}} - 1$) distort relative stress capacity for criteria where damage scales quadratically with stress or strain (e.g., SWT, Smith–Watson–Topper). $FI_{\mathrm{load}}$ accurately recovers the equivalent load-scaling margin.

### d065
* **Date:** 2026-10-19
* **Topic:** Branch consolidation
* **Status:** Active
* **Decision:** Fast-forward `dev/tg-carry-forward` to `0e87e95` and prune temporary integration branches.

### d066
* **Date:** 2026-10-19
* **Topic:** Pipeline edge case resolution
* **Status:** Active
* **Decision:** Resolve nine deferred review items: ignore Excel lock files (`~$*.xlsx`), reject duplicate material IDs, guard against non-finite values in summaries, and preserve case identity metadata.

### d067
* **Date:** 2026-10-20
* **Topic:** Integration of upstream PRs #8 and #9
* **Status:** Active
* **Decision:** Port isolated harmonic Findley damage evaluation (`fin_harmonic.py`) and configurable calibration amplitudes from upstream `ab0e828`.

### d068
* **Date:** 2026-10-20
* **Topic:** Configurable Findley calibration amplitude
* **Status:** Active
* **Decision:** Provide `--shear-amplitude-algorithm` option in `multifat-calibrate` (`mce_harmonic`, `mcc_harmonic`, `rss`). Production default remains legacy MCE.

### d069
* **Date:** 2026-10-20
* **Topic:** Findley MCC calibration plane search
* **Status:** Active
* **Decision:** Execute MCC calibration via the `longest_chord` plane rule (`FindleyMCC`) using `multifat`'s refined plane search.

### d070
* **Date:** 2026-10-20
* **Topic:** Calibration record algorithm guard
* **Status:** Active
* **Decision:** Reject non-MCE calibration records when loading via `--constants` into the production pipeline.

### d071
* **Date:** 2026-10-22
* **Topic:** MIT licence adoption
* **Status:** Active (supersedes `d044`)
* **Decision:** Formally relicense `multifat` under the **MIT License** (Copyright 2026 Andrea Chiocca, Michele Sgamma, and Tommaso Grossi) in commit `f590efa`.
* **Rationale:** Permissive licensing provides maximum research utility, industry adoption, and post-processor integration. All incorporated third-party code must be permissively licensed (MIT, BSD, ISC, Apache-2.0).
