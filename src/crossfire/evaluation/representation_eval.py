"""Layer 1 representation quality evaluation — system claims vs gold claims (FR27).

Evaluates the quality of the pipeline's internal knowledge graph claims
against gold-standard claims derived from injection annotations.
"""

from loguru import logger

from crossfire.shared.schemas.evaluation import (
    EvaluationResult,
    RepresentationQualityResult,
)
from crossfire.shared.schemas.knowledge_graph import KnowledgeGraphClaim


def _normalize(text: str) -> str:
    """Normalize text for comparison."""
    return text.strip().lower()


def score_representation(
    system_claims: list[KnowledgeGraphClaim],
    gold_claims: list[KnowledgeGraphClaim],
) -> EvaluationResult:
    """Evaluate pipeline's internal knowledge graph claims against gold claims.

    Computes two metrics:
    - Claim coverage: fraction of gold (subject, predicate, object) triples
      covered by system claims
    - Cross-reference accuracy: fraction of system claims whose source_document
      associations match gold claim source_document associations

    Returns EvaluationResult with representation_quality populated.
    """
    logger.info(
        f"Representation eval: system={len(system_claims)} claims, "
        f"gold={len(gold_claims)} claims"
    )

    # Handle both-empty case
    if not system_claims and not gold_claims:
        rq = RepresentationQualityResult(
            claim_coverage=0.0,
            cross_reference_accuracy=0.0,
        )
        logger.info(
            f"Representation result: claim_coverage={rq.claim_coverage:.4f} "
            f"cross_ref_accuracy={rq.cross_reference_accuracy:.4f}"
        )
        return EvaluationResult(
            overall_precision=0.0,
            overall_recall=0.0,
            overall_f1=0.0,
            representation_quality=rq,
        )

    # Claim coverage: fraction of gold triples found in system claims
    gold_triples = {
        (_normalize(c.subject), _normalize(c.predicate), _normalize(c.object))
        for c in gold_claims
    }
    system_triples = {
        (_normalize(c.subject), _normalize(c.predicate), _normalize(c.object))
        for c in system_claims
    }
    if gold_triples:
        claim_coverage = len(gold_triples & system_triples) / len(gold_triples)
    else:
        claim_coverage = 0.0

    # Cross-reference accuracy: fraction of system (subject, predicate, object, source_doc)
    # tuples matching gold tuples
    gold_sourced = {
        (
            _normalize(c.subject),
            _normalize(c.predicate),
            _normalize(c.object),
            c.source_document,
        )
        for c in gold_claims
    }
    system_sourced = {
        (
            _normalize(c.subject),
            _normalize(c.predicate),
            _normalize(c.object),
            c.source_document,
        )
        for c in system_claims
    }
    if system_sourced:
        cross_ref_accuracy = len(system_sourced & gold_sourced) / len(system_sourced)
    elif not gold_sourced:
        cross_ref_accuracy = 1.0
    else:
        cross_ref_accuracy = 0.0

    rq = RepresentationQualityResult(
        claim_coverage=claim_coverage,
        cross_reference_accuracy=cross_ref_accuracy,
    )
    logger.info(
        f"Representation result: claim_coverage={rq.claim_coverage:.4f} "
        f"cross_ref_accuracy={rq.cross_reference_accuracy:.4f}"
    )
    return EvaluationResult(
        overall_precision=0.0,
        overall_recall=0.0,
        overall_f1=0.0,
        representation_quality=rq,
    )
