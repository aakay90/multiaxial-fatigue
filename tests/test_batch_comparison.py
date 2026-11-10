"""Cross-batch statistics (examples/batch_comparison.py, issue #71).

The statistics are checked on synthetic errors with known structure; the last test fails when a
method or a workbook of a declared family changed since the committed results were generated.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples import batch_comparison as bc  # noqa: E402

BATCHES = ["B1", "B2", "B3"]


def _cells(bias):
    """Cell table of an exact method x batch bias matrix, with a known SD and n."""
    rows = [
        dict(Method=m, Batch=b, Path="T", n=10, bias=bias[i, j], sd=0.1)
        for i, m in enumerate(["M1", "M2", "M3", "M4"])
        for j, b in enumerate(BATCHES)
    ]
    return pd.DataFrame(rows)


def test_two_way_recovers_additive_offsets():
    alpha = np.array([0.1, -0.2, 0.05, 0.3])
    alpha -= alpha.mean()  # effects of an additive model are centred
    beta = np.array([0.12, 0.04, -0.16])
    summary, residuals = bc.two_way(_cells(0.07 + alpha[:, None] + beta[None, :]), BATCHES)
    full = summary[summary["batches"] == "B1+B2+B3"].iloc[0]
    assert full["mu"] == pytest.approx(0.07)
    for b, value in zip(BATCHES, beta):
        assert full[f"offset_{b}"] == pytest.approx(value)
    assert full["interaction_rms"] == pytest.approx(0.0, abs=1e-12)
    assert full["cell_se"] == pytest.approx(0.1 / np.sqrt(10))
    assert full["method_sd"] == pytest.approx(np.std(alpha, ddof=1))
    assert np.allclose(residuals["residual"], 0.0)
    # every subset of >= 2 batches is decomposed as well
    assert set(summary["batches"]) == {"B1+B2+B3", "B1+B2", "B1+B3", "B2+B3"}


def test_two_way_interaction_is_the_non_additive_part():
    bias = np.zeros((4, 3))
    bias[0, 0] = 0.3  # one method reacts to one batch
    summary, _ = bc.two_way(_cells(bias), BATCHES)
    full = summary[summary["batches"] == "B1+B2+B3"].iloc[0]
    # residual of a single bump in a 4 x 3 table: 0.3 (1 - 1/4)(1 - 1/3) at the bumped cell
    assert full["interaction_rms"] > 0.05


def test_benjamini_hochberg_matches_scipy():
    p = np.array([0.001, 0.04, 0.03, 0.2, np.nan, 0.5])
    q = bc.benjamini_hochberg(p)
    ok = np.isfinite(p)
    assert np.allclose(q[ok], stats.false_discovery_control(p[ok]))
    assert np.isnan(q[~ok]).all()


def test_bootstrap_interval_is_reproducible_and_brackets_the_mean():
    x = np.random.default_rng(1).normal(0.1, 0.2, 30)
    a = bc.bootstrap_mean_ci(x, np.random.default_rng(bc.SEED))
    b = bc.bootstrap_mean_ci(x, np.random.default_rng(bc.SEED))
    assert a == b and a[0] < x.mean() < a[1]
    assert np.isnan(bc.bootstrap_mean_ci(x[:2], np.random.default_rng(0))).all()


def test_batch_effect_detects_a_shift_only():
    rng = np.random.default_rng(3)
    rows = []
    for method, shift in (("SAME", 0.0), ("SHIFT", 0.3)):
        for k, b in enumerate(BATCHES):
            for e in rng.normal(shift * k, 0.05, 15):
                rows.append(dict(Method=method, Path="T", Batch=b, Error_load=e))
    t = bc.batch_effect(pd.DataFrame(rows)).set_index("Method")
    assert t.loc["SHIFT", "q_BH"] < 1e-4 < t.loc["SAME", "q_BH"]


def test_transfer_penalty_pairs_the_same_tests():
    own = pd.DataFrame(
        dict(Method="M", Batch="B2", Flag=[0, 1, 1, 1, 1], Observation_id=list("abcde"),
             Error_load=[0.0, 0.1, -0.1, 0.1, -0.1])
    )  # fmt: skip
    moved = pd.DataFrame(
        dict(Method="M", Batch="B2", Design="B1", Flag=1, Observation_id=list("abcdef"),
             Error_load=[0.5, 0.3, 0.3, 0.3, 0.3, 9.0])
    )  # fmt: skip
    (row,) = bc.transfer_penalty(own, moved).to_dict("records")
    # 'a' is a design test of the own run and 'f' is not in it: both are left out
    assert row["n"] == 4
    assert row["rms_own"] == pytest.approx(0.1)
    assert row["rms_transfer"] == pytest.approx(0.3)
    assert row["penalty"] == pytest.approx(0.2)


def test_committed_batch_comparison_is_current():
    """A new method, a changed workbook or a new revision needs the results regenerated."""
    problems = bc.check()
    assert not problems, (
        "; ".join(problems)
        + " -> uv run python examples/batch_comparison.py all <tmp_dir> --jobs 4"
    )
