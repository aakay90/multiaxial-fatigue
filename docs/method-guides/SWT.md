# Smith–Watson–Topper (`SWT`)

> **Registry name:** `SWT` (and `SWT_ext`) · **Catalogue entry:** [I_SWT](../../METHODS.md#i_swt) ·
> **Source:** Smith, Watson & Topper (1970), *Journal of Materials* 5(4), 767–778 (no DOI) ·
> **Implementation:** [`cp_methods/swt.py`](../../src/multifat/models/cp_methods/swt.py)

## Overview

- **Type and family:** strain–stress (energy-like) parameter, used here in its critical-plane
  extension.
- **Idea:** damage is driven by the normal strain amplitude on a plane, multiplied by the largest
  tensile stress that opens cracks on it. The product accounts for mean stress without a separate
  mean-stress correction.
- **Proposed for:** uniaxial mean-stress effects (1970); in its critical-plane form, materials that
  fail predominantly by tensile (mode I) cracking.
- **Status:** fully implemented for the declared repository scope; checked against the 1970
  definition. No experimental dataset of the paper is reproduced.

## Original formulation

Smith, Watson & Topper (1970, p. 769) define the parameter as $\sigma_{\max}\,\varepsilon_a$,
"where $\sigma_{\max}$ is the maximum tensile stress and $\varepsilon_a$ is the strain amplitude",
and use it as the equivalent stress

```math
\sqrt{\sigma_{\max}\,\varepsilon_a\,E} = \text{constant at a given life.}
```

A fully compressive cycle ($\sigma_{\max} \le 0$) causes no damage. Combined with the Basquin and
Manson–Coffin curves it gives the common life relation

```math
\sigma_{\max}\,\varepsilon_a = \frac{\sigma_f'^2}{E}(2N_f)^{2b} + \sigma_f'\,\varepsilon_f'\,(2N_f)^{b+c}.
```

The multiaxial (critical-plane) extension evaluates $\sigma_{n,\max}\,\varepsilon_{n,a}$ on the
plane of maximum normal strain amplitude (e.g. Socie 1987; Socie & Marquis 2000). This extension
is not part of the 1970 paper.

## Repository implementation

On every candidate plane (normal = local $z$ axis):

```math
\mathrm{DP} = \sigma_{n,\max}\,\varepsilon_{n,a}, \qquad
\varepsilon_{n,a} = \tfrac12\,|\Delta\varepsilon_{zz}|, \qquad
\sigma_{n,\max} = \max(\sigma_{n,m} + \sigma_{n,a},\,0).
```

DP is in MPa (stress × strain).

- `SWT`: DP on the plane of largest normal strain range (critical-plane extension); ties resolved
  towards the larger DP.
- `SWT_ext`: largest DP over all planes (repository variant).

**Repository choices**

- *Product, not square root.* DP is $\sigma_{\max}\varepsilon_a$, not
  $\sqrt{\sigma_{\max}\varepsilon_a E}$. The transform is monotone: master-curve lives are
  unchanged, but the fitted exponent and the log-damage errors are doubled.
- *Elastic strains.* Strains follow from the stresses by isotropic linear elasticity (`E`, `nu`).
- *Life.* The shared master curve $\mathrm{DP} = A N_f^b$ replaces the strain–life relation above
  ([README](README.md#from-damage-parameter-to-life-the-master-curve)).
- No material constant is calibrated.

## Material constants and inputs

| Symbol | Python / workbook name | Unit | Source | Required |
| --- | --- | --- | --- | --- |
| $E$, $\nu$ | `E`, `nu` / Summary | MPa, – | workbook | yes (strains) |
| $\boldsymbol\sigma(t)$ | `S_mean`, `S_sin`, `S_cos` | MPa | Dataset sheet | yes |

## Calibration

SWT has no criterion-specific constant. The only fitted quantities are the master-curve constants
$A$, $b$, obtained from the uniaxial $R = -1$ design tests. In the original formulation they would
be $\sigma_f'$, $b$, $\varepsilon_f'$, $c$ of the uniaxial strain–life curve.

A consequence worth knowing: for fully reversed tension $\mathrm{DP} = \sigma_a^2/E$, and for fully
reversed torsion the plane at 45° gives $\varepsilon_{n,a} = (1+\nu)\tau_a/E$ and
$\sigma_{n,\max} = \tau_a$, so $\mathrm{DP} = (1+\nu)\tau_a^2/E$. Equal damage at the two fatigue
limits therefore requires $t_{-1}/f_{-1} = 1/\sqrt{1+\nu} \approx 0.88$ (for $\nu = 0.3$). Materials
with a lower ratio, such as ductile metals close to the von Mises value $1/\sqrt3 \approx 0.58$,
are expected to show torsion tests off the tension master curve; this is a property of the criterion, not of the implementation.

## Worked example

Synthetic demonstration (not experimental data): $E = 200$ GPa, $\nu = 0.3$.

```python
import numpy as np

from multifat.models.registry import get_models
from multifat.planes.sampling import build_R_list

E, nu = 200000.0, 0.3  # MPa, - (synthetic)
swt = get_models(["SWT"])[0]
planes = build_R_list(n1=20, n2=40)
zero = np.zeros((3, 3))


def hooke(S):
    """Isotropic linear-elastic strain tensor."""
    return ((1 + nu) * S - nu * np.trace(S) * np.eye(3)) / E


def swt_dp(S_mean, S_sin):
    """SWT damage parameter of S(t) = S_mean + S_sin sin(wt), elastic strains."""
    result = swt.evaluate_case(
        S0=S_mean + S_sin,
        S1=S_mean - S_sin,
        E0=hooke(S_mean + S_sin),
        E1=hooke(S_mean - S_sin),
        params={},
        R_list=planes,
        harmonics={
            "S_mean": S_mean,
            "S_sin": S_sin,
            "S_cos": zero,
            "E_sin": hooke(S_sin),
            "E_cos": zero,
        },
    )
    return result.values[""]


s_a, tau_a = 300.0, 200.0  # MPa
torsion = np.zeros((3, 3))
torsion[0, 1] = torsion[1, 0] = tau_a

dp_tension = swt_dp(zero, np.diag([s_a, 0.0, 0.0]))
dp_torsion = swt_dp(zero, torsion)
dp_mean = swt_dp(np.diag([150.0, 0, 0]), np.diag([s_a, 0, 0]))  # R = -1/3
dp_compressive = swt_dp(np.diag([-400.0, 0, 0]), np.diag([100.0, 0, 0]))

assert abs(dp_tension - s_a**2 / E) < 1e-9
assert abs(dp_torsion - (1 + nu) * tau_a**2 / E) < 1e-9
assert abs(dp_mean - (150.0 + s_a) * s_a / E) < 1e-9
assert dp_compressive == 0.0  # no tensile stress, no damage

print(f"tension {dp_tension:.4f}, torsion {dp_torsion:.4f} MPa")
print(f"tension with mean {dp_mean:.4f} MPa, compressive cycle {dp_compressive:.1f}")
print(f"t/f giving equal DP: {1 / np.sqrt(1 + nu):.3f}")
```

Output:

```text
tension 0.4500, torsion 0.2600 MPa
tension with mean 0.6750 MPa, compressive cycle 0.0
t/f giving equal DP: 0.877
```

**On a supplied workbook:**

```bash
uv run multifat-pipeline --material Al7075_T6 --models SWT --all-variants --results-dir Results/current/guides
```

`SWT_Al7075_T6.csv` and `SWT_ext_Al7075_T6.csv` hold the DP (`CP_value`, MPa) and the
master-curve life. SWT is skipped on a workbook without `E` or `nu`.

## Comparison capabilities and outputs

- **Life:** master curve (`Nf_expected`), not the strain–life relation.
- **DP comparison:** supported, against the master-curve `DP_fit`. Because DP is quadratic in the
  stresses, a DP error is about twice the corresponding stress error.
- **`_ext`:** available; maximum DP over planes, a repository variant.
- **Fatigue-limit datasets:** the stress-scaled index `FI_load` $= 1/s - 1$ is the meaningful
  index for a quadratic DP (`multifat.eval.endurance`).

## Verification and limitations

- [`tests/methods/test_swt.py`](../../tests/methods/test_swt.py): uniaxial product with tensile,
  zero and compressive means, and zero damage for a fully compressive cycle.
- Not verified: reproduction of the 1970 experimental data or of a multiaxial dataset.
- Limitations: elastic strains only; designed for tensile cracking, so shear-dominated ductile
  materials are expected to be poorly described in torsion.

## References

- K. N. Smith, P. Watson, T. H. Topper (1970), A stress–strain function for the fatigue of
  metals, *Journal of Materials* 5(4), 767–778.
- D. F. Socie (1987), Multiaxial fatigue damage models, *Journal of Engineering Materials and
  Technology*.
- D. F. Socie, G. B. Marquis (2000), *Multiaxial Fatigue*, SAE International.
