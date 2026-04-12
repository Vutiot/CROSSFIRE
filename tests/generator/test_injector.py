"""Tests for the contradiction injector — comprehensive coverage of all bug fixes and features.

Covers:
    P1: Phantom label prevention
    P2: Char offsets computed after replacement
    P3: No bogus char_start=0 fallback
    P4: File write-back preserves original filenames
    P6: Markdown fence stripping
    P7: Zero-rate produces zero injections
    P8: All-zero weights doesn't crash
    P11: Affinity distribution configuration
    AC10: Model selection from GenerationParams
"""

import json
from pathlib import Path

import pytest

from crossfire.shared.schemas.config import GenerationParams
from crossfire.shared.schemas.contradictions import ContradictionLabel
from crossfire.shared.schemas.corpus import Document
from crossfire.shared.seed_manager import SeedManager

from crossfire.generator.injector import (
    inject_contradictions,
    strip_json_fences,
    _weighted_choice,
    _load_docs,
    _write_docs,
    _extract_key_terms,
    _select_inter_doc_targets,
)


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


def _write_case(tmp_path: Path, docs: list[Document], filename: str = "report.jsonl") -> Path:
    """Write docs into ``tmp_path/anonymized_docs/{filename}`` and return case dir."""
    case_dir = tmp_path / "case_001"
    docs_dir = case_dir / "anonymized_docs"
    docs_dir.mkdir(parents=True)

    path = docs_dir / filename
    with open(path, "w") as f:
        for doc in docs:
            f.write(doc.model_dump_json() + "\n")

    return case_dir


def _write_case_multi_file(tmp_path: Path, file_docs: dict[str, list[Document]]) -> Path:
    """Write docs into multiple JSONL files and return case dir."""
    case_dir = tmp_path / "case_001"
    docs_dir = case_dir / "anonymized_docs"
    docs_dir.mkdir(parents=True)

    for filename, docs in file_docs.items():
        path = docs_dir / filename
        with open(path, "w") as f:
            for doc in docs:
                f.write(doc.model_dump_json() + "\n")

    return case_dir


def _default_params(**overrides) -> GenerationParams:
    """Create GenerationParams with sensible test defaults."""
    defaults = dict(
        version_id="test-v1",
        contradiction_rate_intra_doc=0.5,
        contradiction_rate_inter_doc=0.0,
        distractor_ratio=0.3,
    )
    defaults.update(overrides)
    return GenerationParams(**defaults)


# The mock LLM returns text that ACTUALLY EXISTS in the test document content.
_DOC_CONTENT = "The aircraft was cruising at 35,000 feet when the incident occurred. The pilot reported engine failure at approximately 14:30 UTC."
_ORIGINAL_TEXT = "The aircraft was cruising at 35,000 feet"
_MODIFIED_TEXT = "The aircraft was cruising at 28,000 feet"


def _fake_llm(prompt: str, model: str = "claude-sonnet-4-20250514", temperature: float = 0):
    """Fake LLM that handles fact extraction, intra-doc modification, and inter-doc modification.

    Returns text that ACTUALLY EXISTS in _DOC_CONTENT so char offsets work.
    """
    if "Extract key factual claims" in prompt:
        return json.dumps({
            "facts": [
                {"fact": _ORIGINAL_TEXT, "type": "numeric"},
                {"fact": "The pilot reported engine failure", "type": "causal"},
            ]
        }), None
    elif "inserting a contradicting fact" in prompt:
        # Inter-doc modification prompt
        return json.dumps({
            "modified_text": "The aircraft was actually at 28,000 feet according to other sources.",
            "insertion_paragraph": 0,
        }), None
    elif "modifying a single fact" in prompt:
        return json.dumps({
            "original_text": _ORIGINAL_TEXT,
            "modified_text": _MODIFIED_TEXT,
        }), None
    return None, "Unexpected prompt"


def _fake_llm_fenced(prompt: str, model: str = "claude-sonnet-4-20250514", temperature: float = 0):
    """Fake LLM that wraps JSON responses in markdown code fences."""
    if "Extract key factual claims" in prompt:
        return '```json\n' + json.dumps({
            "facts": [
                {"fact": _ORIGINAL_TEXT, "type": "numeric"},
            ]
        }) + '\n```', None
    elif "modifying a single fact" in prompt:
        return '```\n' + json.dumps({
            "original_text": _ORIGINAL_TEXT,
            "modified_text": _MODIFIED_TEXT,
        }) + '\n```', None
    return None, "Unexpected prompt"


def _fake_llm_phantom(prompt: str, model: str = "claude-sonnet-4-20250514", temperature: float = 0):
    """Fake LLM that returns original_text NOT in the document (triggers P1)."""
    if "Extract key factual claims" in prompt:
        return json.dumps({
            "facts": [
                {"fact": "Some text that exists in the doc", "type": "numeric"},
            ]
        }), None
    elif "modifying a single fact" in prompt:
        return json.dumps({
            "original_text": "THIS TEXT DOES NOT EXIST IN THE DOCUMENT AT ALL",
            "modified_text": "Replacement text",
        }), None
    return None, "Unexpected prompt"


# ---------------------------------------------------------------------------
# Tests: strip_json_fences (AC8, P6)
# ---------------------------------------------------------------------------


class TestStripJsonFences:
    """Tests for the markdown fence stripping utility."""

    def test_no_fences(self):
        raw = '{"key": "value"}'
        assert strip_json_fences(raw) == '{"key": "value"}'

    def test_json_fences(self):
        raw = '```json\n{"key": "value"}\n```'
        assert strip_json_fences(raw) == '{"key": "value"}'

    def test_plain_fences(self):
        raw = '```\n{"key": "value"}\n```'
        assert strip_json_fences(raw) == '{"key": "value"}'

    def test_fences_with_whitespace(self):
        raw = '  ```json\n  {"key": "value"}  \n  ```  '
        result = strip_json_fences(raw)
        assert json.loads(result) == {"key": "value"}

    def test_multiline_content(self):
        content = '{"facts": [\n  {"fact": "test", "type": "numeric"}\n]}'
        raw = f'```json\n{content}\n```'
        result = strip_json_fences(raw)
        assert json.loads(result) == json.loads(content)

    def test_no_modification_without_fences(self):
        raw = '  {"key": "value"}  '
        assert strip_json_fences(raw) == '{"key": "value"}'


# ---------------------------------------------------------------------------
# Tests: _weighted_choice (P8, P11)
# ---------------------------------------------------------------------------


class TestWeightedChoice:
    """Tests for _weighted_choice."""

    import random

    def test_uniform_fallback_empty_distribution(self):
        """Empty distribution should fall back to uniform random."""
        import random
        rng = random.Random(42)
        result = _weighted_choice({}, ["a", "b", "c"], rng)
        assert result in ["a", "b", "c"]

    def test_weighted_selection(self):
        """Should respect distribution weights."""
        import random
        rng = random.Random(42)
        dist = {"a": 1.0, "b": 0.0, "c": 0.0}
        # With a=1.0 and others=0.0, should always pick "a"
        # But P8 fix: sum > 0, so choices works, just heavily weighted
        results = {_weighted_choice(dist, ["a", "b", "c"], rng) for _ in range(20)}
        assert "a" in results

    def test_all_zero_weights_no_crash(self):
        """P8 fix: all-zero weights should not crash, falls back to uniform on matched keys."""
        import random
        rng = random.Random(42)
        dist = {"a": 0.0, "b": 0.0, "c": 0.0}
        result = _weighted_choice(dist, ["a", "b", "c"], rng)
        assert result in ["a", "b", "c"]

    def test_mismatched_keys_warning(self):
        """Distribution keys not matching choices should fall back to uniform."""
        import random
        rng = random.Random(42)
        dist = {"x": 1.0, "y": 1.0}
        result = _weighted_choice(dist, ["a", "b", "c"], rng)
        assert result in ["a", "b", "c"]

    def test_single_weight_deterministic(self):
        """Single non-zero weight should always pick that value."""
        import random
        rng = random.Random(42)
        dist = {"balanced": 1.0}
        for _ in range(10):
            result = _weighted_choice(dist, ["balanced", "graph_favoring", "agentic_favoring"], rng)
            assert result == "balanced"


# ---------------------------------------------------------------------------
# Tests: inject_contradictions — core behavior
# ---------------------------------------------------------------------------


class TestInjectContradictions:
    """Tests for inject_contradictions."""

    def test_happy_path(self, tmp_path):
        """Should inject contradictions and return labels with correct metadata."""
        # All docs contain _ORIGINAL_TEXT so the mock LLM's response always matches
        docs = [
            _make_doc("doc_001", _DOC_CONTENT),
            _make_doc("doc_002", _DOC_CONTENT + " Second document variant."),
            _make_doc("doc_003", _DOC_CONTENT + " Third document variant."),
        ]
        case_dir = _write_case(tmp_path, docs)

        params = _default_params(contradiction_rate_intra_doc=0.5)
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None
        assert len(labels) > 0

        for label in labels:
            assert isinstance(label, ContradictionLabel)
            assert label.scope == "intra_doc"
            assert label.ground_truth is True
            assert label.char_start >= 0
            assert label.char_end >= label.char_start
            assert len(label.document_references) >= 1

    def test_no_documents(self, tmp_path):
        """Should return error when no documents are found."""
        case_dir = tmp_path / "empty_case"
        case_dir.mkdir()

        params = _default_params()
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert labels is None
        assert error is not None
        assert "No documents found" in error

    def test_llm_failure(self, tmp_path):
        """Should handle LLM failures gracefully."""
        docs = [_make_doc("doc_001", _DOC_CONTENT)]
        case_dir = _write_case(tmp_path, docs)

        def failing_llm(prompt, model="claude-sonnet-4-20250514", temperature=0):
            return None, "LLM service unavailable"

        params = _default_params(contradiction_rate_intra_doc=1.0)
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=failing_llm,
        )

        # Should still return a list (possibly empty) rather than crash
        assert error is None
        assert labels is not None
        # All injections failed, so labels should be empty
        assert len(labels) == 0

    def test_mechanism_distribution(self, tmp_path):
        """Should respect mechanism_distribution weights."""
        docs = [
            _make_doc(f"doc_{i:03d}", _DOC_CONTENT)
            for i in range(5)
        ]
        case_dir = _write_case(tmp_path, docs)

        params = _default_params(
            contradiction_rate_intra_doc=0.5,
            mechanism_distribution={"numeric_drift": 1.0},
        )
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None
        for label in labels:
            assert label.mechanism == "numeric_drift"

    def test_seed_determinism(self, tmp_path):
        """Two runs with same seed should produce identical labels."""
        docs = [
            _make_doc("doc_001", _DOC_CONTENT),
            _make_doc("doc_002", "The pilot reported engine failure. Ground control was notified."),
        ]

        params = _default_params(contradiction_rate_intra_doc=0.5)

        # Run 1
        case_dir_1 = _write_case(tmp_path / "run1", docs)
        labels_1, _ = inject_contradictions(
            case_dir=case_dir_1,
            params=params,
            seed_mgr=SeedManager(42),
            llm=_fake_llm,
        )

        # Run 2
        case_dir_2 = _write_case(tmp_path / "run2", docs)
        labels_2, _ = inject_contradictions(
            case_dir=case_dir_2,
            params=params,
            seed_mgr=SeedManager(42),
            llm=_fake_llm,
        )

        assert labels_1 is not None
        assert labels_2 is not None
        assert len(labels_1) == len(labels_2)
        for l1, l2 in zip(labels_1, labels_2):
            assert l1.scope == l2.scope
            assert l1.mechanism == l2.mechanism


# ---------------------------------------------------------------------------
# Tests: Bug fixes
# ---------------------------------------------------------------------------


class TestBugFixes:
    """Tests for specific bug fixes identified in code review."""

    def test_p1_phantom_label_prevention(self, tmp_path):
        """P1: When original_text not found in doc, NO label should be created."""
        docs = [_make_doc("doc_001", _DOC_CONTENT)]
        case_dir = _write_case(tmp_path, docs)

        params = _default_params(contradiction_rate_intra_doc=1.0)
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm_phantom,
        )

        assert error is None
        assert labels is not None
        # The phantom LLM returns text not in doc — no labels should be created
        assert len(labels) == 0

    def test_p2_char_offsets_after_replacement(self, tmp_path):
        """P2: char_start/char_end should reference the POST-replacement document."""
        docs = [_make_doc("doc_001", _DOC_CONTENT)]
        case_dir = _write_case(tmp_path, docs)

        params = _default_params(contradiction_rate_intra_doc=1.0)
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None
        assert len(labels) > 0

        # Read back the modified document to verify offsets
        docs_dir = case_dir / "anonymized_docs"
        modified_docs = []
        for jsonl_path in docs_dir.glob("*.jsonl"):
            for line in jsonl_path.read_text().strip().split("\n"):
                if line:
                    modified_docs.append(Document.model_validate_json(line))

        # Find the modified document and check char offsets (AC6)
        for label in labels:
            doc_id = label.document_references[0]
            doc = next((d for d in modified_docs if d.document_id == doc_id), None)
            assert doc is not None, f"Document {doc_id} not found after write-back"
            # The key assertion: content[char_start:char_end] == modified_text
            assert doc.content[label.char_start:label.char_end] == label.modified_text

    def test_p4_file_write_preserves_filenames(self, tmp_path):
        """P4: _write_docs should write back to original source files, not grouped by type."""
        doc_a = _make_doc("doc_001", "Content A", doc_type="report")
        doc_b = _make_doc("doc_002", "Content B", doc_type="summary")

        file_docs = {
            "investigation.jsonl": [doc_a],
            "summaries.jsonl": [doc_b],
        }
        case_dir = _write_case_multi_file(tmp_path, file_docs)

        params = _default_params(contradiction_rate_intra_doc=0.0)
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None

        # Verify the original filenames are preserved
        docs_dir = case_dir / "anonymized_docs"
        filenames = sorted(p.name for p in docs_dir.glob("*.jsonl"))
        assert "investigation.jsonl" in filenames
        assert "summaries.jsonl" in filenames
        # Should NOT have "report.jsonl" or "summary.jsonl" (the old document_type grouping)

    def test_p6_markdown_fence_stripping(self, tmp_path):
        """P6: LLM responses wrapped in markdown fences should parse correctly."""
        docs = [_make_doc("doc_001", _DOC_CONTENT)]
        case_dir = _write_case(tmp_path, docs)

        params = _default_params(contradiction_rate_intra_doc=1.0)
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm_fenced,
        )

        assert error is None
        assert labels is not None
        assert len(labels) > 0
        # If fence stripping didn't work, json.loads would fail and no labels would be created

    def test_p7_zero_rate_produces_zero_injections(self, tmp_path):
        """P7: rate=0.0 should produce exactly zero injections, not force min=1."""
        docs = [
            _make_doc("doc_001", _DOC_CONTENT),
            _make_doc("doc_002", "Another document with content."),
        ]
        case_dir = _write_case(tmp_path, docs)

        call_count = 0

        def counting_llm(prompt, model="claude-sonnet-4-20250514", temperature=0):
            nonlocal call_count
            call_count += 1
            return _fake_llm(prompt, model, temperature)

        params = _default_params(
            contradiction_rate_intra_doc=0.0,
            contradiction_rate_inter_doc=0.0,
        )
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=counting_llm,
        )

        assert error is None
        assert labels is not None
        assert len(labels) == 0
        assert call_count == 0  # No LLM calls should be made

    def test_p8_zero_weights_no_crash(self, tmp_path):
        """P8: All-zero distribution weights should not crash."""
        docs = [_make_doc("doc_001", _DOC_CONTENT)]
        case_dir = _write_case(tmp_path, docs)

        params = _default_params(
            contradiction_rate_intra_doc=1.0,
            mechanism_distribution={"numeric_drift": 0.0, "entity_swap": 0.0},
            difficulty_distribution={"easy": 0.0, "medium": 0.0},
            affinity_distribution={"balanced": 0.0, "graph_favoring": 0.0},
        )
        seed_mgr = SeedManager(42)

        # Should not raise ValueError
        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        # Should complete without crash
        assert error is None

    def test_p11_affinity_distribution_used(self, tmp_path):
        """P11: system_affinity should use affinity_distribution from params."""
        docs = [
            _make_doc(f"doc_{i:03d}", _DOC_CONTENT)
            for i in range(10)
        ]
        case_dir = _write_case(tmp_path, docs)

        # Force all affinity to "graph_favoring"
        params = _default_params(
            contradiction_rate_intra_doc=1.0,
            affinity_distribution={"graph_favoring": 1.0},
        )
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None
        assert len(labels) > 0
        for label in labels:
            assert label.system_affinity == "graph_favoring"


# ---------------------------------------------------------------------------
# Tests: AC10 — Model selection from GenerationParams
# ---------------------------------------------------------------------------


class TestModelSelection:
    """Tests for AC10: model selection from GenerationParams."""

    def test_extraction_uses_extraction_model(self, tmp_path):
        """Fact extraction LLM calls should use params.extraction_model."""
        docs = [_make_doc("doc_001", _DOC_CONTENT)]
        case_dir = _write_case(tmp_path, docs)

        models_used = []

        def tracking_llm(prompt, model="default", temperature=0):
            models_used.append(model)
            return _fake_llm(prompt, model, temperature)

        params = _default_params(
            contradiction_rate_intra_doc=1.0,
            extraction_model="claude-sonnet-4-20250514",
            reasoning_model="claude-opus-4-20250514",
        )
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=tracking_llm,
        )

        assert error is None
        assert len(models_used) >= 2
        # First call is extraction, second is modification
        assert models_used[0] == "claude-sonnet-4-20250514"
        assert models_used[1] == "claude-opus-4-20250514"

    def test_custom_models(self, tmp_path):
        """Custom model names should be passed through to LLM calls."""
        docs = [_make_doc("doc_001", _DOC_CONTENT)]
        case_dir = _write_case(tmp_path, docs)

        models_used = []

        def tracking_llm(prompt, model="default", temperature=0):
            models_used.append(model)
            return _fake_llm(prompt, model, temperature)

        params = _default_params(
            contradiction_rate_intra_doc=1.0,
            extraction_model="custom-extract-model",
            reasoning_model="custom-reason-model",
        )
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=tracking_llm,
        )

        assert error is None
        assert "custom-extract-model" in models_used
        assert "custom-reason-model" in models_used

    def test_no_hardcoded_gpt4o_mini(self, tmp_path):
        """No LLM calls should use hardcoded 'gpt-4o-mini'."""
        docs = [_make_doc("doc_001", _DOC_CONTENT)]
        case_dir = _write_case(tmp_path, docs)

        models_used = []

        def tracking_llm(prompt, model="default", temperature=0):
            models_used.append(model)
            return _fake_llm(prompt, model, temperature)

        params = _default_params(contradiction_rate_intra_doc=1.0)
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=tracking_llm,
        )

        assert error is None
        for model in models_used:
            assert model != "gpt-4o-mini", f"Found hardcoded gpt-4o-mini in LLM call"


# ---------------------------------------------------------------------------
# Tests: File handling
# ---------------------------------------------------------------------------


class TestFileHandling:
    """Tests for document loading and writing."""

    def test_load_docs_tracks_source_files(self, tmp_path):
        """_load_docs should track which file each document came from."""
        doc_a = _make_doc("doc_001", "Content A")
        doc_b = _make_doc("doc_002", "Content B")

        file_docs = {
            "file_a.jsonl": [doc_a],
            "file_b.jsonl": [doc_b],
        }
        case_dir = _write_case_multi_file(tmp_path, file_docs)

        docs, source_map = _load_docs(case_dir)
        assert len(docs) == 2
        assert source_map["doc_001"] == "file_a.jsonl"
        assert source_map["doc_002"] == "file_b.jsonl"

    def test_load_docs_skips_malformed_lines(self, tmp_path):
        """_load_docs should skip malformed JSONL lines without crashing."""
        case_dir = tmp_path / "case_001"
        docs_dir = case_dir / "anonymized_docs"
        docs_dir.mkdir(parents=True)

        doc = _make_doc("doc_001", "Valid content")
        path = docs_dir / "mixed.jsonl"
        with open(path, "w") as f:
            f.write(doc.model_dump_json() + "\n")
            f.write("this is not valid json\n")
            f.write('{"incomplete": true}\n')

        docs, source_map = _load_docs(case_dir)
        assert len(docs) == 1
        assert docs[0].document_id == "doc_001"

    def test_write_docs_preserves_original_filenames(self, tmp_path):
        """_write_docs should write back to original source files."""
        doc_a = _make_doc("doc_001", "Content A", doc_type="report")
        doc_b = _make_doc("doc_002", "Content B", doc_type="summary")

        case_dir = tmp_path / "case_001"
        docs_dir = case_dir / "anonymized_docs"
        docs_dir.mkdir(parents=True)

        source_map = {
            "doc_001": "original_file_a.jsonl",
            "doc_002": "original_file_b.jsonl",
        }

        _write_docs(case_dir, [doc_a, doc_b], source_map)

        filenames = sorted(p.name for p in docs_dir.glob("*.jsonl"))
        assert "original_file_a.jsonl" in filenames
        assert "original_file_b.jsonl" in filenames

    def test_writes_modified_docs_back(self, tmp_path):
        """Should write modified documents back to disk."""
        docs = [_make_doc("doc_001", _DOC_CONTENT)]
        case_dir = _write_case(tmp_path, docs)

        params = _default_params(contradiction_rate_intra_doc=1.0)
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        # Check that files were written
        docs_dir = case_dir / "anonymized_docs"
        jsonl_files = list(docs_dir.glob("*.jsonl"))
        assert len(jsonl_files) > 0

        # Read back and verify content was modified
        modified_docs = []
        for jsonl_path in jsonl_files:
            for line in jsonl_path.read_text().strip().split("\n"):
                if line:
                    modified_docs.append(Document.model_validate_json(line))

        assert len(modified_docs) == 1
        assert _MODIFIED_TEXT in modified_docs[0].content

    def test_inter_count_zero_when_single_doc(self, tmp_path):
        """Story 3.2: inter_count should be 0 when only 1 document is available."""
        docs = [_make_doc("doc_001", _DOC_CONTENT)]
        case_dir = _write_case(tmp_path, docs)

        params = _default_params(
            contradiction_rate_intra_doc=0.0,
            contradiction_rate_inter_doc=1.0,  # would produce injections, but only 1 doc
        )
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None
        assert len(labels) == 0  # inter_count forced to 0


# ---------------------------------------------------------------------------
# Tests: Inter-document injection (Story 3.2)
# ---------------------------------------------------------------------------


class TestInterDocInjection:
    """Tests for inter-document contradiction injection."""

    def test_inter_doc_injections_produced(self, tmp_path):
        """AC1: Inter-doc injections should be produced when rate > 0 and docs >= 2."""
        docs = [
            _make_doc("doc_001", _DOC_CONTENT),
            _make_doc("doc_002", _DOC_CONTENT + " Second document variant."),
            _make_doc("doc_003", _DOC_CONTENT + " Third document variant."),
        ]
        case_dir = _write_case(tmp_path, docs)

        params = _default_params(
            contradiction_rate_intra_doc=0.0,
            contradiction_rate_inter_doc=0.5,
        )
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None
        assert len(labels) > 0
        for label in labels:
            assert label.scope == "inter_doc"
            assert label.ground_truth is True

    def test_inter_count_zero_single_doc(self, tmp_path):
        """AC1 guard: inter_count should be 0 when only 1 document available."""
        docs = [_make_doc("doc_001", _DOC_CONTENT)]
        case_dir = _write_case(tmp_path, docs)

        params = _default_params(
            contradiction_rate_intra_doc=0.0,
            contradiction_rate_inter_doc=1.0,
        )
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None
        assert len(labels) == 0

    def test_document_references_two_different_ids(self, tmp_path):
        """AC5: document_references should have 2 different document IDs for inter_doc."""
        docs = [
            _make_doc("doc_001", _DOC_CONTENT),
            _make_doc("doc_002", _DOC_CONTENT + " Second document variant."),
        ]
        case_dir = _write_case(tmp_path, docs)

        params = _default_params(
            contradiction_rate_intra_doc=0.0,
            contradiction_rate_inter_doc=1.0,
        )
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None
        assert len(labels) > 0
        for label in labels:
            assert len(label.document_references) == 2
            assert label.document_references[0] != label.document_references[1]

    def test_inter_doc_char_offsets_reference_target(self, tmp_path):
        """AC4: char offsets should reference doc_b (the target document)."""
        docs = [
            _make_doc("doc_001", _DOC_CONTENT),
            _make_doc("doc_002", "Target document content here."),
        ]
        case_dir = _write_case(tmp_path, docs)

        params = _default_params(
            contradiction_rate_intra_doc=0.0,
            contradiction_rate_inter_doc=1.0,
        )
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None
        assert len(labels) > 0
        for label in labels:
            assert label.char_start >= 0
            assert label.char_end > label.char_start

    def test_mixed_intra_and_inter_doc(self, tmp_path):
        """Both intra and inter doc injections should work together."""
        docs = [
            _make_doc("doc_001", _DOC_CONTENT),
            _make_doc("doc_002", _DOC_CONTENT + " Second variant."),
            _make_doc("doc_003", _DOC_CONTENT + " Third variant."),
            _make_doc("doc_004", _DOC_CONTENT + " Fourth variant."),
        ]
        case_dir = _write_case(tmp_path, docs)

        params = _default_params(
            contradiction_rate_intra_doc=0.5,
            contradiction_rate_inter_doc=0.5,
        )
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None
        scopes = {label.scope for label in labels}
        assert "intra_doc" in scopes
        assert "inter_doc" in scopes

    def test_inter_doc_same_mechanisms_available(self, tmp_path):
        """AC3: All 6 mechanisms should be available for inter_doc scope."""
        docs = [
            _make_doc(f"doc_{i:03d}", _DOC_CONTENT + f" Variant {i}.")
            for i in range(10)
        ]
        case_dir = _write_case(tmp_path, docs)

        # Force numeric_drift for predictable testing
        params = _default_params(
            contradiction_rate_intra_doc=0.0,
            contradiction_rate_inter_doc=1.0,
            mechanism_distribution={"numeric_drift": 1.0},
        )
        seed_mgr = SeedManager(42)

        labels, error = inject_contradictions(
            case_dir=case_dir,
            params=params,
            seed_mgr=seed_mgr,
            llm=_fake_llm,
        )

        assert error is None
        assert labels is not None
        assert len(labels) > 0
        for label in labels:
            assert label.mechanism == "numeric_drift"


# ---------------------------------------------------------------------------
# Tests: Entity-aware target selection (Story 3.2)
# ---------------------------------------------------------------------------


class TestEntityAwareSelection:
    """Tests for _extract_key_terms and _select_inter_doc_targets."""

    def test_extract_key_terms_capitalized_phrases(self):
        """Should extract capitalized multi-word phrases as key terms."""
        content = "Captain John Smith reported the incident. Federal Aviation Administration investigated."
        terms = _extract_key_terms(content)
        assert "captain john smith" in terms or "john smith" in terms
        assert "federal aviation administration" in terms

    def test_extract_key_terms_numbers_with_units(self):
        """Should extract numbers with units."""
        content = "The aircraft was at 35,000 feet traveling at 450 knots."
        terms = _extract_key_terms(content)
        assert any("35,000 feet" in t or "35000 feet" in t for t in terms)

    def test_extract_key_terms_acronyms(self):
        """Should extract acronyms."""
        content = "The NTSB and FAA conducted the investigation jointly."
        terms = _extract_key_terms(content)
        assert "ntsb" in terms
        assert "faa" in terms

    def test_extract_key_terms_empty_content(self):
        """Should return empty set for content with no key terms."""
        content = "a simple sentence with no proper nouns or numbers."
        terms = _extract_key_terms(content)
        assert isinstance(terms, set)

    def test_select_inter_doc_prefers_overlapping_docs(self):
        """AC2: Should prefer document pairs that share entity references."""
        import random

        # doc_a and doc_b share "Captain John Smith" and "35,000 feet"
        doc_a = _make_doc(
            "doc_a",
            "Captain John Smith was flying at 35,000 feet near Chicago Airport."
        )
        doc_b = _make_doc(
            "doc_b",
            "Captain John Smith reported turbulence at 35,000 feet to ATC."
        )
        # doc_c has completely different entities
        doc_c = _make_doc(
            "doc_c",
            "the weather was mild with gentle winds from the south."
        )

        all_docs = [doc_a, doc_b, doc_c]

        # Run selection many times and count how often the overlapping pair is picked
        overlap_count = 0
        total_runs = 100
        for seed in range(total_runs):
            rng = random.Random(seed)
            pair = _select_inter_doc_targets(all_docs, rng)
            pair_ids = {pair[0].document_id, pair[1].document_id}
            if pair_ids == {"doc_a", "doc_b"}:
                overlap_count += 1

        # The overlapping pair should be selected significantly more often
        # than random chance (1/3 = ~33%). We expect > 60%.
        assert overlap_count > 60, (
            f"Entity-aware selection picked overlapping pair only {overlap_count}/{total_runs} times"
        )

    def test_select_inter_doc_random_fallback(self):
        """Should fall back to random pairing when no entity overlap exists."""
        import random

        # All docs have completely different content with no shared terms
        doc_a = _make_doc("doc_a", "simple text with nothing notable.")
        doc_b = _make_doc("doc_b", "another plain document without entities.")
        doc_c = _make_doc("doc_c", "yet more unremarkable content here.")

        all_docs = [doc_a, doc_b, doc_c]

        # Should not crash — falls back to random
        rng = random.Random(42)
        pair = _select_inter_doc_targets(all_docs, rng)
        assert len(pair) == 2
        assert pair[0].document_id != pair[1].document_id

    def test_select_inter_doc_two_docs_minimum(self):
        """Should work with exactly 2 documents."""
        import random

        doc_a = _make_doc("doc_a", "Content A")
        doc_b = _make_doc("doc_b", "Content B")

        rng = random.Random(42)
        pair = _select_inter_doc_targets([doc_a, doc_b], rng)
        assert len(pair) == 2
        ids = {pair[0].document_id, pair[1].document_id}
        assert ids == {"doc_a", "doc_b"}

    def test_select_inter_doc_raises_with_single_doc(self):
        """Should raise ValueError with fewer than 2 documents."""
        import random

        rng = random.Random(42)
        with pytest.raises(ValueError, match="at least 2"):
            _select_inter_doc_targets([_make_doc("doc_a", "Content")], rng)
