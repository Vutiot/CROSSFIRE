"""Multi-seed aggregation and mode comparison (FR29)."""

import math
from statistics import mean as _mean
from statistics import stdev as _stdev

from loguru import logger
from scipy import stats as scipy_stats

from crossfire.shared.schemas.evaluation import (
    AggregatedResult,
    EvaluationResult,
    MetricStats,
)


def _compute_stats(values: list[float], confidence: float) -> MetricStats:
    """Compute mean, std, and confidence interval for a list of values."""
    n = len(values)
    if n == 0:
        return MetricStats(mean=0.0, std=0.0, ci_lower=0.0, ci_upper=0.0)

    m = _mean(values)

    if n == 1:
        return MetricStats(mean=m, std=0.0, ci_lower=m, ci_upper=m)

    s = _stdev(values)
    se = s / math.sqrt(n)

    if se == 0.0:
        return MetricStats(mean=m, std=0.0, ci_lower=m, ci_upper=m)

    ci_low, ci_high = scipy_stats.t.interval(confidence, df=n - 1, loc=m, scale=se)
    return MetricStats(mean=m, std=s, ci_lower=ci_low, ci_upper=ci_high)


def aggregate_seeds(
    results: list[EvaluationResult],
    confidence: float = 0.95,
) -> AggregatedResult:
    """Aggregate evaluation results across multiple seeds.

    Computes mean, standard deviation, and confidence intervals for all
    metrics.  Includes per-scope and per-stage breakdowns.

    Uses scipy.stats.t for confidence intervals.
    """
    n = len(results)
    logger.info(f"Aggregating {n} seed results (confidence={confidence})")

    if n == 0:
        zero = MetricStats(mean=0.0, std=0.0, ci_lower=0.0, ci_upper=0.0)
        return AggregatedResult(
            n_seeds=0, precision=zero, recall=zero, f1=zero
        )

    # Overall metrics
    precisions = [r.overall_precision for r in results]
    recalls = [r.overall_recall for r in results]
    f1s = [r.overall_f1 for r in results]

    precision_stats = _compute_stats(precisions, confidence)
    recall_stats = _compute_stats(recalls, confidence)
    f1_stats = _compute_stats(f1s, confidence)

    # Optional partial credit
    pcs_values = [
        r.overall_partial_credit_score
        for r in results
        if r.overall_partial_credit_score is not None
    ]
    pcs_stats = _compute_stats(pcs_values, confidence) if pcs_values else None

    # Optional distractor FPR
    fpr_values = [
        r.distractor_false_positive_rate
        for r in results
        if r.distractor_false_positive_rate is not None
    ]
    fpr_stats = _compute_stats(fpr_values, confidence) if fpr_values else None

    # Per-scope aggregation
    all_scopes: set[str] = set()
    for r in results:
        for sr in r.per_scope:
            all_scopes.add(sr.scope)

    per_scope: dict[str, dict[str, MetricStats]] = {}
    for scope in sorted(all_scopes):
        scope_metrics: dict[str, list[float]] = {
            "precision": [],
            "recall": [],
            "f1": [],
            "partial_credit_score": [],
        }
        for r in results:
            found = None
            for sr in r.per_scope:
                if sr.scope == scope:
                    found = sr
                    break
            scope_metrics["precision"].append(found.precision if found else 0.0)
            scope_metrics["recall"].append(found.recall if found else 0.0)
            scope_metrics["f1"].append(found.f1 if found else 0.0)
            scope_metrics["partial_credit_score"].append(
                found.partial_credit_score if found else 0.0
            )

        per_scope[scope] = {
            k: _compute_stats(v, confidence) for k, v in scope_metrics.items()
        }

    # Per-stage aggregation
    all_stages: set[str] = set()
    for r in results:
        for sr in r.per_stage:
            all_stages.add(sr.stage)

    per_stage: dict[str, dict[str, MetricStats]] = {}
    for stage in sorted(all_stages):
        stage_metrics: dict[str, list[float]] = {
            "precision": [],
            "recall": [],
            "f1": [],
        }
        for r in results:
            found = None
            for sr in r.per_stage:
                if sr.stage == stage:
                    found = sr
                    break
            stage_metrics["precision"].append(found.precision if found else 0.0)
            stage_metrics["recall"].append(found.recall if found else 0.0)
            stage_metrics["f1"].append(found.f1 if found else 0.0)

        per_stage[stage] = {
            k: _compute_stats(v, confidence) for k, v in stage_metrics.items()
        }

    agg = AggregatedResult(
        n_seeds=n,
        precision=precision_stats,
        recall=recall_stats,
        f1=f1_stats,
        partial_credit_score=pcs_stats,
        distractor_fpr=fpr_stats,
        per_scope=per_scope,
        per_stage=per_stage,
    )
    logger.info(
        f"Aggregation: {n} seeds, "
        f"P={agg.precision.mean:.4f}±{agg.precision.std:.4f} "
        f"R={agg.recall.mean:.4f}±{agg.recall.std:.4f} "
        f"F1={agg.f1.mean:.4f}±{agg.f1.std:.4f}"
    )
    return agg


def compare_modes(
    results_a: list[EvaluationResult],
    results_b: list[EvaluationResult],
) -> dict[str, float]:
    """Compute p-values for performance differences between two pipeline modes.

    Uses scipy.stats.ttest_ind (two-sample independent t-test) for each metric.
    Returns dict mapping metric name to p-value.
    """
    if not results_a or not results_b:
        return {}

    metrics: dict[str, tuple[list[float], list[float]]] = {
        "precision": (
            [r.overall_precision for r in results_a],
            [r.overall_precision for r in results_b],
        ),
        "recall": (
            [r.overall_recall for r in results_a],
            [r.overall_recall for r in results_b],
        ),
        "f1": (
            [r.overall_f1 for r in results_a],
            [r.overall_f1 for r in results_b],
        ),
    }

    # Add optional metrics if present in both
    pcs_a = [
        r.overall_partial_credit_score
        for r in results_a
        if r.overall_partial_credit_score is not None
    ]
    pcs_b = [
        r.overall_partial_credit_score
        for r in results_b
        if r.overall_partial_credit_score is not None
    ]
    if pcs_a and pcs_b:
        metrics["partial_credit_score"] = (pcs_a, pcs_b)

    fpr_a = [
        r.distractor_false_positive_rate
        for r in results_a
        if r.distractor_false_positive_rate is not None
    ]
    fpr_b = [
        r.distractor_false_positive_rate
        for r in results_b
        if r.distractor_false_positive_rate is not None
    ]
    if fpr_a and fpr_b:
        metrics["distractor_fpr"] = (fpr_a, fpr_b)

    p_values: dict[str, float] = {}
    for name, (vals_a, vals_b) in sorted(metrics.items()):
        if len(vals_a) < 2 or len(vals_b) < 2:
            continue
        _, p_value = scipy_stats.ttest_ind(vals_a, vals_b)
        p_values[name] = float(p_value)

    logger.info(
        f"Mode comparison: {len(p_values)} metrics tested, "
        f"p-values: {', '.join(f'{k}={v:.4f}' for k, v in p_values.items())}"
    )
    return p_values
