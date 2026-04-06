"""Shared fixtures for pipeline tests."""

import json
from pathlib import Path

import pytest

from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.reports import DetectedIncoherence
from crossfire.shared.seed_manager import SeedManager


@pytest.fixture
def seed_manager():
    return SeedManager(master_seed=42)


@pytest.fixture
def tmp_corpus_dir(tmp_path):
    """Create a minimal test corpus with 2 subcorpora x 2 docs each."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()

    docs_by_subcorpus = {
        "sc-0": [
            Document(
                id="sc-0_doc_000",
                document_type="investigation_report",
                subcorpus_id="sc-0",
                reliability_signal=0.9,
                content="The aircraft experienced engine failure at 14:32 UTC.",
            ),
            Document(
                id="sc-0_doc_001",
                document_type="witness_testimony",
                subcorpus_id="sc-0",
                reliability_signal=0.7,
                content="I saw smoke coming from the left engine around 2:30 PM.",
            ),
        ],
        "sc-1": [
            Document(
                id="sc-1_doc_000",
                document_type="technical_analysis",
                subcorpus_id="sc-1",
                reliability_signal=0.95,
                content="Metallurgical analysis revealed fatigue cracking in turbine blade.",
            ),
            Document(
                id="sc-1_doc_001",
                document_type="regulatory_filing",
                subcorpus_id="sc-1",
                reliability_signal=0.85,
                content="FAA Airworthiness Directive 2025-NE-042 issued for engine model.",
            ),
        ],
    }

    for sc_id, docs in docs_by_subcorpus.items():
        jsonl_path = corpus_dir / f"subcorpus_{sc_id}.jsonl"
        jsonl_path.write_text(
            "\n".join(d.model_dump_json() for d in docs) + "\n",
            encoding="utf-8",
        )

    return corpus_dir


@pytest.fixture
def sample_detections():
    """Pre-built DetectedIncoherence list for mock strategies."""
    return [
        DetectedIncoherence(
            id="det_001",
            evidence_references=["sc-0_doc_000", "sc-0_doc_001"],
            confidence=0.85,
            description="Temporal contradiction: 14:32 UTC vs 2:30 PM timing discrepancy",
        ),
        DetectedIncoherence(
            id="det_002",
            evidence_references=["sc-1_doc_000", "sc-1_doc_001"],
            confidence=0.72,
            description="Entity reference mismatch in turbine component identification",
        ),
    ]
