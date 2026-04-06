# Story 5.3: Per-Stage Breakdown

Status: review

## Story

As a researcher,
I want evaluation results broken down by pipeline stage,
so that I can pinpoint whether failures occur in entity resolution, graph construction, or scanning.

## Acceptance Criteria

1. Given a `PipelineReport` with stage-level metadata and gold labels — when I run stage breakdown evaluation — then it computes separate scores for entity resolution, graph construction, and scanning stages independently (FR26)
2. Stage scores do NOT cascade — a failure in entity resolution does not automatically penalize graph construction or scanning scores
3. Each stage is evaluated against its own relevant subset of gold labels
4. Results are returned as `StageResult` models nested within `EvaluationResult`
5. If graph-native mode is dropped (FR19 contingency), graph construction stage evaluation gracefully returns N/A rather than failing

## Tasks / Subtasks

- [x] Task 1: Create `src/crossfire/evaluation/stage_breakdown.py` (AC: #1, #2, #3, #4, #5)
  - [x] `score_by_stage(report: PipelineReport, gold_labels: list[IncoherenceLabel]) -> EvaluationResult`
  - [x] Map gold label `detectability` to pipeline stage: `single_hop` -> `scanning`, `multi_hop` -> `graph_construction`, `entity_resolution_dependent` -> `entity_resolution`
  - [x] Group gold labels by mapped stage
  - [x] For each stage: run `score_binary` on (full report, stage-filtered gold) to get P/R/F1
  - [x] Build `StageResult` per stage
  - [x] Populate `EvaluationResult.per_stage` with all stage results
  - [x] Also compute overall metrics across all gold labels
  - [x] Handle edge case: stage with no gold labels is omitted from results (not zero-filled)

- [x] Task 2: Update `src/crossfire/evaluation/__init__.py` with exports
  - [x] Add `score_by_stage` export

- [x] Task 3: Write tests in `tests/evaluation/test_stage_breakdown.py` (AC: #1-#5)
  - [x] Test: perfect match produces per-stage P/R/F1 for each stage
  - [x] Test: non-cascading — missing all entity_resolution detections doesn't affect scanning scores
  - [x] Test: detectability-to-stage mapping is correct
  - [x] Test: empty report produces all-zero stage results
  - [x] Test: gold labels in only one stage produce results for that stage only
  - [x] Test: FR19 contingency — no graph_construction gold labels means no graph_construction StageResult
  - [x] Test: determinism across calls

- [x] Task 4: Run full test suite — no regressions

## Dev Notes

### Architecture Compliance

**Evaluator Boundary:** Same as Stories 5.1/5.2 — evaluator consumes `PipelineReport` + gold labels.
[Source: architecture.md#Pipeline -> Evaluator Boundary]

**NFR2 — Deterministic Evaluation:** Stage breakdown must be deterministic. Use sorted iteration over stage names.
[Source: prd.md#NFR2]

### Existing Code — REUSE, DO NOT DUPLICATE

**Story 5.1 binary scorer** is the foundation. Stage breakdown delegates to it:
- `score_binary(report, stage_gold)` — returns `EvaluationResult` with P/R/F1

Import from `crossfire.evaluation.binary_scorer`.

**Story 5.2 pattern** — scope breakdown uses the same filter-and-delegate approach. Stage breakdown follows the identical pattern but groups by detectability-to-stage mapping instead of scope.

```python
from crossfire.evaluation.binary_scorer import score_binary

DETECTABILITY_TO_STAGE = {
    "single_hop": "scanning",
    "multi_hop": "graph_construction",
    "entity_resolution_dependent": "entity_resolution",
}
```

### Detectability-to-Stage Mapping (AC #1, #3)

Gold labels don't have a `stage` field. The `detectability` field serves as a proxy for which pipeline stage is primarily responsible for detecting each incoherence:

| Detectability | Pipeline Stage | Rationale |
|---------------|---------------|-----------|
| `single_hop` | `scanning` | Directly detectable by scanning documents — no graph traversal needed |
| `multi_hop` | `graph_construction` | Requires multi-hop graph traversal to detect — tests graph quality |
| `entity_resolution_dependent` | `entity_resolution` | Requires correct entity resolution before detection is possible |

This mapping ensures non-cascading evaluation (AC #2): each stage evaluates a disjoint subset of gold labels.

### Non-Cascading Semantics (AC #2)

Each stage is evaluated against its own subset of gold labels, using ALL detections. A detection matching a `single_hop` gold label contributes to `scanning` stage score but has no effect on `entity_resolution` or `graph_construction` scores. Pipeline failures in one stage cannot penalize another stage's evaluation.

### FR19 Contingency (AC #5)

If graph-native mode is dropped, there may be no `multi_hop` gold labels in the dataset (or they may be present but hard to detect). The function handles this naturally:
- If no gold labels map to `graph_construction`, that stage is omitted from `per_stage` results
- No error, no N/A sentinel — the stage simply isn't present in the results
- Callers can check `if any(sr.stage == "graph_construction" for sr in result.per_stage)` to determine availability

### Existing Schemas — DO NOT MODIFY

**StageResult** in `src/crossfire/shared/schemas/evaluation.py`:
```python
class StageResult(BaseModel):
    stage: str
    precision: float
    recall: float
    f1: float
```

Note: `StageResult` has NO `partial_credit_score` field (unlike `ScopeResult`). Per-stage evaluation is binary-only.

**EvaluationResult** already has `per_stage: list[StageResult] = []` — no schema changes needed.

**IncoherenceLabel.detectability** is `Literal["single_hop", "multi_hop", "entity_resolution_dependent"]`.

[Source: src/crossfire/shared/schemas/evaluation.py, incoherences.py]

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| Empty report | All stages get P=0.0, R=0.0, F1=0.0 |
| Empty gold labels | No stage results (empty `per_stage` list) |
| Stage with no gold labels | That stage omitted from results |
| All gold in one stage | Only that stage in results; overall metrics reflect all gold |

### Error Handling

Pure computation — no I/O, no LLM calls. Let Pydantic validation propagate.
[Source: architecture.md#Error Handling]

### Logging

```python
from loguru import logger
logger.info(f"Stage breakdown: {len(stages)} stages found in {len(gold_labels)} gold labels")
logger.info(f"Stage '{stage}': P={sr.precision:.4f} R={sr.recall:.4f} F1={sr.f1:.4f}")
```
loguru only. No `print()`.
[Source: architecture.md#Logging]

### Previous Story Learnings (from Stories 5.1, 5.2)

- Scope breakdown delegated to `score_binary` and `score_partial` per scope — same pattern here with `score_binary` only (StageResult has no partial credit)
- Test fixtures in `tests/evaluation/conftest.py` have `sample_gold_labels` with detectabilities: `single_hop`, `multi_hop`, `entity_resolution_dependent` — one per stage, perfect for stage breakdown tests
- 373 tests currently pass — must not break them

### Anti-Patterns to Avoid

- Do NOT reimplement binary scoring logic — delegate to `score_binary`
- Do NOT add partial credit to stage breakdown — `StageResult` has no `partial_credit_score` field
- Do NOT use `print()` — use loguru
- Do NOT modify existing schemas
- Do NOT hardcode stage names beyond the mapping constant — discover from gold labels

### Project Structure Notes

Files to create:
```
src/crossfire/evaluation/
├── __init__.py             # UPDATE — add score_by_stage export
└── stage_breakdown.py      # NEW — per-stage evaluation (FR26)

tests/evaluation/
└── test_stage_breakdown.py # NEW — stage breakdown tests
```

Existing files (read-only reference):
- `src/crossfire/evaluation/binary_scorer.py` — score_binary (reuse)
- `src/crossfire/evaluation/scope_breakdown.py` — pattern reference
- `src/crossfire/shared/schemas/evaluation.py` — StageResult, EvaluationResult
- `src/crossfire/shared/schemas/incoherences.py` — IncoherenceLabel with detectability field
- `tests/evaluation/conftest.py` — sample_gold_labels (1 per detectability), perfect_report, empty_report

### References

- [Source: architecture.md#Pipeline -> Evaluator Boundary]
- [Source: architecture.md#Logging]
- [Source: epics.md#Story 5.3: Per-Stage Breakdown]
- [Source: epics.md#Epic 5: Evaluation & Diagnostics]
- [Source: prd.md#FR26, FR19, NFR2]
- [Source: src/crossfire/shared/schemas/evaluation.py]
- [Source: src/crossfire/shared/schemas/incoherences.py]
- [Source: src/crossfire/evaluation/binary_scorer.py]
- [Source: src/crossfire/evaluation/scope_breakdown.py]
- [Source: _bmad-output/implementation-artifacts/5-1-binary-and-partial-credit-scorers.md]
- [Source: _bmad-output/implementation-artifacts/5-2-per-scope-breakdown.md]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- Task 1: Created `stage_breakdown.py` — `score_by_stage()` maps `detectability` to pipeline stages via `DETECTABILITY_TO_STAGE` constant. Delegates to `score_binary` per stage. Stages discovered from gold labels (not hardcoded). Sorted alphabetically for determinism.
- Task 2: Updated `evaluation/__init__.py` with `score_by_stage` export.
- Task 3: 10 tests across 6 test classes covering: perfect match per-stage, overall metrics, stage name sorting, detectability mapping, non-cascading independence, edge cases (empty report/gold/single stage), FR19 contingency (no graph_construction stage), and determinism.
- Task 4: 383 tests pass (373 existing + 10 new). Zero regressions.

### File List

- src/crossfire/evaluation/__init__.py (modified — added score_by_stage export)
- src/crossfire/evaluation/stage_breakdown.py (new)
- tests/evaluation/test_stage_breakdown.py (new)

### Change Log

- 2026-04-06: Story 5.3 implemented — per-stage evaluation breakdown with 10 tests
