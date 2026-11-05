# Papuga–Růžička critical-plane criterion (`PCR`)

> **Registry name:** `PCR` · **Catalogue entry:** [G01](../../METHODS.md#g01) ·
> **Source:** Papuga & Růžička (2008), <https://doi.org/10.1016/j.ijfatigue.2007.02.015> ·
> **Implementation:**
> [`integral_methods/papuga_ruzicka.py`](../../src/multifat/models/integral_methods/papuga_ruzicka.py)

## Overview

- **Type and family:** stress-based critical-plane fatigue-limit criterion (PCr, later PCRN).
- **Idea:** on each plane, a quadratic combination of the shear amplitude and a linear term in the
  normal stress amplitude and mean; the critical plane maximises it. The coefficients are chosen so
  that both fully reversed limits are met exactly, with two branches in $\kappa = f_{-1}/t_{-1}$.
- **Proposed for:** the high-cycle fatigue limit of metals under in-phase and out-of-phase loading
  with mean stresses.
- **Status:** fully implemented; the calibrations of the paper's Appendix B reproduced in both
  branches. The paper prints no per-test values.

## Original formulation

Papuga & Růžička (2008, Eq. 17):

```math
\max_{\mathbf n}\sqrt{a_c\,C_a^2 + b_c\left(N_a + \frac{t_{-1}}{f_0}\,N_m\right)} \le f_{-1},
```

where $C_a$ is the radius of the smallest circle enclosing the shear path on the plane, $N_a$ and
$N_m$ the normal stress amplitude and mean, and $f_0$ the repeated ($R = 0$) axial fatigue limit as a
maximum stress. With $\kappa = f_{-1}/t_{-1}$:

```math
\kappa < \sqrt{4/3}:\quad a_c = \tfrac12\left(\kappa^2 + \sqrt{\kappa^4 - \kappa^2}\right),\quad b_c = f_{-1};
\qquad
\kappa \ge \sqrt{4/3}:\quad a_c = \left(\frac{4\kappa^2}{4 + \kappa^2}\right)^2,\quad
b_c = \frac{8 f_{-1}\kappa^2(4 - \kappa^2)}{(4 + \kappa^2)^2}.
```

The two branches meet at $\kappa = \sqrt{4/3}$. In the paper $f_0$ comes from Morrow's formula
(Eq. 1). Eq. (A.17) prints $\sin 2\varphi_t$ as the common factor of Eq. (A.16), which factors as
$\sin 2\psi_t$ (misprint).

## Repository implementation

$\mathrm{DP} = $ LHS $/f_{-1}$, equal to 1 on the fatigue limit; the paper's fatigue index error
(Eq. 5) is $100\,(\mathrm{DP} - 1)$. The maximum over planes uses a 24 × 48 sphere grid refined by
pattern search.

**Repository choices**

- *Negative radicand* (compressive mean normal stress) clipped to 0.
- *$f_0$:* workbook `Sig0`, else the Böhme et al. (2026) Eq. (1) estimate from `Su` (as for BP),
  not Morrow's formula.
- *Life:* the index is the DP of the shared master curve
  ([README](README.md#from-damage-parameter-to-life-the-master-curve)).
- No `_ext` variant.

## Material constants and inputs

| Symbol | Python / workbook name | Unit | Source | Required |
| --- | --- | --- | --- | --- |
| $f_{-1}$ | `Sigm1` | MPa (amplitude) | workbook Summary, R = -1 | yes |
| $t_{-1}$ | `Taum1` | MPa (amplitude) | workbook Summary, R = -1 | yes |
| $f_0$ | `Sig0` | MPa (maximum stress, R = 0) | workbook, else estimate from `Su` | `Sig0` or `Su` |
| $\boldsymbol\sigma(t)$ | `S_mean`, `S_sin`, `S_cos` | MPa | Dataset sheet | yes |

## Calibration

1. **Original procedure.** Closed-form $a_c$, $b_c$ from $f_{-1}$, $t_{-1}$ (Appendix B); $f_0$ from
   Morrow's formula.
2. **Repository.** The same closed forms; $f_0$ measured or estimated as above. Nothing is fitted
   except the master-curve constants on the uniaxial R = -1 design tests.

## Worked example

Synthetic demonstration material: $f_{-1} = 300$, $t_{-1} = 187.5$ MPa ($\kappa = 1.6$, second
branch), $f_0 = 450$ MPa. For uniaxial loading with amplitude $\sigma_a$ and mean $\sigma_m$, a plane
at angle $\theta$ from the load axis has $C_a = \sigma_a\sin\theta\cos\theta$,
$N_a = \sigma_a\cos^2\theta$, $N_m = \sigma_m\cos^2\theta$; the maximum over $x = \cos^2\theta$ of
$a_c\sigma_a^2 x(1-x) + b_c(\sigma_a + t_{-1}\sigma_m/f_0)\,x$ is checked below against a fine sweep.

```python
import numpy as np

from multifat.models.registry import get_models

f_m1, t_m1, f_0 = 300.0, 187.5, 450.0  # MPa, synthetic
kappa_sq = (f_m1 / t_m1) ** 2
a_c = (4 * kappa_sq / (4 + kappa_sq)) ** 2  # kappa >= sqrt(4/3)
b_c = 8 * f_m1 * kappa_sq * (4 - kappa_sq) / (4 + kappa_sq) ** 2
pcr = get_models(["PCR"])[0]
zero = np.zeros((3, 3))
params = {"Sigm1": f_m1, "Taum1": t_m1, "Sig0": f_0}


def index(S_mean, S_sin):
    result = pcr.evaluate_case(
        S0=S_mean + S_sin,
        S1=S_mean - S_sin,
        E0=zero,
        E1=zero,
        params=params,
        harmonics={"S_mean": S_mean, "S_sin": S_sin, "S_cos": zero},
    )
    return result.values[""]


torsion = np.zeros((3, 3))
torsion[0, 1] = torsion[1, 0] = t_m1
assert abs(index(zero, np.diag([f_m1, 0, 0])) - 1) < 1e-9
assert abs(index(zero, torsion) - 1) < 1e-9

s_a, s_m = 200.0, 100.0
x = np.linspace(0.0, 1.0, 1_000_001)  # x = cos^2(theta)
sweep = a_c * s_a**2 * x * (1 - x) + b_c * (s_a + t_m1 / f_0 * s_m) * x
with_mean = index(np.diag([s_m, 0, 0]), np.diag([s_a, 0, 0]))
assert abs(with_mean - np.sqrt(sweep.max()) / f_m1) < 1e-6

print(f"a_c = {a_c:.4f}, b_c = {b_c:.2f} MPa")
print(f"tension with mean: index {with_mean:.4f}")
```

Output:

```text
a_c = 2.4366, b_c = 205.59 MPa
tension with mean: index 0.7856
```

**On a supplied workbook:**

```bash
uv run multifat-pipeline --material Al7075_T6 --models PCR --results-dir Results/current/guides
```

## Comparison capabilities and outputs

- **Life:** master curve on the index (`Nf_expected`).
- **DP comparison:** supported, against the master-curve `DP_fit`.
- **Fatigue-limit datasets:** index error ($\mathrm{FI} - 1$, Eq. 5).
- No `_ext` variant.

## Verification and limitations

- [`tests/methods/test_papuga_ruzicka.py`](../../tests/methods/test_papuga_ruzicka.py): Appendix B
  calibration in both branches, continuity at $\kappa = \sqrt{4/3}$, rotation invariance, the plane
  maximum against a dense sweep for out-of-phase loading, the $f_0$ fallback.
- On the 43 Papadopoulos et al. (1997) tests PI/PCr give mean −0.4/+1.2 % and SD 5.0/4.7 %, close
  to the paper's Table 2 ([method audit](../method-audit.md)).
- Limitations: numerical maximum; estimated $f_0$ when `Sig0` is missing; fatigue-limit criterion
  extended to finite life by the master curve.

## References

- J. Papuga, M. Růžička (2008), Two new multiaxial criteria for high cycle fatigue computation,
  *International Journal of Fatigue* 30(1), 58–66. <https://doi.org/10.1016/j.ijfatigue.2007.02.015>
