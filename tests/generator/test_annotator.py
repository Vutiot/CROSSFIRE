"""Tests for the gold annotation assembler."""

import json
from pathlib import Path

import pytest

from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.incoherences import DistractorLabel, IncoherenceLabel


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_incoherence_labels() -> list[IncoherenceLabel]:
    """Create sample incoherence labels for testing."""
    return [
        IncoherenceLabel(
            id="incoherence_0000",
            scope="intra_doc",
            mechanism="numeric_drift",
            detectability="single_hop",
            system_affinity="balanced",
            document_references=["sc-0_doc_000"],
            modified_fact="The aircraft was traveling at 280 knots",
            original_fact="The aircraft was traveling at 450 knots",
        ),
        IncoherenceLabel(
            id="incoherence_0001",
            scope="intra_corpus",
            mechanism="entity_swap",
            detectability="multi_hop",
            system_affinity="graph_favoring",
            document_references=["sc-0_doc_001", "sc-0_doc_002"],
            modified_fact="FAA manufactured the aircraft",
            original_fact="Boeing manufactured the aircraft",
        ),
        IncoherenceLabel(
            id="incoherence_0002",
            scope="inter_corpus",
            mechanism="temporal_contradiction",
            detectability="entity_resolution_dependent",
            system_affinity="agentic_favoring",
            document_references=["sc-0_doc_000", "sc-1_doc_000"],
            modified_fact="The incident occurred on March 15, 2024",
            original_fact="The incident occurred on January 5, 2024",
        ),
    ]


def _make_distractor_labels() -> list[DistractorLabel]:
    """Create sample distractor labels for testing."""
    return [
        DistractorLabel(
            id="distractor_0000",
            scope="intra_doc",
            document_references=["sc-0_doc_001"],
            divergence_type="expert_opinion",
            description="Different expert interpretation of root cause",
        ),
        DistractorLabel(
            id="distractor_0001",
            scope="intra_corpus",
            document_references=["sc-1_doc_000", "sc-1_doc_001"],
            divergence_type="measurement_methodology",
            description="Radar vs barometric altitude readings differ",
        ),
    ]


def _create_test_corpus(corpus_dir: Path, modified_facts: list[str] | None = None) -> list[Document]:
    """Create a test corpus. Optionally embed modified_facts into document content."""
    corpus_dir.mkdir(parents=True, exist_ok=True)
    all_docs = []

    extra_text = ""
    if modified_facts:
        extra_text = " ".join(modified_facts) + " "

    for sc_idx in range(2):
        sc_id = f"sc-{sc_idx}"
        docs = []
        for doc_idx in range(3):
            doc = Document(
                id=f"{sc_id}_doc_{doc_idx:03d}",
                document_type="investigation_report",
                subcorpus_id=sc_id,
                reliability_signal=0.85,
                content=(
                    f"FACTUAL REPORT — Subcorpus {sc_idx}, Document {doc_idx}\n\n"
                    f"{extra_text}"
                    f"The aircraft was traveling at 280 knots during the event. "
                    f"FAA manufactured the aircraft model involved. "
                    f"The incident occurred on March 15, 2024."
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
# Task 1 tests: Core assembler
# ---------------------------------------------------------------------------

class TestAssembleGoldAnnotations:
    """Tests for the core assemble_gold_annotations function."""

    def test_function_exists_and_callable(self):
        from crossfire.generator.annotator import assemble_gold_annotations
        assert callable(assemble_gold_annotations)

    def test_writes_incoherence_labels_json(self, tmp_path):
        from crossfire.generator.annotator import assemble_gold_annotations

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir, modified_facts=[
            "The aircraft was traveling at 280 knots",
            "FAA manufactured the aircraft",
            "The incident occurred on March 15, 2024",
        ])

        inc_labels = _make_incoherence_labels()
        dist_labels = _make_distractor_labels()

        summary, error = assemble_gold_annotations(
            output_dir, inc_labels, dist_labels, corpus_dir
        )
        assert error is None

        labels_path = output_dir / "gold_incoherence_labels.json"
        assert labels_path.exists()
        data = json.loads(labels_path.read_text())
        assert len(data) == 3
        # Validate round-trip
        for item in data:
            IncoherenceLabel.model_validate(item)

    def test_writes_distractor_labels_json(self, tmp_path):
        from crossfire.generator.annotator import assemble_gold_annotations

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)

        inc_labels = _make_incoherence_labels()
        dist_labels = _make_distractor_labels()

        assemble_gold_annotations(output_dir, inc_labels, dist_labels, corpus_dir)

        labels_path = output_dir / "gold_distractor_labels.json"
        assert labels_path.exists()
        data = json.loads(labels_path.read_text())
        assert len(data) == 2
        for item in data:
            DistractorLabel.model_validate(item)

    def test_empty_labels_produce_empty_json(self, tmp_path):
        from crossfire.generator.annotator import assemble_gold_annotations

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)

        summary, error = assemble_gold_annotations(
            output_dir, [], [], corpus_dir
        )
        assert error is None

        inc_data = json.loads((output_dir / "gold_incoherence_labels.json").read_text())
        dist_data = json.loads((output_dir / "gold_distractor_labels.json").read_text())
        assert inc_data == []
        assert dist_data == []

    def test_returns_error_for_missing_output_dir(self, tmp_path):
        from crossfire.generator.annotator import assemble_gold_annotations

        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)

        summary, error = assemble_gold_annotations(
            tmp_path / "nonexistent", [], [], corpus_dir
        )
        assert summary is None
        assert error is not None


# ---------------------------------------------------------------------------
# Task 2 tests: Cross-validation
# ---------------------------------------------------------------------------

class TestCrossValidation:
    """Tests for cross-validation of labels against corpus."""

    def test_cross_validation_passes_when_facts_in_corpus(self, tmp_path):
        from crossfire.generator.annotator import assemble_gold_annotations

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        corpus_dir = tmp_path / "corpus"
        # Embed modified facts into corpus content
        _create_test_corpus(corpus_dir, modified_facts=[
            "The aircraft was traveling at 280 knots",
            "FAA manufactured the aircraft",
            "The incident occurred on March 15, 2024",
        ])

        inc_labels = _make_incoherence_labels()
        summary, error = assemble_gold_annotations(
            output_dir, inc_labels, [], corpus_dir
        )
        assert error is None
        assert summary["cross_validation_passed"] == 3
        assert summary["cross_validation_failed"] == 0

    def test_cross_validation_warns_on_missing_facts(self, tmp_path):
        from crossfire.generator.annotator import assemble_gold_annotations

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        corpus_dir = tmp_path / "corpus"
        # Corpus does NOT contain the modified facts
        _create_test_corpus(corpus_dir, modified_facts=[])

        inc_labels = [
            IncoherenceLabel(
                id="incoherence_0000",
                scope="intra_doc",
                mechanism="numeric_drift",
                detectability="single_hop",
                system_affinity="balanced",
                document_references=["sc-0_doc_000"],
                modified_fact="UNIQUE FACT NOT IN CORPUS XYZ123",
                original_fact="original fact",
            ),
        ]
        summary, error = assemble_gold_annotations(
            output_dir, inc_labels, [], corpus_dir
        )
        # Should still succeed — cross-validation failures are warnings
        assert error is None
        assert summary["cross_validation_failed"] == 1


# ---------------------------------------------------------------------------
# Task 3 tests: Metadata update
# ---------------------------------------------------------------------------

class TestMetadataUpdate:
    """Tests for metadata.json version update."""

    def test_creates_metadata_with_version(self, tmp_path):
        from crossfire.generator.annotator import assemble_gold_annotations

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)

        assemble_gold_annotations(
            output_dir, _make_incoherence_labels(), _make_distractor_labels(),
            corpus_dir, version="1.0"
        )

        meta_path = output_dir / "metadata.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text())
        assert meta["version"] == "1.0"
        assert "annotation_summary" in meta

    def test_preserves_existing_metadata(self, tmp_path):
        from crossfire.generator.annotator import assemble_gold_annotations

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir)

        # Pre-existing metadata
        existing = {"benchmark_version": "1.0", "master_seed": 42, "custom_field": "keep_me"}
        (output_dir / "metadata.json").write_text(json.dumps(existing))

        assemble_gold_annotations(
            output_dir, [], [], corpus_dir, version="1.1"
        )

        meta = json.loads((output_dir / "metadata.json").read_text())
        assert meta["benchmark_version"] == "1.0"
        assert meta["master_seed"] == 42
        assert meta["custom_field"] == "keep_me"
        assert meta["version"] == "1.1"

    def test_annotation_summary_has_correct_counts(self, tmp_path):
        from crossfire.generator.annotator import assemble_gold_annotations

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir, modified_facts=[
            "The aircraft was traveling at 280 knots",
            "FAA manufactured the aircraft",
            "The incident occurred on March 15, 2024",
        ])

        inc_labels = _make_incoherence_labels()
        dist_labels = _make_distractor_labels()

        assemble_gold_annotations(
            output_dir, inc_labels, dist_labels, corpus_dir
        )

        meta = json.loads((output_dir / "metadata.json").read_text())
        summary = meta["annotation_summary"]
        assert summary["total_incoherences"] == 3
        assert summary["total_distractors"] == 2
        assert summary["incoherences_by_scope"]["intra_doc"] == 1
        assert summary["incoherences_by_scope"]["intra_corpus"] == 1
        assert summary["incoherences_by_scope"]["inter_corpus"] == 1


# ---------------------------------------------------------------------------
# Task 4 tests: Summary counts (verified via return value)
# ---------------------------------------------------------------------------

class TestSummaryCounts:
    """Tests for summary return value."""

    def test_summary_has_correct_structure(self, tmp_path):
        from crossfire.generator.annotator import assemble_gold_annotations

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        corpus_dir = tmp_path / "corpus"
        _create_test_corpus(corpus_dir, modified_facts=[
            "The aircraft was traveling at 280 knots",
            "FAA manufactured the aircraft",
            "The incident occurred on March 15, 2024",
        ])

        summary, error = assemble_gold_annotations(
            output_dir, _make_incoherence_labels(), _make_distractor_labels(), corpus_dir
        )
        assert error is None
        assert summary["total_incoherences"] == 3
        assert summary["total_distractors"] == 2
        assert "incoherences_by_scope" in summary
        assert "cross_validation_passed" in summary
        assert "cross_validation_failed" in summary
