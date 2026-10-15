# Contributing to WG4.3

Start with [METHODS.md](METHODS.md), the [suggested roadmap](ROADMAP.md) and [prepared Issues](docs/contribution-issues/README.md). Contributions can implement a method, resolve a source ambiguity, build a reproducible benchmark, validate existing code or improve documentation. Priority is advisory, not a project assignment.

## Select and specify a method

1. Search existing open and closed Issues by permanent catalogue ID, aliases and original authors. Comment on an existing Issue or open a scoped proposal using the method template. Avoid duplicate tasks and bundling unrelated laws into one PR.
2. Obtain the exact original paper and relevant errata/supplements. DOI metadata verifies identity, not governing equations. If the source has no verified DOI, provide a traceable bibliographic reference. Do not upload copyrighted articles without distribution rights; cite equations and record a concise implementation specification.
3. State the supported CA loading path, mean-stress convention, material domain, required measurements and output (limit, utilization, damage parameter, native life or probability). General periodic loading does not imply the current importer supports it. Identify shared prerequisites before promising a plug-in.
4. Record original versus repository adaptations separately. Never infer equivalence from names, replace an amplitude definition silently, omit plastic work or substitute an empirical life fit for a published native law.

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
MPLBACKEND=Agg python -m unittest discover -s tests -v
python tools/generate_method_docs.py
python tools/generate_method_docs.py --check
git diff --check
# For changes affecting shared numerical behavior, also consider:
# python tests/run_material_validation.py /tmp/wg43-validation
```

The broad sweep is appropriate for shared numerical changes; routine documentation changes do not require regenerating all experimental results. Include commands, results and known warnings in the PR.

## Update the catalogue

`docs/catalogue/methods.json` is the current source of truth. Keep permanent IDs, add canonical relationships and optional secondary classifications, and count each identifiable scoped method once by its primary family. Exclude unresolved bundles/overlaps from progress totals until reconciled. The archived research CSV is provenance, not another live status source.

Update implementation status, declared scope, module/symbol, tests, remaining work, validation evidence and actual Issue URL. Generate `METHODS.md`, `ROADMAP.md`, the CSV, README counts and prepared briefs using `tools/generate_method_docs.py`. CI checks output freshness and evidence paths against the registry. Do not edit generated files independently. When adding an ID, update the generator's selected Issue/roadmap ID lists only if appropriate; the full catalogue is generated automatically.

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
