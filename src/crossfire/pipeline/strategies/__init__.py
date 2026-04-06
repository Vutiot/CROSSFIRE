"""Pipeline strategy interfaces and implementations."""

from crossfire.pipeline.strategies.base import (
    GraphResult,
    GraphStrategy,
    ReasoningResult,
    ReasoningStrategy,
)
from crossfire.pipeline.strategies.null_strategies import (
    NullGraphStrategy,
    NullReasoningStrategy,
)

__all__ = [
    "GraphResult",
    "GraphStrategy",
    "NullGraphStrategy",
    "NullReasoningStrategy",
    "ReasoningResult",
    "ReasoningStrategy",
]
