"""Shared fixtures for pipeline tests."""

from pathlib import Path

import pytest

from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.reports import DetectedContradiction
from crossfire.shared.seed_manager import SeedManager


@pytest.fixture
def seed_manager():
    return SeedManager(master_seed=42)


@pytest.fixture
def tmp_corpus_dir(tmp_path):
    """Create a minimal test corpus with anonymized_docs/ containing 2 JSONL files."""
    corpus_dir = tmp_path / "case_001"
    corpus_dir.mkdir()
    anon_dir = corpus_dir / "anonymized_docs"
    anon_dir.mkdir()

    docs_by_file = {
        "batch_0.jsonl": [
            Document(
                document_id="case_001_doc_000",
                source="ntsb",
                document_type="investigation_report",
                source_case_id="case_001",
                scope_classification="primary",
                content="The aircraft experienced engine failure at 14:32 UTC.",
            ),
            Document(
                document_id="case_001_doc_001",
                source="ntsb",
                document_type="witness_testimony",
                source_case_id="case_001",
                scope_classification="primary",
                content="I saw smoke coming from the left engine around 2:30 PM.",
            ),
        ],
        "batch_1.jsonl": [
            Document(
                document_id="case_001_doc_002",
                source="ntsb",
                document_type="meteorology_report",
                source_case_id="case_001",
                scope_classification="secondary",
                content="Metallurgical analysis revealed fatigue cracking in turbine blade.",
            ),
            Document(
                document_id="case_001_doc_003",
                source="ntsb",
                document_type="maintenance_record",
                source_case_id="case_001",
                scope_classification="secondary",
                content="Maintenance log shows engine overhaul completed 2025-01-15.",
            ),
        ],
    }

    for filename, docs in docs_by_file.items():
        jsonl_path = anon_dir / filename
        jsonl_path.write_text(
            "\n".join(d.model_dump_json() for d in docs) + "\n",
            encoding="utf-8",
        )

    return corpus_dir


@pytest.fixture
def sample_detections():
    """Pre-built DetectedContradiction list for mock strategies."""
    return [
        DetectedContradiction(
            scope="inter_doc",
            document_references=["case_001_doc_000", "case_001_doc_001"],
            text_span_start=0,
            text_span_end=50,
            evidence_text="Engine failure at 14:32 UTC vs 2:30 PM timing",
            confidence=0.85,
            description="Temporal contradiction: 14:32 UTC vs 2:30 PM timing discrepancy",
        ),
        DetectedContradiction(
            scope="inter_doc",
            document_references=["case_001_doc_002", "case_001_doc_003"],
            text_span_start=0,
            text_span_end=40,
            evidence_text="Fatigue cracking vs recent overhaul",
            confidence=0.72,
            description="Entity reference mismatch in turbine component identification",
        ),
    ]
