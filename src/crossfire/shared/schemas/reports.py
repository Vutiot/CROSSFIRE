"""Pipeline report schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class DetectedContradiction(BaseModel):
    scope: Literal["intra_doc", "inter_doc"]
    document_references: list[str]
    text_span_start: int
    text_span_end: int
    evidence_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    description: str


class PipelineReport(BaseModel):
    pipeline_mode: str
    case_dir: str
    detections: list[DetectedContradiction] = []
    timestamp: str
    run_metadata: dict = {}
