"""Tests for diff-based gold label verification (Story 3.4-NEW).

Covers:
    AC1: Diff-derived char offsets
    AC2: Context contamination check
    AC3: Unintended modifications detected
    AC4: Discrepancy logging
    AC5: Rejection tracking
    AC6: Verified gold labels output
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure generation/ scripts can import from crossfire.shared.schemas
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

# Import from generation script (not a package, so we manipulate sys.path)
if str(_PROJECT_ROOT / "generation") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "generation"))

from verify_dataset import (  # noqa: E402
    compute_diff,
    check_context_contamination,
    load_docs_by_id,
    load_agent_labels,
    verify_label,
    verify_case,
)
from crossfire.shared.schemas.contradictions import ContradictionLabel  # noqa: E402
from crossfire.shared.schemas.corpus import Document  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ORIGINAL_CONTENT = (
    "The aircraft was flying at 35,000 feet when the engine experienced "
    "a mechanical failure. The pilot initiated an emergency descent to "
    "the nearest airport, reaching 10,000 feet within minutes."
)

# Single clean replacement: "35,000 feet" -> "28,000 feet"
_MODIFIED_CONTENT = _ORIGINAL_CONTENT.replace("35,000 feet", "28,000 feet", 1)

# Pre-compute known diff offsets
_DIFF_ORIG_START = _ORIGINAL_CONTENT.index("35,000 feet")
_DIFF_ORIG_END = _DIFF_ORIG_START + len("35,000 feet")
_DIFF_MOD_START = _MODIFIED_CONTENT.index("28,000 feet")
_DIFF_MOD_END = _DIFF_MOD_START + len("28,000 feet")


def _make_doc(document_id: str, content: str, doc_type: str = "report") -> Document:
    return Document(
        document_id=document_id,
        source="ntsb",
        document_type=doc_type,
        source_case_id="case_001",
        scope_classification="intra_doc",
        content=content,
    )


def _make_agent_label(
    scope: str = "intra_doc",
    char_start: int = _DIFF_MOD_START,
    char_end: int = _DIFF_MOD_END,
    original_text: str = "35,000 feet",
    modified_text: str = "28,000 feet",
    doc_refs: list[str] | None = None,
) -> dict:
    """Build an agent-reported label dict (as would be in gold_labels.jsonl)."""
    return {
        "scope": scope,
        "mechanism": "numeric_drift",
        "detectability": "single_hop",
        "system_affinity": "balanced",
        "difficulty": "medium",
        "char_start": char_start,
        "char_end": char_end,
        "original_text": original_text,
        "modified_text": modified_text,
        "rationale": "Numeric drift applied to altitude value",
        "ground_truth": True,
        "document_references": doc_refs or ["doc_001"],
    }


def _setup_case(
    tmp_path: Path,
    original_content: str = _ORIGINAL_CONTENT,
    modified_content: str = _MODIFIED_CONTENT,
    agent_labels: list[dict] | None = None,
    doc_id: str = "doc_001",
) -> Path:
    """Create a minimal case directory with original, modified, and agent labels."""
    case_dir = tmp_path / "case_001"
    orig_dir = case_dir / "anonymized_docs_original"
    mod_dir = case_dir / "anonymized_docs"
    contra_dir = case_dir / "contradictions"

    orig_dir.mkdir(parents=True)
    mod_dir.mkdir(parents=True)
    contra_dir.mkdir(parents=True)

    # Write original doc
    orig_doc = _make_doc(doc_id, original_content)
    (orig_dir / "report.jsonl").write_text(
        orig_doc.model_dump_json() + "\n", encoding="utf-8",
    )

    # Write modified doc
    mod_doc = _make_doc(doc_id, modified_content)
    (mod_dir / "report.jsonl").write_text(
        mod_doc.model_dump_json() + "\n", encoding="utf-8",
    )

    # Write agent labels
    if agent_labels is None:
        agent_labels = [_make_agent_label()]

    with open(contra_dir / "gold_labels.jsonl", "w", encoding="utf-8") as f:
        for label in agent_labels:
            f.write(json.dumps(label) + "\n")

    return case_dir


# ---------------------------------------------------------------------------
# Unit tests: diff engine
# ---------------------------------------------------------------------------


class TestComputeDiff:
    """Tests for the compute_diff function."""

    def test_single_replace(self) -> None:
        ops = compute_diff(_ORIGINAL_CONTENT, _MODIFIED_CONTENT)
        assert len(ops) == 1
        tag, i1, i2, j1, j2 = ops[0]
        assert tag == "replace"
        assert _ORIGINAL_CONTENT[i1:i2] == "35"
        assert _MODIFIED_CONTENT[j1:j2] == "28"

    def test_identical_texts(self) -> None:
        ops = compute_diff("same text", "same text")
        assert len(ops) == 0

    def test_multiple_changes(self) -> None:
        original = "A is 10 and B is 20"
        modified = "A is 99 and B is 77"
        ops = compute_diff(original, modified)
        assert len(ops) >= 2, "Should detect multiple changes"

    def test_insertion(self) -> None:
        original = "Hello world"
        modified = "Hello beautiful world"
        ops = compute_diff(original, modified)
        assert len(ops) >= 1
        # At least one insert or replace operation
        tags = {op[0] for op in ops}
        assert tags & {"insert", "replace"}


class TestContextContamination:
    """Tests for context contamination checks."""

    def test_clean_context(self) -> None:
        # Single replacement, context is identical
        ops = compute_diff(_ORIGINAL_CONTENT, _MODIFIED_CONTENT)
        tag, i1, i2, j1, j2 = ops[0]
        assert check_context_contamination(
            _ORIGINAL_CONTENT, _MODIFIED_CONTENT, i1, i2, j1, j2,
        )

    def test_contaminated_leading_context(self) -> None:
        # Modify some text before the target
        contaminated = "EXTRA " + _MODIFIED_CONTENT
        # The diff will show multiple changes, but we can test the function directly
        assert not check_context_contamination(
            _ORIGINAL_CONTENT, contaminated, 0, 5, 0, 11,
        )

    def test_near_start_of_text(self) -> None:
        """Context check should handle positions near the start gracefully."""
        original = "35,000 feet and more text"
        modified = "28,000 feet and more text"
        ops = compute_diff(original, modified)
        tag, i1, i2, j1, j2 = ops[0]
        assert check_context_contamination(original, modified, i1, i2, j1, j2)


# ---------------------------------------------------------------------------
# Unit tests: verify_label
# ---------------------------------------------------------------------------


class TestVerifyLabel:
    """Tests for single-label verification."""

    def test_clean_injection_passes(self) -> None:
        """AC1: A clean single-replacement injection should pass verification."""
        originals = {"doc_001": _ORIGINAL_CONTENT}
        modifieds = {"doc_001": _MODIFIED_CONTENT}
        agent_label = _make_agent_label()

        result = verify_label(0, agent_label, originals, modifieds)

        assert result.passed
        assert result.rejection_reason is None
        assert result.verified_label is not None
        # Diff-derived offsets should be used (not necessarily same as agent)
        assert result.verified_label.char_start == result.diff_char_start
        assert result.verified_label.char_end == result.diff_char_end

    def test_diff_derived_offsets_used(self) -> None:
        """AC1: Verified label uses diff-derived offsets, not agent offsets."""
        originals = {"doc_001": _ORIGINAL_CONTENT}
        modifieds = {"doc_001": _MODIFIED_CONTENT}
        # Agent reports wrong offsets
        agent_label = _make_agent_label(char_start=999, char_end=1010)

        result = verify_label(0, agent_label, originals, modifieds)

        assert result.passed
        assert result.verified_label is not None
        # Verified label should use diff-derived, NOT 999/1010
        assert result.verified_label.char_start != 999
        assert result.verified_label.char_end != 1010

    def test_unintended_modifications_rejected(self) -> None:
        """AC3: Multiple changes should be flagged and rejected."""
        originals = {"doc_001": "A is 10 and B is 20"}
        modifieds = {"doc_001": "A is 99 and B is 77"}
        agent_label = _make_agent_label(doc_refs=["doc_001"])

        result = verify_label(0, agent_label, originals, modifieds)

        assert not result.passed
        assert "multiple diffs" in result.rejection_reason
        assert len(result.unintended_modifications) >= 2

    def test_offset_discrepancy_logged(self) -> None:
        """AC4: When agent offsets differ from diff, discrepancy is logged."""
        originals = {"doc_001": _ORIGINAL_CONTENT}
        modifieds = {"doc_001": _MODIFIED_CONTENT}
        agent_label = _make_agent_label(char_start=100, char_end=111)

        result = verify_label(0, agent_label, originals, modifieds)

        # Should still pass (diff wins)
        assert result.passed
        # But discrepancy should be logged
        assert result.agent_discrepancy is not None
        assert result.agent_discrepancy["agent_char_start"] == 100
        assert result.agent_discrepancy["diff_char_start"] == result.diff_char_start

    def test_no_discrepancy_when_offsets_match(self) -> None:
        """No discrepancy when agent offsets match diff offsets."""
        originals = {"doc_001": _ORIGINAL_CONTENT}
        modifieds = {"doc_001": _MODIFIED_CONTENT}
        # Compute actual diff offsets to use as agent offsets
        ops = compute_diff(_ORIGINAL_CONTENT, _MODIFIED_CONTENT)
        _, _, _, j1, j2 = ops[0]
        agent_label = _make_agent_label(char_start=j1, char_end=j2)

        result = verify_label(0, agent_label, originals, modifieds)

        assert result.passed
        assert result.agent_discrepancy is None

    def test_missing_document_rejected(self) -> None:
        """Labels referencing non-existent documents are rejected."""
        originals = {}
        modifieds = {"doc_001": _MODIFIED_CONTENT}
        agent_label = _make_agent_label()

        result = verify_label(0, agent_label, originals, modifieds)

        assert not result.passed
        assert "not found in originals" in result.rejection_reason

    def test_no_diff_rejected(self) -> None:
        """Labels where original == modified are rejected."""
        originals = {"doc_001": _ORIGINAL_CONTENT}
        modifieds = {"doc_001": _ORIGINAL_CONTENT}  # same content
        agent_label = _make_agent_label()

        result = verify_label(0, agent_label, originals, modifieds)

        assert not result.passed
        assert "no diff" in result.rejection_reason

    def test_no_document_references_rejected(self) -> None:
        """Labels with empty document_references are rejected."""
        originals = {"doc_001": _ORIGINAL_CONTENT}
        modifieds = {"doc_001": _MODIFIED_CONTENT}
        agent_label = _make_agent_label()
        agent_label["document_references"] = []

        result = verify_label(0, agent_label, originals, modifieds)

        assert not result.passed
        assert "no document_references" in result.rejection_reason

    def test_inter_doc_uses_second_doc_ref(self) -> None:
        """Inter-doc labels diff against the second document reference."""
        originals = {
            "doc_src": "source original content",
            "doc_tgt": _ORIGINAL_CONTENT,
        }
        modifieds = {
            "doc_src": "source original content",
            "doc_tgt": _MODIFIED_CONTENT,
        }
        agent_label = _make_agent_label(
            scope="inter_doc",
            doc_refs=["doc_src", "doc_tgt"],
        )

        result = verify_label(0, agent_label, originals, modifieds)

        assert result.passed
        assert result.verified_label is not None


# ---------------------------------------------------------------------------
# Integration tests: verify_case
# ---------------------------------------------------------------------------


class TestVerifyCase:
    """Integration tests for case-level verification."""

    def test_clean_case_passes(self, tmp_path: Path) -> None:
        """AC1+AC6: Clean injection passes and produces verified labels."""
        case_dir = _setup_case(tmp_path)
        summary = verify_case(case_dir)

        assert summary["total_labels"] == 1
        assert summary["passed"] == 1
        assert summary["rejected"] == 0

    def test_output_files_created(self, tmp_path: Path) -> None:
        """AC5+AC6: All expected output files are created."""
        case_dir = _setup_case(tmp_path)
        verify_case(case_dir)

        # Validation outputs
        assert (case_dir / "validation" / "diff_verification_log.json").exists()
        assert (case_dir / "validation" / "rejected_contradictions.jsonl").exists()
        assert (case_dir / "validation" / "unintended_modifications.json").exists()
        assert (case_dir / "validation" / "agent_label_discrepancies.json").exists()

        # Scope-split outputs
        assert (case_dir / "contradictions" / "intra_doc_contradictions.jsonl").exists()
        assert (case_dir / "contradictions" / "inter_doc_contradictions.jsonl").exists()
        assert (case_dir / "contradictions" / "all_contradictions.jsonl").exists()

    def test_verified_labels_validate_against_schema(self, tmp_path: Path) -> None:
        """AC6: Every line in all_contradictions.jsonl validates against ContradictionLabel."""
        case_dir = _setup_case(tmp_path)
        verify_case(case_dir)

        all_path = case_dir / "contradictions" / "all_contradictions.jsonl"
        lines = all_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) >= 1

        for line in lines:
            if line.strip():
                label = ContradictionLabel.model_validate_json(line)
                assert label.char_start >= 0
                assert label.char_end >= label.char_start

    def test_scope_split_output(self, tmp_path: Path) -> None:
        """AC6: Intra and inter labels are correctly split."""
        # Create case with both intra and inter labels
        case_dir = tmp_path / "case_split"
        orig_dir = case_dir / "anonymized_docs_original"
        mod_dir = case_dir / "anonymized_docs"
        contra_dir = case_dir / "contradictions"

        for d in [orig_dir, mod_dir, contra_dir]:
            d.mkdir(parents=True)

        # Use replacements that produce exactly one diff opcode (no shared chars)
        doc1_orig = "The measurement read XYZQW at the sensor station."
        doc1_mod = doc1_orig.replace("XYZQW", "PJKLM", 1)
        doc2_orig = "Field report dated UVWST from the regional office."
        doc2_mod = doc2_orig.replace("UVWST", "HFGBN", 1)

        for doc_id, content, d in [
            ("d1", doc1_orig, orig_dir),
            ("d1", doc1_mod, mod_dir),
        ]:
            doc = _make_doc(doc_id, content)
            (d / "report.jsonl").write_text(doc.model_dump_json() + "\n")

        for doc_id, content, d in [
            ("d2", doc2_orig, orig_dir),
            ("d2", doc2_mod, mod_dir),
        ]:
            doc = _make_doc(doc_id, content)
            with open(d / "report2.jsonl", "w") as f:
                f.write(doc.model_dump_json() + "\n")

        # Compute actual diff offsets for d1
        ops_d1 = compute_diff(doc1_orig, doc1_mod)
        assert len(ops_d1) == 1, f"Expected 1 opcode for d1, got {ops_d1}"
        _, _, _, j1_d1, j2_d1 = ops_d1[0]

        # Compute actual diff offsets for d2
        ops_d2 = compute_diff(doc2_orig, doc2_mod)
        assert len(ops_d2) == 1, f"Expected 1 opcode for d2, got {ops_d2}"
        _, _, _, j1_d2, j2_d2 = ops_d2[0]

        intra_label = _make_agent_label(
            scope="intra_doc",
            char_start=j1_d1,
            char_end=j2_d1,
            original_text="XYZQW",
            modified_text="PJKLM",
            doc_refs=["d1"],
        )
        inter_label = {
            "scope": "inter_doc",
            "mechanism": "temporal_contradiction",
            "detectability": "single_hop",
            "system_affinity": "balanced",
            "difficulty": "easy",
            "char_start": j1_d2,
            "char_end": j2_d2,
            "original_text": "UVWST",
            "modified_text": "HFGBN",
            "rationale": "Temporal contradiction between documents",
            "ground_truth": True,
            "document_references": ["d1", "d2"],
        }

        with open(contra_dir / "gold_labels.jsonl", "w") as f:
            f.write(json.dumps(intra_label) + "\n")
            f.write(json.dumps(inter_label) + "\n")

        summary = verify_case(case_dir)
        assert summary["passed"] == 2

        # Check scope split files
        intra_path = contra_dir / "intra_doc_contradictions.jsonl"
        inter_path = contra_dir / "inter_doc_contradictions.jsonl"
        all_path = contra_dir / "all_contradictions.jsonl"

        intra_lines = [
            l for l in intra_path.read_text().strip().split("\n") if l.strip()
        ]
        inter_lines = [
            l for l in inter_path.read_text().strip().split("\n") if l.strip()
        ]
        all_lines = [
            l for l in all_path.read_text().strip().split("\n") if l.strip()
        ]

        assert len(intra_lines) == 1
        assert len(inter_lines) == 1
        assert len(all_lines) == 2

        intra_data = json.loads(intra_lines[0])
        assert intra_data["scope"] == "intra_doc"
        inter_data = json.loads(inter_lines[0])
        assert inter_data["scope"] == "inter_doc"

    def test_contamination_flagged(self, tmp_path: Path) -> None:
        """AC2+AC3: Extra text changes are detected and rejected."""
        # Modify two separate things in the document
        contaminated = _ORIGINAL_CONTENT.replace(
            "35,000 feet", "28,000 feet", 1,
        ).replace("10,000 feet", "15,000 feet", 1)

        case_dir = _setup_case(
            tmp_path,
            modified_content=contaminated,
        )
        summary = verify_case(case_dir)

        assert summary["rejected"] == 1
        assert summary["unintended_modifications"] == 1

        # Check rejected file has details
        rejected_path = case_dir / "validation" / "rejected_contradictions.jsonl"
        lines = rejected_path.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert "multiple diffs" in data["reason"]

    def test_discrepancy_logged_in_output(self, tmp_path: Path) -> None:
        """AC4: Offset discrepancies are written to agent_label_discrepancies.json."""
        agent_label = _make_agent_label(char_start=100, char_end=111)
        case_dir = _setup_case(tmp_path, agent_labels=[agent_label])

        summary = verify_case(case_dir)

        assert summary["agent_discrepancies"] == 1
        assert summary["passed"] == 1  # Still passes — diff values win

        disc_path = case_dir / "validation" / "agent_label_discrepancies.json"
        data = json.loads(disc_path.read_text())
        assert len(data) == 1
        assert data[0]["agent_char_start"] == 100

    def test_no_backup_skips(self, tmp_path: Path) -> None:
        """Verification fails gracefully when no backup exists."""
        case_dir = tmp_path / "case_no_backup"
        mod_dir = case_dir / "anonymized_docs"
        mod_dir.mkdir(parents=True)

        summary = verify_case(case_dir)

        assert "error" in summary
        assert "no pre-injection backup" in summary["error"]

    def test_no_agent_labels(self, tmp_path: Path) -> None:
        """Case with no agent labels produces empty summary."""
        case_dir = _setup_case(tmp_path, agent_labels=[])
        summary = verify_case(case_dir)

        assert summary["total_labels"] == 0
        assert summary["passed"] == 0
        assert summary["rejected"] == 0

    def test_verification_log_contents(self, tmp_path: Path) -> None:
        """AC5: diff_verification_log.json records full results."""
        case_dir = _setup_case(tmp_path)
        verify_case(case_dir)

        log_path = case_dir / "validation" / "diff_verification_log.json"
        data = json.loads(log_path.read_text())
        assert len(data) == 1
        entry = data[0]
        assert "label_index" in entry
        assert "passed" in entry
        assert entry["passed"] is True
        assert entry["diff_char_start"] is not None
        assert entry["diff_char_end"] is not None

    def test_rejected_log_contents(self, tmp_path: Path) -> None:
        """AC5: rejected_contradictions.jsonl records rejection details."""
        # Create a case where the document hasn't actually changed
        case_dir = _setup_case(
            tmp_path,
            modified_content=_ORIGINAL_CONTENT,  # no modification
        )
        summary = verify_case(case_dir)

        assert summary["rejected"] == 1
        rejected_path = case_dir / "validation" / "rejected_contradictions.jsonl"
        lines = rejected_path.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert "reason" in data
        assert "no diff" in data["reason"]


# ---------------------------------------------------------------------------
# Injector backup tests
# ---------------------------------------------------------------------------


class TestInjectorBackup:
    """Tests for _backup_originals added to injector.py."""

    def test_backup_creates_copy(self, tmp_path: Path) -> None:
        """Backup should copy anonymized_docs/ to anonymized_docs_original/."""
        from crossfire.generator.injector import _backup_originals

        case_dir = tmp_path / "case"
        docs_dir = case_dir / "anonymized_docs"
        docs_dir.mkdir(parents=True)
        (docs_dir / "report.jsonl").write_text('{"test": true}\n')

        _backup_originals(case_dir)

        backup_dir = case_dir / "anonymized_docs_original"
        assert backup_dir.exists()
        assert (backup_dir / "report.jsonl").exists()
        assert (backup_dir / "report.jsonl").read_text() == '{"test": true}\n'

    def test_backup_is_idempotent(self, tmp_path: Path) -> None:
        """Second call should not overwrite existing backup."""
        from crossfire.generator.injector import _backup_originals

        case_dir = tmp_path / "case"
        docs_dir = case_dir / "anonymized_docs"
        docs_dir.mkdir(parents=True)
        (docs_dir / "report.jsonl").write_text("original\n")

        _backup_originals(case_dir)

        # Modify the anonymized_docs content
        (docs_dir / "report.jsonl").write_text("modified\n")

        # Backup again -- should NOT overwrite
        _backup_originals(case_dir)

        backup_content = (case_dir / "anonymized_docs_original" / "report.jsonl").read_text()
        assert backup_content == "original\n"

    def test_backup_no_source_dir(self, tmp_path: Path) -> None:
        """Backup should do nothing if anonymized_docs/ doesn't exist."""
        from crossfire.generator.injector import _backup_originals

        case_dir = tmp_path / "case"
        case_dir.mkdir(parents=True)

        _backup_originals(case_dir)

        assert not (case_dir / "anonymized_docs_original").exists()
