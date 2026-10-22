"""COIN (roadmap G08): Schmidt & Kraft (2023) Int J Fatigue 168:107474,
doi:10.1016/j.ijfatigue.2022.107474 (Zotero WKDZPXJW); Eqs. (17)-(32) pp.5-6 (crops
_audit-trail/phase2/crops/WKDZPXJW/p5.png, p6_*.png). The paper's results are life statistics
(Table 4) on data not reproduced here, so the tests check the formulation:

- Eqs. (27) and (30) for plane stress with independent phases;
- the stated special cases of k_phi (p.6): 1 = RMS of the invariants (H = 2 mean Q), 0.5 = maximum
  of the static (time-domain) Eq. (21), 0 = cancellation of 90 deg shifted invariants;
- calibration: reversed tension s_-1 and reversed torsion t_-1 both give 1 with k_a = s_-1/t_-1.
"""

import numpy as np
import pytest

from multifat.models.invariant_methods.coin_liwi import coin_amplitude
from multifat.models.registry import get_models

Z = np.zeros((3, 3))
KA = 1.6


def _plane(sx, sy, t, px, py, pt):
    Zc = np.array(
        [
            [sx * np.exp(1j * px), t * np.exp(1j * pt), 0.0],
            [t * np.exp(1j * pt), sy * np.exp(1j * py), 0.0],
            [0.0, 0.0, 0.0],
        ]
    )
    return -Zc.imag, Zc.real  # S_sin, S_cos of Re(Z e^{jwt})


def test_eqs_27_and_30_plane_stress():
    sx, sy, t, px, py, pt = 200.0, 120.0, 80.0, 0.3, 1.1, -0.4
    S_sin, S_cos = _plane(sx, sy, t, px, py, pt)
    e27 = sx**2 + sy**2 + (2 - KA**2) * sx * sy * np.cos(px - py) + KA**2 * t**2
    e30 = (
        sx**2 * np.exp(2j * px)
        + sy**2 * np.exp(2j * py)
        + (2 - KA**2) * sx * sy * np.exp(1j * (px + py))
        + KA**2 * t**2 * np.exp(2j * pt)
    )
    assert coin_amplitude(S_sin, S_cos, KA, 1.0) ** 2 == pytest.approx(e27, rel=1e-12)
    assert coin_amplitude(S_sin, S_cos, KA, 0.0) ** 2 == pytest.approx(abs(e30), rel=1e-12)


@pytest.mark.parametrize("seed", range(3))
def test_k_phi_special_cases_against_time_domain(seed):
    rng = np.random.default_rng(seed)
    A, B = (0.5 * (X + X.T) for X in rng.normal(scale=100.0, size=(2, 3, 3)))
    w = np.linspace(0, 2 * np.pi, 20001)[:-1]
    S = A[None] * np.sin(w)[:, None, None] + B[None] * np.cos(w)[:, None, None]
    i1 = np.trace(S, axis1=1, axis2=2)
    i2 = 0.5 * (i1**2 - np.einsum("tij,tji->t", S, S))
    q = i1**2 - KA**2 * i2  # Eq. (21) squared, plane stress generalised to 3-D invariants
    assert coin_amplitude(A, B, KA, 1.0) ** 2 == pytest.approx(2 * q.mean(), rel=1e-9)
    assert coin_amplitude(A, B, KA, 0.5) ** 2 == pytest.approx(q.max(), rel=1e-6)


def test_k_phi_zero_cancels_quarter_period_shift():
    """sigma_x and tau_xy 90 deg apart with sigma_x^2 = k_a^2 tau^2: |C| = 0 (Fig. 7i)."""
    S_sin, S_cos = _plane(KA * 100.0, 0.0, 100.0, 0.0, 0.0, np.pi / 2)
    assert coin_amplitude(S_sin, S_cos, KA, 0.0) == pytest.approx(0.0, abs=1e-4)


def test_calibration_and_registry():
    s, t = 313.9, 196.2
    (model,) = get_models(["COIN"])
    ax, to = np.diag([s, 0.0, 0.0]), np.zeros((3, 3))
    to[0, 1] = to[1, 0] = t
    for S in (ax, to):
        for k_phi in (None, 0.85):
            p = {"Sigm1": s, "Taum1": t, "k_phi": k_phi}
            val = model.evaluate_case(S0=S, S1=-S, E0=Z, E1=Z, params=p).values[""]
            assert val == pytest.approx(1.0, rel=1e-12)
