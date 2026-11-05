"""Critical-amplitude integral mean criterion (CAIM), Boehme, Papuga & Lange (2026).

doi:10.1111/ffe.70244::

    sigma_eq^2 = max_n (a tau_a^2 + b sigma_a^2) + <c tau_a tau_m + d sigma_a sigma_m>
    a = kappa^2,  b = 1 (kappa^2 < 2) or kappa^2 - kappa^4 / 4 (kappa^2 >= 2)

with the BP mean-stress weights c, d. The constants and the clipping rule reproduce
damage_criteria_CAIM.m. Restricted to single-harmonic stress histories.

Repository choices:
  - sphere quadrature replaces the uniform angular summation of the MATLAB code, and the
    amplitude peak is sharpened with a numerical plane search (searched, not proven, maximum);
  - the index sigma_eq / s_-1 is used as the damage parameter of the shared master curve.

User guide: docs/method-guides/CAIM.md.
"""

import numpy as np

from .bohme_papuga import BohmePapuga, _plane_amplitudes, refine_plane_max


class CAIM(BohmePapuga):
    """Hybrid criterion scaled by the reversed axial fatigue strength."""

    name = "CAIM"

    def _amplitude_coefficients(self, kappa_sq):
        return kappa_sq, 1.0 if kappa_sq < 2.0 else kappa_sq - kappa_sq**2 / 4.0

    def _combine(
        self,
        a_CAIM,
        b_CAIM,
        c_CAIM,
        d_CAIM,
        sigma_a,
        sigma_m,
        tau_a,
        tau_m,
        weights,
        normals,
        S_mean,
        S_sin,
        S_cos,
    ):
        grid_amplitude = a_CAIM * tau_a**2 + b_CAIM * sigma_a**2

        # Polish a few grid maxima so the outcome depends less on grid orientation.
        def directional_amplitude(normal):
            sigma_a_plane, _, tau_a_plane, _ = _plane_amplitudes(S_mean, S_sin, S_cos, normal)
            return a_CAIM * tau_a_plane**2 + b_CAIM * sigma_a_plane**2

        peak = refine_plane_max(directional_amplitude, normals, grid_amplitude)
        mean_term = np.dot(weights, c_CAIM * tau_a * tau_m + d_CAIM * sigma_a * sigma_m)
        return peak + mean_term
