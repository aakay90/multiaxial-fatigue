# Repository organization checkpoint — 15 October 2026

Baseline: public `andreachiocca/multiaxial-fatigue`, GitHub main `01418383ac2ab3cea8bab225f718dd652ba82820`. The original local HEAD was `32d1118`; all tracked blobs matched the remote tree, so no numerical work was missing or overwritten. Dedicated branch: `docs/wg43-method-catalogue`. GitHub publication uses a commit parented directly on the checked remote main; local source history is preserved.

## Completed

- Reused the 161-record master, full supplied review, 51/51 coverage, prior feasibility assessment, saved DOI identity records and numerical audit. No new literature search or DOI verification was performed.
- Central JSON contains 117 identifiable method/scoped candidates: 10 fully implemented for explicit repository scopes, five known partial/disabled, five active requiring source review, 97 missing. Forty-four bundled/overlapping/related/unresolved/workstream records remain traceable outside progress totals.
- Implementation and validation statuses are independent. No method is claimed independently scientifically validated. Archived disabled methods have guard-test evidence only and are marked not tested as fatigue implementations.
- Generated METHODS, roadmap, CSV, README progress table and 16 prepared contribution briefs from the JSON. Added contributor checklist, Issue/PR templates and a documentation freshness CI workflow. Application code/data/results were not changed.
- `MPLBACKEND=Agg python -m unittest discover -s tests -q`: 20 tests passed. Existing Matplotlib deprecation warnings remain.
- `python tools/generate_method_docs.py --check`: passes unique IDs, A–D values, canonical links, full registry coverage, source/test paths, saved DOI records and 51/51 review entries.
- Relative Markdown file links, `git diff --check` and credential-pattern scan passed. Only documentation/metadata/generator/CI changes are staged; no temporary outputs, article PDFs, caches, raw-data or archived-result changes.

## Remaining limitations

The available GitHub connector exposes no Issue or label creation operation. No live Issues/labels were created. Sixteen consistent bodies are prepared in `docs/contribution-issues/`; search for duplicates before posting and update JSON `issue_url` afterwards. Do not represent those briefs as open Issues.

Full-source mathematical checks remain pending for MGSE_ZHU, MKBM, LIU2021, LI and scalar MSWT. The five disabled methods require substantive repairs. Broad C workstream reference numbering was inconsistent in inherited notes and remains flagged. Historical identities and overlap checks need original sources; the literature search was not restarted. Eighty-five missing counted candidates have preliminary A/B feasibility; available equations and measured parameters must still be confirmed before coding.

The repository has no selected software license. Maintainers should choose one before representing reuse terms as established open-source licensing. No visibility or license change was made.

## Continue

Review/merge the documentation PR, post the selected prepared Issues and apply agreed labels, then obtain Papuga–Růžička (2008), DOI `10.1016/j.ijfatigue.2007.02.015`, for separately scoped PCR/PI work. Source-faithful review/repair of existing methods can proceed independently. Future numerical implementations must use individual evidence-backed tasks and preserve BP/CAIM and all-slope log damage reporting.
