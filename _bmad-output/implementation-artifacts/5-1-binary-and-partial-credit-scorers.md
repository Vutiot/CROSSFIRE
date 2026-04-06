# Story 5.1: Binary & Partial Credit Scorers

Status: review

## Story

As a researcher,
I want to score pipeline results using both exact match and localization proximity,
so that I get both strict and lenient measures of detection accuracy.

## Acceptance Criteria

1. Given a `PipelineReport` and gold incoherence labels — when I run the binary scorer — then it computes exact match precision, recall, and F1 — a detected incoherence counts only if it matches a gold label on the same document pair and fact (FR23)
2. When I run the partial credit scorer — then it computes localization proximity scores — partial credit for detections that identify the right documents but wrong fact, or right fact area but imprecise localization (FR24)
3. Both scorers return `EvaluationResult` Pydantic models
4. Both scorers are fully deterministic — same inputs always produce identical scores (NFR2)
5. Both scorers correctly handle edge cases: empty pipeline report (all zeros), empty gold labels (perfect precision, zero recall), no overlap (all zeros)
6. pytest tests verify scoring against hand-crafted examples with known expected results

## Tasks / Subtasks

- [x] Task 1: Create `src/crossfire/evaluation/binary_scorer.py` (AC: #1, #3, #4, #5)
  - [x] `score_binary(report: PipelineReport, gold_labels: list[IncoherenceLabel]) -> EvaluationResult`
  - [x] Match detections to gold labels by comparing `evidence_references` (sorted set) to `document_references` (sorted set)
  - [x] Greedy one-to-one assignment: each gold label matched by at most one detection, each detection matched by at most one gold label
  - [x] Compute precision = matched / total_detections, recall = matched / total_gold_labels, F1 = harmonic mean
  - [x] Handle all edge cases per AC #5

- [x] Task 2: Create `src/crossfire/evaluation/partial_scorer.py` (AC: #2, #3, #4, #5)
  - [x] `score_partial(report: PipelineReport, gold_labels: list[IncoherenceLabel]) -> EvaluationResult`
  - [x] For each detection, compute proximity to each gold label: Jaccard similarity of `evidence_references` ∩ `document_references`
  - [x] Assign each detection to its best-matching gold label (greedy, highest similarity first, one-to-one)
  - [x] Partial credit precision = sum(assigned_similarities) / total_detections
  - [x] Partial credit recall = sum(assigned_similarities) / total_gold_labels
  - [x] Partial credit F1 = harmonic mean of partial precision and recall
  - [x] Handle all edge cases per AC #5

- [x] Task 3: Extend `EvaluationResult` schema (AC: #3)
  - [x] Add optional `overall_partial_credit_score: float | None = None` to `EvaluationResult`
  - [x] Keep backward compatible — existing tests must still pass

- [x] Task 4: Update `src/crossfire/evaluation/__init__.py` with exports
  - [x] Export `score_binary` and `score_partial`

- [x] Task 5: Write tests (AC: #5, #6)
  - [x] Create `tests/evaluation/__init__.py`
  - [x] Create `tests/evaluation/conftest.py` with shared fixtures (sample gold labels, sample pipeline reports)
  - [x] Create `tests/evaluation/test_binary_scorer.py` — hand-crafted examples with known expected P/R/F1
  - [x] Create `tests/evaluation/test_partial_scorer.py` — hand-crafted examples with known expected partial scores
  - [x] Test edge cases: empty report, empty gold, no overlap, perfect match, partial overlap
  - [x] Test determinism: same inputs → identical outputs across multiple calls

- [x] Task 6: Run full test suite — no regressions

## Dev Notes

### Architecture Compliance

**Evaluator Boundary (Pipeline -> Evaluator):**
The evaluator consumes `PipelineReport` JSON + gold annotation JSON files. It NEVER runs the pipeline — it only scores pre-existing results. The evaluator is the ONLY component that reads both pipeline output and gold annotations.
[Source: architecture.md#Pipeline -> Evaluator Boundary]

**AR11 Still Applies — But Differently:**
AR11 says "pipeline NEVER reads gold annotations." The evaluator is the exception — it MUST read gold annotations. But the evaluator NEVER runs pipeline strategies or generates corpus data.
[Source: architecture.md#Architectural Boundaries]

**NFR2 — Deterministic Evaluation:**
Both scorers must produce bit-identical results for identical inputs. No randomness, no SeedManager needed. Use sorted iteration over collections to ensure determinism regardless of dict/set insertion order.
[Source: prd.md#NFR2]

### Existing Schemas — DO NOT RECREATE

**EvaluationResult** in `src/crossfire/shared/schemas/evaluation.py`:
```python
class EvaluationResult(BaseModel):
    overall_precision: float
    overall_recall: float
    overall_f1: float
    per_scope: list[ScopeResult] = []
    per_stage: list[StageResult] = []
```

**PipelineReport** in `src/crossfire/shared/schemas/reports.py`:
```python
class DetectedIncoherence(BaseModel):
    id: str
    evidence_references: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    description: str

class PipelineReport(BaseModel):
    pipeline_mode: str
    corpus_path: str
    detections: list[DetectedIncoherence] = []
    timestamp: str
```

**IncoherenceLabel** in `src/crossfire/shared/schemas/incoherences.py`:
```python
class IncoherenceLabel(BaseModel):
    id: str
    scope: Scope  # "intra_doc" | "intra_corpus" | "inter_corpus"
    mechanism: Mechanism
    detectability: Detectability
    system_affinity: SystemAffinity
    document_references: list[str]
    modified_fact: str
    original_fact: str
```

Import all from `crossfire.shared.schemas.*` — do NOT create duplicate models.
[Source: src/crossfire/shared/schemas/evaluation.py, reports.py, incoherences.py]

### Schema Extension

The current `EvaluationResult` supports binary scoring (`overall_precision`, `overall_recall`, `overall_f1`) but has no top-level field for partial credit. Add:
```python
class EvaluationResult(BaseModel):
    overall_precision: float
    overall_recall: float
    overall_f1: float
    overall_partial_credit_score: float | None = None  # NEW — partial credit aggregate
    per_scope: list[ScopeResult] = []
    per_stage: list[StageResult] = []
```
The `None` default keeps backward compatibility. Binary scorer sets this to `None`; partial credit scorer populates it.
[Source: src/crossfire/shared/schemas/evaluation.py]

### Matching Semantics — Binary Scorer

**Document-pair matching:**
A detection matches a gold label when `sorted(detection.evidence_references) == sorted(gold_label.document_references)`.

**Greedy one-to-one assignment:**
1. For each detection, find all gold labels with matching document references
2. Assign matches greedily (first detection to first unmatched gold label)
3. Each gold label can be matched at most once
4. Each detection can be matched at most once
5. Unmatched detections are false positives; unmatched gold labels are false negatives

**Metrics:**
- `precision = matched_count / len(detections)` (0.0 if no detections)
- `recall = matched_count / len(gold_labels)` (0.0 if no gold labels)
- `f1 = 2 * precision * recall / (precision + recall)` (0.0 if both are 0)

### Matching Semantics — Partial Credit Scorer

**Proximity metric:**
For a detection `d` and gold label `g`:
```python
similarity = len(set(d.evidence_references) & set(g.document_references)) / len(set(d.evidence_references) | set(g.document_references))
```
This is Jaccard similarity on the document reference sets.

**Greedy assignment with partial credit:**
1. Compute similarity for all (detection, gold_label) pairs
2. Sort by similarity descending (break ties by sorted detection id, then gold label id for determinism)
3. Greedily assign: pick highest-similarity pair where neither detection nor gold label is already assigned
4. Continue until no more pairs with similarity > 0

**Metrics:**
- `partial_precision = sum(assigned_similarities) / len(detections)` (0.0 if no detections)
- `partial_recall = sum(assigned_similarities) / len(gold_labels)` (0.0 if no gold labels)
- `partial_f1 = harmonic mean` (0.0 if both are 0)
- `overall_partial_credit_score = mean(assigned_similarities)` (0.0 if no assignments)

### Edge Cases

| Scenario | Precision | Recall | F1 |
|----------|-----------|--------|----|
| Empty report, any gold | 0.0 | 0.0 | 0.0 |
| Any report, empty gold | 1.0 (no FP possible) | 0.0 | 0.0 |
| No overlap | 0.0 | 0.0 | 0.0 |
| Perfect match | 1.0 | 1.0 | 1.0 |

**Note on "empty gold" edge case:** AC says "perfect precision, zero recall". Rationale: with no gold labels, no detection can be a false positive (vacuous truth), so precision = 1.0. But there are no true positives to recall, so recall = 0.0.

### Error Handling

Both scorers are pure computation — no I/O, no LLM calls. They receive pre-loaded Pydantic models. Return-value error handling is not needed since inputs are already validated by Pydantic. If malformed data somehow reaches the scorer, let Pydantic validation errors propagate.
[Source: architecture.md#Error Handling]

### Logging

```python
from loguru import logger
logger.info(f"Binary scoring: {len(report.detections)} detections vs {len(gold_labels)} gold labels")
logger.info(f"Binary result: P={result.overall_precision:.4f} R={result.overall_recall:.4f} F1={result.overall_f1:.4f}")
```
loguru only. No `print()`.
[Source: architecture.md#Logging]

### Previous Epic Learnings (from Epic 4)

- Use `model_validate_json(text)` for loading from JSON files; `model_dump_json()` for serialization
- Use sorted iteration (`sorted(...)`) for deterministic processing
- Keep test fixtures minimal but sufficient — don't over-engineer
- 339 tests currently pass — must not break them
- Follow established import patterns: `from crossfire.shared.schemas.X import Y`

### Anti-Patterns to Avoid

- Do NOT use `print()` — use loguru
- Do NOT construct raw dicts for Pydantic models — use constructors
- Do NOT use `random`, `numpy.random`, or SeedManager — evaluation is pure computation
- Do NOT read corpus JSONL files — the evaluator works with pre-loaded PipelineReport and gold labels
- Do NOT use `sklearn.metrics` for basic P/R/F1 — implement directly for transparency and to avoid unnecessary dependency for simple math
- Do NOT modify existing schemas beyond the specified `overall_partial_credit_score` addition

### Project Structure Notes

Files to create:
```
src/crossfire/evaluation/
├── __init__.py             # UPDATE — add exports
├── binary_scorer.py        # NEW — exact match scoring (FR23)
└── partial_scorer.py       # NEW — localization proximity scoring (FR24)

src/crossfire/shared/schemas/
└── evaluation.py           # UPDATE — add overall_partial_credit_score field

tests/evaluation/
├── __init__.py             # NEW (replace .gitkeep)
├── conftest.py             # NEW — shared fixtures
├── test_binary_scorer.py   # NEW — binary scorer tests
└── test_partial_scorer.py  # NEW — partial scorer tests
```

Existing files (read-only reference):
- `src/crossfire/shared/schemas/evaluation.py` — EvaluationResult, ScopeResult, StageResult
- `src/crossfire/shared/schemas/reports.py` — PipelineReport, DetectedIncoherence
- `src/crossfire/shared/schemas/incoherences.py` — IncoherenceLabel, DistractorLabel
- `src/crossfire/shared/schemas/__init__.py` — re-exports all schemas

### Test Fixtures (conftest.py)

```python
@pytest.fixture
def sample_gold_labels():
    """3 gold incoherence labels for scoring tests."""
    return [
        IncoherenceLabel(id="gold_001", scope="intra_doc", mechanism="numeric_drift",
            detectability="single_hop", system_affinity="balanced",
            document_references=["doc_A", "doc_B"], modified_fact="speed was 120 mph",
            original_fact="speed was 150 mph"),
        IncoherenceLabel(id="gold_002", scope="intra_corpus", mechanism="entity_swap",
            detectability="multi_hop", system_affinity="graph_favoring",
            document_references=["doc_C", "doc_D"], modified_fact="Boeing 737",
            original_fact="Airbus A320"),
        IncoherenceLabel(id="gold_003", scope="inter_corpus", mechanism="temporal_contradiction",
            detectability="entity_resolution_dependent", system_affinity="agentic_favoring",
            document_references=["doc_E", "doc_F"], modified_fact="incident on March 5",
            original_fact="incident on March 12"),
    ]

@pytest.fixture
def perfect_report():
    """Pipeline report that perfectly matches all 3 gold labels."""
    ...

@pytest.fixture
def partial_report():
    """Pipeline report with 1 exact match, 1 partial overlap, 1 miss, 1 false positive."""
    ...

@pytest.fixture
def empty_report():
    """Pipeline report with no detections."""
    ...
```

### References

- [Source: architecture.md#Pipeline -> Evaluator Boundary]
- [Source: architecture.md#Architectural Boundaries]
- [Source: architecture.md#Error Handling]
- [Source: architecture.md#Logging]
- [Source: epics.md#Story 5.1: Binary & Partial Credit Scorers]
- [Source: epics.md#Epic 5: Evaluation & Diagnostics]
- [Source: prd.md#FR23, FR24, NFR2]
- [Source: src/crossfire/shared/schemas/evaluation.py]
- [Source: src/crossfire/shared/schemas/reports.py]
- [Source: src/crossfire/shared/schemas/incoherences.py]
- [Source: _bmad-output/implementation-artifacts/deferred-work.md]
- [Source: _bmad-output/implementation-artifacts/4-1-strategy-interfaces-and-pipeline-skeleton.md]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- Task 3: Extended `EvaluationResult` schema with `overall_partial_credit_score: float | None = None`. Backward compatible — all 339 existing tests still pass.
- Task 1: Created `binary_scorer.py` — `score_binary()` matches detections to gold labels by sorted document reference equality. Greedy one-to-one assignment via lookup map. Handles all edge cases (empty report, empty gold, no overlap).
- Task 2: Created `partial_scorer.py` — `score_partial()` uses Jaccard similarity on document reference sets. Greedy assignment by descending similarity with deterministic tie-breaking (detection id, gold id). Returns partial P/R/F1 plus aggregate PCS.
- Task 4: Updated `evaluation/__init__.py` with `score_binary` and `score_partial` exports.
- Task 5: 23 tests across 14 test classes covering: perfect match, no overlap, partial match, edge cases (empty report/gold/both), document ref ordering, one-to-one assignment, and determinism — for both scorers.
- Task 6: 362 tests pass (339 existing + 23 new). Zero regressions.

### File List

- src/crossfire/shared/schemas/evaluation.py (modified — added overall_partial_credit_score field)
- src/crossfire/evaluation/__init__.py (modified — added exports)
- src/crossfire/evaluation/binary_scorer.py (new)
- src/crossfire/evaluation/partial_scorer.py (new)
- tests/evaluation/__init__.py (new)
- tests/evaluation/conftest.py (new)
- tests/evaluation/test_binary_scorer.py (new)
- tests/evaluation/test_partial_scorer.py (new)

### Change Log

- 2026-04-06: Story 5.1 implemented — binary and partial credit scorers with 23 tests
