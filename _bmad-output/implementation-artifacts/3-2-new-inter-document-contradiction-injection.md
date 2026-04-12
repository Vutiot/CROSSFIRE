# Story 3.2-NEW: Inter-Document Contradiction Injection

Status: review

## Story

As a researcher,
I want to inject controlled contradictions across documents within a case,
So that I can benchmark systems on detecting cross-document factual incoherences requiring entity resolution and multi-document reasoning.

## Context

This is the SECOND story in Epic 3-NEW. Story 3.1-NEW implemented intra-doc injection with all code review fixes. This story extends the injector to support `inter_doc` scope — where the original claim is in one document and the contradicting modification is in a different document.

**Key difference from intra-doc:** Inter-doc injection must leverage natural cross-document entity references. Random document pairing (the bug from the code review: Auditor F9) produces unrealistic contradictions. The injector should prefer document pairs that share entities or topics.

**Code review finding to fix:**
- Auditor F9: Inter-doc injection ignores entity relationships — random `rng.sample(all_docs, 2)` instead of entity-aware selection

## Acceptance Criteria

1. **(AC1) Cross-Document Scope**
   **Given** anonymized documents from a processed case
   **When** the injection pipeline runs with `contradiction_rate_inter_doc > 0`
   **Then** contradictions are injected where the original claim is in one document and the modification is in a different document (FR6)

2. **(AC2) Entity-Aware Target Selection**
   **Given** inter-document injection
   **When** target documents are selected
   **Then** the injector prefers document pairs that share entity references or topic overlap — not purely random pairing

3. **(AC3) Same Mechanisms Available**
   **Given** injection parameters for mechanism, detectability, and system affinity
   **When** inter-doc contradictions are injected
   **Then** the same 6 mechanisms, 3 detectability levels, and 3 system affinity options are available (FR7, FR8, FR9)

4. **(AC4) Minimal-Pair Across Documents**
   **Given** an inter-doc injection
   **When** a modification is made
   **Then** only the target fact is changed in the target document (FR10)

5. **(AC5) Document References in Label**
   **Given** a completed inter-doc injection
   **When** I inspect the label
   **Then** `document_references` lists both the source document (where the original claim is) and the target document (where the modification was made)

## Tasks / Subtasks

### Task 1: Enable inter_doc in injection count logic (AC: 1)

- [x] In `inject_contradictions()`, compute `inter_count = round(total_docs * params.contradiction_rate_inter_doc) if params.contradiction_rate_inter_doc > 0 else 0`
- [x] Guard: if `len(all_docs) < 2`, force `inter_count = 0` with warning
- [x] Add inter_doc entries to the injection plan via `_build_injection_plan`

### Task 2: Implement entity-aware target selection (AC: 2)

- [x] Add `_select_inter_doc_targets()` function that:
  1. Extracts key terms/entities from each document (simple approach: split content into words, find capitalized multi-word phrases or domain terms)
  2. Computes term overlap between document pairs
  3. Selects pairs with highest overlap (or random fallback if no overlap found)
- [x] The entity detection should be lightweight (no LLM call) — use regex or simple NLP heuristics
- [x] Fall back to random pairing if no entity overlap is found (don't fail)

### Task 3: Handle inter-doc modification flow (AC: 4, 5)

- [x] For inter-doc: extract facts from document A (source), apply modification to document B (target)
- [x] The modification prompt should reference the original fact from doc A and instruct the LLM to insert a contradicting version into doc B
- [x] Build label with `document_references = [doc_a.document_id, doc_b.document_id]`

### Task 4: Update tests (AC: 1-5)

- [x] Add inter-doc test cases to `tests/generator/test_injector.py`:
  - Test inter_doc injections produced when rate > 0 and docs >= 2
  - Test inter_count = 0 when only 1 document
  - Test document_references has 2 different document IDs
  - Test entity-aware selection prefers overlapping docs
  - Test random fallback when no entity overlap
- [x] Update mock LLM to handle inter-doc modification prompts

### Task 5: Run full test suite (AC: all)

- [x] `pytest tests/generator/test_injector.py -v`
- [x] `pytest tests/ -q` — verify 540+ passed, 0 failures

## Dev Notes

### Entity-Aware Target Selection Strategy

Simple heuristic approach (no LLM needed):
1. For each document, extract a set of "key terms" — capitalized phrases (2+ words), numbers with units, proper nouns
2. Compute Jaccard similarity between document term sets
3. Rank document pairs by similarity; select from top pairs weighted by similarity
4. If all similarities are 0 (no shared terms), fall back to random selection

This is lightweight and deterministic (given seed). No need for full NLP or LLM-based entity extraction — that's the pipeline's job, not the injector's.

### What Exists Already

The injector from Story 3.1-NEW already has:
- `_load_docs()` with source_map tracking
- `_write_docs()` with original file preservation
- `strip_json_fences()` utility
- `_weighted_choice()` with zero-weight protection
- `_extract_facts()` and `_apply_modification()` with model selection
- Char offset computation after replacement
- Phantom label prevention

This story only needs to:
1. Enable `inter_count` computation (currently hardcoded to 0)
2. Add `_select_inter_doc_targets()` function
3. Modify `_execute_injection()` to handle inter-doc flow (modify doc B based on fact from doc A)

### References

- [Source: epics.md#Story 3.2] — acceptance criteria
- Code review finding: Auditor F9 (inter-doc ignores entity relationships)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- All 45 injector tests passed on first run after a single test assertion fix (regex captured "The Federal..." as proper noun phrase)
- Full suite: 554 passed in 3.71s

### Completion Notes List

- Task 1: Replaced hardcoded `inter_count = 0` with computed value from `params.contradiction_rate_inter_doc`. Added guard for < 2 docs with warning log. The existing `_build_injection_plan` already had inter_doc loop, just needed non-zero count.
- Task 2: Added `_extract_key_terms()` using compiled regex (`_KEY_TERM_RE`) for capitalized phrases, acronyms, and numbers with units. Added `_select_inter_doc_targets()` with Jaccard similarity computation, weighted selection from overlapping pairs, and random fallback. All lightweight, no LLM calls.
- Task 3: Added `_execute_inter_doc_injection()` that extracts facts from doc_a, calls new `_apply_inter_doc_modification()` to generate contradicting text for doc_b, inserts at paragraph boundary, and builds label with both document IDs. Updated `_select_targets()` to use entity-aware selection for inter_doc scope.
- Task 4: Added 14 new tests across `TestInterDocInjection` (6 tests) and `TestEntityAwareSelection` (8 tests). Updated `_fake_llm` to handle inter-doc modification prompts. Updated existing `test_inter_count_always_zero` to `test_inter_count_zero_when_single_doc`.
- Task 5: 45/45 injector tests passed. 554/554 full suite tests passed.

### File List

- src/crossfire/generator/injector.py (modified)
- tests/generator/test_injector.py (modified)

### Change Log

- 2026-04-11: Implemented Story 3.2-NEW — inter-document contradiction injection with entity-aware target selection
