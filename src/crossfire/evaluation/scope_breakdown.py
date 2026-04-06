"""Per-scope evaluation breakdown (FR25)."""

from loguru import logger

from crossfire.evaluation.binary_scorer import score_binary
from crossfire.evaluation.partial_scorer import score_partial
from crossfire.shared.schemas.evaluation import EvaluationResult, ScopeResult
from crossfire.shared.schemas.incoherences import IncoherenceLabel
from crossfire.shared.schemas.reports import PipelineReport


def score_by_scope(
    report: PipelineReport,
    gold_labels: list[IncoherenceLabel],
) -> EvaluationResult:
    """Score pipeline detections with per-scope breakdown.

    Groups gold labels by scope (intra_doc, intra_corpus, inter_corpus) and
    runs both binary and partial credit scoring independently per scope.
    Each scope is evaluated against ALL detections but only that scope's
    gold labels, ensuring complete independence between scopes.

    Returns EvaluationResult with overall metrics and per_scope breakdown.
    """
    # Overall metrics across all gold labels
    overall_binary = score_binary(report, gold_labels)
    overall_partial = score_partial(report, gold_labels)

    # Discover scopes present in gold labels
    scopes: set[str] = set()
    for label in gold_labels:
        scopes.add(label.scope)

    logger.info(
        f"Scope breakdown: {len(scopes)} scopes found "
        f"in {len(gold_labels)} gold labels"
    )

    # Per-scope scoring
    scope_results: list[ScopeResult] = []
    for scope in sorted(scopes):
        scope_gold = [g for g in gold_labels if g.scope == scope]
        binary_result = score_binary(report, scope_gold)
        partial_result = score_partial(report, scope_gold)

        sr = ScopeResult(
            scope=scope,
            precision=binary_result.overall_precision,
            recall=binary_result.overall_recall,
            f1=binary_result.overall_f1,
            partial_credit_score=partial_result.overall_partial_credit_score or 0.0,
        )
        scope_results.append(sr)
        logger.info(
            f"Scope '{scope}': P={sr.precision:.4f} R={sr.recall:.4f} "
            f"F1={sr.f1:.4f} PCS={sr.partial_credit_score:.4f}"
        )

    return EvaluationResult(
        overall_precision=overall_binary.overall_precision,
        overall_recall=overall_binary.overall_recall,
        overall_f1=overall_binary.overall_f1,
        overall_partial_credit_score=overall_partial.overall_partial_credit_score,
        per_scope=scope_results,
    )
