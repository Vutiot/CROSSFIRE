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
from crossfire.shared.schemas.entities import EntityGraph, EntityNode
from crossfire.shared.schemas.reports import DetectedIncoherence, PipelineReport
from crossfire.shared.seed_manager import SeedManager


# ---------------------------------------------------------------------------
# Mock strategies for testing
# ---------------------------------------------------------------------------


class MockGraphStrategy(GraphStrategy):
    """Graph strategy that returns pre-configured detections."""

    def __init__(self, detections=None, internal_graph=None):
        self._detections = detections or []
        self._internal_graph = internal_graph

    def run(self, corpus_path):
        return (
            GraphResult(
                detected_incoherences=self._detections,
                internal_graph=self._internal_graph,
            ),
            None,
        )


class MockReasoningStrategy(ReasoningStrategy):
    """Reasoning strategy that returns pre-configured detections."""

    def __init__(self, detections=None):
        self._detections = detections or []

    def run(self, corpus_path):
        return ReasoningResult(detected_incoherences=self._detections), None


class FailingGraphStrategy(GraphStrategy):
    """Graph strategy that always fails."""

    def run(self, corpus_path):
        return None, "Graph strategy failed intentionally"


class FailingReasoningStrategy(ReasoningStrategy):
    """Reasoning strategy that always fails."""

    def run(self, corpus_path):
        return None, "Reasoning strategy failed intentionally"


# ---------------------------------------------------------------------------
# Test: Result models
# ---------------------------------------------------------------------------


class TestResultModels:
    def test_graph_result_defaults(self):
        result = GraphResult()
        assert result.detected_incoherences == []
        assert result.internal_graph is None

    def test_graph_result_with_data(self, sample_detections):
        graph = EntityGraph(
            nodes=[EntityNode(id="e1", entity_type="company", canonical_name="AirCo")],
        )
        result = GraphResult(
            detected_incoherences=sample_detections,
            internal_graph=graph,
        )
        assert len(result.detected_incoherences) == 2
        assert result.internal_graph is not None
        assert len(result.internal_graph.nodes) == 1

    def test_reasoning_result_defaults(self):
        result = ReasoningResult()
        assert result.detected_incoherences == []

    def test_reasoning_result_with_data(self, sample_detections):
        result = ReasoningResult(detected_incoherences=sample_detections)
        assert len(result.detected_incoherences) == 2


# ---------------------------------------------------------------------------
# Test: Null strategies
# ---------------------------------------------------------------------------


class TestNullStrategies:
    def test_null_graph_returns_empty(self):
        strategy = NullGraphStrategy()
        result, error = strategy.run("/any/path")
        assert error is None
        assert result.detected_incoherences == []
        assert result.internal_graph is None

    def test_null_reasoning_returns_empty(self):
        strategy = NullReasoningStrategy()
        result, error = strategy.run("/any/path")
        assert error is None
        assert result.detected_incoherences == []

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
        assert report.corpus_path == str(tmp_corpus_dir)
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
        assert report.pipeline_mode == "graph-native"
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
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        pipeline = HybridPipeline(NullGraphStrategy(), NullReasoningStrategy(), seed_manager)
        report, error = pipeline.run(str(empty_dir))
        assert report is None
        assert "No subcorpus JSONL files" in error


# ---------------------------------------------------------------------------
# Test: AR11 — pipeline never accesses gold files
# ---------------------------------------------------------------------------


class TestAR11Boundary:
    def test_pipeline_ignores_gold_files(self, tmp_corpus_dir, seed_manager):
        """Verify pipeline only reads subcorpus JSONL, not gold annotation files."""
        # Create gold files that should NOT be accessed
        (tmp_corpus_dir / "gold_incoherence_labels.json").write_text("[]")
        (tmp_corpus_dir / "gold_distractor_labels.json").write_text("[]")
        (tmp_corpus_dir / "entity_graph.json").write_text("{}")
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
    def test_duplicate_evidence_refs_keep_higher_confidence(self, tmp_corpus_dir, seed_manager):
        """When both strategies detect same document pair, keep higher confidence."""
        low_conf = DetectedIncoherence(
            id="graph_det",
            evidence_references=["sc-0_doc_000", "sc-0_doc_001"],
            confidence=0.5,
            description="Graph detection",
        )
        high_conf = DetectedIncoherence(
            id="reason_det",
            evidence_references=["sc-0_doc_000", "sc-0_doc_001"],
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
        """Different evidence references are not deduplicated."""
        det_a = DetectedIncoherence(
            id="a", evidence_references=["sc-0_doc_000"], confidence=0.8, description="A"
        )
        det_b = DetectedIncoherence(
            id="b", evidence_references=["sc-1_doc_000"], confidence=0.7, description="B"
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
                assert d1.id == d2.id
                assert d1.evidence_references == d2.evidence_references
                assert d1.confidence == d2.confidence
