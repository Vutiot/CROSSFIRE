"""CROSSFIRE evaluation module — scoring pipeline results against gold labels."""

from crossfire.evaluation.aggregate import aggregate_seeds, compare_modes
from crossfire.evaluation.binary_scorer import score_binary
from crossfire.evaluation.distractor_eval import score_distractors
from crossfire.evaluation.partial_scorer import score_partial
from crossfire.evaluation.representation_eval import score_representation
from crossfire.evaluation.scope_breakdown import score_by_scope
from crossfire.evaluation.stage_breakdown import score_by_stage

__all__ = [
    "aggregate_seeds",
    "compare_modes",
    "score_binary",
    "score_distractors",
    "score_partial",
    "score_by_scope",
    "score_by_stage",
    "score_representation",
]
