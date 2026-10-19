"""Analytical and source-equation checks for complete harmonic shear ellipses."""
import math
import unittest

import numpy as np

from fatigue.models.utils.shear_amplitude import shear_amplitude


class HarmonicAmplitudeTests(unittest.TestCase):
    def test_zero_line_circle_and_ellipse(self):
        for a, b, mcc, mce in [
            ([0, 0], [0, 0], 0, 0),
            ([10, 0], [0, 0], 10, 10),
            ([10, 0], [0, 10], 10, 10 * math.sqrt(2)),
            ([10, 0], [0, 5], 10, math.sqrt(125)),
            ([3, 4], [6, 8], math.sqrt(125), math.sqrt(125)),
            ([3, 4], [-6, -8], math.sqrt(125), math.sqrt(125)),
        ]:
            with self.subTest(a=a, b=b):
                self.assertAlmostEqual(shear_amplitude(a, b, algorithm='mcc_harmonic'), mcc, places=13)
                self.assertAlmostEqual(shear_amplitude(a, b, algorithm='mce_harmonic'), mce, places=13)

    def test_rotations_reflections_and_phase_origin(self):
        a, b = np.array([10., 0.]), np.array([0., 5.])
        for angle in np.linspace(-math.pi, math.pi, 17):
            Q = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
            for algorithm, expected in [('mcc_harmonic', 10), ('mce_harmonic', math.sqrt(125))]:
                for transform in [Q, np.diag([-1, 1]) @ Q]:
                    self.assertAlmostEqual(shear_amplitude(transform @ a, transform @ b, algorithm=algorithm), expected, places=13)
                # tau(t+angle) = (a*cos(angle) - b*sin(angle))*sin(t)
                #              + (a*sin(angle) + b*cos(angle))*cos(t).
                result = shear_amplitude(a * math.cos(angle) - b * math.sin(angle),
                    a * math.sin(angle) + b * math.cos(angle), algorithm=algorithm)
                self.assertAlmostEqual(result, expected, places=13)

    def test_mean_translation_and_instantaneous_maximum_are_distinct(self):
        t = np.arange(1024) * (2 * math.pi / 1024)
        a, b = np.array([10., 0.]), np.array([0., 10.])
        for mean in [np.zeros(2), np.array([30., -40.])]:
            path = mean + np.sin(t)[:, None] * a + np.cos(t)[:, None] * b
            # Independent Fourier extraction shows that translation affects only the centre.
            recovered_a = 2 * np.mean(path * np.sin(t)[:, None], axis=0)
            recovered_b = 2 * np.mean(path * np.cos(t)[:, None], axis=0)
            for algorithm, expected in [('mcc_harmonic', 10), ('mce_harmonic', math.sqrt(200))]:
                self.assertAlmostEqual(shear_amplitude(recovered_a, recovered_b, algorithm=algorithm), expected, places=12)
        self.assertAlmostEqual(np.max(np.linalg.norm(path, axis=1)), 60, delta=1e-4)
        self.assertEqual(np.linalg.norm(mean), 50)

    def test_direct_sampling_and_longest_chord(self):
        t = np.arange(65536) * (2 * math.pi / 65536)
        for a, b in [(np.array([7., 2.]), np.array([-3., 5.])),
                     (np.array([1., 2.]), np.array([3., 6.])),
                     (np.array([10., 0.]), np.array([0., 10.]))]:
            path = np.sin(t)[:, None] * a + np.cos(t)[:, None] * b
            mcc = shear_amplitude(a, b)
            sampled = np.max(np.linalg.norm(path, axis=1))
            self.assertAlmostEqual(sampled / mcc, 1, delta=2e-9)
            # For a centred harmonic path antipodal points attain the maximum chord.
            half_chords = np.linalg.norm(path[:32768] - path[32768:], axis=1) / 2
            self.assertAlmostEqual(np.max(half_chords) / mcc, 1, delta=2e-9)
            # MCE is sqrt(2) times the RMS distance for a complete harmonic cycle.
            sampled_mce = math.sqrt(2 * np.mean(np.sum(path ** 2, axis=1)))
            self.assertAlmostEqual(sampled_mce, shear_amplitude(a, b, algorithm='mce_harmonic'), places=12)
        # All-pairs check avoids assuming the antipodal chord rule in the numerical reference.
        t = np.arange(512) * (2 * math.pi / 512)
        path = np.stack([10 * np.sin(t), 5 * np.cos(t)], axis=-1)
        self.assertAlmostEqual(np.max(np.linalg.norm(path[:, None] - path[None, :], axis=-1)) / 2, 10, places=13)

    def test_extreme_scales_subnormals_and_true_overflow(self):
        for scale in [1e-300, 1e-200, 1., 1e200, 1e300]:
            for algorithm, factor in [('mcc_harmonic', 1), ('mce_harmonic', math.sqrt(1.25))]:
                result = shear_amplitude([scale, 0], [0, scale / 2], algorithm=algorithm)
                self.assertAlmostEqual(result / scale, factor, places=14)
        tiny = np.nextafter(0., 1.)
        self.assertEqual(shear_amplitude([tiny, 0], [0, 0]), tiny)
        self.assertEqual(shear_amplitude([tiny, 0], [0, 0], algorithm='rss'), tiny)
        huge = np.finfo(float).max
        self.assertEqual(shear_amplitude([huge, 0], [0, huge]), huge)
        with self.assertRaises(OverflowError):
            shear_amplitude([huge, 0], [0, huge], algorithm='mce_harmonic')
        with self.assertRaises(OverflowError):
            shear_amplitude([huge, huge], [huge, huge])

    def test_nearly_circular_elongated_and_mixed_magnitudes(self):
        for epsilon in [np.finfo(float).eps, 1e-12, 1e-6]:
            self.assertAlmostEqual(shear_amplitude([1, 0], [0, 1 + epsilon]), 1 + epsilon, places=14)
        self.assertEqual(shear_amplitude([1e300, 0], [0, 1e-300]), 1e300)
        self.assertEqual(shear_amplitude([1e-300, 0], [0, 1e300], algorithm='rss'), 1e300)

    def test_batch_matches_individual_inputs_without_mutation(self):
        a = np.array([[0, 0], [10, 0], [3, 4.]]).reshape(1, 3, 2)
        b = np.array([[0, 0], [0, 5], [-6, -8.]]).reshape(1, 3, 2)
        original_a, original_b = a.copy(), b.copy()
        for algorithm in ['mcc_harmonic', 'mce_harmonic', 'rss']:
            result = shear_amplitude(a, b, algorithm=algorithm)
            self.assertEqual(result.shape, (1, 3))
            for i in range(3):
                self.assertEqual(result[0, i], shear_amplitude(a[0, i], b[0, i], algorithm=algorithm))
        np.testing.assert_array_equal(a, original_a)
        np.testing.assert_array_equal(b, original_b)
        self.assertEqual(shear_amplitude(np.empty((0, 2)), np.empty((0, 2))).shape, (0,))

    def test_svd_independent_crosscheck(self):
        rng = np.random.default_rng(4381)
        matrices = rng.normal(size=(1000, 2, 2))
        s = np.linalg.svd(matrices, compute_uv=False)
        np.testing.assert_allclose(shear_amplitude(matrices[..., 0], matrices[..., 1]), s[:, 0], rtol=7e-15)
        np.testing.assert_allclose(shear_amplitude(matrices[..., 0], matrices[..., 1], algorithm='rss'),
                                   np.hypot(s[:, 0], s[:, 1]), rtol=7e-15)

    def test_invalid_shapes_types_nonfinite_and_unknown_algorithms(self):
        for a, b in [([1], [2]), (1, 2), (np.eye(3), np.eye(3)),
                     ([1, 2], [[1, 2]]), ([np.nan, 0], [0, 0]),
                     ([0, 0], [np.inf, 0]), ([1j, 0], [0, 0]), (['1', '2'], [0, 0])]:
            with self.subTest(a=a, b=b), self.assertRaises((TypeError, ValueError)):
                shear_amplitude(a, b)
        if np.finfo(np.longdouble).tiny < np.longdouble(np.nextafter(0., 1.)):
            extended_tiny = np.array([np.finfo(np.longdouble).tiny, 0], dtype=np.longdouble)
            with self.assertRaises(ValueError):
                shear_amplitude(extended_tiny, [0, 0])
        for name in ['method_default', 'mcc', 'MCC', '', None, [], 1]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                shear_amplitude([1, 2], [3, 4], algorithm=name)

    def test_existing_rss_range_and_tensorial_strain_conventions(self):
        from fatigue.eval.evaluator import _equivalent_shear_range_from_harmonics
        from fatigue.models.utils.plane_history import strain_ranges
        a, b = np.array([3., 4.]), np.array([2., -1.])
        sine, cosine = np.zeros((3, 3)), np.zeros((3, 3))
        sine[:2, 2] = sine[2, :2] = a
        cosine[:2, 2] = cosine[2, :2] = b
        mce = shear_amplitude(a, b, algorithm='mce_harmonic')
        self.assertEqual(mce, shear_amplitude(a, b, algorithm='rss'))
        self.assertAlmostEqual(mce, math.sqrt(30), places=14)
        self.assertAlmostEqual(2 * mce, _equivalent_shear_range_from_harmonics(sine, cosine), places=13)
        self.assertAlmostEqual(4 * mce, strain_ranges(sine, cosine)[0], places=13)

    def test_existing_bp_major_semiaxis(self):
        from fatigue.models.integral_methods.bohme_papuga import _plane_amplitudes
        sine, cosine = np.zeros((3, 3)), np.zeros((3, 3))
        sine[:2, 2] = sine[2, :2] = [7, 2]
        cosine[:2, 2] = cosine[2, :2] = [-3, 5]
        result = _plane_amplitudes(np.zeros((3, 3)), sine, cosine, np.array([[0., 0., 1.]]))[2][0]
        self.assertAlmostEqual(shear_amplitude([7, 2], [-3, 5]), result, places=13)

    def test_matlab_ca_expression_and_reconstructed_load_cases(self):
        # Algebraic Ca.m uses a=(f,p), b=(g,q). Its active result is MCC;
        # the commented sqrt(a1^2+a2^2) alternative is MCE.
        # At phi=0, theta=pi/4, delta_torsion=pi/2, radial/hoop=0,
        # f=0, p=-Sigma_ax/2, g=-Sigma_torsion/sqrt(2), q=0.
        for axial, torsion, mcc, mce in [(20, 10 * math.sqrt(2), 10, math.sqrt(200)),
                                       (20, 5 * math.sqrt(2), 10, math.sqrt(125))]:
            f, p, g, q = 0., -axial / 2, -torsion / math.sqrt(2), 0.
            half_trace = (f*f + p*p + g*g + q*q) / 2
            root = math.sqrt(half_trace**2 - (f*q-g*p)**2)
            matlab_mcc = math.sqrt(half_trace + root)
            matlab_mce = math.sqrt((half_trace + root) + (half_trace - root))
            self.assertAlmostEqual(matlab_mcc, mcc, places=13)
            self.assertAlmostEqual(matlab_mce, mce, places=13)
            self.assertAlmostEqual(shear_amplitude([f, p], [g, q]), matlab_mcc, places=13)
            self.assertAlmostEqual(shear_amplitude([f, p], [g, q], algorithm='rss'), matlab_mce, places=13)
