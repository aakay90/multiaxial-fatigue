"""Cross-batch statistics of every method on the batches of one material (issue #71).

A family of batches of one material is declared in ``examples/data/material_families.json``.
Every method is run twice on each batch:

- **own batch**: calibrated and assessed on the same batch (the ordinary pipeline run);
- **transfer**: the batch predicted from each other batch of the family
  (``multifat-pipeline --design-material``), with the Summary, constants, design set and master
  curve of the design batch.

The statistic is the load-equivalent error e = Error_load = ln(1/s*) of the assessed failures
(Flag 1), grouped by loading path (A, T, AT-IP, AT-NP, with "+mean" for a non-zero mean stress):

- per method, batch and path: n, bias = mean(e) with a 95 % percentile-bootstrap interval, SD,
  RMS and the share within +-20 % of the load;
- per method and path: Kruskal-Wallis test of equal errors across batches, Benjamini-Hochberg q
  over the methods;
- per path: additive decomposition of the cell means,
  bias_mb = mu + alpha_m + beta_b + (alpha beta)_mb, on the methods present on every batch of
  that path (batch offsets beta_b, interaction RMS, compared with the standard error of a cell);
- transfer: the same statistics per design -> target pair, and the RMS change on the tests the
  own-batch run assesses (paired by Observation_id);
- a method-free reference: Basquin fits of the R = -1 axial and torsion failures of each batch
  and their ratio tau_a / sigma_a at 1e5 and 1e6 cycles.

The results are written to ``examples/data/batch_comparison/<family>/`` (CSV, LaTeX tables and a
manifest) and ``docs/images/batch_comparison_<family>_*.png``. The manifest records the
registered models, the implementation revision and the dataset fingerprints; ``check`` (run by
``tests/test_batch_comparison.py``) fails when a method or a workbook has changed since, so the
results are regenerated with every new method or data change:

    uv run python examples/batch_comparison.py all <tmp_dir> --jobs 4   # run + analyse
    uv run python examples/batch_comparison.py run <tmp_dir> --jobs 4   # pipeline runs only
    uv run python examples/batch_comparison.py analyse <tmp_dir>        # statistics and figures
    uv run python examples/batch_comparison.py check                    # committed results current?

Caveats: the points of one S-N curve are not independent (one machine, one lot), so the p-values
are optimistic; the own-batch errors are measured with a design set from the same batch.
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from itertools import combinations, permutations
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.style import DATA_DIR, DOCS_IMG_DIR, apply_academic_style  # noqa: E402

FAMILIES_FILE = DATA_DIR / "material_families.json"
OUT_ROOT = DATA_DIR / "batch_comparison"
SEED = 20261110  # bootstrap seed, fixed for reproducible intervals
N_BOOT = 4000
MIN_N = 3  # smallest group entering a test or a decomposition
WITHIN = 0.2  # share of failures within +-20 % of the load
PATH_NAMES = {
    "Tensile": "A",
    "Torsion": "T",
    "Multiaxial proportional": "AT-IP",
    "Multiaxial non-proportional": "AT-NP",
}
PATH_ORDER = ["A", "A+mean", "T", "T+mean", "AT-IP", "AT-IP+mean", "AT-NP", "AT-NP+mean"]
# Validated categorical palette (dataviz skill, light surface): blue, orange, aqua; markers give
# the batch identity without colour.
BATCH_COLOURS = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"]
BATCH_MARKERS = ["o", "s", "^", "D"]


# ---- families and inputs -------------------------------------------------------------------
def families() -> dict:
    data = json.loads(FAMILIES_FILE.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def registered_models() -> list[str]:
    from multifat.cli.pipeline import _every_model

    return sorted(_every_model())


def dataset_fingerprints(batches) -> dict:
    from multifat.cli import run as runmod
    from multifat.report.subsets import dataset_fingerprint

    out = {}
    for b in batches:
        data, mat = runmod.load_material(b)
        out[b] = dataset_fingerprint(data[mat])
    return out


def loading_paths(batches) -> pd.DataFrame:
    """Loading path of every failure and run-out, keyed by (Batch, Observation_id)."""
    from multifat.cli import run as runmod
    from multifat.report.subsets import observation_index

    rows = []
    for b in batches:
        data, mat = runmod.load_material(b)
        block = data[mat]
        index = observation_index(block)
        for kind, group in (("case", block["cases"]), ("runout", block.get("runouts", {}))):
            for cid, case in group.items():
                H = case["harmonics"]
                label = PATH_NAMES.get(
                    runmod.classify_loading_type(H=H, meta=case.get("meta", {})), "?"
                )
                if np.max(np.abs(np.asarray(H["S_mean"], float))) > 1e-6:
                    label += "+mean"
                rows.append(
                    dict(Batch=b, Observation_id=index[(kind, int(cid))]["Observation_id"],
                         Path=label)
                )  # fmt: skip
    return pd.DataFrame(rows)


# ---- pipeline runs -------------------------------------------------------------------------
def _pipeline(args: list[str]) -> int:
    cmd = [sys.executable, "-m", "multifat.cli.pipeline", *args, "--no-compare"]
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


def run(out: Path, family: str, jobs: int, models: str) -> None:
    """Own-batch runs, then every ordered transfer, into out/<family>/{own,transfer}.

    A batch listed under the family's ``constants`` (a published-constants record, e.g. the SSF
    surface of 42CrMo4_Reis) is run with ``--constants`` on its own and as a design batch; those
    constants then reach the other batches only through the transfer.
    """
    spec = families()[family]
    batches, constants = spec["batches"], spec.get("constants", {})
    base = out / family
    common = ["--models", models, "--jobs", str(jobs)]

    def materials(names):
        return [arg for b in names for arg in ("--material", b)]

    def supplied(batch):
        return ["--constants", str(REPO_ROOT / constants[batch])] if batch in constants else []

    plain = [b for b in batches if b not in constants]
    codes = []
    if plain:
        codes.append(_pipeline([*materials(plain), *common, "--results-dir", str(base / "own")]))
    for b in (b for b in batches if b in constants):
        codes.append(
            _pipeline([*materials([b]), *supplied(b), *common, "--results-dir", str(base / "own")])
        )
    for design in batches:
        others = [b for b in batches if b != design]
        codes.append(
            _pipeline(
                [*materials(others), "--design-material", design, *supplied(design), *common,
                 "--results-dir", str(base / "transfer")]
            )
        )  # fmt: skip
    if any(codes):  # a failed model is reported in the run reports; the others are usable
        print(f"warning: pipeline exit codes {codes}; see the *_run_report.tsv files")


def read_results(folder: Path, materials: dict[str, tuple[str, str | None]]) -> pd.DataFrame:
    """Rows of the base-variant CSVs of `materials` {material id: (target, design or None)}."""
    frames = []
    for path in sorted(folder.glob("*.csv")):
        head = pd.read_csv(path, nrows=1)
        if not {"Method", "Material", "Flag", "Error_load"} <= set(head.columns):
            continue
        material, method = str(head["Material"].iloc[0]), str(head["Method"].iloc[0])
        if material not in materials or method.endswith("_ext"):
            continue
        frame = pd.read_csv(path)
        target, design = materials[material]
        frame["Batch"], frame["Design"] = target, design or target
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    d = pd.concat(frames, ignore_index=True)
    d["Error_load"] = pd.to_numeric(d["Error_load"], errors="coerce")
    return d


# ---- statistics ----------------------------------------------------------------------------
def bootstrap_mean_ci(x: np.ndarray, rng: np.random.Generator) -> tuple[float, float]:
    """95 % percentile-bootstrap interval of the mean (NaN below MIN_N values)."""
    if x.size < MIN_N:
        return (np.nan, np.nan)
    means = x[rng.integers(0, x.size, size=(N_BOOT, x.size))].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


def cell_statistics(d: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """n, bias (with bootstrap interval), SD, RMS and share within +-20 % per group of `keys`."""
    rng = np.random.default_rng(SEED)
    rows = []
    for key, g in d.groupby(keys, sort=True):
        e = g["Error_load"].to_numpy(float)
        e = e[np.isfinite(e)]
        if e.size == 0:
            continue
        lo, hi = bootstrap_mean_ci(e, rng)
        rows.append(
            {**dict(zip(keys, key)), "n": int(e.size), "bias": e.mean(), "bias_lo": lo,
             "bias_hi": hi, "sd": e.std(ddof=1) if e.size > 1 else np.nan,
             "rms": float(np.sqrt(np.mean(e**2))),
             "within_20pct": float(np.mean(np.abs(np.expm1(e)) <= WITHIN))}
        )  # fmt: skip
    return pd.DataFrame(rows)


def benjamini_hochberg(p) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values (q), NaN entries left NaN."""
    p = np.asarray(p, float)
    q = np.full_like(p, np.nan)
    ok = np.isfinite(p)
    if ok.any():
        order = np.argsort(p[ok])
        ranked = p[ok][order] * ok.sum() / np.arange(1, ok.sum() + 1)
        ranked = np.minimum.accumulate(ranked[::-1])[::-1]
        out = np.empty_like(ranked)
        out[order] = np.minimum(ranked, 1.0)
        q[ok] = out
    return q


def batch_effect(d: pd.DataFrame) -> pd.DataFrame:
    """Kruskal-Wallis test of equal errors across batches, per method and path."""
    from scipy import stats

    rows = []
    for (method, path), g in d.groupby(["Method", "Path"], sort=True):
        groups = {
            b: x["Error_load"].to_numpy(float)[np.isfinite(x["Error_load"].to_numpy(float))]
            for b, x in g.groupby("Batch")
        }
        groups = {b: v for b, v in groups.items() if v.size >= MIN_N}
        if len(groups) < 2:
            continue
        test = stats.kruskal(*groups.values())
        means = {b: float(v.mean()) for b, v in groups.items()}
        rows.append(
            dict(Method=method, Path=path, batches="+".join(groups),
                 n="+".join(str(v.size) for v in groups.values()),
                 spread=max(means.values()) - min(means.values()), H=float(test.statistic),
                 p=float(test.pvalue))
        )  # fmt: skip
    t = pd.DataFrame(rows)
    if len(t):
        t["q_BH"] = np.nan
        for path, idx in t.groupby("Path").groups.items():  # one family of tests per path
            t.loc[idx, "q_BH"] = benjamini_hochberg(t.loc[idx, "p"])
    return t


def two_way(cells: pd.DataFrame, batches: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Additive decomposition of the cell biases per path (methods present on >= 2 batches).

    Returns the per-path summary (offsets, interaction RMS, cell SE, method-effect SD) and the
    per-cell interaction residuals.
    """
    summary, residuals = [], []
    for path, g in cells[cells["n"] >= MIN_N].groupby("Path", sort=False):
        full = g.pivot(index="Method", columns="Batch", values="bias")
        available = [b for b in batches if b in full and full[b].notna().sum() >= 2]
        # every subset of >= 2 batches, largest first: the methods complete on that subset
        subsets = [c for k in range(len(available), 1, -1) for c in combinations(available, k)]
        for present in map(list, subsets):
            row, res = _decompose(g, full[present].dropna(), present, path)
            if row is None:
                continue
            summary.append(row)
            if len(present) == len(available):  # residuals of the largest subset only
                residuals.append(res)
    return pd.DataFrame(summary), (pd.concat(residuals) if residuals else pd.DataFrame())


def _decompose(g: pd.DataFrame, table: pd.DataFrame, present: list[str], path: str):
    """One additive fit of a complete method x batch table of biases."""
    if len(table) < MIN_N:  # too few methods for a method effect and an interaction
        return None, None
    sd = g.pivot(index="Method", columns="Batch", values="sd").loc[table.index, present]
    n = g.pivot(index="Method", columns="Batch", values="n").loc[table.index, present]
    mu = float(table.to_numpy().mean())
    alpha = table.mean(axis=1) - mu
    beta = table.mean(axis=0) - mu
    res = table - mu - alpha.to_numpy()[:, None] - beta.to_numpy()[None, :]
    cell_se = float(np.sqrt(np.nanmean((sd**2 / n).to_numpy())))
    row = dict(Path=path, batches="+".join(present), n_methods=len(table), mu=mu,
               interaction_rms=float(np.sqrt(np.mean(res.to_numpy() ** 2))),
               cell_se=cell_se, method_sd=float(alpha.std(ddof=1)))  # fmt: skip
    row.update({f"offset_{b}": float(beta[b]) for b in present})
    long = res.reset_index().melt(id_vars="Method", var_name="Batch", value_name="residual")
    return row, long.assign(Path=path)


def transfer_penalty(own: pd.DataFrame, moved: pd.DataFrame) -> pd.DataFrame:
    """RMS of the own-batch and transfer errors on the same tests (own-batch Flag 1, paired)."""
    a = own[own["Flag"] == 1][["Method", "Batch", "Observation_id", "Error_load"]]
    b = moved[moved["Flag"] == 1][["Method", "Batch", "Design", "Observation_id", "Error_load"]]
    j = b.merge(a, on=["Method", "Batch", "Observation_id"], suffixes=("_transfer", "_own"))
    j = j[np.isfinite(j["Error_load_transfer"]) & np.isfinite(j["Error_load_own"])]
    rows = []
    for (method, design, target), g in j.groupby(["Method", "Design", "Batch"], sort=True):
        if len(g) < MIN_N:
            continue
        rms_own = float(np.sqrt(np.mean(g["Error_load_own"] ** 2)))
        rms_tr = float(np.sqrt(np.mean(g["Error_load_transfer"] ** 2)))
        rows.append(
            dict(Method=method, Design=design, Target=target, n=len(g),
                 bias_own=float(g["Error_load_own"].mean()),
                 bias_transfer=float(g["Error_load_transfer"].mean()), rms_own=rms_own,
                 rms_transfer=rms_tr, penalty=rms_tr - rms_own)
        )  # fmt: skip
    return pd.DataFrame(rows)


def batch_reference(batches) -> pd.DataFrame:
    """Method-free Basquin fits of the R = -1 tension and torsion failures of each batch."""
    from multifat.cli import run as runmod
    from multifat.eval.material_fits import reversed_uniaxial_tests

    rows = []
    for b in batches:
        data, mat = runmod.load_material(b)
        tests = reversed_uniaxial_tests(data, mat)
        fits = {}
        for family, (_, amp, N) in tests.items():
            if len(amp) < MIN_N:
                continue
            slope, intercept = np.polyfit(np.log10(N), np.log10(amp), 1)
            fits[family] = (10**intercept, slope)
            rows.append(
                dict(Batch=b, curve=family, n=len(amp), A_MPa=10**intercept, b=slope,
                     N_min=min(N), N_max=max(N))
            )  # fmt: skip
        if {"tension", "torsion"} <= fits.keys():
            for N in (1e5, 1e6):
                ratio = (fits["torsion"][0] * N ** fits["torsion"][1]) / (
                    fits["tension"][0] * N ** fits["tension"][1]
                )
                rows.append(dict(Batch=b, curve=f"tau/sigma at {N:.0e}", n=np.nan, A_MPa=ratio))
    return pd.DataFrame(rows)


# ---- analysis, figures, tables ---------------------------------------------------------------
def analyse(out: Path, family: str) -> Path:
    spec = families()[family]
    batches = spec["batches"]
    from multifat.cli.run import transfer_material_id

    base = out / family
    own = read_results(base / "own", {b: (b, None) for b in batches})
    moved = read_results(
        base / "transfer",
        {transfer_material_id(t, dsg): (t, dsg) for t, dsg in permutations(batches, 2)},
    )
    if own.empty:
        raise SystemExit(f"no own-batch results in {base / 'own'}; run first")
    paths = loading_paths(batches)
    own = own.merge(paths, on=["Batch", "Observation_id"], how="left", validate="m:1")
    if not moved.empty:
        moved = moved.merge(paths, on=["Batch", "Observation_id"], how="left", validate="m:1")
    dest = OUT_ROOT / family
    dest.mkdir(parents=True, exist_ok=True)

    assessed = own[own["Flag"] == 1]
    cells = cell_statistics(assessed, ["Method", "Batch", "Path"])
    effect = batch_effect(assessed)
    decomposition, residuals = two_way(cells, batches)
    if len(residuals):
        cells = cells.merge(residuals, on=["Method", "Batch", "Path"], how="left")
    write = dict(index=False, float_format="%.5g")
    cells.to_csv(dest / "own_cells.csv", **write)
    effect.to_csv(dest / "own_batch_effect.csv", **write)
    decomposition.to_csv(dest / "own_two_way.csv", **write)
    batch_reference(batches).to_csv(dest / "batch_reference.csv", **write)
    penalty = pd.DataFrame()
    if not moved.empty:
        tcells = cell_statistics(moved[moved["Flag"] == 1], ["Method", "Design", "Batch", "Path"])
        tcells.rename(columns={"Batch": "Target"}).to_csv(dest / "transfer_cells.csv", **write)
        penalty = transfer_penalty(own, moved)
        penalty.to_csv(dest / "transfer_penalty.csv", **write)
    _latex_tables(dest, decomposition, penalty, batches)
    _figure_bias(cells, batches, family)
    if len(penalty):
        _figure_transfer(penalty, batches, family)
    manifest = dict(
        family=family, batches=batches, notes=spec.get("notes", ""),
        constants=spec.get("constants", {}),
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        git_commit=_git("rev-parse", "HEAD"), registered_models=registered_models(),
        implementation_revision=_revision(), dataset_fingerprints=dataset_fingerprints(batches),
        methods_with_results=sorted(own["Method"].unique()),
        statistic="Error_load = ln(1/s*), assessed failures (Flag 1)", bootstrap=[N_BOOT, SEED],
    )  # fmt: skip
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(f"results -> {dest}")
    return dest


def _git(*flags) -> str | None:
    proc = subprocess.run(["git", *flags], cwd=REPO_ROOT, capture_output=True, text=True)
    return proc.stdout.strip() or None


def _revision() -> str:
    from multifat.models.references import IMPLEMENTATION_REVISION

    return IMPLEMENTATION_REVISION


def _short(batch: str, family: str) -> str:
    return batch.removeprefix(family + "_") or batch


def _latex_tables(dest: Path, decomposition, penalty, batches) -> None:
    family = dest.name
    lines = [
        r"\begin{tabular}{llrr" + "r" * len(batches) + "rr}",
        r"\hline",
        "Path & Batches & Methods & "
        + " & ".join(rf"$\beta_{{\mathrm{{{_short(b, family)}}}}}$" for b in batches)
        + r" & Interaction RMS & Cell SE & Method SD \\",
        r"\hline",
    ]
    for _, r in decomposition.iterrows():
        offsets = " & ".join(
            f"{r[f'offset_{b}']:+.3f}" if pd.notna(r.get(f"offset_{b}")) else "--" for b in batches
        )
        lines.append(
            f"{r['Path']} & {r['batches'].count('+') + 1} & {r['n_methods']} & {offsets} & "
            f"{r['interaction_rms']:.3f} & {r['cell_se']:.3f} & {r['method_sd']:.3f} \\\\"
        )
    lines += [r"\hline", r"\end{tabular}"]
    (dest / "own_two_way.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if penalty.empty:
        return
    s = (
        penalty.groupby("Method")
        .apply(
            lambda g: pd.Series(
                dict(pairs=len(g), rms_own=np.sqrt(np.average(g.rms_own**2, weights=g.n)),
                     rms_transfer=np.sqrt(np.average(g.rms_transfer**2, weights=g.n)))
            ),
            include_groups=False,
        )
        .sort_values("rms_transfer")
    )  # fmt: skip
    s["penalty"] = s["rms_transfer"] - s["rms_own"]
    s.to_csv(dest / "transfer_summary.csv", float_format="%.5g")
    rows = [r"\begin{tabular}{lrrrr}", r"\hline",
            r"Method & Pairs & RMS own & RMS transfer & $\Delta$ \\", r"\hline"]  # fmt: skip
    for m, r in s.iterrows():
        rows.append(
            f"{m} & {int(r.pairs)} & {r.rms_own:.3f} & {r.rms_transfer:.3f} & {r.penalty:+.3f} \\\\"
        )
    rows += [r"\hline", r"\end{tabular}"]
    (dest / "transfer_summary.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _figure_bias(cells: pd.DataFrame, batches, family: str) -> None:
    """Own-batch bias with 95 % interval per method, one panel per path shared by >= 2 batches."""
    import matplotlib.pyplot as plt

    apply_academic_style()
    shared = [
        p
        for p in PATH_ORDER
        if cells[(cells["Path"] == p) & (cells["n"] >= MIN_N)]["Batch"].nunique() >= 2
    ]
    if not shared:
        return
    methods = sorted(cells["Method"].unique())
    fig, axes = plt.subplots(
        1, len(shared), figsize=(2.6 * len(shared) + 1.2, 0.2 * len(methods) + 1.4), sharey=True
    )
    axes = np.atleast_1d(axes)
    y = {m: i for i, m in enumerate(methods)}
    handles = {}
    for ax, path in zip(axes, shared):
        sub = cells[(cells["Path"] == path) & (cells["n"] >= MIN_N)]
        counts = []
        for k, b in enumerate(batches):
            g = sub[sub["Batch"] == b]
            if g.empty:
                continue
            counts.append(f"{_short(b, family)} {int(g['n'].max())}")
            yy = np.array([y[m] for m in g["Method"]]) + (k - (len(batches) - 1) / 2) * 0.22
            handles[b] = ax.errorbar(
                g["bias"], yy,
                xerr=[g["bias"] - g["bias_lo"], g["bias_hi"] - g["bias"]],
                fmt=BATCH_MARKERS[k], ms=3.2, lw=0.8, color=BATCH_COLOURS[k],
            )  # fmt: skip
        ax.axvline(0.0, color="#52514e", lw=0.8)
        for x in (np.log(1 / 1.2), np.log(1 / 0.8)):  # +-20 % of the load
            ax.axvline(x, color="#888888", lw=0.5, ls=":")
        ax.set_title(f"{path}\n" + r"$n$: " + ", ".join(counts), fontsize=9)
        ax.set_xlabel(r"bias $\bar e_L = \overline{\ln(1/s^*)}$")
        ax.grid(axis="x", color="#dddddd", lw=0.5)
    fig.legend(
        [handles[b] for b in batches if b in handles],
        [_short(b, family) for b in batches if b in handles],
        loc="upper center", ncol=len(handles), bbox_to_anchor=(0.5, 0.965), frameon=False,
    )  # fmt: skip
    axes[0].set_yticks(range(len(methods)), methods, fontsize=7)
    axes[0].invert_yaxis()
    fig.suptitle(
        f"{family}: own-batch load error by loading path (mean, 95 % bootstrap interval; "
        "dotted: $\\pm$20 % of the load)",
        y=0.995,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(DOCS_IMG_DIR / f"batch_comparison_{family}_bias.png", dpi=200)
    plt.close(fig)


def _figure_transfer(penalty: pd.DataFrame, batches, family: str) -> None:
    """RMS of the load error, own batch and predicted from each other batch, on the same tests."""
    import matplotlib.pyplot as plt

    apply_academic_style()
    cols, labels = [], []
    for t in batches:
        cols.append((t, None))
        labels.append(f"{_short(t, family)}\nown")
        for dsg in batches:
            if dsg != t:
                cols.append((t, dsg))
                labels.append(f"{_short(t, family)}\nfrom {_short(dsg, family)}")
    methods = sorted(penalty["Method"].unique())
    grid = np.full((len(methods), len(cols)), np.nan)
    for i, m in enumerate(methods):
        for j, (t, dsg) in enumerate(cols):
            g = penalty[(penalty["Method"] == m) & (penalty["Target"] == t)]
            if dsg is None:
                g = g.drop_duplicates("Target")
                value = g["rms_own"]
            else:
                value = g[g["Design"] == dsg]["rms_transfer"]
            if len(value):
                grid[i, j] = float(value.iloc[0])
    fig, ax = plt.subplots(figsize=(1.0 * len(cols) + 2.0, 0.2 * len(methods) + 1.6))
    vmax = float(np.nanpercentile(grid, 98)) if np.isfinite(grid).any() else 1.0
    image = ax.imshow(grid, cmap="Blues", vmin=0.0, vmax=vmax, aspect="auto")
    for i in range(len(methods)):
        for j in range(len(cols)):
            if np.isfinite(grid[i, j]):
                ax.text(
                    j, i, f"{grid[i, j]:.2f}", ha="center", va="center", fontsize=5.5,
                    color="white" if grid[i, j] > 0.6 * vmax else "#0b0b0b",
                )  # fmt: skip
    ax.set_xticks(range(len(cols)), labels, fontsize=6.5)
    ax.set_yticks(range(len(methods)), methods, fontsize=7)
    for j in range(1, len(cols)):
        if cols[j][1] is None:
            ax.axvline(j - 0.5, color="white", lw=2)
    fig.colorbar(image, ax=ax, shrink=0.6, label=r"RMS of $e_L$ (same tests)")
    ax.set_title(f"{family}: own-batch versus cross-batch prediction")
    fig.tight_layout()
    fig.savefig(DOCS_IMG_DIR / f"batch_comparison_{family}_transfer.png", dpi=200)
    plt.close(fig)


# ---- staleness check -----------------------------------------------------------------------
def check(family: str | None = None) -> list[str]:
    """Reasons the committed results are out of date (empty list: current)."""
    problems = []
    for name, spec in families().items():
        if family and name != family:
            continue
        path = OUT_ROOT / name / "manifest.json"
        if not path.exists():
            problems.append(f"{name}: no results ({path.relative_to(REPO_ROOT)})")
            continue
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest["batches"] != spec["batches"]:
            problems.append(f"{name}: batches changed")
        if manifest.get("constants", {}) != spec.get("constants", {}):
            problems.append(f"{name}: supplied constants changed")
        added = sorted(set(registered_models()) - set(manifest["registered_models"]))
        removed = sorted(set(manifest["registered_models"]) - set(registered_models()))
        if added or removed:
            problems.append(f"{name}: models added {added}, removed {removed}")
        if manifest["implementation_revision"] != _revision():
            problems.append(f"{name}: implementation revision changed")
        now = dataset_fingerprints(spec["batches"])
        changed = [b for b in spec["batches"] if manifest["dataset_fingerprints"].get(b) != now[b]]
        if changed:
            problems.append(f"{name}: datasets changed {changed}")
    return problems


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=["run", "analyse", "all", "check"])
    parser.add_argument("out", type=Path, nargs="?", help="folder of the pipeline runs")
    parser.add_argument("--family", default=None, help="one family (default: all)")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--models", default="all")
    args = parser.parse_args(argv)
    if args.action == "check":
        problems = check(args.family)
        for p in problems:
            print(p)
        if problems:
            raise SystemExit("rerun: uv run python examples/batch_comparison.py all <tmp_dir>")
        print("batch comparison results are current")
        return
    if args.out is None:
        parser.error(f"{args.action} needs the run folder")
    for family in [args.family] if args.family else list(families()):
        if args.action in ("run", "all"):
            run(args.out, family, args.jobs, args.models)
        if args.action in ("analyse", "all"):
            analyse(args.out, family)


if __name__ == "__main__":
    main()
