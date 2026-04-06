"""Corpus document and metadata schemas."""

from typing import Literal

from pydantic import BaseModel, Field

DocumentType = Literal[
    "investigation_report",
    "technical_analysis",
    "witness_testimony",
    "regulatory_filing",
    "press_coverage",
    "expert_deposition",
    "internal_memo",
    "preliminary_report",
]


class Document(BaseModel):
    id: str
    document_type: DocumentType
    subcorpus_id: str
    reliability_signal: float = Field(ge=0.0, le=1.0)
    content: str


class SubcorpusMetadata(BaseModel):
    subcorpus_id: str
    document_count: int
    document_types: list[str]
