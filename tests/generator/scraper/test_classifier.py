"""Tests for document type classification."""

import pytest

from crossfire.generator.scraper.classifier import classify_document
from crossfire.generator.scraper.models import ExtractedDocument


def _make_doc(title: str, group: str = "") -> ExtractedDocument:
    return ExtractedDocument(ntsb_id="TEST", item_number=1, title=title, file_type="pdf", group=group)


class TestClassifyDocument:
    @pytest.mark.parametrize("title,expected", [
        ("2-A OPERATIONAL FACTORS - GROUP CHAIRMAN FACTUAL REPORT", "investigation_report"),
        ("STRUCTURES GROUP CHAIR'S FACTUAL REPORT", "investigation_report"),
        ("SURVIVAL FACTORS GROUP CHAIR'S FACTUAL REPORT", "investigation_report"),
    ])
    def test_investigation_report(self, title, expected):
        assert classify_document(_make_doc(title)) == expected

    @pytest.mark.parametrize("title,expected", [
        ("10-A FLIGHT DATA RECORDER REPORT", "technical_analysis"),
        ("COCKPIT VOICE RECORDER REPORT", "technical_analysis"),
        ("MATERIALS LABORATORY REPORT", "technical_analysis"),
    ])
    def test_technical_analysis(self, title, expected):
        assert classify_document(_make_doc(title)) == expected

    @pytest.mark.parametrize("title,expected", [
        ("2-B CREW INTERVIEW TRANSCRIPTS AND STATEMENTS", "witness_testimony"),
        ("PASSENGER INTERVIEW SUMMARIES", "witness_testimony"),
        ("FLIGHT ATTENDANTS INTERVIEW TRANSCRIPTS", "witness_testimony"),
    ])
    def test_witness_testimony(self, title, expected):
        assert classify_document(_make_doc(title)) == expected

    @pytest.mark.parametrize("title,expected", [
        ("FAA OVERSIGHT PRESENTATION", "regulatory_filing"),
        ("EXPLANATION OF AD COMPLIANCE IN PRODUCTION", "regulatory_filing"),
        ("FAA SMS RULE OVERVIEW", "regulatory_filing"),
    ])
    def test_regulatory_filing(self, title, expected):
        assert classify_document(_make_doc(title)) == expected

    @pytest.mark.parametrize("title,expected", [
        ("BOEING QUALITY ALERT 2023-0056-AR", "internal_memo"),
        ("BCA QMS DOCUMENT CONTROL", "internal_memo"),
        ("PROCESSING SPEAK UP REPORTS", "internal_memo"),
        ("FLIGHT OPS TRAINING BULLETIN", "internal_memo"),
    ])
    def test_internal_memo(self, title, expected):
        assert classify_document(_make_doc(title)) == expected

    @pytest.mark.parametrize("title,expected", [
        ("ALASKA AIRLINES HEARING SUBMISSION", "expert_deposition"),
        ("SPIRIT AEROSYSTEMS HEARING SUBMISSION", "expert_deposition"),
        ("PARTY FINAL SUBMISSIONS (ALL)", "expert_deposition"),
    ])
    def test_expert_deposition(self, title, expected):
        assert classify_document(_make_doc(title)) == expected

    @pytest.mark.parametrize("title,expected", [
        ("1-A ORDER OF HEARING", "preliminary_report"),
        ("1-G WITNESS LIST", "preliminary_report"),
        ("BOARD MEETING PRESENTATIONS", "preliminary_report"),
    ])
    def test_preliminary_report(self, title, expected):
        assert classify_document(_make_doc(title)) == expected

    def test_fallback_uses_group(self):
        doc = _make_doc("SOME UNKNOWN DOCUMENT", group="Operational Factors")
        assert classify_document(doc) == "investigation_report"
