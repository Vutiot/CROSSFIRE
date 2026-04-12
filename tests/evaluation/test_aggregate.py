"""Tests for multi-seed aggregation and mode comparison."""

import pytest

from crossfire.evaluation.aggregate import aggregate_seeds, compare_modes
from crossfire.shared.schemas.evaluation import (
    EvaluationResult,
    ScopeResult,
    StageResult,
)


def _make_result(p, r, f1, pcs=None, fpr=None, scopes=None, stages=None):
    return EvaluationResult(
        overall_precision=p,
        overall_recall=r,
        overall_f1=f1,
        overall_partial_credit_score=pcs,
        distractor_false_positive_rate=fpr,
        per_scope=scopes or [],
        per_stage=stages or [],
    )


class TestAggregateIdentical:
    """Aggregating identical results produces std=0 and mean=value."""

    def test_identical_results(self):
        results = [_make_result(0.8, 0.6, 0.685) for _ in range(3)]
        agg = aggregate_seeds(results)
        assert agg.n_seeds == 3
        assert agg.precision.mean == pytest.approx(0.8)
        assert agg.precision.std == pytest.approx(0.0)
        assert agg.precision.ci_lower == pytest.approx(0.8)
        assert agg.precision.ci_upper == pytest.approx(0.8)
        assert agg.recall.mean == pytest.approx(0.6)
        assert agg.f1.mean == pytest.approx(0.685)


class TestAggregateVaried:
    """Aggregating varied results produces correct statistics."""

    def test_mean_and_std(self):
        results = [
            _make_result(0.7, 0.5, 0.58),
            _make_result(0.8, 0.6, 0.685),
            _make_result(0.9, 0.7, 0.79),
        ]
        agg = aggregate_seeds(results)
        assert agg.precision.mean == pytest.approx(0.8)
        assert agg.precision.std == pytest.approx(0.1)
        assert agg.recall.mean == pytest.approx(0.6)
        assert agg.recall.std == pytest.approx(0.1)

    def test_confidence_interval_contains_mean(self):
        results = [
            _make_result(0.7, 0.5, 0.58),
            _make_result(0.8, 0.6, 0.685),
            _make_result(0.9, 0.7, 0.79),
        ]
        agg = aggregate_seeds(results)
        assert agg.precision.ci_lower < agg.precision.mean
        assert agg.precision.ci_upper > agg.precision.mean

    def test_optional_partial_credit(self):
        results = [
            _make_result(0.8, 0.6, 0.685, pcs=0.7),
            _make_result(0.8, 0.6, 0.685, pcs=0.8),
            _make_result(0.8, 0.6, 0.685, pcs=0.9),
        ]
        agg = aggregate_seeds(results)
        assert agg.partial_credit_score is not None
        assert agg.partial_credit_score.mean == pytest.approx(0.8)

    def test_optional_distractor_fpr(self):
        results = [
            _make_result(0.8, 0.6, 0.685, fpr=0.1),
            _make_result(0.8, 0.6, 0.685, fpr=0.2),
            _make_result(0.8, 0.6, 0.685, fpr=0.3),
        ]
        agg = aggregate_seeds(results)
        assert agg.distractor_fpr is not None
        assert agg.distractor_fpr.mean == pytest.approx(0.2)


class TestAggregateSingleSeed:
    """Single seed produces mean=value, std=0."""

    def test_single_result(self):
        results = [_make_result(0.8, 0.6, 0.685)]
        agg = aggregate_seeds(results)
        assert agg.n_seeds == 1
        assert agg.precision.mean == pytest.approx(0.8)
        assert agg.precision.std == 0.0
        assert agg.precision.ci_lower == pytest.approx(0.8)
        assert agg.precision.ci_upper == pytest.approx(0.8)


class TestAggregateEmpty:
    """Empty results list produces zeros."""

    def test_empty(self):
        agg = aggregate_seeds([])
        assert agg.n_seeds == 0
        assert agg.precision.mean == 0.0
        assert agg.recall.mean == 0.0
        assert agg.f1.mean == 0.0


class TestAggregatePerScope:
    """Per-scope aggregation across seeds."""

    def test_per_scope(self):
        results = [
            _make_result(
                0.8,
                0.6,
                0.685,
                scopes=[
                    ScopeResult(
                        scope="intra_doc",
                        precision=0.9,
                        recall=0.8,
                        f1=0.845,
                        partial_credit_score=0.85,
                    ),
                ],
            ),
            _make_result(
                0.8,
                0.6,
                0.685,
                scopes=[
                    ScopeResult(
                        scope="intra_doc",
                        precision=0.7,
                        recall=0.6,
                        f1=0.645,
                        partial_credit_score=0.65,
                    ),
                ],
            ),
        ]
        agg = aggregate_seeds(results)
        assert "intra_doc" in agg.per_scope
        assert agg.per_scope["intra_doc"]["precision"].mean == pytest.approx(0.8)
        assert agg.per_scope["intra_doc"]["recall"].mean == pytest.approx(0.7)

    def test_scope_absent_in_some_seeds(self):
        results = [
            _make_result(
                0.8,
                0.6,
                0.685,
                scopes=[
                    ScopeResult(
                        scope="intra_doc",
                        precision=1.0,
                        recall=1.0,
                        f1=1.0,
                        partial_credit_score=1.0,
                    ),
                ],
            ),
            _make_result(0.8, 0.6, 0.685, scopes=[]),  # no intra_doc scope
        ]
        agg = aggregate_seeds(results)
        # intra_doc present in seed 1 (1.0) absent in seed 2 (0.0) → mean=0.5
        assert agg.per_scope["intra_doc"]["precision"].mean == pytest.approx(0.5)


class TestAggregatePerStage:
    """Per-stage aggregation across seeds."""

    def test_per_stage(self):
        results = [
            _make_result(
                0.8,
                0.6,
                0.685,
                stages=[
                    StageResult(stage="claim_extraction", precision=0.9, recall=0.8, f1=0.845),
                ],
            ),
            _make_result(
                0.8,
                0.6,
                0.685,
                stages=[
                    StageResult(stage="claim_extraction", precision=0.7, recall=0.6, f1=0.645),
                ],
            ),
        ]
        agg = aggregate_seeds(results)
        assert "claim_extraction" in agg.per_stage
        assert agg.per_stage["claim_extraction"]["precision"].mean == pytest.approx(0.8)


class TestCompareModes:
    """Statistical significance testing between pipeline modes."""

    def test_returns_p_values(self):
        results_a = [
            _make_result(0.8, 0.7, 0.75),
            _make_result(0.82, 0.72, 0.77),
            _make_result(0.78, 0.68, 0.73),
        ]
        results_b = [
            _make_result(0.5, 0.4, 0.44),
            _make_result(0.52, 0.42, 0.46),
            _make_result(0.48, 0.38, 0.43),
        ]
        p_values = compare_modes(results_a, results_b)
        assert "precision" in p_values
        assert "recall" in p_values
        assert "f1" in p_values
        # Significant difference expected
        assert p_values["precision"] < 0.05
        assert p_values["recall"] < 0.05

    def test_similar_modes_high_p_value(self):
        results_a = [
            _make_result(0.8, 0.7, 0.75),
            _make_result(0.81, 0.71, 0.76),
            _make_result(0.79, 0.69, 0.74),
        ]
        results_b = [
            _make_result(0.8, 0.7, 0.75),
            _make_result(0.79, 0.69, 0.74),
            _make_result(0.81, 0.71, 0.76),
        ]
        p_values = compare_modes(results_a, results_b)
        # No significant difference expected
        assert p_values["precision"] > 0.05

    def test_empty_results(self):
        p_values = compare_modes([], [_make_result(0.8, 0.7, 0.75)])
        assert p_values == {}

    def test_single_result_per_mode_skipped(self):
        p_values = compare_modes(
            [_make_result(0.8, 0.7, 0.75)],
            [_make_result(0.5, 0.4, 0.44)],
        )
        # t-test needs >= 2 samples per group
        assert p_values == {}


class TestAggregateDeterminism:
    """Same inputs always produce identical results."""

    def test_deterministic(self):
        results = [
            _make_result(0.7, 0.5, 0.58),
            _make_result(0.8, 0.6, 0.685),
            _make_result(0.9, 0.7, 0.79),
        ]
        a1 = aggregate_seeds(results)
        a2 = aggregate_seeds(results)
        assert a1 == a2

    def test_compare_deterministic(self):
        ra = [_make_result(0.8, 0.7, 0.75), _make_result(0.82, 0.72, 0.77)]
        rb = [_make_result(0.5, 0.4, 0.44), _make_result(0.52, 0.42, 0.46)]
        p1 = compare_modes(ra, rb)
        p2 = compare_modes(ra, rb)
        assert p1 == p2
