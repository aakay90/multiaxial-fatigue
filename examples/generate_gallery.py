"""Gallery Generator for Multiaxial Fatigue Examples.

Generates the complete suite of publication-quality figures for documentation
and README display:
1. Critical-plane polar damage landscapes (proportional vs 90° out-of-phase)
2. Multiaxial fatigue life prediction correlation (log-log scatter with F2/F3 bands)
3. Model benchmark error and systematic bias (s_ln dispersion vs mu_ln bias)
4. Biaxial fatigue limit failure envelopes in normalized stress space
"""

import sys
from pathlib import Path
from typing import List

# Ensure repository root is on sys.path for direct script execution
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.plot_benchmark_error import plot_benchmark_error
from examples.plot_damage_polar import plot_critical_plane_polar
from examples.plot_fatigue_limit import plot_fatigue_limit_envelopes
from examples.plot_life_correlation import plot_life_correlation

DOCS_IMG_DIR = REPO_ROOT / "docs" / "images"


def generate_all_gallery_plots(target_dir: Path = DOCS_IMG_DIR) -> List[Path]:
    """Generate all gallery plots into target_dir."""
    target_dir.mkdir(parents=True, exist_ok=True)
    generated: List[Path] = []

    print("Generating multiaxial fatigue visual gallery...")

    p1 = plot_critical_plane_polar(out_path=target_dir / "critical_plane_polar.png")
    print(f"  [1/4] Polar damage landscape: {p1}")
    generated.append(p1)

    p2 = plot_life_correlation(out_path=target_dir / "life_prediction_correlation.png")
    print(f"  [2/4] Life prediction correlation: {p2}")
    generated.append(p2)

    p3 = plot_benchmark_error(out_path=target_dir / "model_benchmark_error.png")
    print(f"  [3/4] Model benchmark error: {p3}")
    generated.append(p3)

    p4 = plot_fatigue_limit_envelopes(out_path=target_dir / "fatigue_limit_envelopes.png")
    print(f"  [4/4] Fatigue limit envelopes: {p4}")
    generated.append(p4)

    print("Gallery generation complete! All figures saved.")
    return generated


if __name__ == "__main__":
    generate_all_gallery_plots()
