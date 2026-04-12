"""Tests for partial credit (localization proximity) scorer."""

import pytest

from crossfire.evaluation.partial_scorer import score_partial
from crossfire.shared.schemas.contradictions import ContradictionLabel
from crossfire.shared.schemas.reports import DetectedContradiction, PipelineReport


def _make_report(detections):
    return PipelineReport(
        pipeline_mode="hybrid",
        case_dir="/test",
        detections=detections,
        timestamp="2026-04-06T00:00:00",
    )


class TestPartialPerfectMatch:
    """All detections exactly match all gold labels (Jaccard = 1.0 each)."""

    def test_perfect_scores(self, sample_gold_labels, perfect_report):
        result = score_partial(perfect_report, sample_gold_labels)
        assert result.overall_precision == 1.0
        assert result.overall_recall == 1.0
        assert result.overall_f1 == 1.0
        assert result.overall_partial_credit_score == 1.0

    def test_returns_partial_credit_score(self, sample_gold_labels, perfect_report):
        result = score_partial(perfect_report, sample_gold_labels)
        assert result.overall_partial_credit_score is not None


class TestPartialNoOverlap:
    """No document reference overlap at all."""

    def test_no_overlap_all_zeros(self, sample_gold_labels):
        report = _make_report(
            [
                DetectedContradiction(
                    scope="inter_doc",
                    document_references=["doc_X", "doc_Y"],
                    text_span_start=0,
                    text_span_end=10,
                    evidence_text="unrelated",
                    confidence=0.9,
                    description="unrelated",
                ),
            ]
        )
        result = score_partial(report, sample_gold_labels)
        assert result.overall_precision == 0.0
        assert result.overall_recall == 0.0
        assert result.overall_f1 == 0.0
        assert result.overall_partial_credit_score == 0.0


class TestPartialCredit:
    """Partial overlap gives fractional credit."""

    def test_partial_overlap(self, sample_gold_labels, partial_report):
        # partial_report: det_001 matches gold_001 exactly (Jaccard=1.0)
        # det_002 has ["doc_C","doc_X"] vs gold_002 ["doc_C","doc_D"]
        #   Jaccard = |{doc_C}| / |{doc_C,doc_D,doc_X}| = 1/3
        # det_003 has ["doc_Z","doc_W"] — no overlap with any gold
        # Greedy assigns: det_001->gold_001 (1.0), det_002->gold_002 (1/3)
        # sum_sim = 1.0 + 1/3 = 4/3
        # precision = (4/3) / 3 detections = 4/9
        # recall = (4/3) / 3 gold = 4/9
        result = score_partial(partial_report, sample_gold_labels)
        assert result.overall_precision == pytest.approx(4 / 9)
        assert result.overall_recall == pytest.approx(4 / 9)
        expected_f1 = 2 * (4 / 9) * (4 / 9) / ((4 / 9) + (4 / 9))
        assert result.overall_f1 == pytest.approx(expected_f1)
        # PCS = mean of assigned similarities = (1.0 + 1/3) / 2 = 2/3
        assert result.overall_partial_credit_score == pytest.approx(2 / 3)

    def test_single_partial_overlap(self):
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
                document_references=["a", "b", "c"],
            ),
        ]
        report = _make_report(
            [
                DetectedContradiction(
                    scope="intra_doc",
                    document_references=["a", "b", "d"],
                    text_span_start=0,
                    text_span_end=10,
                    evidence_text="partial",
                    confidence=0.9,
                    description="partial",
                ),
            ]
        )
        result = score_partial(report, gold)
        # Jaccard({a,b,d}, {a,b,c}) = |{a,b}| / |{a,b,c,d}| = 2/4 = 0.5
        assert result.overall_precision == pytest.approx(0.5)
        assert result.overall_recall == pytest.approx(0.5)
        assert result.overall_partial_credit_score == pytest.approx(0.5)


class TestPartialEdgeCases:
    """Edge cases: empty report, empty gold, both empty."""

    def test_empty_report(self, sample_gold_labels, empty_report):
        result = score_partial(empty_report, sample_gold_labels)
        assert result.overall_precision == 0.0
        assert result.overall_recall == 0.0
        assert result.overall_f1 == 0.0
        assert result.overall_partial_credit_score == 0.0

    def test_empty_gold_labels(self, perfect_report):
        result = score_partial(perfect_report, [])
        assert result.overall_precision == 1.0
        assert result.overall_recall == 0.0
        assert result.overall_f1 == 0.0
        assert result.overall_partial_credit_score == 0.0

    def test_both_empty(self, empty_report):
        result = score_partial(empty_report, [])
        assert result.overall_precision == 0.0
        assert result.overall_recall == 0.0
        assert result.overall_f1 == 0.0
        assert result.overall_partial_credit_score == 0.0


class TestPartialOneToOne:
    """Greedy assignment prevents double-counting."""

    def test_duplicate_detections_greedy(self):
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
                    document_references=["a", "b"],
                    text_span_start=0,
                    text_span_end=10,
                    evidence_text="duplicate",
                    confidence=0.8,
                    description="duplicate",
                ),
            ]
        )
        result = score_partial(report, gold)
        # 1 gold matched by first detection (Jaccard=1.0), second unmatched
        # precision = 1.0 / 2 = 0.5
        # recall = 1.0 / 1 = 1.0
        assert result.overall_precision == 0.5
        assert result.overall_recall == 1.0
        assert result.overall_partial_credit_score == 1.0


class TestPartialDocRefOrder:
    """Document reference order should not matter."""

    def test_reversed_refs_still_match(self, sample_gold_labels):
        report = _make_report(
            [
                DetectedContradiction(
                    scope="inter_doc",
                    document_references=["doc_B", "doc_A"],
                    text_span_start=0,
                    text_span_end=20,
                    evidence_text="speed mismatch",
                    confidence=0.9,
                    description="speed mismatch",
                ),
            ]
        )
        result = score_partial(report, sample_gold_labels)
        # Jaccard({doc_A,doc_B}, {doc_A,doc_B}) = 1.0
        assert result.overall_precision == 1.0
        assert result.overall_recall == pytest.approx(1 / 3)
        assert result.overall_partial_credit_score == 1.0


class TestPartialDeterminism:
    """Same inputs always produce identical scores."""

    def test_deterministic_across_calls(self, sample_gold_labels, perfect_report):
        r1 = score_partial(perfect_report, sample_gold_labels)
        r2 = score_partial(perfect_report, sample_gold_labels)
        assert r1 == r2

    def test_deterministic_partial(self, sample_gold_labels, partial_report):
        r1 = score_partial(partial_report, sample_gold_labels)
        r2 = score_partial(partial_report, sample_gold_labels)
        assert r1 == r2
