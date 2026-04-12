# Story 3.3-NEW: Distractor Generation

Status: review

## Story

As a researcher,
I want legitimate perspective divergences injected alongside real contradictions,
So that I can measure false positive rates and ensure systems distinguish genuine incoherences from natural disagreement.

## Context

This is the THIRD story in Epic 3-NEW. Stories 3.1 and 3.2 implemented contradiction injection with all code review fixes. This story rewrites `distractor_generator.py` to fix the critical content truncation bug (P5) and align with the same patterns.

**Code review finding to fix:**
- P5 (High): Distractor generator replaces entire `doc.content` with LLM output truncated to 2000 chars — silently destroys documents longer than 2000 chars

## Acceptance Criteria

1. **(AC1) Configurable Distractor Ratio**
   **Given** injection parameters specifying a distractor ratio
   **When** the pipeline generates distractors
   **Then** distractors are produced at the configured ratio relative to real contradictions (FR11)

2. **(AC2) Four Divergence Types**
   **Given** a generated distractor
   **When** I inspect its label
   **Then** it is tagged with: `expert_opinion`, `preliminary_vs_final`, `measurement_methodology`, or `uncertainty_expression`

3. **(AC3) Legitimate Divergences**
   **Given** a distractor
   **When** I review the content
   **Then** it represents a legitimate perspective divergence that should NOT be flagged as an incoherence

4. **(AC4) JSONL Output**
   **Given** distractors for a case
   **When** written to disk
   **Then** stored in `distractors/distractor_labels.jsonl` in the case directory, each line validating against `DistractorLabel` schema

5. **(AC5) No Content Truncation**
   **Given** a document with more than 2000 characters
   **When** a distractor is applied
   **Then** the full document content is preserved — only the target passage is modified, not the entire content replaced

6. **(AC6) Model Selection**
   **Given** `GenerationParams` with `extraction_model` and `reasoning_model`
   **When** the distractor generator makes LLM calls
   **Then** it uses `params.reasoning_model` (distractors require nuanced judgment)

## Tasks / Subtasks

### Task 1: Fix content truncation bug (AC: 5, review P5)

- [x] Remove `primary_doc.content = modified_passage` — this destroys content beyond 2000 chars
- [x] Instead: LLM returns only the divergence passage text + a description; the full document content is preserved
- [x] Distractor generation should ADD a divergence description to the label, not modify document content at all (distractors are labeled passages, not modifications)

### Task 2: Implement proper distractor generation (AC: 1, 2, 3)

- [x] Rewrite `generate_distractors()` to:
  1. Load documents from `case_dir/anonymized_docs/`
  2. Compute distractor count: `round(contradiction_count * params.distractor_ratio)`
  3. For each distractor: select a random document, ask LLM to identify a legitimate divergence in that document
  4. Build `DistractorLabel` with scope, divergence_type, document_references, description
- [x] Use `strip_json_fences()` from injector for LLM response parsing
- [x] Use `_weighted_choice` pattern for divergence type selection (or uniform if no distribution specified)

### Task 3: Fix file handling (AC: 4)

- [x] Use same `_load_docs`/`_write_docs` pattern from injector (with source_map)
- [x] Write distractor labels to `case_dir/distractors/distractor_labels.jsonl`
- [x] Each line must validate against `DistractorLabel` Pydantic schema

### Task 4: Add model selection (AC: 6)

- [x] Use `params.reasoning_model` for LLM calls (not hardcoded `gpt-4o-mini`)

### Task 5: Update tests (AC: 1-6)

- [x] Rewrite `tests/generator/test_distractor_generator.py`
- [x] Test distractor count matches ratio
- [x] Test all 4 divergence types appear
- [x] Test no content truncation (document content length unchanged after generation)
- [x] Test JSONL output written correctly
- [x] Test model selection from params
- [x] Test zero contradiction_count produces zero distractors
- [x] Test markdown fence stripping in responses

### Task 6: Run full test suite (AC: all)

- [x] `pytest tests/generator/test_distractor_generator.py -v` — 15 passed
- [x] `pytest tests/ -q` — 563 passed (exceeds 554+ threshold)

## Dev Notes

### Key Design Decision: Distractors Don't Modify Documents

Unlike contradictions (which modify document content), distractors should NOT modify the corpus. A distractor is a label that says "this passage represents a legitimate divergence" — the passage already exists naturally in the document. The LLM identifies existing divergent content and labels it.

This means:
- No `_write_docs()` call needed (documents stay unchanged)
- No char offset tracking needed (distractors reference passages by description, not modification spans)
- `DistractorLabel` only needs: scope, divergence_type, document_references, description

### Import strip_json_fences

The `strip_json_fences()` utility was created in Story 3.1 in `injector.py`. Import it:
```python
from crossfire.generator.injector import strip_json_fences
```

Or move it to a shared utility if the import feels wrong architecturally.

### References

- [Source: epics.md#Story 3.3] — acceptance criteria
- Code review finding: P5 (content truncation)
- [Source: src/crossfire/shared/schemas/contradictions.py] — `DistractorLabel` schema

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation, all tests passed on first run.

### Completion Notes List

- Rewrote `distractor_generator.py` to fix P5 content truncation bug: distractors no longer modify document content at all. The old code replaced `primary_doc.content` with a 2000-char LLM output, destroying long documents. The new code treats distractors as labels on existing passages — documents stay unchanged.
- Imported `strip_json_fences` from `crossfire.generator.injector` for markdown fence stripping in LLM responses.
- Replaced `_write_docs()` call with `_write_labels()` that writes `DistractorLabel` JSONL to `case_dir/distractors/distractor_labels.jsonl`.
- Changed LLM model from hardcoded `gpt-4o-mini` to `params.reasoning_model`.
- LLM prompt changed from "modify this passage" to "identify a legitimate divergence" — aligning with the design decision that distractors are labels, not mutations.
- Rewrote test file with 15 tests covering all 6 ACs: count matching, zero count, all 4 divergence types, no content truncation, JSONL output, model selection, markdown fence stripping, error handling, and label structure.
- Full test suite: 563 passed (exceeds 554+ threshold).

### File List

- `src/crossfire/generator/distractor_generator.py` — rewritten (P5 fix, no doc mutation, JSONL labels output, reasoning_model, strip_json_fences)
- `tests/generator/test_distractor_generator.py` — rewritten (15 tests for all ACs)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — status updated
- `_bmad-output/implementation-artifacts/3-3-new-distractor-generation.md` — tasks checked, record filled

### Change Log

- 2026-04-11: Implemented Story 3.3-NEW — distractor generation rewrite (P5 fix, read-only design, JSONL labels, model selection). All tests pass (563/563).
