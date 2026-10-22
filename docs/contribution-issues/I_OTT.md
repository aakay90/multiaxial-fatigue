# I_OTT: Ottosen/Tveit proportional reduction (archived scope)

**Prepared Issue body; not an open GitHub Issue.** Before posting, search open and closed Issues for the permanent ID and aliases. Do not create a duplicate. Suggested labels: `method:invariant-based`, `status:partial`, `help-wanted`, `validation-needed`. No `good-first-issue` claim is made.

## Scope and scientific reference

- Primary family: Invariant based; secondary: none recorded.
- Status: Fully implemented; enabled: True.
- Authors/year: Sigbjørn Tveit, Aase Reyes, Emrah Erduran (2024).
- Reference: A continuum approach to multiaxial high-cycle fatigue modeling for ductile metallic materials, Results in Engineering.
- DOI: https://doi.org/10.1016/j.rineng.2024.102171
- Reference evidence: Exact-title Crossref work record; implementation attribution subject to audit caveats; saved metadata in docs/research/doi-records.json.
- Mathematical evidence: Checked against the source PDF in Phase 2 (2026-10-17); see docs/method-audit.md.
- Principle: Tveit et al. (2024), A continuum approach to multiaxial high-cycle fatigue modeling for ductile metallic materials.
- Loading scope: Single-frequency harmonic CA, proportional and phase-shifted NP via the minimum circumscribed Hershey-Hosford ball; calibrated range 0.5 <= t_-1/s_-1 <= 0.5852 (capped m = 2.767 above)..

## Available components and remaining work

FABER phase: Plain/smooth CA candidate or scoped point formulation; original loading, material and response requirements still apply.

External source discovery: no_accessible_source_identified; not integrated or independently validated. Consult the linked inventory for exact variant, language, license, evidence and reuse restrictions. External code does not count as integrated WG4.3 implementation.

No known essential coding gap within the declared repository scope. The incremental continuum model is out of scope.

Existing implementation: [src/multifat/models/invariant_methods/ottosen.py](../../src/multifat/models/invariant_methods/ottosen.py); symbol `OttosenReduced`. Existing tests: [tests/methods/test_ottosen.py](../../tests/methods/test_ottosen.py), [tests/test_method_audit.py](../../tests/test_method_audit.py).

Reuse: Physical harmonic tensors; direct FatigueModel interface; original-law-specific postprocessing.

Expected inputs: Sigm1, Taum1; A_OTT or an R = 0 strength (Sig0, or Su for the Böhme 2026 estimate); optional m_OTT.. Expected output: Damage parameter; fitted life where valid.

Known restrictions: Reduced cycle-based form of Tveit et al. (2024), not the incremental back-stress model; out-of-phase rows agree with Tveit's incremental results within about 0.7 points (7/10). Materials with t_-1/s_-1 > 0.5852 use the capped exponent outside the calibrated range.

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

Validation lead: tests/methods/test_ottosen.py: Tveit et al. (2024) Table A.1, all 47 in-phase rows to print rounding (modified and original model), out-of-phase rows within 0.8 points except three unresolved 30NCD16 rows.

Dependencies: confirm source/version and measured parameters first; consult [ROADMAP.md](../../ROADMAP.md) for shared cycle, quadrature, native-life and data prerequisites. G01/G02 share a paper but retain distinct laws; other candidate dependencies require specification, not automatic coupling.

Use separate reviewable PRs for source/benchmark specification, prerequisites and numerical implementation when the scope warrants it. Repository entry: [METHODS.md#i_ott](../../METHODS.md#i_ott).
