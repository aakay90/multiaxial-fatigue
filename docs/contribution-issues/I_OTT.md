# I_OTT: Ottosen/Tveit proportional reduction (archived scope)

**Prepared Issue body; not an open GitHub Issue.** Before posting, search open and closed Issues for the permanent ID and aliases. Do not create a duplicate. Suggested labels: `method:invariant-based`, `status:partial`, `help-wanted`, `validation-needed`. No `good-first-issue` claim is made.

## Scope and scientific reference

- Primary family: Invariant based; secondary: disabled; source retained.
- Status: Partially implemented; enabled: False.
- Authors/year: Sigbjørn Tveit, Aase Reyes, Emrah Erduran (2024).
- Reference: A continuum approach to multiaxial high-cycle fatigue modeling for ductile metallic materials, Results in Engineering.
- DOI: https://doi.org/10.1016/j.rineng.2024.102171
- Reference evidence: Exact-title Crossref work record; implementation attribution subject to audit caveats; saved metadata in docs/research/doi-records.json.
- Mathematical evidence: Inherited repository audit, not repeated.
- Principle: Tveit et al. (2024), A continuum approach to multiaxial high-cycle fatigue modeling for ductile metallic materials.
- Loading scope: No currently supported executable scope; archived proxy must not be used..

## Available components and remaining work

Only a proportional cycle reduction; non-proportional extension is unverified and fatigue-ratio calibration silently falls back to m=2 outside its supported range. Restore only after source-faithful repair and regression/reference checks.

Existing implementation: [fatigue/models/invariant_methods/ottosen.py](../../fatigue/models/invariant_methods/ottosen.py); symbol `OttosenReduced`. Existing tests: [tests/test_method_audit.py](../../tests/test_method_audit.py).

Reuse: Physical harmonic tensors; direct FatigueModel interface; original-law-specific postprocessing.

Expected inputs: Physical stress cycle; calibrated fatigue ratio and exact proportional-reduction constants/domain. Expected output: Damage parameter; fitted life where valid.

Known restrictions: Only a proportional cycle reduction; non-proportional extension is unverified and fatigue-ratio calibration silently falls back to m=2 outside its supported range.

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

Validation lead: tests/test_method_audit.py verifies disabled-name guards only. This is not numerical verification or scientific validation of the archived criterion. Restoration needs original-paper examples.

Dependencies: confirm source/version and measured parameters first; consult [ROADMAP.md](../../ROADMAP.md) for shared cycle, quadrature, native-life and data prerequisites. G01/G02 share a paper but retain distinct laws; other candidate dependencies require specification, not automatic coupling.

Use separate reviewable PRs for source/benchmark specification, prerequisites and numerical implementation when the scope warrants it. Repository entry: [METHODS.md#i_ott](../../METHODS.md#i_ott).
