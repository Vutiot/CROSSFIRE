"""Per-stage evaluation breakdown (FR26)."""

from loguru import logger

from crossfire.evaluation.binary_scorer import score_binary
from crossfire.shared.schemas.contradictions import ContradictionLabel
from crossfire.shared.schemas.evaluation import EvaluationResult, StageResult
from crossfire.shared.schemas.reports import PipelineReport

DETECTABILITY_TO_STAGE: dict[str, str] = {
    "single_hop": "claim_extraction",
    "multi_hop": "cross_reference_identification",
    "entity_resolution_dependent": "contradiction_detection",
}


def score_by_stage(
    report: PipelineReport,
    gold_labels: list[ContradictionLabel],
) -> EvaluationResult:
    """Score pipeline detections with per-stage breakdown.

    Maps gold label detectability to pipeline stages and runs binary scoring
    independently per stage.  Each stage evaluates a disjoint subset of gold
    labels against ALL detections, ensuring non-cascading scores.

    Returns EvaluationResult with overall metrics and per_stage breakdown.
    """
    # Overall metrics across all gold labels
    overall = score_binary(report, gold_labels)

    # Discover stages present in gold labels
    stages: set[str] = set()
    for label in gold_labels:
        stage = DETECTABILITY_TO_STAGE.get(label.detectability)
        if stage:
            stages.add(stage)

    logger.info(
        f"Stage breakdown: {len(stages)} stages found "
        f"in {len(gold_labels)} gold labels"
    )

    # Per-stage scoring
    stage_results: list[StageResult] = []
    for stage in sorted(stages):
        stage_gold = [
            g
            for g in gold_labels
            if DETECTABILITY_TO_STAGE.get(g.detectability) == stage
        ]
        binary_result = score_binary(report, stage_gold)

        sr = StageResult(
            stage=stage,
            precision=binary_result.overall_precision,
            recall=binary_result.overall_recall,
            f1=binary_result.overall_f1,
        )
        stage_results.append(sr)
        logger.info(
            f"Stage '{stage}': P={sr.precision:.4f} R={sr.recall:.4f} "
            f"F1={sr.f1:.4f}"
        )

    return EvaluationResult(
        overall_precision=overall.overall_precision,
        overall_recall=overall.overall_recall,
        overall_f1=overall.overall_f1,
        per_stage=stage_results,
    )
