"""PBP (roadmap N37): Cristofori, Susmel & Tovo (2008) Int J Fatigue 30:1646-1658,
doi:10.1016/j.ijfatigue.2007.11.006 (Zotero 9MQP75G8); Eqs. (4)-(13), (A.3), Appendix B (crops
_audit-trail/phase2/crops/9MQP75G8/p5.png, p6_*.png). The paper prints Table 1 (Woehler constants)
and figures only, so the tests are structural:

- the covariance-eigenbasis procedure of Eqs. (4)-(5) on a sampled harmonic path reproduces the
  closed form Gamma = sqrt(J2(A) + J2(B)) (the basis drops out for one harmonic);
- calibration: rho = 1 and Gamma/sqrt(J2A,1) = 1 in reversed tension at f_-1, rho = 0 in torsion;
- consequence: in-phase and 90 deg out-of-phase bending-torsion of equal amplitudes give the same
  index (the closed form B.9 has no phase either).
Source issues: Eq. (2) cross term sign (+ for -), Eqs. (4)-(5) without 1/T (irrelevant to the
eigenbasis), Eq. (B.5) omits the sqrt(3) of Eq. (6), N_A undefined (life part not implemented).
"""

import numpy as np
import pytest

from multifat.models.invariant_methods.pbp import (
    deviatoric_vector,
    pbp_amplitude,
    pbp_index,
    projection_amplitudes,
)
from multifat.models.registry import get_models

Z = np.zeros((3, 3))
F, T = 313.9, 196.2


def _bt(s, t):
    return np.array([[s, t, 0.0], [t, 0.0, 0.0], [0.0, 0.0, 0.0]])


def test_deviatoric_vector_norm_is_j2():
    S = np.array([[120.0, 40.0, -10.0], [40.0, -30.0, 25.0], [-10.0, 25.0, 60.0]])
    D = S - np.trace(S) / 3 * np.eye(3)
    assert np.sum(deviatoric_vector(S) ** 2) == pytest.approx(0.5 * np.sum(D * D), rel=1e-12)


@pytest.mark.parametrize("seed", range(3))
def test_covariance_projection_procedure_equals_closed_form(seed):
    rng = np.random.default_rng(seed)
    A, B = (0.5 * (X + X.T) for X in rng.normal(scale=100.0, size=(2, 3, 3)))
    w = np.linspace(0, 2 * np.pi, 8001)[:-1]
    history = A[None] * np.sin(w)[:, None, None] + B[None] * np.cos(w)[:, None, None]
    gamma = np.sqrt(np.sum(projection_amplitudes(history) ** 2))
    assert gamma == pytest.approx(pbp_amplitude(A, B), rel=1e-6)


def test_calibration_eq6_eq8():
    assert pbp_index(Z, _bt(F, 0.0), Z, F, T) == pytest.approx(1.0, rel=1e-12)
    assert pbp_index(Z, _bt(0.0, T), Z, F, T) == pytest.approx(1.0, rel=1e-12)


def test_phase_shift_has_no_effect_in_bending_torsion():
    s, t = 200.0, 120.0
    in_phase = pbp_index(Z, _bt(s, t), Z, F, T)
    out_of_phase = pbp_index(Z, _bt(s, 0.0), _bt(0.0, t), F, T)
    assert out_of_phase == pytest.approx(in_phase, rel=1e-12)


def test_mean_stress_through_rho():
    """rho = sqrt(3) sigma_H,max / Gamma; tension with mean m: rho = sqrt(3)(s + m)/3 / (s/sqrt(3))."""
    s, m = 200.0, 100.0
    rho = (s + m) / s
    ref = T + rho * (F / np.sqrt(3) - T)
    assert pbp_index(_bt(m, 0.0), _bt(s, 0.0), Z, F, T) == pytest.approx(
        (s / np.sqrt(3)) / ref, rel=1e-12
    )


def test_registry_case_model():
    (model,) = get_models(["PBP"])
    S = _bt(200.0, 120.0)
    p = {"Sigm1": F, "Taum1": T}
    assert model.evaluate_case(S0=S, S1=-S, E0=Z, E1=Z, params=p).values[""] == pytest.approx(
        pbp_index(Z, S, Z, F, T), rel=1e-12
    )
