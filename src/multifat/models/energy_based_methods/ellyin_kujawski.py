"""Ellyin & Kujawski (1993), ASTM STP 1191, doi:10.1520/STP24795S (roadmap G16):
distortional strain energy combined with a multiaxial constraint factor and a mean-stress
contribution, in its high-cycle (elastic) form.

Damage parameter (Eqs. 11, 15, 16): psi = dW_d (1 + alpha sigma_m / sigma_bar) / p_bar^n, where
- dW_d is the distortional strain-energy range per reversal (Fig. 1). The explicit zeta of the
  paper (Masing, uniaxial) is the plastic contribution and disappears for elastic strains; the
  paper nonetheless applies Eqs. (16)-(18) in the high-cycle regime, "when bulk material response
  is essentially elastic", where Eq. (18) demands that dW_d scale with sigma_bar^2. The form used
  here: elastic distortional energy dW_d = dsigma_bar^2 / (2 E*), with E* = 3E / (2(1 + nu))
  (Fig. 1) and dsigma_bar = 2 sigma_bar;
- sigma_bar is the effective (von Mises) stress amplitude, while sigma_m = sigma1m + sigma2m +
  sigma3m is the sum of the principal static stresses (Eq. 5b; no 1/3 factor, since the uniaxial
  limit of Eq. 18 requires sigma_m);
- p_bar = (1 + nu_bar) eps_max / gamma_max (Eq. 12), computed from the in-plane principal strains
  of the free surface (the x-y plane here, z being the surface normal) and the normal strain eps_r
  (Eq. 14); for elastic strains Eq. (13) gives nu_bar = nu_e. Limiting values: 1 for uniaxial,
  1 + nu for reversed torsion, 1 - nu for equibiaxial;
- n = 1 and alpha = 1/2, following the paper (p.61, Eq. 18).
Optional plastic contribution (K_prime, n_prime in the workbook; never fitted):
eps_p,a = (sigma_bar/K')^(1/n'), dW_d^p = (1 - n')/(2(1 + n')) dsigma_bar deps_p (the zeta term as
printed), with nu_bar weighted by strain (= Eq. 13 under uniaxial loading) and plastic strains
aligned with the deviatoric stress (stress control assumed).
Non-proportional loading is left aside by the authors. Adaptation in this repository for a single
harmonic: sigma_bar = sqrt(3) times the semi-major axis of the deviatoric ellipse (its longest
half-chord), while eps_max and gamma_max are maxima taken over the period. A non-positive mean
factor returns 0 (Eq. 18 holds only for -1.06 <= sigma_m/sigma_a <= 4.4).
"""

from __future__ import annotations

from typing import Mapping

import numpy as np

from ..base import CaseResult
from ..invariant_methods.stress_invariants import harmonic_parts, sqrt_j2_amplitude

_PHASE_GRID = np.linspace(0.0, 2.0 * np.pi, 360, endpoint=False)


def constraint_factor(E_sin, E_cos, nu: float) -> float:
    """p_bar of Eq. (12), with eps_r taken from Eq. (14) and the effective Poisson ratio of
    Eq. (13); eps_max and gamma_max are maxima over one period of the in-plane principal
    strains."""
    E_t = np.sin(_PHASE_GRID)[:, None, None] * np.asarray(E_sin) + np.cos(_PHASE_GRID)[
        :, None, None
    ] * np.asarray(E_cos)
    exx, eyy, exy = (
        E_t[:, 0, 0],
        E_t[:, 1, 1],
        0.5 * (E_t[:, 0, 1] + E_t[:, 1, 0]),
    )
    ezz = -nu / (1.0 - nu) * (exx + eyy)
    centre, radius = 0.5 * (exx + eyy), np.hypot(0.5 * (exx - eyy), exy)
    major, minor = centre + radius, centre - radius
    eps_max = float(np.max(major))
    gamma_max = float(np.max(np.maximum(np.abs(major - ezz), np.abs(minor - ezz))))
    if gamma_max <= 0.0:
        return 1.0
    return (1.0 + nu) * eps_max / gamma_max


def effective_poisson(eps_e: float, eps_p: float, nu_e: float, nu_p: float = 0.5) -> float:
    """Strain-weighted nu_bar, with eps_e = sigma_bar/E and eps_p the plastic strain amplitude:
    coincides with Eq. (13) under uniaxial loading and remains defined in reversed torsion,
    where Eq. (13) is 0/0 (paper footnote 3)."""
    total = eps_e + eps_p
    return (nu_e * eps_e + nu_p * eps_p) / total if total > 0.0 else nu_e


def ek_damage(
    S_mean,
    S_sin,
    S_cos,
    E_sin,
    E_cos,
    E: float,
    nu: float,
    *,
    alpha: float = 0.5,
    n: float = 1.0,
    K_prime: float | None = None,
    n_prime: float | None = None,
) -> float:
    """psi of Eq. (16). When K', n' are supplied (cyclic Ramberg-Osgood, stress-controlled), the
    plastic distortional energy of the Masing loop (the zeta term of the paper) is included and
    nu_bar, p_bar account for the plastic strains (Prandtl-Reuss direction, nu_p = 0.5)."""
    sigma_bar = np.sqrt(3.0) * sqrt_j2_amplitude(S_sin, S_cos)
    if sigma_bar <= 0.0:
        return 0.0
    effective_modulus = 3.0 * E / (2.0 * (1.0 + nu))
    dW_d = (2.0 * sigma_bar) ** 2 / (2.0 * effective_modulus)
    nu_bar = nu
    e_sin_eff, e_cos_eff = np.asarray(E_sin, float), np.asarray(E_cos, float)
    if K_prime is not None and n_prime is not None:
        eps_p = (sigma_bar / K_prime) ** (1.0 / n_prime)
        dW_d += (1.0 - n_prime) / (2.0 * (1.0 + n_prime)) * (2.0 * sigma_bar) * (2.0 * eps_p)
        nu_bar = effective_poisson(sigma_bar / E, eps_p, nu)
        scale = 1.5 * eps_p / sigma_bar
        e_sin_eff = e_sin_eff + scale * _deviator(S_sin)
        e_cos_eff = e_cos_eff + scale * _deviator(S_cos)
    mean_factor = 1.0 + alpha * float(np.trace(np.asarray(S_mean, dtype=float))) / sigma_bar
    if mean_factor <= 0.0:
        return 0.0
    return dW_d * mean_factor / constraint_factor(e_sin_eff, e_cos_eff, nu_bar) ** n


class EllyinKujawski:
    """Ellyin & Kujawski (1993) Eq. (16): elastic form, with the plastic Masing term via K', n'."""

    name = "EK"
    optional_params = {
        "alpha_EK": "0.5 (per the paper, Eq. 18)",
        "n_EK": "1.0 (per the paper, p.61)",
        "K_prime": "none: elastic form (supplying n_prime adds the plastic Masing term)",
        "n_prime": "none: elastic form (supplying K_prime adds the plastic Masing term)",
    }

    def required_params(self) -> set[str]:
        return {"E", "nu"}

    def evaluate_case(
        self, *, S0, E0, S1, E1, params: Mapping[str, float], R_list=None, harmonics=None
    ) -> CaseResult:
        E, nu = float(params["E"]), float(params["nu"])
        S_mean, S_sin, S_cos = harmonic_parts(S0, S1, harmonics)
        if harmonics is not None and "E_sin" in harmonics:
            E_sin, E_cos = (np.asarray(harmonics[k], dtype=float) for k in ("E_sin", "E_cos"))
        else:
            E_sin, E_cos = (_elastic_strain(x, E, nu) for x in (S_sin, S_cos))
        alpha_opt = params.get("alpha_EK")
        n_opt = params.get("n_EK")
        k_prime_opt, n_prime_opt = params.get("K_prime"), params.get("n_prime")
        psi = ek_damage(
            S_mean,
            S_sin,
            S_cos,
            E_sin,
            E_cos,
            E,
            nu,
            alpha=0.5 if alpha_opt is None else float(alpha_opt),
            n=1.0 if n_opt is None else float(n_opt),
            K_prime=None if k_prime_opt is None else float(k_prime_opt),
            n_prime=None if n_prime_opt is None else float(n_prime_opt),
        )
        return CaseResult(values={"": psi})


def _deviator(S) -> np.ndarray:
    S = np.asarray(S, dtype=float)
    return S - np.trace(S) / 3.0 * np.eye(3)


def _elastic_strain(S, E: float, nu: float) -> np.ndarray:
    S = np.asarray(S, dtype=float)
    return ((1.0 + nu) * S - nu * np.trace(S) * np.eye(3)) / E
