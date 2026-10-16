"""Plotting and metric conventions for right-censored observations."""
import numpy as np


def plot_runouts(ax, x, y, *, color="C0", label="Run-out (recorded cycles are a lower bound)"):
    """Open circles and right-pointing arrows on a cycle-count abscissa."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
    if not valid.any():
        return
    ax.scatter(x[valid], y[valid], facecolors="none", edgecolors=color,
               marker="o", label=label)
    for xx, yy in zip(x[valid], y[valid]):
        ax.annotate("", xy=(xx * 1.35, yy), xytext=(xx, yy),
                    arrowprops={"arrowstyle": "->", "color": color, "lw": 0.8})


def mask_censored_errors(frame):
    """Prevent recomputed life or damage errors from treating bounds as lives."""
    frame = frame.copy()
    if "Test_status" not in frame:
        frame["Test_status"] = "failure"
    censored = frame["Test_status"] != "failure"
    for key in ("Error_ln", "Error_ln_dp", "Error_log10_dp", "Error_dp", "DP_fit"):
        if key in frame:
            frame.loc[censored, key] = np.nan
    return frame
