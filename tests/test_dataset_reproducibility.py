"""Reproducibility verification tests for pre-generated datasets.

These tests verify that regenerating a dataset with the same seed and
configuration produces bit-identical output (excluding generation_timestamp).

The full regeneration test requires LLM API calls and is marked with
@pytest.mark.slow — run with: pytest -m slow
"""

import json
from pathlib import Path

import pytest

from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.entities import EntityGraph
from crossfire.shared.schemas.incoherences import DistractorLabel, IncoherenceLabel

_DATASETS_DIR = Path(__file__).resolve().parent.parent / "data" / "datasets"


class TestDatasetSchemaValidity:
    """Verify committed datasets pass Pydantic schema validation."""

    @pytest.fixture(params=["default", "low_connectivity", "high_connectivity", "stress_test"])
    def dataset_dir(self, request):
        """Parameterized fixture for each preset dataset."""
        d = _DATASETS_DIR / request.param
        if not d.exists():
            pytest.skip(f"Dataset {request.param} not yet generated")
        return d

    def test_corpus_jsonl_files_valid(self, dataset_dir):
        """All JSONL lines parse as Document models."""
        corpus_dir = dataset_dir / "corpus"
        assert corpus_dir.is_dir(), f"Missing corpus dir: {corpus_dir}"

        jsonl_files = sorted(corpus_dir.glob("subcorpus_*.jsonl"))
        assert len(jsonl_files) > 0, "No subcorpus JSONL files found"

        doc_count = 0
        for jsonl_path in jsonl_files:
            for line in jsonl_path.read_text(encoding="utf-8").strip().split("\n"):
                if line:
                    Document.model_validate_json(line)
                    doc_count += 1

        assert doc_count > 0

    def test_entity_graph_valid(self, dataset_dir):
        """Entity graph parses as EntityGraph model."""
        graph_path = dataset_dir / "gold" / "entity_graph.json"
        assert graph_path.is_file()

        graph = EntityGraph.model_validate_json(graph_path.read_text(encoding="utf-8"))
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

    def test_incoherence_labels_valid(self, dataset_dir):
        """Incoherence labels parse as IncoherenceLabel models."""
        inc_path = dataset_dir / "gold" / "gold_incoherence_labels.json"
        assert inc_path.is_file()

        inc_data = json.loads(inc_path.read_text(encoding="utf-8"))
        assert len(inc_data) > 0
        for item in inc_data:
            IncoherenceLabel.model_validate(item)

    def test_distractor_labels_valid(self, dataset_dir):
        """Distractor labels parse as DistractorLabel models."""
        dist_path = dataset_dir / "gold" / "gold_distractor_labels.json"
        assert dist_path.is_file()

        dist_data = json.loads(dist_path.read_text(encoding="utf-8"))
        for item in dist_data:
            DistractorLabel.model_validate(item)

    def test_metadata_has_required_fields(self, dataset_dir):
        """metadata.json contains all required fields."""
        meta_path = dataset_dir / "metadata.json"
        assert meta_path.is_file()

        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        assert "benchmark_version" in metadata
        assert "master_seed" in metadata
        assert "config" in metadata
        assert "generation_summary" in metadata

    def test_metadata_seed_matches_config(self, dataset_dir):
        """metadata.json seed matches the config seed."""
        metadata = json.loads(
            (dataset_dir / "metadata.json").read_text(encoding="utf-8")
        )
        assert metadata["master_seed"] == metadata["config"]["master_seed"]


@pytest.mark.slow
class TestBitIdenticalReproduction:
    """Verify that regenerating a dataset produces identical output.

    These tests require LLM API access and are expensive to run.
    Run with: pytest -m slow
    """

    def test_entity_graph_reproducibility(self, tmp_path):
        """Regenerating with same seed produces identical entity graph."""
        dataset_dir = _DATASETS_DIR / "default"
        if not dataset_dir.exists():
            pytest.skip("Default dataset not yet generated")

        from scripts.generate_dataset import generate_dataset

        metadata = json.loads(
            (dataset_dir / "metadata.json").read_text(encoding="utf-8")
        )
        config_data = metadata["config"]
        config_data["output_dir"] = str(tmp_path / "reproduced")

        from crossfire.shared.schemas.config import GeneratorConfig

        config = GeneratorConfig(**config_data)
        generate_dataset(config)

        # Compare entity graphs
        original = (dataset_dir / "gold" / "entity_graph.json").read_text()
        reproduced = (tmp_path / "reproduced" / "gold" / "entity_graph.json").read_text()
        assert original == reproduced, "Entity graphs differ — reproduction failed"
