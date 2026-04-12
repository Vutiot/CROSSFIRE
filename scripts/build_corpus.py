#!/usr/bin/env python3
"""Build organized corpus directory from extracted source documents.

Supports multiple sources (ntsb, grenfell, copa) with pluggable classifiers.
Usage:
    python scripts/build_corpus.py --source ntsb
    python scripts/build_corpus.py --source grenfell
"""

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from loguru import logger

# ---------------------------------------------------------------------------
# Source registry: maps source_id -> raw data directory (relative to project root)
# ---------------------------------------------------------------------------
SOURCE_DIRECTORIES: dict[str, str] = {
    "ntsb": "data/ntsb_extracted",
    "grenfell": "data/grenfell_extracted",
    "copa": "data/copa_extracted",
}

# ---------------------------------------------------------------------------
# NTSB classification rules: (pattern, document_type)
# Checked in order — first match wins.
# ---------------------------------------------------------------------------
_NTSB_CLASSIFICATION_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"METEOROLOG|WEATHER STUDY|WEATHER FACTUAL", re.I), "meteorology_report"),
    (re.compile(r"AIR TRAFFIC CONTROL|\bATC\b|CTAF TRANSCRIPT", re.I), "atc_transcript"),
    (re.compile(r"OPERATIONAL? FACTORS|OPERATIONS GROUP", re.I), "ops_group_report"),
    (re.compile(r"STRUCTURES GROUP|STRUCTURES FACTUAL", re.I), "structures_analysis"),
    (re.compile(r"POWERPLANTS?\b", re.I), "powerplants_analysis"),
    (re.compile(r"MAINTENANCE RECORD", re.I), "maintenance_record"),
    (re.compile(r"INTERVIEW|STATEMENT|DEPOSITION|TESTIMONY|WITNESS|RECORD OF CONVERSATION", re.I), "witness_testimony"),
    (re.compile(r"PRELIMINARY|ORDER OF HEARING|EXHIBIT LIST|BOARD MEETING|STATEMENT OF PURPOSE|WITNESS LIST|DESIGNATION", re.I), "preliminary_report"),
]


def classify_ntsb(title: str) -> str:
    """Classify an NTSB document title into source-specific document types.

    Uses regex-based title matching; first match wins.
    Falls back to 'investigation_report' as catch-all.
    """
    for pattern, doc_type in _NTSB_CLASSIFICATION_RULES:
        if pattern.search(title):
            return doc_type
    return "investigation_report"


def classify_grenfell(title: str) -> str:
    """Classify a Grenfell Tower Inquiry document title.

    Returns 'hearing_transcript' for transcripts, 'document' as fallback.
    """
    if re.search(r"transcript|hearing", title, re.IGNORECASE):
        return "hearing_transcript"
    return "document"


def classify_copa(title: str) -> str:
    """Classify a Chicago COPA document title.

    Uses filename-derived title patterns to identify document types.
    """
    lower = title.lower()
    if "fsr" in lower or "final_summary" in lower or "final-summary" in lower or "final summary" in lower:
        return "final_summary_report"
    if "trr" in lower or "tactical" in lower:
        return "tactical_response_report"
    if "ocir" in lower or "case-incident" in lower or "case incident" in lower or "original-case" in lower or "original case" in lower:
        return "case_incident_report"
    if "arrest" in lower:
        return "arrest_report"
    if "concur" in lower:
        return "superintendent_concurrence"
    return "document"


def classify_passthrough(title: str) -> str:
    """Fallback classifier for sources without specific rules.

    Returns 'document' for all titles — preserves files as-is (AC4).
    """
    return "document"


# Registry of per-source classifiers
_SOURCE_CLASSIFIERS: dict[str, callable] = {
    "ntsb": classify_ntsb,
    "grenfell": classify_grenfell,
    "copa": classify_copa,
}


def classify_document_type(title: str, source_id: str = "ntsb") -> str:
    """Classify a document title into a source-specific document type.

    Delegates to the source-specific classifier if one exists,
    otherwise falls back to passthrough.
    """
    classifier = _SOURCE_CLASSIFIERS.get(source_id, classify_passthrough)
    return classifier(title)


def _title_from_filename(filename: str) -> str:
    """Derive a document title from a filename when metadata is unavailable.

    Strips numeric prefix and .txt extension, replaces underscores with spaces.
    """
    stem = Path(filename).stem
    # Remove leading numeric prefix (e.g. "001_")
    stem = re.sub(r"^\d+_", "", stem)
    return stem.replace("_", " ")


def build_corpus(source: Path, target: Path, source_id: str = "ntsb") -> dict:
    """Build organized corpus from extracted source data.

    Copies .txt files from source case directories into
    target/{source_id}/{case_id}/, classifies documents, and
    generates a manifest.

    Returns the manifest dict.
    """
    cases = []
    total_documents = 0
    all_types: set[str] = set()

    # Target is corpus/{source_id}/
    source_target = target / source_id

    case_dirs = sorted(d for d in source.iterdir() if d.is_dir())

    for case_dir in case_dirs:
        case_id = case_dir.name
        txt_files = sorted(f for f in case_dir.iterdir() if f.suffix == ".txt")

        if not txt_files:
            logger.warning(f"Skipping {case_id}: no .txt files")
            continue

        # Create target directory: corpus/{source_id}/{case_id}/
        target_case = source_target / case_id
        target_case.mkdir(parents=True, exist_ok=True)

        # Read extraction metadata for titles and word counts
        meta_path = case_dir / "_extraction_meta.json"
        meta_lookup: dict[int, dict] = {}
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
            for doc in meta.get("documents", []):
                meta_lookup[doc["item_number"]] = doc

        # Process each document
        documents = []
        type_counts: dict[str, int] = {}

        for txt_file in txt_files:
            # Copy file to target
            shutil.copy2(txt_file, target_case / txt_file.name)

            # Extract item number from filename prefix
            match = re.match(r"^(\d+)_", txt_file.name)
            item_number = int(match.group(1)) if match else None

            # Get title and word count from metadata or derive from filename
            if item_number and item_number in meta_lookup:
                doc_meta = meta_lookup[item_number]
                title = doc_meta["title"]
                word_count = doc_meta.get("word_count", 0)
            else:
                title = _title_from_filename(txt_file.name)
                word_count = len(txt_file.read_text(errors="replace").split())

            doc_type = classify_document_type(title, source_id)
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
            all_types.add(doc_type)

            documents.append({
                "filename": txt_file.name,
                "title": title,
                "document_type": doc_type,
                "word_count": word_count,
            })

        cases.append({
            "case_id": case_id,
            "source_id": source_id,
            "document_count": len(documents),
            "documents": documents,
            "type_distribution": dict(sorted(type_counts.items())),
        })

        total_documents += len(documents)
        logger.info(f"Processing case {case_id}: {len(documents)} documents")

    # Load existing manifest if present (supports incremental multi-source builds)
    manifest_path = target / "manifest.json"
    existing_sources: dict[str, list] = {}
    existing_types: set[str] = set()
    existing_doc_count = 0

    if manifest_path.exists():
        with open(manifest_path) as f:
            existing_manifest = json.load(f)
        for case in existing_manifest.get("cases", []):
            sid = case.get("source_id", "unknown")
            if sid != source_id:
                existing_sources.setdefault(sid, []).append(case)
                existing_doc_count += case.get("document_count", 0)
                for dtype in case.get("type_distribution", {}):
                    existing_types.add(dtype)

    # Merge: keep cases from other sources, replace current source's cases
    all_cases = []
    for sid in sorted(existing_sources):
        all_cases.extend(existing_sources[sid])
    all_cases.extend(cases)

    combined_types = all_types | existing_types
    combined_doc_count = total_documents + existing_doc_count
    combined_case_count = len(all_cases)

    # Count sources
    sources_found = {c.get("source_id", "unknown") for c in all_cases}

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": sorted(sources_found),
        "cases": all_cases,
        "summary": {
            "total_sources": len(sources_found),
            "total_cases": combined_case_count,
            "total_documents": combined_doc_count,
            "document_types_found": sorted(combined_types),
        },
    }

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def main() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}")

    parser = argparse.ArgumentParser(
        description="Build organized corpus from extracted source documents."
    )
    parser.add_argument(
        "--source",
        required=True,
        choices=list(SOURCE_DIRECTORIES.keys()),
        help="Source identifier (e.g. ntsb, grenfell, copa)",
    )
    args = parser.parse_args()

    source_id = args.source
    source_dir = Path(SOURCE_DIRECTORIES[source_id])
    target_dir = Path("corpus")

    if not source_dir.exists():
        logger.error(f"Source directory not found: {source_dir}")
        sys.exit(1)

    manifest = build_corpus(source_dir, target_dir, source_id)
    summary = manifest["summary"]
    logger.info(
        f"Built corpus for {source_id}: {summary['total_cases']} cases, "
        f"{summary['total_documents']} documents, "
        f"{len(summary['document_types_found'])} document types"
    )


if __name__ == "__main__":
    main()
