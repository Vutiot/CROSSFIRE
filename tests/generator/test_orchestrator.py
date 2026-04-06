"""Tests for the corpus generator orchestrator."""

import json
from pathlib import Path

import pytest

from crossfire.generator.orchestrator import generate_corpus, _build_doc_type_sequence
from crossfire.shared.schemas.config import (
    DetectabilityDistribution,
    GeneratorConfig,
    IncoherenceConfig,
    ScopeDistribution,
)
from crossfire.shared.schemas.corpus import Document
from crossfire.shared.seed_manager import SeedManager


def _mock_llm(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0, dry_run: bool = False):
    """Mock LLM that returns a short document."""
    if dry_run:
        return "Dry-run estimate: ~500 tokens, ~$0.0001", None
    return (
        "FACTUAL REPORT\n\n"
        "1. ACCIDENT INFORMATION\n\n"
        "The aircraft experienced an incident during routine operations. "
        "The investigation found multiple contributing factors including "
        "equipment malfunction and procedural deficiencies. "
        "The FAA issued safety recommendations following the investigation."
    ), None


def _make_config(tmp_path: Path, subcorpora_count: int = 2, docs_per_subcorpus: int = 4) -> GeneratorConfig:
    return GeneratorConfig(
        name="test",
        description="test config",
        master_seed=42,
        subcorpora_count=subcorpora_count,
        docs_per_subcorpus=docs_per_subcorpus,
        connectivity_level=2,
        doc_type_mix="balanced",
        incoherences=IncoherenceConfig(
            scope_distribution=ScopeDistribution(intra_doc=0.2, intra_corpus=0.5, inter_corpus=0.3),
            mechanism="uniform",
            detectability_distribution=DetectabilityDistribution(single_hop=0.3, multi_hop=0.5, entity_resolution=0.2),
            system_affinity="balanced",
            count="auto",
        ),
        distractor_ratio=0.3,
        output_dir=str(tmp_path / "output"),
    )


class TestGenerateCorpus:
    def test_produces_output_files(self, tmp_path):
        config = _make_config(tmp_path)
        seed_mgr = SeedManager(42)
        metadata, error = generate_corpus(config, seed_mgr, llm=_mock_llm)

        assert error is None
        output = Path(config.output_dir)
        assert (output / "metadata.json").exists()
        assert (output / "entity_graph.json").exists()
        assert (output / "subcorpus_sc-0.jsonl").exists()
        assert (output / "subcorpus_sc-1.jsonl").exists()

    def test_jsonl_contains_valid_documents(self, tmp_path):
        config = _make_config(tmp_path, docs_per_subcorpus=4)
        seed_mgr = SeedManager(42)
        generate_corpus(config, seed_mgr, llm=_mock_llm)

        jsonl_path = Path(config.output_dir) / "subcorpus_sc-0.jsonl"
        lines = jsonl_path.read_text().strip().split("\n")
        assert len(lines) == 4

        for line in lines:
            doc = Document.model_validate_json(line)
            assert doc.subcorpus_id == "sc-0"
            assert 0.0 <= doc.reliability_signal <= 1.0
            assert len(doc.content) > 0

    def test_metadata_has_required_fields(self, tmp_path):
        config = _make_config(tmp_path)
        seed_mgr = SeedManager(42)
        metadata, _ = generate_corpus(config, seed_mgr, llm=_mock_llm)

        assert metadata["benchmark_version"] == "1.0"
        assert metadata["master_seed"] == 42
        assert "generation_timestamp" in metadata
        assert "config" in metadata
        assert "generation_summary" in metadata

        summary = metadata["generation_summary"]
        assert "total_documents" in summary
        assert "total_entities" in summary
        assert "total_edges" in summary

    def test_entity_graph_json_valid(self, tmp_path):
        config = _make_config(tmp_path)
        seed_mgr = SeedManager(42)
        generate_corpus(config, seed_mgr, llm=_mock_llm)

        graph_path = Path(config.output_dir) / "entity_graph.json"
        data = json.loads(graph_path.read_text())
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) > 0

    def test_document_types_balanced(self, tmp_path):
        # With 8 docs per subcorpus and balanced mix, each type appears once
        config = _make_config(tmp_path, docs_per_subcorpus=8)
        seed_mgr = SeedManager(42)
        generate_corpus(config, seed_mgr, llm=_mock_llm)

        jsonl_path = Path(config.output_dir) / "subcorpus_sc-0.jsonl"
        lines = jsonl_path.read_text().strip().split("\n")
        types = [Document.model_validate_json(line).document_type for line in lines]
        unique_types = set(types)
        assert len(unique_types) == 8, f"Expected 8 types, got {unique_types}"

    def test_llm_error_does_not_crash(self, tmp_path):
        def failing_llm(prompt, **kwargs):
            return None, "API error"

        config = _make_config(tmp_path)
        seed_mgr = SeedManager(42)
        metadata, error = generate_corpus(config, seed_mgr, llm=failing_llm)
        # Should complete with errors logged, not crash
        assert error is None
        assert metadata["generation_summary"]["total_errors"] > 0

    def test_deterministic_output(self, tmp_path):
        config1 = _make_config(tmp_path / "run1")
        config2 = _make_config(tmp_path / "run2")

        generate_corpus(config1, SeedManager(42), llm=_mock_llm)
        generate_corpus(config2, SeedManager(42), llm=_mock_llm)

        # Same seed → same documents
        docs1 = (Path(config1.output_dir) / "subcorpus_sc-0.jsonl").read_text()
        docs2 = (Path(config2.output_dir) / "subcorpus_sc-0.jsonl").read_text()
        assert docs1 == docs2


class TestDocTypeMix:
    def test_balanced_produces_all_types(self):
        seq = _build_doc_type_sequence("balanced", 16, SeedManager(42))
        assert len(seq) == 16
        assert len(set(seq)) == 8

    def test_balanced_round_robin(self):
        seq = _build_doc_type_sequence("balanced", 8, SeedManager(42))
        assert len(set(seq)) == 8  # all 8 types present in first 8

    def test_unknown_mix_falls_back_to_balanced(self):
        seq = _build_doc_type_sequence("unknown_mix", 8, SeedManager(42))
        assert len(seq) == 8
        assert len(set(seq)) == 8
