"""Analyze document structure characteristics per document type."""

from collections import defaultdict

from loguru import logger

from .models import DocumentTypeProfile, ExtractedDocument


def analyze_document_structures(
    documents: list[ExtractedDocument],
) -> dict[str, DocumentTypeProfile]:
    """Compute per-type structure metrics across all documents."""
    # Group documents by type
    by_type: dict[str, list[ExtractedDocument]] = defaultdict(list)
    for doc in documents:
        if doc.document_type and doc.quality and doc.quality.passed:
            by_type[doc.document_type].append(doc)

    profiles: dict[str, DocumentTypeProfile] = {}

    for doc_type, docs in sorted(by_type.items()):
        word_counts = [d.quality.word_count for d in docs if d.quality]
        line_counts = [d.quality.line_count for d in docs if d.quality]

        profile = DocumentTypeProfile(
            document_type=doc_type,
            count=len(docs),
            word_count_min=min(word_counts) if word_counts else 0,
            word_count_max=max(word_counts) if word_counts else 0,
            word_count_mean=round(sum(word_counts) / len(word_counts), 1) if word_counts else 0.0,
            avg_line_count=round(sum(line_counts) / len(line_counts), 1) if line_counts else 0.0,
            example_titles=[d.title[:100] for d in docs[:5]],
            structural_notes=_infer_structural_notes(doc_type, docs),
        )
        profiles[doc_type] = profile

        logger.info(
            f"  {doc_type}: {len(docs)} docs, "
            f"{profile.word_count_min}-{profile.word_count_max} words "
            f"(mean {profile.word_count_mean})"
        )

    return profiles


def _infer_structural_notes(doc_type: str, docs: list[ExtractedDocument]) -> list[str]:
    """Infer structural characteristics from document content."""
    notes = []

    # Sample text from first few docs
    sample_texts = [d.text for d in docs[:5] if d.text]
    if not sample_texts:
        return ["No text available for structural analysis"]

    # Check for common structural patterns
    has_numbered_sections = any("1." in t[:500] or "1)" in t[:500] for t in sample_texts)
    has_headers = any(
        any(line.isupper() and len(line.split()) <= 8 and len(line) > 3 for line in t.split("\n")[:20])
        for t in sample_texts
    )
    has_tables = any("  " in t and "|" in t for t in sample_texts)

    avg_words = sum(len(t.split()) for t in sample_texts) / len(sample_texts)

    if has_numbered_sections:
        notes.append("Contains numbered sections/subsections")
    if has_headers:
        notes.append("Contains uppercase section headers")
    if has_tables:
        notes.append("Contains tabular data")

    if avg_words > 5000:
        notes.append("Long-form document (>5000 words typical)")
    elif avg_words > 1000:
        notes.append("Medium-length document (1000-5000 words)")
    else:
        notes.append("Short document (<1000 words)")

    _TYPE_NOTES = {
        "investigation_report": "Formal factual report with structured sections and findings",
        "technical_analysis": "Detailed technical data with specialized terminology",
        "witness_testimony": "Narrative/Q&A format, first-person accounts",
        "regulatory_filing": "Formal regulatory language, references to CFR/FAR",
        "expert_deposition": "Argumentative structure, evidence-based reasoning",
        "internal_memo": "Organizational communication, process-oriented",
        "preliminary_report": "Summary format, initial findings and procedural content",
    }
    if doc_type in _TYPE_NOTES:
        notes.append(_TYPE_NOTES[doc_type])

    return notes
