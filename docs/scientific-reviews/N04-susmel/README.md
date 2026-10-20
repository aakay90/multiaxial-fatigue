# N04: Susmel and Lazzarin modified Woehler curve (2002)

**Scientific decision: READY FOR RESTRICTED IMPLEMENTATION.** This package documents the 2002 stress-based, high-cycle formulation for smooth/plain specimens under constant-amplitude, single-harmonic multiaxial loading. It supports a fatigue-limit comparison using matched fully reversed axial and torsional fatigue strengths. A numerical fatigue-life prediction additionally requires both matched stress-life curves and their inverse slopes at a common reference life; the present package supplies neither those slopes nor experimental predictive validation.

The authoritative mathematical dossier is [N04-susmel.tex](N04-susmel.tex) (compiled as [N04-susmel.pdf](N04-susmel.pdf)). Its stable equation labels are `eq:stress-history` (D1), `eq:traction` (D2), `eq:normal-extrema` (D3), `eq:mcc-amplitude` (D4), `eq:modified-wohler` (D5), and `eq:endurance-index` (D6). Section labels are `sec:assessment`, `sec:sources`, `sec:math`, `sec:benchmarks`, `sec:applicability`, `sec:integration`, `sec:gaps`, and `sec:handoff`.

## Scientific basis and scope

The original source is Susmel and Lazzarin, *A bi-parametric Woehler curve for high cycle multiaxial fatigue assessment*, *Fatigue & Fracture of Engineering Materials & Structures* **25** (2002), 63-78, [doi:10.1046/j.1460-2695.2002.00462.x](https://doi.org/10.1046/j.1460-2695.2002.00462.x). The full original article was examined. Related publications from 2003, 2005, and 2008 are listed in [references.bib](references.bib), but only their abstracts and bibliographic records were available for this review. No later-variant equation is imported into N04.

Use physical, symmetric Cauchy stress tensors in MPa, with a common harmonic phase: `sigma(theta) = sigma_m + sigma_s sin(theta) + sigma_c cos(theta)` (D1). For a unit plane normal `n`, compute signed normal traction `n^T sigma n` and in-plane shear vector `(I - nn^T) sigma n` (D2). The normal maximum is its mean plus its exact harmonic amplitude (D3); do not silently clip negative values. Mean normal stress enters through this maximum.

The critical plane **maximises shear amplitude**, not the final combined damage quantity. The prescribed amplitude is the minimum-circumscribed-circle (MCC) radius of the *physical vector shear path*. For a complete harmonic history it is exactly the square root of the largest eigenvalue of the 2-by-2 Gram matrix of the sine and cosine shear vectors (D4). RSS/MCE is not interchangeable with MCC. Plane sampling is a numerical approximation to a continuous orientation search; establish convergence. A plane normal and its negative denote the same plane.

For positive shear amplitude, set `rho = sigma_n,max / tau_a`. The 2002 reference shear strength varies linearly with `rho`, and its inverse Woehler slope is interpolated between matched axial and torsional curves (D5). At a specified fatigue limit, let `c = tau_A - sigma_A/2`; the independent test quantity is `D = tau_a + c*rho`, with utilisation `U = D/tau_A` (D6). `D` is in MPa, `U` is dimensionless. Do not treat `U` as a life prediction or replace the native life relation with a generic damage-life fit.

## Inputs and implementation requirements

- Required load input: symmetric `sigma_m`, `sigma_s`, and `sigma_c` tensors, each in MPa, for one common-frequency harmonic.
- Fatigue-limit input: fully reversed axial strength `sigma_A` and torsional strength `tau_A`, in MPa, defined at the same documented reference life and compatible test conditions.
- Native-life-only input: matching fully reversed axial and torsional stress-life curves, their inverse slopes, common `N_Ref`, fitted life interval, and provenance. No numerical life benchmark is asserted here.
- Evaluate D2-D4 on candidate planes, maximise MCC shear amplitude, and then evaluate D3 and D5 or D6 on a selected maximum-shear plane. Document the finite search and convergence error.
- Make a scientifically approved policy for tied maximum-shear planes before returning a unique result. Reject or explicitly mark zero-shear cases as undefined under the original ratio-based equations; do not invent a finite result.
- Treat high tensile/compressive mean stress, non-positive interpolated reference strength, strong extrapolation outside calibration endpoints, notches, plastic low-cycle response, and variable-amplitude loading as outside this restricted handoff unless separately justified.

## Independent verification data

[benchmarks.json](benchmarks.json) contains the independently derived B1-B8 cases using the 2002 paper's Table 1 strengths `sigma_A = 215.8 MPa` and `tau_A = 127.2 MPa` for the reported 0.35% C carbon steel. B1/B2 recover the axial/torsional limits; B3/B4 cover proportional and 90-degree out-of-phase combinations; B5 adds tensile normal mean stress; B6 distinguishes MCC (`100 MPa`) from RSS/MCE (`116.61903789690601 MPa`); B7 records **two tied-plane outcomes, not one expected damage value**; B8 is a zero-shear domain case with **no finite result defined by the original formulation**. B8 now includes numerical inputs for constant positive hydrostatic stress, alternating hydrostatic stress with `p = 100 MPa`, and zero loading. None has a finite ratio-based output. The positive value is an illustrative test input, not a published material property. The JSON separates exact prescribed-plane checks from global maximum-shear targets. Exact-plane float64 checks use `1e-8 MPa` absolute and `1e-10` relative tolerances; a sampled orientation search requires a separate convergence assessment. These are mathematical checks, not publication-reported predictions or experimental validation. Full derivations and provenance are in `sec:benchmarks` of the TeX dossier.

The previous B4 value `D = 133.86439825623583 MPa` remains valid on its listed 45-degree planes. The global maximum-shear search also admits `(e_x + e_z)/sqrt(2)`, where `D = 129.3 MPa`. Thus B4, like B7, has no unique final assessment until a tie policy is approved. This qualification corrects the earlier interpretation of B4 as a unique global target without altering its original prescribed-plane result.

## Unresolved decisions and publication status

The 2002 article does not specify a tie rule for equally maximum-shear planes, an output at zero shear, or a complete admissibility rule for extrapolated `rho`. Matched stress-life slopes are still needed for numerical native-life tests. This public edition excludes observations drawn from privately supplied third-party source files and redistributes no such code or original publication PDF. No further permission-dependent content has been identified in the five public files. The package is ready for repository integration after the user's final scientific approval; its scientific restrictions remain in force.

## Build and integration

Build dependencies are a LaTeX distribution with `pdflatex`, `bibtex`, `latexmk`, and the packages declared in the TeX preamble (`geometry`, `needspace`, `lmodern`, `microtype`, `amsmath`, `amssymb`, `booktabs`, `array`, `longtable`, `xcolor`, `hyperref`, `fancyhdr`, and `enumitem`). From this directory, run `latexmk -pdf -interaction=nonstopmode -halt-on-error N04-susmel.tex`. `latexmk` invokes BibTeX and repeat LaTeX passes as needed. The intended future repository location, after the user's approval, is `docs/scientific-reviews/N04-susmel/`. The Software Engineer should link this README from the N04 method-catalogue entry and preserve the existing method identity; no repository change is authorised by this package.
