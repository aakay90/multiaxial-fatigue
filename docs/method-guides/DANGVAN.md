# Dang Van (`DANGVAN`)

> **Registry name:** `DANGVAN` · **Catalogue entry:** [I_DANGVAN](../../METHODS.md#i_dangvan) ·
> **Source:** Dang Van (1973); implemented in the form of Böhme, Papuga & Lange (2026),
> <https://doi.org/10.1111/ffe.70244> · **Implementation:**
> [`cp_methods/dangvan.py`](../../src/multifat/models/cp_methods/dangvan.py)

## Overview

- **Type and family:** mesoscopic, stress-based fatigue-limit criterion (a critical-plane search
  on the shear amplitude combined with the hydrostatic stress).
- **Idea:** fatigue cracks nucleate in the grains that are least favourably oriented; after elastic
  shakedown, the mesoscopic shear stress in those grains, combined with the hydrostatic stress,
  must stay below a limit line.
- **Proposed for:** the high-cycle fatigue limit of metallic components; widely used in industrial
  (e.g. automotive) design.
- **Status:** fully implemented as a **documented variant**; the closed forms and Table 4 DV
  statistics of Böhme et al. (2026) are reproduced.

## Original formulation

Dang Van's criterion (1973; in the form popularised in later papers) states that, at every instant
of the stabilised cycle,

```math
\max_t\,\bigl[\tau(t) + a\,\sigma_H(t)\bigr] \le b, \qquad
a = 3\left(\frac{t_{-1}}{f_{-1}} - \frac12\right), \qquad b = t_{-1},
```

where $\tau(t)$ is the mesoscopic shear stress (Tresca measure of the deviatoric stress minus its
shakedown centre) and $\sigma_H(t)$ the hydrostatic stress. The original papers define $\tau$
through the elastic-shakedown state and do not give closed forms for general loading.

## Repository implementation

The code implements Eq. (3) of Böhme, Papuga & Lange (2026), the modified form of Papuga and
Halama:

```math
\sigma_{eq,DV} = \kappa\,\max_{\mathbf n}\tau_{sa}(\mathbf n) + \left(3 - \tfrac32\kappa\right)\sigma_{H,\max},
\qquad \kappa = \frac{f_{-1}}{t_{-1}},
\qquad \mathrm{DP} = \frac{\sigma_{eq,DV}}{f_{-1}},
```

where $\tau_{sa}(\mathbf n)$ is the radius of the smallest circle enclosing the shear-stress path on
the plane of normal $\mathbf n$ (exact for a single harmonic), maximised over a sphere grid with
pattern-search refinement, and $\sigma_{H,\max} = \sigma_{H,m} + \sigma_{H,a}$. Dividing by $\kappa$
shows the equivalence with the classical constants:
$\tau_{sa} + 3(t_{-1}/f_{-1} - 1/2)\,\sigma_{H,\max} \le t_{-1}$.

**Repository choices**

- *Amplitude plus maximum, not maximum of the sum.* The variant adds the largest shear amplitude
  and the largest hydrostatic stress, instead of maximising $\tau(t) + a\sigma_H(t)$ over time. For
  proportional loading the two coincide. For the single-harmonic histories of this repository the
  shakedown centre is the mean deviatoric stress, which projects onto the centre of each plane's
  shear ellipse, so $|\tau(t)| \le \tau_{sa}$; with $a > 0$ ($t_{-1}/f_{-1} > 1/2$) the variant is
  therefore conservative (a sum of maxima is not smaller than the maximum of the sum).
- *Shear amplitude.* Minimum circumscribed circle on each plane, as in BP and CAIM.
- *Life.* The index is the DP of the shared master curve
  ([README](README.md#from-damage-parameter-to-life-the-master-curve)); Dang Van is a fatigue-limit
  criterion.
- `DANGVAN` is a case-level model: it has no `_ext` variant.

## Material constants and inputs

| Symbol | Python / workbook name | Unit | Source | Required |
| --- | --- | --- | --- | --- |
| $f_{-1}$ ($s_{-1}$) | `Sigm1` | MPa (amplitude) | workbook Summary, R = -1 | yes, $> 0$ |
| $t_{-1}$ | `Taum1` | MPa (amplitude) | workbook Summary, R = -1 | yes, $> 0$ |
| $\boldsymbol\sigma(t)$ | `S_mean`, `S_sin`, `S_cos` | MPa | Dataset sheet | yes |

## Calibration

1. **Original procedure.** $a$ and $b$ from the fully reversed tension (bending) and torsion
   fatigue limits.
2. **Repository.** Closed form from the workbook `Sigm1`, `Taum1`. The index equals 1 at both
   limits. Nothing is fitted except the master-curve constants on the uniaxial R = -1 design tests.

## Worked example

Synthetic demonstration material: $f_{-1} = 300$, $t_{-1} = 200$ MPa ($\kappa = 1.5$). Both limits
give an index of 1, and an equibiaxial load follows the closed form of Böhme et al. (2026, Eq. 16),
$\sigma_{eq,DV} = 2\sigma_a(1 - \kappa/4)$.

```python
import numpy as np

from multifat.models.registry import get_models

f_m1, t_m1 = 300.0, 200.0  # MPa, synthetic
kappa = f_m1 / t_m1
dang_van = get_models(["DANGVAN"])[0]
zero = np.zeros((3, 3))


def index(S_mean, S_sin):
    """Dang Van index sigma_eq,DV / f_-1 of S(t) = S_mean + S_sin sin(wt)."""
    result = dang_van.evaluate_case(
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
assert abs(index(zero, np.diag([f_m1, 0, 0])) - 1) < 1e-9
assert abs(index(zero, torsion) - 1) < 1e-9

s_a = 150.0  # equibiaxial amplitude, MPa
equibiaxial = index(zero, np.diag([s_a, s_a, 0]))
assert abs(equibiaxial - 2 * s_a * (1 - kappa / 4) / f_m1) < 1e-9

# Tension with a mean stress: tau_sa = s_a / 2, sigma_H,max = (s_m + s_a) / 3
s_a, s_m = 200.0, 100.0
with_mean = index(np.diag([s_m, 0, 0]), np.diag([s_a, 0, 0]))
assert abs(with_mean - (kappa * s_a / 2 + (3 - 1.5 * kappa) * (s_m + s_a) / 3) / f_m1) < 1e-9

print(f"equibiaxial index: {equibiaxial:.4f}; tension with mean: {with_mean:.4f}")
```

Output:

```text
equibiaxial index: 0.6250; tension with mean: 0.7500
```

**On a supplied workbook:**

```bash
uv run multifat-pipeline --material Al7075_T6 --models DANGVAN --results-dir Results/current/guides
```

## Comparison capabilities and outputs

- **Life:** master curve on the index (`Nf_expected`).
- **DP comparison:** supported, against the master-curve `DP_fit`.
- **Fatigue-limit datasets:** index error.
- No `_ext` variant.

## Verification and limitations

- [`tests/methods/test_dangvan.py`](../../tests/methods/test_dangvan.py): Eq. (16) closed forms for
  equibiaxial and equitriaxial loading over several $\kappa$, and the Table 4 DV statistics of
  Böhme et al. (2026).
- [`tests/methods/test_vu_halm_nadot.py`](../../tests/methods/test_vu_halm_nadot.py): the DV column
  of Vu, Halm & Nadot (2010) on 115 of 117 tests.
- Not implemented: the original shakedown-based mesoscopic formulation for arbitrary paths.
- Limitations: documented variant, conservative for out-of-phase loading; fatigue-limit criterion
  extended to finite life by the master curve.

## References

- K. Dang Van (1973), Sur la résistance à la fatigue des métaux, *Sciences et Technique de
  l'Armement* 47, 647–722.
- Böhme, Papuga & Lange (2026), *Fatigue & Fracture of Engineering Materials &
  Structures*. <https://doi.org/10.1111/ffe.70244>
