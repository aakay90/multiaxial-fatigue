"""Modified Mohr-Mises hypothesis (MMMH) of Mertens & Liebich (2017), Int J Fatigue,
doi:10.1016/j.ijfatigue.2017.06.003 (roadmap G07): kernel routines for smooth surfaces
(m_a = n_el = m_o1 = m_a1 = 1), together with the registered MMMH model.

Eq. (1):  sigma_eq,MMM(eta) = V(eta) sqrt((4 - k_a^2) M_M^2 + k_a^2 R_M^2),
Eq. (4):  M_M = (sigma_1 + sigma_2)/2 - sigma_3,  |R_M| = |sigma_1 - sigma_2|/2  (surface, sigma_3 = sigma_z),
Eq. (9):  V = sign(sqrt(4 - k_a^2) M_M + k_a R_M),  Eq. (25): sigma_eq,a = (max - min)/2.

Regardless of the signs taken by M_M and R_M, the square root keeps the Mertens expression
I1^2 - k_a^2 I2. For one harmonic the mean-free signal flips sign when shifted by half a period, so
both M_M and the signed R_M of Tab. 1 flip as well, sigma_eq,MMM flips, and
sigma_eq,a = max_t sqrt(I1^2 - k_a^2 I2) = COIN with k_phi = 0.5. In the time-domain routine below a
shear stress taken in the frame that cancels it at the smallest radius supplies the sign of R_M
(Eqs. 14-19); the quotient of Eq. (20) only fixes a global sign of R_M, so it does not alter the
single-harmonic amplitude and is left out.

Equivalent mean stress (Eqs. 22-24): sigma_eq,m = sigma_o1 - sigma_a1, where sigma_o1 is the largest
maximum principal stress of the total stress and sigma_a1 the amplitude of the signed principal
stress sigma_1. Eq. (22) takes the largest maximum principal stress of the total stress across the
cycle; Eq. (23) takes the half range of the signed sigma_1(eta) = M_plane + R_M of Eq. (21), using
the global sign quot of Eq. (20) and Tab. 1 step 9. Since for one harmonic the mean-free stress flips
sign after half a period, the sigma_1,max of the mean-free stress coincides with |sigma_2,min| and
step 9 yields quot,o: R_M carries the sign of sigma_1 at its maximum, sigma_1 attains sigma_1,max
there and -sigma_1,max half a period later, and sigma_a1 = max_eta sigma_1(eta) of the mean-free
stress, for proportional and non-proportional loading alike (cross-checked in the tests against a
literal implementation of Eqs. 20-23).

Assessment (registered model): reproducing the load-cycle dependent Haigh diagrams of the paper
calls for M_N from refs. [16, 23] (Konstruktion 1997; dissertation Hahn 1995), which cannot be
obtained. The paper permits endurance-limit values taken from guidelines, so this model adopts the
endurance-limit Haigh line sigma_A(sigma_m) = s_-1 - M sigma_m, with the mean-stress sensitivity
M = (s_-1 - s_0/2)/(s_0/2) from Dubbel (2004) E1 (between R = -1 and R = 0) and k_a = s_-1/t_-1,
and returns (sigma_eq,a + M sigma_eq,m)/s_-1. As with CROSSLAND, the life follows from the fitted
universal curve.
Source note: for k_a^2 = 0, Eq. (8) yields |s1a + s2a| whereas the text reports |s1a - s2a|.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np

from ..base import CaseResult
from .coin_liwi import coin_amplitude
from .stress_invariants import harmonic_parts


def mmmh_amplitude(S_sin, S_cos, k_a: float) -> float:
    """sigma_eq,a of Eq. (25) for one harmonic (= COIN with k_phi = 0.5)."""
    return coin_amplitude(S_sin, S_cos, k_a, k_phi=0.5)


def mmmh_equivalent_history(sigma_x, sigma_y, tau_xy, k_a: float, sigma_z=0.0) -> np.ndarray:
    """sigma_eq,MMM(eta) of Eq. (1) for sampled mean-free surface stresses (smooth, m_a = n_el = 1)."""
    sigma_x, sigma_y, tau_xy = (
        np.asarray(comp, dtype=float) for comp in (sigma_x, sigma_y, tau_xy)
    )
    sigma_z = np.broadcast_to(np.asarray(sigma_z, dtype=float), sigma_x.shape)
    M_M = 0.5 * (sigma_x + sigma_y) - sigma_z
    half_diff = 0.5 * (sigma_x - sigma_y)
    shear_mag = np.hypot(half_diff, tau_xy)
    idx_min = int(np.argmin(shear_mag))
    angle = 0.5 * np.arctan2(tau_xy[idx_min], half_diff[idx_min])
    shear_rot = -half_diff * np.sin(2.0 * angle) + tau_xy * np.cos(2.0 * angle)
    R_M = np.sign(shear_rot) * shear_mag
    magnitude = np.sqrt(np.maximum((4.0 - k_a**2) * M_M**2 + k_a**2 * R_M**2, 0.0))
    return np.sign(np.sqrt(4.0 - k_a**2) * M_M + k_a * R_M) * magnitude


def mmmh_mean_proportional(S_mean, S_amp) -> float:
    """sigma_eq,m of Eq. (24) for proportional loading S(t) = S_mean + S_amp f(t), |f| <= 1."""
    S_mean, S_amp = np.asarray(S_mean, dtype=float), np.asarray(S_amp, dtype=float)
    top_mean = max(
        np.linalg.eigvalsh(S_mean + S_amp)[-1],
        np.linalg.eigvalsh(S_mean - S_amp)[-1],
    )
    half_range = float(np.max(np.abs(np.linalg.eigvalsh(S_amp))))
    return float(top_mean - half_range)


def _peak_principal_stress(S_mean, S_sin, S_cos, n_samples: int = 720) -> float:
    """max over eta of the largest principal stress of S_mean + S_sin sin(eta) + S_cos cos(eta)."""

    def largest_eig(phase):
        phase = np.atleast_1d(phase)
        tensor = (
            S_mean + np.sin(phase)[:, None, None] * S_sin + np.cos(phase)[:, None, None] * S_cos
        )
        return np.linalg.eigvalsh(tensor)[:, -1]

    samples = np.linspace(0.0, 2.0 * np.pi, n_samples, endpoint=False)
    largest = largest_eig(samples)
    # coincident maxima give the same value, which is all this needs
    top = int(np.argmax(largest))
    spacing = samples[1] - samples[0]
    lo, hi = samples[top] - spacing, samples[top] + spacing
    for _ in range(60):  # golden-section search inside the bracket
        left = hi - 0.618034 * (hi - lo)
        right = lo + 0.618034 * (hi - lo)
        if largest_eig(left)[0] >= largest_eig(right)[0]:
            hi = right
        else:
            lo = left
    return max(float(largest[top]), float(largest_eig(0.5 * (lo + hi))[0]))


def mmmh_mean(S_mean, S_sin, S_cos) -> float:
    """sigma_eq,m of Eq. (24) (smooth: m_o1 = m_a1 = n_el = 1) for a single-harmonic cycle."""
    S_mean, S_sin, S_cos = (np.asarray(comp, dtype=float) for comp in (S_mean, S_sin, S_cos))
    peak_total = _peak_principal_stress(S_mean, S_sin, S_cos)  # Eq. (22)
    peak_oscillating = _peak_principal_stress(np.zeros((3, 3)), S_sin, S_cos)  # Eq. (23), see above
    return float(peak_total - peak_oscillating)


def mmmh_index(S_mean, S_sin, S_cos, f_m1: float, t_m1: float, M: float) -> float:
    """(sigma_eq,a + M sigma_eq,m)/s_-1 on the endurance-limit Haigh line, k_a = s_-1/t_-1."""
    k_a = f_m1 / t_m1
    if not 0.0 < k_a <= 2.0:
        raise ValueError("MMMH needs 0 < k_a = Sigm1/Taum1 <= 2 (Eq. 1)")
    return (mmmh_amplitude(S_sin, S_cos, k_a) + M * mmmh_mean(S_mean, S_sin, S_cos)) / f_m1


class MMMH:
    """Modified Mohr-Mises hypothesis at the endurance limit (see the module docstring)."""

    name = "MMMH"
    optional_params = {
        "M_MMMH": "2 Sigm1/Sig0 - 1 (Dubbel 2004, E1: mean-stress sensitivity between R = -1 and 0)",
        "Sig0": "Boehme et al. 2026 Eq. (1) from Su and Sigm1",
        "Su": "only to estimate Sig0",
    }

    def required_params(self) -> set[str]:
        return {"Sigm1", "Taum1"}

    def evaluate_case(
        self, *, S0, E0, S1, E1, params: Mapping[str, float], R_list=None, harmonics=None
    ) -> CaseResult:
        S_mean, S_sin, S_cos = harmonic_parts(S0, S1, harmonics)
        M = params.get("M_MMMH")
        if M is None:
            from ..integral_methods.bohme_papuga import _strengths

            f_m1, _, f_0, _ = _strengths(params, self.name)
            M = 2.0 * f_m1 / f_0 - 1.0
        index = mmmh_index(
            S_mean,
            S_sin,
            S_cos,
            float(params["Sigm1"]),
            float(params["Taum1"]),
            float(M),
        )
        return CaseResult(values={"": index})
