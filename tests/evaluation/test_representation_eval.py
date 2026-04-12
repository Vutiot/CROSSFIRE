"""Tests for Layer 1 representation quality evaluation."""

import pytest

from crossfire.evaluation.representation_eval import score_representation
from crossfire.shared.schemas.knowledge_graph import KnowledgeGraphClaim


def _make_claim(claim_id, subject, predicate, obj, source_doc, confidence=0.9):
    return KnowledgeGraphClaim(
        claim_id=claim_id,
        subject=subject,
        predicate=predicate,
        object=obj,
        source_document=source_doc,
        confidence=confidence,
    )


def _gold_claims():
    """Gold claims: 3 triples across 2 source documents."""
    return [
        _make_claim("g1", "Acme Corp", "manufactured", "Engine Model X", "doc_A"),
        _make_claim("g2", "Acme Corp", "located_in", "Denver", "doc_A"),
        _make_claim("g3", "Engine Model X", "has_hours", "12000", "doc_B"),
    ]


class TestRepresentationPerfectMatch:
    """System claims perfectly match gold claims."""

    def test_perfect_scores(self):
        gold = _gold_claims()
        system = [
            _make_claim("s1", "Acme Corp", "manufactured", "Engine Model X", "doc_A"),
            _make_claim("s2", "Acme Corp", "located_in", "Denver", "doc_A"),
            _make_claim("s3", "Engine Model X", "has_hours", "12000", "doc_B"),
        ]
        result = score_representation(system, gold)
        rq = result.representation_quality
        assert rq is not None
        assert rq.claim_coverage == 1.0
        assert rq.cross_reference_accuracy == 1.0

    def test_returns_evaluation_result(self):
        gold = _gold_claims()
        system = [_make_claim("s1", "Acme Corp", "manufactured", "Engine Model X", "doc_A")]
        result = score_representation(system, gold)
        assert result.representation_quality is not None
        # Layer 1 doesn't set detection metrics
        assert result.overall_precision == 0.0


class TestClaimCoverage:
    """Claim coverage metric."""

    def test_partial_coverage(self):
        gold = _gold_claims()
        # System covers 2 of 3 gold triples
        system = [
            _make_claim("s1", "Acme Corp", "manufactured", "Engine Model X", "doc_A"),
            _make_claim("s2", "Engine Model X", "has_hours", "12000", "doc_B"),
        ]
        result = score_representation(system, gold)
        assert result.representation_quality.claim_coverage == pytest.approx(2 / 3)

    def test_no_coverage(self):
        gold = _gold_claims()
        system = [
            _make_claim("s1", "Acme Corp", "wrong_predicate", "Engine Model X", "doc_A"),
        ]
        result = score_representation(system, gold)
        assert result.representation_quality.claim_coverage == 0.0

    def test_case_insensitive(self):
        gold = _gold_claims()
        system = [
            _make_claim("s1", "acme corp", "manufactured", "engine model x", "doc_A"),
            _make_claim("s2", "acme corp", "located_in", "denver", "doc_A"),
            _make_claim("s3", "engine model x", "has_hours", "12000", "doc_B"),
        ]
        result = score_representation(system, gold)
        assert result.representation_quality.claim_coverage == 1.0


class TestCrossReferenceAccuracy:
    """Cross-reference accuracy metric."""

    def test_all_correct_source_docs(self):
        gold = _gold_claims()
        system = [
            _make_claim("s1", "Acme Corp", "manufactured", "Engine Model X", "doc_A"),
            _make_claim("s2", "Acme Corp", "located_in", "Denver", "doc_A"),
            _make_claim("s3", "Engine Model X", "has_hours", "12000", "doc_B"),
        ]
        result = score_representation(system, gold)
        assert result.representation_quality.cross_reference_accuracy == 1.0

    def test_wrong_source_doc(self):
        gold = _gold_claims()
        # Right triple but wrong source document
        system = [
            _make_claim("s1", "Acme Corp", "manufactured", "Engine Model X", "doc_B"),  # wrong doc
        ]
        result = score_representation(system, gold)
        assert result.representation_quality.cross_reference_accuracy == 0.0

    def test_mixed_correct_and_wrong(self):
        gold = _gold_claims()
        system = [
            _make_claim("s1", "Acme Corp", "manufactured", "Engine Model X", "doc_A"),  # correct
            _make_claim("s2", "Acme Corp", "located_in", "Denver", "doc_B"),  # wrong doc
        ]
        result = score_representation(system, gold)
        assert result.representation_quality.cross_reference_accuracy == pytest.approx(0.5)


class TestRepresentationEdgeCases:
    """Edge cases: empty claim lists."""

    def test_both_empty(self):
        result = score_representation([], [])
        rq = result.representation_quality
        assert rq.claim_coverage == 0.0
        assert rq.cross_reference_accuracy == 0.0

    def test_empty_system(self):
        gold = _gold_claims()
        result = score_representation([], gold)
        assert result.representation_quality.claim_coverage == 0.0

    def test_empty_gold(self):
        system = [_make_claim("s1", "Acme", "made", "Widget", "doc_A")]
        result = score_representation(system, [])
        assert result.representation_quality.claim_coverage == 0.0


class TestRepresentationIndependence:
    """Layer 1 is independent from Layer 2 — no PipelineReport needed."""

    def test_no_pipeline_report_dependency(self):
        gold = _gold_claims()
        system = [_make_claim("s1", "Acme Corp", "manufactured", "Engine Model X", "doc_A")]
        result = score_representation(system, gold)
        assert result.representation_quality is not None
        assert result.per_scope == []
        assert result.per_stage == []


class TestRepresentationDeterminism:
    """Same inputs always produce identical results."""

    def test_deterministic(self):
        gold = _gold_claims()
        system = [
            _make_claim("s1", "Acme Corp", "manufactured", "Engine Model X", "doc_A"),
            _make_claim("s2", "Engine Model X", "has_hours", "12000", "doc_B"),
        ]
        r1 = score_representation(system, gold)
        r2 = score_representation(system, gold)
        assert r1 == r2
