"""Per-model Wohler and parity plots with run-outs (ported from upstream 7a87256, A. Chiocca)."""

import matplotlib

matplotlib.use("Agg")

import numpy as np  # noqa: E402

from multifat.eval.fat_cycles import fatigue_plots  # noqa: E402


def _plots(**kw):
    base = dict(F_par=[300.0, 250.0], N_exp=[1e5, 1e6], N_pred=[2e5, 8e5], A=1000.0, B=-0.1)
    base.update(kw)
    return fatigue_plots(show=False, **base)


def test_wohler_plot_draws_runouts():
    fig1, ax1, fig2, ax2 = _plots(F_runout=[200.0, 190.0], N_runout=[5e6, 5e6],
                                  N_pred_runout=[2e7, 3e7])  # fmt: skip
    open_markers = [c for c in ax1.collections if len(c.get_facecolor()) == 0]
    assert open_markers and len(open_markers[0].get_offsets()) == 2
    assert len(ax1.texts) == 2 and len(ax2.texts) == 2  # one arrow per run-out
    assert any("Run-out" in t.get_text() for t in ax1.get_legend().get_texts())


def test_parity_plot_without_predictions():
    fig1, ax1, fig2, ax2 = _plots(N_pred=[np.nan, np.nan])
    assert any("unavailable" in t.get_text() for t in ax2.texts)
    lo, hi = ax2.get_xlim()
    assert np.isfinite(lo) and np.isfinite(hi)
