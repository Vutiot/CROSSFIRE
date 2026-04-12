# Story 3.1-NEW: Intra-Document Contradiction Injection

Status: review

## Story

As a researcher,
I want to inject controlled contradictions within individual documents using minimal-pair modification,
So that I can benchmark systems on detecting intra-document factual incoherences with known ground truth.

## Context

This is the FIRST story in Epic 3-NEW (Contradiction Injection & Gold Annotation). It replaces the deprecated Story 3.1. The existing `src/crossfire/generator/injector.py` was quick-fix rewritten to unbreak imports but has **critical bugs identified by code review** that must be fixed.

**Architecture decision:** The PRD specifies injection as part of the agentic pipeline (Claude Code CLI), but this story implements the **Python programmatic path** for injection — used for testing, reproducibility verification, and as a fallback when CLI sessions are unavailable. The plan documents (Story 2.3) describe the CLI-driven injection flow. Both paths produce identical `ContradictionLabel` output.

**Code review findings to fix (from the Blind Hunter + Edge Case Hunter + Acceptance Auditor):**
- P1: Silent no-op when `original_text` not found — phantom label created
- P2: `char_start`/`char_end` stale after content mutation
- P3: `char_start=0` fallback produces bogus offsets
- P4: `_write_docs` groups by `document_type` — overwrites/duplicates files
- P6: LLM JSON responses wrapped in markdown fences not handled
- P7: `intra_count`/`inter_count` forced to 1 even when rate is 0
- P8: `_weighted_choice` crashes with ValueError if all weights are zero
- P11: `system_affinity` randomly assigned, not configurable
- P14: `GenerationParams` missing field validation

## Acceptance Criteria

1. **(AC1) Minimal-Pair Construction**
   **Given** an anonymized document from a processed case
   **When** the injection pipeline runs with scope `intra_doc`
   **Then** contradictions are injected by modifying only the target fact, not surrounding prose (FR10)

2. **(AC2) 6 Mechanisms Supported**
   **Given** injection parameters specifying mechanism distribution
   **When** contradictions are injected
   **Then** each uses one of: numeric_drift, entity_swap, causal_inversion, temporal_contradiction, omission_based_implicit, temporal_revision_conflict (FR7)

3. **(AC3) Detectability Tagging**
   **Given** injection parameters specifying detectability distribution
   **When** contradictions are injected
   **Then** each is tagged with: single_hop, multi_hop, or entity_resolution_dependent (FR8)

4. **(AC4) Configurable System Affinity**
   **Given** injection parameters with `affinity_distribution`
   **When** contradictions are injected
   **Then** each is tagged with system_affinity sampled from the configured distribution: balanced, graph_favoring, or agentic_favoring (FR9)

5. **(AC5) Complete Label Metadata**
   **Given** a completed intra-doc injection
   **When** I inspect the label
   **Then** it includes: scope, mechanism, detectability, system_affinity, difficulty, char_start, char_end, original_text, modified_text, rationale, ground_truth, document_references

6. **(AC6) Char Offsets Are Correct**
   **Given** a completed injection
   **When** I check `char_start` and `char_end` against the **modified** document content
   **Then** `doc.content[char_start:char_end]` equals `modified_text` (offsets reference the post-replacement document)

7. **(AC7) No Phantom Labels**
   **Given** an injection where `original_text` is not found in the document
   **When** the replacement fails
   **Then** the injection is counted as a failure (not a success), no label is created

8. **(AC8) Markdown Fence Stripping**
   **Given** an LLM response wrapped in ```json ... ``` fences
   **When** the response is parsed
   **Then** fences are stripped before JSON parsing

9. **(AC9) Zero-Rate Produces Zero Injections**
   **Given** `contradiction_rate_intra_doc=0.0`
   **When** the injector runs
   **Then** zero intra-doc injections are attempted

10. **(AC10) Model Selection from GenerationParams**
    **Given** `GenerationParams` with `extraction_model` and `reasoning_model` fields
    **When** the injector makes LLM calls
    **Then** fact extraction uses `params.extraction_model` (default: Sonnet) and modification uses `params.reasoning_model` (default: Opus)

## Tasks / Subtasks

### Task 1: Fix `_load_docs` / `_write_docs` file handling (AC: 6, review P4)

- [x] Track original source filename for each document during load (add a `_source_file` attribute or side-map)
- [x] `_write_docs`: write documents back to their ORIGINAL source files (not grouped by document_type)
- [x] Handle the case where `_load_docs` reads from multiple JSONL files — preserve file-to-document mapping
- [x] Add `try/except` around `Document.model_validate_json(line)` to skip malformed lines with warning

### Task 2: Add markdown fence stripping utility (AC: 8, review P6)

- [x] Create helper function `strip_json_fences(text: str) -> str` that removes ```json ... ``` wrapping
- [x] Apply before every `json.loads()` call in the injector
- [x] Handle variations: ````json`, `````, triple backticks with/without language tag

### Task 3: Fix injection count logic (AC: 9, review P7)

- [x] Change `intra_count = max(1, round(...))` to `intra_count = round(total_docs * rate) if rate > 0 else 0`
- [x] Same for `inter_count` — but inter_count is Story 3.2's concern; set to 0 in this story's scope
- [x] Guard `inter_count` based on `len(all_docs)`: if fewer than 2 documents, force `inter_count = 0`

### Task 4: Fix `_weighted_choice` (AC: 4, review P8, P11)

- [x] Handle all-zero weights: check `sum(weights) > 0` before `rng.choices()`, fall back to uniform
- [x] Log warning when distribution keys don't match valid choices
- [x] Use `affinity_distribution` from `GenerationParams` for system_affinity selection (not random)

### Task 5: Fix char offset computation (AC: 6, review P2, P3)

- [x] Compute `char_start`/`char_end` AFTER the replacement, not before
- [x] Use `doc.content.find(modified_text)` after the replace to get correct post-replacement offsets
- [x] If `modified_text` not found after replacement (shouldn't happen but defensive): set `char_start=-1, char_end=-1` as sentinel

### Task 6: Fix phantom label creation (AC: 7, review P1)

- [x] When `original_text` not found in document content: return `(None, "original_text not found in document")` — do NOT create a label
- [x] Remove the silent fallback that logs warning but still creates a label

### Task 7: Add model selection from params (AC: 10)

- [x] Use `params.extraction_model` for fact extraction LLM calls (currently hardcoded `gpt-4o-mini`)
- [x] Use `params.reasoning_model` for modification LLM calls (currently hardcoded `gpt-4o-mini`)
- [x] Remove all hardcoded `model="gpt-4o-mini"` from injector

### Task 8: Update tests (AC: 1-10)

- [x] Update `tests/generator/test_injector.py` with tests for all new behaviors:
  - Test zero-rate produces zero injections
  - Test phantom label prevention (mock LLM returns text not in doc)
  - Test markdown fence stripping
  - Test affinity_distribution configuration
  - Test char offsets reference post-replacement content
  - Test file write-back preserves original filenames
  - Test all-zero weights doesn't crash
  - Test model selection from params (verify LLM called with correct model)
- [x] Ensure mock LLM returns realistic responses with correct field names

### Task 9: Run full test suite (AC: all)

- [x] Run `pytest tests/generator/test_injector.py -v`
- [x] Run `pytest tests/ -q` — verify 515+ passed, 0 failures

## Dev Notes

### Architecture Compliance

- `src/crossfire/generator/injector.py` lives inside the Python package. The PRD says generation should be in `generation/`, but this is the **programmatic injection path** — a Python utility for testing and verification. The agentic path uses Claude Code CLI (Story 2.3/2.4). Both are valid.
- The injector imports from `crossfire.shared.schemas` — this is correct.
- The injector uses `crossfire.shared.llm.llm_call` — correct for the Python path.

### Key Schema References

**ContradictionLabel** (`src/crossfire/shared/schemas/contradictions.py`):
```python
class ContradictionLabel(BaseModel):
    scope: Literal["intra_doc", "inter_doc"]
    mechanism: Mechanism  # 6 values
    detectability: Detectability  # 3 values
    system_affinity: SystemAffinity  # 3 values
    difficulty: Difficulty  # easy, medium, hard
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    original_text: str
    modified_text: str
    rationale: str
    ground_truth: bool
    document_references: list[str]
```

**GenerationParams** (`src/crossfire/shared/schemas/config.py`):
```python
class GenerationParams(BaseModel):
    version_id: str
    contradiction_rate_intra_doc: float = Field(ge=0.0, le=1.0)
    contradiction_rate_inter_doc: float = Field(ge=0.0, le=1.0)
    distractor_ratio: float = Field(ge=0.0)
    mechanism_distribution: dict[str, float] = {}
    difficulty_distribution: dict[str, float] = {}
    affinity_distribution: dict[str, float] = {}
    extraction_model: str = "claude-sonnet-4-20250514"
    reasoning_model: str = "claude-opus-4-20250514"
```

### What to REUSE

| Resource | Location | How to Use |
|---|---|---|
| Existing injector | `src/crossfire/generator/injector.py` | Rewrite in-place — keep the structure, fix the bugs |
| Existing tests | `tests/generator/test_injector.py` | Rewrite to match new behavior |
| LLM wrapper | `src/crossfire/shared/llm.py` | Use for all LLM calls |
| SeedManager | `src/crossfire/shared/seed_manager.py` | Deterministic random operations |
| Document model | `src/crossfire/shared/schemas/corpus.py` | `Document` with `document_id`, `source`, `document_type`, `source_case_id`, `scope_classification`, `content` |

### What NOT to Create

- Do NOT create new files — rewrite `injector.py` and `test_injector.py` in place
- Do NOT modify schemas — `GenerationParams` already has the needed fields
- Do NOT modify `llm.py` — it already supports model parameter

### References

- [Source: epics.md#Story 3.1] — acceptance criteria
- [Source: prd.md lines 194, 279] — fan-out architecture, model selection
- [Source: architecture.md line 73] — generation boundary
- Code review findings: P1, P2, P3, P4, P6, P7, P8, P11, P14

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- 31/31 injector tests pass
- 540/540 full suite tests pass (0 failures, 0 skipped)

### Completion Notes List

- Rewrote `injector.py` with all 8 code-review bug fixes (P1, P2, P3, P4, P6, P7, P8, P11)
- P1: Phantom labels prevented — `_execute_injection` returns `(None, error)` when `original_text` not in document
- P2: Char offsets computed AFTER `content.replace()` using `doc.content.find(modified_text)`
- P3: Defensive sentinel — if `modified_text` not found post-replace, returns failure instead of bogus offset
- P4: `_load_docs` returns `source_map` tracking document_id -> source filename; `_write_docs` uses it to preserve original files
- P6: `strip_json_fences()` utility strips markdown fences before every `json.loads()` call
- P7: Zero rate produces zero injections: `round(rate * docs) if rate > 0 else 0`
- P8: `_weighted_choice` checks `sum(weights) > 0` before `rng.choices()`, falls back to uniform
- P11: `system_affinity` uses `_weighted_choice(params.affinity_distribution, ...)` instead of `rng.choice()`
- AC10: `params.extraction_model` for fact extraction, `params.reasoning_model` for modification; no hardcoded `gpt-4o-mini`
- inter_count hardcoded to 0 (Story 3.2 scope)
- Malformed JSONL lines logged and skipped during load
- Comprehensive test suite: 31 tests across 6 test classes

### File List

- src/crossfire/generator/injector.py (modified — full rewrite with bug fixes)
- tests/generator/test_injector.py (modified — full rewrite with comprehensive tests)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — status update)
- _bmad-output/implementation-artifacts/3-1-new-intra-document-contradiction-injection.md (modified — task tracking)

### Change Log

- 2026-04-11: Story 3.1-NEW implemented — rewrote injector.py with all code-review bug fixes (P1-P11), added strip_json_fences utility, model selection from GenerationParams, comprehensive test coverage (31 tests, 540 total suite)
