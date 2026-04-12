"""Abstract strategy interfaces and intermediate result models for the auditing pipeline."""

from abc import ABC, abstractmethod

from pydantic import BaseModel

from crossfire.shared.schemas.knowledge_graph import KnowledgeGraphClaim
from crossfire.shared.schemas.reports import DetectedContradiction


class GraphResult(BaseModel):
    """Intermediate result from a graph strategy."""

    detected_contradictions: list[DetectedContradiction] = []
    internal_claims: list[KnowledgeGraphClaim] = []


class ReasoningResult(BaseModel):
    """Intermediate result from a reasoning strategy."""

    detected_contradictions: list[DetectedContradiction] = []


class GraphStrategy(ABC):
    """Abstract base for graph-based auditing strategies."""

    @abstractmethod
    def run(self, case_dir: str) -> tuple[GraphResult | None, str | None]:
        """Run graph strategy against a case directory.

        Returns (GraphResult, None) on success, (None, error_message) on failure.
        """


class ReasoningStrategy(ABC):
    """Abstract base for LLM reasoning-based auditing strategies."""

    @abstractmethod
    def run(self, case_dir: str) -> tuple[ReasoningResult | None, str | None]:
        """Run reasoning strategy against a case directory.

        Returns (ReasoningResult, None) on success, (None, error_message) on failure.
        """
