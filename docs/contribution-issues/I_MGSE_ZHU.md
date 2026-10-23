# I_MGSE_ZHU: Zhu weighted generalized strain energy

**Prepared Issue body; not an open GitHub Issue.** Before posting, search open and closed Issues for the permanent ID and aliases. Do not create a duplicate. Suggested labels: `method:energy-based`, `status:review`, `help-wanted`, `validation-needed`. No `good-first-issue` claim is made.

## Scope and scientific reference

- Primary family: Energy based; secondary: Critical plane.
- Status: Requires review; enabled: True.
- Authors/year: Shun-Peng Zhu, Zheng-Yong Yu, José Correia, Abílio De Jesus, Filippo Berto (2018).
- Reference: Evaluation and comparison of critical plane criteria for multiaxial fatigue analysis of ductile and brittle materials, International Journal of Fatigue.
- DOI: https://doi.org/10.1016/j.ijfatigue.2018.03.028
- Reference evidence: Exact-title Crossref work record; implementation attribution subject to audit caveats; saved metadata in docs/research/doi-records.json.
- Mathematical evidence: Inherited repository audit, not repeated.
- Principle: tau_max*gamma_a+k_MGSE*sigma_max*epsilon_a.
- Loading scope: Single-frequency harmonic CA; proportional / phase-shifted NP; mean stresses within declared conventions. Arbitrary periodic waveforms are not imported..

## Available components and remaining work

FABER phase: Plain/smooth CA candidate or scoped point formulation; original loading, material and response requirements still apply.

External source discovery: no_accessible_source_identified; not integrated or independently validated. Consult the linked inventory for exact variant, language, license, evidence and reuse restrictions. External code does not count as integrated WG4.3 implementation.

Weighting and original plane rule require full-source verification. Add an independently calculated original-paper case before declaring complete.

Existing implementation: [src/multifat/models/cp_methods/mgse_zhu.py](../../src/multifat/models/cp_methods/mgse_zhu.py); symbol `MGSE_Zhu`. Existing tests: [tests/test_method_audit.py](../../tests/test_method_audit.py).

Reuse: Physical harmonic tensors; direct FatigueModel interface; original-law-specific postprocessing. Tensor rotations and candidate plane search where the source plane rule permits.

Expected inputs: k_MGSE optional (default 1). Expected output: Damage parameter; empirical fitted life only where curve inversion is valid.

Known restrictions: Weighting and original plane rule require full-source verification.

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

Validation lead: docs/method-audit.md and tests/test_method_audit.py. Analytical/regression evidence only; no independent published/experimental dataset reproduction claimed.

Dependencies: confirm source/version and measured parameters first; consult [ROADMAP.md](../../ROADMAP.md) for shared cycle, quadrature, native-life and data prerequisites. G01/G02 share a paper but retain distinct laws; other candidate dependencies require specification, not automatic coupling.

Use separate reviewable PRs for source/benchmark specification, prerequisites and numerical implementation when the scope warrants it. Repository entry: [METHODS.md#i_mgse_zhu](../../METHODS.md#i_mgse_zhu).
