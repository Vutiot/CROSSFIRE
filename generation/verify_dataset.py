#!/usr/bin/env python3
"""Diff-based gold label verification (Story 3.4-NEW).

Mechanically verifies injected contradictions by comparing original (pre-injection)
and modified (post-injection) documents via ``difflib.SequenceMatcher``. Diff-derived
char offsets take precedence over agent self-reported offsets (FR14).

Usage::

    python generation/verify_dataset.py --case <case_dir>
    python generation/verify_dataset.py --all <dataset_root>

Directory expectations (per case)::

    case_dir/
        anonymized_docs_original/*.jsonl   <- pre-injection backup
        anonymized_docs/*.jsonl            <- post-injection (modified)
        contradictions/gold_labels.jsonl   <- agent-reported labels

Outputs (per case)::

    case_dir/validation/diff_verification_log.json
    case_dir/validation/rejected_contradictions.jsonl
    case_dir/validation/unintended_modifications.json
    case_dir/validation/agent_label_discrepancies.json
    case_dir/contradictions/intra_doc_contradictions.jsonl
    case_dir/contradictions/inter_doc_contradictions.jsonl
    case_dir/contradictions/all_contradictions.jsonl
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

# Allow imports from the crossfire package (project root may not be on sys.path)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from crossfire.shared.schemas.contradictions import ContradictionLabel  # noqa: E402
from crossfire.shared.schemas.corpus import Document  # noqa: E402

# Context window size for contamination check (chars before/after modification)
_CONTEXT_WINDOW = 200


# ---------------------------------------------------------------------------
# Document I/O
# ---------------------------------------------------------------------------


def load_docs_by_id(docs_dir: Path) -> dict[str, str]:
    """Load all documents from ``docs_dir/*.jsonl`` and return {doc_id: content}."""
    result: dict[str, str] = {}
    if not docs_dir.exists():
        return result
    for jsonl_path in sorted(docs_dir.glob("*.jsonl")):
        text = jsonl_path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            doc = Document.model_validate_json(line)
            result[doc.document_id] = doc.content
    return result


def load_agent_labels(case_dir: Path) -> list[dict[str, Any]]:
    """Load agent-reported labels from ``contradictions/gold_labels.jsonl``."""
    labels_path = case_dir / "contradictions" / "gold_labels.jsonl"
    if not labels_path.exists():
        return []
    labels: list[dict[str, Any]] = []
    for line in labels_path.read_text(encoding="utf-8").strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        labels.append(json.loads(line))
    return labels


# ---------------------------------------------------------------------------
# Diff engine
# ---------------------------------------------------------------------------


def compute_diff(original: str, modified: str) -> list[tuple[str, int, int, int, int]]:
    """Return non-equal opcodes from SequenceMatcher.

    Each tuple: (tag, i1, i2, j1, j2) where tag is 'replace', 'insert', or
    'delete'.  'equal' blocks are excluded.
    """
    sm = difflib.SequenceMatcher(None, original, modified)
    return [op for op in sm.get_opcodes() if op[0] != "equal"]


def check_context_contamination(
    original: str,
    modified: str,
    orig_start: int,
    orig_end: int,
    mod_start: int,
    mod_end: int,
) -> bool:
    """Return True if surrounding context is clean (identical), False if contaminated.

    Compares +-CONTEXT_WINDOW chars around the modification in both versions.
    """
    # Leading context
    orig_leading = original[max(0, orig_start - _CONTEXT_WINDOW) : orig_start]
    mod_leading = modified[max(0, mod_start - _CONTEXT_WINDOW) : mod_start]
    if orig_leading != mod_leading:
        return False

    # Trailing context
    orig_trailing = original[orig_end : orig_end + _CONTEXT_WINDOW]
    mod_trailing = modified[mod_end : mod_end + _CONTEXT_WINDOW]
    if orig_trailing != mod_trailing:
        return False

    return True


# ---------------------------------------------------------------------------
# Verification logic
# ---------------------------------------------------------------------------


class VerificationResult:
    """Holds the outcome of verifying a single label."""

    __slots__ = (
        "label_index",
        "agent_label",
        "passed",
        "rejection_reason",
        "diff_char_start",
        "diff_char_end",
        "diff_original_text",
        "diff_modified_text",
        "unintended_modifications",
        "agent_discrepancy",
        "verified_label",
    )

    def __init__(self, label_index: int, agent_label: dict[str, Any]) -> None:
        self.label_index = label_index
        self.agent_label = agent_label
        self.passed = False
        self.rejection_reason: str | None = None
        self.diff_char_start: int | None = None
        self.diff_char_end: int | None = None
        self.diff_original_text: str | None = None
        self.diff_modified_text: str | None = None
        self.unintended_modifications: list[dict[str, Any]] = []
        self.agent_discrepancy: dict[str, Any] | None = None
        self.verified_label: ContradictionLabel | None = None

    def to_log_dict(self) -> dict[str, Any]:
        """Serialize for diff_verification_log.json."""
        return {
            "label_index": self.label_index,
            "passed": self.passed,
            "rejection_reason": self.rejection_reason,
            "diff_char_start": self.diff_char_start,
            "diff_char_end": self.diff_char_end,
            "diff_original_text": self.diff_original_text,
            "diff_modified_text": self.diff_modified_text,
            "unintended_modification_count": len(self.unintended_modifications),
            "has_agent_discrepancy": self.agent_discrepancy is not None,
        }


def verify_label(
    label_index: int,
    agent_label: dict[str, Any],
    originals: dict[str, str],
    modifieds: dict[str, str],
) -> VerificationResult:
    """Verify a single agent-reported label against mechanical diff.

    Args:
        label_index: Index of the label in the input file.
        agent_label: Raw dict from gold_labels.jsonl.
        originals: {doc_id: content} from anonymized_docs_original/.
        modifieds: {doc_id: content} from anonymized_docs/.

    Returns:
        VerificationResult with all findings.
    """
    result = VerificationResult(label_index, agent_label)
    doc_refs = agent_label.get("document_references", [])

    if not doc_refs:
        result.rejection_reason = "no document_references in label"
        return result

    # Determine the target document for diff — try all doc_refs to find the one that was modified
    scope = agent_label.get("scope", "intra_doc")
    target_doc_id = None
    original_content = None
    modified_content = None

    for candidate_id in doc_refs:
        orig = originals.get(candidate_id)
        mod = modifieds.get(candidate_id)
        if orig is not None and mod is not None and orig != mod:
            target_doc_id = candidate_id
            original_content = orig
            modified_content = mod
            break

    if target_doc_id is None:
        # No modified doc found — check if docs exist at all
        missing = [d for d in doc_refs if d not in originals or d not in modifieds]
        if missing:
            result.rejection_reason = f"document(s) {missing} not found in originals or modified docs"
        else:
            result.rejection_reason = "no diff detected between original and modified document for any referenced document"
        return result

    # Compute diff
    diff_ops = compute_diff(original_content, modified_content)

    if not diff_ops:
        result.rejection_reason = "no diff opcodes found"
        return result

    # Count non-equal opcodes: if > 1 replace/insert/delete, flag as contaminated
    if len(diff_ops) > 1:
        # Multiple changes detected -> unintended modifications
        extra_ops = []
        for tag, i1, i2, j1, j2 in diff_ops:
            extra_ops.append({
                "tag": tag,
                "original_range": [i1, i2],
                "modified_range": [j1, j2],
                "original_text": original_content[i1:i2],
                "modified_text": modified_content[j1:j2],
            })
        result.unintended_modifications = extra_ops
        result.rejection_reason = (
            f"multiple diffs detected ({len(diff_ops)} non-equal opcodes); "
            f"expected exactly 1 modification"
        )
        return result

    # Exactly one diff opcode -- this is the expected case
    tag, i1, i2, j1, j2 = diff_ops[0]
    result.diff_char_start = j1
    result.diff_char_end = j2
    result.diff_original_text = original_content[i1:i2]
    result.diff_modified_text = modified_content[j1:j2]

    # Context contamination check
    context_clean = check_context_contamination(
        original_content, modified_content, i1, i2, j1, j2,
    )
    if not context_clean:
        result.rejection_reason = "context contamination: surrounding text differs"
        return result

    # Compare diff-derived offsets with agent-reported offsets (log discrepancies)
    agent_char_start = agent_label.get("char_start")
    agent_char_end = agent_label.get("char_end")
    if agent_char_start is not None and agent_char_end is not None:
        if agent_char_start != j1 or agent_char_end != j2:
            result.agent_discrepancy = {
                "label_index": label_index,
                "agent_char_start": agent_char_start,
                "agent_char_end": agent_char_end,
                "diff_char_start": j1,
                "diff_char_end": j2,
                "agent_original_text": agent_label.get("original_text", ""),
                "agent_modified_text": agent_label.get("modified_text", ""),
                "diff_original_text": result.diff_original_text,
                "diff_modified_text": result.diff_modified_text,
            }
            logger.info(
                f"Label {label_index}: agent offsets ({agent_char_start}, {agent_char_end}) "
                f"differ from diff offsets ({j1}, {j2}); diff values take precedence"
            )

    # Build verified ContradictionLabel with diff-derived offsets
    try:
        verified = ContradictionLabel(
            scope=agent_label["scope"],
            mechanism=agent_label["mechanism"],
            detectability=agent_label["detectability"],
            system_affinity=agent_label["system_affinity"],
            difficulty=agent_label["difficulty"],
            char_start=j1,
            char_end=j2,
            original_text=result.diff_original_text,
            modified_text=result.diff_modified_text,
            rationale=agent_label.get("rationale", ""),
            ground_truth=agent_label.get("ground_truth", True),
            document_references=doc_refs,
        )
        result.verified_label = verified
        result.passed = True
    except Exception as e:
        result.rejection_reason = f"schema validation failed: {e}"

    return result


# ---------------------------------------------------------------------------
# Case-level verification
# ---------------------------------------------------------------------------


def verify_case(case_dir: Path) -> dict[str, Any]:
    """Run diff-based verification for a single case directory.

    Returns a summary dict with counts and any issues.
    """
    case_dir = Path(case_dir)
    original_dir = case_dir / "anonymized_docs_original"
    modified_dir = case_dir / "anonymized_docs"
    validation_dir = case_dir / "validation"
    contradictions_dir = case_dir / "contradictions"

    summary: dict[str, Any] = {
        "case_dir": str(case_dir),
        "total_labels": 0,
        "passed": 0,
        "rejected": 0,
        "unintended_modifications": 0,
        "agent_discrepancies": 0,
    }

    # Check pre-injection backup exists
    if not original_dir.exists():
        logger.error(
            f"No pre-injection backup found at {original_dir}; "
            f"cannot verify case {case_dir.name}"
        )
        summary["error"] = "no pre-injection backup (anonymized_docs_original/)"
        return summary

    # Load documents
    originals = load_docs_by_id(original_dir)
    modifieds = load_docs_by_id(modified_dir)

    # Load agent labels
    agent_labels = load_agent_labels(case_dir)
    summary["total_labels"] = len(agent_labels)

    if not agent_labels:
        logger.info(f"No agent labels found for case {case_dir.name}")
        return summary

    # Verify each label
    results: list[VerificationResult] = []
    for idx, label in enumerate(agent_labels):
        vr = verify_label(idx, label, originals, modifieds)
        results.append(vr)

    # Collect outputs
    verification_log: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    unintended: list[dict[str, Any]] = []
    discrepancies: list[dict[str, Any]] = []
    verified_labels: list[ContradictionLabel] = []

    for vr in results:
        verification_log.append(vr.to_log_dict())

        if vr.passed:
            summary["passed"] += 1
            assert vr.verified_label is not None
            verified_labels.append(vr.verified_label)
        else:
            summary["rejected"] += 1
            rejected.append({
                "label_index": vr.label_index,
                "reason": vr.rejection_reason,
                "agent_label": vr.agent_label,
            })

        if vr.unintended_modifications:
            summary["unintended_modifications"] += 1
            unintended.append({
                "label_index": vr.label_index,
                "modifications": vr.unintended_modifications,
                "agent_label": vr.agent_label,
            })

        if vr.agent_discrepancy:
            summary["agent_discrepancies"] += 1
            discrepancies.append(vr.agent_discrepancy)

    # Write validation outputs
    validation_dir.mkdir(parents=True, exist_ok=True)

    _write_json(validation_dir / "diff_verification_log.json", verification_log)
    _write_jsonl(validation_dir / "rejected_contradictions.jsonl", rejected)
    _write_json(validation_dir / "unintended_modifications.json", unintended)
    _write_json(validation_dir / "agent_label_discrepancies.json", discrepancies)

    # Write verified labels split by scope
    contradictions_dir.mkdir(parents=True, exist_ok=True)

    intra_labels = [l for l in verified_labels if l.scope == "intra_doc"]
    inter_labels = [l for l in verified_labels if l.scope == "inter_doc"]

    _write_model_jsonl(
        contradictions_dir / "intra_doc_contradictions.jsonl", intra_labels,
    )
    _write_model_jsonl(
        contradictions_dir / "inter_doc_contradictions.jsonl", inter_labels,
    )
    _write_model_jsonl(
        contradictions_dir / "all_contradictions.jsonl", verified_labels,
    )

    logger.info(
        f"Verification complete for {case_dir.name}: "
        f"{summary['passed']}/{summary['total_labels']} passed, "
        f"{summary['rejected']} rejected, "
        f"{summary['unintended_modifications']} unintended modifications, "
        f"{summary['agent_discrepancies']} discrepancies"
    )

    return summary


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: Any) -> None:
    """Write data as formatted JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _write_jsonl(path: Path, items: list[dict[str, Any]]) -> None:
    """Write list of dicts as JSONL."""
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _write_model_jsonl(path: Path, models: list) -> None:
    """Write list of Pydantic models as JSONL."""
    with open(path, "w", encoding="utf-8") as f:
        for model in models:
            f.write(model.model_dump_json() + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Diff-based gold label verification for CROSSFIRE dataset.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--case",
        type=Path,
        help="Path to a single case directory to verify.",
    )
    group.add_argument(
        "--all",
        type=Path,
        help="Path to dataset root; verifies all case directories found recursively.",
    )

    args = parser.parse_args()

    if args.case:
        summary = verify_case(args.case)
        print(json.dumps(summary, indent=2))
    elif args.all:
        dataset_root = args.all
        # Find case directories: look for dirs with anonymized_docs_original/
        case_dirs = sorted(
            p.parent
            for p in dataset_root.rglob("anonymized_docs_original")
            if p.is_dir()
        )
        if not case_dirs:
            logger.warning(f"No verifiable cases found under {dataset_root}")
            sys.exit(1)

        all_summaries: list[dict[str, Any]] = []
        for case_dir in case_dirs:
            logger.info(f"Verifying case: {case_dir}")
            summary = verify_case(case_dir)
            all_summaries.append(summary)

        total_labels = sum(s["total_labels"] for s in all_summaries)
        total_passed = sum(s["passed"] for s in all_summaries)
        total_rejected = sum(s["rejected"] for s in all_summaries)
        total_unintended = sum(s["unintended_modifications"] for s in all_summaries)
        total_discrepancies = sum(s["agent_discrepancies"] for s in all_summaries)

        aggregate = {
            "total_cases": len(all_summaries),
            "total_labels": total_labels,
            "passed": total_passed,
            "rejected": total_rejected,
            "unintended_modifications": total_unintended,
            "agent_discrepancies": total_discrepancies,
            "per_case": all_summaries,
        }
        print(json.dumps(aggregate, indent=2))


if __name__ == "__main__":
    main()
