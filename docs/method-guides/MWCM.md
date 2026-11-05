# Modified Wöhler Curve Method (`MWCM`)

> **Registry name:** `MWCM` · **Catalogue entry:** [N04](../../METHODS.md#n04) ·
> **Source:** Susmel & Lazzarin (2002), <https://doi.org/10.1046/j.1460-2695.2002.00462.x> ·
> **Implementation:** [`cp_methods/mwcm.py`](../../src/multifat/models/cp_methods/mwcm.py) ·
> **Scientific dossier:** [N04-susmel](../scientific-reviews/N04-susmel/README.md)

## Overview

- **Type and family:** stress-based critical-plane criterion.
- **Idea:** on the plane of maximum shear stress amplitude, the ratio between the maximum normal
  stress and the shear amplitude, $\rho$, measures how much the normal stress opens the cracks.
  The admissible shear amplitude decreases linearly with $\rho$, between the torsion limit
  ($\rho = 0$) and the tension limit ($\rho = 1$).
- **Proposed for:** high-cycle fatigue of plain and notched components under proportional and
  non-proportional loading (the repository covers the plain, high-cycle form).
- **Status:** fully implemented (high-cycle form); reference examples reproduced; scientific dossier
  available.

## Original formulation

Susmel & Lazzarin (2002, Eqs. 5–13). On the plane where the shear stress amplitude $\tau_a$ is
largest,

```math
\rho = \frac{\sigma_{n,\max}}{\tau_a} \quad\text{(Eq. 5)}, \qquad
\tau_{A,\mathrm{Ref}}(\rho) = \tau_A + \rho\left(\frac{\sigma_A}{2} - \tau_A\right) \quad\text{(Eq. 8)},
\qquad \tau_a \le \tau_{A,\mathrm{Ref}}(\rho) \quad\text{(Eqs. 9–11)},
```

with $\sigma_A = f_{-1}$ and $\tau_A = t_{-1}$ the fully reversed fatigue limits (reference values
at the same number of cycles), $\tau_a$ the radius of the smallest circle enclosing the shear path
on the plane (p. 66) and $\sigma_{n,\max} = \sigma_{n,m} + \sigma_{n,a}$. The error index of Eq. (13)
is $E = \tau_a/\tau_{A,\mathrm{Ref}}(\rho) - 1$. A finite-life form (Eq. 7) also interpolates the
inverse slope $k_\tau(\rho)$ of the modified Wöhler curves.

## Repository implementation

On every candidate plane:

```math
\mathrm{DP} = \frac{\tau_a}{\tau_{A,\mathrm{Ref}}(\rho)} = \frac{\tau_a^2}{t_{-1}\,\tau_a - (t_{-1} - f_{-1}/2)\,\sigma_{n,\max}}
```

(dimensionless, $E + 1$ of Eq. 13), evaluated on the plane of largest $\tau_a$ with the
minimum-circumscribed-circle amplitude (`np_shear_rule = "longest_chord"`). $\sigma_{n,\max}$ keeps
its sign, so a compressive mean gives $\rho < 0$. DP is $+\infty$ when
$\tau_{A,\mathrm{Ref}}(\rho) \le 0$, i.e. for $\rho \ge t_{-1}/(t_{-1} - f_{-1}/2)$ (the paper
imposes no cut-off for $\rho > 1$), and 0 when $\tau_a = 0$ with no tension.

**Repository choices**

- *No `_ext` variant* (`ext_variant = False`): $\rho$ diverges where $\tau_a \to 0$, so a maximum of
  DP over all planes is not meaningful.
- *Tie rule.* Planes with equal maximum $\tau_a$ are resolved towards the larger DP; the paper
  gives no rule. On the Papadopoulos et al. (1997) tests this choice changes the outcome of several
  rows (see Verification).
- *High-cycle form only.* The finite-life branch (Eq. 7) with $k_\tau(\rho)$ is not implemented;
  life comes from the shared master curve on the DP
  ([README](README.md#from-damage-parameter-to-life-the-master-curve)).

## Material constants and inputs

| Symbol | Python / workbook name | Unit | Source | Required |
| --- | --- | --- | --- | --- |
| $\sigma_A = f_{-1}$ | `Sigm1` | MPa (amplitude) | workbook Summary, R = -1 | yes, $> 0$ |
| $\tau_A = t_{-1}$ | `Taum1` | MPa (amplitude) | workbook Summary, R = -1 | yes, $> 0$ |
| $\boldsymbol\sigma(t)$ | `S_mean`, `S_sin`, `S_cos` | MPa | Dataset sheet | yes |

## Calibration

1. **Original procedure.** Two fully reversed fatigue curves (tension and torsion) define
   $\tau_{A,\mathrm{Ref}}(\rho)$ and, at finite life, $k_\tau(\rho)$.
2. **Repository.** The endurance form with the workbook `Sigm1`, `Taum1`; DP = 1 at both limits.
   Nothing is fitted except the master-curve constants on the uniaxial R = -1 design tests.
   The [N04 dossier](../scientific-reviews/N04-susmel/README.md) specifies the inputs a native
   finite-life implementation would require.

## Worked example

Synthetic demonstration material: $f_{-1} = 300$, $t_{-1} = 200$ MPa. Torsion has $\rho = 0$,
reversed tension $\rho = 1$, and both give DP = 1. A tensile mean raises $\rho$ and lowers the
reference shear amplitude.

```python
import numpy as np

from multifat.models.registry import get_models
from multifat.planes.sampling import build_R_list

f_m1, t_m1 = 300.0, 200.0  # MPa, synthetic
mwcm = get_models(["MWCM"])[0]
planes = build_R_list(n1=20, n2=40)
zero = np.zeros((3, 3))


def mwcm_dp(S_mean, S_sin):
    """MWCM index tau_a / tau_A,Ref(rho) of S(t) = S_mean + S_sin sin(wt)."""
    result = mwcm.evaluate_case(
        S0=S_mean + S_sin,
        S1=S_mean - S_sin,
        E0=zero,
        E1=zero,
        params={"Sigm1": f_m1, "Taum1": t_m1},
        R_list=planes,
        harmonics={"S_mean": S_mean, "S_sin": S_sin, "S_cos": zero},
    )
    assert set(result.values) == {""}  # no _ext variant
    return result.values[""]


torsion = np.zeros((3, 3))
torsion[0, 1] = torsion[1, 0] = t_m1
assert abs(mwcm_dp(zero, torsion) - 1) < 1e-9
assert abs(mwcm_dp(zero, np.diag([f_m1, 0, 0])) - 1) < 1e-9

# Tension s_a = 200 with mean s_m = 100: tau_a = s_a/2, sigma_n,max = (s_m + s_a)/2
s_a, s_m = 200.0, 100.0
rho = (s_m + s_a) / s_a
tau_ref = t_m1 + rho * (f_m1 / 2 - t_m1)
with_mean = mwcm_dp(np.diag([s_m, 0, 0]), np.diag([s_a, 0, 0]))
assert abs(with_mean - (s_a / 2) / tau_ref) < 1e-9

print(f"rho = {rho:.2f}, tau_A,Ref = {tau_ref:.1f} MPa, index = {with_mean:.4f}")
print(f"cut-off: DP is infinite for rho >= {t_m1 / (t_m1 - f_m1 / 2):.1f}")
```

Output:

```text
rho = 1.50, tau_A,Ref = 125.0 MPa, index = 0.8000
cut-off: DP is infinite for rho >= 4.0
```

**On a supplied workbook:**

```bash
uv run multifat-pipeline --material Al7075_T6 --models MWCM --results-dir Results/current/guides
```

## Comparison capabilities and outputs

- **Life:** master curve on the index (`Nf_expected`), not the MWCM finite-life curves.
- **DP comparison:** supported, against the master-curve `DP_fit`; infinite DP values have
  undefined errors and are not counted in statistics.
- **Fatigue-limit datasets:** $\mathrm{DP} - 1$ is the error index of Eq. (13).

## Verification and limitations

- [`tests/methods/test_mwcm.py`](../../tests/methods/test_mwcm.py): Eq. (8) reference points,
  calibration at both limits, Eq. (13), mean stress and cut-off, tie rule.
- On the 43 Papadopoulos et al. (1997) tests the result depends on the unspecified tie rule: the
  larger-damage rule gives 12/16 in-phase rows within ±20 % and 24/27 out-of-phase rows within
  ±30 % (the paper's stated bands), the smaller-damage rule 14/16 and 20/27. Unresolved; not used
  as a test oracle.
- [`docs/scientific-reviews/N04-susmel`](../scientific-reviews/N04-susmel/README.md): independent
  analytical benchmarks B1–B8 and the specification for a restricted native implementation.
- Limitations: high-cycle form only; no `_ext` variant; sensitivity to plane ties for degenerate
  out-of-phase paths.

## References

- L. Susmel, P. Lazzarin (2002), A bi-parametric Wöhler curve for high cycle multiaxial fatigue
  assessment, *Fatigue & Fracture of Engineering Materials & Structures* 25(1), 63–78.
  <https://doi.org/10.1046/j.1460-2695.2002.00462.x>
