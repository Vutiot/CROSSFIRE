"""Tests for the document factory."""

import pytest

from crossfire.generator.templates.document_factory import create_document
from crossfire.shared.schemas.corpus import Document

from .conftest import mock_llm_call


class TestCreateDocument:
    def test_returns_document_on_success(self, sample_entities, sample_context, seed_mgr):
        doc, error = create_document(
            "investigation_report", sample_entities, sample_context, mock_llm_call, seed_mgr
        )
        assert error is None
        assert isinstance(doc, Document)
        assert doc.document_type == "investigation_report"

    def test_document_id_format(self, sample_entities, sample_context, seed_mgr):
        doc, _ = create_document(
            "technical_analysis", sample_entities, sample_context, mock_llm_call, seed_mgr, index=5
        )
        assert doc.id == "sub_001_technical_analysis_005"

    def test_subcorpus_id_set(self, sample_entities, sample_context, seed_mgr):
        doc, _ = create_document(
            "witness_testimony", sample_entities, sample_context, mock_llm_call, seed_mgr
        )
        assert doc.subcorpus_id == "sub_001"

    def test_reliability_signal_in_range(self, sample_entities, sample_context, seed_mgr):
        doc, _ = create_document(
            "investigation_report", sample_entities, sample_context, mock_llm_call, seed_mgr
        )
        assert 0.0 <= doc.reliability_signal <= 1.0

    def test_content_not_empty(self, sample_entities, sample_context, seed_mgr):
        doc, _ = create_document(
            "internal_memo", sample_entities, sample_context, mock_llm_call, seed_mgr
        )
        assert len(doc.content) > 0

    @pytest.mark.parametrize("doc_type", [
        "investigation_report",
        "technical_analysis",
        "witness_testimony",
        "regulatory_filing",
        "press_coverage",
        "expert_deposition",
        "internal_memo",
        "preliminary_report",
    ])
    def test_all_8_types_dispatch(self, doc_type, sample_entities, sample_context, seed_mgr):
        doc, error = create_document(doc_type, sample_entities, sample_context, mock_llm_call, seed_mgr)
        assert error is None
        assert doc.document_type == doc_type

    def test_unknown_type_returns_error(self, sample_entities, sample_context, seed_mgr):
        doc, error = create_document("unknown_type", sample_entities, sample_context, mock_llm_call, seed_mgr)
        assert doc is None
        assert "Unknown document type" in error

    def test_llm_error_propagated(self, sample_entities, sample_context, seed_mgr):
        def failing_llm(prompt, **kwargs):
            return None, "API quota exceeded"

        doc, error = create_document(
            "investigation_report", sample_entities, sample_context, failing_llm, seed_mgr
        )
        assert doc is None
        assert "API quota exceeded" in error

    def test_deterministic_output(self, sample_entities, sample_context, seed_mgr):
        doc1, _ = create_document("investigation_report", sample_entities, sample_context, mock_llm_call, seed_mgr)
        seed_mgr2 = type(seed_mgr)(master_seed=42)
        doc2, _ = create_document("investigation_report", sample_entities, sample_context, mock_llm_call, seed_mgr2)
        assert doc1.id == doc2.id
        assert doc1.reliability_signal == doc2.reliability_signal
        assert doc1.content == doc2.content
