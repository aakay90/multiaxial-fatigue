"""Shared academic plotting style and color palettes for multifat examples."""

from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_IMG_DIR = REPO_ROOT / "docs" / "images"
DATA_DIR = REPO_ROOT / "examples" / "data"

# Academic palette
PALETTE = {
    "navy": "#1B365D",
    "crimson": "#C0392B",
    "cerulean": "#2980B9",
    "emerald": "#27AE60",
    "purple": "#8E44AD",
    "amber": "#E67E22",
    "charcoal": "#2B2B2B",
    "grid": "#888888",
    "band_f2": "#2C3E50",
    "safe_fill": "#EBF5FB",
}


def apply_academic_style() -> None:
    """Configure matplotlib with Times New Roman and Computer Modern math."""
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif"],
            "mathtext.fontset": "cm",
            "axes.edgecolor": PALETTE["charcoal"],
            "axes.linewidth": 1.0,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 9.2,
            "legend.framealpha": 0.95,
            "figure.titlesize": 13.5,
            "figure.dpi": 300,
        }
    )
