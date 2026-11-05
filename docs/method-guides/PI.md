# Papuga–Růžička integral criterion (`PI`)

> **Registry name:** `PI` · **Catalogue entry:** [G02](../../METHODS.md#g02) ·
> **Source:** Papuga & Růžička (2008), <https://doi.org/10.1016/j.ijfatigue.2007.02.015> ·
> **Implementation:**
> [`integral_methods/papuga_ruzicka.py`](../../src/multifat/models/integral_methods/papuga_ruzicka.py)

## Overview

- **Type and family:** stress-based integral fatigue-limit criterion.
- **Idea:** the companion of [PCR](PCR.md): the same kind of per-plane quantity, averaged over all
  plane orientations instead of maximised.
- **Proposed for:** the high-cycle fatigue limit of metals under multiaxial loading.
- **Status:** fully implemented as printed; the axial calibration of Appendix A holds, the torsional
  one does not (see below).

## Original formulation

Papuga & Růžička (2008, Eq. 16):

```math
\sqrt{\frac{1}{4\pi}\int_0^{2\pi}\!\!\int_0^{\pi}
\left[a_I\,C_a^2 + b_I\left(N_a + \kappa\,N_m\right)\right]\sin\psi\,d\psi\,d\varphi} \le f_{-1},
\qquad a_I = \tfrac52\,\kappa^2,\quad b_I = f_{-1}\,(3 - \kappa^2),
```

with $\kappa = f_{-1}/t_{-1}$, $C_a$ the minimum-circumscribed-circle shear amplitude and $N_a$, $N_m$
the normal stress amplitude and mean on each plane. The orientation average of $N_m$ is the mean
hydrostatic stress $\sigma_{H,m}$.

**Source inconsistency.** Appendix A (Eq. A.2) integrates $N_a = t_{-1}\sin 2\varphi\sin^2\psi$ in
torsion as a *signed* quantity (integral 0). An amplitude is non-negative; with $|N_a|$ the torsion
calibration is not met: reversed torsion at $t_{-1}$ gives the index
$\sqrt{1 + (3 - \kappa^2)\,4/(3\pi\kappa)}$ (+5.6 % at $\kappa = 1.6$).

## Repository implementation

$\mathrm{DP} = $ LHS $/f_{-1}$, with the sphere average on a 48 × 192 Gauss–Legendre/azimuth grid
(the non-smooth $|N_a|$ integrates to about $4\cdot10^{-4}$ relative).

**Repository choices**

- *Eq. (16) as printed, with $N_a \ge 0$.* Reversed tension gives exactly 1; reversed torsion does
  not (formula above). This is a property of the published criterion, kept visible rather than
  re-calibrated.
- *Negative radicand* clipped to 0.
- *Life:* the index is the DP of the shared master curve
  ([README](README.md#from-damage-parameter-to-life-the-master-curve)).
- No `_ext` variant.

## Material constants and inputs

| Symbol | Python / workbook name | Unit | Source | Required |
| --- | --- | --- | --- | --- |
| $f_{-1}$ | `Sigm1` | MPa (amplitude) | workbook Summary, R = -1 | yes |
| $t_{-1}$ | `Taum1` | MPa (amplitude) | workbook Summary, R = -1 | yes |
| $\boldsymbol\sigma(t)$ | `S_mean`, `S_sin`, `S_cos` | MPa | Dataset sheet | yes |

## Calibration

1. **Original procedure.** Closed-form $a_I$, $b_I$ from $f_{-1}$, $t_{-1}$ (Appendix A).
2. **Repository.** The same closed forms; nothing is fitted except the master-curve constants on the
   uniaxial R = -1 design tests.

## Worked example

Synthetic demonstration material: $f_{-1} = 300$, $t_{-1} = 187.5$ MPa ($\kappa = 1.6$). In uniaxial
loading the orientation averages are $\langle C_a^2\rangle = 2\sigma_a^2/15$,
$\langle N_a\rangle = \sigma_a/3$ and $\langle N_m\rangle = \sigma_m/3$, so

```math
(f_{-1}\,\mathrm{DP})^2 = \frac{\kappa^2}{3}\,\sigma_a^2 + \frac{f_{-1}(3 - \kappa^2)}{3}\,(\sigma_a + \kappa\,\sigma_m).
```

```python
import numpy as np

from multifat.models.registry import get_models

f_m1, t_m1 = 300.0, 187.5  # MPa, synthetic
kappa = f_m1 / t_m1
pi_model = get_models(["PI"])[0]
zero = np.zeros((3, 3))


def index(S_mean, S_sin):
    result = pi_model.evaluate_case(
        S0=S_mean + S_sin,
        S1=S_mean - S_sin,
        E0=zero,
        E1=zero,
        params={"Sigm1": f_m1, "Taum1": t_m1},
        harmonics={"S_mean": S_mean, "S_sin": S_sin, "S_cos": zero},
    )
    return result.values[""]


assert abs(index(zero, np.diag([f_m1, 0, 0])) - 1) < 1e-6  # Eq. (A.5)

torsion = np.zeros((3, 3))
torsion[0, 1] = torsion[1, 0] = t_m1
torsion_index = index(zero, torsion)
printed_inconsistency = np.sqrt(1 + (3 - kappa**2) * 4 / (3 * np.pi * kappa))
assert abs(torsion_index - printed_inconsistency) < 1e-3 * printed_inconsistency

s_a, s_m = 200.0, 100.0
closed_form = np.sqrt(kappa**2 / 3 * s_a**2 + f_m1 * (3 - kappa**2) / 3 * (s_a + kappa * s_m)) / f_m1
with_mean = index(np.diag([s_m, 0, 0]), np.diag([s_a, 0, 0]))
assert abs(with_mean - closed_form) < 1e-5

print(f"reversed torsion at t_-1: index {torsion_index:.4f} (formula: {printed_inconsistency:.4f})")
print(f"tension with mean: index {with_mean:.4f}")
```

Output:

```text
reversed torsion at t_-1: index 1.0567 (formula: 1.0567)
tension with mean: index 0.7452
```

**On a supplied workbook:**

```bash
uv run multifat-pipeline --material Al7075_T6 --models PI --results-dir Results/current/guides
```

## Comparison capabilities and outputs

- **Life:** master curve on the index (`Nf_expected`).
- **DP comparison:** supported, against the master-curve `DP_fit`.
- **Fatigue-limit datasets:** index error; torsion tests carry the calibration offset above.
- No `_ext` variant.

## Verification and limitations

- [`tests/methods/test_papuga_ruzicka.py`](../../tests/methods/test_papuga_ruzicka.py): Eq. (16)
  parameters, the Appendix A sphere averages, the axial calibration and the torsion inconsistency,
  the hydrostatic mean term, rotation invariance.
- On the 43 Papadopoulos et al. (1997) tests PI gives mean −0.4 % and SD 5.0 %, close to the
  paper's Table 2 ([method audit](../method-audit.md)).
- Limitations: torsion calibration not met as printed; quadrature error about $4\cdot10^{-4}$;
  fatigue-limit criterion extended to finite life by the master curve.

## References

- J. Papuga, M. Růžička (2008), Two new multiaxial criteria for high cycle fatigue computation,
  *International Journal of Fatigue* 30(1), 58–66. <https://doi.org/10.1016/j.ijfatigue.2007.02.015>
