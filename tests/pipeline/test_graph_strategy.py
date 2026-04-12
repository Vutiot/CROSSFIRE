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
        if "case_001_doc_000" in prompt:
            return json.dumps({
                "claims": [
                    {"subject": "Boeing 737-800", "predicate": "has_flight_hours", "object": "12000", "confidence": 0.9},
                    {"subject": "Engine #1", "predicate": "status", "object": "failed", "confidence": 0.95},
                ],
                "relationships": [
                    {"source": "Engine #1", "target": "Boeing 737-800", "type": "installed_on"},
                ],
            }), None
        if "case_001_doc_001" in prompt:
            return json.dumps({
                "claims": [
                    {"subject": "Boeing 737-800", "predicate": "has_flight_hours", "object": "8000", "confidence": 0.85},
                ],
                "relationships": [],
            }), None
        if "case_001_doc_002" in prompt:
            return json.dumps({
                "claims": [
                    {"subject": "Turbine blade", "predicate": "condition", "object": "fatigue cracking", "confidence": 0.9},
                ],
                "relationships": [],
            }), None
        if "case_001_doc_003" in prompt:
            return json.dumps({
                "claims": [
                    {"subject": "Engine", "predicate": "maintenance", "object": "overhaul completed", "confidence": 0.8},
                ],
                "relationships": [],
            }), None
        return json.dumps({"claims": [], "relationships": []}), None

    if "Analyze the following knowledge graph" in prompt:
        return json.dumps([{
            "entity_or_relationship": "Boeing 737-800 flight_hours",
            "doc_a": "case_001_doc_000",
            "doc_b": "case_001_doc_001",
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
        assert len(result.internal_claims) > 0

    def test_builds_claims(self, tmp_corpus_dir, seed_manager):
        strategy = LLMGraphStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, _ = strategy.run(str(tmp_corpus_dir))
        assert len(result.internal_claims) >= 4


class TestAnomalyDetection:
    def test_detects_anomalies(self, tmp_corpus_dir, seed_manager):
        strategy = LLMGraphStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, _ = strategy.run(str(tmp_corpus_dir))
        assert len(result.detected_contradictions) >= 1

    def test_detection_has_valid_fields(self, tmp_corpus_dir, seed_manager):
        strategy = LLMGraphStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, _ = strategy.run(str(tmp_corpus_dir))
        for det in result.detected_contradictions:
            assert len(det.document_references) >= 1
            assert 0.0 <= det.confidence <= 1.0
            assert det.description


class TestInternalClaimsExposure:
    def test_exposes_internal_claims_for_layer1_eval(self, tmp_corpus_dir, seed_manager):
        strategy = LLMGraphStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, _ = strategy.run(str(tmp_corpus_dir))
        assert len(result.internal_claims) > 0
        # Claims should have proper structure
        for claim in result.internal_claims:
            assert claim.claim_id
            assert claim.subject
            assert claim.source_document


class TestGraphNativeModeIntegration:
    def test_graph_native_mode_with_hybrid_pipeline(self, tmp_corpus_dir, seed_manager):
        strategy = LLMGraphStrategy(llm=_mock_llm, seed_manager=seed_manager)
        pipeline = HybridPipeline(strategy, NullReasoningStrategy(), seed_manager)
        report, error = pipeline.run(str(tmp_corpus_dir))
        assert error is None
        assert isinstance(report, PipelineReport)
        assert report.pipeline_mode == "graph_native"
        assert len(report.detections) >= 1


class TestErrorHandling:
    def test_llm_failure_returns_partial_results(self, tmp_corpus_dir, seed_manager):
        strategy = LLMGraphStrategy(llm=_failing_llm, seed_manager=seed_manager)
        result, error = strategy.run(str(tmp_corpus_dir))
        assert error is None
        assert result is not None
        # With all LLM calls failing, claims list should be empty
        assert result.internal_claims == []

    def test_nonexistent_path_returns_error(self, seed_manager):
        strategy = LLMGraphStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, error = strategy.run("/nonexistent/path")
        assert result is None
        assert "not a directory" in error

    def test_empty_corpus_returns_empty(self, tmp_path, seed_manager):
        empty_dir = tmp_path / "empty_case"
        empty_dir.mkdir()
        (empty_dir / "anonymized_docs").mkdir()
        strategy = LLMGraphStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, error = strategy.run(str(empty_dir))
        assert error is None
        assert result.detected_contradictions == []
