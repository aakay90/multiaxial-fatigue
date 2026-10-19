# Independent harmonic shear amplitudes

Phase 1 provides a numerical utility without changing any fatigue criterion,
plane-selection rule, calibration record, experimental input or reporting format.
The existing evaluator, plane-history utilities and Böhme–Papuga implementation
do not import the new module.

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

## Subsequent integration

The definition version is `DEFINITION_VERSION = "harmonic-shear-v1"`. No JSON
schema or compatibility check changes in this PR. A later integration must record
the effective resolved algorithm, its definition/implementation version, the
fatigue method and variant using it, coefficient/strain conventions, and relevant
calibration settings. Resolve aliases such as `rss` before recording the canonical
identifier. Never store an unresolved `method_default` as the effective algorithm.

Compatibility must include that identity only for computations depending on it.
A changed amplitude can change the critical plane and calibration, so affected
records need explicit rejection or recalibration. Unrelated methods must not be
invalidated. Method integration and user configuration require separate review.
