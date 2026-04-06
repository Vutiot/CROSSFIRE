"""Classify NTSB documents into the project's 8-type taxonomy."""

import re

from loguru import logger

from .models import ExtractedDocument, TypeDistribution

# Classification rules: (pattern, document_type)
# Checked in order — first match wins.
_CLASSIFICATION_RULES: list[tuple[re.Pattern, str]] = [
    # Witness testimony — interviews, transcripts, statements, depositions
    (re.compile(r"INTERVIEW|TRANSCRIPT|STATEMENT|DEPOSITION|TESTIMONY", re.I), "witness_testimony"),
    # Technical analysis — specialist reports, lab reports, recorder data
    (re.compile(r"FLIGHT DATA RECORDER|FDR|COCKPIT VOICE RECORDER|CVR|MATERIALS LAB|METALLURGICAL|RADAR DATA|WEATHER STUDY", re.I), "technical_analysis"),
    # Regulatory filing — FAA, AD compliance, CFR, safety recommendation, airworthiness
    (re.compile(r"\bFAA\b|AIRWORTHINESS DIRECTIVE|SAFETY RECOMMENDATION|COMPLIANCE|REGULATORY|14 CFR|OVERSIGHT|SMS RULE", re.I), "regulatory_filing"),
    # Internal memo — quality alerts, process instructions, internal communications, QMS docs
    (re.compile(r"QUALITY ALERT|PROCESS INSTRUCTION|INTERNAL|BULLETIN|NCR|NCO|QUALITY ESCAPE|SPEAK UP|SAFETY ACTION|\bQMS\b", re.I), "internal_memo"),
    # Preliminary report — opening statements, sequence of events, board meeting, preliminary
    (re.compile(r"PRELIMINARY|OPENING STATEMENT|BOARD MEETING|SEQUENCE OF EVENTS|EXHIBIT LIST", re.I), "preliminary_report"),
    # Expert deposition — party submissions, hearing presentations, expert analysis
    (re.compile(r"SUBMISSION|PARTY|PRESENTATION|FOLLOW-UP ANSWER|FINAL SUBMISSION", re.I), "expert_deposition"),
    # Investigation report — group factual reports (the catch-all for factual investigation docs)
    (re.compile(r"FACTUAL REPORT|GROUP CHAIR|GROUP CHAIRMAN|ERRATA|SUPPLEMENT|REPORT", re.I), "investigation_report"),
    # Hearing documents that didn't match above — classify as preliminary_report
    (re.compile(r"ORDER OF HEARING|DESIGNATION|NOTICE|WITNESS LIST|BIOGRAPHIES", re.I), "preliminary_report"),
]


def classify_document(doc: ExtractedDocument) -> str:
    """Classify a single document into the project's DocumentType taxonomy.

    Uses title-based rules. Returns the document type string.
    """
    title = doc.title

    for pattern, doc_type in _CLASSIFICATION_RULES:
        if pattern.search(title):
            return doc_type

    # Fallback: use group hint
    group = doc.group.lower()
    if "operational" in group or "survival" in group or "structures" in group or "systems" in group:
        return "investigation_report"
    if "recorder" in group:
        return "technical_analysis"
    if "materials" in group:
        return "technical_analysis"
    if "manufacturing" in group or "human performance" in group:
        return "investigation_report"
    if "hearing" in group:
        return "preliminary_report"
    if "party" in group:
        return "expert_deposition"
    if "regulatory" in group:
        return "regulatory_filing"

    return "investigation_report"  # safe default


def classify_docket_documents(documents: list[ExtractedDocument]) -> TypeDistribution:
    """Classify all documents in a docket and return distribution."""
    counts: dict[str, int] = {}
    for doc in documents:
        doc_type = classify_document(doc)
        doc.document_type = doc_type
        counts[doc_type] = counts.get(doc_type, 0) + 1

    dist = TypeDistribution(counts=counts, total=len(documents))

    if documents:
        ntsb_id = documents[0].ntsb_id
        parts = [f"{count} {dtype}" for dtype, count in sorted(counts.items())]
        logger.info(f"Docket {ntsb_id} — classified: {', '.join(parts)}")

    return dist
