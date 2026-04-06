"""Baseline auditing pipelines for lower-bound comparison."""

from crossfire.pipeline.baselines.bm25_baseline import run_bm25_baseline
from crossfire.pipeline.baselines.hypothesis_only import run_hypothesis_only_baseline
from crossfire.pipeline.baselines.random_baseline import run_random_baseline

__all__ = [
    "run_bm25_baseline",
    "run_hypothesis_only_baseline",
    "run_random_baseline",
]
