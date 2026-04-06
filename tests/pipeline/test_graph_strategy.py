"""Tests for LLMGraphStrategy — KG construction and structural anomaly detection."""

import json

import pytest

from crossfire.pipeline.hybrid_pipeline import HybridPipeline
from crossfire.pipeline.strategies.graph_strategy import LLMGraphStrategy
from crossfire.pipeline.strategies.null_strategies import NullReasoningStrategy
from crossfire.shared.schemas.reports import PipelineReport
from crossfire.shared.seed_manager import SeedManager


def _mock_llm(prompt, model="gpt-4o-mini", temperature=0, dry_run=False):
    """Mock LLM for entity extraction and anomaly detection."""
    if "Extract all entities" in prompt:
        if "sc-0_doc_000" in prompt:
            return json.dumps({
                "entities": [
                    {"name": "Boeing 737-800", "type": "equipment", "attributes": {"flight_hours": "12000"}},
                    {"name": "Engine #1", "type": "component", "attributes": {"status": "failed"}},
                ],
                "relationships": [
                    {"source": "Engine #1", "target": "Boeing 737-800", "type": "installed_on"},
                ],
            }), None
        if "sc-0_doc_001" in prompt:
            return json.dumps({
                "entities": [
                    {"name": "Boeing 737-800", "type": "equipment", "attributes": {"flight_hours": "8000"}},
                ],
                "relationships": [],
            }), None
        if "sc-1_doc_000" in prompt:
            return json.dumps({
                "entities": [
                    {"name": "Turbine blade", "type": "component", "attributes": {}},
                ],
                "relationships": [],
            }), None
        if "sc-1_doc_001" in prompt:
            return json.dumps({
                "entities": [
                    {"name": "FAA", "type": "organization", "attributes": {}},
                ],
                "relationships": [],
            }), None
        return json.dumps({"entities": [], "relationships": []}), None

    if "Analyze the following knowledge graph" in prompt:
        return json.dumps([{
            "entity_or_relationship": "Boeing 737-800 flight_hours",
            "doc_a": "sc-0_doc_000",
            "doc_b": "sc-0_doc_001",
            "confidence": 0.88,
            "description": "Conflicting flight hours: 12000 vs 8000",
        }]), None

    return "[]", None


def _failing_llm(prompt, model="gpt-4o-mini", temperature=0, dry_run=False):
    return None, "API error"


class TestEntityExtraction:
    def test_extracts_entities_from_documents(self, tmp_corpus_dir, seed_manager):
        strategy = LLMGraphStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, error = strategy.run(str(tmp_corpus_dir))
        assert error is None
        assert result is not None
        assert result.internal_graph is not None
        assert len(result.internal_graph.nodes) > 0

    def test_builds_edges(self, tmp_corpus_dir, seed_manager):
        strategy = LLMGraphStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, _ = strategy.run(str(tmp_corpus_dir))
        assert len(result.internal_graph.edges) >= 1


class TestAnomalyDetection:
    def test_detects_anomalies(self, tmp_corpus_dir, seed_manager):
        strategy = LLMGraphStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, _ = strategy.run(str(tmp_corpus_dir))
        assert len(result.detected_incoherences) >= 1

    def test_detection_has_valid_fields(self, tmp_corpus_dir, seed_manager):
        strategy = LLMGraphStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, _ = strategy.run(str(tmp_corpus_dir))
        for det in result.detected_incoherences:
            assert det.id.startswith("graph_")
            assert len(det.evidence_references) >= 1
            assert 0.0 <= det.confidence <= 1.0
            assert det.description


class TestInternalGraphExposure:
    def test_exposes_internal_graph_for_layer1_eval(self, tmp_corpus_dir, seed_manager):
        strategy = LLMGraphStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, _ = strategy.run(str(tmp_corpus_dir))
        graph = result.internal_graph
        assert graph is not None
        # Should be convertible to NetworkX
        nx_graph = graph.to_networkx()
        assert nx_graph.number_of_nodes() > 0


class TestGraphNativeModeIntegration:
    def test_graph_native_mode_with_hybrid_pipeline(self, tmp_corpus_dir, seed_manager):
        strategy = LLMGraphStrategy(llm=_mock_llm, seed_manager=seed_manager)
        pipeline = HybridPipeline(strategy, NullReasoningStrategy(), seed_manager)
        report, error = pipeline.run(str(tmp_corpus_dir))
        assert error is None
        assert isinstance(report, PipelineReport)
        assert report.pipeline_mode == "graph-native"
        assert len(report.detections) >= 1


class TestErrorHandling:
    def test_llm_failure_returns_partial_results(self, tmp_corpus_dir, seed_manager):
        strategy = LLMGraphStrategy(llm=_failing_llm, seed_manager=seed_manager)
        result, error = strategy.run(str(tmp_corpus_dir))
        assert error is None
        assert result is not None
        assert result.internal_graph is not None

    def test_nonexistent_path_returns_error(self, seed_manager):
        strategy = LLMGraphStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, error = strategy.run("/nonexistent/path")
        assert result is None
        assert "not a directory" in error

    def test_empty_corpus_returns_empty(self, tmp_path, seed_manager):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        strategy = LLMGraphStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, error = strategy.run(str(empty_dir))
        assert error is None
        assert result.detected_incoherences == []
