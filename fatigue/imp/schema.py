"""Explicit workbook aliases and stable identifiers for experimental inputs."""
import re


def normalise(value):
    return ' '.join(str(value).strip().lower().split())


def material_id(filename_stem):
    """Remove an ordering prefix without merging alloy or treatment names."""
    return re.sub(r'^\d+_', '', filename_stem)


# Only documented spelling changes are aliases. Forces are never stress aliases.
DATASET_HEADERS = {
    'Nf': ['Number of cycles to failure'], 'notched': ['Notched'],
    'runout': ['Run out (Yes/No)'],
    'mean_rad': ['Mean RADIAL stress (MPa)'],
    'amp_rad': ['Amplitute RADIAL stress (MPa)', 'Amplitude RADIAL stress (MPa)'],
    'mean_ax': ['Mean AXIAL stress (MPa)'],
    'amp_ax': ['Amplitute AXIAL stress (MPa)', 'Amplitude AXIAL stress (MPa)'],
    'mean_sh': ['Mean SHEAR stress (MPa)'],
    'amp_sh': ['Amplitute SHEAR stress (MPa)', 'Amplitude SHEAR stress (MPa)'],
    'phase_rad': ['Phase RADIAL load (°)'],
    'phase_ax': ['Phase AXIAL load (°)'],
    'phase_tor': ['Phase TORSIONAL load (°)'],
}


def dataset_column(columns, key):
    candidates = [c for c in columns if normalise(c) in
                  {normalise(h) for h in DATASET_HEADERS[key]}]
    if len(candidates) != 1:
        raise KeyError(f'Expected one {key} column, found {candidates}; accepted {DATASET_HEADERS[key]}')
    return candidates[0]
