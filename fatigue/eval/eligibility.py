"""Method-specific input checks shared by calibration, assessment and reporting."""
import math
import warnings

from fatigue.eval.calibration_store import (METHOD_PARAMETERS, material_parameters,
                                            load_calibration)
from fatigue.imp.observations import is_failure
from fatigue.models.registry import get_models

STRESS_ONLY = {'FIN', 'MATAKE', 'MCD', 'BP', 'CAIM'}
# These identifiers explicitly describe steels in the supplied collection.
UML_STEELS = {'42CrMo4_QT', 'En3B', '25CrMo4', '30NCD16', '34Cr4', '982FA', 'S65A', 'AISI316L'}


def valid_parameter(key, value):
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return False
    if key == 'nu':
        return -1 < value < 0.5
    if key in {'b_fat', 'c_fat', 'b0', 'c0'}:
        return value < 0
    if key in METHOD_PARAMETERS.values():
        return value >= 0 and (key != 'a_MSWT' or value <= 1)
    return value > 0


def input_requirements(data, material, method, *, calibration=False, parameters=None):
    """Check actual model dependencies, including conditional empirical estimates."""
    base = method.removesuffix('_ext')
    model = get_models([base])[0]
    params = material_parameters(data[material]['material'], parameters)
    required = set(model.required_params())
    if base == 'LIU2021':
        required.discard('Su')  # Su is used only by the missing-property estimate.
    if base not in STRESS_ONLY:
        required.update({'E', 'nu'})
    if calibration:
        required.difference_update(METHOD_PARAMETERS.values())
    elif base in METHOD_PARAMETERS:
        required.add(METHOD_PARAMETERS[base])
    approximations = []
    if base in {'BP', 'CAIM'} and params.get('Sig0') is None:
        required.add('Su')
        approximations.append('R=0 strengths estimated using Böhme et al. (2026), Eqs. (1)-(2)')
    for key in ('Sig0', 'Tau0') if base in {'BP', 'CAIM'} else ():
        if params.get(key) is not None:
            required.add(key)
    if base in {'GSA', 'LIU2021'}:
        target = 'sigma_f' if base == 'GSA' else 'tau_f'
        if params.get(target) is not None:
            required.add(target)
        else:
            axial = {'sigma_f', 'epsilon_f', 'b_fat', 'c_fat'}
            shear = {'tau_f', 'gamma_f', 'b0', 'c0'}
            if base == 'LIU2021' and all(params.get(k) is not None for k in shear):
                required.update(shear)
            elif all(params.get(k) is not None for k in axial):
                required.update(axial)
                approximations.append('Shear properties derived from supplied axial properties')
            elif material in UML_STEELS:
                required.update({'Su', 'E'})
                approximations.append('Uniform Material Law for steel; shear conversion where required')
            else:
                required.add(target)
    missing = sorted(k for k in required if not valid_parameter(k, params.get(k)))
    issues = list(data[material].get('identity_issues', []))
    issues.extend(reason for key, reason in data[material].get('property_issues', {}).items() if key in required)
    return missing, issues, approximations


def case_issue(case, *, strain=False):
    import numpy as np
    reasons = list(case['meta'].get('loading_issues', []))
    if case['meta'].get('test_status', 'failure') not in {'failure', 'runout'}:
        reasons.append('Unknown observation status')
    for step in (1, 2):
        for quantity in ('stress', 'strain') if strain else ('stress',):
            tensor = np.asarray(case[1][step][quantity])
            if tensor.shape != (3, 3) or not np.isfinite(tensor).all():
                reasons.append(f'Missing or invalid {quantity} tensor')
    return list(dict.fromkeys(reasons))


def calibration_readiness(data, material, method, *, shear_amplitude_algorithm="method_default"):
    """Report whether current failure data permit an attempt, not fit success."""
    from fatigue.imp.experimental_data import extract_uniaxial_tension
    base = method.removesuffix('_ext')
    from fatigue.eval.findley_calibration import check_amplitude_methods, require_stress_harmonics
    try:
        check_amplitude_methods([base], shear_amplitude_algorithm)
    except ValueError as exc:
        return {'can_calibrate': False, 'missing_properties': [], 'reasons': [str(exc)],
                'approximations': [], 'design_failures': 0}
    missing, issues, approximations = input_requirements(data, material, base, calibration=True)
    usable = {cid: c for cid, c in data[material]['cases'].items()
              if not case_issue(c, strain=base not in STRESS_ONLY)}
    selected = {material: {**data[material], 'cases': usable}}
    points = extract_uniaxial_tension(selected).get(material, {}).get('points', [])
    lives = {p['Nf_cycles'] for p in points}
    if base == 'FIN' and shear_amplitude_algorithm != 'method_default':
        for point in points:
            try:
                require_stress_harmonics(usable[point['case_id']], material, point['case_id'])
            except ValueError as exc:
                issues.append(str(exc))
    if len(points) < 2 or len(lives) < 2:
        issues.append('Master curve requires at least two distinct observed axial R=-1 failure lives')
    return {'can_calibrate': not missing and not issues, 'missing_properties': missing,
            'reasons': issues, 'approximations': approximations,
            'design_failures': len(points)}


def assess_eligibility(*, data, material, method, settings, folder='Calibrations', calibration_id=None):
    """Separate stored-calibration availability, possible fitting and comparisons."""
    base = method.removesuffix('_ext')
    try:
        ready = calibration_readiness(data, material, method)
    except (KeyError, ValueError) as exc:
        return {'material': material, 'method': method, 'status': 'unsupported',
                'prediction_available': False, 'quantitative_comparison_available': False,
                'life_comparison_available': False, 'can_calibrate': False, 'n_failures': 0,
                'n_runouts': 0, 'missing_properties': [], 'reasons': [str(exc)]}
    result = {'material': material, 'method': method, **ready,
              'prediction_available': False, 'quantitative_comparison_available': False,
              'life_comparison_available': False, 'eligible_case_ids': [], 'excluded_cases': [],
              'n_failures': 0, 'n_runouts': 0, 'calibration_id': None, 'status': 'unavailable'}
    record = curve = None
    calibration_error = None
    try:
        record, curve, _ = load_calibration(data=data, material=material, model=base,
            settings=settings, folder=folder, calibration_id=calibration_id)
    except (ValueError, OSError) as exc:
        calibration_error = str(exc)
    missing, issues, approximations = input_requirements(data, material, base,
        parameters=record['parameters'] if record else None)
    # A missing coefficient with sufficient inputs is a missing result, not a missing measured property.
    result['missing_properties'] = [k for k in missing if k not in METHOD_PARAMETERS.values()]
    result['missing_parameters'] = [k for k in missing if k in METHOD_PARAMETERS.values()]
    result['approximations'] = approximations
    result['reasons'] = issues
    if record is None:
        result['reasons'].append(calibration_error)
        result['reasons'].extend(ready['reasons'])
        result['status'] = 'calibration_required' if ready['can_calibrate'] else 'insufficient_inputs'
    if missing:
        result['reasons'].append('Missing or invalid inputs: ' + ', '.join(missing))
    for cid, case in data[material]['cases'].items():
        reasons = case_issue(case, strain=base not in STRESS_ONLY)
        if reasons:
            result['excluded_cases'].append({'case_id': cid, 'reasons': reasons})
        else:
            result['eligible_case_ids'].append(cid)
    if not result['eligible_case_ids']:
        result['reasons'].append('No eligible plain experimental observations')
    fit = curve.get('fit_ext' if method.endswith('_ext') else 'fit') if curve else None
    if record and fit is None:
        result['reasons'].append('Requested variant has no calibrated master curve')
    if record and not missing and not issues and result['eligible_case_ids'] and fit:
        result['prediction_available'] = True
        result['calibration_id'] = record['calibration_id']
        cases = [data[material]['cases'][cid] for cid in result['eligible_case_ids']]
        result['n_failures'] = sum(is_failure(c) for c in cases)
        result['n_runouts'] = sum(c['meta'].get('test_status') == 'runout' for c in cases)
        result['quantitative_comparison_available'] = result['n_failures'] > 0
        b = fit['b']
        result['life_comparison_available'] = result['n_failures'] > 0 and b < 0 and -1 / b <= 15
        result['status'] = 'available' if result['n_failures'] else 'prediction_only'
    return result


def warn_unavailable(result, stage='assessment'):
    warnings.warn(f"Cannot perform {stage} for {result['material']}/{result['method']}. "
                  + '; '.join(result['reasons'])
                  + '. Skipped; no prediction generated. Correct inputs or run Script 0 explicitly.',
                  RuntimeWarning, stacklevel=2)
