"""Tests for docket HTML parsing."""

from crossfire.generator.scraper.docket_parser import parse_docket_html


class TestParseDocketHtml:
    def test_parses_all_documents(self, sample_docket_html):
        manifest = parse_docket_html(sample_docket_html, "TEST001", "https://example.com")
        assert manifest.ntsb_id == "TEST001"
        assert manifest.document_count == 8

    def test_extracts_document_fields(self, sample_docket_html):
        manifest = parse_docket_html(sample_docket_html, "TEST001", "https://example.com")
        doc = manifest.documents[0]
        assert doc.item_number == 1
        assert "OPERATIONAL FACTORS" in doc.title
        assert doc.file_type == "pdf"
        assert doc.page_count == 36
        assert "docBLOB" in doc.download_url

    def test_detects_csv_file_type(self, sample_docket_html):
        manifest = parse_docket_html(sample_docket_html, "TEST001", "https://example.com")
        csv_doc = next(d for d in manifest.documents if d.item_number == 7)
        assert csv_doc.file_type == "csv"

    def test_infers_group_from_prefix(self, sample_docket_html):
        manifest = parse_docket_html(sample_docket_html, "TEST001", "https://example.com")
        doc = manifest.documents[0]  # 2-A OPERATIONAL FACTORS
        assert doc.group == "Operational Factors"

    def test_infers_group_from_keyword(self, sample_docket_html):
        manifest = parse_docket_html(sample_docket_html, "TEST001", "https://example.com")
        fdr_doc = next(d for d in manifest.documents if d.item_number == 3)
        assert fdr_doc.group == "Flight Data Recorder"

    def test_handles_empty_html(self):
        manifest = parse_docket_html("<html><body></body></html>", "EMPTY", "https://example.com")
        assert manifest.document_count == 0
        assert manifest.documents == []
