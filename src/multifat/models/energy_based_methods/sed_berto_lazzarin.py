"""Strain energy density (SED) averaged over the control volume for sharp V-notches
loaded in combined mode I and mode III, after Berto & Lazzarin (2011), Int J
Fatigue 33:1055-1065, doi:10.1016/j.ijfatigue.2010.11.019 (roadmap G30). The
implementation consists of standalone point kernels that receive the notch
quantities as explicit arguments; it is deliberately not registered as a model,
because a plain specimen has no singular stress field, in which case the
averaged SED falls back to the local value and R1 and R3 are no longer needed.

Eq. (7):  Delta W = (1/E) [e1 Delta K1^2 / R1^(2(1 - lambda1)) + e3 Delta K3^2 / R3^(2(1 - lambda3))]
Eq. (8a): R1 = (sqrt(2 e1) Delta K1A / Delta sigma1A)^(1/(1 - lambda1))
Eq. (8b): R3 = (sqrt(e3/(1 + nu)) Delta K3A / Delta tau3A)^(1/(1 - lambda3))

Here Delta K denotes the notch stress intensity factor ranges, lambda the
Williams eigenvalues, and e1, e3 the SED shape constants associated with the
opening angle (2 alpha = 90 deg, nu = 0.3: lambda1 = 0.5445, lambda3 = 0.6667,
e1 = 0.1462, e3 = 0.3103, p.1063), while the A-level ranges are taken from
notched and plain specimens at the same N_A. By construction, evaluating Eq. (7)
at the A level yields Delta sigma1A^2/(2E) for mode I and
(1 + nu) Delta tau3A^2 / E for mode III. The phase effect reported in the paper
appears only in the scatter band (no separate term), and the load ratio is
weighted by c_W (Eq. 1), equal to 1 for R = 0 and 0.5 for R = -1.
"""

from __future__ import annotations

import numpy as np


def control_radii(
    dK1A: float,
    dsigma1A: float,
    dK3A: float,
    dtau3A: float,
    e1: float,
    e3: float,
    lambda1: float,
    lambda3: float,
    nu: float,
) -> tuple[float, float]:
    """Return the control radii R1 and R3 defined by Eqs. (8a) and (8b)."""
    R1 = (np.sqrt(2.0 * e1) * dK1A / dsigma1A) ** (1.0 / (1.0 - lambda1))
    R3 = (np.sqrt(e3 / (1.0 + nu)) * dK3A / dtau3A) ** (1.0 / (1.0 - lambda3))
    return float(R1), float(R3)


def averaged_sed(
    dK1: float,
    dK3: float,
    R1: float,
    R3: float,
    e1: float,
    e3: float,
    lambda1: float,
    lambda3: float,
    E: float,
) -> float:
    """Delta W from Eq. (7) (energy per unit volume, i.e. NSIF^2 / (E length))."""
    mode1_contribution = e1 * dK1**2 / R1 ** (2.0 * (1.0 - lambda1))
    mode3_contribution = e3 * dK3**2 / R3 ** (2.0 * (1.0 - lambda3))
    return float((mode1_contribution + mode3_contribution) / E)
