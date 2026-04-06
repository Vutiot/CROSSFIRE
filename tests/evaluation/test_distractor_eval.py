"""Tests for distractor false positive evaluation."""

import pytest

from crossfire.evaluation.distractor_eval import score_distractors
from crossfire.shared.schemas.incoherences import DistractorLabel
from crossfire.shared.schemas.reports import DetectedIncoherence, PipelineReport


def _make_report(detections):
    return PipelineReport(
        pipeline_mode="hybrid",
        corpus_path="/test",
        detections=detections,
        timestamp="2026-04-06T00:00:00",
    )


def _make_distractors():
    """3 distractor labels."""
    return [
        DistractorLabel(
            id="dist_001",
            scope="intra_doc",
            document_references=["doc_A", "doc_B"],
            divergence_type="expert_opinion",
            description="Differing expert assessments",
        ),
        DistractorLabel(
            id="dist_002",
            scope="intra_corpus",
            document_references=["doc_C", "doc_D"],
            divergence_type="methodology",
            description="Different measurement methods",
        ),
        DistractorLabel(
            id="dist_003",
            scope="inter_corpus",
            document_references=["doc_E", "doc_F"],
            divergence_type="preliminary_vs_final",
            description="Preliminary vs final report",
        ),
    ]


class TestDistractorAllFlagged:
    """All distractors incorrectly flagged as incoherences."""

    def test_fpr_one(self):
        distractors = _make_distractors()
        report = _make_report(
            [
                DetectedIncoherence(
                    id="d1",
                    evidence_references=["doc_A", "doc_B"],
                    confidence=0.9,
                    description="flagged dist_001",
                ),
                DetectedIncoherence(
                    id="d2",
                    evidence_references=["doc_C", "doc_D"],
                    confidence=0.8,
                    description="flagged dist_002",
                ),
                DetectedIncoherence(
                    id="d3",
                    evidence_references=["doc_E", "doc_F"],
                    confidence=0.7,
                    description="flagged dist_003",
                ),
            ]
        )
        result = score_distractors(report, distractors)
        assert result.distractor_false_positive_rate == 1.0


class TestDistractorNoneFlagged:
    """No distractors flagged — perfect distractor rejection."""

    def test_fpr_zero(self):
        distractors = _make_distractors()
        report = _make_report(
            [
                DetectedIncoherence(
                    id="d1",
                    evidence_references=["doc_X", "doc_Y"],
                    confidence=0.9,
                    description="unrelated detection",
                ),
            ]
        )
        result = score_distractors(report, distractors)
        assert result.distractor_false_positive_rate == 0.0


class TestDistractorPartialFlagging:
    """Some distractors flagged."""

    def test_partial_fpr(self):
        distractors = _make_distractors()
        report = _make_report(
            [
                DetectedIncoherence(
                    id="d1",
                    evidence_references=["doc_A", "doc_B"],
                    confidence=0.9,
                    description="flagged dist_001",
                ),
            ]
        )
        result = score_distractors(report, distractors)
        assert result.distractor_false_positive_rate == pytest.approx(1 / 3)

    def test_doc_ref_order_independent(self):
        distractors = _make_distractors()
        report = _make_report(
            [
                DetectedIncoherence(
                    id="d1",
                    evidence_references=["doc_B", "doc_A"],  # reversed
                    confidence=0.9,
                    description="flagged dist_001",
                ),
            ]
        )
        result = score_distractors(report, distractors)
        assert result.distractor_false_positive_rate == pytest.approx(1 / 3)


class TestDistractorEdgeCases:
    """Edge cases: empty report, empty distractors."""

    def test_empty_report(self):
        distractors = _make_distractors()
        result = score_distractors(_make_report([]), distractors)
        assert result.distractor_false_positive_rate == 0.0

    def test_empty_distractors(self):
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
        result = score_distractors(report, [])
        assert result.distractor_false_positive_rate == 0.0

    def test_both_empty(self):
        result = score_distractors(_make_report([]), [])
        assert result.distractor_false_positive_rate == 0.0

    def test_separate_from_detection_metrics(self):
        """FP rate is reported separately — overall P/R/F1 are 0.0."""
        distractors = _make_distractors()
        report = _make_report(
            [
                DetectedIncoherence(
                    id="d1",
                    evidence_references=["doc_A", "doc_B"],
                    confidence=0.9,
                    description="flagged",
                ),
            ]
        )
        result = score_distractors(report, distractors)
        assert result.overall_precision == 0.0
        assert result.overall_recall == 0.0
        assert result.overall_f1 == 0.0
        assert result.distractor_false_positive_rate is not None


class TestDistractorDeterminism:
    """Same inputs always produce identical results."""

    def test_deterministic(self):
        distractors = _make_distractors()
        report = _make_report(
            [
                DetectedIncoherence(
                    id="d1",
                    evidence_references=["doc_A", "doc_B"],
                    confidence=0.9,
                    description="flagged",
                ),
            ]
        )
        r1 = score_distractors(report, distractors)
        r2 = score_distractors(report, distractors)
        assert r1 == r2
