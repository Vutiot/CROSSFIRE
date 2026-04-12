"""Tests for the gold annotation assembler."""

import json
from pathlib import Path

import pytest

from crossfire.shared.schemas.contradictions import ContradictionLabel, DistractorLabel
from crossfire.shared.schemas.corpus import Document

from crossfire.generator.annotator import assemble_gold_annotations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_doc(document_id: str, content: str, doc_type: str = "report") -> Document:
    return Document(
        document_id=document_id,
        source="ntsb",
        document_type=doc_type,
        source_case_id="case_001",
        scope_classification="intra_doc",
        content=content,
    )


def _write_case(tmp_path: Path, docs: list[Document]) -> Path:
    """Write docs into case_dir/anonymized_docs/ and return case_dir."""
    case_dir = tmp_path / "case_001"
    docs_dir = case_dir / "anonymized_docs"
    docs_dir.mkdir(parents=True)

    by_type: dict[str, list[Document]] = {}
    for doc in docs:
        by_type.setdefault(doc.document_type, []).append(doc)

    for doc_type, type_docs in by_type.items():
        path = docs_dir / f"{doc_type}.jsonl"
        with open(path, "w") as f:
            for d in type_docs:
                f.write(d.model_dump_json() + "\n")

    return case_dir


def _make_contradiction(
    doc_id: str = "doc_001",
    original: str = "35,000 feet",
    modified: str = "28,000 feet",
    char_start: int = 10,
    char_end: int = 22,
) -> ContradictionLabel:
    return ContradictionLabel(
        scope="intra_doc",
        mechanism="numeric_drift",
        detectability="single_hop",
        system_affinity="balanced",
        difficulty="medium",
        char_start=char_start,
        char_end=char_end,
        original_text=original,
        modified_text=modified,
        rationale="Numeric drift applied to altitude value",
        ground_truth=True,
        document_references=[doc_id],
    )


def _make_distractor(doc_id: str = "doc_001") -> DistractorLabel:
    return DistractorLabel(
        scope="intra_doc",
        divergence_type="expert_opinion",
        document_references=[doc_id],
        description="Expert disagreement on failure cause.",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAssembleGoldAnnotations:
    """Tests for assemble_gold_annotations."""

    def test_happy_path(self, tmp_path):
        """Should write annotations and return summary."""
        content_with_modification = "The plane at 28,000 feet experienced failure."
        docs = [_make_doc("doc_001", content_with_modification)]
        case_dir = _write_case(tmp_path, docs)

        contradictions = [_make_contradiction(
            doc_id="doc_001",
            modified="28,000 feet",
            char_start=13,
            char_end=25,
        )]
        distractors = [_make_distractor("doc_001")]

        summary, error = assemble_gold_annotations(
            case_dir=case_dir,
            contradictions=contradictions,
            distractors=distractors,
        )

        assert error is None
        assert summary is not None
        assert summary["total_contradictions"] == 1
        assert summary["total_distractors"] == 1
        assert summary["cross_validation_passed"] == 1
        assert summary["cross_validation_failed"] == 0

    def test_writes_jsonl_files(self, tmp_path):
        """Should create contradictions/ and distractors/ directories with JSONL."""
        docs = [_make_doc("doc_001", "Some modified content with 28,000 feet.")]
        case_dir = _write_case(tmp_path, docs)

        contradictions = [_make_contradiction(doc_id="doc_001")]
        distractors = [_make_distractor("doc_001")]

        summary, error = assemble_gold_annotations(
            case_dir=case_dir,
            contradictions=contradictions,
            distractors=distractors,
        )

        assert error is None

        # Check contradiction JSONL
        contra_path = case_dir / "contradictions" / "gold_labels.jsonl"
        assert contra_path.exists()
        lines = contra_path.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["scope"] == "intra_doc"
        assert data["mechanism"] == "numeric_drift"
        assert "id" not in data  # No id field

        # Check distractor JSONL
        dist_path = case_dir / "distractors" / "gold_labels.jsonl"
        assert dist_path.exists()
        lines = dist_path.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["divergence_type"] == "expert_opinion"
        assert "id" not in data

    def test_cross_validation_failure(self, tmp_path):
        """Should report failed cross-validation when modified text not in corpus."""
        docs = [_make_doc("doc_001", "This content does not contain the modified text.")]
        case_dir = _write_case(tmp_path, docs)

        contradictions = [_make_contradiction(
            doc_id="doc_001",
            modified="text_that_is_nowhere",
        )]
        distractors = []

        summary, error = assemble_gold_annotations(
            case_dir=case_dir,
            contradictions=contradictions,
            distractors=distractors,
        )

        assert error is None
        assert summary is not None
        assert summary["cross_validation_passed"] == 0
        assert summary["cross_validation_failed"] == 1

    def test_empty_labels(self, tmp_path):
        """Should handle empty label lists gracefully."""
        docs = [_make_doc("doc_001", "Some content.")]
        case_dir = _write_case(tmp_path, docs)

        summary, error = assemble_gold_annotations(
            case_dir=case_dir,
            contradictions=[],
            distractors=[],
        )

        assert error is None
        assert summary is not None
        assert summary["total_contradictions"] == 0
        assert summary["total_distractors"] == 0
        assert summary["cross_validation_passed"] == 0
        assert summary["cross_validation_failed"] == 0

    def test_case_dir_missing(self, tmp_path):
        """Should return error when case_dir does not exist."""
        case_dir = tmp_path / "nonexistent"

        summary, error = assemble_gold_annotations(
            case_dir=case_dir,
            contradictions=[],
            distractors=[],
        )

        assert summary is None
        assert error is not None
        assert "does not exist" in error

    def test_multiple_contradictions(self, tmp_path):
        """Should handle multiple contradictions with scope breakdown."""
        docs = [
            _make_doc("doc_001", "Content with 28,000 feet and other data."),
            _make_doc("doc_002", "Another document with 28,000 feet reference."),
        ]
        case_dir = _write_case(tmp_path, docs)

        contradictions = [
            _make_contradiction(doc_id="doc_001"),
            ContradictionLabel(
                scope="inter_doc",
                mechanism="entity_swap",
                detectability="multi_hop",
                system_affinity="balanced",
                difficulty="hard",
                char_start=0,
                char_end=10,
                original_text="Boeing 737",
                modified_text="Airbus A320",
                rationale="Entity swap between documents",
                ground_truth=True,
                document_references=["doc_001", "doc_002"],
            ),
        ]
        distractors = [_make_distractor("doc_001")]

        summary, error = assemble_gold_annotations(
            case_dir=case_dir,
            contradictions=contradictions,
            distractors=distractors,
        )

        assert error is None
        assert summary["total_contradictions"] == 2
        assert summary["contradictions_by_scope"]["intra_doc"] == 1
        assert summary["contradictions_by_scope"]["inter_doc"] == 1
        assert summary["total_distractors"] == 1
