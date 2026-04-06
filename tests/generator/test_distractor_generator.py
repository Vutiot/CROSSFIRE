"""Tests for the distractor generator."""

import json
from pathlib import Path

import pytest

from crossfire.shared.schemas.config import (
    DetectabilityDistribution,
    GeneratorConfig,
    IncoherenceConfig,
    ScopeDistribution,
)
from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.entities import EntityEdge, EntityGraph, EntityNode
from crossfire.shared.schemas.incoherences import DistractorLabel
from crossfire.shared.seed_manager import SeedManager


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _mock_llm(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0, dry_run: bool = False):
    """Mock LLM that returns predictable text for distractor tests."""
    if dry_run:
        return "Dry-run estimate: ~500 tokens, ~$0.0001", None

    if "divergence" in prompt.lower() or "distractor" in prompt.lower() or "perspective" in prompt.lower():
        return json.dumps({
            "modified_passage": (
                "The aircraft was traveling at approximately 450 knots when the incident occurred. "
                "Some analysts noted the airspeed indicator may have been reading slightly high due "
                "to pitot tube calibration differences."
            ),
            "description": (
                "Different measurement methodology: pitot tube calibration differences "
                "can produce slightly varying airspeed readings, which is a legitimate "
                "technical divergence, not a factual contradiction."
            ),
        }), None

    return json.dumps({
        "modified_passage": "Modified text.",
        "description": "A legitimate divergence.",
    }), None


def _make_config(
    tmp_path: Path,
    distractor_ratio=0.3,
    subcorpora_count=2,
    docs_per_subcorpus=4,
) -> GeneratorConfig:
    return GeneratorConfig(
        name="test",
        description="test config",
        master_seed=42,
        subcorpora_count=subcorpora_count,
        docs_per_subcorpus=docs_per_subcorpus,
        connectivity_level=2,
        doc_type_mix="balanced",
        incoherences=IncoherenceConfig(
            scope_distribution=ScopeDistribution(
                intra_doc=0.2, intra_corpus=0.5, inter_corpus=0.3
            ),
            mechanism="uniform",
            detectability_distribution=DetectabilityDistribution(
                single_hop=0.3, multi_hop=0.5, entity_resolution=0.2
            ),
            system_affinity="balanced",
            count="auto",
        ),
        distractor_ratio=distractor_ratio,
        output_dir=str(tmp_path / "output"),
    )


def _make_entity_graph() -> EntityGraph:
    """Create a small entity graph for testing."""
    nodes = [
        EntityNode(
            id="org_000", entity_type="organization",
            canonical_name="Boeing", aliases=["The Boeing Company", "BCA"],
            subcorpus_memberships=["sc-0", "sc-1"],
        ),
        EntityNode(
            id="org_001", entity_type="organization",
            canonical_name="FAA", aliases=["Federal Aviation Administration"],
            subcorpus_memberships=["sc-0", "sc-1"],
        ),
        EntityNode(
            id="equip_000", entity_type="equipment",
            canonical_name="Boeing 737 MAX 9", aliases=["737 MAX 9"],
            subcorpus_memberships=["sc-0"],
        ),
    ]
    edges = [
        EntityEdge(source="org_000", target="equip_000", relationship_type="manufactures"),
    ]
    return EntityGraph(nodes=nodes, edges=edges)


def _create_test_corpus(corpus_dir: Path) -> list[Document]:
    """Create a small test corpus on disk and return the documents."""
    corpus_dir.mkdir(parents=True, exist_ok=True)
    all_docs = []

    for sc_idx in range(2):
        sc_id = f"sc-{sc_idx}"
        docs = []
        for doc_idx in range(4):
            doc = Document(
                id=f"{sc_id}_doc_{doc_idx:03d}",
                document_type="investigation_report",
                subcorpus_id=sc_id,
                reliability_signal=0.85,
                content=(
                    f"FACTUAL REPORT — Subcorpus {sc_idx}, Document {doc_idx}\n\n"
                    f"The aircraft was traveling at 450 knots when the incident occurred. "
                    f"Boeing manufactured the aircraft model involved in the investigation. "
                    f"The FAA issued an airworthiness directive following the event. "
                    f"The incident occurred on January 5, 2024 near Portland, Oregon. "
                    f"Engine failure caused the emergency landing. "
                    f"Preliminary findings indicated structural fatigue in the fuselage. "
                    f"The final report concluded that maintenance procedures were inadequate."
                ),
            )
            docs.append(doc)
            all_docs.append(doc)

        jsonl_path = corpus_dir / f"subcorpus_{sc_id}.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for doc in docs:
                f.write(doc.model_dump_json() + "\n")

    return all_docs


# ---------------------------------------------------------------------------
# Task 1 tests: Core scaffold
# ---------------------------------------------------------------------------

class TestGenerateDistractorsScaffold:
    """Tests for the core generate_distractors function."""

    def test_function_exists_and_callable(self):
        from crossfire.generator.distractor_generator import generate_distractors
        assert callable(generate_distractors)

    def test_returns_labels_on_success(self, tmp_path):
        from crossfire.generator.distractor_generator import generate_distractors

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, distractor_ratio=0.5)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            corpus_dir, config, entity_graph,
            incoherence_count=10, seed_mgr=seed_mgr, llm=_mock_llm
        )
        assert error is None
        assert isinstance(labels, list)

    def test_count_matches_ratio(self, tmp_path):
        from crossfire.generator.distractor_generator import generate_distractors

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, distractor_ratio=0.5)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        # 10 incoherences * 0.5 ratio = 5 distractors
        labels, error = generate_distractors(
            corpus_dir, config, entity_graph,
            incoherence_count=10, seed_mgr=seed_mgr, llm=_mock_llm
        )
        assert error is None
        assert len(labels) == 5

    def test_zero_ratio_produces_empty(self, tmp_path):
        from crossfire.generator.distractor_generator import generate_distractors

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, distractor_ratio=0.0)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            corpus_dir, config, entity_graph,
            incoherence_count=10, seed_mgr=seed_mgr, llm=_mock_llm
        )
        assert error is None
        assert labels == []

    def test_returns_error_on_empty_corpus(self, tmp_path):
        from crossfire.generator.distractor_generator import generate_distractors

        corpus_dir = tmp_path / "empty"
        corpus_dir.mkdir(parents=True, exist_ok=True)
        config = _make_config(tmp_path, distractor_ratio=0.3)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            corpus_dir, config, entity_graph,
            incoherence_count=10, seed_mgr=seed_mgr, llm=_mock_llm
        )
        assert labels is None
        assert error is not None


# ---------------------------------------------------------------------------
# Task 2 tests: Divergence types
# ---------------------------------------------------------------------------

class TestDivergenceTypes:
    """Tests for divergence type selection."""

    def test_all_four_types_appear(self, tmp_path):
        from crossfire.generator.distractor_generator import generate_distractors

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, distractor_ratio=1.0)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        # 8 incoherences * 1.0 = 8 distractors — enough for all 4 types
        labels, error = generate_distractors(
            corpus_dir, config, entity_graph,
            incoherence_count=8, seed_mgr=seed_mgr, llm=_mock_llm
        )
        assert error is None
        types_used = {label.divergence_type for label in labels}
        expected = {
            "expert_opinion", "preliminary_vs_final",
            "measurement_methodology", "uncertainty_expression",
        }
        assert types_used == expected

    def test_divergence_types_are_valid(self, tmp_path):
        from crossfire.generator.distractor_generator import generate_distractors

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, distractor_ratio=0.5)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            corpus_dir, config, entity_graph,
            incoherence_count=10, seed_mgr=seed_mgr, llm=_mock_llm
        )
        assert error is None
        valid_types = {
            "expert_opinion", "preliminary_vs_final",
            "measurement_methodology", "uncertainty_expression",
        }
        for label in labels:
            assert label.divergence_type in valid_types


# ---------------------------------------------------------------------------
# Task 4 tests: DistractorLabel metadata
# ---------------------------------------------------------------------------

class TestDistractorLabels:
    """Tests for DistractorLabel metadata completeness."""

    def test_labels_have_all_required_fields(self, tmp_path):
        from crossfire.generator.distractor_generator import generate_distractors

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, distractor_ratio=0.5)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            corpus_dir, config, entity_graph,
            incoherence_count=10, seed_mgr=seed_mgr, llm=_mock_llm
        )
        assert error is None
        for label in labels:
            assert label.id.startswith("distractor_")
            assert label.scope in {"intra_doc", "intra_corpus", "inter_corpus"}
            assert len(label.document_references) >= 1
            assert label.divergence_type
            assert label.description

    def test_document_references_are_valid(self, tmp_path):
        from crossfire.generator.distractor_generator import generate_distractors

        corpus_dir = tmp_path / "corpus"
        original_docs = _create_test_corpus(corpus_dir)
        valid_ids = {d.id for d in original_docs}
        config = _make_config(tmp_path, distractor_ratio=0.5)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            corpus_dir, config, entity_graph,
            incoherence_count=10, seed_mgr=seed_mgr, llm=_mock_llm
        )
        assert error is None
        for label in labels:
            for ref in label.document_references:
                assert ref in valid_ids, f"Invalid doc reference: {ref}"

    def test_labels_are_valid_pydantic_models(self, tmp_path):
        from crossfire.generator.distractor_generator import generate_distractors

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, distractor_ratio=0.5)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            corpus_dir, config, entity_graph,
            incoherence_count=10, seed_mgr=seed_mgr, llm=_mock_llm
        )
        assert error is None
        for label in labels:
            revalidated = DistractorLabel.model_validate(label.model_dump())
            assert revalidated == label


# ---------------------------------------------------------------------------
# Task 5 tests: Write back to disk
# ---------------------------------------------------------------------------

class TestCorpusWriteBack:
    """Tests for writing modified corpus back to disk."""

    def test_documents_written_back(self, tmp_path):
        from crossfire.generator.distractor_generator import generate_distractors

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, distractor_ratio=0.5)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        generate_distractors(
            corpus_dir, config, entity_graph,
            incoherence_count=10, seed_mgr=seed_mgr, llm=_mock_llm
        )

        # Verify JSONL files still valid
        for jsonl_path in corpus_dir.glob("subcorpus_*.jsonl"):
            for line in jsonl_path.read_text(encoding="utf-8").strip().split("\n"):
                doc = Document.model_validate_json(line)
                assert doc.document_type == "investigation_report"
                assert 0.0 <= doc.reliability_signal <= 1.0

    def test_document_ids_preserved(self, tmp_path):
        from crossfire.generator.distractor_generator import generate_distractors

        corpus_dir = tmp_path / "corpus"
        original_docs = _create_test_corpus(corpus_dir)
        original_ids = {d.id for d in original_docs}

        config = _make_config(tmp_path, distractor_ratio=0.5)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        generate_distractors(
            corpus_dir, config, entity_graph,
            incoherence_count=10, seed_mgr=seed_mgr, llm=_mock_llm
        )

        disk_ids = set()
        for jsonl_path in corpus_dir.glob("subcorpus_*.jsonl"):
            for line in jsonl_path.read_text(encoding="utf-8").strip().split("\n"):
                doc = Document.model_validate_json(line)
                disk_ids.add(doc.id)

        assert disk_ids == original_ids


# ---------------------------------------------------------------------------
# Task 6 tests: Determinism and error handling
# ---------------------------------------------------------------------------

class TestDeterminism:
    """Tests for reproducibility."""

    def test_same_seed_produces_identical_results(self, tmp_path):
        from crossfire.generator.distractor_generator import generate_distractors

        corpus_dir1 = tmp_path / "corpus1"
        corpus_dir2 = tmp_path / "corpus2"
        _create_test_corpus(corpus_dir1)
        _create_test_corpus(corpus_dir2)

        config1 = _make_config(tmp_path / "c1", distractor_ratio=0.5)
        config2 = _make_config(tmp_path / "c2", distractor_ratio=0.5)
        entity_graph = _make_entity_graph()

        labels1, _ = generate_distractors(
            corpus_dir1, config1, entity_graph,
            incoherence_count=10, seed_mgr=SeedManager(42), llm=_mock_llm
        )
        labels2, _ = generate_distractors(
            corpus_dir2, config2, entity_graph,
            incoherence_count=10, seed_mgr=SeedManager(42), llm=_mock_llm
        )

        assert len(labels1) == len(labels2)
        for l1, l2 in zip(labels1, labels2):
            assert l1.id == l2.id
            assert l1.scope == l2.scope
            assert l1.divergence_type == l2.divergence_type


class TestErrorHandling:
    """Tests for graceful error handling."""

    def test_llm_errors_handled_gracefully(self, tmp_path):
        from crossfire.generator.distractor_generator import generate_distractors

        def failing_llm(prompt, **kwargs):
            return None, "API error"

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, distractor_ratio=0.5)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            corpus_dir, config, entity_graph,
            incoherence_count=10, seed_mgr=seed_mgr, llm=failing_llm
        )
        assert error is None
        assert isinstance(labels, list)
        assert len(labels) == 0  # All failed gracefully
