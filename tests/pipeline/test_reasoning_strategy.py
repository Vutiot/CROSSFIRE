"""Tests for LLMReasoningStrategy — claim extraction and cross-checking."""

import json

import pytest

from crossfire.pipeline.hybrid_pipeline import HybridPipeline
from crossfire.pipeline.strategies.null_strategies import NullGraphStrategy
from crossfire.pipeline.strategies.reasoning_strategy import LLMReasoningStrategy
from crossfire.shared.schemas.reports import PipelineReport
from crossfire.shared.seed_manager import SeedManager


def _mock_llm(prompt, model="gpt-4o-mini", temperature=0, dry_run=False):
    """Mock LLM returning deterministic claim extraction and contradiction results."""
    if "Extract all atomic factual claims" in prompt:
        if "sc-0_doc_000" in prompt:
            return json.dumps([
                "The engine failed at 14:32 UTC",
                "The aircraft was a Boeing 737-800",
            ]), None
        if "sc-0_doc_001" in prompt:
            return json.dumps([
                "Smoke was observed from the left engine around 2:30 PM",
                "The aircraft was a Boeing 737-800",
            ]), None
        if "sc-1_doc_000" in prompt:
            return json.dumps([
                "Fatigue cracking was found in the turbine blade",
                "The engine had accumulated 12,000 flight hours",
            ]), None
        if "sc-1_doc_001" in prompt:
            return json.dumps([
                "FAA issued Airworthiness Directive 2025-NE-042",
                "The engine had accumulated 8,000 flight hours",
            ]), None
        return json.dumps(["Generic claim"]), None

    if "Compare the following two sets of claims" in prompt:
        # Return contradiction between sc-1 docs (flight hours mismatch)
        if "sc-1_doc_000" in prompt and "sc-1_doc_001" in prompt:
            return json.dumps([{
                "claim_a": "The engine had accumulated 12,000 flight hours",
                "claim_b": "The engine had accumulated 8,000 flight hours",
                "confidence": 0.92,
                "description": "Contradictory flight hour counts: 12,000 vs 8,000",
            }]), None
        return json.dumps([]), None

    return "[]", None


def _failing_llm(prompt, model="gpt-4o-mini", temperature=0, dry_run=False):
    """Mock LLM that always fails."""
    return None, "API error: service unavailable"


def _bad_json_llm(prompt, model="gpt-4o-mini", temperature=0, dry_run=False):
    """Mock LLM that returns invalid JSON."""
    return "not valid json {{{", None


class TestClaimExtraction:
    def test_extracts_claims_from_documents(self, tmp_corpus_dir, seed_manager):
        strategy = LLMReasoningStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, error = strategy.run(str(tmp_corpus_dir))
        assert error is None
        assert result is not None

    def test_produces_detected_incoherences(self, tmp_corpus_dir, seed_manager):
        strategy = LLMReasoningStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, error = strategy.run(str(tmp_corpus_dir))
        assert error is None
        # Should find the flight hours contradiction between sc-1 docs
        assert len(result.detected_incoherences) >= 1

    def test_detection_has_valid_fields(self, tmp_corpus_dir, seed_manager):
        strategy = LLMReasoningStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, _ = strategy.run(str(tmp_corpus_dir))
        for det in result.detected_incoherences:
            assert det.id.startswith("reasoning_")
            assert len(det.evidence_references) == 2
            assert 0.0 <= det.confidence <= 1.0
            assert det.description


class TestCrossChecking:
    def test_cross_checks_document_pairs(self, tmp_corpus_dir, seed_manager):
        strategy = LLMReasoningStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, _ = strategy.run(str(tmp_corpus_dir))
        # Find the specific contradiction we configured
        flight_hours = [
            d for d in result.detected_incoherences
            if "flight hour" in d.description.lower()
        ]
        assert len(flight_hours) == 1
        assert flight_hours[0].confidence == 0.92
        assert "sc-1_doc_000" in flight_hours[0].evidence_references
        assert "sc-1_doc_001" in flight_hours[0].evidence_references


class TestAgenticModeIntegration:
    def test_agentic_mode_with_hybrid_pipeline(self, tmp_corpus_dir, seed_manager):
        strategy = LLMReasoningStrategy(llm=_mock_llm, seed_manager=seed_manager)
        pipeline = HybridPipeline(NullGraphStrategy(), strategy, seed_manager)
        report, error = pipeline.run(str(tmp_corpus_dir))
        assert error is None
        assert isinstance(report, PipelineReport)
        assert report.pipeline_mode == "agentic"
        assert len(report.detections) >= 1


class TestErrorHandling:
    def test_llm_failure_returns_partial_results(self, tmp_corpus_dir, seed_manager):
        strategy = LLMReasoningStrategy(llm=_failing_llm, seed_manager=seed_manager)
        result, error = strategy.run(str(tmp_corpus_dir))
        # Strategy should handle LLM failures gracefully
        assert error is None
        assert result is not None
        assert result.detected_incoherences == []

    def test_bad_json_returns_partial_results(self, tmp_corpus_dir, seed_manager):
        strategy = LLMReasoningStrategy(llm=_bad_json_llm, seed_manager=seed_manager)
        result, error = strategy.run(str(tmp_corpus_dir))
        assert error is None
        assert result is not None
        assert result.detected_incoherences == []

    def test_nonexistent_path_returns_error(self, seed_manager):
        strategy = LLMReasoningStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, error = strategy.run("/nonexistent/path")
        assert result is None
        assert "not a directory" in error


class TestEmptyCorpus:
    def test_empty_dir_returns_empty_result(self, tmp_path, seed_manager):
        empty_dir = tmp_path / "empty_corpus"
        empty_dir.mkdir()
        strategy = LLMReasoningStrategy(llm=_mock_llm, seed_manager=seed_manager)
        result, error = strategy.run(str(empty_dir))
        assert error is None
        assert result.detected_incoherences == []
