"""Configuration schemas for CROSSFIRE preset and runtime configs."""

from typing import Literal, Union

from pydantic import BaseModel


class ScopeDistribution(BaseModel):
    intra_doc: float
    intra_corpus: float
    inter_corpus: float


class DetectabilityDistribution(BaseModel):
    single_hop: float
    multi_hop: float
    entity_resolution: float


class IncoherenceConfig(BaseModel):
    scope_distribution: ScopeDistribution
    mechanism: str
    detectability_distribution: DetectabilityDistribution
    system_affinity: Literal["balanced", "graph-favoring", "agentic-favoring"]
    count: Union[str, int]


class PresetConfig(BaseModel):
    name: str
    description: str
    master_seed: int
    subcorpora_count: int
    docs_per_subcorpus: int
    connectivity_level: Literal[0, 1, 2, 3]
    doc_type_mix: str
    incoherences: IncoherenceConfig
    distractor_ratio: float


class GeneratorConfig(PresetConfig):
    output_dir: str = "output/generated"
    dry_run: bool = False


class PipelineConfig(BaseModel):
    mode: Literal["hybrid", "agentic", "graph-native"]
    corpus_path: str
    output_dir: str = "output/reports"
