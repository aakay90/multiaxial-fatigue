# Critical-amplitude integral-mean criterion (`CAIM`)

> **Registry name:** `CAIM` · **Catalogue entry:** [I_CAIM](../../METHODS.md#i_caim) ·
> **Source:** Böhme, Papuga & Lange (2026), <https://doi.org/10.1111/ffe.70244> ·
> **Implementation:** [`integral_methods/caim.py`](../../src/multifat/models/integral_methods/caim.py)

## Overview

- **Type and family:** hybrid stress criterion: a **critical-plane** maximum for the amplitude
  term and an **integral** (orientation average) for the mean-stress term.
- **Idea:** amplitude effects are governed by the most loaded plane, whereas mean-stress effects
  are better described by an average over all planes; the two are decoupled.
- **Proposed for:** the high-cycle fatigue limit of metals under multiaxial loading with mean
  stresses; it is the successor of [BP](BP.md) by the same authors.
- **Status:** fully implemented for single-harmonic loading; equations checked against the
  supplied MATLAB implementation (`damage_criteria_CAIM.m`) by an independent dense angular
  evaluation.

## Original formulation

Böhme, Papuga & Lange (2026):

```math
\sigma_{eq,CAIM}^2 = \max_{\mathbf n}\left(a\,\tau_a^2 + b\,\sigma_{n,a}^2\right)
+ \frac{1}{4\pi}\int_{S^2}\left(c\,\tau_a\tau_m + d\,\sigma_{n,a}\sigma_{n,m}\right)dS,
\qquad \sigma_{eq,CAIM} \le s_{-1},
```

with $\kappa = s_{-1}/t_{-1}$,

```math
a = \kappa^2, \qquad
b = \begin{cases} 1 & \kappa^2 < 2 \\ \kappa^2 - \kappa^4/4 & \kappa^2 \ge 2 \end{cases},
```

and the mean-stress weights $c$, $d$ of [BP](BP.md#original-formulation) (from $t_0$ and $s_0$, the
$R = 0$ strengths as maximum stresses, estimated by Eqs. 1–2 when not measured). Plane quantities
are as in BP. Negative squared equivalent stresses are clipped to zero, as in the MATLAB code.

## Repository implementation

The model returns $\mathrm{DP} = \sigma_{eq,CAIM}/s_{-1}$ (1 on the fatigue limit).

- Amplitude term: maximum over a 24 × 48 sphere grid, refined by a pattern search from the 12 best
  grid normals and the three axes.
- Mean term: the same orientation average as BP.
- $\tau_a$: radius of the minimum circumscribed circle of the shear ellipse on each plane.

**Repository choices**

- *Quadrature and maximum.* Sphere quadrature and a numerical refinement replace the uniform
  angular summation of the MATLAB code; agreement is within discretisation error and the global
  maximum is searched, not proven.
- *Estimated $R = 0$ strengths* when `Sig0`/`Tau0` are missing (needs `Su`).
- *Life.* The index is the DP of the shared master curve
  ([README](README.md#from-damage-parameter-to-life-the-master-curve)).
- No `_ext` variant.

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

1. **Original procedure.** Closed-form weights from $s_{-1}$, $t_{-1}$, $s_0$, $t_0$.
2. **Repository.** The same closed forms from the workbook values (with the BP estimates for the
   $R = 0$ strengths when missing); nothing is fitted except the master-curve constants on the
   uniaxial R = -1 design tests.

## Worked example

Synthetic demonstration material: $s_{-1} = 300$, $t_{-1} = 220$, $\sigma_u = 800$ MPa
($\kappa^2 = 1.86 < 2$, so $b = 1$). In uniaxial loading the amplitude maximum is on the plane normal
to the load, $\max(a\tau_a^2 + \sigma_{n,a}^2) = \sigma_a^2$ (since $\kappa^2 < 2$), and the mean
term is the BP one, so CAIM and BP coincide: both give
$\sigma_{eq}^2 = \sigma_a^2 + \sigma_a\sigma_m[(2s_{-1}/s_0)^2 - 1]$. They differ for multiaxial
amplitudes, where CAIM keeps the most loaded plane.

```python
import numpy as np

from multifat.models.registry import get_models

f_m1, t_m1, Su = 300.0, 220.0, 800.0  # MPa, synthetic
f_0 = 4 * f_m1 * Su / (f_m1 + 2 * Su)  # Eq. (1)
caim, bp = get_models(["CAIM", "BP"])
zero = np.zeros((3, 3))
params = {"Sigm1": f_m1, "Taum1": t_m1, "Su": Su}


def index(model, S_mean, S_sin, S_cos=zero):
    result = model.evaluate_case(
        S0=S_mean + S_sin,
        S1=S_mean - S_sin,
        E0=zero,
        E1=zero,
        params=params,
        harmonics={"S_mean": S_mean, "S_sin": S_sin, "S_cos": S_cos},
    )
    return result.values[""]


torsion = np.zeros((3, 3))
torsion[0, 1] = torsion[1, 0] = t_m1
assert abs(index(caim, zero, np.diag([f_m1, 0, 0])) - 1) < 1e-9
assert abs(index(caim, zero, torsion) - 1) < 1e-9

s_a, s_m = 200.0, 150.0
closed_form = np.sqrt(s_a**2 + s_a * s_m * ((2 * f_m1 / f_0) ** 2 - 1)) / f_m1
uniaxial = (np.diag([s_m, 0, 0]), np.diag([s_a, 0, 0]))
assert abs(index(caim, *uniaxial) - closed_form) < 1e-9
assert abs(index(bp, *uniaxial) - closed_form) < 1e-9

# Equibiaxial amplitude: every plane containing the z axis carries sigma_n,a = s_a, tau_a = 0
equibiaxial = np.diag([s_a, s_a, 0.0])
assert abs(index(caim, zero, equibiaxial) - s_a / f_m1) < 1e-9

print(f"uniaxial with mean: CAIM {index(caim, *uniaxial):.4f} = BP {index(bp, *uniaxial):.4f}")
print(f"equibiaxial: CAIM {index(caim, zero, equibiaxial):.4f}, BP {index(bp, zero, equibiaxial):.4f}")
```

Output:

```text
uniaxial with mean: CAIM 0.7623 = BP 0.7623
equibiaxial: CAIM 0.6667, BP 0.9754
```

For the equibiaxial amplitude CAIM takes the most loaded plane ($\sigma_{n,a} = \sigma_a$), whereas
BP averages over all orientations with weights tuned on uniaxial and torsional loading, and gives a
46 % higher index here. Which is closer to experiment is what a comparison on biaxial data tests.

**On a supplied workbook:**

```bash
uv run multifat-pipeline --material Al7075_T6 --models CAIM --results-dir Results/current/guides
```

## Comparison capabilities and outputs

- **Life:** master curve on the index (`Nf_expected`).
- **DP comparison:** supported, against the master-curve `DP_fit`.
- **Fatigue-limit datasets:** index error.
- No `_ext` variant.

## Verification and limitations

- [`tests/test_caim.py`](../../tests/test_caim.py): the four loading limits and both branches of
  $b$; an independent dense angular evaluation of the MATLAB equations; clipping; BP and CAIM
  distinct.
- Not verified: the paper's database statistics; the catalogue records `basic_numerical_tests`.
- Limitations: single-harmonic loading; numerical maximum; estimated $R = 0$ strengths.

## References

- Böhme, Papuga & Lange (2026), Decoupling amplitude and mean stress effects in multiaxial
  fatigue: a critical–integral approach, *Fatigue & Fracture of Engineering Materials &
  Structures*. <https://doi.org/10.1111/ffe.70244>
