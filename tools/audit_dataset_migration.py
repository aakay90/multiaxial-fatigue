"""Compare workbook structure and imported inputs without editing measured data."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from openpyxl import load_workbook
from fatigue.imp.experimental_data import import_experimental_data_grouped_by_material
from fatigue.imp.schema import material_id
from fatigue.imp.observations import observation_counts
from fatigue.eval.calibration_store import input_fingerprint, json_value


def headers(path):
    w = load_workbook(path, read_only=True, data_only=True)
    value = {name: [str(c.value) for c in next(w[name].iter_rows()) if c.value is not None]
             for name in ('Summary', 'Dataset')}
    w.close()
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--old-dir', default='Experimental_Data/archive/pre-dataset-migration')
    parser.add_argument('--new-dir', default='Experimental_Data')
    parser.add_argument('--output', default='Results/Comparison/dataset-migration.json')
    args = parser.parse_args()
    old = import_experimental_data_grouped_by_material(args.old_dir)
    new = import_experimental_data_grouped_by_material(args.new_dir)
    old_paths = {material_id(p.stem): p for p in Path(args.old_dir).glob('*.xlsx')}
    new_paths = {material_id(p.stem): p for p in Path(args.new_dir).glob('*.xlsx')}
    records = []
    for material in sorted(old.keys() | new.keys()):
        before, after = old.get(material), new.get(material)
        record = {'material': material, 'old_workbook': old_paths[material].name if before else None,
                  'new_workbook': new_paths[material].name if after else None,
                  'status': 'retained' if before and after else 'added' if after else 'archived_or_regrouped'}
        for label, block in [('old', before), ('new', after)]:
            if block:
                record[label + '_observations'] = observation_counts(block)
                record[label + '_scope_exclusions'] = len(block.get('scope_exclusions', []))
                record[label + '_properties'] = block['material']
        if after:
            record['identity_issues'] = after['identity_issues']
            record['property_issues'] = after['property_issues']
            record['source_summary_rows'] = after['source_property_rows']
            record['new_workbook_sha256'] = hashlib.sha256(new_paths[material].read_bytes()).hexdigest()
        if before and after:
            record['calibration_inputs_unchanged'] = input_fingerprint(old, material) == input_fingerprint(new, material)
            first, second = headers(old_paths[material]), headers(new_paths[material])
            record['header_changes'] = {sheet: {'removed': sorted(set(first[sheet]) - set(second[sheet])),
                'added': sorted(set(second[sheet]) - set(first[sheet]))} for sheet in first}
            old_cases = {(c['meta']['specimen_id'], c['meta']['Nf_cycles'],
                          c['meta']['test_status']): c for c in before['cases'].values()}
            import numpy as np
            record['matching_stress_observations'] = sum(
                key in old_cases and all(np.array_equal(c[1][step]['stress'], old_cases[key][1][step]['stress'])
                                         for step in (1, 2))
                for c in after['cases'].values()
                for key in [(c['meta']['specimen_id'], c['meta']['Nf_cycles'], c['meta']['test_status'])])
        records.append(record)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(json_value(records), indent=2, allow_nan=False) + '\n')
    print(f'Compared {len(old)} previous and {len(new)} current material IDs; wrote {output}')


if __name__ == '__main__':
    main()
