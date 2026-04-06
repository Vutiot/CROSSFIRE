"""Tests for the incoherence injector."""

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
from crossfire.shared.schemas.entities import EntityGraph, EntityNode, EntityEdge
from crossfire.shared.schemas.incoherences import IncoherenceLabel
from crossfire.shared.seed_manager import SeedManager


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _mock_llm(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0, dry_run: bool = False):
    """Mock LLM that returns predictable text for injection tests."""
    if dry_run:
        return "Dry-run estimate: ~500 tokens, ~$0.0001", None

    # Detect which kind of prompt this is and return structured JSON
    if "extract" in prompt.lower() and "fact" in prompt.lower():
        # Fact extraction prompt
        return json.dumps({
            "facts": [
                {"fact": "The aircraft was traveling at 450 knots", "type": "numeric"},
                {"fact": "Boeing manufactured the aircraft", "type": "entity"},
                {"fact": "The incident occurred on January 5, 2024", "type": "temporal"},
                {"fact": "Engine failure caused the crash", "type": "causal"},
            ]
        }), None

    if "modify" in prompt.lower() or "inject" in prompt.lower() or "change" in prompt.lower():
        # Fact modification prompt
        return json.dumps({
            "modified_passage": "The aircraft was traveling at 280 knots during the event.",
            "original_fact": "The aircraft was traveling at 450 knots",
            "modified_fact": "The aircraft was traveling at 280 knots",
        }), None

    # Default: return generic text
    return "Modified text content.", None


def _make_config(
    tmp_path: Path,
    count=10,
    system_affinity="balanced",
    mechanism="uniform",
    subcorpora_count=2,
    docs_per_subcorpus=4,
    connectivity_level=2,
) -> GeneratorConfig:
    return GeneratorConfig(
        name="test",
        description="test config",
        master_seed=42,
        subcorpora_count=subcorpora_count,
        docs_per_subcorpus=docs_per_subcorpus,
        connectivity_level=connectivity_level,
        doc_type_mix="balanced",
        incoherences=IncoherenceConfig(
            scope_distribution=ScopeDistribution(
                intra_doc=0.2, intra_corpus=0.5, inter_corpus=0.3
            ),
            mechanism=mechanism,
            detectability_distribution=DetectabilityDistribution(
                single_hop=0.3, multi_hop=0.5, entity_resolution=0.2
            ),
            system_affinity=system_affinity,
            count=count,
        ),
        distractor_ratio=0.3,
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
            canonical_name="Boeing 737 MAX 9", aliases=["737 MAX 9", "737-9"],
            subcorpus_memberships=["sc-0"],
        ),
        EntityNode(
            id="equip_001", entity_type="equipment",
            canonical_name="Boeing 767-300", aliases=["767-300"],
            subcorpus_memberships=["sc-1"],
        ),
        EntityNode(
            id="loc_000", entity_type="location",
            canonical_name="Portland, Oregon", aliases=["PDX"],
            subcorpus_memberships=["sc-0"],
        ),
    ]
    edges = [
        EntityEdge(source="org_000", target="equip_000", relationship_type="manufactures"),
        EntityEdge(source="org_000", target="equip_001", relationship_type="manufactures"),
        EntityEdge(source="org_001", target="org_000", relationship_type="regulated_by"),
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

class TestInjectIncoherencesScaffold:
    """Tests for the core inject_incoherences function scaffold."""

    def test_function_exists_and_callable(self):
        from crossfire.generator.injector import inject_incoherences
        assert callable(inject_incoherences)

    def test_loads_documents_from_corpus_dir(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, count=2)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None
        assert isinstance(labels, list)

    def test_auto_count_heuristic(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)  # 8 docs total
        config = _make_config(tmp_path, count="auto")
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None
        # auto = max(10, 8 // 10) = max(10, 0) = 10, but capped at available
        # With 8 docs, we can't do more injections than feasible
        assert isinstance(labels, list)

    def test_fixed_count(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, count=4)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None
        assert len(labels) == 4

    def test_returns_error_on_empty_corpus_dir(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "empty_corpus"
        corpus_dir.mkdir(parents=True, exist_ok=True)
        config = _make_config(tmp_path, count=4)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert labels is None
        assert error is not None
        assert "No documents" in error or "no subcorpus" in error.lower() or "empty" in error.lower()


# ---------------------------------------------------------------------------
# Task 2 tests: Scope selection
# ---------------------------------------------------------------------------

class TestScopeDistribution:
    """Tests for scope distribution across injections."""

    def test_scope_distribution_matches_config(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        # 20% intra_doc, 50% intra_corpus, 30% inter_corpus with count=10
        config = _make_config(tmp_path, count=10)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None

        scope_counts = {}
        for label in labels:
            scope_counts[label.scope] = scope_counts.get(label.scope, 0) + 1

        # With 10 injections: intra_doc=2, intra_corpus=5, inter_corpus=3
        # Allow +-1 tolerance for rounding
        assert abs(scope_counts.get("intra_doc", 0) - 2) <= 1
        assert abs(scope_counts.get("intra_corpus", 0) - 5) <= 1
        assert abs(scope_counts.get("inter_corpus", 0) - 3) <= 1

    def test_all_scope_values_are_valid(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, count=6)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None
        valid_scopes = {"intra_doc", "intra_corpus", "inter_corpus"}
        for label in labels:
            assert label.scope in valid_scopes, f"Invalid scope: {label.scope}"


# ---------------------------------------------------------------------------
# Task 3 tests: Mechanism selection
# ---------------------------------------------------------------------------

class TestMechanismSelection:
    """Tests for mechanism selection and assignment."""

    def test_uniform_mechanism_uses_all_six(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, count=12, mechanism="uniform")
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None
        mechanisms_used = {label.mechanism for label in labels}
        # With 12 injections and uniform distribution, all 6 should appear
        all_mechanisms = {
            "numeric_drift", "entity_swap", "causal_inversion",
            "temporal_contradiction", "omission_based_implicit",
            "temporal_revision_conflict",
        }
        assert mechanisms_used == all_mechanisms

    def test_specific_mechanism_applied_to_all(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, count=4, mechanism="entity_swap")
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None
        for label in labels:
            assert label.mechanism == "entity_swap"

    def test_all_mechanism_values_are_valid(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, count=6)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None
        valid_mechanisms = {
            "numeric_drift", "entity_swap", "causal_inversion",
            "temporal_contradiction", "omission_based_implicit",
            "temporal_revision_conflict",
        }
        for label in labels:
            assert label.mechanism in valid_mechanisms


# ---------------------------------------------------------------------------
# Task 4 tests: Detectability assignment
# ---------------------------------------------------------------------------

class TestDetectabilityAssignment:
    """Tests for detectability level distribution."""

    def test_detectability_distribution_matches_config(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        # 30% single_hop, 50% multi_hop, 20% entity_resolution
        config = _make_config(tmp_path, count=10)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None

        detect_counts = {}
        for label in labels:
            detect_counts[label.detectability] = detect_counts.get(label.detectability, 0) + 1

        # 30% of 10 = 3, 50% of 10 = 5, 20% of 10 = 2
        assert abs(detect_counts.get("single_hop", 0) - 3) <= 1
        assert abs(detect_counts.get("multi_hop", 0) - 5) <= 1
        assert abs(detect_counts.get("entity_resolution_dependent", 0) - 2) <= 1

    def test_all_detectability_values_are_valid(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, count=6)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None
        valid_detectabilities = {"single_hop", "multi_hop", "entity_resolution_dependent"}
        for label in labels:
            assert label.detectability in valid_detectabilities


# ---------------------------------------------------------------------------
# Task 5 tests: System affinity
# ---------------------------------------------------------------------------

class TestSystemAffinity:
    """Tests for system affinity normalization and application."""

    def test_affinity_normalization_hyphen_to_underscore(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, count=4, system_affinity="graph-favoring")
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None
        for label in labels:
            assert label.system_affinity == "graph_favoring"

    def test_agentic_favoring_normalization(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, count=4, system_affinity="agentic-favoring")
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None
        for label in labels:
            assert label.system_affinity == "agentic_favoring"

    def test_balanced_affinity_unchanged(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, count=4, system_affinity="balanced")
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None
        for label in labels:
            assert label.system_affinity == "balanced"


# ---------------------------------------------------------------------------
# Task 6 & 7 tests: Minimal-pair modification & IncoherenceLabel metadata
# ---------------------------------------------------------------------------

class TestMinimalPairAndLabels:
    """Tests for LLM-based modification and label metadata."""

    def test_labels_have_all_required_fields(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, count=4)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None
        for label in labels:
            assert label.id.startswith("incoherence_")
            assert label.scope in {"intra_doc", "intra_corpus", "inter_corpus"}
            assert label.mechanism in {
                "numeric_drift", "entity_swap", "causal_inversion",
                "temporal_contradiction", "omission_based_implicit",
                "temporal_revision_conflict",
            }
            assert label.detectability in {
                "single_hop", "multi_hop", "entity_resolution_dependent"
            }
            assert label.system_affinity in {
                "balanced", "graph_favoring", "agentic_favoring"
            }
            assert len(label.document_references) >= 1
            assert label.modified_fact
            assert label.original_fact

    def test_document_references_point_to_valid_ids(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        original_docs = _create_test_corpus(corpus_dir)
        valid_ids = {d.id for d in original_docs}
        config = _make_config(tmp_path, count=4)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None
        for label in labels:
            for ref in label.document_references:
                assert ref in valid_ids, f"Invalid doc reference: {ref}"

    def test_labels_are_valid_pydantic_models(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, count=4)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None
        for label in labels:
            # Validate by re-creating from dict
            revalidated = IncoherenceLabel.model_validate(label.model_dump())
            assert revalidated == label


# ---------------------------------------------------------------------------
# Task 8 tests: Write modified corpus back to disk
# ---------------------------------------------------------------------------

class TestCorpusWriteBack:
    """Tests for writing modified corpus back to disk."""

    def test_modified_documents_written_to_disk(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        original_docs = _create_test_corpus(corpus_dir)

        # Read original content for comparison
        original_contents = {}
        for doc in original_docs:
            original_contents[doc.id] = doc.content

        config = _make_config(tmp_path, count=4)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None

        # Read back from disk and verify structure is preserved
        for jsonl_path in corpus_dir.glob("subcorpus_*.jsonl"):
            for line in jsonl_path.read_text(encoding="utf-8").strip().split("\n"):
                doc = Document.model_validate_json(line)
                # Document metadata preserved
                assert doc.id in original_contents
                assert doc.document_type == "investigation_report"
                assert 0.0 <= doc.reliability_signal <= 1.0

    def test_document_ids_preserved_after_injection(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        original_docs = _create_test_corpus(corpus_dir)
        original_ids = {d.id for d in original_docs}

        config = _make_config(tmp_path, count=4)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        inject_incoherences(corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm)

        # Read all doc IDs back
        disk_ids = set()
        for jsonl_path in corpus_dir.glob("subcorpus_*.jsonl"):
            for line in jsonl_path.read_text(encoding="utf-8").strip().split("\n"):
                doc = Document.model_validate_json(line)
                disk_ids.add(doc.id)

        assert disk_ids == original_ids


# ---------------------------------------------------------------------------
# Task 9 tests: Comprehensive / integration
# ---------------------------------------------------------------------------

class TestDeterminism:
    """Tests for reproducibility."""

    def test_same_seed_produces_identical_results(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir1 = tmp_path / "corpus1"
        corpus_dir2 = tmp_path / "corpus2"
        _create_test_corpus(corpus_dir1)
        _create_test_corpus(corpus_dir2)

        config1 = _make_config(tmp_path / "cfg1", count=4)
        config2 = _make_config(tmp_path / "cfg2", count=4)
        entity_graph = _make_entity_graph()

        labels1, _ = inject_incoherences(
            corpus_dir1, config1, entity_graph, SeedManager(42), llm=_mock_llm
        )
        labels2, _ = inject_incoherences(
            corpus_dir2, config2, entity_graph, SeedManager(42), llm=_mock_llm
        )

        assert len(labels1) == len(labels2)
        for l1, l2 in zip(labels1, labels2):
            assert l1.id == l2.id
            assert l1.scope == l2.scope
            assert l1.mechanism == l2.mechanism
            assert l1.detectability == l2.detectability
            assert l1.system_affinity == l2.system_affinity


class TestErrorHandling:
    """Tests for graceful error handling."""

    def test_llm_errors_handled_gracefully(self, tmp_path):
        from crossfire.generator.injector import inject_incoherences

        def failing_llm(prompt, **kwargs):
            return None, "API error"

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, count=4)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=failing_llm
        )
        # Should not crash — returns empty list with no fatal error
        assert error is None
        assert isinstance(labels, list)
        assert len(labels) == 0  # All injections failed gracefully


class TestAllMechanismsTriggerable:
    """Test that each mechanism can be triggered individually."""

    @pytest.mark.parametrize("mechanism", [
        "numeric_drift",
        "entity_swap",
        "causal_inversion",
        "temporal_contradiction",
        "omission_based_implicit",
        "temporal_revision_conflict",
    ])
    def test_specific_mechanism(self, tmp_path, mechanism):
        from crossfire.generator.injector import inject_incoherences

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)
        config = _make_config(tmp_path, count=2, mechanism=mechanism)
        entity_graph = _make_entity_graph()
        seed_mgr = SeedManager(42)

        labels, error = inject_incoherences(
            corpus_dir, config, entity_graph, seed_mgr, llm=_mock_llm
        )
        assert error is None
        for label in labels:
            assert label.mechanism == mechanism
