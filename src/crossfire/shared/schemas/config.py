"""Configuration schemas for CROSSFIRE pipeline and dataset versioning."""

from typing import Literal

from pydantic import BaseModel, Field


class PipelineConfig(BaseModel):
    mode: Literal["hybrid", "agentic", "graph_native"]
    case_dir: str
    output_dir: str = "output/reports"


class DatasetVersion(BaseModel):
    version_id: str
    base_version: str | None = None
    label_corrections: list[str] = []


class GenerationParams(BaseModel):
    version_id: str
    base_version: str | None = None
    contradiction_rate_intra_doc: float = Field(ge=0.0, le=1.0)
    contradiction_rate_inter_doc: float = Field(ge=0.0, le=1.0)
    distractor_ratio: float = Field(ge=0.0)
    mechanism_distribution: dict[str, float] = {}
    difficulty_distribution: dict[str, float] = {}
    affinity_distribution: dict[str, float] = {}
    extraction_model: str = "claude-sonnet-4-20250514"
    reasoning_model: str = "claude-opus-4-20250514"
