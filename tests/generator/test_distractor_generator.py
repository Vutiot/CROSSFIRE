"""Tests for the distractor generator.

Validates:
- Distractor count matches ratio (AC1)
- All 4 divergence types can appear (AC2)
- Documents are NOT modified — no content truncation (AC5, P5 fix)
- JSONL output written to distractors/distractor_labels.jsonl (AC4)
- Model selection uses params.reasoning_model (AC6)
- Zero contradiction count returns empty list
- Markdown fence stripping in LLM responses
"""

import json
from pathlib import Path

import pytest

from crossfire.shared.schemas.config import GenerationParams
from crossfire.shared.schemas.contradictions import DistractorLabel
from crossfire.shared.schemas.corpus import Document
from crossfire.shared.seed_manager import SeedManager

from crossfire.generator.distractor_generator import generate_distractors


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


_CALL_COUNT = 0


def _fake_llm(prompt: str, model: str = "test-model", temperature: float = 0):
    """Fake LLM that returns a valid distractor response with rotating divergence types."""
    global _CALL_COUNT
    _CALL_COUNT += 1
    return json.dumps({
        "divergence_type": "expert_opinion",
        "description": f"Expert A and Expert B disagree on failure cause (call {_CALL_COUNT}).",
        "scope": "intra_doc",
    }), None


def _fake_llm_with_fences(prompt: str, model: str = "test-model", temperature: float = 0):
    """Fake LLM that returns a response wrapped in markdown code fences."""
    return '```json\n' + json.dumps({
        "divergence_type": "expert_opinion",
        "description": "Expert disagreement on root cause analysis.",
        "scope": "intra_doc",
    }) + '\n```', None


def _default_params(**overrides) -> GenerationParams:
    """Create GenerationParams with sensible defaults."""
    kwargs = dict(
        version_id="v1",
        contradiction_rate_intra_doc=0.5,
        contradiction_rate_inter_doc=0.5,
        distractor_ratio=0.5,
        reasoning_model="test-reasoning-model",
    )
    kwargs.update(overrides)
    return GenerationParams(**kwargs)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDistractorCount:
    """AC1: Distractor count matches ratio."""

    def test_count_matches_ratio(self, tmp_path):
        """round(contradiction_count * distractor_ratio) distractors should be generated."""
        docs = [
            _make_doc("doc_001", "The aircraft experienced a loss of control."),
            _make_doc("doc_002", "Maintenance logs show no discrepancies."),
            _make_doc("doc_003", "Weather conditions were within normal limits."),
        ]
        case_dir = _write_case(tmp_path, docs)
        params = _default_params(distractor_ratio=0.5)
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            case_dir=case_dir,
            contradiction_count=4,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None
        assert len(labels) == 2  # round(4 * 0.5)

    def test_count_with_different_ratio(self, tmp_path):
        """Different ratio should produce different count."""
        docs = [
            _make_doc("doc_001", "Content A."),
            _make_doc("doc_002", "Content B."),
        ]
        case_dir = _write_case(tmp_path, docs)
        params = _default_params(distractor_ratio=1.0)
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            case_dir=case_dir,
            contradiction_count=3,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None
        assert len(labels) == 3  # round(3 * 1.0)


class TestZeroCount:
    """Zero contradiction count or zero ratio should return empty list."""

    def test_zero_ratio(self, tmp_path):
        """distractor_ratio=0.0 should produce zero distractors."""
        docs = [_make_doc("doc_001", "Some content.")]
        case_dir = _write_case(tmp_path, docs)
        params = _default_params(distractor_ratio=0.0)
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            case_dir=case_dir,
            contradiction_count=5,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels == []

    def test_zero_contradiction_count(self, tmp_path):
        """contradiction_count=0 should produce zero distractors."""
        docs = [_make_doc("doc_001", "Some content.")]
        case_dir = _write_case(tmp_path, docs)
        params = _default_params(distractor_ratio=0.5)
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            case_dir=case_dir,
            contradiction_count=0,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels == []


class TestDivergenceTypes:
    """AC2: All 4 divergence types can appear."""

    def test_all_four_types_appear(self, tmp_path):
        """With enough distractors, all 4 divergence types should be assigned."""
        docs = [
            _make_doc("doc_001", "Content A about investigation."),
            _make_doc("doc_002", "Content B about maintenance."),
            _make_doc("doc_003", "Content C about weather conditions."),
        ]
        case_dir = _write_case(tmp_path, docs)
        # Request 8 distractors to ensure round-robin covers all 4 types
        params = _default_params(distractor_ratio=1.0)
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            case_dir=case_dir,
            contradiction_count=8,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None
        types_found = {label.divergence_type for label in labels}
        assert types_found == {
            "expert_opinion",
            "preliminary_vs_final",
            "measurement_methodology",
            "uncertainty_expression",
        }


class TestNoContentTruncation:
    """AC5 / P5 fix: Document content must NOT be modified."""

    def test_document_content_unchanged(self, tmp_path):
        """Documents must be byte-identical after distractor generation."""
        long_content = "A" * 5000  # Well above the old 2000-char truncation
        docs = [_make_doc("doc_001", long_content)]
        case_dir = _write_case(tmp_path, docs)
        params = _default_params(distractor_ratio=1.0)
        seed_mgr = SeedManager(42)

        # Record content before
        content_before = long_content

        labels, error = generate_distractors(
            case_dir=case_dir,
            contradiction_count=2,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None

        # Re-read documents from disk — they should be unchanged
        docs_dir = case_dir / "anonymized_docs"
        for jsonl_path in docs_dir.glob("*.jsonl"):
            for line in jsonl_path.read_text().strip().split("\n"):
                if line:
                    doc = Document.model_validate_json(line)
                    assert doc.content == content_before
                    assert len(doc.content) == 5000

    def test_multiple_documents_all_preserved(self, tmp_path):
        """All documents should retain their exact original content."""
        docs = [
            _make_doc("doc_001", "First document " * 300),
            _make_doc("doc_002", "Second document " * 400),
            _make_doc("doc_003", "Third document " * 200),
        ]
        case_dir = _write_case(tmp_path, docs)
        original_contents = {d.document_id: d.content for d in docs}
        params = _default_params(distractor_ratio=1.0)
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            case_dir=case_dir,
            contradiction_count=3,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None

        # Re-read and verify all docs unchanged
        docs_dir = case_dir / "anonymized_docs"
        for jsonl_path in docs_dir.glob("*.jsonl"):
            for line in jsonl_path.read_text().strip().split("\n"):
                if line:
                    doc = Document.model_validate_json(line)
                    assert doc.content == original_contents[doc.document_id]


class TestJSONLOutput:
    """AC4: Labels written to distractors/distractor_labels.jsonl."""

    def test_jsonl_written(self, tmp_path):
        """Labels should be written as JSONL to the distractors directory."""
        docs = [
            _make_doc("doc_001", "Investigation content here."),
            _make_doc("doc_002", "Maintenance record content."),
        ]
        case_dir = _write_case(tmp_path, docs)
        params = _default_params(distractor_ratio=1.0)
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            case_dir=case_dir,
            contradiction_count=3,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None

        # Verify JSONL file exists
        jsonl_path = case_dir / "distractors" / "distractor_labels.jsonl"
        assert jsonl_path.exists()

        # Verify each line validates against DistractorLabel
        lines = jsonl_path.read_text().strip().split("\n")
        assert len(lines) == len(labels)

        for line in lines:
            parsed = DistractorLabel.model_validate_json(line)
            assert parsed.scope in ("intra_doc", "inter_doc")
            assert parsed.divergence_type in (
                "expert_opinion",
                "preliminary_vs_final",
                "measurement_methodology",
                "uncertainty_expression",
            )
            assert len(parsed.document_references) >= 1
            assert parsed.description

    def test_no_id_field_in_output(self, tmp_path):
        """DistractorLabel should not have an id field in the JSONL output."""
        docs = [_make_doc("doc_001", "Some content.")]
        case_dir = _write_case(tmp_path, docs)
        params = _default_params(distractor_ratio=1.0)
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            case_dir=case_dir,
            contradiction_count=1,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None
        assert len(labels) == 1

        # Check label object
        dumped = labels[0].model_dump()
        assert "id" not in dumped

        # Also check JSONL on disk
        jsonl_path = case_dir / "distractors" / "distractor_labels.jsonl"
        line = jsonl_path.read_text().strip()
        data = json.loads(line)
        assert "id" not in data


class TestModelSelection:
    """AC6: Uses params.reasoning_model for LLM calls."""

    def test_uses_reasoning_model(self, tmp_path):
        """LLM should be called with params.reasoning_model, not a hardcoded model."""
        docs = [_make_doc("doc_001", "Content about the investigation.")]
        case_dir = _write_case(tmp_path, docs)
        params = _default_params(reasoning_model="custom-reasoning-model-v2")
        seed_mgr = SeedManager(42)

        models_used = []

        def tracking_llm(prompt: str, model: str = "default", temperature: float = 0):
            models_used.append(model)
            return json.dumps({
                "divergence_type": "expert_opinion",
                "description": "Expert disagreement.",
                "scope": "intra_doc",
            }), None

        labels, error = generate_distractors(
            case_dir=case_dir,
            contradiction_count=2,
            params=params,
            seed_mgr=seed_mgr,
            llm=tracking_llm,
        )

        assert error is None
        assert labels is not None
        # All LLM calls should use the custom reasoning model
        assert len(models_used) > 0
        for m in models_used:
            assert m == "custom-reasoning-model-v2"


class TestMarkdownFenceStripping:
    """Markdown fences in LLM responses should be stripped before JSON parsing."""

    def test_handles_fenced_response(self, tmp_path):
        """LLM response wrapped in ```json...``` should be parsed correctly."""
        docs = [_make_doc("doc_001", "Investigation content here.")]
        case_dir = _write_case(tmp_path, docs)
        params = _default_params(distractor_ratio=1.0)
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            case_dir=case_dir,
            contradiction_count=1,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm_with_fences,
        )

        assert error is None
        assert labels is not None
        assert len(labels) == 1
        assert labels[0].description == "Expert disagreement on root cause analysis."


class TestErrorHandling:
    """Error cases: no documents, LLM failures."""

    def test_no_documents(self, tmp_path):
        """Should return error when no documents are found."""
        case_dir = tmp_path / "empty_case"
        case_dir.mkdir()
        params = _default_params(distractor_ratio=0.5)
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            case_dir=case_dir,
            contradiction_count=4,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert labels is None
        assert error is not None
        assert "No documents found" in error

    def test_llm_failure(self, tmp_path):
        """Should handle LLM failures gracefully — failed calls produce fewer labels."""
        docs = [_make_doc("doc_001", "Some content.")]
        case_dir = _write_case(tmp_path, docs)

        def failing_llm(prompt, model="test-model", temperature=0):
            return None, "LLM service unavailable"

        params = _default_params(distractor_ratio=1.0)
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            case_dir=case_dir,
            contradiction_count=2,
            params=params,
            seed_mgr=seed_mgr,
            llm=failing_llm,
        )

        assert error is None
        assert labels is not None
        assert len(labels) == 0  # All failed

    def test_malformed_json_response(self, tmp_path):
        """Should handle malformed JSON from LLM gracefully."""
        docs = [_make_doc("doc_001", "Content here.")]
        case_dir = _write_case(tmp_path, docs)

        def bad_json_llm(prompt, model="test-model", temperature=0):
            return "not valid json {{{", None

        params = _default_params(distractor_ratio=1.0)
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            case_dir=case_dir,
            contradiction_count=1,
            params=params,
            seed_mgr=seed_mgr,
            llm=bad_json_llm,
        )

        assert error is None
        assert labels is not None
        assert len(labels) == 0  # Parsing failed, but no hard error


class TestLabelStructure:
    """Verify DistractorLabel has the correct fields."""

    def test_label_fields(self, tmp_path):
        """Each label should have scope, divergence_type, document_references, description."""
        docs = [
            _make_doc("doc_001", "Content A."),
            _make_doc("doc_002", "Content B."),
        ]
        case_dir = _write_case(tmp_path, docs)
        params = _default_params(distractor_ratio=1.0)
        seed_mgr = SeedManager(42)

        labels, error = generate_distractors(
            case_dir=case_dir,
            contradiction_count=2,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None
        for label in labels:
            assert isinstance(label, DistractorLabel)
            assert label.scope in ("intra_doc", "inter_doc")
            assert label.divergence_type in (
                "expert_opinion",
                "preliminary_vs_final",
                "measurement_methodology",
                "uncertainty_expression",
            )
            assert len(label.document_references) >= 1
            assert isinstance(label.description, str)
            assert len(label.description) > 0
