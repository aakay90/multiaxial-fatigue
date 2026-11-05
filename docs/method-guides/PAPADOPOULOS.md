# Papadopoulos (`PAPADOPOULOS`)

> **Registry name:** `PAPADOPOULOS` · **Catalogue entry:** [N03](../../METHODS.md#n03) ·
> **Source:** Papadopoulos (2001), <https://doi.org/10.1016/S0142-1123(01)00059-7> ·
> **Implementation:**
> [`integral_methods/papadopoulos.py`](../../src/multifat/models/integral_methods/papadopoulos.py)

## Overview

- **Type and family:** mesoscopic, critical-plane/integral criterion on the generalised shear
  amplitude.
- **Idea:** plastic slip in a grain depends on the resolved shear stress along all slip
  directions of a plane; the root-mean-square over the directions of a plane (the generalised shear
  amplitude $T_a$), maximised over planes, plus the hydrostatic stress, governs fatigue. A
  multiaxial S–N form extends the limit to finite life.
- **Proposed for:** long-life (high-cycle) fatigue of metals under in-phase and out-of-phase
  loading, with mean stresses.
- **Status:** fully implemented; closed forms and coefficients of the 2001 paper reproduced.

## Original formulation

Papadopoulos (2001). The generalised shear amplitude on the plane of normal $\mathbf n$ is
(Eq. 10)

```math
T_a(\mathbf n)^2 = \frac1\pi\int_0^{2\pi}\tau_a(\mathbf n,\chi)^2\,d\chi ,
```

where $\tau_a(\mathbf n,\chi)$ is the amplitude of the shear stress resolved along the direction
$\chi$ of the plane. The fatigue limit (Eqs. 1, 25) and the multiaxial S–N curve (Eqs. 40–41) read

```math
\max_{\mathbf n} T_a + \alpha\,\sigma_{H,\max} \le \gamma, \qquad
\frac{\max_{\mathbf n} T_a + \alpha\,\sigma_{H,a}}{1 - (\alpha/\gamma)\,\sigma_{H,m}} = \gamma_N,
\qquad \gamma = t_{-1}, \quad \alpha = 3\left(\frac{t_{-1}}{f_{-1}} - \frac12\right),
```

where $\gamma_N$ is the equivalent fully reversed torsion amplitude at life $N$ (Eq. 42). With
$\sigma_{H,m} = 0$ the S–N form reduces to the limit form.

## Repository implementation

For a single-harmonic history the shear traction on a plane is
$\mathbf t_s\sin\omega t + \mathbf t_c\cos\omega t$ and Eq. (10) integrates exactly to
$T_a^2 = |\mathbf t_s|^2 + |\mathbf t_c|^2$ (the RSS shear amplitude). The code returns

```math
\mathrm{DP} = \frac{\gamma_N}{t_{-1}} =
\frac{\max_{\mathbf n} T_a + \alpha\,\sigma_{H,a}}{t_{-1}\,\bigl(1 - (\alpha/t_{-1})\,\sigma_{H,m}\bigr)},
```

maximising $T_a$ over a 24 × 48 sphere grid with pattern-search refinement. DP = 1 at both fully
reversed limits and is $+\infty$ once $\sigma_{H,m} \ge t_{-1}/\alpha$.

**Repository choices**

- *Index of Eq. (41).* The equivalent torsion amplitude is divided by $t_{-1}$, so the fatigue-limit
  value is 1. Eq. (40) writes $T_a$ without the max of Eqs. (39) and (41) (notational slip in the
  paper); the max is used.
- *Life.* The index is the DP of the shared master curve
  ([README](README.md#from-damage-parameter-to-life-the-master-curve)); the paper's torsional
  S–N curve $\gamma_N(N)$ is not fitted separately.
- The 1999 volumetric form $\sqrt{J_2(\mathbf A) + J_2(\mathbf B)} + \alpha\sigma_{H,\max} \le t_{-1}$
  (Papadopoulos 1999) is a tested function (`papadopoulos_1999_index`), not a registered model.

## Material constants and inputs

| Symbol | Python / workbook name | Unit | Source | Required |
| --- | --- | --- | --- | --- |
| $f_{-1}$ | `Sigm1` | MPa (amplitude) | workbook Summary, R = -1 | yes, $> 0$ |
| $t_{-1}$ | `Taum1` | MPa (amplitude) | workbook Summary, R = -1 | yes, $> 0$ |
| $\boldsymbol\sigma(t)$ | `S_mean`, `S_sin`, `S_cos` | MPa | Dataset sheet | yes |

## Calibration

1. **Original procedure.** $\alpha$ and $\gamma$ from the fully reversed tension (bending) and
   torsion limits; $\gamma_N$ from a torsion S–N curve.
2. **Repository.** Closed form from the workbook `Sigm1`, `Taum1`; nothing is fitted except the
   master-curve constants on the uniaxial R = -1 design tests.
3. $\alpha > 0$ requires $t_{-1}/f_{-1} > 1/2$.

## Worked example

Synthetic demonstration material: $f_{-1} = 300$, $t_{-1} = 200$ MPa, so $\alpha = 0.5$. In
reversed tension $\max T_a = \sigma_a/2$ and $\sigma_{H,a} = \sigma_a/3$; in torsion
$\max T_a = \tau_a$.

```python
import numpy as np

from multifat.models.registry import get_models

f_m1, t_m1 = 300.0, 200.0  # MPa, synthetic
alpha = 3 * (t_m1 / f_m1 - 0.5)
papadopoulos = get_models(["PAPADOPOULOS"])[0]
zero = np.zeros((3, 3))


def index(S_mean, S_sin):
    """Papadopoulos (2001) index gamma_N / t_-1 of S(t) = S_mean + S_sin sin(wt)."""
    result = papadopoulos.evaluate_case(
        S0=S_mean + S_sin,
        S1=S_mean - S_sin,
        E0=zero,
        E1=zero,
        params={"Sigm1": f_m1, "Taum1": t_m1},
        harmonics={"S_mean": S_mean, "S_sin": S_sin, "S_cos": zero},
    )
    return result.values[""]


torsion = np.zeros((3, 3))
torsion[0, 1] = torsion[1, 0] = t_m1
assert abs(index(zero, torsion) - 1) < 1e-9
assert abs(index(zero, np.diag([f_m1, 0, 0])) - 1) < 1e-9

# Tension s_a = 200 with mean s_m = 100 MPa, Eq. (41)
s_a, s_m = 200.0, 100.0
eq41 = (s_a / 2 + alpha * s_a / 3) / (1 - alpha / t_m1 * s_m / 3) / t_m1
with_mean = index(np.diag([s_m, 0, 0]), np.diag([s_a, 0, 0]))
assert abs(with_mean - eq41) < 1e-9

print(f"alpha = {alpha:.3f}; tension with mean: index = {with_mean:.4f}")
print(f"index infinite for a mean hydrostatic stress >= {t_m1 / alpha:.0f} MPa")
```

Output:

```text
alpha = 0.500; tension with mean: index = 0.7273
index infinite for a mean hydrostatic stress >= 400 MPa
```

**On a supplied workbook:**

```bash
uv run multifat-pipeline --material Al7075_T6 --models PAPADOPOULOS --results-dir Results/current/guides
```

## Comparison capabilities and outputs

- **Life:** master curve on the index (`Nf_expected`).
- **DP comparison:** supported, against the master-curve `DP_fit`.
- **Fatigue-limit datasets:** index error.
- No `_ext` variant. [MOREL](../../METHODS.md#g23) uses the same index as its damage parameter and
  adds a native life law.

## Verification and limitations

- [`tests/methods/test_papadopoulos.py`](../../tests/methods/test_papadopoulos.py): Section 2.2
  closed forms, the coefficients of Eqs. (54) and (58) and the bending S–N curve of Eq. (55) of
  the 2001 paper (which prints no per-test values); the 1999 volumetric form against Papadopoulos
  (1999) Tables 1–4 and the Papadopoulos et al. (1997) Table 1 column (36 of 43 rows to print
  precision).
- Source misprints recorded in the tests: Eq. (46) of the 2001 paper; Eq. (5.19) of the 1999
  chapter ($1/(4\pi)$ for $1/(8\pi)$).
- Limitations: fatigue-limit/long-life formulation extended to finite life by the shared master
  curve.

## References

- I. V. Papadopoulos (2001), Long life fatigue under multiaxial loading, *International Journal of
  Fatigue* 23(10), 839–849. <https://doi.org/10.1016/S0142-1123(01)00059-7>
- I. V. Papadopoulos (1999), Multiaxial fatigue limit criterion of metals, in K. Dang Van,
  I. V. Papadopoulos (eds.), *High-Cycle Metal Fatigue*, CISM Courses and Lectures 392, Springer.
  <https://doi.org/10.1007/978-3-7091-2474-1_3>
