# Contributing to WG4.3

This framework supports preparation of the **FABER WG4.3 scientific review article** and collaborative comparison of published multiaxial fatigue criteria. The present phase is **constant-amplitude loading of plain/smooth geometries**, P/NP where the selected law supports it, without explicit notches, cracks or significant gradients. Wider loading/geometry work remains a potential future track, not an existing capability or committed deliverable.

## Check external code before starting from scratch

Consult the [external-code inventory](docs/EXTERNAL_IMPLEMENTATIONS.md) and the method’s discovery metadata. An external implementation remains external until independently reviewed, integrated and tested; it does not change WG4.3 completeness or validation.

For any proposed reuse or translation, record the exact file/revision, method/version correspondence, original paper, loading/material/geometry assumptions, dependencies, tests and license grant. Public code without an explicit applicable license is not permission to copy, translate or redistribute. GPL obligations differ from MIT/ISC notices, and this repository’s own license is still undecided: resolve compatibility with maintainers before integration. Where permission is absent, link the source and seek permission or derive an independent implementation from the scientific formulation with appropriate review. Do not port unknown-license code under a new license.

Compare intermediate quantities and source-specific plane/amplitude conventions, not only final life. External tests and published claims are evidence leads, not scientific validation of a port. Attach provenance and notices to the eventual PR. For geometry/gradient/spectral software, first establish whether a faithful smooth-point CA subcase exists; do not silently import a broader physical model.

Start with [METHODS.md](METHODS.md), the [suggested roadmap](ROADMAP.md) and [prepared Issues](docs/contribution-issues/README.md). Contributions can implement a method, resolve a source ambiguity, build a reproducible benchmark, validate existing code or improve documentation. Priority is advisory, not a project assignment.

## Ten steps from a method to a PR

1. **Choose an ID.** Browse [all missing methods by family](docs/METHOD_INDEX.md#missing-methods-by-family), repairs or source-review tasks. The roadmap is a suggested sequence; you may propose another catalogued method. For a genuinely new candidate, establish its relationship to existing entries before assigning a new permanent ID.
2. **Find or propose the task.** Use the entry’s Search Issues link, check aliases and closed Issues, and claim an existing task or open a scoped proposal. The Propose task link opens the method-specific template with its ID/title. Prepared briefs are not live Issues.
3. **Confirm the primary formulation.** Obtain the exact original article, relevant errata/supplements and traceable citation. DOI metadata confirms identity, not equations. An unresolved variant needs reference work before numerical implementation. Do not upload copyrighted papers without redistribution rights.
4. **Write a bounded specification.** State CA P/NP/mean-stress scope, material domain, equations, amplitude/range and shear conventions, required measurements and output (limit, damage parameter, native life or probability). Record repository adaptations separately from the original law.
5. **Inspect reusable components.** Read only the [model interface guide](docs/adding-methods.md), one nearby implementation and relevant projection/search helpers. Verify that reuse preserves the source plane rule and physical simultaneous path. List any input, native-life or spatial/statistical prerequisite.
6. **Implement and integrate.** Place the law in the appropriate model family, declare parameters, register it and add runtime citation metadata. Follow the paths/interfaces below; propose major prerequisites separately. A contributor need not understand all plotting/calibration code to implement one criterion.
7. **Document inputs and limits.** Add material fields only when needed. State units, provenance, measured versus estimated constants, supported loading and explicitly unsupported cases. Never silently omit work terms or replace the native life law with a generic fit.
8. **Numerically verify.** Add focused analytical/degenerate, phase/mean/frame checks as appropriate, unsupported-input checks and search/integration convergence. Compute at least one reference result independently of the implementation.
9. **Validate and report evidence.** Reproduce a published case with its material/loading data and intermediate values where available. Keep calibration separate from validation; state inaccessible data or remaining predictive-validation gaps. Run the regression and documentation checks below.
10. **Update and submit.** Update the JSON catalogue, source/test/evidence and actual Issue links; regenerate documentation. Submit a PR using the template, citing the permanent ID and acceptance checklist. A maintainer reviews scoped completeness and validation independently; passing unit tests alone does not promote scientific validation.

## Develop locally

Use Python 3.10+ and install `requirements.txt` as in the README. Branch from current `main`. Run entry scripts from the repository root. Preserve experimental workbooks and archived `Results/*.csv`; direct test output to a temporary directory. Do not commit generated caches, private data or article PDFs.

Follow [the architecture](docs/architecture.md) and [adding methods](docs/adding-methods.md):

- Plane-level criteria belong in `fatigue/models/cp_methods/`, implement `CriticalPlaneMethod.evaluate_on_plane` and return `CPPlaneResult(damage, metric)`. A scan may only be reused when it matches the source's plane rule.
- Direct criteria belong in the appropriate `invariant_methods/`, `energy_based_methods/` or `integral_methods/` folder. Implement `FatigueModel.evaluate_case` and return `CaseResult`; consume physical `harmonics` when timing/phase matters.
- Register in `fatigue/models/registry.py`. Add runtime citation metadata in `fatigue/models/references.py`. Add inputs through `fatigue/imp/experimental_data.py` and the runner only when needed. Follow existing names and `_ext` conventions.
- A new physical model or data structure needs its own explicit proposal. The plane/scalar interface does not justify dropping source requirements. Keep BP/CAIM distinct and preserve all-slope `log10(DP_e/DP)` reporting and life-suppression rules.

The current legacy CP RSS ellipse convention differs from BP/CAIM's major-axis/MCC convention. Strain shear is tensorial in tensors and engineering shear in relevant scalar ranges. Record amplitude versus range, cycles versus reversals, units, stress sign, plane normal, coordinate basis and all empirical material fallbacks.

## Evidence required in a PR

Provide source/version, supported scope, equations implemented, parameter provenance, numerical choices, limitations and a reproducible validation command. Cite relevant original equation numbers without copying excessive text. Include focused checks for pure axial/torsion, degeneracy, mean stress, phase and coordinate/time-origin invariance as appropriate. Demonstrate search/quadrature convergence where relevant.

Reference cases should include the article's material data, actual repeated path, intermediate quantities and expected output. Calculate at least one result independently of the implementation. Separate calibration data from validation data. Record measurement uncertainty and inaccessible data honestly. A passing test of the coded equation is numerical verification; it does not establish predictive accuracy.

Run:

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check .
MPLBACKEND=Agg python -m unittest discover -s tests -v
python tools/generate_method_docs.py
python tools/generate_method_docs.py --check
python tools/check_docs.py
git diff --check
# For changes affecting shared numerical behavior, also consider:
# python tests/run_material_validation.py /tmp/wg43-validation
```

The broad sweep is appropriate for shared numerical changes; routine documentation changes do not require regenerating all experimental results. Include commands, results and known warnings in the PR.

Ruff checks unused imports, redefinitions and undefined names. No mass formatting
migration is required. The documentation checker covers maintained local links
and fragments; external availability and frozen research prose need separate
review. Runtime dependencies remain in `requirements.txt`; development tooling
is isolated in `requirements-dev.txt`. Preserve the historical CSVs described
in [Results/README.md](Results/README.md).

## Update the catalogue

`docs/catalogue/methods.json` is the current source of truth. Keep permanent IDs, add canonical relationships and optional secondary classifications, and count each identifiable scoped method once by its primary family. Exclude unresolved bundles/overlaps from progress totals until reconciled. The archived research CSV is provenance, not another live status source.

Update implementation status, declared scope, module/symbol, tests, remaining work, validation evidence and actual Issue URL. Generate `METHODS.md`, `ROADMAP.md`, the CSV, README counts and prepared briefs using `tools/generate_method_docs.py`. CI checks output freshness and evidence paths against the registry. Do not edit generated files independently. Roadmap selection is stored in each JSON record as `roadmap_rank`, `development_track` and `development_reason`; every record needs an explicit disposition. Unscheduled candidates must remain in the catalogue. The generator’s Issue-ID list controls only which prepared briefs are emitted, not which methods contributors may choose.

### Ready for “fully implemented”

- [ ] Exact supported formulation/version identified, with explicit adaptations and loading/material restrictions.
- [ ] Every essential component of that declared formulation implemented; no known essential omission.
- [ ] Required inputs/parameters supported and checked; measured and estimated properties distinguished.
- [ ] Original plane, path, integration and native life rules faithfully handled within declared scope.
- [ ] Registered, documented and covered by meaningful automated tests, including unsupported-input behavior.
- [ ] Source → catalogue → code → tests → evidence → Issue/PR links complete.
- [ ] Existing numerical regression checks pass and generated docs are current.
- [ ] Completeness reviewed by a maintainer; uncertain completeness remains `requires_review`.

Validation is a separate promotion: `not_tested` → `basic_numerical_tests` → `reference_examples_reproduced` → `independently_validated`. Reference reproduction needs independently calculated published examples; independent validation needs traceable published/experimental data beyond self-consistency tests. A complete scoped implementation may still have only basic numerical evidence.

## Submit

Open a PR linking the permanent method ID and relevant Issue. Summarize the resulting scientific capability, scope, departures and evidence. Use separate reviewable prerequisites for large workstreams. Do not re-enable disabled proxies until their recorded audit gaps are resolved. No repository license has yet been selected; maintainer agreement on licensing remains necessary for clear reuse terms. This documentation does not grant a new software license.
