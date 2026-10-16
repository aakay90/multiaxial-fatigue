"""Compare models returning cycles without refitting their life predictions."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from fatigue.imp import experimental_data as exp
from fatigue.eval.calibration_store import material_parameters
from fatigue.models.base import model_output_quantity
from fatigue.report.export_csv import save_fatigue_csv
from fatigue.report.observations import plot_runouts


def run_direct_life(*, data, material, model, method_name, variant, results_dir,
                    classify_loading_type, make_plots=False, plot_dir=None, show_runouts=True):
    """Export native cycle predictions and censored observations without a DP fit.

    Only independently supplied material properties are available on this path.
    A model requiring calibrated coefficients needs an explicit calibration
    procedure before registration, rather than an implicit fit of predicted lives.
    """
    if model_output_quantity(model) != "life_cycles":
        raise ValueError("Direct life comparison requires life_cycles")
    params = material_parameters(data[material]["material"])
    missing = [key for key in model.required_params() if params.get(key) is None]
    if missing:
        raise ValueError(f"Missing material parameters for {model.name}: {missing}")
    cycles, predicted, statuses, specimens, loading = [], [], [], [], []
    for cid, case in data[material]["cases"].items():
        meta = case["meta"]
        status = meta.get("test_status", "failure")
        if status not in {"failure", "runout"}:
            continue
        S0, E0, S1, E1, harmonics = exp.extract_tensor(data, material, cid, include_harmonics=True)
        result = model.evaluate_case(S0=S0, E0=E0, S1=S1, E1=E1,
            params=params, R_list=None, harmonics=harmonics)
        model_output_quantity(model, result)
        if variant not in result.values:
            raise ValueError(f"Missing variant {variant!r} for {model.name}")
        life = float(result.values[variant])
        if not np.isfinite(life) or life <= 0:
            raise ValueError(f"{model.name} must return finite positive life in cycles, case {cid}")
        cycles.append(meta["Nf_cycles"])
        predicted.append(life)
        statuses.append(status)
        specimens.append(meta.get("specimen_id", str(cid)))
        loading.append(classify_loading_type(H=harmonics, meta=meta))
    csv_path = save_fatigue_csv(out_dir=results_dir, method_name=method_name, material_name=material,
        N_exp=cycles, CP=np.full(len(cycles), np.nan), N_pred=predicted,
        test_status=statuses, specimen_ids=specimens, loading_type=loading, metric_mode="Nf_direct")
    if make_plots and cycles:
        fig, ax = plt.subplots()
        x, y = np.asarray(cycles), np.asarray(predicted)
        failed = np.asarray(statuses) == "failure"
        ax.scatter(x[failed], y[failed], label="Failed specimens")
        if show_runouts:
            censored = np.asarray(statuses) == "runout"
            plot_runouts(ax, x[censored], y[censored])
        lo, hi = min(x.min(), y.min()) / 2, max(x.max(), y.max()) * 2
        ax.plot([lo, hi], [lo, hi], "k--", label="y = x")
        ax.set(xscale="log", yscale="log", xlim=(lo, hi), ylim=(lo, hi),
               xlabel="Recorded experimental cycles (run-outs are lower bounds)",
               ylabel="Predicted life (cycles)")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, which="both")
        ax.legend()
        if plot_dir is None:
            plt.show()
        else:
            directory = Path(plot_dir)
            directory.mkdir(parents=True, exist_ok=True)
            fig.savefig(directory / f"{method_name}_{material}_life_parity.png", dpi=160, bbox_inches="tight")
        plt.close(fig)
    print("Saved:", csv_path)
    return csv_path
