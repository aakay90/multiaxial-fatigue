# Sines (`SINES`)

> **Registry name:** `SINES` · **Catalogue entry:** [N02](../../METHODS.md#n02) ·
> **Source:** Sines (1959), as restated by Papadopoulos et al. (1997),
> <https://doi.org/10.1016/S0142-1123(96)00064-3> · **Implementation:**
> [`invariant_methods/sines.py`](../../src/multifat/models/invariant_methods/sines.py)

## Overview

- **Type and family:** stress-invariant fatigue-limit criterion.
- **Idea:** as Crossland, the amplitude of $\sqrt{J_2}$ drives fatigue, but only the **mean**
  hydrostatic stress shifts the limit; the hydrostatic amplitude has no effect.
- **Proposed for:** the high-cycle fatigue limit of metals with mean stresses. It is the oldest of
  the invariant criteria in common use.
- **Status:** fully implemented; Papadopoulos et al. (1997) Table 1 reproduced for phase shifts of
  0°, 90° and 180°.

## Original formulation

Papadopoulos et al. (1997, Eqs. 62–64, p. 9) write Sines' criterion as

```math
\sqrt{J_{2,a}} + \kappa\,\sigma_{H,m} \le \lambda .
```

Sines' own calibration (Eq. 63) uses the fully reversed and the repeated ($R = 0$) bending
limits, $\kappa = 3t_{-1}/f_0 - \sqrt3$, $\lambda = t_{-1}$. With the Goodman estimate
$f_0 = f_{-1}/(1 + f_{-1}/\sigma_u)$ and the torsion-to-bending ratio implied by the criterion,
$t_{-1} = f_{-1}/\sqrt3$, this becomes the form evaluated in the paper's Table 1 (Eq. 64):

```math
\sqrt{J_{2,a}} + \kappa\,\sigma_{H,m} \le t_{-1}, \qquad \kappa = \frac{\sqrt3\,f_{-1}}{\sigma_u}.
```

$\sqrt{J_{2,a}}$ and $\sigma_{H,m}$ are defined as for [Crossland](CROSSLAND.md); $\sigma_u$ is the
ultimate tensile strength.

## Repository implementation

```math
\mathrm{DP} = \frac{\sqrt{J_{2,a}} + \kappa\,\sigma_{H,m}}{t_{-1}}, \qquad \kappa = \frac{\sqrt3\,f_{-1}}{S_u},
```

a dimensionless index with the exact enclosing radius of the single-harmonic deviatoric ellipse
(as in Crossland). No plane search; no `_ext` variant.

**Repository choices**

- *Printed Eq. (64).* The coefficient $\kappa = \sqrt3 f_{-1}/S_u$ is independent of $t_{-1}$, as in
  the paper's Table 1. Consequently fully reversed tension at $f_{-1}$ gives the index
  $f_{-1}/(\sqrt3\,t_{-1})$, which equals 1 only when $t_{-1} = f_{-1}/\sqrt3$. Using Eq. (63)
  with the Goodman $f_0$ would miss the paper's mean-stress rows by up to 11 points.
- *Life.* The index is the DP of the shared master curve
  ([README](README.md#from-damage-parameter-to-life-the-master-curve)), a repository extension of a
  fatigue-limit criterion.

## Material constants and inputs

| Symbol | Python / workbook name | Unit | Source | Required |
| --- | --- | --- | --- | --- |
| $f_{-1}$ | `Sigm1` | MPa (amplitude) | workbook Summary, R = -1 | yes |
| $t_{-1}$ | `Taum1` | MPa (amplitude) | workbook Summary, R = -1 | yes |
| $\sigma_u$ | `Su` | MPa | workbook Summary | yes |
| $\boldsymbol\sigma(t)$ | `S_mean`, `S_sin`, `S_cos` | MPa | Dataset sheet | yes |

## Calibration

1. **Original procedure.** $\kappa$ from the reversed and repeated bending limits (Eq. 63).
2. **Repository.** Closed form of Eq. (64) from the workbook $f_{-1}$, $t_{-1}$, $S_u$; nothing is
   fitted except the master-curve constants on the uniaxial R = -1 design tests. A measured
   $f_0$ (`Sig0`) is not used.

## Worked example

Synthetic demonstration material: $f_{-1} = 300$, $t_{-1} = 200$, $S_u = 800$ MPa.

```python
import numpy as np

from multifat.models.registry import get_models

f_m1, t_m1, Su = 300.0, 200.0, 800.0  # MPa, synthetic
kappa = np.sqrt(3) * f_m1 / Su
sines = get_models(["SINES"])[0]
zero = np.zeros((3, 3))
params = {"Sigm1": f_m1, "Taum1": t_m1, "Su": Su}


def index(S_mean, S_sin):
    """Sines index of S(t) = S_mean + S_sin sin(wt)."""
    result = sines.evaluate_case(
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
tension = np.diag([f_m1, 0, 0])
assert abs(index(zero, torsion) - 1) < 1e-12
assert abs(index(zero, tension) - f_m1 / (np.sqrt(3) * t_m1)) < 1e-12

# Tension sigma_a = 200 MPa with mean sigma_m = 150 MPa: only the mean hydrostatic stress counts
s_a, s_m = 200.0, 150.0
with_mean = index(np.diag([s_m, 0, 0]), np.diag([s_a, 0, 0]))
assert abs(with_mean - (s_a / np.sqrt(3) + kappa * s_m / 3) / t_m1) < 1e-12

print(f"kappa = {kappa:.4f}")
print(f"index at f_-1: {index(zero, tension):.4f} (1 only if t_-1 = f_-1/sqrt(3))")
print(f"index with mean stress: {with_mean:.4f}")
```

Output:

```text
kappa = 0.6495
index at f_-1: 0.8660 (1 only if t_-1 = f_-1/sqrt(3))
index with mean stress: 0.7397
```

**On a supplied workbook:**

```bash
uv run multifat-pipeline --material Al7075_T6 --models SINES --results-dir Results/current/guides
```

## Comparison capabilities and outputs

- **Life:** master curve on the index (`Nf_expected`).
- **DP comparison:** supported, against the master-curve `DP_fit`.
- **Fatigue-limit datasets:** index error; note the non-unit index at $f_{-1}$ discussed above.
- No `_ext` variant.

## Verification and limitations

- [`tests/methods/test_crossland_sines.py`](../../tests/methods/test_crossland_sines.py):
  Papadopoulos et al. (1997) Table 1 reproduced for $\delta = 0°, 90°, 180°$; intermediate phase
  shifts are strict expected failures (the table used $\sin\delta$ for $\sin^2\delta$); two 42CrMo4
  rows remain 0.3 points off (unresolved).
- Limitations: the hydrostatic amplitude is ignored, so fully reversed tension and torsion are not
  both matched unless $t_{-1}/f_{-1} = 1/\sqrt3$; fatigue-limit criterion extended to finite life by
  the master curve.

## References

- G. Sines (1959), Behavior of metals under complex static and alternating stresses, in G. Sines,
  J. L. Waisman (eds.), *Metal Fatigue*, McGraw-Hill, New York.
- I. V. Papadopoulos, P. Davoli, C. Gorla, M. Filippini, A. Bernasconi (1997), A comparative study
  of multiaxial high-cycle fatigue criteria for metals, *International Journal of Fatigue* 19(3),
  219–235. <https://doi.org/10.1016/S0142-1123(96)00064-3>
