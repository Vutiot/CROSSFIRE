"""Gold annotation assembler — produces versioned gold annotation files.

Serializes incoherence and distractor labels to JSON, cross-validates against
the corpus, and updates metadata with version and summary counts.

FRs covered: FR14, FR15, FR16
"""

import json
from pathlib import Path

from loguru import logger

from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.incoherences import DistractorLabel, IncoherenceLabel


def assemble_gold_annotations(
    output_dir: Path,
    incoherence_labels: list[IncoherenceLabel],
    distractor_labels: list[DistractorLabel],
    corpus_dir: Path,
    version: str = "1.0",
) -> tuple[dict | None, str | None]:
    """Assemble gold annotation files from label lists.

    Args:
        output_dir: Directory to write gold annotation JSON files.
        incoherence_labels: List of IncoherenceLabel from the injector.
        distractor_labels: List of DistractorLabel from the distractor generator.
        corpus_dir: Directory containing corpus JSONL files for cross-validation.
        version: Benchmark version identifier (FR16).

    Returns:
        (summary_dict, None) on success, (None, error_message) on failure.
    """
    if not output_dir.exists():
        return None, f"Output directory does not exist: {output_dir}"

    # Step 1: Write gold incoherence labels
    inc_path = output_dir / "gold_incoherence_labels.json"
    inc_data = [label.model_dump() for label in incoherence_labels]
    inc_path.write_text(json.dumps(inc_data, indent=2), encoding="utf-8")
    logger.info(f"Gold incoherence labels written: {len(inc_data)} labels → {inc_path}")

    # Step 2: Write gold distractor labels
    dist_path = output_dir / "gold_distractor_labels.json"
    dist_data = [label.model_dump() for label in distractor_labels]
    dist_path.write_text(json.dumps(dist_data, indent=2), encoding="utf-8")
    logger.info(f"Gold distractor labels written: {len(dist_data)} labels → {dist_path}")

    # Step 3: Cross-validate incoherence labels against corpus
    cv_passed, cv_failed = _cross_validate(incoherence_labels, corpus_dir)

    # Step 4: Compute summary counts
    scope_counts: dict[str, int] = {}
    for label in incoherence_labels:
        scope_counts[label.scope] = scope_counts.get(label.scope, 0) + 1

    summary = {
        "total_incoherences": len(incoherence_labels),
        "incoherences_by_scope": scope_counts,
        "total_distractors": len(distractor_labels),
        "cross_validation_passed": cv_passed,
        "cross_validation_failed": cv_failed,
    }

    # Step 5: Log summary
    scope_parts = ", ".join(f"{k}: {v}" for k, v in sorted(scope_counts.items()))
    logger.info(
        f"Gold annotations: {len(incoherence_labels)} incoherences "
        f"({scope_parts}), {len(distractor_labels)} distractors"
    )
    logger.info(
        f"Cross-validation: {cv_passed}/{len(incoherence_labels)} "
        f"incoherences verified in corpus"
    )

    # Step 6: Update metadata.json
    _update_metadata(output_dir, version, summary)

    return summary, None


def _cross_validate(
    incoherence_labels: list[IncoherenceLabel],
    corpus_dir: Path,
) -> tuple[int, int]:
    """Cross-validate incoherence labels against corpus documents.

    Returns (passed_count, failed_count).
    """
    if not incoherence_labels:
        return 0, 0

    # Load all document content indexed by ID
    doc_contents: dict[str, str] = {}
    for jsonl_path in sorted(corpus_dir.glob("subcorpus_*.jsonl")):
        text = jsonl_path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        for line in text.split("\n"):
            if line:
                doc = Document.model_validate_json(line)
                doc_contents[doc.id] = doc.content

    passed = 0
    failed = 0

    for label in incoherence_labels:
        found = False
        for doc_id in label.document_references:
            content = doc_contents.get(doc_id, "")
            if label.modified_fact in content:
                found = True
                break

        if found:
            passed += 1
        else:
            logger.warning(
                f"Cross-validation failed for {label.id}: "
                f"modified_fact not found in referenced documents "
                f"{label.document_references}"
            )
            failed += 1

    return passed, failed


def _update_metadata(
    output_dir: Path,
    version: str,
    summary: dict,
) -> None:
    """Update metadata.json with version and annotation summary."""
    meta_path = output_dir / "metadata.json"

    # Load existing metadata if present
    metadata: dict = {}
    if meta_path.exists():
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))

    # Add annotation fields
    metadata["version"] = version
    metadata["annotation_summary"] = summary

    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info(f"Metadata updated with version={version} → {meta_path}")
