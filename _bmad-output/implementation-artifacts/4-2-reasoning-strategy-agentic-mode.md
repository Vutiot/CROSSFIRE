# Story 4.2: Reasoning Strategy (Agentic Mode)

Status: review

## Story

As a researcher,
I want an LLM-agentic auditing pipeline that extracts claims and cross-checks them,
so that I can evaluate CLAIRE-style approaches on CROSSFIRE corpora.

## Acceptance Criteria

1. Given a `ReasoningStrategy` implementation in `reasoning_strategy.py` — when I run it against a corpus — then it extracts atomic claims from each document using LLM calls
2. It cross-checks claims across documents for contradictions
3. It produces `DetectedIncoherence` entries with evidence_references (source documents) and confidence scores
4. Running `HybridPipeline` with `NullGraphStrategy` + this reasoning strategy constitutes agentic mode (FR18)
5. The strategy uses SeedManager for any random decisions
6. LLM calls go through the thin wrapper with cost tracking

## Tasks / Subtasks

- [x] Task 1: Create `src/crossfire/pipeline/strategies/reasoning_strategy.py` (AC: #1, #2, #3, #5, #6)
  - [x] Implement `LLMReasoningStrategy(ReasoningStrategy)` with constructor accepting `llm_call` function and `SeedManager`
  - [x] Implement claim extraction: for each document, call LLM to extract atomic factual claims as JSON
  - [x] Implement cross-checking: compare claims across document pairs, call LLM to identify contradictions
  - [x] Produce `DetectedIncoherence` entries with document IDs as evidence_references and LLM-derived confidence
  - [x] Return `(ReasoningResult, None)` on success, `(None, error)` on failure

- [x] Task 2: Write tests in `tests/pipeline/test_reasoning_strategy.py` (AC: #1-#6)
  - [x] Mock LLM calls to return deterministic claim extraction and contradiction detection
  - [x] Test: claims extracted from documents
  - [x] Test: contradictions detected across document pairs
  - [x] Test: DetectedIncoherence entries have valid evidence_references and confidence
  - [x] Test: integration with HybridPipeline in agentic mode
  - [x] Test: LLM failure handled gracefully
  - [x] Test: empty corpus produces empty results

- [x] Task 3: Run full test suite — no regressions

## Dev Notes

### Existing Infrastructure
- `llm_call(prompt, model, temperature, dry_run)` in `src/crossfire/shared/llm.py` — returns `(response, error)` tuple
- `SeedManager` in `src/crossfire/shared/seed_manager.py` — `get_seed(component, index)`
- `ReasoningStrategy` ABC and `ReasoningResult` in `src/crossfire/pipeline/strategies/base.py`
- `DetectedIncoherence(id, evidence_references, confidence, description)` in `src/crossfire/shared/schemas/reports.py`
- `Document(id, document_type, subcorpus_id, reliability_signal, content)` in `src/crossfire/shared/schemas/corpus.py`

### LLM Call Pattern
All LLM calls through `llm_call()` wrapper. Temperature=0 for determinism. Parse JSON responses.

### Error Handling
Return `(result, error)` tuples. Individual LLM failures logged WARNING, continue processing remaining documents.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No issues encountered.

### Completion Notes List

- Task 1: Created `LLMReasoningStrategy` with two-phase pipeline: (1) extract atomic claims from each document via LLM, (2) cross-check claims across all document pairs for contradictions. Uses `llm_call()` wrapper, temperature=0, JSON parsing with graceful error handling.
- Task 2: 9 tests covering claim extraction, cross-checking, agentic mode integration, LLM failure handling, bad JSON, and empty corpus.
- Task 3: 339 tests pass (zero regressions).

### File List

- src/crossfire/pipeline/strategies/reasoning_strategy.py (new)
- src/crossfire/pipeline/strategies/__init__.py (modified)
- tests/pipeline/test_reasoning_strategy.py (new)

### Change Log

- 2026-04-06: Story 4.2 implemented — LLM reasoning strategy with claim extraction and cross-checking, 9 tests
