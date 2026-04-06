"""Abstract strategy interfaces and intermediate result models for the auditing pipeline."""

from abc import ABC, abstractmethod

from pydantic import BaseModel

from crossfire.shared.schemas.entities import EntityGraph
from crossfire.shared.schemas.reports import DetectedIncoherence


class GraphResult(BaseModel):
    """Intermediate result from a graph strategy."""

    detected_incoherences: list[DetectedIncoherence] = []
    internal_graph: EntityGraph | None = None


class ReasoningResult(BaseModel):
    """Intermediate result from a reasoning strategy."""

    detected_incoherences: list[DetectedIncoherence] = []


class GraphStrategy(ABC):
    """Abstract base for graph-based auditing strategies."""

    @abstractmethod
    def run(self, corpus_path: str) -> tuple[GraphResult | None, str | None]:
        """Run graph strategy against a corpus.

        Returns (GraphResult, None) on success, (None, error_message) on failure.
        """


class ReasoningStrategy(ABC):
    """Abstract base for LLM reasoning-based auditing strategies."""

    @abstractmethod
    def run(self, corpus_path: str) -> tuple[ReasoningResult | None, str | None]:
        """Run reasoning strategy against a corpus.

        Returns (ReasoningResult, None) on success, (None, error_message) on failure.
        """
