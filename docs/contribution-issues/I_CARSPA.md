# I_CARSPA: Carpinteri–Spagnoli

**Prepared Issue body; not an open GitHub Issue.** Before posting, search open and closed Issues for the permanent ID and aliases. Do not create a duplicate. Suggested labels: `method:critical-plane`, `status:partial`, `help-wanted`, `validation-needed`. No `good-first-issue` claim is made.

## Scope and scientific reference

- Primary family: Critical plane; secondary: disabled; source retained, Critical plane.
- Status: Partially implemented; enabled: False.
- Authors/year: A CARPINTERI, A SPAGNOLI (2001).
- Reference: Multiaxial high-cycle fatigue criterion for hard metals, International Journal of Fatigue.
- DOI: https://doi.org/10.1016/s0142-1123(00)00075-x
- Reference evidence: Exact-title Crossref work record; implementation attribution subject to audit caveats; saved metadata in docs/research/doi-records.json.
- Mathematical evidence: Inherited repository audit, not repeated.
- Principle: Carpinteri & Spagnoli (2001), Multiaxial high-cycle fatigue criterion for hard metals.
- Loading scope: No currently supported executable scope; archived proxy must not be used..

## Available components and remaining work

Missing the published critical-plane orientation construction; maximum-shear/max-damage scans are not that criterion. Restore only after source-faithful repair and regression/reference checks.

Existing implementation: [fatigue/models/cp_methods/car_spa.py](../../fatigue/models/cp_methods/car_spa.py); symbol `CarSpa`. Existing tests: [tests/test_method_audit.py](../../tests/test_method_audit.py).

Reuse: Physical harmonic tensors; direct FatigueModel interface; original-law-specific postprocessing. Tensor rotations and candidate plane search where the source plane rule permits.

Expected inputs: Physical stress harmonics; Sigm1, Taum1 and published material-dependent orientation parameters. Expected output: Damage parameter; fitted life where valid.

Known restrictions: Missing the published critical-plane orientation construction; maximum-shear/max-damage scans are not that criterion.

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

Use separate reviewable PRs for source/benchmark specification, prerequisites and numerical implementation when the scope warrants it. Repository entry: [METHODS.md#i_carspa](../../METHODS.md#i_carspa).
