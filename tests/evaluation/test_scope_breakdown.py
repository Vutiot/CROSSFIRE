"""Tests for per-scope evaluation breakdown."""

import pytest

from crossfire.evaluation.scope_breakdown import score_by_scope
from crossfire.shared.schemas.contradictions import ContradictionLabel
from crossfire.shared.schemas.reports import DetectedContradiction, PipelineReport


def _make_report(detections):
    return PipelineReport(
        pipeline_mode="hybrid",
        case_dir="/test",
        detections=detections,
        timestamp="2026-04-06T00:00:00",
    )


class TestScopePerfectMatch:
    """All detections match all gold labels — each scope gets 1.0."""

    def test_per_scope_perfect(self, sample_gold_labels, perfect_report):
        result = score_by_scope(perfect_report, sample_gold_labels)
        assert len(result.per_scope) == 2  # intra_doc, inter_doc
        for sr in result.per_scope:
            assert sr.recall == 1.0
            assert sr.partial_credit_score == 1.0

    def test_overall_metrics_perfect(self, sample_gold_labels, perfect_report):
        result = score_by_scope(perfect_report, sample_gold_labels)
        assert result.overall_precision == 1.0
        assert result.overall_recall == 1.0
        assert result.overall_f1 == 1.0

    def test_scope_names(self, sample_gold_labels, perfect_report):
        result = score_by_scope(perfect_report, sample_gold_labels)
        scope_names = [sr.scope for sr in result.per_scope]
        # Sorted alphabetically
        assert scope_names == ["inter_doc", "intra_doc"]


class TestScopeIndependence:
    """Missing detections in one scope doesn't affect other scopes."""

    def test_one_scope_missed(self, sample_gold_labels):
        # Only match intra_doc (doc_A, doc_B) — miss inter_doc
        report = _make_report(
            [
                DetectedContradiction(
                    scope="intra_doc",
                    document_references=["doc_A", "doc_B"],
                    text_span_start=0,
                    text_span_end=20,
                    evidence_text="speed mismatch",
                    confidence=0.9,
                    description="speed mismatch",
                ),
            ]
        )
        result = score_by_scope(report, sample_gold_labels)

        scope_map = {sr.scope: sr for sr in result.per_scope}

        # intra_doc: 1 detection matches 1 gold -> recall=1.0, precision=1.0
        assert scope_map["intra_doc"].recall == 1.0
        assert scope_map["intra_doc"].precision == 1.0
        assert scope_map["intra_doc"].f1 == 1.0

        # inter_doc: 0 matches / 2 gold -> recall=0.0
        assert scope_map["inter_doc"].recall == 0.0
        assert scope_map["inter_doc"].f1 == 0.0


class TestScopeAssignment:
    """Detection scope comes from gold label, not pipeline."""

    def test_detection_gets_gold_scope(self):
        # Two gold labels: one intra_doc, one inter_doc — different doc refs
        gold = [
            ContradictionLabel(
                scope="intra_doc",
                mechanism="numeric_drift",
                detectability="single_hop",
                system_affinity="balanced",
                difficulty="easy",
                char_start=0,
                char_end=10,
                original_text="y",
                modified_text="x",
                rationale="test",
                ground_truth=True,
                document_references=["a", "b"],
            ),
            ContradictionLabel(
                scope="inter_doc",
                mechanism="entity_swap",
                detectability="multi_hop",
                system_affinity="graph_favoring",
                difficulty="medium",
                char_start=0,
                char_end=10,
                original_text="n",
                modified_text="m",
                rationale="test2",
                ground_truth=True,
                document_references=["c", "d"],
            ),
        ]
        report = _make_report(
            [
                DetectedContradiction(
                    scope="intra_doc",
                    document_references=["a", "b"],
                    text_span_start=0,
                    text_span_end=10,
                    evidence_text="match intra_doc",
                    confidence=0.9,
                    description="match intra_doc",
                ),
                DetectedContradiction(
                    scope="inter_doc",
                    document_references=["c", "d"],
                    text_span_start=0,
                    text_span_end=10,
                    evidence_text="match inter_doc",
                    confidence=0.8,
                    description="match inter_doc",
                ),
            ]
        )
        result = score_by_scope(report, gold)
        scope_map = {sr.scope: sr for sr in result.per_scope}

        # Each scope has 1 gold matched by its detection
        assert scope_map["intra_doc"].recall == 1.0
        assert scope_map["inter_doc"].recall == 1.0


class TestScopeEdgeCases:
    """Edge cases: empty report, empty gold, single scope."""

    def test_empty_report(self, sample_gold_labels, empty_report):
        result = score_by_scope(empty_report, sample_gold_labels)
        assert len(result.per_scope) == 2  # intra_doc, inter_doc
        for sr in result.per_scope:
            assert sr.precision == 0.0
            assert sr.recall == 0.0
            assert sr.f1 == 0.0
            assert sr.partial_credit_score == 0.0

    def test_empty_gold(self):
        report = _make_report(
            [
                DetectedContradiction(
                    scope="intra_doc",
                    document_references=["a", "b"],
                    text_span_start=0,
                    text_span_end=10,
                    evidence_text="orphan",
                    confidence=0.9,
                    description="orphan",
                ),
            ]
        )
        result = score_by_scope(report, [])
        assert result.per_scope == []

    def test_single_scope_all_gold(self):
        gold = [
            ContradictionLabel(
                scope="intra_doc",
                mechanism="numeric_drift",
                detectability="single_hop",
                system_affinity="balanced",
                difficulty="easy",
                char_start=0,
                char_end=10,
                original_text="y",
                modified_text="x",
                rationale="test",
                ground_truth=True,
                document_references=["a", "b"],
            ),
            ContradictionLabel(
                scope="intra_doc",
                mechanism="entity_swap",
                detectability="multi_hop",
                system_affinity="graph_favoring",
                difficulty="medium",
                char_start=0,
                char_end=10,
                original_text="n",
                modified_text="m",
                rationale="test2",
                ground_truth=True,
                document_references=["c", "d"],
            ),
        ]
        report = _make_report(
            [
                DetectedContradiction(
                    scope="intra_doc",
                    document_references=["a", "b"],
                    text_span_start=0,
                    text_span_end=10,
                    evidence_text="first",
                    confidence=0.9,
                    description="first",
                ),
                DetectedContradiction(
                    scope="intra_doc",
                    document_references=["c", "d"],
                    text_span_start=0,
                    text_span_end=10,
                    evidence_text="second",
                    confidence=0.8,
                    description="second",
                ),
            ]
        )
        result = score_by_scope(report, gold)
        assert len(result.per_scope) == 1
        assert result.per_scope[0].scope == "intra_doc"
        assert result.per_scope[0].recall == 1.0
        assert result.per_scope[0].precision == 1.0
        assert result.per_scope[0].f1 == 1.0


class TestScopePartialCredit:
    """Partial credit scoring per scope."""

    def test_partial_overlap_per_scope(self, sample_gold_labels, partial_report):
        # partial_report: det_001 matches gold_001 (intra_doc), det_002 partial with gold_002 (inter_doc)
        result = score_by_scope(partial_report, sample_gold_labels)
        scope_map = {sr.scope: sr for sr in result.per_scope}

        # intra_doc: exact match -> PCS=1.0
        assert scope_map["intra_doc"].partial_credit_score == 1.0

        # inter_doc: partial overlap (doc_C shared) -> Jaccard({doc_C,doc_X},{doc_C,doc_D})=1/3
        # one match out of 2 gold labels in inter_doc scope
        assert scope_map["inter_doc"].partial_credit_score == pytest.approx(1 / 3)


class TestScopeDeterminism:
    """Same inputs always produce identical results."""

    def test_deterministic(self, sample_gold_labels, perfect_report):
        r1 = score_by_scope(perfect_report, sample_gold_labels)
        r2 = score_by_scope(perfect_report, sample_gold_labels)
        assert r1 == r2

    def test_deterministic_partial(self, sample_gold_labels, partial_report):
        r1 = score_by_scope(partial_report, sample_gold_labels)
        r2 = score_by_scope(partial_report, sample_gold_labels)
        assert r1 == r2
