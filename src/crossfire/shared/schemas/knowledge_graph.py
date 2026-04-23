"""Knowledge graph intermediate artifact schemas.

These are intermediate artifacts that ship for transparency.
The evaluator NEVER imports these for scoring.
"""

from typing import Literal

from pydantic import BaseModel, Field


# Categorical relation enum — shared by pairwise cross-references and multi-
# claim clusters. Free-text rationale / theme lives in a separate field.
RelationCategory = Literal[
    "supports",          # A corroborates B
    "contradicts",       # A directly conflicts with B
    "same_fact",         # A restates the same proposition as B
    "disagrees_with",    # milder than contradicts (witness disagreement)
    "discrepancy",       # spec-vs-spec / spec-vs-test mismatch
    "elaborates",        # A provides detail / causal explanation for B
    "sequence",          # temporal or chronological ordering
    "causal",            # A caused / drove / enabled B
    "response_to",       # challenge → justification, advice → action
    "omission",          # identifies a gap / absence / failure-to-do
    "awareness",         # establishes knowledge / ignorance of something
    "shared_topic",      # group shares a common subject ("All concern X")
    "other",             # didn't match any of the above — needs triage
]


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


# ── Evolved KG link schema ──────────────────────────────────────────────────
# The grenfell-module1 corpus exposed that the single-string `relationship`
# field was being used for two distinct kinds of data: categorical predicates
# AND free-text analytical summaries. The models below split those concerns:
# `ClaimCrossRef` keeps the categorical slot clean, and `ClaimCluster`
# represents many-way groupings (3+ claims) with a prose theme.
#
# These are additive; the legacy `CrossReference` model stays unchanged for
# existing evaluator / test code paths.


class ClaimCrossRef(BaseModel):
    """Pairwise link between 1–2 claims, categorical relation + prose rationale."""
    xref_id: str
    claim_ids: list[str] = Field(min_length=1, max_length=2)
    relationship_type: RelationCategory
    rationale: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ClaimCluster(BaseModel):
    """Group of 3+ claims that share a common relation / theme."""
    cluster_id: str
    claim_ids: list[str] = Field(min_length=3)
    relation: RelationCategory
    theme: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
