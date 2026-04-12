"""CROSSFIRE data contract schemas."""

from crossfire.shared.schemas.anonymization import AnonymizationMapping
from crossfire.shared.schemas.config import (
    DatasetVersion,
    GenerationParams,
    PipelineConfig,
)
from crossfire.shared.schemas.contradictions import (
    ContradictionLabel,
    DistractorLabel,
)
from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.domain_registry import DomainEntry, DomainRegistry
from crossfire.shared.schemas.evaluation import (
    AggregatedResult,
    EvaluationResult,
    MetricStats,
    RepresentationQualityResult,
    ScopeResult,
    StageResult,
)
from crossfire.shared.schemas.knowledge_graph import (
    CrossReference,
    KnowledgeGraphClaim,
)
from crossfire.shared.schemas.reports import DetectedContradiction, PipelineReport
from crossfire.shared.schemas.scope_map import ScopeMap, ScopeMapEntry

__all__ = [
    "AnonymizationMapping",
    "AggregatedResult",
    "ContradictionLabel",
    "CrossReference",
    "DatasetVersion",
    "DetectedContradiction",
    "DistractorLabel",
    "Document",
    "DomainEntry",
    "DomainRegistry",
    "EvaluationResult",
    "GenerationParams",
    "KnowledgeGraphClaim",
    "MetricStats",
    "PipelineConfig",
    "PipelineReport",
    "RepresentationQualityResult",
    "ScopeMap",
    "ScopeMapEntry",
    "ScopeResult",
    "StageResult",
]
