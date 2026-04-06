# Story 5.5: Distractor Evaluation & Multi-Seed Aggregation

Status: review

## Story

As a researcher,
I want to measure false positive rates on distractors and aggregate results across seeds,
so that I know whether my system flags legitimate divergences and my results are statistically significant.

## Acceptance Criteria

1. Given a `PipelineReport` and gold distractor labels — when I run distractor evaluation — then it computes false positive rate: what fraction of distractors the pipeline incorrectly flags as incoherences (FR28)
2. Distractor false positive rate is reported separately from incoherence detection accuracy
3. Given evaluation results from multiple runs with different seeds — when I run multi-seed aggregation — then it computes mean, standard deviation, and confidence intervals across seeds for all metrics (FR29)
4. It computes statistical significance (p-values) for performance differences between pipeline modes
5. Aggregated results include per-scope and per-stage breakdowns with significance measures
6. All aggregation uses scipy for statistical tests

## Tasks / Subtasks

- [x] Task 1: Add schema extensions to `evaluation.py` (AC: #2, #3)
  - [x] Add `distractor_false_positive_rate: float | None = None` to `EvaluationResult`
  - [x] Define `MetricStats(mean: float, std: float, ci_lower: float, ci_upper: float)` model
  - [x] Define `AggregatedResult` model with aggregated overall metrics, per-scope, per-stage, and optional p-values
  - [x] Export new models from `schemas/__init__.py`
  - [x] Keep backward compatible — existing tests must still pass

- [x] Task 2: Create `src/crossfire/evaluation/distractor_eval.py` (AC: #1, #2)
  - [x] `score_distractors(report: PipelineReport, distractor_labels: list[DistractorLabel]) -> EvaluationResult`
  - [x] Match detections to distractors by comparing `evidence_references` to `document_references` (sorted sets)
  - [x] FP rate = flagged_distractors / total_distractors (0.0 if no distractors)
  - [x] Return `EvaluationResult` with `distractor_false_positive_rate` populated
  - [x] Handle edge cases: empty report (FP rate = 0.0), empty distractors (FP rate = 0.0)

- [x] Task 3: Create `src/crossfire/evaluation/aggregate.py` (AC: #3, #4, #5, #6)
  - [x] `aggregate_seeds(results: list[EvaluationResult], confidence: float = 0.95) -> AggregatedResult`
  - [x] Compute mean, std, CI for: overall_precision, overall_recall, overall_f1, overall_partial_credit_score, distractor_false_positive_rate
  - [x] Compute per-scope aggregation: for each scope present, aggregate P/R/F1/PCS across seeds
  - [x] Compute per-stage aggregation: for each stage present, aggregate P/R/F1 across seeds
  - [x] Use `scipy.stats.t.interval` for confidence intervals
  - [x] `compare_modes(results_a: list[EvaluationResult], results_b: list[EvaluationResult]) -> dict[str, float]`
  - [x] Use `scipy.stats.ttest_ind` for p-values between two pipeline modes on each metric
  - [x] Handle edge cases: single result (std=0, no CI), empty results

- [x] Task 4: Update `src/crossfire/evaluation/__init__.py` with exports
  - [x] Add `score_distractors`, `aggregate_seeds`, `compare_modes` exports

- [x] Task 5: Write tests (AC: #1-#6)
  - [x] Create `tests/evaluation/test_distractor_eval.py`
    - [x] Test: all distractors flagged → FP rate = 1.0
    - [x] Test: no distractors flagged → FP rate = 0.0
    - [x] Test: partial flagging → correct FP rate
    - [x] Test: empty report → FP rate = 0.0
    - [x] Test: empty distractors → FP rate = 0.0
    - [x] Test: determinism
  - [x] Create `tests/evaluation/test_aggregate.py`
    - [x] Test: aggregate 3 identical results → std=0, mean=value
    - [x] Test: aggregate varied results → correct mean/std/CI
    - [x] Test: compare_modes returns p-values for each metric
    - [x] Test: per-scope and per-stage aggregation
    - [x] Test: single result → mean=value, std=0
    - [x] Test: determinism

- [x] Task 6: Run full test suite — no regressions

## Dev Notes

### Architecture Compliance

**Evaluator Boundary:** Same as previous stories — evaluator consumes PipelineReport + gold labels.
[Source: architecture.md#Pipeline -> Evaluator Boundary]

**NFR2 — Deterministic Evaluation:** Distractor scoring is deterministic. Aggregation uses deterministic scipy functions.
[Source: prd.md#NFR2]

### Existing Code — REUSE

**Binary scorer matching logic** is the pattern for distractor matching. Match detections to distractors by `evidence_references` == `document_references` (sorted sets). Reuse the same approach — do NOT import score_binary (it counts matches for P/R/F1, we just need FP rate).

### Existing Schemas — Key References

**DistractorLabel** in `src/crossfire/shared/schemas/incoherences.py`:
```python
class DistractorLabel(BaseModel):
    id: str
    scope: Scope
    document_references: list[str]
    divergence_type: str
    description: str
```

**EvaluationResult** in `src/crossfire/shared/schemas/evaluation.py` — current fields:
```python
class EvaluationResult(BaseModel):
    overall_precision: float
    overall_recall: float
    overall_f1: float
    overall_partial_credit_score: float | None = None
    per_scope: list[ScopeResult] = []
    per_stage: list[StageResult] = []
    representation_quality: RepresentationQualityResult | None = None
```

### Schema Extensions

**Add to `EvaluationResult`:**
```python
class EvaluationResult(BaseModel):
    ...
    distractor_false_positive_rate: float | None = None  # NEW
```

**New models:**
```python
class MetricStats(BaseModel):
    mean: float
    std: float
    ci_lower: float
    ci_upper: float

class AggregatedResult(BaseModel):
    n_seeds: int
    precision: MetricStats
    recall: MetricStats
    f1: MetricStats
    partial_credit_score: MetricStats | None = None
    distractor_fpr: MetricStats | None = None
    per_scope: dict[str, dict[str, MetricStats]] = {}  # scope -> metric_name -> stats
    per_stage: dict[str, dict[str, MetricStats]] = {}  # stage -> metric_name -> stats
    mode_comparison: dict[str, float] | None = None  # metric_name -> p_value
```

### Distractor Matching Semantics

A detection "flags" a distractor when `sorted(detection.evidence_references) == sorted(distractor.document_references)`. This uses the same exact-match logic as the binary scorer.

```
FP_rate = |distractors matched by ≥1 detection| / |total distractors|
```
- 0.0 if no distractors (nothing to flag)
- 0.0 if no detections (nothing flagged)
- Reported separately from incoherence detection (AC #2)

### Multi-Seed Aggregation Semantics

**Per-metric aggregation:**
For each numeric metric across N seeds:
- `mean = numpy.mean(values)`
- `std = numpy.std(values, ddof=1)` (sample std)
- CI via `scipy.stats.t.interval(confidence, df=N-1, loc=mean, scale=std/sqrt(N))`

**Per-scope/per-stage aggregation:**
For each scope/stage present in ANY seed result, collect the metric values across seeds (use 0.0 for seeds where scope/stage is absent).

**Mode comparison (AC #4):**
`scipy.stats.ttest_ind(values_a, values_b)` for each metric. Returns dict of metric_name -> p_value.

### Edge Cases

| Scenario | Distractor FP Rate |
|----------|--------------------|
| Empty report, any distractors | 0.0 |
| Any report, no distractors | 0.0 |
| All distractors flagged | 1.0 |
| No distractors flagged | 0.0 |

| Aggregation Scenario | Behavior |
|----------------------|----------|
| Single seed | mean=value, std=0.0, CI=value±0 |
| Empty results list | All zeros |

### Error Handling

Pure computation. Scipy functions may warn on degenerate cases (e.g., zero variance) — let warnings propagate, don't suppress.
[Source: architecture.md#Error Handling]

### Logging

```python
from loguru import logger
logger.info(f"Distractor eval: {flagged}/{total} distractors flagged (FP rate={rate:.4f})")
logger.info(f"Aggregation: {n} seeds, P={stats.precision.mean:.4f}±{stats.precision.std:.4f}")
```
loguru only. No `print()`.

### Previous Story Learnings (from Stories 5.1-5.4)

- Keep functions pure — take Pydantic models, return Pydantic models
- Use sorted iteration for determinism
- Hand-crafted test examples with known expected values
- 402 tests currently pass — must not break them
- Schema extensions with `None` defaults are backward compatible

### Anti-Patterns to Avoid

- Do NOT use `print()` — use loguru
- Do NOT use `random` — deterministic computation
- Do NOT modify existing schema fields — only add new optional fields
- Do NOT implement custom statistical tests — use scipy
- Do NOT import numpy directly for mean/std — use scipy/statistics or compute inline (avoid adding numpy as a new import dependency in evaluation module unless already imported)

### Project Structure Notes

Files to create/modify:
```
src/crossfire/shared/schemas/
├── evaluation.py           # UPDATE — add distractor_false_positive_rate, MetricStats, AggregatedResult
└── __init__.py             # UPDATE — export MetricStats, AggregatedResult

src/crossfire/evaluation/
├── __init__.py             # UPDATE — add score_distractors, aggregate_seeds, compare_modes
├── distractor_eval.py      # NEW — distractor false positive evaluation (FR28)
└── aggregate.py            # NEW — multi-seed aggregation + significance (FR29)

tests/evaluation/
├── test_distractor_eval.py # NEW — distractor evaluation tests
└── test_aggregate.py       # NEW — aggregation tests
```

Existing files (read-only reference):
- `src/crossfire/shared/schemas/incoherences.py` — DistractorLabel
- `src/crossfire/shared/schemas/evaluation.py` — EvaluationResult, ScopeResult, StageResult
- `src/crossfire/evaluation/binary_scorer.py` — matching pattern reference

### References

- [Source: architecture.md#Pipeline -> Evaluator Boundary]
- [Source: architecture.md#Logging]
- [Source: epics.md#Story 5.5: Distractor Evaluation & Multi-Seed Aggregation]
- [Source: epics.md#Epic 5: Evaluation & Diagnostics]
- [Source: prd.md#FR28, FR29, NFR2]
- [Source: src/crossfire/shared/schemas/evaluation.py]
- [Source: src/crossfire/shared/schemas/incoherences.py]
- [Source: src/crossfire/evaluation/binary_scorer.py — matching pattern]
- [Source: _bmad-output/implementation-artifacts/5-1-binary-and-partial-credit-scorers.md]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- Task 1: Extended `EvaluationResult` with `distractor_false_positive_rate: float | None = None`. Added `MetricStats` (mean, std, ci_lower, ci_upper) and `AggregatedResult` (n_seeds, per-metric stats, per-scope/stage dicts, mode_comparison) models. Exported from `schemas/__init__.py`. Backward compatible — all 402 existing tests still pass.
- Task 2: Created `distractor_eval.py` — `score_distractors()` builds detection reference index, checks which distractors match any detection by sorted document references. FP rate = flagged / total. Reported separately from P/R/F1.
- Task 3: Created `aggregate.py` — `aggregate_seeds()` computes mean/std/CI via `statistics.mean`, `statistics.stdev`, and `scipy.stats.t.interval` for all metrics including per-scope and per-stage breakdowns. `compare_modes()` uses `scipy.stats.ttest_ind` for p-values between two pipeline modes. Handles edge cases (single seed, empty results, zero variance).
- Task 4: Updated `evaluation/__init__.py` with `score_distractors`, `aggregate_seeds`, `compare_modes` exports.
- Task 5: 25 tests — 9 distractor tests (all flagged, none flagged, partial, edge cases, determinism) + 16 aggregate tests (identical/varied/single/empty results, CI bounds, optional metrics, per-scope/stage, mode comparison significance, determinism).
- Task 6: 427 tests pass (402 existing + 25 new). Zero regressions.

### File List

- src/crossfire/shared/schemas/evaluation.py (modified — added distractor_false_positive_rate, MetricStats, AggregatedResult)
- src/crossfire/shared/schemas/__init__.py (modified — added MetricStats, AggregatedResult exports)
- src/crossfire/evaluation/__init__.py (modified — added score_distractors, aggregate_seeds, compare_modes exports)
- src/crossfire/evaluation/distractor_eval.py (new)
- src/crossfire/evaluation/aggregate.py (new)
- tests/evaluation/test_distractor_eval.py (new)
- tests/evaluation/test_aggregate.py (new)

### Change Log

- 2026-04-06: Story 5.5 implemented — distractor evaluation and multi-seed aggregation with 25 tests
