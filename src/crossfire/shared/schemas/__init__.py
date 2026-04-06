"""CROSSFIRE data contract schemas."""

from crossfire.shared.schemas.config import (
    ScopeDistribution,
    DetectabilityDistribution,
    IncoherenceConfig,
    PresetConfig,
    GeneratorConfig,
    PipelineConfig,
)
from crossfire.shared.schemas.corpus import Document, SubcorpusMetadata
from crossfire.shared.schemas.entities import EntityNode, EntityEdge, EntityGraph
from crossfire.shared.schemas.incoherences import IncoherenceLabel, DistractorLabel
from crossfire.shared.schemas.reports import DetectedIncoherence, PipelineReport
from crossfire.shared.schemas.evaluation import (
    ScopeResult,
    StageResult,
    RepresentationQualityResult,
    EvaluationResult,
    MetricStats,
    AggregatedResult,
)

__all__ = [
    "ScopeDistribution",
    "DetectabilityDistribution",
    "IncoherenceConfig",
    "PresetConfig",
    "GeneratorConfig",
    "PipelineConfig",
    "Document",
    "SubcorpusMetadata",
    "EntityNode",
    "EntityEdge",
    "EntityGraph",
    "IncoherenceLabel",
    "DistractorLabel",
    "DetectedIncoherence",
    "PipelineReport",
    "ScopeResult",
    "StageResult",
    "RepresentationQualityResult",
    "EvaluationResult",
    "MetricStats",
    "AggregatedResult",
]
