"""Critical-amplitude integral mean criterion, following Boehme et al. (2026).

The constants and the clipping rule reproduce damage_criteria_CAIM.m. The
uniform angular summation used there is replaced by sphere quadrature, and the
amplitude peak is sharpened with a numerical plane search. Restricted to
single-harmonic stress histories.
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
