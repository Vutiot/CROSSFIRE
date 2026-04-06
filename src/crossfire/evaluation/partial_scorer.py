"""Partial credit (localization proximity) scorer for pipeline evaluation (FR24)."""

from loguru import logger

from crossfire.shared.schemas.evaluation import EvaluationResult
from crossfire.shared.schemas.incoherences import IncoherenceLabel
from crossfire.shared.schemas.reports import PipelineReport


def _jaccard_similarity(refs_a: list[str], refs_b: list[str]) -> float:
    """Compute Jaccard similarity between two document reference lists."""
    set_a = set(refs_a)
    set_b = set(refs_b)
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def score_partial(
    report: PipelineReport,
    gold_labels: list[IncoherenceLabel],
) -> EvaluationResult:
    """Score pipeline detections with partial credit for localization proximity.

    Uses Jaccard similarity on document reference sets.  Greedy one-to-one
    assignment by highest similarity prevents double-counting.

    Returns EvaluationResult with partial-credit precision, recall, F1,
    and overall_partial_credit_score.
    """
    logger.info(
        f"Partial credit scoring: {len(report.detections)} detections "
        f"vs {len(gold_labels)} gold labels"
    )

    n_detections = len(report.detections)
    n_gold = len(gold_labels)

    # Edge cases
    if n_detections == 0 and n_gold == 0:
        result = EvaluationResult(
            overall_precision=0.0,
            overall_recall=0.0,
            overall_f1=0.0,
            overall_partial_credit_score=0.0,
        )
        logger.info(
            f"Partial result: P={result.overall_precision:.4f} "
            f"R={result.overall_recall:.4f} F1={result.overall_f1:.4f} "
            f"PCS={result.overall_partial_credit_score:.4f}"
        )
        return result

    if n_detections == 0:
        result = EvaluationResult(
            overall_precision=0.0,
            overall_recall=0.0,
            overall_f1=0.0,
            overall_partial_credit_score=0.0,
        )
        logger.info(
            f"Partial result: P={result.overall_precision:.4f} "
            f"R={result.overall_recall:.4f} F1={result.overall_f1:.4f} "
            f"PCS={result.overall_partial_credit_score:.4f}"
        )
        return result

    if n_gold == 0:
        result = EvaluationResult(
            overall_precision=1.0,
            overall_recall=0.0,
            overall_f1=0.0,
            overall_partial_credit_score=0.0,
        )
        logger.info(
            f"Partial result: P={result.overall_precision:.4f} "
            f"R={result.overall_recall:.4f} F1={result.overall_f1:.4f} "
            f"PCS={result.overall_partial_credit_score:.4f}"
        )
        return result

    # Compute all pairwise similarities
    pairs: list[tuple[float, int, int, str, str]] = []
    for d_idx, detection in enumerate(report.detections):
        for g_idx, gold in enumerate(gold_labels):
            sim = _jaccard_similarity(
                detection.evidence_references, gold.document_references
            )
            if sim > 0:
                # Tie-breaking: detection id then gold id (deterministic)
                pairs.append((sim, d_idx, g_idx, detection.id, gold.id))

    # Sort descending by similarity, then by det id, then by gold id for determinism
    pairs.sort(key=lambda p: (-p[0], p[3], p[4]))

    # Greedy one-to-one assignment
    assigned_det: set[int] = set()
    assigned_gold: set[int] = set()
    assigned_similarities: list[float] = []

    for sim, d_idx, g_idx, _, _ in pairs:
        if d_idx not in assigned_det and g_idx not in assigned_gold:
            assigned_det.add(d_idx)
            assigned_gold.add(g_idx)
            assigned_similarities.append(sim)

    sum_sim = sum(assigned_similarities)

    precision = sum_sim / n_detections
    recall = sum_sim / n_gold
    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0

    pcs = sum_sim / len(assigned_similarities) if assigned_similarities else 0.0

    result = EvaluationResult(
        overall_precision=precision,
        overall_recall=recall,
        overall_f1=f1,
        overall_partial_credit_score=pcs,
    )
    logger.info(
        f"Partial result: P={result.overall_precision:.4f} "
        f"R={result.overall_recall:.4f} F1={result.overall_f1:.4f} "
        f"PCS={result.overall_partial_credit_score:.4f}"
    )
    return result
