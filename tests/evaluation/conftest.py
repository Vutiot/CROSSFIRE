"""Shared fixtures for evaluation tests."""

import pytest

from crossfire.shared.schemas.incoherences import IncoherenceLabel
from crossfire.shared.schemas.reports import DetectedIncoherence, PipelineReport


@pytest.fixture
def sample_gold_labels():
    """3 gold incoherence labels spanning different scopes."""
    return [
        IncoherenceLabel(
            id="gold_001",
            scope="intra_doc",
            mechanism="numeric_drift",
            detectability="single_hop",
            system_affinity="balanced",
            document_references=["doc_A", "doc_B"],
            modified_fact="speed was 120 mph",
            original_fact="speed was 150 mph",
        ),
        IncoherenceLabel(
            id="gold_002",
            scope="intra_corpus",
            mechanism="entity_swap",
            detectability="multi_hop",
            system_affinity="graph_favoring",
            document_references=["doc_C", "doc_D"],
            modified_fact="Boeing 737",
            original_fact="Airbus A320",
        ),
        IncoherenceLabel(
            id="gold_003",
            scope="inter_corpus",
            mechanism="temporal_contradiction",
            detectability="entity_resolution_dependent",
            system_affinity="agentic_favoring",
            document_references=["doc_E", "doc_F"],
            modified_fact="incident on March 5",
            original_fact="incident on March 12",
        ),
    ]


def _make_report(detections: list[DetectedIncoherence]) -> PipelineReport:
    return PipelineReport(
        pipeline_mode="hybrid",
        corpus_path="/test/corpus",
        detections=detections,
        timestamp="2026-04-06T00:00:00",
    )


@pytest.fixture
def perfect_report():
    """Pipeline report that perfectly matches all 3 gold labels."""
    return _make_report(
        [
            DetectedIncoherence(
                id="det_001",
                evidence_references=["doc_A", "doc_B"],
                confidence=0.9,
                description="speed mismatch",
            ),
            DetectedIncoherence(
                id="det_002",
                evidence_references=["doc_C", "doc_D"],
                confidence=0.85,
                description="aircraft model swap",
            ),
            DetectedIncoherence(
                id="det_003",
                evidence_references=["doc_E", "doc_F"],
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
            DetectedIncoherence(
                id="det_001",
                evidence_references=["doc_A", "doc_B"],
                confidence=0.9,
                description="speed mismatch",
            ),
            DetectedIncoherence(
                id="det_002",
                evidence_references=["doc_C", "doc_X"],
                confidence=0.7,
                description="partial overlap with gold_002",
            ),
            DetectedIncoherence(
                id="det_003",
                evidence_references=["doc_Z", "doc_W"],
                confidence=0.6,
                description="false positive",
            ),
        ]
    )


@pytest.fixture
def empty_report():
    """Pipeline report with no detections."""
    return _make_report([])
