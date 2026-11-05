# Morel mesoscopic life model (`MOREL`)

> **Registry name:** `MOREL` · **Catalogue entry:** [G23](../../METHODS.md#g23) ·
> **Source:** Morel (1998), <https://doi.org/10.1046/j.1460-2695.1998.00452.x> ·
> **Implementation:** [`integral_methods/morel.py`](../../src/multifat/models/integral_methods/morel.py)

## Overview

- **Type and family:** mesoscopic (grain-scale plasticity) model with a **native life law**.
- **Idea:** fatigue damage is the plastic slip accumulated in the worst-oriented grains. A fatigue
  limit follows from Papadopoulos' generalised shear amplitude and the hydrostatic stress; the life
  above the limit follows from a three-parameter law in the critical-plane shear amplitude, which
  accounts for the shape of the load path through a phase-difference coefficient.
- **Proposed for:** constant-amplitude multiaxial high-cycle fatigue, including out-of-phase loading.
- **Status:** fully implemented; the paper's worked example reproduced (with a misprint identified).

## Original formulation

Morel (1998). Endurance criterion (Eqs. 9–11):

```math
T_S + a\,P_{\max} \le b, \qquad
T_S = \max_{\mathbf n}\sqrt{\int_0^{2\pi}\tau_a(\mathbf n,\psi)^2\,d\psi} = \sqrt\pi\,T_a,\qquad
a = \frac{\sqrt\pi\,(t_{-1} - f_{-1}/2)}{f_{-1}/3},\quad b = \sqrt\pi\,t_{-1},
```

with $T_a$ the generalised shear amplitude of [Papadopoulos (2001)](PAPADOPOULOS.md) and $P$ the
hydrostatic stress. For the similar-loading group, with $f = T_S/P_a$, the limit loading is
(Eq. 33)

```math
T_{S,\lim} = \frac{f\,(b - a P_m)}{a + f}.
```

The phase-difference coefficient is $H = T_S/C_A$ (Eq. 35), where $C_A$ is half the longest chord of
the shear path on the critical plane; $H = \sqrt\pi$ for proportional and $\sqrt{2\pi}$ for circular
paths. The limit shear amplitude is $\tau_{\lim} = T_{S,\lim}/H$ (Eq. 37) and the life is (Eq. 38)

```math
N_i = p\,\ln\frac{C_A}{C_A - \tau_{\lim}} + q\,\frac{\tau_{\lim}}{C_A - \tau_{\lim}} - \frac{r}{C_A},
\qquad C_A > \tau_{\lim}\ (\text{else } N_i = \infty),
```

with material constants $p$, $q$, $r$ fitted to one S–N curve (not printed in the paper).

## Repository implementation

- **Damage parameter:** $\mathrm{DP} = T_S/T_{S,\lim}$, which equals the
  [Papadopoulos (2001)](PAPADOPOULOS.md) Eq. (41) index exactly (same iso-life planes).
- **Native life:** Eq. (38) with $p$, $q$, $r$ fitted on the uniaxial R = -1 design tests above the
  Morel limit, by linear least squares on the **relative** life error (Eq. 38 is linear in
  $p, q, r$). Tests below the limit get $N_i = \infty$.
- Critical plane: sphere grid plus pattern search on $T_S$; $C_A$ is the exact semi-major axis of
  the shear ellipse on that plane.

**Repository choices**

- *Fitting objective* for $p, q, r$: relative life error, at least three design tests above the
  limit; the paper fits them to one S–N curve without stating an objective. Fewer tests: no native
  prediction, reported, not replaced by the master curve.
- *Misprint:* the worked example prints $b = 775$ MPa; Eq. (10) gives $\sqrt\pi\cdot426 = 755$ MPa,
  and only 755 reproduces the printed $T_{S,\lim} = 633$ MPa.
- An empirical DP master curve is also available for the DP comparison; it does not assess Eq. (38).

## Material constants and inputs

| Symbol | Python / workbook name | Unit | Source | Required |
| --- | --- | --- | --- | --- |
| $f_{-1}$ | `Sigm1` | MPa (amplitude) | workbook Summary, R = -1 | yes |
| $t_{-1}$ | `Taum1` | MPa (amplitude) | workbook Summary, R = -1 | yes |
| $p, q, r$ | life fit | cycles, cycles, cycles·MPa | fitted on the design tests | native life only |
| $\boldsymbol\sigma(t)$ | `S_mean`, `S_sin`, `S_cos` | MPa | Dataset sheet | yes |

## Calibration

1. **Original procedure.** $a$, $b$ from the two fatigue limits (Eq. 10); $p$, $q$, $r$ from one S–N
   curve.
2. **Repository.** $a$, $b$ as in Eq. (10). $p$, $q$, $r$ fitted on the uniaxial tension R = -1
   failures above the limit (≥ 3 required), recorded with the run. These tests are design rows
   (`Flag = 0`).

## Worked example

The paper's worked example (Morel 1998, pp. 252–253): 30NCD16 with $f_{-1} = 680$, $t_{-1} = 426$ MPa,
$\sigma_{11,a} = 600$ MPa and $\sigma_{12,a} = 335$ MPa with a 90° phase shift. Printed:
$T_S = 697$, $a = 0.67$, $T_{S,\lim} = 633$, $C_A = 282$, $H = 2.47$ MPa. Then a synthetic check that
the life fit recovers known $p, q, r$ (demonstration, not experimental data).

```python
import numpy as np

from multifat.models.integral_methods.morel import (
    fit_morel_life,
    morel_life,
    morel_limit,
    morel_parameters,
)

zero = np.zeros((3, 3))
S_sin, S_cos = np.zeros((3, 3)), np.zeros((3, 3))
S_sin[0, 0] = 600.0
S_cos[0, 1] = S_cos[1, 0] = -335.0  # 335 sin(wt - 90 deg)

a, b = morel_parameters(680.0, 426.0)
limit = morel_limit(zero, S_sin, S_cos, 680.0, 426.0)
assert abs(a - 0.67) < 0.005 and abs(b - 755.0) < 0.5  # b = 775 in print is a misprint
assert abs(limit.T_S - 697.0) < 0.5
assert abs(limit.T_Slim - 633.0) < 0.5
assert abs(limit.C_A - 282.0) < 0.011 * 282.0  # 285.1 computed, 282 printed (unresolved, 1 %)

# Life law: synthetic design tests generated from known constants are fitted back exactly
rng = np.random.default_rng(3)
tau_lim = rng.uniform(200.0, 260.0, 12)
C_A = tau_lim * rng.uniform(1.05, 1.8, 12)
p, q, r = 4.0e4, 2.5e4, 1.0e5
N = morel_life(C_A, tau_lim, p, q, r)
assert np.allclose(fit_morel_life(C_A, tau_lim, N), (p, q, r), rtol=1e-8)
assert morel_life(200.0, 250.0, p, q, r) == np.inf  # below the limit

print(f"a = {a:.4f}, b = {b:.1f} MPa")
print(f"T_S = {limit.T_S:.1f}, T_Slim = {limit.T_Slim:.1f}, C_A = {limit.C_A:.1f}, H = {limit.H:.3f}")
print(f"index T_S/T_Slim = {limit.T_S / limit.T_Slim:.4f}")
```

Output:

```text
a = 0.6725, b = 755.1 MPa
T_S = 697.5, T_Slim = 633.0, C_A = 285.1, H = 2.447
index T_S/T_Slim = 1.1019
```

The index above 1 means the paper's load is above the Morel limit, hence a finite life.

**On a supplied workbook:**

```bash
uv run multifat-pipeline --material Al7075_T6 --models MOREL --results-dir Results/current/guides
```

`MOREL_Al7075_T6.csv` carries the native life in `Nf_native` (and in `Nf_expected`, with
`Metric_mode = Nf_direct`); `Comparison/native_life_prediction_summary.csv` counts design rows,
assessed failures, run-outs and infinite predictions separately.

## Comparison capabilities and outputs

- **Life:** native, Eq. (38) with fitted $p, q, r$.
- **DP comparison:** empirical DP master curve on $T_S/T_{S,\lim}$; it does not assess Eq. (38).
- Infinite native lives (below the limit) are kept and counted, not discarded.
- See [comparison capabilities](../comparison-capabilities.md#audited-native-life-methods).

## Verification and limitations

- [`tests/methods/test_morel.py`](../../tests/methods/test_morel.py): Eq. (10) parameters and the
  $b$ misprint, the worked example ($T_S$, $T_{S,\lim}$; $C_A$ printed 282 vs 285.1 computed is a
  strict expected failure), the $H$ bounds, the identity with the Papadopoulos index, Eq. (38),
  recovery of $p, q, r$, the case model.
- The paper's life $N_i = 2\cdot10^5$ for the example cannot be checked ($p, q, r$ not printed).
- Limitations: $p, q, r$ fitted on uniaxial tension only; at least three design tests above the
  limit are needed.

## References

- F. Morel (1998), A fatigue life prediction method based on a mesoscopic approach in constant
  amplitude multiaxial loading, *Fatigue & Fracture of Engineering Materials & Structures* 21,
  241–256. <https://doi.org/10.1046/j.1460-2695.1998.00452.x>
- I. V. Papadopoulos (2001), Long life fatigue under multiaxial loading, *International Journal of
  Fatigue* 23(10), 839–849. <https://doi.org/10.1016/S0142-1123(01)00059-7>
