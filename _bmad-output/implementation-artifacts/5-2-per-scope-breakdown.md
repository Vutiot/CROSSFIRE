# Story 5.2: Per-Scope Breakdown

Status: review

## Story

As a researcher,
I want evaluation results broken down by incoherence scope,
so that I can see where my system succeeds or fails across document boundaries.

## Acceptance Criteria

1. Given a `PipelineReport` and gold incoherence labels with scope metadata — when I run scope breakdown evaluation — then it computes separate scores for intra-document, intra-subcorpus, and inter-subcorpus incoherences independently (FR25)
2. Each scope produces its own precision, recall, F1 (binary) and proximity score (partial credit)
3. Results are returned as `ScopeResult` models nested within `EvaluationResult`
4. A detection is assigned to the scope of its matching gold label — not the scope the pipeline claims
5. Scope breakdown is independent — poor performance in one scope does not affect scores in another

## Tasks / Subtasks

- [x] Task 1: Create `src/crossfire/evaluation/scope_breakdown.py` (AC: #1, #2, #3, #4, #5)
  - [x] `score_by_scope(report: PipelineReport, gold_labels: list[IncoherenceLabel]) -> EvaluationResult`
  - [x] Group gold labels by `scope` field (intra_doc, intra_corpus, inter_corpus)
  - [x] For each scope: run `score_binary` on (full report, scope-filtered gold) to get binary P/R/F1
  - [x] For each scope: run `score_partial` on (full report, scope-filtered gold) to get partial credit score
  - [x] Build `ScopeResult` per scope with binary P/R/F1 and partial credit score
  - [x] Populate `EvaluationResult.per_scope` with all scope results
  - [x] Also compute overall metrics across all gold labels (reuse `score_binary` and `score_partial`)
  - [x] Handle edge cases: scope with no gold labels produces zeros, empty report produces all zeros

- [x] Task 2: Update `src/crossfire/evaluation/__init__.py` with exports
  - [x] Add `score_by_scope` export

- [x] Task 3: Write tests in `tests/evaluation/test_scope_breakdown.py` (AC: #1-#5)
  - [x] Test: perfect match produces per-scope P/R/F1 of 1.0 for each scope
  - [x] Test: detection assigned to gold label's scope (not claimed)
  - [x] Test: scope independence — missing all detections in one scope doesn't affect other scopes
  - [x] Test: empty report produces all-zero scope results
  - [x] Test: scope with no gold labels produces zero scores for that scope
  - [x] Test: determinism across calls

- [x] Task 4: Run full test suite — no regressions

## Dev Notes

### Architecture Compliance

**Evaluator Boundary:** Same as Story 5.1 — evaluator consumes `PipelineReport` + gold labels, never runs the pipeline.
[Source: architecture.md#Pipeline -> Evaluator Boundary]

**NFR2 — Deterministic Evaluation:** Scope breakdown must be deterministic. Use sorted iteration over scope names and sorted gold labels within each scope.
[Source: prd.md#NFR2]

### Existing Code — REUSE, DO NOT DUPLICATE

**Story 5.1 scorers** are the foundation. Scope breakdown delegates to them:
- `score_binary(report, scope_gold)` — returns `EvaluationResult` with P/R/F1
- `score_partial(report, scope_gold)` — returns `EvaluationResult` with P/R/F1 + partial credit

Import from `crossfire.evaluation.binary_scorer` and `crossfire.evaluation.partial_scorer`.

**Key pattern:** For each scope, filter gold labels to that scope and call the existing scorers. This ensures scope independence and avoids reimplementing matching logic.

```python
from crossfire.evaluation.binary_scorer import score_binary
from crossfire.evaluation.partial_scorer import score_partial

for scope in sorted(scopes):
    scope_gold = [g for g in gold_labels if g.scope == scope]
    binary_result = score_binary(report, scope_gold)
    partial_result = score_partial(report, scope_gold)
    scope_results.append(ScopeResult(
        scope=scope,
        precision=binary_result.overall_precision,
        recall=binary_result.overall_recall,
        f1=binary_result.overall_f1,
        partial_credit_score=partial_result.overall_partial_credit_score or 0.0,
    ))
```

### Existing Schemas — DO NOT MODIFY

**ScopeResult** in `src/crossfire/shared/schemas/evaluation.py`:
```python
class ScopeResult(BaseModel):
    scope: str
    precision: float
    recall: float
    f1: float
    partial_credit_score: float
```

**EvaluationResult** already has `per_scope: list[ScopeResult] = []` — no schema changes needed.

**IncoherenceLabel.scope** is `Literal["intra_doc", "intra_corpus", "inter_corpus"]` — these are the 3 scope values.

[Source: src/crossfire/shared/schemas/evaluation.py, incoherences.py]

### Scope Assignment Semantics (AC #4)

A detection is assigned to the scope of its **matching gold label**, not a scope the pipeline might claim. Since `DetectedIncoherence` has no `scope` field, all scope information comes from the gold label. The per-scope filtering of gold labels naturally handles this — if a detection matches a gold label in `intra_doc`, it counts as a TP for `intra_doc`.

### Independence Semantics (AC #5)

Each scope is scored as a completely independent evaluation against ALL detections but only that scope's gold labels. This means:
- A detection matching an `intra_doc` gold label contributes to `intra_doc` TP
- The same detection is simply a non-match for `inter_corpus` evaluation (it doesn't match any `inter_corpus` gold label)
- No cross-scope contamination

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| Empty report | All scopes get P=0.0, R=0.0, F1=0.0, PCS=0.0 |
| Empty gold labels | No scope results (empty `per_scope` list) |
| Scope with no gold labels | That scope not included in results (only scopes present in gold appear) |
| All gold in one scope | Only that scope has results; overall metrics reflect all gold |

### Error Handling

Pure computation — no I/O, no LLM calls. Let Pydantic validation propagate.
[Source: architecture.md#Error Handling]

### Logging

```python
from loguru import logger
logger.info(f"Scope breakdown: {len(scopes)} scopes found in {len(gold_labels)} gold labels")
logger.info(f"Scope '{scope}': P={sr.precision:.4f} R={sr.recall:.4f} F1={sr.f1:.4f} PCS={sr.partial_credit_score:.4f}")
```
loguru only. No `print()`.
[Source: architecture.md#Logging]

### Previous Story Learnings (from Story 5.1)

- Binary scorer uses sorted document reference comparison with greedy one-to-one matching
- Partial scorer uses Jaccard similarity with greedy highest-similarity-first assignment
- Both handle edge cases (empty report → zeros, empty gold → precision 1.0)
- Test fixtures in `tests/evaluation/conftest.py` have `sample_gold_labels` with one label per scope (intra_doc, intra_corpus, inter_corpus) — perfect for scope breakdown tests
- `_make_report()` helper available in conftest
- 362 tests currently pass — must not break them

### Anti-Patterns to Avoid

- Do NOT reimplement binary/partial scoring logic — delegate to `score_binary` and `score_partial`
- Do NOT use `print()` — use loguru
- Do NOT construct raw dicts for Pydantic models — use constructors
- Do NOT use `random` — evaluation is pure computation
- Do NOT modify existing schemas — `ScopeResult` and `EvaluationResult` already have all needed fields
- Do NOT hardcode scope values — discover them from gold labels

### Project Structure Notes

Files to create:
```
src/crossfire/evaluation/
├── __init__.py             # UPDATE — add score_by_scope export
└── scope_breakdown.py      # NEW — per-scope evaluation (FR25)

tests/evaluation/
└── test_scope_breakdown.py # NEW — scope breakdown tests
```

Existing files (read-only reference):
- `src/crossfire/evaluation/binary_scorer.py` — score_binary (reuse)
- `src/crossfire/evaluation/partial_scorer.py` — score_partial (reuse)
- `src/crossfire/shared/schemas/evaluation.py` — ScopeResult, EvaluationResult
- `src/crossfire/shared/schemas/incoherences.py` — IncoherenceLabel with scope field
- `tests/evaluation/conftest.py` — sample_gold_labels (1 per scope), perfect_report, partial_report, empty_report

### References

- [Source: architecture.md#Pipeline -> Evaluator Boundary]
- [Source: architecture.md#Logging]
- [Source: epics.md#Story 5.2: Per-Scope Breakdown]
- [Source: epics.md#Epic 5: Evaluation & Diagnostics]
- [Source: prd.md#FR25, NFR2]
- [Source: src/crossfire/shared/schemas/evaluation.py]
- [Source: src/crossfire/shared/schemas/incoherences.py]
- [Source: src/crossfire/evaluation/binary_scorer.py]
- [Source: src/crossfire/evaluation/partial_scorer.py]
- [Source: _bmad-output/implementation-artifacts/5-1-binary-and-partial-credit-scorers.md]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- Task 1: Created `scope_breakdown.py` — `score_by_scope()` discovers scopes from gold labels, delegates to `score_binary` and `score_partial` per scope. Overall metrics computed from full gold set. Scopes sorted alphabetically for determinism.
- Task 2: Updated `evaluation/__init__.py` with `score_by_scope` export.
- Task 3: 11 tests across 6 test classes covering: perfect match per-scope, overall metrics, scope name ordering, scope independence, scope assignment from gold labels, edge cases (empty report/gold/single scope), partial credit per scope, and determinism.
- Task 4: 373 tests pass (362 existing + 11 new). Zero regressions.

### File List

- src/crossfire/evaluation/__init__.py (modified — added score_by_scope export)
- src/crossfire/evaluation/scope_breakdown.py (new)
- tests/evaluation/test_scope_breakdown.py (new)

### Change Log

- 2026-04-06: Story 5.2 implemented — per-scope evaluation breakdown with 11 tests
