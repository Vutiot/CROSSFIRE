"""Pipeline report schemas."""

from pydantic import BaseModel, Field


class DetectedIncoherence(BaseModel):
    id: str
    evidence_references: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    description: str


class PipelineReport(BaseModel):
    pipeline_mode: str
    corpus_path: str
    detections: list[DetectedIncoherence] = []
    timestamp: str
