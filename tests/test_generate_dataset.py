"""Tests for the dataset generation script."""

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from crossfire.shared.schemas.config import GeneratorConfig
from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.entities import EntityGraph, EntityNode, EntityEdge
from crossfire.shared.schemas.incoherences import IncoherenceLabel, DistractorLabel
from crossfire.shared.seed_manager import SeedManager


@pytest.fixture
def tmp_dataset_dir(tmp_path):
    """Create a temporary dataset output directory."""
    return tmp_path / "test_dataset"


@pytest.fixture
def preset_config():
    """Minimal preset config for testing."""
    return {
        "name": "test_preset",
        "description": "Test preset",
        "master_seed": 42,
        "subcorpora_count": 2,
        "docs_per_subcorpus": 4,
        "connectivity_level": 1,
        "doc_type_mix": "balanced",
        "incoherences": {
            "scope_distribution": {
                "intra_doc": 0.5,
                "intra_corpus": 0.3,
                "inter_corpus": 0.2,
            },
            "mechanism": "uniform",
            "detectability_distribution": {
                "single_hop": 0.5,
                "multi_hop": 0.3,
                "entity_resolution": 0.2,
            },
            "system_affinity": "balanced",
            "count": 4,
        },
        "distractor_ratio": 0.5,
    }


def _mock_llm(prompt, model="gpt-4o-mini", temperature=0, dry_run=False):
    """Mock LLM that returns plausible responses for all generator stages."""
    if dry_run:
        return "Dry-run estimate: ~100 tokens", None

    if "Extract key factual claims" in prompt:
        return json.dumps({
            "facts": [
                {"fact": "The aircraft was at 16,000 feet", "type": "numeric"},
                {"fact": "Boeing 737 MAX 9", "type": "entity"},
                {"fact": "January 5, 2024", "type": "temporal"},
            ]
        }), None

    if "modifying a single fact" in prompt:
        return json.dumps({
            "modified_passage": "The aircraft was modified.",
            "original_fact": "The aircraft was at 16,000 feet",
            "modified_fact": "The aircraft was at 22,000 feet",
        }), None

    if "legitimate perspective divergence" in prompt:
        return json.dumps({
            "modified_passage": "Document with divergence added.",
            "description": "Expert disagreement on failure mode",
        }), None

    # Default: return a plausible document content
    return (
        "On January 5, 2024, a Boeing 737 MAX 9 experienced a rapid decompression "
        "event at 16,000 feet after departure. The aircraft was inspected by FAA "
        "investigators who found evidence of manufacturing defects in the door plug "
        "assembly. The National Transportation Safety Board issued preliminary "
        "findings indicating structural failure. Total cost of repairs was estimated "
        "at $2.3 million. Captain John Smith reported unusual vibrations prior to "
        "the event occurring at approximately 14:32 local time."
    ), None


class TestGenerateDataset:
    """Test the single-preset dataset generation function."""

    def test_generate_produces_expected_directory_structure(self, tmp_dataset_dir, preset_config):
        """Generated dataset has corpus/, gold/, and metadata.json."""
        from scripts.generate_dataset import generate_dataset

        config = GeneratorConfig(**preset_config, output_dir=str(tmp_dataset_dir))
        result, error = generate_dataset(config, llm=_mock_llm)

        assert error is None, f"Generation failed: {error}"

        # Verify directory structure
        assert (tmp_dataset_dir / "corpus").is_dir()
        assert (tmp_dataset_dir / "gold").is_dir()
        assert (tmp_dataset_dir / "metadata.json").is_file()

    def test_corpus_dir_contains_jsonl_files(self, tmp_dataset_dir, preset_config):
        """Corpus directory has one JSONL per subcorpus."""
        from scripts.generate_dataset import generate_dataset

        config = GeneratorConfig(**preset_config, output_dir=str(tmp_dataset_dir))
        generate_dataset(config, llm=_mock_llm)

        corpus_dir = tmp_dataset_dir / "corpus"
        jsonl_files = sorted(corpus_dir.glob("subcorpus_*.jsonl"))
        assert len(jsonl_files) == preset_config["subcorpora_count"]

        # Each line should parse as a Document
        for jsonl_path in jsonl_files:
            lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
            assert len(lines) > 0
            for line in lines:
                doc = Document.model_validate_json(line)
                assert doc.content

    def test_gold_dir_contains_all_annotation_files(self, tmp_dataset_dir, preset_config):
        """Gold directory has entity graph, incoherence labels, distractor labels."""
        from scripts.generate_dataset import generate_dataset

        config = GeneratorConfig(**preset_config, output_dir=str(tmp_dataset_dir))
        generate_dataset(config, llm=_mock_llm)

        gold_dir = tmp_dataset_dir / "gold"
        assert (gold_dir / "entity_graph.json").is_file()
        assert (gold_dir / "gold_incoherence_labels.json").is_file()
        assert (gold_dir / "gold_distractor_labels.json").is_file()

        # Validate entity graph parses
        graph = EntityGraph.model_validate_json(
            (gold_dir / "entity_graph.json").read_text(encoding="utf-8")
        )
        assert len(graph.nodes) > 0

        # Validate incoherence labels parse
        inc_data = json.loads(
            (gold_dir / "gold_incoherence_labels.json").read_text(encoding="utf-8")
        )
        for item in inc_data:
            IncoherenceLabel.model_validate(item)

        # Validate distractor labels parse
        dist_data = json.loads(
            (gold_dir / "gold_distractor_labels.json").read_text(encoding="utf-8")
        )
        for item in dist_data:
            DistractorLabel.model_validate(item)

    def test_metadata_contains_required_fields(self, tmp_dataset_dir, preset_config):
        """metadata.json has benchmark_version, master_seed, config, generation_summary, annotation_summary."""
        from scripts.generate_dataset import generate_dataset

        config = GeneratorConfig(**preset_config, output_dir=str(tmp_dataset_dir))
        generate_dataset(config, llm=_mock_llm)

        metadata = json.loads(
            (tmp_dataset_dir / "metadata.json").read_text(encoding="utf-8")
        )
        assert metadata["benchmark_version"] == "1.0"
        assert metadata["master_seed"] == 42
        assert "config" in metadata
        assert "generation_summary" in metadata
        assert "annotation_summary" in metadata
        assert metadata["config"]["name"] == "test_preset"

    def test_deterministic_generation(self, tmp_path, preset_config):
        """Same seed produces identical outputs (excluding timestamp)."""
        from scripts.generate_dataset import generate_dataset

        dir_a = tmp_path / "run_a"
        dir_b = tmp_path / "run_b"

        config_a = GeneratorConfig(**preset_config, output_dir=str(dir_a))
        config_b = GeneratorConfig(**preset_config, output_dir=str(dir_b))

        generate_dataset(config_a, llm=_mock_llm)
        generate_dataset(config_b, llm=_mock_llm)

        # Compare entity graphs (should be identical)
        graph_a = (dir_a / "gold" / "entity_graph.json").read_text()
        graph_b = (dir_b / "gold" / "entity_graph.json").read_text()
        assert graph_a == graph_b

        # Compare corpus files
        for jsonl_a in sorted((dir_a / "corpus").glob("subcorpus_*.jsonl")):
            jsonl_b = dir_b / "corpus" / jsonl_a.name
            assert jsonl_a.read_text() == jsonl_b.read_text()

        # Compare gold labels
        for gold_file in ["gold_incoherence_labels.json", "gold_distractor_labels.json"]:
            a = (dir_a / "gold" / gold_file).read_text()
            b = (dir_b / "gold" / gold_file).read_text()
            assert a == b


class TestValidateDatasets:
    """Test the dataset validation function."""

    def test_valid_dataset_passes(self, tmp_dataset_dir, preset_config):
        """A properly generated dataset passes validation."""
        from scripts.generate_dataset import generate_dataset
        from scripts.validate_datasets import validate_dataset

        config = GeneratorConfig(**preset_config, output_dir=str(tmp_dataset_dir))
        generate_dataset(config, llm=_mock_llm)

        result = validate_dataset(tmp_dataset_dir)
        assert result["valid"] is True

    def test_missing_corpus_fails(self, tmp_dataset_dir):
        """Dataset with missing corpus directory fails validation."""
        from scripts.validate_datasets import validate_dataset

        tmp_dataset_dir.mkdir(parents=True, exist_ok=True)
        (tmp_dataset_dir / "metadata.json").write_text("{}")
        (tmp_dataset_dir / "gold").mkdir()
        (tmp_dataset_dir / "gold" / "entity_graph.json").write_text('{"nodes":[],"edges":[]}')

        result = validate_dataset(tmp_dataset_dir)
        assert result["valid"] is False

    def test_malformed_jsonl_fails(self, tmp_dataset_dir):
        """Dataset with invalid JSONL fails validation."""
        from scripts.validate_datasets import validate_dataset

        tmp_dataset_dir.mkdir(parents=True, exist_ok=True)
        corpus_dir = tmp_dataset_dir / "corpus"
        corpus_dir.mkdir()
        gold_dir = tmp_dataset_dir / "gold"
        gold_dir.mkdir()

        # Write malformed JSONL
        (corpus_dir / "subcorpus_sc-0.jsonl").write_text("not valid json\n")
        (gold_dir / "entity_graph.json").write_text('{"nodes":[],"edges":[]}')
        (gold_dir / "gold_incoherence_labels.json").write_text("[]")
        (gold_dir / "gold_distractor_labels.json").write_text("[]")
        (tmp_dataset_dir / "metadata.json").write_text('{"benchmark_version":"1.0","master_seed":42}')

        result = validate_dataset(tmp_dataset_dir)
        assert result["valid"] is False
