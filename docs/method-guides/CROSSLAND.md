# Crossland (`CROSSLAND`)

> **Registry name:** `CROSSLAND` · **Catalogue entry:** [N01](../../METHODS.md#n01) ·
> **Source:** Crossland (1956), as restated by Papadopoulos et al. (1997),
> <https://doi.org/10.1016/S0142-1123(96)00064-3> · **Implementation:**
> [`invariant_methods/crossland.py`](../../src/multifat/models/invariant_methods/crossland.py)

## Overview

- **Type and family:** stress-invariant fatigue-limit criterion.
- **Idea:** the amplitude of the second invariant of the deviatoric stress (a measure of cyclic
  shear) is the driving force; the **maximum** hydrostatic stress over the cycle opens or closes
  micro-cracks and shifts the limit linearly.
- **Proposed for:** the high-cycle fatigue limit of ductile metals under multiaxial loading; it is
  one of the reference invariant criteria in most comparative studies.
- **Status:** fully implemented; Papadopoulos et al. (1997) Table 1 reproduced for phase shifts of
  0°, 90° and 180°.

## Original formulation

In the form restated by Papadopoulos et al. (1997, Eqs. 65–66, p. 9):

```math
\sqrt{J_{2,a}} + \kappa\,\sigma_{H,\max} \le \lambda, \qquad
\kappa = \frac{3\,t_{-1}}{f_{-1}} - \sqrt3, \qquad \lambda = t_{-1},
```

where $f_{-1}$ and $t_{-1}$ are the fully reversed tension (bending) and torsion fatigue limits,
$\sigma_{H,\max} = \sigma_{H,a} + \sigma_{H,m}$ is the largest hydrostatic stress of the cycle
(Eq. 45) and $\sqrt{J_{2,a}}$ is the amplitude of the square root of the second deviatoric invariant.
For a non-proportional history, $\sqrt{J_{2,a}}$ is the radius of the smallest hypersphere that
encloses the deviatoric load path, in the norm $\|\mathbf s\| = \sqrt{\mathbf s:\mathbf s/2}$
(Eqs. 38–39). For bending with amplitude $\sigma_a$ and torsion $\tau_a$ out of phase by $\delta$
(Eq. 44):

```math
\sqrt{J_{2,a}} = \frac{1}{\sqrt2}\left[\frac{\sigma_a^2}{3} + \tau_a^2 +
\sqrt{\left(\frac{\sigma_a^2}{3} + \tau_a^2\right)^2 - \frac43\,\sigma_a^2\tau_a^2\sin^2\delta}\;\right]^{1/2}.
```

The constants follow from requiring equality at the two fatigue limits: in torsion
$\sqrt{J_{2,a}} = t_{-1}$, $\sigma_H = 0$; in tension $\sqrt{J_{2,a}} = f_{-1}/\sqrt3$,
$\sigma_{H,\max} = f_{-1}/3$.

## Repository implementation

The model returns the **fatigue index**

```math
\mathrm{DP} = \frac{\sqrt{J_{2,a}} + \kappa\,(\sigma_{H,a} + \sigma_{H,m})}{t_{-1}},
```

equal to 1 on the fatigue limit; Papadopoulos' error index is $I = 100\,(\mathrm{DP} - 1)$ (Eq. 85).
For a single-harmonic history $\boldsymbol\sigma_m + \boldsymbol\sigma_s\sin\omega t +
\boldsymbol\sigma_c\cos\omega t$ the deviatoric path is an ellipse centred on
$\mathrm{dev}\,\boldsymbol\sigma_m$, so $\sqrt{J_{2,a}}$ is its semi-major axis: the square root of
the largest eigenvalue of the $2\times2$ Gram matrix of $\mathrm{dev}\,\boldsymbol\sigma_s$ and
$\mathrm{dev}\,\boldsymbol\sigma_c$. $\sigma_{H,a} = \sqrt{(\mathrm{tr}\,\boldsymbol\sigma_s)^2 +
(\mathrm{tr}\,\boldsymbol\sigma_c)^2}/3$ and $\sigma_{H,m} = \mathrm{tr}\,\boldsymbol\sigma_m/3$.
No plane search is needed and there is no `_ext` variant.

**Repository choices**

- *Life.* Crossland is a fatigue-limit criterion. For finite-life comparison the index is used as
  the damage parameter of the shared master curve $\mathrm{DP} = A N_f^b$
  ([README](README.md#from-damage-parameter-to-life-the-master-curve)), with $f_{-1}$, $t_{-1}$
  kept at their fatigue-limit values. This is a repository extension, not Crossland's.
- The exact enclosing radius for a single harmonic replaces any numerical minimum-ball search.

## Material constants and inputs

| Symbol | Python / workbook name | Unit | Source | Required |
| --- | --- | --- | --- | --- |
| $f_{-1}$ | `Sigm1` / Summary tensile R = -1 fatigue limit | MPa (amplitude) | workbook | yes |
| $t_{-1}$ | `Taum1` / Summary torsional R = -1 fatigue limit | MPa (amplitude) | workbook | yes |
| $\boldsymbol\sigma(t)$ | `S_mean`, `S_sin`, `S_cos` | MPa | Dataset sheet | yes |

## Calibration

1. **Original procedure.** $\kappa$ and $\lambda$ follow in closed form from $f_{-1}$ and $t_{-1}$
   (above).
2. **Repository.** The same closed form, with the R = -1 limits of the workbook Summary (averaged
   per loading mode when several sources report a value at R = -1, see
   [dataset workflow](../dataset-workflow.md)). Nothing is fitted except the master-curve
   constants $A$, $b$ on the uniaxial R = -1 design tests.
3. A material whose fatigue limits are missing or flagged by the importer is skipped, with the
   reason in `<MATERIAL>_run_report.tsv`.

$\kappa > 0$ (a tensile hydrostatic stress is detrimental) requires $t_{-1}/f_{-1} > 1/\sqrt3$.

## Worked example

Synthetic demonstration material (not experimental data): $f_{-1} = 300$ MPa,
$t_{-1} = 200$ MPa, so $\kappa = 3\cdot200/300 - \sqrt3 = 0.2679$. Both fatigue limits must give
an index of 1; a bending–torsion load with a 60° phase shift is checked against Eq. (44).

```python
import numpy as np

from multifat.models.registry import get_models

f_m1, t_m1 = 300.0, 200.0  # MPa, synthetic R = -1 fatigue limits
kappa = 3 * t_m1 / f_m1 - np.sqrt(3)
crossland = get_models(["CROSSLAND"])[0]
zero = np.zeros((3, 3))


def index(S_mean, S_sin, S_cos=zero):
    """Crossland fatigue index of S(t) = S_mean + S_sin sin(wt) + S_cos cos(wt)."""
    result = crossland.evaluate_case(
        S0=S_mean + S_sin,
        S1=S_mean - S_sin,
        E0=zero,
        E1=zero,
        params={"Sigm1": f_m1, "Taum1": t_m1},
        harmonics={"S_mean": S_mean, "S_sin": S_sin, "S_cos": S_cos},
    )
    return result.values[""]


def shear(tau):
    T = np.zeros((3, 3))
    T[0, 1] = T[1, 0] = tau
    return T


assert abs(index(zero, np.diag([f_m1, 0, 0])) - 1) < 1e-12
assert abs(index(zero, shear(t_m1)) - 1) < 1e-12

# Bending sigma_a with torsion tau_a lagging by delta: tau(t) = tau_a sin(wt - delta)
s_a, tau_a, delta = 200.0, 120.0, np.radians(60.0)
S_sin = np.diag([s_a, 0, 0]) + shear(tau_a * np.cos(delta))
S_cos = shear(-tau_a * np.sin(delta))
total = s_a**2 / 3 + tau_a**2
sqrt_J2_a = np.sqrt((total + np.sqrt(total**2 - 4 / 3 * (s_a * tau_a * np.sin(delta)) ** 2)) / 2)
eq44 = (sqrt_J2_a + kappa * s_a / 3) / t_m1
out_of_phase = index(zero, S_sin, S_cos)
assert abs(out_of_phase - eq44) < 1e-12

in_phase = index(zero, np.diag([s_a, 0, 0]) + shear(tau_a))
print(f"kappa = {kappa:.4f}")
print(f"index, in phase: {in_phase:.4f}; 60 deg out of phase: {out_of_phase:.4f}")
```

Output:

```text
kappa = 0.2679
index, in phase: 0.9220; 60 deg out of phase: 0.8107
```

Crossland predicts a lower index, hence a longer life, for the out-of-phase load at the same
amplitudes, because the deviatoric path is an ellipse whose enclosing radius is smaller than the
in-phase segment's half-length. Whether a phase shift is beneficial, neutral or detrimental
depends on the material; this is a property of the criterion that comparisons on out-of-phase
data test.

**On a supplied workbook:**

```bash
uv run multifat-pipeline --material Al7075_T6 --models CROSSLAND --results-dir Results/current/guides
```

`CROSSLAND_Al7075_T6.csv` holds the index (`CP_value`, dimensionless) and the master-curve life.

## Comparison capabilities and outputs

- **Life:** master curve on the index (`Nf_expected`).
- **DP comparison:** supported, against the master-curve `DP_fit`.
- **Fatigue-limit datasets:** the index error $\mathrm{DP} - 1$ is directly Crossland's error.
- No `_ext` variant.

## Verification and limitations

- [`tests/methods/test_crossland_sines.py`](../../tests/methods/test_crossland_sines.py):
  Papadopoulos et al. (1997) Table 1 reproduced to print precision for $\delta = 0°, 90°, 180°$.
  The rows at 30°, 45°, 60° and 120° were computed in the paper with $\sin\delta$ instead of the
  $\sin^2\delta$ of Eq. (44); they are kept as strict expected failures (paper calculation error).
- [`tests/test_method_audit.py`](../../tests/test_method_audit.py) and the Vu–Halm–Nadot tables
  ([`tests/methods/test_vu_halm_nadot.py`](../../tests/methods/test_vu_halm_nadot.py)) check the
  same index on further published tests.
- Limitations: fatigue-limit criterion extended to finite life through the master curve; no
  sensitivity to the phase shift beyond the enclosing radius.

## References

- B. Crossland (1956), Effect of large hydrostatic pressures on the torsional fatigue strength of
  an alloy steel, *Proceedings of the International Conference on Fatigue of Metals*, Institution
  of Mechanical Engineers, London.
- I. V. Papadopoulos, P. Davoli, C. Gorla, M. Filippini, A. Bernasconi (1997), A comparative study
  of multiaxial high-cycle fatigue criteria for metals, *International Journal of Fatigue* 19(3),
  219–235. <https://doi.org/10.1016/S0142-1123(96)00064-3>
