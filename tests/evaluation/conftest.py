"""Shared fixtures for evaluation tests."""

import pytest

from crossfire.shared.schemas.contradictions import ContradictionLabel
from crossfire.shared.schemas.reports import DetectedContradiction, PipelineReport


@pytest.fixture
def sample_gold_labels():
    """3 gold contradiction labels spanning different scopes and detectabilities."""
    return [
        ContradictionLabel(
            scope="intra_doc",
            mechanism="numeric_drift",
            detectability="single_hop",
            system_affinity="balanced",
            difficulty="easy",
            char_start=0,
            char_end=20,
            original_text="speed was 150 mph",
            modified_text="speed was 120 mph",
            rationale="Numeric value changed",
            ground_truth=True,
            document_references=["doc_A", "doc_B"],
        ),
        ContradictionLabel(
            scope="inter_doc",
            mechanism="entity_swap",
            detectability="multi_hop",
            system_affinity="graph_favoring",
            difficulty="medium",
            char_start=0,
            char_end=15,
            original_text="Airbus A320",
            modified_text="Boeing 737",
            rationale="Aircraft model swapped",
            ground_truth=True,
            document_references=["doc_C", "doc_D"],
        ),
        ContradictionLabel(
            scope="inter_doc",
            mechanism="temporal_contradiction",
            detectability="entity_resolution_dependent",
            system_affinity="agentic_favoring",
            difficulty="hard",
            char_start=0,
            char_end=25,
            original_text="incident on March 12",
            modified_text="incident on March 5",
            rationale="Date changed",
            ground_truth=True,
            document_references=["doc_E", "doc_F"],
        ),
    ]


def _make_report(detections: list[DetectedContradiction]) -> PipelineReport:
    return PipelineReport(
        pipeline_mode="hybrid",
        case_dir="/test/case",
        detections=detections,
        timestamp="2026-04-06T00:00:00",
    )


@pytest.fixture
def perfect_report():
    """Pipeline report that perfectly matches all 3 gold labels."""
    return _make_report(
        [
            DetectedContradiction(
                scope="inter_doc",
                document_references=["doc_A", "doc_B"],
                text_span_start=0,
                text_span_end=20,
                evidence_text="speed mismatch",
                confidence=0.9,
                description="speed mismatch",
            ),
            DetectedContradiction(
                scope="inter_doc",
                document_references=["doc_C", "doc_D"],
                text_span_start=0,
                text_span_end=15,
                evidence_text="aircraft model swap",
                confidence=0.85,
                description="aircraft model swap",
            ),
            DetectedContradiction(
                scope="inter_doc",
                document_references=["doc_E", "doc_F"],
                text_span_start=0,
                text_span_end=25,
                evidence_text="date contradiction",
                confidence=0.8,
                description="date contradiction",
            ),
        ]
    )


@pytest.fixture
def partial_report():
    """1 exact match (gold_001), 1 partial overlap (shares doc_C), 1 FP, misses gold_003."""
    return _make_report(
        [
            DetectedContradiction(
                scope="inter_doc",
                document_references=["doc_A", "doc_B"],
                text_span_start=0,
                text_span_end=20,
                evidence_text="speed mismatch",
                confidence=0.9,
                description="speed mismatch",
            ),
            DetectedContradiction(
                scope="inter_doc",
                document_references=["doc_C", "doc_X"],
                text_span_start=0,
                text_span_end=15,
                evidence_text="partial overlap with gold_002",
                confidence=0.7,
                description="partial overlap with gold_002",
            ),
            DetectedContradiction(
                scope="inter_doc",
                document_references=["doc_Z", "doc_W"],
                text_span_start=0,
                text_span_end=10,
                evidence_text="false positive",
                confidence=0.6,
                description="false positive",
            ),
        ]
    )


@pytest.fixture
def empty_report():
    """Pipeline report with no detections."""
    return _make_report([])
