"""Contradiction and distractor label schemas (replaces incoherences.py)."""

from typing import Literal

from pydantic import BaseModel, Field

Scope = Literal["intra_doc", "inter_doc"]
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
DivergenceType = Literal[
    "expert_opinion",
    "preliminary_vs_final",
    "measurement_methodology",
    "uncertainty_expression",
]
Difficulty = Literal["easy", "medium", "hard"]


class ContradictionLabel(BaseModel):
    scope: Scope
    mechanism: Mechanism
    detectability: Detectability
    system_affinity: SystemAffinity
    difficulty: Difficulty
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    original_text: str
    modified_text: str
    rationale: str
    ground_truth: bool
    document_references: list[str]


class DistractorLabel(BaseModel):
    scope: Scope
    divergence_type: DivergenceType
    document_references: list[str]
    description: str
