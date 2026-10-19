"""Observation identities and matched failure subsets for review comparisons."""
import csv
from collections import defaultdict
import hashlib
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from fatigue.eval.calibration_store import input_fingerprint, json_value


def observation_index(block):
    """Identify load cases and repeated observations without depending on row position."""
    occurrences = defaultdict(int)
    result = {}
    for cid, case in block['cases'].items():
        meta = case['meta']
        raw = meta.get('experimental_metadata', {})
        reference = raw.get('Article DOI / Reference', raw.get('Article DOI', ''))
        content = json_value({'specimen': meta.get('specimen_id'), 'reference': str(reference).strip(),
                             'stress': {step: case[1][step]['stress'] for step in (1, 2)},
                             'harmonics': {k: v for k, v in case.get('harmonics', {}).items() if k.startswith('S_')}})
        case_key = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
        observation = f"{case_key}/{meta['Nf_cycles']}/{meta.get('test_status', 'failure')}"
        occurrences[observation] += 1
        result[cid] = (case_key, hashlib.sha256(
            f'{observation}/{occurrences[observation]}'.encode()).hexdigest())
    return result


def attach_observation_ids(path, block):
    """Append identifiers without changing the numerical text in existing columns.

    Ambiguous legacy provenance remains unmatched rather than merging different
    loading histories. Fresh results should supply unambiguous specimen metadata.
    """
    index = observation_index(block)
    by_meta = defaultdict(list)
    for cid, case in block['cases'].items():
        meta = case['meta']
        by_meta[(str(meta.get('specimen_id', '')), float(meta['Nf_cycles']),
                 meta.get('test_status', 'failure'))].append(index[cid])
    with open(path, newline='') as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    material = rows[0]['Material'] if rows else ''
    fingerprint = input_fingerprint({material: block}, material)
    for row in rows:
        key = (row['Specimen_id'], float(row['Nf_exp']), row['Test_status'])
        candidates = by_meta.get(key, [])
        # Duplicate identical histories can be indexed by occurrence. Different
        # histories with the same specimen/life cannot be resolved from old CSVs.
        unique_cases = {c[0] for c in candidates}
        identity = candidates.pop(0) if len(unique_cases) == 1 and candidates else ('', '')
        row.update(Case_id=identity[0], Observation_id=identity[1], Dataset_fingerprint=fingerprint)
    with open(path, 'w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields + ['Case_id', 'Observation_id', 'Dataset_fingerprint'])
        writer.writeheader()
        writer.writerows(rows)


KEYS = ['Material', 'Dataset_fingerprint', 'Observation_id']
METRICS = {'life': 'Error_ln', 'damage': 'Error_log10_dp'}


def eligible_failures(df, metric='life'):
    column = METRICS[metric]
    values = pd.to_numeric(df[column], errors='coerce')
    mask = ((df['Test_status'] == 'failure') & np.isfinite(values)
            & np.isfinite(df['Nf_exp']) & (df['Nf_exp'] > 0))
    if metric == 'life':
        mask &= np.isfinite(df['Nf_expected']) & (df['Nf_expected'] > 0) & (df['Nf_exp'] > 0)
    return df.loc[mask].copy()


def common_subset(df, methods, metric='life'):
    """Return exactly matched failure observations with a finite selected metric."""
    methods = list(dict.fromkeys(methods))
    if len(methods) < 2:
        raise ValueError('Select at least two methods for a common comparison')
    if any(k not in df for k in KEYS):
        raise ValueError('Common comparisons require regenerated observation IDs and dataset fingerprints')
    selected = eligible_failures(df[df['Method'].isin(methods)], metric)
    if selected[KEYS].isna().any().any() or (selected[KEYS].astype(str) == '').any().any():
        raise ValueError('Unresolved observation identity; regenerate results with unambiguous specimen provenance')
    if selected.duplicated(['Method', *KEYS]).any():
        raise ValueError('Duplicate method-observation results; select one result/calibration per observation')
    sets = [set(map(tuple, selected.loc[selected.Method == method, KEYS].to_numpy())) for method in methods]
    common = set.intersection(*sets)
    keep = [tuple(row) in common for row in selected[KEYS].to_numpy()]
    subset = selected.loc[keep].copy()
    # Same IDs must not conceal different lives or fitting/evaluation roles.
    for column in ['Nf_exp', 'Flag', 'Case_id']:
        if column in subset and (subset.groupby(KEYS)[column].nunique() > 1).any():
            raise ValueError(f'Conflicting {column} for matched observations')
    return subset


def write_subset_reports(df, directory, methods=None):
    """Export individual availability and metric-specific pairwise/group overlaps."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    methods = list(methods or sorted(df['Method'].unique()))
    counts = []
    overlaps = []
    for metric in METRICS:
        eligible = eligible_failures(df, metric)
        for method in methods:
            part = eligible[eligible.Method == method]
            counts.append({'method': method, 'metric': metric, 'materials': part.Material.nunique(),
                           'observations': len(part), 'cases': part.Case_id.nunique() if 'Case_id' in part else None})
        groups = list(combinations(methods, 2))
        if len(methods) > 2:
            groups.append(tuple(methods))
        for group in groups:
            try:
                common = common_subset(df, group, metric)
                first = common[common.Method == group[0]]
                overlaps.append({'methods': group, 'metric': metric, 'materials': sorted(first.Material.unique()),
                    'n_observations': len(first), 'n_cases': first.Case_id.nunique(),
                    'observation_keys': first[KEYS].to_dict('records')})
            except ValueError as exc:
                overlaps.append({'methods': group, 'metric': metric, 'unavailable_reason': str(exc)})
    pd.DataFrame(counts).to_csv(directory / 'individual_availability.csv', index=False)
    (directory / 'common_subsets.json').write_text(json.dumps(json_value(overlaps), indent=2, allow_nan=False) + '\n')
    return counts, overlaps
