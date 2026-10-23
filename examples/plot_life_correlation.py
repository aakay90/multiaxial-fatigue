import sys
from pathlib import Path
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Ensure repository root is on sys.path for direct script execution
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.style import DATA_DIR, DOCS_IMG_DIR, PALETTE, apply_academic_style


def plot_life_correlation(out_path: Path | None = None) -> Path:
    """Generate log-log experimental vs predicted fatigue life correlation plot."""
    apply_academic_style()
    if out_path is None:
        out_path = DOCS_IMG_DIR / "life_prediction_correlation.png"

    csv_path = DATA_DIR / "42CrMo4_QT_predictions.csv"
    df = pd.read_csv(csv_path)

    target_models: List[Tuple[str, str, str, str]] = [
        ("Smith-Watson-Topper (SWT)", "SWT", PALETTE["cerulean"], "^"),
        ("Crossland", "CROSSLAND", PALETTE["emerald"], "D"),
        ("Findley (FIN)", "FIN", PALETTE["navy"], "o"),
        ("Fatemi-Socie (FS)", "FS", PALETTE["crimson"], "s"),
        ("Sines", "SINES", PALETTE["purple"], "v"),
    ]

    fig, ax = plt.subplots(figsize=(9.2, 6.6), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")

    n_min, n_max = 8e2, 5e7
    line = np.logspace(np.log10(n_min), np.log10(n_max), 200)

    ax.plot(line, line, "k-", linewidth=1.8, label="1:1 Bisector (Exact)")
    ax.fill_between(
        line, line / 2.0, line * 2.0, color=PALETTE["band_f2"], alpha=0.07, label="Factor-of-2 Band"
    )
    ax.plot(line, line * 2.0, color="#555555", linestyle="--", linewidth=1.1)
    ax.plot(line, line / 2.0, color="#555555", linestyle="--", linewidth=1.1)
    ax.plot(
        line, line * 3.0, color="#777777", linestyle=":", linewidth=1.1, label="Factor-of-3 Band"
    )
    ax.plot(line, line / 3.0, color="#777777", linestyle=":", linewidth=1.1)

    for label, m_name, color, marker in target_models:
        sub = df[(df["Method"] == m_name) & (df["Flag"] != 2)].copy()
        sub = sub[
            pd.to_numeric(sub["Nf_exp"], errors="coerce").notna()
            & pd.to_numeric(sub["Nf_expected"], errors="coerce").notna()
        ]
        exp = sub["Nf_exp"].astype(float).values
        pred = sub["Nf_expected"].astype(float).values

        ratio = pred / exp
        pct_f2 = np.mean((ratio >= 0.5) & (ratio <= 2.0)) * 100.0

        ax.scatter(
            exp,
            pred,
            label=f"{label} ({pct_f2:.0f}% in F2)",
            color=color,
            marker=marker,
            s=42,
            alpha=0.82,
            edgecolors="black",
            linewidths=0.6,
            zorder=4,
        )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1e3, 1e7)
    ax.set_ylim(1e3, 1e7)
    ax.set_xlabel(
        r"Experimental Fatigue Life, $N_{f,\mathrm{exp}}$ [cycles]", fontweight="bold", labelpad=8
    )
    ax.set_ylabel(
        r"Predicted Fatigue Life, $N_{f,\mathrm{pred}}$ [cycles]", fontweight="bold", labelpad=8
    )
    ax.set_title(
        r"$\mathbf{Multiaxial\ Fatigue\ Life\ Prediction\ Correlation}$"
        + "\n42CrMo4-QT, plain axial and torsion tests (run-outs excluded)",
        fontsize=12,
        pad=12,
    )
    ax.grid(True, which="both", linestyle=":", alpha=0.45, color=PALETTE["grid"])

    # Safe / Unsafe callouts in completely unobstructed locations
    ax.text(
        4.0e3,
        2.5e6,
        "Unconservative\n($N_{f,\\mathrm{pred}} > N_{f,\\mathrm{exp}}$)",
        fontsize=8.5,
        color="#8B0000",
        ha="center",
        bbox=dict(boxstyle="round,pad=0.35", fc="#FFF5F5", ec="#E6B0AA", alpha=0.92),
    )
    ax.text(
        7.0e5,
        1.8e3,
        "Conservative\n($N_{f,\\mathrm{pred}} < N_{f,\\mathrm{exp}}$)",
        fontsize=8.5,
        color="#1B4F72",
        ha="center",
        bbox=dict(boxstyle="round,pad=0.35", fc="#F0F8FF", ec="#AED6F1", alpha=0.92),
    )

    ax.legend(
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=True,
        edgecolor="#CCCCCC",
        fontsize=9.0,
    )

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    p = plot_life_correlation()
    print(f"Generated: {p}")
