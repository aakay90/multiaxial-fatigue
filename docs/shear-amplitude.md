# Harmonic shear amplitudes and controlled Findley evaluation

Phase 1 provides a numerical utility without changing any fatigue criterion,
plane-selection rule, calibration record, experimental input or reporting format.
The existing evaluator, plane-history utilities and Böhme–Papuga implementation
do not import the new module. Phase 2 adds a separate Findley damage-parameter
entry point for numerical comparisons, without changing production predictions.
Phase 3A uses that interface for configurable Findley calibration in Script 0.
Production Findley assessment continues to evaluate MCE and load MCE-compatible
records only.

## Definition and API

For a complete single-frequency trajectory in a common two-dimensional tangent
basis,

\[
\boldsymbol\tau(t)=\boldsymbol\tau_m+\mathbf a\sin t+\mathbf b\cos t,
\qquad A=[\mathbf a\;\mathbf b],
\]

the singular values \(s_1\geq s_2\) of \(A\) are the ellipse semiaxes. The API returns
an amplitude in the units supplied by the caller.

| Identifier | Returned amplitude | Harmonic equivalence |
|---|---|---|
| `mcc_harmonic` | \(s_1\) | Minimum circumscribed circle radius and half the longest chord |
| `mce_harmonic` | \(\sqrt{s_1^2+s_2^2}=\sqrt{\|a\|^2+\|b\|^2}\) | Existing harmonic RSS definition |
| `rss` | Alias of `mce_harmonic` | Identical numerical implementation |

```python
from fatigue.models.utils.shear_amplitude import shear_amplitude

mcc = shear_amplitude([10, 0], [0, 5], algorithm="mcc_harmonic")  # 10
mce = shear_amplitude([10, 0], [0, 5], algorithm="mce_harmonic")  # sqrt(125)
```

Inputs have shape `(2,)`, or identical batch shapes `(..., 2)`. A single pair
returns `float`; a batch returns an array with the last axis removed. Inputs
must be finite real numeric coefficients representable in float64. Shape
broadcasting, complex values and unknown identifiers are rejected. `method_default`
is deliberately not an algorithm. No global user option is introduced.

The mean vector is the ellipse centre, so it is not an amplitude input. Its norm
is a separate scalar. Neither amplitude is generally the maximum instantaneous
magnitude of the translated trajectory. For example, a circle of radius 10 with
mean `(30, -40)` has MCC 10, MCE \(10\sqrt2\), mean magnitude 50 and maximum total
magnitude 60. A shear range is twice the chosen amplitude. The function does not
convert strain conventions. Tensorial shear strain must be converted by the
caller when an engineering shear measure is required.

## Numerical formulation

MCC uses the larger eigenvalue of the 2 by 2 Gram matrix, without subtracting
nearly equal quantities. Each input pair is first divided by the largest absolute
coefficient, then the square root of

\[
\lambda_+=\tfrac12\left(a\cdot a+b\cdot b+
\operatorname{hypot}(a\cdot a-b\cdot b,2a\cdot b)\right)
\]

is multiplied by that scale. MCE uses the scaled Frobenius norm. This avoids
squaring the original coefficients and protects very small and very large paths.
Only exact zero is classified as a zero path. There is no absolute physical
cutoff, eigenvalue clipping tolerance or iterative optimisation.

Calculations use float64. Contributions lost by underflow after normalisation
cannot alter the leading amplitude at float64 precision. Subnormal results retain
float64 rounding; a result beyond its finite range raises `OverflowError`.
No relative accuracy guarantee is possible below the subnormal spacing.
The algorithms cover complete harmonic ellipses and their line/point limits.
They are not enclosing-circle/ellipse solvers for arbitrary sampled paths,
partial cycles or multiple frequencies. No minor-semiaxis estimate is returned.

A local comparison on 100,000 random matrices, using the median of five batches
of three evaluations, measured approximately 0.020 s for this MCC implementation
and 0.062 s for NumPy SVD. This observation motivates the simple closed form;
it is not a portable timing guarantee. Tests compare both amplitudes against
SVD on 1,000 matrices independently of the analytical examples.

## Source interpretation and verification

The scientific reference is Eva Cízová, *Parameters of Stress Tensor History and
Their Impact on Fatigue Life*, Czech Technical University in Prague, 2021,
supervised by Jan Papuga. Equation numbering follows the supplied searchable
reference extracted from that thesis. The full PDF was not available in this
session, so no independent page/image verification of its equations is claimed.

- Eq. (2.1) defines longest-chord amplitude; Eqs. (2.5)-(2.6) define MCC.
- Eq. (2.9) supplies the MCE semiaxis combination. Eqs. (3.26), (3.27) and (3.29)
  are referenced in the supplied summary for the harmonic ellipse identities.
- Section 2.5 describes moment of inertia with path-length weighting. It is a
  different amplitude definition and is not implemented here.

The MATLAB appendix was inspected directly. Its algebraic `Ca.m` files under
`Programy_DP/Nová kritéria` and the circle/ellipse directory are byte-identical
(SHA-256 `e96f70827fc0ce5c158ab56ade21af3a9eb8e4b72e47f205c5f3c93ab08092e5`).
They define `Cl=f*sin(t)+g*cos(t)` and `Cr=p*sin(t)+q*cos(t)`, so the Python input
mapping is `a=(f,p)`, `b=(g,q)`. The active expression returns the major semiaxis
(MCC). The commented `sqrt(a1^2+a2^2)` alternative is MCE. `MOI/Ca.m` instead
uses temporal quadrature weighted by path speed.

Two source-equation reconstructions use `phi=0`, `theta=pi/4`, torsional phase
`pi/2`, zero radial/hoop amplitudes, axial amplitude 20 and torsional amplitude
\(10\sqrt2\) or \(5\sqrt2\). The resulting coefficients are respectively
`a=(0,-10), b=(-10,0)` and `a=(0,-10), b=(-5,0)`. Expected MCC/MCE amplitudes are
10 / \(\sqrt{200}\) and 10 / \(\sqrt{125}\). Automated tests reproduce the
MATLAB algebra in Python and agree to 13 decimal places. A MATLAB/Octave runtime
was not available, so this is an equation-level comparison, not execution of
MATLAB. The appendix result file `FatLimResultsAll.mat` contains a 286 by 60
comparison array; its criterion-level results were not used as isolated amplitude
benchmarks. No thesis experimental data are redistributed.

PragTic `solve.cpp` was inspected for `MCCM_IM` and `MCEM_IM`. Those routines
accept sampled polygons and iteratively determine centres and amplitudes;
`MCEM_IM` combines fitted axes through their quadratic norm. Their tolerances,
convergence behaviour and general-path algorithms are not ported or validated
by this phase. The provided files were supplied by Jan Papuga for WG4.3 study
and adaptation. The new implementation follows the stated harmonic identities;
no external solver implementation or source archive is copied into the package.

Run `python -m unittest discover -s tests -p test_shear_amplitude.py -v` for the
12 focused checks. They include exact zero, proportional/degenerate paths,
circles/ellipses, rotations/reflections, phase shifts, translated means, direct
time sampling, longest chords, extreme scales, invalid inputs, batch evaluation,
source-equation reconstructions and agreement with existing RSS and BP helpers.
Run `MPLBACKEND=Agg python tools/run_tests.py` for existing fatigue regressions too.

## Controlled Findley evaluation

The method-specific function `evaluate_findley` in
`fatigue/models/cp_methods/fin_harmonic.py` accepts the existing CP adapter case
arguments (`S0`, `E0`, `S1`, `E1`, `params`, `R_list`, `harmonics`) and the optional
keyword `shear_amplitude_algorithm`. It returns the existing `CaseResult`, with
stress-valued damage parameters, not fatigue life.

```python
from fatigue.models.cp_methods.fin_harmonic import evaluate_findley

# case contains the existing CP adapter arguments, including params['k_FI'].
legacy = evaluate_findley(**case)
mce = evaluate_findley(**case, shear_amplitude_algorithm="mce_harmonic")
mcc = evaluate_findley(**case, shear_amplitude_algorithm="mcc_harmonic")
print(mcc.values[""], mcc.values["_ext"])  # FIN and FIN_ext damage parameters
```

Omitted selection (`None`) delegates exactly to the unchanged production FIN
adapter. This preserves the existing harmonic MCE/RSS convention and, if harmonic
coefficients are unavailable, the existing two-endpoint calculation. `None` is
an interface sentinel, not another numerical amplitude algorithm. Every explicit
selection, including MCE or its `rss` alias, requires both finite, real 3 by 3
stress tensors `harmonics['S_sin']` and `harmonics['S_cos']`. Partial or absent
coefficients raise `ValueError`; two endpoints cannot establish phase information.
No `method_default` identifier is accepted.

Stress tensors and coefficient tensors share a global basis. Each orthonormal
matrix in `R_list` has the candidate-plane axes as columns, with its third column
as the normal. After transformation by \(R^T S R\), the local xz/yz entries of
each coefficient tensor form the two input vectors to the shared amplitude
function. Strain tensors retain the adapter interface but do not enter Findley.
The midpoint `(S0 + S1)/2` defines the mean stress, as in the production evaluator;
a separate `S_mean` entry is not read. The coefficient tensors, not the synthetic
endpoint shear range, determine explicit harmonic amplitudes.

On **every** candidate plane the function evaluates
\(P=\tau_a+k_{\mathrm{FI}}\sigma_{n,\max}\), then maximises this complete
expression. The existing normal-extrema helper is reused without alteration,
including signed compression. It gives
\(\sigma_{n,\max}=\sigma_{n,m}+\sqrt{\sigma_{n,s}^2+\sigma_{n,c}^2}\)
independently of the selected shear algorithm. Mean shear does not enter the
amplitude. No factor of two is applied to amplitude in the Findley expression.
Both output keys contain the same maximum because Findley selects planes by
damage itself; no artificial distinction between FIN and FIN_ext is introduced.

For a prescribed plane with mean normal stress 7, normal sine/cosine coefficients
3 and 4, and \(k_{\mathrm{FI}}=0.2\), the normal contribution is 2.4.

| Shear semiaxes | MCC amplitude | MCE amplitude | MCC Findley | MCE Findley |
|---|---:|---:|---:|---:|
| 10, 10 | 10 | 14.142136 | 12.4 | 16.542136 |
| 10, 5 | 10 | 11.180340 | 12.4 | 13.580340 |
| 10, 0 | 10 | 10 | 12.4 | 12.4 |

The automated two-plane example additionally reverses the ranking. On normal z,
a circle of radius 10 and mean normal 7 gives MCC/MCE damage 11.4/15.542136.
On normal x, a line of amplitude \(\sqrt{164}\) and mean normal 5 gives
13.806248 for either algorithm. Thus MCC selects normal x and MCE selects normal z.
Replacing amplitude only after an MCE search would give the wrong MCC result.
The tests also compare 30 random planes with independent SVD and normal-traction
projections, and check default snapshots, phase/basis invariance, mean stresses,
endpoint rejection, small/large shear scales and other-method isolation.
Run `python -m unittest discover -s tests -p test_findley_harmonic.py -v`.

Only the supplied finite plane set is searched. The input assumptions and
arbitrary-path restrictions of the shared library still apply. Explicit MCE and
legacy harmonic MCE agree within float64 rounding for ordinary stress scales;
explicit evaluation avoids the legacy synthetic-shear endpoint cutoff and mean
subtraction. The omitted-selection path remains exactly unchanged. Normal-extrema
arithmetic retains the existing float64 limits, including overflow when normal
coefficients are squared at extreme scales. These are numerical verifications,
not independent experimental validation of alternative-amplitude Findley.

This separate entry point is intentional. Calibration fingerprints hash entire
production source files, including `fin.py`, the evaluator and adapter. Keeping
them unchanged preserves both established results and existing record identities.
No algorithm parameter is added to the general adapter, production registry or
material dictionary. Script 0 has a Findley-specific calibration option, described
below. Other criteria cannot inherit this selection.
The diagnostic function does not load or apply a damage-life curve. In particular,
an MCE-calibrated curve must not be applied to MCC damage parameters.

## Findley calibration selection

Script 0 accepts `--shear-amplitude-algorithm method_default|mcc_harmonic|mce_harmonic`.
It also accepts `rss` as a canonicalised MCE alias. The default preserves the
historical numerical path, including its endpoint fallback. Explicit selections
require stored stress sine and cosine tensors for every selected coefficient and
master-curve failure observation. Checking the original case avoids silently
using the proportional fallback supplied by the general tensor extractor.

`fatigue/eval/findley_calibration.py` supplies the configured case-level callable
to both calibration stages. Every candidate plane is evaluated using the same
selected amplitude in coefficient optimisation and curve fitting. The existing
selection rules, normal-stress maximum, coefficient bounds, scatter objective,
failure-only fitting and plane-grid settings are retained. An explicit override
for another method is rejected; unavailable batch pairs are reported and skipped.

New Findley records store method-scoped `amplitude_settings`, including the resolved
algorithm, `DEFINITION_VERSION` from the shared library (`harmonic-shear-v1`), the
evaluation path and implementation fingerprint. The fingerprint and metadata also
distinguish records in calibration history, even when proportional cases give
identical fitted values. Metadata-free legacy MCE requires verified historical
source identity and all existing input/procedure/settings compatibility checks.

The [calibration workflow](calibration-workflow.md#findley-amplitude-selection)
provides commands, record fields, compatibility rules and a complete numerical
example. Script 1 and the production Findley registry remain unchanged. Their
ordinary calibration lookups require MCE before choosing the newest compatible
record, including when an explicit ID is supplied. MCC records cannot supply that
assessment. Production MCC life prediction and its configuration require separate
Phase 3B approval. Neither calibration agreement nor these software checks establish
independent experimental validation of alternative-amplitude Findley.
