# I_DANGVAN: Dang Van

**Prepared Issue body; not an open GitHub Issue.** Before posting, search open and closed Issues for the permanent ID and aliases. Do not create a duplicate. Suggested labels: `method:mesoscopic-and-damage`, `status:partial`, `help-wanted`, `validation-needed`. No `good-first-issue` claim is made.

## Scope and scientific reference

- Primary family: Mesoscopic and damage; secondary: none recorded.
- Status: Fully implemented; enabled: True.
- Authors/year: Dang Van (1973), Sur la résistance à la fatigue des métaux, Sciences et Technique de l'Armement 47, 647–722.
- Reference: Dang Van (1973), Sur la résistance à la fatigue des métaux, Sciences et Technique de l'Armement 47, 647–722.
- DOI: Original DOI not verified; retrieve the traceable primary source before coding.
- Reference evidence: Original source has no verified DOI in registry.
- Mathematical evidence: Checked against the source PDF in Phase 2 (2026-10-17); see docs/method-audit.md.
- Principle: Dang Van criterion in the form restated by Böhme, Papuga & Lange (2026) Eq. (3): kappa max tau_a + (3 - 1.5 kappa) sigma_H,max, kappa = s_-1/t_-1.
- Loading scope: Single-frequency harmonic CA, proportional and phase-shifted NP; MCC shear amplitude per plane..

## Available components and remaining work

FABER phase: Plain/smooth CA candidate or scoped point formulation; original loading, material and response requirements still apply.

External source discovery: possible_or_related_source; [EXT07](../EXTERNAL_IMPLEMENTATIONS.md#ext07); not integrated or independently validated. Consult the linked inventory for exact variant, language, license, evidence and reuse restrictions. External code does not count as integrated WG4.3 implementation.

No known essential coding gap within the declared repository scope.

Existing implementation: [src/multifat/models/cp_methods/dangvan.py](../../src/multifat/models/cp_methods/dangvan.py); symbol `DangVan`. Existing tests: [tests/methods/test_dangvan.py](../../tests/methods/test_dangvan.py), [tests/test_method_audit.py](../../tests/test_method_audit.py).

Reuse: Physical harmonic tensors; direct FatigueModel interface; original-law-specific postprocessing.

Expected inputs: Sigm1, Taum1.. Expected output: Damage parameter; fitted life where valid.

Known restrictions: Documented variant: Dang Van (1993, 1999) defines the criterion through mesoscopic shakedown without closed-form a, b; this is the Papuga-Halama / Böhme 2026 calibration. 24x48 sphere grid with pattern refinement.

## Acceptance criteria

- [ ] Identify exact original formulation, version, supplements and errata; record equations and departures. If source identity/equivalence is unresolved, resolve it before implementation.
- [ ] Agree bounded CA scope: proportional, phase-shifted NP, mean stresses and applicable material domain. Reject unsupported inputs explicitly.
- [ ] Implement missing components faithfully using physical simultaneous tensors and the original amplitude/plane rule; declare material fields, units, calibration and missing-data behavior.
- [ ] Integrate using [the existing interfaces](../../docs/adding-methods.md), registry and runtime source metadata. Do not enable an archived proxy before repair.
- [ ] Check axial/torsion limits, zero/degenerate cases, means, phase/time-origin and frame invariance as applicable; demonstrate grid/quadrature/optimizer convergence where needed.
- [ ] Obtain at least one independently calculated original-paper numerical case with material/loading data and intermediate quantities. Keep calibration and validation separate; record inaccessible data rather than inventing it.
- [ ] Preserve BP/CAIM, disabled guards, reporting and all-slope `log10(DP_e/DP)` behavior; run `MPLBACKEND=Agg python -m unittest discover -s tests -v`.
- [ ] Update `docs/catalogue/methods.json`, attach Issue/PR and validation evidence, regenerate documentation and pass `python tools/generate_method_docs.py --check`.
- [ ] Review implementation completeness separately from validation; never promote validation merely because numerical tests pass.

Validation lead: tests/methods/test_dangvan.py: Böhme et al. (2026) Eq. (16) closed forms and Table 4 DV statistics over 18 cases (Max and SD within 0.07 of print).

Dependencies: confirm source/version and measured parameters first; consult [ROADMAP.md](../../ROADMAP.md) for shared cycle, quadrature, native-life and data prerequisites. G01/G02 share a paper but retain distinct laws; other candidate dependencies require specification, not automatic coupling.

Use separate reviewable PRs for source/benchmark specification, prerequisites and numerical implementation when the scope warrants it. Repository entry: [METHODS.md#i_dangvan](../../METHODS.md#i_dangvan).
