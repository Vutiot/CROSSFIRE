"""Incoherence and distractor label schemas."""

from typing import Literal

from pydantic import BaseModel

Scope = Literal["intra_doc", "intra_corpus", "inter_corpus"]
Mechanism = Literal[
    "numeric_drift",
    "entity_swap",
    "causal_inversion",
    "temporal_contradiction",
    "omission_based_implicit",
    "temporal_revision_conflict",
]
Detectability = Literal["single_hop", "multi_hop", "entity_resolution_dependent"]
SystemAffinity = Literal["balanced", "graph_favoring", "agentic_favoring"]


class IncoherenceLabel(BaseModel):
    id: str
    scope: Scope
    mechanism: Mechanism
    detectability: Detectability
    system_affinity: SystemAffinity
    document_references: list[str]
    modified_fact: str
    original_fact: str


class DistractorLabel(BaseModel):
    id: str
    scope: Scope
    document_references: list[str]
    divergence_type: str
    description: str
