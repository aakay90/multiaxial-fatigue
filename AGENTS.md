# Working on this repository

- Begin each development session by reading `docs/audit-checkpoint.md`, checking Git status, recent commits and any existing PR, and verifying that the checkpoint matches the source. Continue from its first unfinished task. Do not repeat completed audits or create a competing progress file.
- At each meaningful milestone, run focused checks, update that checkpoint with the actual result, modified files, remaining work, blockers and exact next action, then commit and push verified progress when authorised. Record untested changes explicitly before an interruption. Keep scientific validation distinct from software regression. Preserve uncommitted work and use the existing branch and PR when appropriate. Do not force-push or merge without the user's instruction.

- Preserve the existing numerical behavior unless the task explicitly asks to change it. Check the experimental workbook schema and CSV output columns before editing shared data flow.
- Add a critical-plane method in `fatigue/models/cp_methods/`; add a direct method in `fatigue/models/invariant_methods/` or `fatigue/models/energy_based_methods/`. Register new methods in `fatigue/models/registry.py`.
- Follow `docs/adding-methods.md` for model interfaces and naming conventions, including `_ext` variants. See `docs/architecture.md` for the data flow.
- The three numbered scripts are current entry points. Run them from the repository root because data and output paths are relative to it.
- Do not commit Python caches or `Results/Comparison/`. Treat the existing `Results/*.csv` files as reference outputs; review their diff if a run overwrites them.
- For a new method or numerical change, add focused tests or a reproducible comparison against existing results. Do not claim validation solely from import or syntax checks.
