# Findley (`FIN`)

> **Registry name:** `FIN` (and `FIN_ext`) · **Catalogue entry:** [I_FIN](../../METHODS.md#i_fin) ·
> **Source:** Findley (1959), <https://doi.org/10.1115/1.4008327> · **Implementation:**
> [`cp_methods/fin.py`](../../src/multifat/models/cp_methods/fin.py)

## Overview

- **Type and family:** stress-based critical-plane criterion.
- **Idea:** fatigue damage on a material plane is driven by the alternating shear stress on that
  plane, increased linearly by the largest normal stress acting on it. The critical plane is the
  plane where this combination is largest.
- **Proposed for:** high-cycle fatigue of metals under combined bending (or axial load) and
  torsion, with mean stresses. It is one of the most widely used stress-based criteria for
  ductile metals and a common reference in multiaxial comparisons.
- **Status:** fully implemented for the declared repository scope; equation-level checks against
  the 1959 paper. No experimental dataset of the paper is reproduced (see
  [Verification and limitations](#verification-and-limitations)).

## Original formulation

Findley (1959, Eqs. 2 and 8–10, p. 302) writes the criterion on a plane of orientation $\theta$ as

```math
\tau_{\theta A} + k\,\sigma_{\theta M} = f ,
```

where $\tau_{\theta A}$ is the alternating (amplitude) shear stress on the plane,
$\sigma_{\theta M}$ the maximum normal stress on the same plane, $k$ a material constant
(dimensionless) and $f$ a material fatigue strength (MPa) at the life considered. The critical plane
is the one that maximises the left-hand side.

For in-phase bending and torsion with stress amplitudes $\sigma_A$, $\tau_A$ and maxima
$\sigma_M$, $\tau_M$, the maximum over planes has the closed form (Eq. 18)

```math
f = \sqrt{\left(\tfrac{\sigma_A}{2}\right)^2 + \tau_A^2 + k^2\left[\left(\tfrac{\sigma_M}{2}\right)^2 + \tau_M^2\right]} + k\,\frac{\sigma_M}{2}.
```

Fully reversed torsion (Eq. 19) and fully reversed bending (Eq. 24) give the two fatigue limits

```math
f = t_{-1}\sqrt{1+k^2}, \qquad f = \frac{f_{-1}}{2}\left(k + \sqrt{1+k^2}\right),
```

so the torsion-to-bending fatigue-limit ratio fixes $k$:

```math
\frac{t_{-1}}{f_{-1}} = \frac{k + \sqrt{1+k^2}}{2\sqrt{1+k^2}}
\quad\Longleftrightarrow\quad
k = \frac{2r - 1}{\sqrt{1 - (2r-1)^2}}, \qquad r = \frac{t_{-1}}{f_{-1}} \in \left(\tfrac12, 1\right).
```

$k \to 0$ when $r \to 1/2$ (Tresca-like behaviour) and $k$ grows without bound as $r \to 1$.
For zero-mean loading the critical plane lies at $\tan 2\theta = 1/k$ from the largest principal
stress (Eq. 13).

Findley's paper treats proportional (in-phase) loading. At finite life the same left-hand side is
commonly related to life through a torsional Basquin-type law; the 1959 paper does not prescribe a
specific one.

## Repository implementation

On every candidate plane (normal = local $z$ axis) the code evaluates

```math
\mathrm{DP} = \tau_a + k_\mathrm{FI}\,\sigma_{n,\max}, \qquad
\tau_a = \tfrac12\,\Delta\tau, \qquad
\sigma_{n,\max} = \sigma_{n,m} + \sigma_{n,a},
```

and takes the largest value over the planes. `DP` is in MPa. Since the selection metric is the DP
itself, `FIN` and `FIN_ext` are identical.

- $\Delta\tau$ is the shear range on the plane. For an out-of-phase history the shear vector
  describes an ellipse with semi-axes $a \ge b$ and the production rule (`rss`, also called MCE)
  uses $\tau_a = \sqrt{a^2 + b^2}$. For proportional loading $\tau_a = a$.
- $\sigma_{n,\max}$ keeps its sign: a compressive normal stress lowers the DP.
- The plane search starts from 522 grid planes plus analytical seed planes and refines the normal
  locally; on the closed forms above it reaches the continuous maximum to a relative $10^{-8}$.

**Repository choices**

- *Out-of-phase shear amplitude.* The 1959 paper gives no rule; the repository uses the RSS of the
  ellipse semi-axes (`np_shear_rule = "rss"`). `multifat-run --shear-amplitude-algorithm
  mcc_harmonic` evaluates the minimum-circumscribed-circle amplitude $\tau_a = a$ instead, with a
  $k_\mathrm{FI}$ calibrated under the same rule; see [shear-amplitude.md](../shear-amplitude.md).
- *Life.* Life is obtained from the shared master curve $\mathrm{DP} = A N_f^b$ fitted on the
  uniaxial $R=-1$ design tests ([README](README.md#from-damage-parameter-to-life-the-master-curve)),
  not from a Findley-specific life law.
- *Calibration of $k$.* By default $k_\mathrm{FI}$ minimises the life scatter of tension and torsion
  failures at finite life, not the fatigue-limit ratio above (see [Calibration](#calibration)).
- *Mean shear stress* does not enter the DP, as in the original criterion.

## Material constants and inputs

| Symbol | Python / workbook name | Unit | Source | Required |
| --- | --- | --- | --- | --- |
| $k$ | `k_FI` / Summary column `k FI` | – | workbook, `--constants` record, or pipeline calibration (bounds $0 \le k \le 3$) | yes, $k \ge 0$ |
| $\boldsymbol\sigma(t)$ | `S_mean`, `S_sin`, `S_cos` | MPa | Dataset sheet | yes |

Strains are not used: FIN runs on workbooks without `E` and `nu`.

## Calibration

1. **Original procedure.** $k$ follows from the ratio of the fully reversed torsion and bending
   fatigue limits (closed form above), or from fitting fatigue strengths in two loading modes at
   the same life.
2. **Repository default.** When the workbook has no `k FI`, `multifat-pipeline` selects the uniaxial
   tension and torsion failures at $R = -1$ and searches $k_\mathrm{FI} \in [0, 3]$ for the value
   that minimises the standard deviation of $\ln N_f$ about one fitted master curve
   (`multifat.cli.calibrate.calibrate_material_params`). The critical plane is re-selected for each
   trial $k$. This makes tension and torsion lives collapse at finite life; it reduces to the
   original procedure only if the two S–N curves are parallel and the fatigue-limit ratio holds at
   every life.
3. **Fatigue-limit datasets** (run-outs only): $k_\mathrm{FI}$ is chosen so that the R = -1 tension
   and torsion limits give the same DP, which is the original procedure.
4. **Supplied constants.** `--constants FILE` uses a record from `Calibrations/` or a previous
   `<MATERIAL>_calibration.json`. Records calibrated with the MCC amplitude are rejected by the
   production (MCE) assessment.

The value, the objective (`scatter_STD`), the flat range of the objective (`plateau`) and the IDs
of the tension and torsion tests used (`selection`) are written to `<MATERIAL>_calibration.json`.
The tension and torsion tests used for $k_\mathrm{FI}$ are reported as design rows (`Flag = 0`) in
the result CSV, so they do not enter the assessment statistics.

## Worked example

Synthetic demonstration material (not experimental data): $f_{-1} = 300$ MPa,
$t_{-1} = 200$ MPa. The closed form gives $k = (1/3)/\sqrt{8/9} = 0.3536$ and
$f = t_{-1}\sqrt{1+k^2} = 212.13$ MPa. With this $k$, both fatigue limits must return the same
Findley DP, and a bending test with a tensile mean must follow Eq. (18).

```python
import numpy as np

from multifat.models.registry import get_models
from multifat.planes.sampling import build_R_list

f_m1, t_m1 = 300.0, 200.0  # MPa, synthetic R = -1 fatigue limits
r = t_m1 / f_m1
k_FI = (2 * r - 1) / np.sqrt(1 - (2 * r - 1) ** 2)  # closed form from the limit ratio
f_findley = t_m1 * np.sqrt(1 + k_FI**2)  # Findley's f, Eq. (19)

fin = get_models(["FIN"])[0]
planes = build_R_list(n1=20, n2=40)  # production plane grid
zero = np.zeros((3, 3))


def findley_dp(S_mean, S_sin):
    """FIN damage parameter of S(t) = S_mean + S_sin sin(wt)."""
    result = fin.evaluate_case(
        S0=S_mean + S_sin,
        S1=S_mean - S_sin,
        E0=zero,
        E1=zero,
        params={"k_FI": k_FI},
        R_list=planes,
        harmonics={"S_mean": S_mean, "S_sin": S_sin, "S_cos": zero},
    )
    assert result.values[""] == result.values["_ext"]  # metric = DP for Findley
    return result.values[""]


torsion = np.zeros((3, 3))
torsion[0, 1] = torsion[1, 0] = t_m1
dp_torsion = findley_dp(zero, torsion)
dp_tension = findley_dp(zero, np.diag([f_m1, 0.0, 0.0]))
assert abs(dp_torsion - f_findley) < 1e-6 * f_findley
assert abs(dp_tension - f_findley) < 1e-6 * f_findley

# Bending with a tensile mean: sigma_a = 200, sigma_m = 100 (sigma_M = 300 MPa), Eq. (18)
sigma_A, sigma_M = 200.0, 300.0
eq18 = np.sqrt((sigma_A / 2) ** 2 + k_FI**2 * (sigma_M / 2) ** 2) + k_FI * sigma_M / 2
dp_mean = findley_dp(np.diag([sigma_M - sigma_A, 0, 0]), np.diag([sigma_A, 0, 0]))
assert abs(dp_mean - eq18) < 1e-6 * eq18

print(f"k_FI = {k_FI:.4f}, f = {f_findley:.2f} MPa")
print(f"DP at the limits: tension {dp_tension:.2f}, torsion {dp_torsion:.2f} MPa")
print(f"DP with mean stress: {dp_mean:.2f} MPa (fatigue index {dp_mean / f_findley:.3f})")
```

Output:

```text
k_FI = 0.3536, f = 212.13 MPa
DP at the limits: tension 212.13, torsion 212.13 MPa
DP with mean stress: 166.23 MPa (fatigue index 0.784)
```

The ratio $\mathrm{DP}/f$ is a fatigue index: below 1 the load is below the fatigue limit in
Findley's sense. The 100 MPa tensile mean raises the DP of a 200 MPa bending amplitude from
$100\,(k + \sqrt{1+k^2}) = 141.4$ MPa to 166.2 MPa.

**On a supplied workbook.** Calibrate $k_\mathrm{FI}$, run FIN and compare:

```bash
uv run multifat-pipeline --material Al7075_T6 --models FIN --all-variants --results-dir Results/current/guides
```

Look at `Results/current/guides/Al7075_T6_calibration.json` (`params.k_FI`, `scatter_STD`, `selection`),
`Results/current/guides/FIN_Al7075_T6.csv` (`CP_value` is the Findley DP in MPa, `Nf_expected` the
master-curve life) and `Results/current/guides/Comparison/`. At commit `5cd5124` the calibrated value is
$k_\mathrm{FI} \approx 0.392$ on this workbook; it changes if the data change.

## Comparison capabilities and outputs

- **Life:** master curve (`Metric_mode = Nf`; `Nf_expected` from the inverted fit).
- **DP comparison:** supported, against `DP_fit` $= A N_{f,\exp}^b$ of the master curve.
- **`_ext`:** identical to `FIN`.
- **Fatigue-limit datasets:** assessed through the fatigue index error.

## Verification and limitations

- [`tests/methods/test_findley.py`](../../tests/methods/test_findley.py): the plane search reproduces
  the closed forms Eqs. (18), (19), (24) and the critical-plane angle of Eq. (13) for
  $k = 0.1, 0.2, 0.3, 1.1$, and the limit ratios of p. 303. The plane angles printed on p. 305
  differ from Eq. (13) by up to 0.65°; they appear read from a figure (paper inconsistency).
- [`tests/test_method_audit.py`](../../tests/test_method_audit.py),
  [`tests/test_findley_harmonic.py`](../../tests/test_findley_harmonic.py),
  [`tests/test_findley_calibration.py`](../../tests/test_findley_calibration.py) and
  [`tests/test_findley_assessment.py`](../../tests/test_findley_assessment.py): analytical plane
  values, MCC/MCE amplitudes, calibration and the explicit-amplitude assessment path.
- Not verified: reproduction of the experimental data of the 1959 paper or of an independent
  multiaxial dataset. The catalogue therefore records `basic_numerical_tests`.
- Validity: constant-amplitude, single-harmonic loading. For out-of-phase loading the result
  depends on the shear-amplitude definition (RSS vs MCC); the two coincide for proportional loading.

## References

- W. N. Findley (1959), A theory for the effect of mean stress on fatigue of metals under combined
  torsion and axial load or bending, *Journal of Engineering for Industry*.
  <https://doi.org/10.1115/1.4008327>
- D. F. Socie, G. B. Marquis (2000), *Multiaxial Fatigue*, SAE International (textbook treatment of
  Findley's criterion and its life form).
