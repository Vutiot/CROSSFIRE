"""Generate the final NTSB analysis report."""

import json
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from .models import (
    CrossDocketPatterns,
    DocumentTypeProfile,
    DocumentTypeTaxonomy,
    DocketSummary,
    EntityAnalysis,
    EntityProfile,
    ExtractedDocument,
    NTSBAnalysisReport,
)


def build_taxonomy(
    all_documents: list[ExtractedDocument],
) -> DocumentTypeTaxonomy:
    """Build document type taxonomy from classified documents."""
    counts: dict[str, int] = {}
    for doc in all_documents:
        if doc.document_type:
            counts[doc.document_type] = counts.get(doc.document_type, 0) + 1

    # Check which of the 8 canonical types are present vs absent
    canonical_types = [
        "investigation_report", "technical_analysis", "witness_testimony",
        "regulatory_filing", "press_coverage", "expert_deposition",
        "internal_memo", "preliminary_report",
    ]
    present = [t for t in canonical_types if counts.get(t, 0) > 0]
    absent = [t for t in canonical_types if counts.get(t, 0) == 0]

    notes = []
    if absent:
        notes.append(f"Types not found in scraped data: {', '.join(absent)}")
    if "press_coverage" in absent:
        notes.append("press_coverage is expected absent — NTSB dockets don't contain press articles (synthetic only)")

    return DocumentTypeTaxonomy(
        types=present,
        counts=counts,
        total_documents=len(all_documents),
        discovery_notes=notes,
    )


def build_entity_analysis(profiles: list[EntityProfile]) -> EntityAnalysis:
    """Build entity analysis section from entity profiles."""
    by_type: dict[str, list[str]] = {}
    for p in profiles:
        by_type.setdefault(p.entity_type, []).append(p.canonical_name)

    return EntityAnalysis(
        entity_types=sorted(by_type.keys()),
        total_unique_entities=len(profiles),
        entities_by_type={t: names[:20] for t, names in by_type.items()},
        top_entities=profiles[:20],
    )


def build_synthesis_recommendations(
    taxonomy: DocumentTypeTaxonomy,
    characteristics: dict[str, DocumentTypeProfile],
    cross_docket: CrossDocketPatterns,
) -> list[str]:
    """Generate actionable recommendations for Story 2.2 template design."""
    recs = []

    # Document type template recommendations
    for doc_type, profile in characteristics.items():
        recs.append(
            f"Template for '{doc_type}': target {profile.word_count_min}-{profile.word_count_max} words "
            f"(mean {profile.word_count_mean}). {'; '.join(profile.structural_notes[:2])}"
        )

    # Missing types
    if "press_coverage" in (taxonomy.discovery_notes or [""]):
        recs.append(
            "Template for 'press_coverage': no real NTSB data available — design based on "
            "typical aviation journalism structure (inverted pyramid, quotes, background)"
        )

    # Entity patterns
    if cross_docket.naming_variations:
        sample = list(cross_docket.naming_variations.items())[:3]
        variation_examples = "; ".join(f"'{k}' appears as: {', '.join(v)}" for k, v in sample)
        recs.append(
            f"Entity naming: real data shows significant naming variation. "
            f"Examples: {variation_examples}. "
            f"Templates should use varied entity references to match reality."
        )

    if cross_docket.connectivity_score > 0:
        recs.append(
            f"Entity connectivity: observed score of {cross_docket.connectivity_score:.2f} "
            f"(avg dockets per shared entity). Use this as baseline for connectivity level 2."
        )

    return recs


def generate_report(
    docket_summaries: list[DocketSummary],
    all_documents: list[ExtractedDocument],
    entity_profiles: list[EntityProfile],
    cross_docket: CrossDocketPatterns,
    characteristics: dict[str, DocumentTypeProfile],
    output_dir: Path,
) -> tuple[NTSBAnalysisReport, str | None]:
    """Generate and save the final analysis report. Returns (report, error)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    taxonomy = build_taxonomy(all_documents)
    entity_analysis = build_entity_analysis(entity_profiles)
    recommendations = build_synthesis_recommendations(taxonomy, characteristics, cross_docket)

    # Data quality notes
    quality_notes = []
    total_docs = sum(d.extracted_documents for d in docket_summaries)
    clean_docs = sum(d.clean_documents for d in docket_summaries)
    if total_docs > 0:
        quality_notes.append(f"Overall extraction: {clean_docs}/{total_docs} documents passed quality ({clean_docs/total_docs:.0%})")
    for ds in docket_summaries:
        if ds.clean_rate < 0.8:
            quality_notes.append(f"Docket {ds.ntsb_id}: low clean rate ({ds.clean_rate:.0%})")

    report = NTSBAnalysisReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        dockets_analyzed=docket_summaries,
        document_type_taxonomy=taxonomy,
        entity_analysis=entity_analysis,
        cross_docket_patterns=cross_docket,
        document_characteristics=characteristics,
        data_quality_notes=quality_notes,
        synthesis_recommendations=recommendations,
    )

    report_path = output_dir / "analysis_report.json"
    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    logger.info(f"Analysis report saved to {report_path}")

    # Log summary
    logger.info("=== NTSB Analysis Summary ===")
    logger.info(f"  Dockets analyzed: {len(docket_summaries)}")
    logger.info(f"  Total documents: {taxonomy.total_documents}")
    logger.info(f"  Document types found: {len(taxonomy.types)} — {', '.join(taxonomy.types)}")
    logger.info(f"  Unique entities: {entity_analysis.total_unique_entities}")
    logger.info(f"  Shared entities (2+ dockets): {cross_docket.shared_entity_count}")
    logger.info(f"  Connectivity score: {cross_docket.connectivity_score:.2f}")
    logger.info(f"  Recommendations: {len(recommendations)}")

    return report, None
