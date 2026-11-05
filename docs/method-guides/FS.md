# Fatemi–Socie (`FS`)

> **Registry name:** `FS` (and `FS_ext`) · **Catalogue entry:** [I_FS](../../METHODS.md#i_fs) ·
> **Source:** Fatemi & Socie (1988), <https://doi.org/10.1111/j.1460-2695.1988.tb01169.x> ·
> **Implementation:** [`cp_methods/fs.py`](../../src/multifat/models/cp_methods/fs.py)

## Overview

- **Type and family:** strain-based critical-plane criterion (shear-strain driven, with a
  normal-stress correction).
- **Idea:** cracks nucleate and grow on planes of maximum shear strain; a tensile normal stress on
  those planes opens the crack faces, reduces friction between them and accelerates growth.
- **Proposed for:** low- and high-cycle fatigue of ductile metals that fail by shear cracking,
  including out-of-phase loading with additional (non-proportional) hardening.
- **Status:** fully implemented for the declared repository scope; equation-level checks against
  the 1988 paper. No experimental dataset of the paper is reproduced.

## Original formulation

Fatemi & Socie (1988, Eq. 8) state that, on the plane of maximum shear strain amplitude,

```math
\frac{\Delta\gamma_{\max}}{2}\left(1 + n\,\frac{\sigma_n^{\max}}{\sigma_y}\right) = \text{constant},
```

where $\Delta\gamma_{\max}/2$ is the maximum **engineering** shear strain amplitude,
$\sigma_n^{\max}$ the largest normal stress on that plane over the cycle, $\sigma_y$ the (cyclic)
yield strength and $n$ a dimensionless material constant. Combining it with the uniaxial
strain–life curve gives the life relation (Eq. 9)

```math
\frac{\Delta\gamma_{\max}}{2}\left(1 + n\frac{\sigma_n^{\max}}{\sigma_y}\right)
= (1+\nu_e)\frac{\sigma_f'}{E}(2N_f)^b + \frac{n}{2}(1+\nu_e)\frac{\sigma_f'^2}{E\,\sigma_y}(2N_f)^{2b}
+ (1+\nu_p)\,\varepsilon_f'(2N_f)^c + \frac{n}{2}(1+\nu_p)\frac{\varepsilon_f'\sigma_f'}{\sigma_y}(2N_f)^{b+c},
```

with $\nu_e$, $\nu_p$ the elastic and plastic Poisson ratios. With $n = 0.6$, $\nu_e = 0.29$,
$\nu_p = 0.5$ the coefficients become those of Eq. (10). A torsional form
$(\tau_f'/G)(2N_f)^{b_0} + \gamma_f'(2N_f)^{c_0}$ is also widely used for the right-hand side.

## Repository implementation

On every candidate plane (normal = local $z$ axis):

```math
\mathrm{DP} = \gamma_a\left(1 + k_\mathrm{FS}\,\frac{\sigma_{n,\max}}{S_y}\right), \qquad
\gamma_a = \left\|\Delta\boldsymbol\varepsilon_{\text{shear}}\right\|, \qquad
\sigma_{n,\max} = \max(\sigma_{n,m} + \sigma_{n,a},\,0).
```

$\Delta\boldsymbol\varepsilon_{\text{shear}} = (\Delta\varepsilon_{xz}, \Delta\varepsilon_{yz})$ is
the range of the **tensorial** shear strain on the plane; since $\gamma = 2\varepsilon$, its norm
is the engineering shear strain **amplitude**, so no factor 2 is applied. DP is dimensionless.

- `FS`: DP on the plane of largest $\gamma_a$ (Fatemi–Socie's plane rule); among tied planes
  (e.g. the two 45° planes in tension) the one with the larger DP.
- `FS_ext`: largest DP over all planes (repository variant). Closed-form solutions for this
  maximum under proportional elastic loading are given by Chiocca et al. (2024); the repository uses the
  numerical plane search.
- Out-of-phase loading: $\gamma_a$ is half the longest chord of the shear-strain ellipse
  (`np_shear_rule = "longest_chord"`), i.e. the maximum shear range on the plane over the cycle, as
  the source defines it.

**Repository choices**

- *Compression clipped.* $\sigma_{n,\max} < 0$ is set to 0, so compression never reduces the DP.
- *Monotonic yield strength.* The workbook `Sy` replaces the cyclic yield strength.
- *Elastic strains.* Strains are computed from the stresses with isotropic linear elasticity (`E`,
  `nu`); cyclic plasticity and non-proportional hardening are not modelled. In the high-cycle
  regime of the supplied datasets this makes $\gamma_a = \tau_a/G$.
- *Life.* The shared master curve $\mathrm{DP} = A N_f^b$ replaces Eq. (9)
  ([README](README.md#from-damage-parameter-to-life-the-master-curve)).
- *Calibration of $n$.* $k_\mathrm{FS}$ ($= n$) minimises the life scatter of tension and torsion
  failures (see [Calibration](#calibration)).

## Material constants and inputs

| Symbol | Python / workbook name | Unit | Source | Required |
| --- | --- | --- | --- | --- |
| $n$ | `k_FS` / Summary column `k FS` | – | workbook, `--constants`, or pipeline calibration ($0 \le n \le 3$) | yes, $n \ge 0$ |
| $\sigma_y$ | `Sy` / Summary yield strength | MPa | workbook | yes, $> 0$ |
| $E$, $\nu$ | `E`, `nu` / Summary | MPa, – | workbook | yes (strains) |
| $\boldsymbol\sigma(t)$ | `S_mean`, `S_sin`, `S_cos` | MPa | Dataset sheet | yes |

## Calibration

1. **Original procedure.** $n$ is chosen so that the uniaxial and torsional fatigue data collapse
   when plotted against the FS parameter, i.e. by equating Eq. (9) with the torsional strain–life
   curve at the lives of interest. The repository assumes $n$ independent of life.
2. **Repository default.** When the workbook has no `k FS`, `multifat-pipeline` searches
   $k_\mathrm{FS} \in [0, 3]$ for the value that minimises the standard deviation of $\ln N_f$ of
   the R = -1 tension and torsion failures about one master curve. Since the FS plane is chosen by
   $\gamma_a$, it does not depend on $k_\mathrm{FS}$. A single constant is fitted for all lives.
3. **Fatigue-limit datasets** (run-outs only): $k_\mathrm{FS}$ equalises the DP of the R = -1
   tension and torsion limits. For elastic strains this has the closed form
   $k_\mathrm{FS} = 2\,(2t_{-1}/f_{-1} - 1)\,S_y/f_{-1}$ (see the worked example).

The value and the tests used are written to `<MATERIAL>_calibration.json`. The tension and torsion
tests used for $k_\mathrm{FS}$ are reported as design rows (`Flag = 0`).

## Worked example

Synthetic demonstration material (not experimental data): $E = 200$ GPa, $\nu = 0.3$,
$S_y = 400$ MPa, $f_{-1} = 300$ MPa, $t_{-1} = 200$ MPa. In fully reversed tension the maximum shear
planes lie at 45°, with $\gamma_a = (1+\nu)\sigma_a/E$ and $\sigma_{n,\max} = \sigma_a/2$; in
torsion $\gamma_a = \tau_a/G = 2(1+\nu)\tau_a/E$ and $\sigma_{n,\max} = 0$. Equal DP at the two
limits gives $k_\mathrm{FS} = 2\,(2t_{-1}/f_{-1} - 1)\,S_y/f_{-1} = 0.8889$.

```python
import numpy as np

from multifat.models.registry import get_models
from multifat.planes.sampling import build_R_list

E, nu, Sy = 200000.0, 0.3, 400.0  # MPa, -, MPa (synthetic)
f_m1, t_m1 = 300.0, 200.0  # MPa, synthetic R = -1 fatigue limits
k_FS = 2 * (2 * t_m1 / f_m1 - 1) * Sy / f_m1  # equal DP at both limits (elastic strains)

fs = get_models(["FS"])[0]
planes = build_R_list(n1=20, n2=40)
zero = np.zeros((3, 3))


def hooke(S):
    """Isotropic linear-elastic strain tensor (tensorial shear components)."""
    return ((1 + nu) * S - nu * np.trace(S) * np.eye(3)) / E


def fs_dp(S_mean, S_sin):
    """FS and FS_ext of S(t) = S_mean + S_sin sin(wt), elastic strains."""
    result = fs.evaluate_case(
        S0=S_mean + S_sin,
        S1=S_mean - S_sin,
        E0=hooke(S_mean + S_sin),
        E1=hooke(S_mean - S_sin),
        params={"k_FS": k_FS, "Sy": Sy},
        R_list=planes,
        harmonics={
            "S_mean": S_mean,
            "S_sin": S_sin,
            "S_cos": zero,
            "E_sin": hooke(S_sin),
            "E_cos": zero,
        },
    )
    return result.values[""], result.values["_ext"]


torsion = np.zeros((3, 3))
torsion[0, 1] = torsion[1, 0] = t_m1
dp_torsion, _ = fs_dp(zero, torsion)
dp_tension, ext_tension = fs_dp(zero, np.diag([f_m1, 0.0, 0.0]))

expected = 2 * (1 + nu) * t_m1 / E  # gamma_a in torsion
assert abs(dp_torsion - expected) < 1e-8 * expected
assert abs(dp_tension - expected) < 1e-8 * expected
# FS_ext: max over the plane angle theta of (1+nu) s/E sin(2 theta) (1 + k s cos^2(theta) / Sy)
theta = np.linspace(0.0, np.pi / 2, 200001)
sweep = (1 + nu) * f_m1 / E * np.sin(2 * theta) * (1 + k_FS * f_m1 * np.cos(theta) ** 2 / Sy)
assert abs(ext_tension - sweep.max()) < 1e-8 * sweep.max()
theta_ext = np.degrees(theta[sweep.argmax()])

# Tension with a tensile mean: sigma_m = 100, sigma_a = 250 MPa
s_m, s_a = 100.0, 250.0
dp_mean, _ = fs_dp(np.diag([s_m, 0, 0]), np.diag([s_a, 0, 0]))
closed_form = (1 + nu) * s_a / E * (1 + k_FS * (s_m + s_a) / 2 / Sy)
assert abs(dp_mean - closed_form) < 1e-8 * closed_form

print(f"k_FS = {k_FS:.4f}")
print(f"FS at the limits: tension {dp_tension:.6f}, torsion {dp_torsion:.6f}")
print(f"FS_ext in tension: {ext_tension:.6f} (plane at {theta_ext:.1f} deg from the axis)")
print(f"FS with mean stress: {dp_mean:.6f}")
```

Output:

```text
k_FS = 0.8889
FS at the limits: tension 0.002600, torsion 0.002600
FS_ext in tension: 0.002676 (plane at 38.5 deg from the axis)
FS with mean stress: 0.002257
```

`FS` evaluates the DP on the 45° planes of largest $\gamma_a$. `FS_ext` finds a larger DP on a
plane rotated towards the load axis, where the shear strain is slightly lower but the normal
stress is higher: in tension
$\mathrm{DP}(\theta) = (1+\nu)\frac{\sigma_a}{E}\sin 2\theta\,\left(1 + k_\mathrm{FS}\,\sigma_a\cos^2\theta/S_y\right)$,
whose maximum moves away from 45° as $k_\mathrm{FS}\sigma_a/S_y$ grows. Both variants use the
same $k_\mathrm{FS}$ (calibrated on the `FS` plane rule), so they give different DP values and
master curves.

**On a supplied workbook:**

```bash
uv run multifat-pipeline --material Al7075_T6 --models FS --all-variants --results-dir Results/current/guides
```

`Results/current/guides/Al7075_T6_calibration.json` holds `params.k_FS`; `FS_Al7075_T6.csv` and
`FS_ext_Al7075_T6.csv` hold the DP (`CP_value`, dimensionless) and the master-curve life. FS is
skipped on a workbook without `Sy`, `E` or `nu`, with the reason in `<MATERIAL>_run_report.tsv`.

## Comparison capabilities and outputs

- **Life:** master curve (`Nf_expected`), not Eq. (9).
- **DP comparison:** supported, against the master-curve `DP_fit`.
- **`_ext`:** available; maximum DP over planes, a repository variant.

## Verification and limitations

- [`tests/methods/test_fatemi_socie.py`](../../tests/methods/test_fatemi_socie.py): Eq. (10)
  coefficients from Eq. (9); uniaxial tension with mean stress (45° plane,
  $\gamma_a = (1+\nu)\varepsilon_a$, $\sigma_n^{\max} = \sigma_{\max}/2$); engineering shear in
  pure torsion.
- [`tests/test_np_shear_rule.py`](../../tests/test_np_shear_rule.py): longest-chord shear range for
  out-of-phase loading.
- Not verified: reproduction of the experimental data of Fatemi & Socie (1988).
- Limitations: elastic strains only (no plasticity, no non-proportional hardening, which is a key
  motivation of the original model); monotonic instead of cyclic yield strength; constant
  $k_\mathrm{FS}$ over life.

## References

- A. Fatemi, D. F. Socie (1988), A critical plane approach to multiaxial fatigue damage including
  out-of-phase loading, *Fatigue & Fracture of Engineering Materials & Structures* 11(3), 149–165.
  <https://doi.org/10.1111/j.1460-2695.1988.tb01169.x>
- A. Chiocca et al. (2024), Closed-form solution for the Fatemi–Socie extended
  critical plane parameter in case of linear elasticity and proportional loading, *Fatigue &
  Fracture of Engineering Materials & Structures*. <https://doi.org/10.1111/ffe.14153>
