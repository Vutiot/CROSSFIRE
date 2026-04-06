"""Null strategy implementations for pipeline mode switching.

NullGraphStrategy and NullReasoningStrategy produce empty results,
enabling mode switching via constructor injection without runtime branching.
"""

from crossfire.pipeline.strategies.base import (
    GraphResult,
    GraphStrategy,
    ReasoningResult,
    ReasoningStrategy,
)


class NullGraphStrategy(GraphStrategy):
    """Returns empty graph results. Used for agentic mode (FR18)."""

    def run(self, corpus_path: str) -> tuple[GraphResult, None]:
        return GraphResult(), None


class NullReasoningStrategy(ReasoningStrategy):
    """Returns empty reasoning results. Used for graph-native mode (FR19)."""

    def run(self, corpus_path: str) -> tuple[ReasoningResult, None]:
        return ReasoningResult(), None
