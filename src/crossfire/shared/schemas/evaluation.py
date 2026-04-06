"""Evaluation result schemas."""

from pydantic import BaseModel


class ScopeResult(BaseModel):
    scope: str
    precision: float
    recall: float
    f1: float
    partial_credit_score: float


class StageResult(BaseModel):
    stage: str
    precision: float
    recall: float
    f1: float


class EvaluationResult(BaseModel):
    overall_precision: float
    overall_recall: float
    overall_f1: float
    per_scope: list[ScopeResult] = []
    per_stage: list[StageResult] = []
