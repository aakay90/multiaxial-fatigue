"""MMMH kernel (roadmap G07): Mertens & Liebich (2017) Int J Fatigue,
doi:10.1016/j.ijfatigue.2017.06.003 (Zotero W6J5CUBE); Eqs. (1), (4), (8), (9), (22)-(25) (crops
_audit-trail/phase2/crops/W6J5CUBE/p4_*, p5_*, p8_*, p9_*, p17_*, p18_*). The paper prints no numerical
results, so the tests check the stated special cases and the single-harmonic reduction to COIN with
k_phi = 0.5. Registered model: Eq. (24) for any single harmonic against a literal Eqs. (20)-(23)
implementation (sign operator quot,o of Tab. 1 step 9 / p. 14), and the endurance-limit Haigh line
with M of Dubbel (2004) E1 through its three calibration points.
"""

import numpy as np
import pytest

from multifat.models.invariant_methods.coin_liwi import coin_amplitude
from multifat.models.invariant_methods.mmmh import (
    MMMH,
    mmmh_amplitude,
    mmmh_equivalent_history,
    mmmh_index,
    mmmh_mean,
    mmmh_mean_proportional,
)

ETA = np.linspace(0, 2 * np.pi, 20001)[:-1]


def _phasors(sx, sy, t, px, py, pt):
    S_sin, S_cos = np.zeros((3, 3)), np.zeros((3, 3))
    for (i, j), a, p in (((0, 0), sx, px), ((1, 1), sy, py), ((0, 1), t, pt)):
        S_cos[i, j] = S_cos[j, i] = a * np.cos(p)
        S_sin[i, j] = S_sin[j, i] = -a * np.sin(p)
    return S_sin, S_cos


@pytest.mark.parametrize("k_a", [1.0, 1.6, np.sqrt(3.0), 1.9])
@pytest.mark.parametrize("seed", range(3))
def test_time_domain_amplitude_equals_coin_half(k_a, seed):
    rng = np.random.default_rng(seed)
    sx, sy, t = rng.normal(scale=150.0, size=3)
    px, py, pt = rng.uniform(0, 2 * np.pi, 3)
    s = mmmh_equivalent_history(
        sx * np.cos(ETA + px), sy * np.cos(ETA + py), t * np.cos(ETA + pt), k_a
    )
    amp = 0.5 * (s.max() - s.min())  # Eq. (25)
    S_sin, S_cos = _phasors(sx, sy, t, px, py, pt)
    assert amp == pytest.approx(mmmh_amplitude(S_sin, S_cos, k_a), rel=1e-6)
    assert mmmh_amplitude(S_sin, S_cos, k_a) == coin_amplitude(S_sin, S_cos, k_a, 0.5)


@pytest.mark.parametrize("k2", [0.0, 1.0, 3.0, 4.0])
def test_eq8_proportional_principal_stresses(k2):
    """sigma1 = s1a cos, sigma2 = s2a cos: amplitude sqrt(s1a^2 + s2a^2 + (2 - k^2) s1a s2a);
    k^2 = 0 gives |s1a + s2a| (the text's |s1a - s2a| is a misprint), k^2 = 4 gives |s1a - s2a|,
    k^2 = 3 the von Mises amplitude."""
    s1, s2 = 200.0, -80.0
    S_sin, S_cos = _phasors(s1, s2, 0.0, 0.0, 0.0, 0.0)
    expected = np.sqrt(s1**2 + s2**2 + (2 - k2) * s1 * s2)
    assert mmmh_amplitude(S_sin, S_cos, np.sqrt(k2)) == pytest.approx(expected, rel=1e-12)
    if k2 == 0.0:
        assert expected == pytest.approx(abs(s1 + s2)) and expected != pytest.approx(abs(s1 - s2))
    if k2 == 4.0:
        assert expected == pytest.approx(abs(s1 - s2))


def test_uniaxial_and_torsion():
    """Uniaxial sigma_a gives sigma_a for any k_a (p.7); torsion tau_a gives k_a tau_a."""
    for k_a in (1.0, 1.5, 2.0):
        assert mmmh_amplitude(*_phasors(250.0, 0, 0, 0, 0, 0), k_a) == pytest.approx(250.0)
        assert mmmh_amplitude(*_phasors(0, 0, 100.0, 0, 0, 0), k_a) == pytest.approx(k_a * 100.0)


def test_eq24_mean_proportional():
    """Uniaxial: sigma_o1 = m + a, sigma_a1 = a -> m; reversed torsion: 0; torsion with mean shear:
    sigma_o1 = t_m + t_a, sigma_a1 = t_a -> t_m."""
    ax = lambda s: np.diag([s, 0.0, 0.0])  # noqa: E731

    def sh(t):
        S = np.zeros((3, 3))
        S[0, 1] = S[1, 0] = t
        return S

    assert mmmh_mean_proportional(ax(120.0), ax(200.0)) == pytest.approx(120.0)
    assert mmmh_mean_proportional(np.zeros((3, 3)), sh(150.0)) == pytest.approx(0.0, abs=1e-12)
    assert mmmh_mean_proportional(sh(60.0), sh(150.0)) == pytest.approx(60.0)


def _literal_mean(S_mean, S_sin, S_cos):
    """Eqs. (20)-(23) and (22) step by step on a sampled cycle (surface stresses, sigma_z = 0)."""
    hist = S_sin[None] * np.sin(ETA)[:, None, None] + S_cos[None] * np.cos(ETA)[:, None, None]
    sx, sy, txy = hist[:, 0, 0], hist[:, 1, 1], hist[:, 0, 1]
    m_plane = 0.5 * (sx + sy)
    half_diff = 0.5 * (sx - sy)
    r_abs = np.hypot(half_diff, txy)
    i = int(np.argmin(r_abs))
    psi = 0.5 * np.arctan2(txy[i], half_diff[i])
    r_aux = np.sign(-half_diff * np.sin(2 * psi) + txy * np.cos(2 * psi)) * r_abs  # R°°_M
    s1_plain = m_plane + r_abs
    k = int(np.argmax(s1_plain))
    quot = np.sign(r_aux[k]) / np.sign(s1_plain[k])  # Eq. (20), quot,o
    sigma1 = m_plane + quot * r_aux  # Eq. (21)
    sigma_a1 = 0.5 * (sigma1.max() - sigma1.min())  # Eq. (23)
    tot = S_mean[None] + hist
    cx, dx = 0.5 * (tot[:, 0, 0] + tot[:, 1, 1]), 0.5 * (tot[:, 0, 0] - tot[:, 1, 1])
    sigma_o1 = np.max(np.maximum(cx + np.hypot(dx, tot[:, 0, 1]), tot[:, 2, 2]))  # Eq. (22)
    return sigma_o1 - sigma_a1


@pytest.mark.parametrize("seed", range(8))
def test_eq24_nonproportional_against_literal_eqs_20_23(seed):
    rng = np.random.default_rng(seed)
    S_sin, S_cos = _phasors(*rng.uniform(-200, 200, 3), *rng.uniform(0, 2 * np.pi, 3))
    S_mean = np.zeros((3, 3))
    S_mean[0, 0], S_mean[1, 1] = rng.uniform(-100, 150, 2)
    S_mean[0, 1] = S_mean[1, 0] = rng.uniform(-80, 80)
    assert mmmh_mean(S_mean, S_sin, S_cos) == pytest.approx(
        _literal_mean(S_mean, S_sin, S_cos), abs=1e-3
    )
    assert mmmh_mean(np.zeros((3, 3)), S_sin, S_cos) == pytest.approx(0.0, abs=1e-9)


def test_eq24_general_equals_proportional():
    S_mean = np.array([[80.0, 30.0, 0], [30.0, 120.0, 0], [0, 0, 0]])
    S_amp = np.array([[150.0, -60.0, 0], [-60.0, 40.0, 0], [0, 0, 0]])
    assert mmmh_mean(S_mean, S_amp, np.zeros((3, 3))) == pytest.approx(
        mmmh_mean_proportional(S_mean, S_amp), rel=1e-12
    )


def test_haigh_calibration_points():
    """Index 1 for reversed tension at s_-1, reversed torsion at t_-1 and R = 0 tension at s_0."""
    s, t, s0 = 300.0, 190.0, 480.0
    M = 2 * s / s0 - 1
    zero = np.zeros((3, 3))
    assert mmmh_index(zero, *_phasors(s, 0, 0, 0, 0, 0), s, t, M) == pytest.approx(1.0)
    assert mmmh_index(zero, *_phasors(0, 0, t, 0, 0, 0), s, t, M) == pytest.approx(1.0)
    mean = np.diag([s0 / 2, 0.0, 0.0])
    assert mmmh_index(mean, *_phasors(s0 / 2, 0, 0, 0, 0, 0), s, t, M) == pytest.approx(1.0)


def test_model_sensitivity_from_boehme_estimate():
    """Without Sig0, M = 2 s/s0 - 1 with Boehme Eq. (1) s0 = 4 s Su/(s + 2 Su), i.e. M = s/(2 Su)."""
    s, t, su = 300.0, 190.0, 900.0
    mean = np.diag([100.0, 0.0, 0.0])
    S_sin, S_cos = _phasors(200.0, 0, 0, 0, 0, 0)
    harm = {"S_mean": mean, "S_sin": S_sin, "S_cos": S_cos}
    out = (
        MMMH()
        .evaluate_case(
            S0=None,
            E0=None,
            S1=None,
            E1=None,
            params={"Sigm1": s, "Taum1": t, "Su": su},
            harmonics=harm,
        )
        .values[""]
    )
    assert out == pytest.approx((200.0 + s / (2 * su) * 100.0) / s)
