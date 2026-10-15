# Documentation development history

Frozen checkpoints from the three merged documentation PRs. They record conditions at the time; current instructions and status are in the root README, catalogue and contributor guide. Original checkpoint content is retained below.


Original path: `docs/catalogue/organization-checkpoint.md`

## Repository organization checkpoint — 15 October 2026

Baseline: public `andreachiocca/multiaxial-fatigue`, GitHub main `01418383ac2ab3cea8bab225f718dd652ba82820`. The original local HEAD was `32d1118`; all tracked blobs matched the remote tree, so no numerical work was missing or overwritten. Dedicated branch: `docs/wg43-method-catalogue`. GitHub publication uses a commit parented directly on the checked remote main; local source history is preserved.

### Completed

- Reused the 161-record master, full supplied review, 51/51 coverage, prior feasibility assessment, saved DOI identity records and numerical audit. No new literature search or DOI verification was performed.
- Central JSON contains 117 identifiable method/scoped candidates: 10 fully implemented for explicit repository scopes, five known partial/disabled, five active requiring source review, 97 missing. Forty-four bundled/overlapping/related/unresolved/workstream records remain traceable outside progress totals.
- Implementation and validation statuses are independent. No method is claimed independently scientifically validated. Archived disabled methods have guard-test evidence only and are marked not tested as fatigue implementations.
- Generated METHODS, roadmap, CSV, README progress table and 16 prepared contribution briefs from the JSON. Added contributor checklist, Issue/PR templates and a documentation freshness CI workflow. Application code/data/results were not changed.
- `MPLBACKEND=Agg python -m unittest discover -s tests -q`: 20 tests passed. Existing Matplotlib deprecation warnings remain.
- `python tools/generate_method_docs.py --check`: passes unique IDs, A–D values, canonical links, full registry coverage, source/test paths, saved DOI records and 51/51 review entries.
- Relative Markdown file links, `git diff --check` and credential-pattern scan passed. Only documentation/metadata/generator/CI changes are staged; no temporary outputs, article PDFs, caches, raw-data or archived-result changes.

### Remaining limitations

The available GitHub connector exposes no Issue or label creation operation. No live Issues/labels were created. Sixteen consistent bodies are prepared in `docs/contribution-issues/`; search for duplicates before posting and update JSON `issue_url` afterwards. Do not represent those briefs as open Issues.

Full-source mathematical checks remain pending for MGSE_ZHU, MKBM, LIU2021, LI and scalar MSWT. The five disabled methods require substantive repairs. Broad C workstream reference numbering was inconsistent in inherited notes and remains flagged. Historical identities and overlap checks need original sources; the literature search was not restarted. Eighty-five missing counted candidates have preliminary A/B feasibility; available equations and measured parameters must still be confirmed before coding.

The repository has no selected software license. Maintainers should choose one before representing reuse terms as established open-source licensing. No visibility or license change was made.

### Continue

Review/merge the documentation PR, post the selected prepared Issues and apply agreed labels, then obtain Papuga–Růžička (2008), DOI `10.1016/j.ijfatigue.2007.02.015`, for separately scoped PCR/PI work. Source-faithful review/repair of existing methods can proceed independently. Future numerical implementations must use individual evidence-backed tasks and preserve BP/CAIM and all-slope log damage reporting.


Original path: `docs/catalogue/readme-review-checkpoint.md`

## Contributor documentation checkpoint — 15 October 2026

Previous documentation PR #1 is merged. This follow-up is based on GitHub main `4982053367ef4c1e8db4e14127ef58066c662a16`, whose tree matches the local checked documentation baseline. Branch: `docs/contributor-readme-reconciliation`.

### Reconciliation

All 161 inherited permanent IDs and all 51 numbered review publications remain traceable. The 117 method/scoped records comprise 20 implementation records and 97 missing candidates. The 22 prioritized additions are a subset of the 97; 75 remain available outside the initial sequence (66 A/B, nine C). Three selected additions also have C feasibility, so major extensions were not excluded merely for difficulty.

The earlier research shortlist had 23 entries. Its only difference from the published sequence is G14, held for unresolved equation-level overlap with GSE/GSA. G14 remains in the catalogue; equivalence has not been asserted. The other 44 research records are documented bundles, related publications/scopes, unresolved leads/overlaps and broader workstreams outside the narrow progress denominator. A final independent-theory count remains unresolved and is not presented as 117 or 161.

Every JSON row now has a development disposition/reason, roadmap rank or explicit deferral, and reference-retrieval action. Roadmap ranks moved from the generator into the JSON. README counts, browse views, roadmap and per-record reconciliation are generated from that source.

### External-reader review

- Project/scientific scope and collaboration goal appear before architecture.
- Missing candidates are reachable by family and status, with original source/DOI, loading scope and direct Issue search/proposal links.
- Active API methods are named prominently and linked to their exact supported scopes.
- Completeness, known partial/disabled code, source uncertainty and scientific validation remain distinct.
- Off-roadmap proposals are explicitly welcome; the ten-step contributor guide covers source, reuse, interface, data, tests, validation and PR requirements.
- The minimal API example and workbook command were executed against the actual code. Detailed BP/CAIM guidance moved to a linked page without removing its scientific content.
- Limitations include harmonic/elastic input, amplitude conventions, incomplete original-source checks, historical CSVs and absent software license.

### Verification

- README API snippet: `BP utilization: 1.000000`.
- README BP/AISI316L command: succeeded with output directed to `/tmp/wg43-readme-example`; R=0 strengths correctly reported as estimates.
- Existing unittest suite: 20 passed; existing Matplotlib deprecation warnings remain.
- Generator freshness/ID/registry/DOI evidence/51-publication coverage checks passed, including exact equality with the inherited 161-ID set and valid unique roadmap ranks.
- Current documentation relative-file and fragment links passed; whitespace check passed.
- No numerical implementation, experimental workbook or archived result changed. No broad literature search or DOI re-verification was performed.

### Remaining collaboration gaps

No live method Issues exist as checked during this task; the connector provides no Issue/label creation operation. Sixteen prepared briefs remain versioned, and each method now offers direct search/proposal links. Post selected tasks and add actual Issue URLs to the JSON. Sixteen missing counted candidates have no verified original DOI; some have traceable historical sources and others need exact primary/variant identification. Full equations, benchmarks and measured parameters still require method-specific checks. Repository reuse terms need a maintainer-selected license.


Original path: `docs/catalogue/external-code-checkpoint.md`

## FABER scope and external-code checkpoint — 15 October 2026

Baseline: GitHub main `81ca6b963cc366ed52e7987d9e02cadcf4cf399d`, tree `a10d26ed71b1608b95cb98d72eafc7010ef4fd32`; previous PR #2 merged. Branch: `docs/faber-scope-external-code`.

### Scope and outputs

README now identifies FABER Working Group 4.3 and support for a scientific review article in preparation. Present phase: CA multiaxial fatigue of plain/smooth geometries, P/NP only where each method supports it, without explicit notches, cracks or significant gradients. VA, richer histories and geometry/structural extensions are potential future directions, not capabilities or commitments. Per-method scope tags carry this distinction into the catalogue, roadmap and contributor workflow.

The JSON remains the source of truth, now including project scope, external-source entities, method links and discovery states. A generated external inventory and CSV expose variants, paths/revisions, dependencies, license evidence, testing limits and potential use. Detailed catalogue records are generated by family to keep pages readable; root method anchors remain stable.

### Search and findings

The saved query register covers 117/117 counted method/scoped records with one named query each, plus stronger targeted queries and primary-source inspection for useful leads. This is a bounded first pass, not comprehensive code indexing or proof of absence. Generic search hits, physiological fatigue and load-flow visualization homonyms were rejected. The 117 are not a final independent-theory count.

- Six counted records: confirmed accessible corresponding or explicitly bounded-variant source (FS, Findley, Crossland, Sines, COIN-LiWI, time-derivative energy/G35).
- Ten counted records: related/unverified implementations, supporting helpers or documented-but-unretrieved numerical source.
- 101 counted records: no accessible corresponding source identified after searching; no nonexistence claim.
- Two additional future workstreams: author ECP code (C04) and ASU random-spectrum code with a CA driver (C09), outside the 117 denominator.
- Fifteen source/lead records, including one unmapped related ASU energy source and one inaccessible Zenodo lead. Six projects have potentially useful licensed current-scope code/helpers; ECP is a seventh licensed future-geometry candidate. License compatibility remains unresolved because the receiving project has no selected license.

MATLAB, Python and C files were inspected. Code_Aster is a Python/Fortran ecosystem lead; only its command interface was read, not its numerical kernels. Unknown-license ASU code remains reference-only pending permission. FLife COIN-LiWI uses amplitude spectra, while its Carpinteri–Spagnoli implementation is a spectral variant. A 2006 strain law and 2020 energy law were not relabelled as differently cited catalogue criteria.

### Verification boundary and next steps

No third-party source was executed, copied, translated or integrated. Confirmed availability is not equation reproduction or predictive validation. The main implementation counts and independent validation states remain unchanged. All 161 inherited records and 51 review dispositions remain preserved.

The direct pinned GitHub links for confirmed sources were successfully read. Actual source files and licensing evidence were checked where stated; inaccessible/metadata-only cases remain explicitly limited. Existing tests and documentation generation/link checks are run before publication. No raw workbook, archived result or numerical model changes are intended.

There are no live method Issues as checked during this task. Relevant prepared Issue briefs now include external-source and scope links; a maintainer can post selected tasks and add returned URLs. The connector has no Issue/label creation operation. Prioritize independent FS/Findley checks, Crossland/Sines specification with openfat as an unvalidated comparator, and COIN-LiWI kernel/wrapper verification. Obtain permission before porting ASU G35 or its data. Preserve ECP for future geometry work.
