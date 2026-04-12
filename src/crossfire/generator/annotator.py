"""Gold annotation assembler — produces versioned gold annotation files.

Serializes contradiction and distractor labels to JSONL, cross-validates against
the corpus, and returns a summary dict.

Operates on per-case directory layout:
    case_dir/anonymized_docs/*.jsonl
    case_dir/contradictions/*.jsonl   (output)
    case_dir/distractors/*.jsonl      (output)
"""

import json
from pathlib import Path

from loguru import logger

from crossfire.shared.schemas.contradictions import ContradictionLabel, DistractorLabel
from crossfire.shared.schemas.corpus import Document


def assemble_gold_annotations(
    case_dir: Path,
    contradictions: list[ContradictionLabel],
    distractors: list[DistractorLabel],
) -> tuple[dict | None, str | None]:
    """Assemble gold annotations from injected contradictions and distractors.

    Args:
        case_dir: Case directory (must exist). Annotations are written to
            ``case_dir/contradictions/`` and ``case_dir/distractors/``.
        contradictions: ContradictionLabel list from the injector.
        distractors: DistractorLabel list from the distractor generator.

    Returns:
        (summary_dict, None) on success, (None, error_message) on failure.
    """
    if not case_dir.exists():
        return None, f"Case directory does not exist: {case_dir}"

    # Step 1: Write contradiction labels as JSONL
    contra_dir = case_dir / "contradictions"
    contra_dir.mkdir(parents=True, exist_ok=True)
    contra_path = contra_dir / "gold_labels.jsonl"
    with open(contra_path, "w", encoding="utf-8") as f:
        for label in contradictions:
            f.write(label.model_dump_json() + "\n")
    logger.info(f"Gold contradiction labels written: {len(contradictions)} -> {contra_path}")

    # Step 2: Write distractor labels as JSONL
    dist_dir = case_dir / "distractors"
    dist_dir.mkdir(parents=True, exist_ok=True)
    dist_path = dist_dir / "gold_labels.jsonl"
    with open(dist_path, "w", encoding="utf-8") as f:
        for label in distractors:
            f.write(label.model_dump_json() + "\n")
    logger.info(f"Gold distractor labels written: {len(distractors)} -> {dist_path}")

    # Step 3: Cross-validate contradiction labels against corpus
    cv_passed, cv_failed = _cross_validate(contradictions, case_dir)

    # Step 4: Compute summary
    scope_counts: dict[str, int] = {}
    for label in contradictions:
        scope_counts[label.scope] = scope_counts.get(label.scope, 0) + 1

    summary = {
        "total_contradictions": len(contradictions),
        "contradictions_by_scope": scope_counts,
        "total_distractors": len(distractors),
        "cross_validation_passed": cv_passed,
        "cross_validation_failed": cv_failed,
    }

    # Step 5: Log summary
    scope_parts = ", ".join(f"{k}: {v}" for k, v in sorted(scope_counts.items()))
    logger.info(
        f"Gold annotations: {len(contradictions)} contradictions "
        f"({scope_parts}), {len(distractors)} distractors"
    )
    logger.info(
        f"Cross-validation: {cv_passed}/{len(contradictions)} "
        f"contradictions verified in corpus"
    )

    return summary, None


def _cross_validate(
    contradictions: list[ContradictionLabel],
    case_dir: Path,
) -> tuple[int, int]:
    """Cross-validate contradiction labels against corpus documents.

    Checks that ``modified_text`` appears in the referenced document content
    at the expected character offsets.

    Returns (passed_count, failed_count).
    """
    if not contradictions:
        return 0, 0

    # Load all document content indexed by document_id
    doc_contents: dict[str, str] = {}
    docs_dir = case_dir / "anonymized_docs"
    if docs_dir.exists():
        for jsonl_path in sorted(docs_dir.glob("*.jsonl")):
            text = jsonl_path.read_text(encoding="utf-8").strip()
            if not text:
                continue
            for line in text.split("\n"):
                if line:
                    doc = Document.model_validate_json(line)
                    doc_contents[doc.document_id] = doc.content

    passed = 0
    failed = 0

    for label in contradictions:
        found = False
        for doc_id in label.document_references:
            content = doc_contents.get(doc_id, "")
            # Check if modified_text appears at expected char offsets
            if label.modified_text in content:
                found = True
                break

        if found:
            passed += 1
        else:
            logger.warning(
                f"Cross-validation failed: modified_text not found in "
                f"referenced documents {label.document_references}"
            )
            failed += 1

    return passed, failed
