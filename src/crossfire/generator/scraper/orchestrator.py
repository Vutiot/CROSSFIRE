"""Orchestrator for the NTSB scraping pipeline with iterative quality refinement."""

from loguru import logger

from .analyzer import analyze_document_structures
from .classifier import classify_docket_documents
from .config import ScraperConfig
from .cross_docket import analyze_cross_docket_patterns
from .docket_parser import fetch_docket_manifest
from .downloader import download_docket_documents
from .entity_extractor import (
    build_entity_profiles,
    extract_entities_from_documents,
)
from .extractor import extract_docket_documents
from .models import (
    CrossDocketPatterns,
    DocketManifest,
    DocketSummary,
    ExtractedDocument,
    NTSBAnalysisReport,
)
from .quality import assess_quality_gates
from .report import generate_report


def run_pipeline(config: ScraperConfig | None = None) -> tuple[NTSBAnalysisReport | None, str | None]:
    """Run the full NTSB scraping and analysis pipeline.

    Iterates until all quality gates pass or max_iterations reached.
    Returns (report, error).
    """
    if config is None:
        config = ScraperConfig()

    logger.info(f"Starting NTSB scraping pipeline — {len(config.target_dockets)} target dockets, max {config.max_iterations} iterations")

    all_manifests: dict[str, DocketManifest] = {}
    all_documents: dict[str, list[ExtractedDocument]] = {}

    for iteration in range(1, config.max_iterations + 1):
        logger.info(f"=== Iteration {iteration}/{config.max_iterations} ===")

        # Phase 1: Discover & download
        _discover_and_download(config, all_manifests, all_documents)

        # Phase 2: Classify all documents
        flat_docs = _flatten_documents(all_documents)
        for ntsb_id, docs in all_documents.items():
            classify_docket_documents(docs)

        # Phase 3: Entity extraction & cross-docket analysis
        all_mentions = extract_entities_from_documents(flat_docs)
        entity_profiles = build_entity_profiles(all_mentions)
        cross_docket = analyze_cross_docket_patterns(entity_profiles)

        # Phase 4: Build summaries & check quality gates
        docket_summaries = _build_docket_summaries(all_documents)
        document_types_found = list({d.document_type for d in flat_docs if d.document_type})

        logger.info(f"--- Quality Gate Check (iteration {iteration}) ---")
        gate_results = assess_quality_gates(docket_summaries, document_types_found, cross_docket, config)

        if gate_results.passed:
            logger.info(f"All quality gates passed on iteration {iteration}")
            break

        logger.warning(f"Failed gates: {', '.join(gate_results.failed_gates)}")

        if iteration < config.max_iterations:
            logger.info("Adjusting strategy for next iteration...")
            # Currently: the pipeline re-processes with any newly available data.
            # Future: could add fallback dockets, adjust extraction settings, etc.
        else:
            logger.warning(f"Max iterations ({config.max_iterations}) reached — proceeding with current data")

    # Phase 5: Structure analysis
    flat_docs = _flatten_documents(all_documents)
    characteristics = analyze_document_structures(flat_docs)

    # Phase 6: Generate report
    docket_summaries = _build_docket_summaries(all_documents)
    all_mentions = extract_entities_from_documents(flat_docs)
    entity_profiles = build_entity_profiles(all_mentions)
    cross_docket = analyze_cross_docket_patterns(entity_profiles)

    report, error = generate_report(
        docket_summaries=docket_summaries,
        all_documents=flat_docs,
        entity_profiles=entity_profiles,
        cross_docket=cross_docket,
        characteristics=characteristics,
        output_dir=config.analysis_dir,
    )

    return report, error


def _discover_and_download(
    config: ScraperConfig,
    all_manifests: dict[str, DocketManifest],
    all_documents: dict[str, list[ExtractedDocument]],
) -> None:
    """Fetch manifests, download docs, and extract text for all target dockets."""
    for target in config.target_dockets:
        ntsb_id = target.ntsb_id
        if ntsb_id in all_documents and all_documents[ntsb_id]:
            logger.debug(f"Docket {ntsb_id} already processed, skipping")
            continue

        # Fetch manifest
        if ntsb_id not in all_manifests:
            manifest, error = fetch_docket_manifest(
                target,
                delay=config.request_delay,
                timeout=config.timeout,
                max_retries=config.max_retries,
            )
            if error:
                logger.error(f"Skipping docket {ntsb_id}: {error}")
                continue
            all_manifests[ntsb_id] = manifest

        manifest = all_manifests[ntsb_id]

        # Download
        downloaded, error = download_docket_documents(manifest, config)
        if error:
            logger.error(f"Download failed for {ntsb_id}: {error}")
            continue

        # Extract
        extracted = extract_docket_documents(manifest, config)
        all_documents[ntsb_id] = extracted


def _flatten_documents(
    all_documents: dict[str, list[ExtractedDocument]],
) -> list[ExtractedDocument]:
    """Flatten per-docket document lists into a single list."""
    flat = []
    for docs in all_documents.values():
        flat.extend(docs)
    return flat


def _build_docket_summaries(
    all_documents: dict[str, list[ExtractedDocument]],
) -> list[DocketSummary]:
    """Build summary stats for each docket."""
    summaries = []
    for ntsb_id, docs in all_documents.items():
        total = len(docs)
        clean = sum(1 for d in docs if d.quality and d.quality.passed)
        type_dist: dict[str, int] = {}
        for d in docs:
            if d.document_type:
                type_dist[d.document_type] = type_dist.get(d.document_type, 0) + 1

        summaries.append(
            DocketSummary(
                ntsb_id=ntsb_id,
                total_documents=total,
                extracted_documents=total,
                clean_documents=clean,
                clean_rate=round(clean / total, 4) if total > 0 else 0.0,
                type_distribution=type_dist,
            )
        )
    return summaries
