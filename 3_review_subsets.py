"""Generate eligibility matrices and optionally evaluate compatible combinations."""
import argparse
import importlib.util
import json
from pathlib import Path

import pandas as pd

from fatigue.eval.calibration_store import curve_settings, json_value
from fatigue.eval.eligibility import assess_eligibility, warn_unavailable
from fatigue.imp.experimental_data import import_experimental_data_grouped_by_material
from fatigue.imp.observations import observation_counts
from fatigue.models.registry import _available_cp_methods, _available_direct_models


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-folder', default='Experimental_Data')
    parser.add_argument('--calibrations-dir', default='Calibrations')
    parser.add_argument('--results-dir', default='Results')
    parser.add_argument('--report-dir', default='Results/Comparison/eligibility')
    parser.add_argument('--models', nargs='+', default=list(_available_cp_methods()) + list(_available_direct_models()))
    parser.add_argument('--materials', nargs='+')
    parser.add_argument('--n1', type=int, default=20)
    parser.add_argument('--n2', type=int, default=40)
    parser.add_argument('--stdnum', type=float, default=0)
    parser.add_argument('--run', action='store_true', help='Assess compatible pairs without automatic recalibration')
    args = parser.parse_args(argv)
    data = import_experimental_data_grouped_by_material(args.data_folder)
    settings = curve_settings(args.n1, args.n2, args.stdnum)
    records = []
    runner = None
    if args.run:
        spec = importlib.util.spec_from_file_location('run_material', Path(__file__).with_name('1_run_material.py'))
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        runner.CALIBRATIONS_DIR, runner.RESULTS_DIR = args.calibrations_dir, args.results_dir
        runner.DCMESH_N1, runner.DCMESH_N2, runner.STDNUM = args.n1, args.n2, args.stdnum
        runner.MAKE_PLOTS = False
    for material in args.materials or data:
        for method in args.models:
            record = assess_eligibility(data=data, material=material, method=method,
                settings=settings, folder=args.calibrations_dir)
            record['observations'] = observation_counts(data[material])
            if args.run:
                if not record['prediction_available']:
                    warn_unavailable(record)
                else:
                    runner.MATERIAL_NAME, runner.MODEL_NAME = material, method
                    try:
                        outcome = runner.main(data=data)
                        record['execution_status'] = outcome['status']
                        record['csv_path'] = outcome.get('csv_path')
                        if record['csv_path']:
                            actual = pd.read_csv(record['csv_path'])
                            record['actual_predictions'] = len(actual)
                            record['actual_failures'] = int((actual.Test_status == 'failure').sum())
                            record['actual_runouts'] = int((actual.Test_status == 'runout').sum())
                            record['actual_life_comparisons'] = int(actual.Error_ln.notna().sum())
                    except (ValueError, KeyError, RuntimeError) as exc:
                        record['execution_status'] = 'failed'
                        record['reasons'].append(str(exc))
                        warn_unavailable(record)
            records.append(record)
    directory = Path(args.report_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'eligibility.json').write_text(json.dumps(json_value(records), indent=2, allow_nan=False) + '\n')
    frame = pd.DataFrame(records)
    frame[['method', 'material', 'status', 'prediction_available', 'quantitative_comparison_available',
           'life_comparison_available', 'can_calibrate', 'n_failures', 'n_runouts', 'reasons']].to_csv(
               directory / 'eligibility.csv', index=False)
    summary = frame.groupby('method').agg(materials=('prediction_available', 'sum'),
        failure_observations=('n_failures', 'sum'), runout_observations=('n_runouts', 'sum'),
        excluded_combinations=('prediction_available', lambda s: int((~s).sum())))
    summary.to_csv(directory / 'method_availability.csv')
    frame.pivot(index='method', columns='material', values='status').to_csv(directory / 'eligibility_matrix.csv')
    print(f"{sum(r['prediction_available'] for r in records)} compatible; "
          f"{sum(not r['prediction_available'] for r in records)} unavailable combinations")
    return records


if __name__ == '__main__':
    main()
