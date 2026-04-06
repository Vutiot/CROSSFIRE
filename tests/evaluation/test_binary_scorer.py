"""Tests for binary (exact match) scorer."""

import pytest

from crossfire.evaluation.binary_scorer import score_binary
from crossfire.shared.schemas.incoherences import IncoherenceLabel
from crossfire.shared.schemas.reports import DetectedIncoherence, PipelineReport


def _make_report(detections):
    return PipelineReport(
        pipeline_mode="hybrid",
        corpus_path="/test",
        detections=detections,
        timestamp="2026-04-06T00:00:00",
    )


class TestBinaryPerfectMatch:
    """All detections match all gold labels exactly."""

    def test_perfect_precision_recall_f1(self, sample_gold_labels, perfect_report):
        result = score_binary(perfect_report, sample_gold_labels)
        assert result.overall_precision == 1.0
        assert result.overall_recall == 1.0
        assert result.overall_f1 == 1.0

    def test_returns_evaluation_result(self, sample_gold_labels, perfect_report):
        result = score_binary(perfect_report, sample_gold_labels)
        assert result.overall_partial_credit_score is None


class TestBinaryNoOverlap:
    """Detections and gold labels have no matching document references."""

    def test_no_overlap_all_zeros(self, sample_gold_labels):
        report = _make_report(
            [
                DetectedIncoherence(
                    id="det_x",
                    evidence_references=["doc_X", "doc_Y"],
                    confidence=0.9,
                    description="unrelated",
                ),
            ]
        )
        result = score_binary(report, sample_gold_labels)
        assert result.overall_precision == 0.0
        assert result.overall_recall == 0.0
        assert result.overall_f1 == 0.0


class TestBinaryPartialMatch:
    """Some detections match, some don't."""

    def test_one_of_three_matched(self, sample_gold_labels, partial_report):
        result = score_binary(partial_report, sample_gold_labels)
        # 1 match out of 3 detections and 3 gold labels
        assert result.overall_precision == pytest.approx(1 / 3)
        assert result.overall_recall == pytest.approx(1 / 3)
        assert result.overall_f1 == pytest.approx(1 / 3)


class TestBinaryEdgeCases:
    """Edge cases: empty report, empty gold, both empty."""

    def test_empty_report(self, sample_gold_labels, empty_report):
        result = score_binary(empty_report, sample_gold_labels)
        assert result.overall_precision == 0.0
        assert result.overall_recall == 0.0
        assert result.overall_f1 == 0.0

    def test_empty_gold_labels(self, perfect_report):
        result = score_binary(perfect_report, [])
        assert result.overall_precision == 1.0
        assert result.overall_recall == 0.0
        assert result.overall_f1 == 0.0

    def test_both_empty(self, empty_report):
        result = score_binary(empty_report, [])
        assert result.overall_precision == 0.0
        assert result.overall_recall == 0.0
        assert result.overall_f1 == 0.0


class TestBinaryDocRefOrder:
    """Document reference order should not matter."""

    def test_reversed_refs_still_match(self, sample_gold_labels):
        report = _make_report(
            [
                DetectedIncoherence(
                    id="det_001",
                    evidence_references=["doc_B", "doc_A"],  # reversed
                    confidence=0.9,
                    description="speed mismatch",
                ),
            ]
        )
        result = score_binary(report, sample_gold_labels)
        assert result.overall_precision == 1.0
        assert result.overall_recall == pytest.approx(1 / 3)


class TestBinaryOneToOne:
    """Each gold label can be matched at most once."""

    def test_duplicate_detections_count_once(self):
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
                    evidence_references=["a", "b"],
                    confidence=0.8,
                    description="duplicate",
                ),
            ]
        )
        result = score_binary(report, gold)
        # Only 1 gold label, so only 1 match despite 2 detections
        assert result.overall_precision == 0.5  # 1 match / 2 detections
        assert result.overall_recall == 1.0  # 1 match / 1 gold
        assert result.overall_f1 == pytest.approx(2 / 3)


class TestBinaryDeterminism:
    """Same inputs always produce identical scores."""

    def test_deterministic_across_calls(self, sample_gold_labels, perfect_report):
        r1 = score_binary(perfect_report, sample_gold_labels)
        r2 = score_binary(perfect_report, sample_gold_labels)
        assert r1 == r2

    def test_deterministic_partial(self, sample_gold_labels, partial_report):
        r1 = score_binary(partial_report, sample_gold_labels)
        r2 = score_binary(partial_report, sample_gold_labels)
        assert r1 == r2
