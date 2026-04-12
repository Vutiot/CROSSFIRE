"""Evaluation result schemas for 2-scope, 3-stage pipeline evaluation."""

from typing import Literal

from pydantic import BaseModel


class ScopeResult(BaseModel):
    scope: Literal["intra_doc", "inter_doc"]
    precision: float
    recall: float
    f1: float
    partial_credit_score: float


class StageResult(BaseModel):
    stage: Literal[
        "claim_extraction",
        "cross_reference_identification",
        "contradiction_detection",
    ]
    precision: float
    recall: float
    f1: float


class RepresentationQualityResult(BaseModel):
    claim_coverage: float
    cross_reference_accuracy: float


class EvaluationResult(BaseModel):
    overall_precision: float
    overall_recall: float
    overall_f1: float
    overall_partial_credit_score: float | None = None
    distractor_false_positive_rate: float | None = None
    per_scope: list[ScopeResult] = []
    per_stage: list[StageResult] = []
    representation_quality: RepresentationQualityResult | None = None


class MetricStats(BaseModel):
    mean: float
    std: float
    ci_lower: float
    ci_upper: float


class AggregatedResult(BaseModel):
    n_seeds: int
    precision: MetricStats
    recall: MetricStats
    f1: MetricStats
    partial_credit_score: MetricStats | None = None
    distractor_fpr: MetricStats | None = None
    per_scope: dict[str, dict[str, MetricStats]] = {}
    per_stage: dict[str, dict[str, MetricStats]] = {}
    mode_comparison: dict[str, float] | None = None
