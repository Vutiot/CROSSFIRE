"""Binary (exact match) scorer for pipeline evaluation (FR23)."""

from loguru import logger

from crossfire.shared.schemas.contradictions import ContradictionLabel
from crossfire.shared.schemas.evaluation import EvaluationResult
from crossfire.shared.schemas.reports import PipelineReport


def score_binary(
    report: PipelineReport,
    gold_labels: list[ContradictionLabel],
) -> EvaluationResult:
    """Score pipeline detections against gold labels using exact match.

    A detection matches a gold label when their document reference sets are
    identical.  Greedy one-to-one assignment prevents double-counting.

    Returns EvaluationResult with precision, recall, and F1.
    """
    logger.info(
        f"Binary scoring: {len(report.detections)} detections "
        f"vs {len(gold_labels)} gold labels"
    )

    n_detections = len(report.detections)
    n_gold = len(gold_labels)

    # Edge cases
    if n_detections == 0 and n_gold == 0:
        result = EvaluationResult(
            overall_precision=0.0, overall_recall=0.0, overall_f1=0.0
        )
        logger.info(
            f"Binary result: P={result.overall_precision:.4f} "
            f"R={result.overall_recall:.4f} F1={result.overall_f1:.4f}"
        )
        return result

    if n_detections == 0:
        result = EvaluationResult(
            overall_precision=0.0, overall_recall=0.0, overall_f1=0.0
        )
        logger.info(
            f"Binary result: P={result.overall_precision:.4f} "
            f"R={result.overall_recall:.4f} F1={result.overall_f1:.4f}"
        )
        return result

    if n_gold == 0:
        result = EvaluationResult(
            overall_precision=1.0, overall_recall=0.0, overall_f1=0.0
        )
        logger.info(
            f"Binary result: P={result.overall_precision:.4f} "
            f"R={result.overall_recall:.4f} F1={result.overall_f1:.4f}"
        )
        return result

    # Build lookup: normalized doc refs -> list of gold label indices
    gold_ref_map: dict[tuple[str, ...], list[int]] = {}
    for i, label in enumerate(gold_labels):
        key = tuple(sorted(label.document_references))
        gold_ref_map.setdefault(key, []).append(i)

    # Greedy one-to-one matching
    matched_gold: set[int] = set()
    matched_count = 0

    for detection in sorted(report.detections, key=lambda d: d.description):
        det_key = tuple(sorted(detection.document_references))
        candidates = gold_ref_map.get(det_key, [])
        for gold_idx in candidates:
            if gold_idx not in matched_gold:
                matched_gold.add(gold_idx)
                matched_count += 1
                break

    precision = matched_count / n_detections
    recall = matched_count / n_gold
    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0

    result = EvaluationResult(
        overall_precision=precision,
        overall_recall=recall,
        overall_f1=f1,
    )
    logger.info(
        f"Binary result: P={result.overall_precision:.4f} "
        f"R={result.overall_recall:.4f} F1={result.overall_f1:.4f}"
    )
    return result
