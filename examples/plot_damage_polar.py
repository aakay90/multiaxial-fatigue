import sys
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np

# Ensure repository root is on sys.path for direct script execution
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from multifat.eval.evaluator import evaluate_planes, prepare_planes
from multifat.models.registry import get_models
from examples.style import DOCS_IMG_DIR, PALETTE, apply_academic_style


def plot_critical_plane_polar(out_path: Path | None = None) -> Path:
    """Generate 2-panel polar figure showing critical plane damage under phase shift."""
    apply_academic_style()
    if out_path is None:
        out_path = DOCS_IMG_DIR / "critical_plane_polar.png"

    angles = np.linspace(0.0, np.pi, 361)
    r_planes_list = []
    for th in angles:
        r_mat = np.array(
            [
                [-np.sin(th), 0.0, np.cos(th)],
                [np.cos(th), 0.0, np.sin(th)],
                [0.0, 1.0, 0.0],
            ]
        )
        r_planes_list.append(r_mat)
    r_planes = np.array(r_planes_list)

    sigma_a, tau_a = 240.0, 150.0
    e_mod, nu = 206000.0, 0.30

    s_sin_ip = np.array([[sigma_a, tau_a, 0.0], [tau_a, 0.0, 0.0], [0.0, 0.0, 0.0]])
    s_cos_ip = np.zeros((3, 3))
    e_sin_ip = np.array(
        [
            [sigma_a / e_mod, (1.0 + nu) * tau_a / e_mod, 0.0],
            [(1.0 + nu) * tau_a / e_mod, -nu * sigma_a / e_mod, 0.0],
            [0.0, 0.0, -nu * sigma_a / e_mod],
        ]
    )
    e_cos_ip = np.zeros((3, 3))

    s_sin_oop = np.array([[sigma_a, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
    s_cos_oop = np.array([[0.0, tau_a, 0.0], [tau_a, 0.0, 0.0], [0.0, 0.0, 0.0]])
    e_sin_oop = np.array(
        [
            [sigma_a / e_mod, 0.0, 0.0],
            [0.0, -nu * sigma_a / e_mod, 0.0],
            [0.0, 0.0, -nu * sigma_a / e_mod],
        ]
    )
    e_cos_oop = np.array(
        [
            [0.0, (1.0 + nu) * tau_a / e_mod, 0.0],
            [(1.0 + nu) * tau_a / e_mod, 0.0, 0.0],
            [0.0, 0.0, 0.0],
        ]
    )

    models: List[Tuple[str, str, Dict[str, float], str, str]] = [
        ("Findley (FIN)", "FIN", {"k_FI": 0.28}, PALETTE["navy"], "-"),
        (
            "Fatemi-Socie (FS)",
            "FS",
            {"k_FS": 0.50, "Sy": 750.0, "E": e_mod, "nu": nu},
            PALETTE["crimson"],
            "--",
        ),
        ("Smith-Watson-Topper (SWT)", "SWT", {"E": e_mod, "nu": nu}, PALETTE["cerulean"], "-."),
    ]

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(11.0, 5.6), subplot_kw={"projection": "polar"}, dpi=300
    )
    fig.patch.set_facecolor("#FFFFFF")

    angles_full = np.concatenate([angles, angles + np.pi])

    cases = [
        (
            r"$\mathbf{Proportional\ Loading}\ (\delta = 0^\circ)$",
            ax1,
            s_sin_ip,
            s_cos_ip,
            e_sin_ip,
            e_cos_ip,
        ),
        (
            r"$\mathbf{Non{-}Proportional\ Loading}\ (\delta = 90^\circ)$",
            ax2,
            s_sin_oop,
            s_cos_oop,
            e_sin_oop,
            e_cos_oop,
        ),
    ]

    for title, ax, s_s, s_c, e_s, e_c in cases:
        ax.set_theta_zero_location("E")
        ax.set_theta_direction(1)
        ax.set_title(title, pad=12, fontweight="bold", fontsize=11.5)
        ax.grid(True, linestyle=":", alpha=0.55, color="#777777")

        for label, m_name, params, color, ls in models:
            m = get_models([m_name])[0]._m
            planes = prepare_planes(
                S0=s_s,
                E0=e_s,
                S1=-s_s,
                E1=-e_s,
                R_list=r_planes,
                S_sin=s_s,
                S_cos=s_c,
                E_sin=e_s,
                E_cos=e_c,
                E=e_mod,
                nu=nu,
            )
            dmg, _ = evaluate_planes(m, planes, params)
            norm_dmg = dmg / np.max(dmg)
            norm_dmg_full = np.concatenate([norm_dmg, norm_dmg])

            idx_max = int(np.argmax(dmg))
            th_cp = angles[idx_max]

            ax.plot(
                angles_full, norm_dmg_full, label=label, color=color, linestyle=ls, linewidth=2.0
            )
            ax.plot(
                [th_cp, th_cp + np.pi],
                [1.0, 1.0],
                marker="o",
                markersize=6,
                color=color,
                markeredgecolor="black",
                markeredgewidth=0.8,
            )
            ax.plot(
                [th_cp, th_cp + np.pi],
                [0.0, 1.0],
                color=color,
                linestyle=":",
                linewidth=1.1,
                alpha=0.65,
            )

        ax.set_ylim(0.0, 1.06)
        ax.set_rticks([0.25, 0.50, 0.75, 1.00])
        ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], fontsize=8, color="#555555")
        ax.set_rlabel_position(25)

    fig.subplots_adjust(top=0.775, bottom=0.18, wspace=0.35)
    ax1.legend(
        loc="upper center",
        bbox_to_anchor=(1.15, -0.14),
        ncol=3,
        frameon=True,
        edgecolor="#CCCCCC",
        fontsize=9.5,
    )
    fig.suptitle(
        r"$\mathbf{Critical\ Plane\ Damage\ Landscapes}$: Orientation-Dependent Damage Distribution",
        fontsize=13.0,
        y=0.955,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    p = plot_critical_plane_polar()
    print(f"Generated: {p}")
