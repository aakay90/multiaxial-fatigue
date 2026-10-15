# Repository cleanup audit — 15 October 2026

Baseline: public `andreachiocca/multiaxial-fatigue`, remote `main`
`68df1342a539cae45503ef6f0f55f50031e1cb08`, tree
`dd7797c2f39f4ff1e3f614d60d137983f7c0ef47`. The starting local tree
matched exactly. Scope: 198 tracked files, including 44 Python files, four
experimental workbooks and 88 historical result CSVs. This is maintenance for
the FABER WG4.3 review and collaborative framework, whose present scope is
constant-amplitude multiaxial loading of plain/smooth geometries.

## Findings and disposition

| Classification | Finding | Action |
|---|---|---|
| Safe to remove | Unused imports, duplicated imports, 150-line commented plotting prototype and hypothetical registry entries | Removed; original code remains in Git history. Public calculation/plotting functions retained. |
| Consolidate | Fourteen identical tensor input validators | One `fatigue/models/utils/tensors.py` implementation, retaining existing `_as33` aliases. Conversion, shape check and exception text are unchanged. |
| Consolidate | Three operational checkpoints mixed with live catalogue data | Complete content retained in [documentation history](research/documentation-history.md); old checkpoint files removed. |
| Improve | Catalogue-only CI, unignored quick-start outputs, deprecated plotting calls | One quality workflow adds unit tests, dependency consistency, narrow Ruff checks and local documentation checks. Ignore fresh output directories. Replace deprecated plotting APIs. |
| Verify before removal | Five disabled criteria and five active methods requiring source review | Preserve source, guards and scientific tasks. Disabled code is not dead research; repair requires source-faithful numerical work. |
| Preserve | Workbooks, 88 historical CSVs, numerical audit, 51-publication review, 161-ID research inventory, external-code/license evidence | No scientific data, catalogue entry, equation, validation claim or reference discarded. [Results guidance](../Results/README.md) distinguishes history from current evidence. |
| Preserve | Existing public interfaces, method-specific constitutive/amplitude conventions, calibration and reporting | No architectural migration. Similar-looking scientific calculations were not merged without proof of equivalence. |

All four runtime dependencies (`numpy`, `pandas`, `openpyxl`, `matplotlib`) are
used, so none was removed. Ruff is isolated in `requirements-dev.txt`. It checks
unused imports, redefinitions and undefined names; no mass formatter or broad
style migration is imposed. No tracked caches, binaries, temporary plots or
debug artifacts required deletion. The three numbered entry scripts stay at
the root to preserve their working-directory and public usage conventions.

## Scientific behavior and checks

- Before: all 20 tests pass; material sweep passes 64 model/material runs and
  3,936 rows, writing outside the repository.
- After: all 20 tests pass; the same 64 runs and 3,936 rows pass. Every parsed CSV
  field compares exactly with the baseline (`pandas.assert_frame_equal`,
  `check_exact=True`), including calibration fits, damage, life and metadata.
- AST comparison of every pre-existing `fatigue` module confirms unchanged
  executable structure after excluding imports and the extracted `_as33`
  definitions. Each extracted validator's body was separately checked identical.
- Generator checks retain 161 IDs, 117 counted records, 51/51 review coverage,
  registry/evidence paths, independent implementation/validation statuses and
  generated output freshness. Catalogue counts and roadmap selections are unchanged.
- Ruff, dependency consistency and local documentation checks pass. The latter
  excludes external URLs, code spans/fences and frozen research/catalogue prose;
  it is not an external-link availability or scientific correctness certificate.
- Matplotlib deprecation warnings from colormap lookup and boxplot labels are
  resolved. Existing warnings about estimated material properties remain useful.

No numerical behavior change or criterion defect fix is intended or observed.
Plotting changes retain the same colormap and explicit box positions/labels;
the existing plotting pipeline test passes. Numerical verification is still
distinct from independent published/experimental validation.

Comparison environment: NumPy 2.3.5, pandas 2.2.3, openpyxl 3.1.5,
Matplotlib 3.10.8, Ruff 0.14.2. All 64 CSVs are also byte-identical. The aggregate
SHA-256 of sorted filename + NUL + file-content sequences is
`5168411a6a804f7c0f17b29d099925c010bb96c538179362d93f2cfd2614387f`.

Reproduce from the repository root:

```bash
python -m pip install -r requirements-dev.txt
python -m pip check
python -m ruff check .
MPLBACKEND=Agg python -m unittest discover -s tests -v
python tools/generate_method_docs.py --check
python tools/check_docs.py
MPLBACKEND=Agg python tests/run_material_validation.py /tmp/wg43-validation
```

## Branch, Issue and PR audit

`git ls-remote --heads --tags origin` and a fresh fetch found four remote
branches and no remote tags. The releases endpoint reported no releases.
All existing PRs (#1, #2, #3) are merged; no open PRs or standalone Issues exist.
There are no obsolete live tasks to close. The 16 prepared method briefs remain
available; they must not be described as live Issues. Existing templates already
cover formulation, scope, independent evidence and third-party licensing.

| Branch | Classification | Evidence / action |
|---|---|---|
| Remote `main` | KEEP — default | Stable publication branch; baseline SHA above. |
| `chore/repository-cleanup` | KEEP — active | Cleanup feature branch based directly on fetched remote `main`; publish through a PR. |
| `docs/wg43-method-catalogue` | DELETE — verified merged | PR #1; tip `7e6db11`; zero unique commits against remote `main`, verified by ancestry and `rev-list`. Local counterpart removed. Remote deletion pending credentials/capability. |
| `docs/contributor-readme-reconciliation` | DELETE — verified merged | PR #2; tip `9874eaa`; same checks; local counterpart removed. Remote deletion pending. |
| `docs/faber-scope-external-code` | DELETE — verified merged | PR #3; tip `6ee5c34`; same checks and identical final tree to `main`; local counterpart removed. Remote deletion pending. |
| Legacy local `main` | ARCHIVE / preserve for review | Tip `32d1118` belongs to the earlier local source-history chain, whose publication commits have different IDs. Do not infer missing work from ancestry alone. Retained without resetting it. |

Before removing local feature pointers, local recovery tag
`archive/local-pre-cleanup-2026-10-15` retained `c1918d4` and its entire local
ancestor chain. Those three branch tips are ancestors of that tag. Remote
feature history is already reachable from merged `main`; no unique scientific
work or active branch was selected for deletion. No existing tag, release,
visibility setting or Git history was deleted or rewritten.

Direct Git fetch works, but the attempted remote branch deletion failed with
`could not read Username for 'https://github.com'`. The connected GitHub tools
can publish commits/PRs but expose neither ref deletion nor repository-setting
updates. Remote deletions therefore remain pending; they were not silently
treated as successful. After rechecking that no branch has advanced, an
authenticated maintainer can run:

```bash
git push origin --delete docs/wg43-method-catalogue docs/contributor-readme-reconciliation docs/faber-scope-external-code
```

## Remaining maintenance decisions

- Choose a software license with the rights holders. Public visibility does not
  establish reuse permission; no legal grant was invented during cleanup.
- Post selected prepared method Issues and link actual URLs into the catalogue.
  Current templates and per-method proposal links are usable without this step.
- Repository description and topics are currently empty; settings updates were
  unavailable. Suggested description: “FABER WG4.3 multiaxial fatigue review and
  collaborative Python assessment methods for constant-amplitude, smooth-specimen
  loading.” Suggested topics: `multiaxial-fatigue`, `fatigue`, `mechanical-engineering`,
  `scientific-computing`, `python`.
- Enable automatic deletion of merged feature branches in GitHub settings when
  desired. Default-branch protection is currently disabled; consider requiring
  the quality checks after the workflow has run successfully.
- Runtime versions remain unconstrained as before. A tested compatibility matrix
  or reproducible environment lock can follow if actual compatibility needs arise.
- Full source review, missing parameter/reference retrieval and independent
  validation remain scientific contribution opportunities, rather than cleanup
  tasks. No new fatigue criterion or literature review was started.

The repository has clearer maintenance checks and preserved scientific
traceability. It is technically approachable for external contributions;
licensing and live task publication remain organizational obstacles.
