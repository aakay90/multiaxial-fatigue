"""Biaxial Fatigue Limit Envelopes Plot.

Failure boundaries for fully reversed, proportional (in-phase) axial + torsional loading in
normalized stress space (sigma_a / sigma_{-1} vs tau_a / tau_{-1}), calibrated on the 42CrMo4-QT
fatigue limits of ``Experimental_Data/6_42CrMo4_QT.xlsx`` (Benedetti et al. 2022):

- Gough-Pollard ellipse
- Maximum shear stress (Tresca), calibrated on sigma_{-1}
- Crossland (J2 amplitude + peak hydrostatic stress), calibrated on sigma_{-1} and tau_{-1}
- Findley critical plane, calibrated on sigma_{-1} and tau_{-1}

The dataset holds no combined-loading fatigue-limit tests, so only the two calibration points
are drawn; no combined-loading data are shown.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Ensure repository root is on sys.path for direct script execution
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.style import DOCS_IMG_DIR, apply_academic_style

SIGMA_M1 = 433.0  # MPa, tensile fatigue limit at R = -1 (workbook Summary, Benedetti 2022)
TAU_M1 = 344.0  # MPa, torsional fatigue limit at R = -1 (same source)


def tresca_envelope(r: float, n: int = 200) -> tuple[np.ndarray, np.ndarray]:
    """sqrt((sigma/2)^2 + tau^2) = sigma_{-1}/2  ->  x^2 + (2 r y)^2 = 1."""
    x = np.linspace(0.0, 1.0, n)
    return x, np.sqrt(1.0 - x**2) / (2.0 * r)


def crossland_envelope(r: float, n: int = 400) -> tuple[np.ndarray, np.ndarray]:
    """sqrt(J2a) + a * sigma_H,max = b with sigma_H,max = sigma_a / 3 and b = tau_{-1}.

    Calibrating on sigma_{-1} and tau_{-1} gives a = 3 (r - 1/sqrt(3)).
    """
    a = 3.0 * (r - 1.0 / np.sqrt(3.0))
    x = np.linspace(0.0, 1.0, n)
    rhs = (1.0 - a * x / (3.0 * r)) ** 2 - x**2 / (3.0 * r**2)
    return x, np.sqrt(np.maximum(rhs, 0.0))


def findley_envelope(r: float, n_dir: int = 181) -> tuple[np.ndarray, np.ndarray, float]:
    """max over planes of (tau_a + k sigma_n,max) = tau_{-1} sqrt(1 + k^2).

    Stress is expressed in units of tau_{-1}; the axial amplitude is x / r.
    """
    k = (2.0 * r - 1.0) / (2.0 * np.sqrt(r * (1.0 - r)))
    th = np.linspace(0.0, np.pi, 1500)
    xs, ys = [], []
    for phi in np.linspace(0.0, np.pi / 2.0, n_dir):
        ux, uy = np.cos(phi), np.sin(phi)
        sig = 0.5 * (ux / r) * (1.0 + np.cos(2.0 * th)) + uy * np.sin(2.0 * th)
        tau = np.abs(-0.5 * (ux / r) * np.sin(2.0 * th) + uy * np.cos(2.0 * th))
        rho = np.sqrt(1.0 + k**2) / np.max(tau + k * np.maximum(0.0, sig))
        xs.append(rho * ux)
        ys.append(rho * uy)
    return np.array(xs), np.array(ys), k


def plot_fatigue_limit_envelopes(
    out_path: Path | None = None,
) -> Path:
    """Generate normalized biaxial fatigue limit failure envelopes in stress space."""
    apply_academic_style()
    if out_path is None:
        out_path = DOCS_IMG_DIR / "fatigue_limit_envelopes.png"
    fig, ax = plt.subplots(figsize=(9.2, 6.5), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")

    r = TAU_M1 / SIGMA_M1

    x = np.linspace(0.0, 1.0, 400)
    ax.plot(
        x,
        np.sqrt(1.0 - x**2),
        label="Gough-Pollard ellipse",
        color="#1B365D",
        linewidth=2.2,
    )

    x_tr, y_tr = tresca_envelope(r)
    ax.plot(
        x_tr,
        y_tr,
        label=r"Max. shear stress (Tresca, calibrated on $\sigma_{-1}$)",
        color="#E67E22",
        linewidth=1.8,
        linestyle="-.",
    )

    x_cr, y_cr = crossland_envelope(r)
    ax.plot(
        x_cr,
        y_cr,
        label="Crossland",
        color="#C0392B",
        linewidth=2.0,
        linestyle="--",
    )

    x_fi, y_fi, k_fi = findley_envelope(r)
    ax.plot(
        x_fi,
        y_fi,
        label=f"Findley critical plane ($k = {k_fi:.2f}$)",
        color="#2980B9",
        linewidth=2.0,
        linestyle=":",
    )

    ax.scatter(
        [1.0, 0.0],
        [0.0, 1.0],
        color="#1B365D",
        marker="o",
        s=55,
        edgecolors="black",
        linewidths=0.8,
        zorder=5,
        label=rf"Fatigue limits ($\sigma_{{-1}}$ = {SIGMA_M1:.0f} MPa, $\tau_{{-1}}$ = {TAU_M1:.0f} MPa)",
    )

    ax.set_xlim(-0.02, 1.25)
    ax.set_ylim(-0.02, 1.25)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(
        r"Normalized Axial Stress Amplitude, $\sigma_a / \sigma_{-1}$",
        fontweight="bold",
        labelpad=8,
    )
    ax.set_ylabel(
        r"Normalized Shear Stress Amplitude, $\tau_a / \tau_{-1}$",
        fontweight="bold",
        labelpad=8,
    )
    ax.set_title(
        r"$\mathbf{Multiaxial\ Fatigue\ Limit\ Envelopes}$"
        + "\n42CrMo4-QT, fully reversed proportional loading "
        + rf"($\tau_{{-1}}/\sigma_{{-1}} = {r:.2f}$)",
        fontsize=12,
        pad=12,
    )
    ax.grid(True, linestyle=":", alpha=0.55, color="#888888")

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
    p = plot_fatigue_limit_envelopes()
    print(f"Generated fatigue limit plot: {p}")
