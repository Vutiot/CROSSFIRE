"""Tests for per-scope evaluation breakdown."""

import pytest

from crossfire.evaluation.scope_breakdown import score_by_scope
from crossfire.shared.schemas.incoherences import IncoherenceLabel
from crossfire.shared.schemas.reports import DetectedIncoherence, PipelineReport


def _make_report(detections):
    return PipelineReport(
        pipeline_mode="hybrid",
        corpus_path="/test",
        detections=detections,
        timestamp="2026-04-06T00:00:00",
    )


class TestScopePerfectMatch:
    """All detections match all gold labels — each scope gets 1.0."""

    def test_per_scope_perfect(self, sample_gold_labels, perfect_report):
        result = score_by_scope(perfect_report, sample_gold_labels)
        assert len(result.per_scope) == 3
        for sr in result.per_scope:
            # Each scope has 1 gold label matched by 1 detection out of 3 total
            # Precision = 1/3 (1 match among 3 detections for this scope's gold)
            # Recall = 1.0 (1 match / 1 gold in scope)
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
        assert scope_names == ["inter_corpus", "intra_corpus", "intra_doc"]


class TestScopeIndependence:
    """Missing detections in one scope doesn't affect other scopes."""

    def test_one_scope_missed(self, sample_gold_labels):
        # Only match intra_doc (doc_A, doc_B) — miss intra_corpus and inter_corpus
        report = _make_report(
            [
                DetectedIncoherence(
                    id="det_001",
                    evidence_references=["doc_A", "doc_B"],
                    confidence=0.9,
                    description="speed mismatch",
                ),
            ]
        )
        result = score_by_scope(report, sample_gold_labels)

        scope_map = {sr.scope: sr for sr in result.per_scope}

        # intra_doc: 1 detection matches 1 gold → recall=1.0, precision=1.0
        assert scope_map["intra_doc"].recall == 1.0
        assert scope_map["intra_doc"].precision == 1.0
        assert scope_map["intra_doc"].f1 == 1.0

        # intra_corpus: 0 matches / 1 gold → recall=0.0
        assert scope_map["intra_corpus"].recall == 0.0
        assert scope_map["intra_corpus"].f1 == 0.0

        # inter_corpus: 0 matches / 1 gold → recall=0.0
        assert scope_map["inter_corpus"].recall == 0.0
        assert scope_map["inter_corpus"].f1 == 0.0


class TestScopeAssignment:
    """Detection scope comes from gold label, not pipeline."""

    def test_detection_gets_gold_scope(self):
        # Two gold labels: one intra_doc, one inter_corpus — same doc refs
        # Detection matches both by doc refs, but greedy picks first
        gold = [
            IncoherenceLabel(
                id="g1",
                scope="intra_doc",
                mechanism="numeric_drift",
                detectability="single_hop",
                system_affinity="balanced",
                document_references=["a", "b"],
                modified_fact="x",
                original_fact="y",
            ),
            IncoherenceLabel(
                id="g2",
                scope="inter_corpus",
                mechanism="entity_swap",
                detectability="multi_hop",
                system_affinity="graph_favoring",
                document_references=["c", "d"],
                modified_fact="m",
                original_fact="n",
            ),
        ]
        report = _make_report(
            [
                DetectedIncoherence(
                    id="d1",
                    evidence_references=["a", "b"],
                    confidence=0.9,
                    description="match intra_doc",
                ),
                DetectedIncoherence(
                    id="d2",
                    evidence_references=["c", "d"],
                    confidence=0.8,
                    description="match inter_corpus",
                ),
            ]
        )
        result = score_by_scope(report, gold)
        scope_map = {sr.scope: sr for sr in result.per_scope}

        # Each scope has 1 gold matched by its detection
        assert scope_map["intra_doc"].recall == 1.0
        assert scope_map["inter_corpus"].recall == 1.0


class TestScopeEdgeCases:
    """Edge cases: empty report, empty gold, single scope."""

    def test_empty_report(self, sample_gold_labels, empty_report):
        result = score_by_scope(empty_report, sample_gold_labels)
        assert len(result.per_scope) == 3
        for sr in result.per_scope:
            assert sr.precision == 0.0
            assert sr.recall == 0.0
            assert sr.f1 == 0.0
            assert sr.partial_credit_score == 0.0

    def test_empty_gold(self):
        report = _make_report(
            [
                DetectedIncoherence(
                    id="d1",
                    evidence_references=["a", "b"],
                    confidence=0.9,
                    description="orphan",
                ),
            ]
        )
        result = score_by_scope(report, [])
        assert result.per_scope == []

    def test_single_scope_all_gold(self):
        gold = [
            IncoherenceLabel(
                id="g1",
                scope="intra_doc",
                mechanism="numeric_drift",
                detectability="single_hop",
                system_affinity="balanced",
                document_references=["a", "b"],
                modified_fact="x",
                original_fact="y",
            ),
            IncoherenceLabel(
                id="g2",
                scope="intra_doc",
                mechanism="entity_swap",
                detectability="multi_hop",
                system_affinity="graph_favoring",
                document_references=["c", "d"],
                modified_fact="m",
                original_fact="n",
            ),
        ]
        report = _make_report(
            [
                DetectedIncoherence(
                    id="d1",
                    evidence_references=["a", "b"],
                    confidence=0.9,
                    description="first",
                ),
                DetectedIncoherence(
                    id="d2",
                    evidence_references=["c", "d"],
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
        # partial_report: det_001 matches gold_001 (intra_doc), det_002 partial with gold_002 (intra_corpus)
        result = score_by_scope(partial_report, sample_gold_labels)
        scope_map = {sr.scope: sr for sr in result.per_scope}

        # intra_doc: exact match → PCS=1.0
        assert scope_map["intra_doc"].partial_credit_score == 1.0

        # intra_corpus: partial overlap (doc_C shared) → Jaccard({doc_C,doc_X},{doc_C,doc_D})=1/3
        assert scope_map["intra_corpus"].partial_credit_score == pytest.approx(1 / 3)

        # inter_corpus: no match → PCS=0.0
        assert scope_map["inter_corpus"].partial_credit_score == 0.0


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
