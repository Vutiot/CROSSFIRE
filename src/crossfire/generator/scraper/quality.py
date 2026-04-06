"""Quality gate assessment for the iterative scraping pipeline."""

from loguru import logger

from .config import ScraperConfig
from .models import (
    CrossDocketPatterns,
    DocketSummary,
    ExtractedDocument,
    GateResult,
    QualityGateResults,
)


def assess_quality_gates(
    docket_summaries: list[DocketSummary],
    document_types_found: list[str],
    cross_docket: CrossDocketPatterns,
    config: ScraperConfig,
) -> QualityGateResults:
    """Check all quality gates and return results."""
    gates = config.gates
    results = []

    # G1: Dockets with sufficient documents
    dockets_with_docs = sum(1 for d in docket_summaries if d.extracted_documents >= gates.min_docs_per_docket)
    g1 = GateResult(
        name="G1: Dockets with sufficient documents",
        passed=dockets_with_docs >= gates.min_dockets_with_docs,
        metric="dockets_with_docs",
        threshold=f">={gates.min_dockets_with_docs}",
        actual=str(dockets_with_docs),
        action="Try additional docket candidates" if dockets_with_docs < gates.min_dockets_with_docs else "",
    )
    results.append(g1)

    # G2: Clean text extraction rate (per docket)
    low_quality_dockets = [d for d in docket_summaries if d.clean_rate < config.quality.min_clean_extraction_rate]
    g2 = GateResult(
        name="G2: Clean text extraction rate",
        passed=len(low_quality_dockets) == 0,
        metric="low_quality_dockets",
        threshold=f"all dockets >={config.quality.min_clean_extraction_rate:.0%}",
        actual=f"{len(low_quality_dockets)} dockets below threshold",
        action="Re-extract with alternative settings" if low_quality_dockets else "",
    )
    results.append(g2)

    # G3: Document types represented
    type_count = len(document_types_found)
    g3 = GateResult(
        name="G3: Document types represented",
        passed=type_count >= gates.min_document_types,
        metric="document_types",
        threshold=f">={gates.min_document_types}",
        actual=f"{type_count} ({', '.join(document_types_found)})",
        action="Note: press_coverage is synthetic-only" if type_count < gates.min_document_types else "",
    )
    results.append(g3)

    # G4: Shared entities across dockets
    shared = cross_docket.shared_entity_count
    g4 = GateResult(
        name="G4: Shared entities across dockets",
        passed=shared >= gates.min_shared_entities,
        metric="shared_entities",
        threshold=f">={gates.min_shared_entities}",
        actual=str(shared),
        action="Expand docket selection for more overlap" if shared < gates.min_shared_entities else "",
    )
    results.append(g4)

    failed = [g.name for g in results if not g.passed]
    all_passed = len(failed) == 0

    for g in results:
        status = "PASS" if g.passed else "FAIL"
        logger.info(f"  {status} {g.name}: {g.actual} (threshold: {g.threshold})")

    return QualityGateResults(passed=all_passed, gates=results, failed_gates=failed)
