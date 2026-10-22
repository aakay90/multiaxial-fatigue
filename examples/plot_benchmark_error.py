"""Model Benchmark Error Distribution Plot.

Generates a two-panel publication-grade horizontal bar chart comparing multiaxial
fatigue criteria on 42CrMo4-QT:
- Left panel: Log-error standard deviation s_ln (lower dispersion is better).
- Right panel: Mean log-error mu_ln (systematic bias, conservative vs unconservative).
"""

import sys
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

# Ensure repository root is on sys.path for direct script execution
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.style import DATA_DIR, DOCS_IMG_DIR, apply_academic_style


def plot_benchmark_error(
    csv_path: Path | None = None,
    out_path: Path | None = None,
) -> Path:
    """Generate two-panel horizontal benchmark ranking models by scatter and bias."""
    apply_academic_style()
    if csv_path is None:
        csv_path = DATA_DIR / "42CrMo4_QT_predictions.csv"
    if out_path is None:
        out_path = DOCS_IMG_DIR / "model_benchmark_error.png"

    df = pd.read_csv(csv_path)

    base_df = df[~df["Method"].str.endswith("_ext") & (df["Flag"] != 2)].copy()
    base_df = base_df[
        pd.to_numeric(base_df["Nf_exp"], errors="coerce").notna()
        & pd.to_numeric(base_df["Nf_expected"], errors="coerce").notna()
    ]
    n_tests = int(base_df.groupby("Method").size().max())

    family_labels: Dict[str, str] = {
        "cp_methods": "Critical Plane",
        "invariant_methods": "Invariant",
        "integral_methods": "Integral",
        "energy_based_methods": "Energy",
    }
    family_map: Dict[str, str] = {
        str(m): family_labels.get(str(f), "Critical Plane")
        for m, f in base_df[["Method", "Method_family"]].drop_duplicates().itertuples(index=False)
    }
    family_map["DANGVAN"] = "Mesoscopic"
    color_map: Dict[str, str] = {
        "Critical Plane": "#1B365D",
        "Invariant": "#C0392B",
        "Mesoscopic": "#E67E22",
        "Integral": "#27AE60",
        "Energy": "#8E44AD",
    }

    records: List[Dict[str, object]] = []
    for method, grp in base_df.groupby("Method"):
        exp = grp["Nf_exp"].astype(float).values
        pred = grp["Nf_expected"].astype(float).values
        # Positive = predicted life shorter than experimental = conservative.
        ln_err = np.log(exp / pred)
        s_ln = float(np.std(ln_err))
        mu_ln = float(np.mean(ln_err))
        ratio = pred / exp
        f2 = float(np.mean((ratio >= 0.5) & (ratio <= 2.0)) * 100.0)
        fam = family_map[str(method)]
        records.append(
            {
                "Method": str(method),
                "s_ln": s_ln,
                "mu_ln": mu_ln,
                "f2": f2,
                "Family": fam,
                "Color": color_map.get(fam, "#555555"),
                "N": len(grp),
            }
        )

    bench_df = pd.DataFrame(records).sort_values(by="s_ln", ascending=True).reset_index(drop=True)

    fig, (ax1, ax2) = plt.subplots(
        1,
        2,
        figsize=(11.5, 1.8 + 0.29 * len(bench_df)),
        sharey=True,
        gridspec_kw={"width_ratios": [1.4, 1.0]},
        dpi=300,
    )
    fig.patch.set_facecolor("#FFFFFF")

    y_pos = np.arange(len(bench_df))

    # Left panel: Scatter standard deviation
    bars1 = ax1.barh(
        y_pos,
        bench_df["s_ln"],
        color=bench_df["Color"],
        alpha=0.88,
        edgecolor="#222222",
        linewidth=0.7,
        height=0.68,
    )
    ax1.axvline(
        np.log(2.0),
        color="#777777",
        linestyle="--",
        linewidth=1.2,
        label=r"$\ln 2 \approx 0.69$ (F2 half-width)",
    )
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(bench_df["Method"], fontweight="bold", fontsize=9.5)
    ax1.invert_yaxis()
    ax1.set_xlabel(
        r"Log-Error Std. Dev., $s_{\ln} = \mathrm{std}(\ln(N_{f,\mathrm{exp}} / N_{f,\mathrm{pred}}))$",
        fontweight="bold",
        labelpad=8,
    )
    ax1.set_title(r"$\mathbf{Error\ Dispersion\ (Lower\ is\ Better)}$", pad=10, fontsize=11)
    ax1.set_xlim(0.0, max(3.0, 1.3 * float(bench_df["s_ln"].max())))
    ax1.grid(True, axis="x", linestyle=":", alpha=0.55)
    ax1.legend(loc="upper right", frameon=True, edgecolor="#CCCCCC", fontsize=9)

    for i, bar in enumerate(bars1):
        f2_val = bench_df.loc[i, "f2"]
        ax1.text(
            bar.get_width() + 0.04,
            bar.get_y() + bar.get_height() / 2,
            f"{f2_val:.0f}% in F2",
            va="center",
            ha="left",
            fontsize=8.5,
            color="#333333",
        )

    # Right panel: Mean Error (bias)
    ax2.barh(
        y_pos,
        bench_df["mu_ln"],
        color=bench_df["Color"],
        alpha=0.88,
        edgecolor="#222222",
        linewidth=0.7,
        height=0.68,
    )
    ax2.axvline(0.0, color="black", linestyle="-", linewidth=1.2)
    ax2.set_xlabel(
        r"Mean Log Error, $\mu_{\ln} = \mathrm{mean}(\ln(N_{f,\mathrm{exp}} / N_{f,\mathrm{pred}}))$",
        fontweight="bold",
        labelpad=8,
    )
    ax2.set_title(r"$\mathbf{Systematic\ Bias\ (>0:\ Conservative)}$", pad=10, fontsize=11)
    bias_lim = float(np.max(np.abs(bench_df["mu_ln"]))) * 1.1
    ax2.set_xlim(-bias_lim if (bench_df["mu_ln"] < 0).any() else -0.2, bias_lim)
    ax2.grid(True, axis="x", linestyle=":", alpha=0.55)

    legend_elements = [
        Patch(facecolor=c, edgecolor="black", label=fam) for fam, c in color_map.items()
    ]
    ax2.legend(
        handles=legend_elements,
        loc="upper right",
        frameon=True,
        edgecolor="#CCCCCC",
        fontsize=8.5,
        title=r"$\mathbf{Model\ Family}$",
    )

    fig.suptitle(
        r"$\mathbf{Comparative\ Benchmark\ of\ Multiaxial\ Fatigue\ Criteria}$"
        + f"\n42CrMo4-QT, plain axial and torsion tests ({n_tests} failures, run-outs excluded)",
        fontsize=13.0,
        y=0.995,
    )
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.965])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    p = plot_benchmark_error()
    print(f"Generated benchmark plot: {p}")
