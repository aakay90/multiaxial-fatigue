"""Ranking of every method by its load-equivalent error, across materials (issue #37).

Rows: methods, ordered by their mean rank over the materials they ran on (best on top).
Columns: materials. Cells: root mean square of Error_load = ln(1/s*) on the assessed failures,
which combines bias and scatter; lower is better. A cell of 0.10 means a typical load
misjudgement of about 10 %. The same scale holds for every
method, whatever its damage parameter, S-N slope or life law. Data: examples/data/load_error_ranking.csv
(see build_load_error_ranking.py).
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.style import DATA_DIR, DOCS_IMG_DIR, PALETTE, apply_academic_style


def plot_load_error_ranking(
    out_path: Path | None = None, data_path: Path = DATA_DIR / "load_error_ranking.csv"
) -> Path:
    apply_academic_style()
    out_path = out_path or DOCS_IMG_DIR / "load_error_ranking.png"
    table = pd.read_csv(data_path)
    sd = table.pivot(index="Method", columns="Material", values="Error_load_rms")
    ranks = sd.rank(axis=0, method="average")
    order = ranks.mean(axis=1).sort_values().index
    sd, ranks = sd.loc[order], ranks.loc[order]
    materials = list(sd.columns)

    fig, ax = plt.subplots(figsize=(1.35 * len(materials) + 3.4, 0.30 * len(sd) + 1.9), dpi=300)
    values = sd.to_numpy(dtype=float)
    shown = np.ma.masked_invalid(values)
    cmap = plt.get_cmap("viridis_r").copy()
    cmap.set_bad("#EEEEEE")
    image = ax.imshow(shown, cmap=cmap, aspect="auto", vmin=0.0, vmax=np.nanpercentile(values, 95))
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            text = "–" if np.isnan(values[i, j]) else f"{values[i, j]:.2f}"
            dark = not np.isnan(values[i, j]) and values[i, j] > 0.6 * image.norm.vmax
            ax.text(j, i, text, ha="center", va="center", fontsize=7.5,
                    color="white" if dark else PALETTE["charcoal"])  # fmt: skip
    mean_rank = ranks.mean(axis=1)
    covered = sd.notna().sum(axis=1)
    labels = [
        f"{name}  ({mean_rank[name]:.1f}, {covered[name]}/{len(materials)})" for name in sd.index
    ]
    ax.set_yticks(range(len(sd)), labels, fontsize=8.5)
    ax.set_xticks(range(len(materials)), [m.replace("_", " ") for m in materials], fontsize=8.5)
    ax.xaxis.tick_top()
    plt.setp(ax.get_xticklabels(), rotation=30, ha="left")
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    bar = fig.colorbar(image, ax=ax, fraction=0.04, pad=0.02)
    bar.set_label(r"RMS of $\ln(1/s^*)$ on assessed failures (lower is better)", fontsize=9)
    ax.set_title(
        "Methods ranked by their load-equivalent error (bias and scatter)\n"
        r"row label: (mean rank, materials covered); $s^*$: load factor reproducing $N_{f,\exp}$",
        fontsize=10.5, pad=46,
    )  # fmt: skip
    fig.tight_layout()
    fig.savefig(out_path, facecolor="#FFFFFF", bbox_inches="tight")
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    print(plot_load_error_ranking())
