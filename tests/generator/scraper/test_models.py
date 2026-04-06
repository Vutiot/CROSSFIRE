"""Tests for scraper Pydantic models."""

import json

import pytest
from pydantic import ValidationError

from crossfire.generator.scraper.config import QualityGates, QualityThresholds, ScraperConfig
from crossfire.generator.scraper.models import (
    DocumentEntry,
    DocketManifest,
    DocketSummary,
    ExtractionQuality,
    ExtractedDocument,
    GateResult,
    NTSBAnalysisReport,
    QualityGateResults,
)


class TestScraperConfig:
    def test_default_config(self):
        config = ScraperConfig()
        assert len(config.target_dockets) == 8
        assert config.request_delay == 1.5
        assert config.max_retries == 3
        assert config.max_iterations == 3

    def test_quality_thresholds_defaults(self):
        t = QualityThresholds()
        assert t.min_char_ratio == 0.85
        assert t.min_word_count == 100

    def test_quality_gates_defaults(self):
        g = QualityGates()
        assert g.min_dockets_with_docs == 5
        assert g.min_shared_entities == 10

    def test_invalid_char_ratio_rejected(self):
        with pytest.raises(ValidationError):
            QualityThresholds(min_char_ratio=1.5)


class TestDocumentModels:
    def test_document_entry_creation(self):
        entry = DocumentEntry(
            item_number=1,
            title="TEST REPORT",
            file_type="pdf",
            page_count=10,
            download_url="/Docket/Document/docBLOB?ID=123",
        )
        assert entry.item_number == 1
        assert entry.group == ""

    def test_docket_manifest_serialization(self):
        manifest = DocketManifest(
            ntsb_id="DCA24MA063",
            url="https://data.ntsb.gov/Docket/?NTSBNumber=DCA24MA063",
            document_count=2,
            documents=[
                DocumentEntry(item_number=1, title="Report", file_type="pdf", download_url="/doc1"),
                DocumentEntry(item_number=2, title="Interview", file_type="pdf", download_url="/doc2"),
            ],
        )
        data = json.loads(manifest.model_dump_json())
        assert data["ntsb_id"] == "DCA24MA063"
        assert len(data["documents"]) == 2

    def test_extraction_quality_bounds(self):
        with pytest.raises(ValidationError):
            ExtractionQuality(char_ratio=1.5, avg_word_length=5.0, word_count=100, line_count=10)


class TestReportModel:
    def test_empty_report_creation(self):
        report = NTSBAnalysisReport(generated_at="2024-01-01T00:00:00Z")
        assert report.dockets_analyzed == []
        assert report.document_type_taxonomy.types == []

    def test_report_round_trip(self):
        report = NTSBAnalysisReport(
            generated_at="2024-01-01T00:00:00Z",
            dockets_analyzed=[
                DocketSummary(ntsb_id="TEST001", total_documents=10, clean_documents=8, clean_rate=0.8)
            ],
            data_quality_notes=["Test note"],
            synthesis_recommendations=["Use structured sections"],
        )
        json_str = report.model_dump_json()
        restored = NTSBAnalysisReport.model_validate_json(json_str)
        assert restored.dockets_analyzed[0].ntsb_id == "TEST001"
        assert len(restored.synthesis_recommendations) == 1


class TestQualityGateResults:
    def test_all_pass(self):
        results = QualityGateResults(
            passed=True,
            gates=[GateResult(name="G1", passed=True, metric="x", threshold="5", actual="6")],
        )
        assert results.passed is True
        assert results.failed_gates == []

    def test_some_fail(self):
        results = QualityGateResults(
            passed=False,
            gates=[
                GateResult(name="G1", passed=True, metric="x", threshold="5", actual="6"),
                GateResult(name="G2", passed=False, metric="y", threshold="80%", actual="60%"),
            ],
            failed_gates=["G2"],
        )
        assert results.passed is False
        assert "G2" in results.failed_gates
