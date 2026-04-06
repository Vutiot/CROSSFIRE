"""Pipeline strategy interfaces and implementations."""

from crossfire.pipeline.strategies.base import (
    GraphResult,
    GraphStrategy,
    ReasoningResult,
    ReasoningStrategy,
)
from crossfire.pipeline.strategies.graph_strategy import LLMGraphStrategy
from crossfire.pipeline.strategies.null_strategies import (
    NullGraphStrategy,
    NullReasoningStrategy,
)
from crossfire.pipeline.strategies.reasoning_strategy import LLMReasoningStrategy

__all__ = [
    "GraphResult",
    "GraphStrategy",
    "LLMGraphStrategy",
    "LLMReasoningStrategy",
    "NullGraphStrategy",
    "NullReasoningStrategy",
    "ReasoningResult",
    "ReasoningStrategy",
]
