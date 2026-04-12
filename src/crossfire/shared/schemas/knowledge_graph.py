"""Knowledge graph intermediate artifact schemas.

These are intermediate artifacts that ship for transparency.
The evaluator NEVER imports these for scoring.
"""

from pydantic import BaseModel, Field


class KnowledgeGraphClaim(BaseModel):
    claim_id: str
    subject: str
    predicate: str
    object: str
    source_document: str
    confidence: float = Field(ge=0.0, le=1.0)


class CrossReference(BaseModel):
    reference_id: str
    source_claim: str
    target_claim: str
    relationship: str
    source_documents: list[str]
