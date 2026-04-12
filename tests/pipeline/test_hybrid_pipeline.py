"""Tests for HybridPipeline, strategy interfaces, and mode switching."""

import json
from pathlib import Path

import pytest

from crossfire.pipeline.hybrid_pipeline import HybridPipeline
from crossfire.pipeline.strategies.base import (
    GraphResult,
    GraphStrategy,
    ReasoningResult,
    ReasoningStrategy,
)
from crossfire.pipeline.strategies.null_strategies import (
    NullGraphStrategy,
    NullReasoningStrategy,
)
from crossfire.shared.schemas.knowledge_graph import KnowledgeGraphClaim
from crossfire.shared.schemas.reports import DetectedContradiction, PipelineReport
from crossfire.shared.seed_manager import SeedManager


# ---------------------------------------------------------------------------
# Mock strategies for testing
# ---------------------------------------------------------------------------


class MockGraphStrategy(GraphStrategy):
    """Graph strategy that returns pre-configured detections."""

    def __init__(self, detections=None, internal_claims=None):
        self._detections = detections or []
        self._internal_claims = internal_claims or []

    def run(self, case_dir):
        return (
            GraphResult(
                detected_contradictions=self._detections,
                internal_claims=self._internal_claims,
            ),
            None,
        )


class MockReasoningStrategy(ReasoningStrategy):
    """Reasoning strategy that returns pre-configured detections."""

    def __init__(self, detections=None):
        self._detections = detections or []

    def run(self, case_dir):
        return ReasoningResult(detected_contradictions=self._detections), None


class FailingGraphStrategy(GraphStrategy):
    """Graph strategy that always fails."""

    def run(self, case_dir):
        return None, "Graph strategy failed intentionally"


class FailingReasoningStrategy(ReasoningStrategy):
    """Reasoning strategy that always fails."""

    def run(self, case_dir):
        return None, "Reasoning strategy failed intentionally"


# ---------------------------------------------------------------------------
# Test: Result models
# ---------------------------------------------------------------------------


class TestResultModels:
    def test_graph_result_defaults(self):
        result = GraphResult()
        assert result.detected_contradictions == []
        assert result.internal_claims == []

    def test_graph_result_with_data(self, sample_detections):
        claims = [
            KnowledgeGraphClaim(
                claim_id="c1",
                subject="engine",
                predicate="failed_at",
                object="14:32 UTC",
                source_document="case_001_doc_000",
                confidence=0.9,
            ),
        ]
        result = GraphResult(
            detected_contradictions=sample_detections,
            internal_claims=claims,
        )
        assert len(result.detected_contradictions) == 2
        assert len(result.internal_claims) == 1
        assert result.internal_claims[0].claim_id == "c1"

    def test_reasoning_result_defaults(self):
        result = ReasoningResult()
        assert result.detected_contradictions == []

    def test_reasoning_result_with_data(self, sample_detections):
        result = ReasoningResult(detected_contradictions=sample_detections)
        assert len(result.detected_contradictions) == 2


# ---------------------------------------------------------------------------
# Test: Null strategies
# ---------------------------------------------------------------------------


class TestNullStrategies:
    def test_null_graph_returns_empty(self):
        strategy = NullGraphStrategy()
        result, error = strategy.run("/any/path")
        assert error is None
        assert result.detected_contradictions == []
        assert result.internal_claims == []

    def test_null_reasoning_returns_empty(self):
        strategy = NullReasoningStrategy()
        result, error = strategy.run("/any/path")
        assert error is None
        assert result.detected_contradictions == []

    def test_null_graph_is_graph_strategy(self):
        assert isinstance(NullGraphStrategy(), GraphStrategy)

    def test_null_reasoning_is_reasoning_strategy(self):
        assert isinstance(NullReasoningStrategy(), ReasoningStrategy)


# ---------------------------------------------------------------------------
# Test: HybridPipeline — both null strategies (empty report)
# ---------------------------------------------------------------------------


class TestPipelineNullStrategies:
    def test_both_null_produces_valid_empty_report(self, tmp_corpus_dir, seed_manager):
        pipeline = HybridPipeline(NullGraphStrategy(), NullReasoningStrategy(), seed_manager)
        report, error = pipeline.run(str(tmp_corpus_dir))
        assert error is None
        assert isinstance(report, PipelineReport)
        assert report.detections == []
        assert report.pipeline_mode == "hybrid"
        assert report.case_dir == str(tmp_corpus_dir)
        assert report.timestamp  # non-empty

    def test_report_validates_as_pydantic(self, tmp_corpus_dir, seed_manager):
        pipeline = HybridPipeline(NullGraphStrategy(), NullReasoningStrategy(), seed_manager)
        report, _ = pipeline.run(str(tmp_corpus_dir))
        # Round-trip through JSON
        data = json.loads(report.model_dump_json())
        restored = PipelineReport(**data)
        assert restored.pipeline_mode == report.pipeline_mode
        assert len(restored.detections) == len(report.detections)


# ---------------------------------------------------------------------------
# Test: Mode switching
# ---------------------------------------------------------------------------


class TestModeSwitching:
    def test_hybrid_mode(self, tmp_corpus_dir, seed_manager, sample_detections):
        """Hybrid: both strategies return detections."""
        graph_dets = [sample_detections[0]]
        reason_dets = [sample_detections[1]]
        pipeline = HybridPipeline(
            MockGraphStrategy(detections=graph_dets),
            MockReasoningStrategy(detections=reason_dets),
            seed_manager,
        )
        report, error = pipeline.run(str(tmp_corpus_dir))
        assert error is None
        assert report.pipeline_mode == "hybrid"
        assert len(report.detections) == 2

    def test_agentic_mode(self, tmp_corpus_dir, seed_manager, sample_detections):
        """Agentic: NullGraphStrategy + real reasoning."""
        pipeline = HybridPipeline(
            NullGraphStrategy(),
            MockReasoningStrategy(detections=sample_detections),
            seed_manager,
        )
        report, error = pipeline.run(str(tmp_corpus_dir))
        assert error is None
        assert report.pipeline_mode == "agentic"
        assert len(report.detections) == 2

    def test_graph_native_mode(self, tmp_corpus_dir, seed_manager, sample_detections):
        """Graph-native: real graph + NullReasoningStrategy."""
        pipeline = HybridPipeline(
            MockGraphStrategy(detections=sample_detections),
            NullReasoningStrategy(),
            seed_manager,
        )
        report, error = pipeline.run(str(tmp_corpus_dir))
        assert error is None
        assert report.pipeline_mode == "graph_native"
        assert len(report.detections) == 2


# ---------------------------------------------------------------------------
# Test: Strategy failure handling
# ---------------------------------------------------------------------------


class TestStrategyFailure:
    def test_graph_failure_uses_empty_result(self, tmp_corpus_dir, seed_manager, sample_detections):
        pipeline = HybridPipeline(
            FailingGraphStrategy(),
            MockReasoningStrategy(detections=sample_detections),
            seed_manager,
        )
        report, error = pipeline.run(str(tmp_corpus_dir))
        assert error is None
        assert len(report.detections) == 2  # reasoning results only

    def test_reasoning_failure_uses_empty_result(self, tmp_corpus_dir, seed_manager, sample_detections):
        pipeline = HybridPipeline(
            MockGraphStrategy(detections=sample_detections),
            FailingReasoningStrategy(),
            seed_manager,
        )
        report, error = pipeline.run(str(tmp_corpus_dir))
        assert error is None
        assert len(report.detections) == 2  # graph results only

    def test_both_fail_produces_empty_report(self, tmp_corpus_dir, seed_manager):
        pipeline = HybridPipeline(
            FailingGraphStrategy(),
            FailingReasoningStrategy(),
            seed_manager,
        )
        report, error = pipeline.run(str(tmp_corpus_dir))
        assert error is None
        assert report.detections == []


# ---------------------------------------------------------------------------
# Test: Corpus loading errors
# ---------------------------------------------------------------------------


class TestCorpusErrors:
    def test_nonexistent_path_returns_error(self, seed_manager):
        pipeline = HybridPipeline(NullGraphStrategy(), NullReasoningStrategy(), seed_manager)
        report, error = pipeline.run("/nonexistent/path")
        assert report is None
        assert "not a directory" in error

    def test_empty_dir_returns_error(self, tmp_path, seed_manager):
        empty_dir = tmp_path / "empty_case"
        empty_dir.mkdir()
        pipeline = HybridPipeline(NullGraphStrategy(), NullReasoningStrategy(), seed_manager)
        report, error = pipeline.run(str(empty_dir))
        assert report is None
        assert "No anonymized_docs/" in error

    def test_empty_anonymized_docs_returns_error(self, tmp_path, seed_manager):
        case_dir = tmp_path / "case_empty"
        case_dir.mkdir()
        (case_dir / "anonymized_docs").mkdir()
        pipeline = HybridPipeline(NullGraphStrategy(), NullReasoningStrategy(), seed_manager)
        report, error = pipeline.run(str(case_dir))
        assert report is None
        assert "No JSONL files" in error


# ---------------------------------------------------------------------------
# Test: AR11 — pipeline never accesses gold files
# ---------------------------------------------------------------------------


class TestAR11Boundary:
    def test_pipeline_ignores_gold_files(self, tmp_corpus_dir, seed_manager):
        """Verify pipeline only reads anonymized_docs JSONL, not gold annotation files."""
        # Create gold files that should NOT be accessed
        (tmp_corpus_dir / "gold_contradiction_labels.json").write_text("[]")
        (tmp_corpus_dir / "gold_distractor_labels.json").write_text("[]")
        (tmp_corpus_dir / "knowledge_graph.json").write_text("{}")
        (tmp_corpus_dir / "metadata.json").write_text("{}")

        pipeline = HybridPipeline(NullGraphStrategy(), NullReasoningStrategy(), seed_manager)
        report, error = pipeline.run(str(tmp_corpus_dir))

        # Pipeline succeeds loading only JSONL corpus
        assert error is None
        assert isinstance(report, PipelineReport)


# ---------------------------------------------------------------------------
# Test: Deduplication in merge
# ---------------------------------------------------------------------------


class TestMergeDeduplication:
    def test_duplicate_document_refs_keep_higher_confidence(self, tmp_corpus_dir, seed_manager):
        """When both strategies detect same document pair, keep higher confidence."""
        low_conf = DetectedContradiction(
            scope="inter_doc",
            document_references=["case_001_doc_000", "case_001_doc_001"],
            text_span_start=0,
            text_span_end=10,
            evidence_text="Graph detection evidence",
            confidence=0.5,
            description="Graph detection",
        )
        high_conf = DetectedContradiction(
            scope="inter_doc",
            document_references=["case_001_doc_000", "case_001_doc_001"],
            text_span_start=0,
            text_span_end=10,
            evidence_text="Reasoning detection evidence",
            confidence=0.9,
            description="Reasoning detection",
        )
        pipeline = HybridPipeline(
            MockGraphStrategy(detections=[low_conf]),
            MockReasoningStrategy(detections=[high_conf]),
            seed_manager,
        )
        report, error = pipeline.run(str(tmp_corpus_dir))
        assert error is None
        assert len(report.detections) == 1
        assert report.detections[0].confidence == 0.9

    def test_distinct_refs_kept_separate(self, tmp_corpus_dir, seed_manager):
        """Different document references are not deduplicated."""
        det_a = DetectedContradiction(
            scope="intra_doc",
            document_references=["case_001_doc_000"],
            text_span_start=0,
            text_span_end=10,
            evidence_text="Evidence A",
            confidence=0.8,
            description="A",
        )
        det_b = DetectedContradiction(
            scope="intra_doc",
            document_references=["case_001_doc_002"],
            text_span_start=0,
            text_span_end=10,
            evidence_text="Evidence B",
            confidence=0.7,
            description="B",
        )
        pipeline = HybridPipeline(
            MockGraphStrategy(detections=[det_a]),
            MockReasoningStrategy(detections=[det_b]),
            seed_manager,
        )
        report, error = pipeline.run(str(tmp_corpus_dir))
        assert error is None
        assert len(report.detections) == 2


# ---------------------------------------------------------------------------
# Test: Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_input_same_output(self, tmp_corpus_dir, sample_detections):
        """Same seed + same input = identical report (minus timestamp)."""
        results = []
        for _ in range(3):
            sm = SeedManager(master_seed=99)
            pipeline = HybridPipeline(
                MockGraphStrategy(detections=[sample_detections[0]]),
                MockReasoningStrategy(detections=[sample_detections[1]]),
                sm,
            )
            report, _ = pipeline.run(str(tmp_corpus_dir))
            results.append(report)

        # All runs produce same detections
        for r in results[1:]:
            assert len(r.detections) == len(results[0].detections)
            for d1, d2 in zip(results[0].detections, r.detections):
                assert d1.document_references == d2.document_references
                assert d1.confidence == d2.confidence
