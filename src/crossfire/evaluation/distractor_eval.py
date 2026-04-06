"""Distractor false positive evaluation (FR28)."""

from loguru import logger

from crossfire.shared.schemas.evaluation import EvaluationResult
from crossfire.shared.schemas.incoherences import DistractorLabel
from crossfire.shared.schemas.reports import PipelineReport


def score_distractors(
    report: PipelineReport,
    distractor_labels: list[DistractorLabel],
) -> EvaluationResult:
    """Compute false positive rate on distractor labels.

    A distractor is "flagged" when any detection's evidence_references
    exactly match the distractor's document_references.

    FP rate = flagged distractors / total distractors.
    Reported separately from incoherence detection accuracy.
    """
    n_distractors = len(distractor_labels)
    n_detections = len(report.detections)

    if n_distractors == 0 or n_detections == 0:
        rate = 0.0
        logger.info(
            f"Distractor eval: 0/{n_distractors} distractors flagged "
            f"(FP rate={rate:.4f})"
        )
        return EvaluationResult(
            overall_precision=0.0,
            overall_recall=0.0,
            overall_f1=0.0,
            distractor_false_positive_rate=rate,
        )

    # Build detection reference index
    det_ref_set: set[tuple[str, ...]] = set()
    for detection in report.detections:
        key = tuple(sorted(detection.evidence_references))
        det_ref_set.add(key)

    # Count flagged distractors
    flagged = 0
    for distractor in distractor_labels:
        key = tuple(sorted(distractor.document_references))
        if key in det_ref_set:
            flagged += 1

    rate = flagged / n_distractors

    logger.info(
        f"Distractor eval: {flagged}/{n_distractors} distractors flagged "
        f"(FP rate={rate:.4f})"
    )
    return EvaluationResult(
        overall_precision=0.0,
        overall_recall=0.0,
        overall_f1=0.0,
        distractor_false_positive_rate=rate,
    )
