# Böhme–Papuga integral criterion (`BP`)

> **Registry name:** `BP` · **Catalogue entry:** [I_BP](../../METHODS.md#i_bp) ·
> **Source:** Böhme & Papuga (2024), <https://doi.org/10.1111/ffe.14281>; equations and
> coefficients as given by Böhme, Papuga & Lange (2026), <https://doi.org/10.1111/ffe.70244> ·
> **Implementation:**
> [`integral_methods/bohme_papuga.py`](../../src/multifat/models/integral_methods/bohme_papuga.py)

## Overview

- **Type and family:** stress-based integral criterion.
- **Idea:** instead of selecting one critical plane, the squared shear and normal stress amplitudes,
  and their products with the mean stresses, are averaged over **all** plane orientations. The
  four weights are fixed by four fatigue strengths: fully reversed tension and torsion, and
  repeated ($R = 0$) tension and torsion.
- **Proposed for:** the high-cycle fatigue limit of metals under multiaxial loading with mean
  stresses; derived in a data-driven study.
- **Status:** fully implemented for single-harmonic loading; analytical limiting cases and phase
  invariance tested.

## Original formulation

Böhme, Papuga & Lange (2026, Eq. 6) write the BP equivalent stress as the square root of the
orientation average of a quadratic form of the plane stresses,

```math
\sigma_{eq,BP}^2 = \frac{1}{4\pi}\int_{S^2}
\left(a\,\tau_a^2 + b\,\sigma_{n,a}^2 + c\,\tau_a\tau_m + d\,\sigma_{n,a}\sigma_{n,m}\right)\,dS ,
\qquad \sigma_{eq,BP} \le s_{-1},
```

where, on each plane, $\tau_a$ and $\tau_m$ are the shear stress amplitude and mean, and
$\sigma_{n,a}$, $\sigma_{n,m}$ the normal stress amplitude and mean. With
$\kappa = s_{-1}/t_{-1}$ the coefficients are

```math
a = \tfrac92\left(\kappa^2 - \tfrac43\right), \quad
b = 3\,(3 - \kappa^2), \quad
c = \tfrac52\,\kappa^2\left[\left(\frac{2t_{-1}}{t_0}\right)^2 - 1\right], \quad
d = 5\left[\left(\frac{2s_{-1}}{s_0}\right)^2 - 1 - \frac{2c}{15}\right],
```

where $s_0$ and $t_0$ are the $R = 0$ fatigue strengths, given as **maximum** stresses (amplitude
$s_0/2$ with mean $s_0/2$). The amplitude weights are non-negative only for
$4/3 \le \kappa^2 \le 3$. When $s_0$, $t_0$ are not measured, the paper estimates them (Eqs. 1–2):

```math
s_0 = \frac{4\,s_{-1}\,\sigma_u}{s_{-1} + 2\sigma_u}, \qquad
\frac{4t_{-1}}{t_0} - \frac{2s_{-1}}{s_0} = 1 .
```

## Repository implementation

The model returns the fatigue index $\mathrm{DP} = \sigma_{eq,BP}/s_{-1}$ (1 on the fatigue limit).

- The orientation average uses a 24 × 48 Gauss–Legendre/azimuth quadrature (weights sum to 1).
- $\tau_a$ is the radius of the minimum circumscribed circle of the shear path on each plane (the
  major semi-axis of the single-harmonic ellipse); $\tau_m$ is the magnitude of the mean shear
  vector; $\sigma_{n,a}$, $\sigma_{n,m}$ follow from the harmonic tensors exactly.
- A negative integral (possible with negative mean-stress weights) is clipped to 0 before the
  square root.

**Repository choices**

- *Estimated $R = 0$ strengths.* When `Sig0` (and/or `Tau0`) is missing, Eqs. (1)–(2) are used,
  which needs `Su`. These estimates are not measured values.
- *Life.* The index is the DP of the shared master curve
  ([README](README.md#from-damage-parameter-to-life-the-master-curve)); BP is a fatigue-limit
  criterion.
- *Quadrature.* The paper's MATLAB code uses a different angular grid; agreement is within
  discretisation error, not bitwise.
- No `_ext` variant (no plane is selected).

## Material constants and inputs

| Symbol | Python / workbook name | Unit | Source | Required |
| --- | --- | --- | --- | --- |
| $s_{-1}$ | `Sigm1` | MPa (amplitude) | workbook Summary, R = -1 | yes |
| $t_{-1}$ | `Taum1` | MPa (amplitude) | workbook Summary, R = -1 | yes |
| $s_0$ | `Sig0` | MPa (maximum stress, R = 0) | workbook, else Eq. (1) | optional |
| $t_0$ | `Tau0` | MPa (maximum stress, R = 0) | workbook, else Eq. (2) | optional |
| $\sigma_u$ | `Su` | MPa | workbook (only to estimate `Sig0`) | if `Sig0` missing |
| $\boldsymbol\sigma(t)$ | `S_mean`, `S_sin`, `S_cos` | MPa | Dataset sheet | yes |

## Calibration

1. **Original procedure.** Closed-form coefficients from four fatigue strengths ($s_{-1}$,
   $t_{-1}$, $s_0$, $t_0$), the $R = 0$ ones measured or estimated by Eqs. (1)–(2).
2. **Repository.** The same closed forms from the workbook values; nothing is fitted except the
   master-curve constants on the uniaxial R = -1 design tests. The estimated `Sig0`/`Tau0` are
   reported by the run when used.

## Worked example

Synthetic demonstration material: $s_{-1} = 300$, $t_{-1} = 220$, $\sigma_u = 800$ MPa
($\kappa^2 = 1.86$, inside the admissible range); $s_0$ is estimated by Eq. (1). For uniaxial
loading the orientation averages are $\langle\cos^4\theta\rangle = 1/5$ and
$\langle\cos^2\theta\sin^2\theta\rangle = 2/15$, so with amplitude $\sigma_a$ and mean $\sigma_m$

```math
\sigma_{eq,BP}^2 = \sigma_a^2 + \sigma_a\sigma_m\left[\left(\frac{2s_{-1}}{s_0}\right)^2 - 1\right],
```

which gives 1 both at $s_{-1}$ (fully reversed) and at $s_0$ ($\sigma_a = \sigma_m = s_0/2$).

```python
import numpy as np

from multifat.models.registry import get_models

f_m1, t_m1, Su = 300.0, 220.0, 800.0  # MPa, synthetic
f_0 = 4 * f_m1 * Su / (f_m1 + 2 * Su)  # Eq. (1), R = 0 maximum stress
bp = get_models(["BP"])[0]
zero = np.zeros((3, 3))
params = {"Sigm1": f_m1, "Taum1": t_m1, "Su": Su}


def index(S_mean, S_sin, S_cos=zero):
    """BP fatigue index sigma_eq,BP / s_-1."""
    result = bp.evaluate_case(
        S0=S_mean + S_sin,
        S1=S_mean - S_sin,
        E0=zero,
        E1=zero,
        params=params,
        harmonics={"S_mean": S_mean, "S_sin": S_sin, "S_cos": S_cos},
    )
    return result.values[""]


def uniaxial(amplitude, mean):
    return np.diag([mean, 0, 0]), np.diag([amplitude, 0, 0])


torsion = np.zeros((3, 3))
torsion[0, 1] = torsion[1, 0] = t_m1
assert abs(index(*uniaxial(f_m1, 0.0)) - 1) < 1e-9
assert abs(index(zero, torsion) - 1) < 1e-9
assert abs(index(*uniaxial(f_0 / 2, f_0 / 2)) - 1) < 1e-9  # R = 0 limit

s_a, s_m = 200.0, 150.0
closed_form = np.sqrt(s_a**2 + s_a * s_m * ((2 * f_m1 / f_0) ** 2 - 1)) / f_m1
with_mean = index(*uniaxial(s_a, s_m))
assert abs(with_mean - closed_form) < 1e-9

# Moving the time origin (a common phase shift of all components) leaves the index unchanged
S_sin, S_cos = np.diag([s_a, 0, 0]), np.zeros((3, 3))
S_cos[0, 1] = S_cos[1, 0] = 100.0
phi = 0.4
shifted = index(
    zero, S_sin * np.cos(phi) - S_cos * np.sin(phi), S_sin * np.sin(phi) + S_cos * np.cos(phi)
)
assert abs(index(zero, S_sin, S_cos) - shifted) < 1e-9

print(f"estimated s_0 = {f_0:.1f} MPa")
print(f"index with mean stress: {with_mean:.4f}; out of phase: {index(zero, S_sin, S_cos):.4f}")
```

Output:

```text
estimated s_0 = 505.3 MPa
index with mean stress: 0.7623; out of phase: 0.7859
```

**On a supplied workbook:**

```bash
uv run multifat-pipeline --material Al7075_T6 --models BP --results-dir Results/current/guides
```

## Comparison capabilities and outputs

- **Life:** master curve on the index (`Nf_expected`).
- **DP comparison:** supported, against the master-curve `DP_fit`.
- **Fatigue-limit datasets:** index error, i.e. Böhme & Papuga's fatigue index error
  $\mathrm{FI} - 1$.
- No `_ext` variant.

## Verification and limitations

- [`tests/test_bohme_papuga.py`](../../tests/test_bohme_papuga.py): the four loading limits, phase
  origin invariance, the $R = 0$ estimates.
- [`tests/test_caim.py`](../../tests/test_caim.py): BP and CAIM are distinct registered models.
- Not verified: the paper's database results; the catalogue records `basic_numerical_tests`.
- Limitations: single-harmonic loading; admissible $\kappa$ range $4/3 \le \kappa^2 \le 3$ is not
  enforced (a weight becomes negative outside it); estimated $R = 0$ strengths.

## References

- Böhme & Papuga (2024), Advancements in stress-based multiaxial fatigue prediction: a
  data-driven approach and a new criterion, *Fatigue & Fracture of Engineering Materials &
  Structures* 47. <https://doi.org/10.1111/ffe.14281>
- Böhme, Papuga & Lange (2026), Decoupling amplitude and mean stress effects in multiaxial
  fatigue: a critical–integral approach, *Fatigue & Fracture of Engineering Materials &
  Structures*. <https://doi.org/10.1111/ffe.70244>
