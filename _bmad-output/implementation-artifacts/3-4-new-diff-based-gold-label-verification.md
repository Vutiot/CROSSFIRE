# Story 3.4-NEW: Diff-Based Gold Label Verification

Status: complete

## Story

As a researcher,
I want mechanical verification that each injected contradiction changed only the target fact,
So that gold labels are provably correct and contamination-free — not dependent on agent self-reporting.

## Context

This is the FOURTH story in Epic 3-NEW. Stories 3.1-3.2 inject contradictions (modifying document content), Story 3.3 generates distractor labels (no content modification). This story creates the verification gate: a standalone script that compares original and modified documents via mechanical diff, validates that only the target fact was changed, and produces verified gold labels.

**Key principle (FR14, NFR5):** Diff-derived char offsets take precedence over agent self-reported offsets. The mechanical diff is the source of truth for gold labels.

**Architecture:** This script lives in `generation/` at project root — it's a verification utility in the generation toolchain, not part of the evaluable Python package.

## Acceptance Criteria

1. **(AC1) Diff-Derived Char Offsets**
   **Given** an original document and its modified version
   **When** `generation/verify_dataset.py` runs diff verification
   **Then** char offsets are derived from the mechanical diff, not from agent self-reported offsets (FR14)

2. **(AC2) Context Contamination Check**
   **Given** a diff between original and modified documents
   **When** the surrounding context is checked
   **Then** the +-200 characters around each modification must be identical — any deviation flags contamination (FR12)

3. **(AC3) Unintended Modifications Detected**
   **Given** an injection where the agent introduced unintended secondary changes
   **When** diff verification detects them
   **Then** the contradiction is flagged in `validation/unintended_modifications.json` and rejected from gold set (FR10)

4. **(AC4) Discrepancy Logging**
   **Given** discrepancies between agent self-reported and diff-derived labels
   **When** verification detects them
   **Then** logged to `validation/agent_label_discrepancies.json`; diff-derived values take precedence

5. **(AC5) Rejection Tracking**
   **Given** contradictions that fail verification
   **When** rejected
   **Then** written to `validation/rejected_contradictions.jsonl` with rejection reason
   **And** `validation/diff_verification_log.json` records full results

6. **(AC6) Verified Gold Labels Output**
   **Given** all passing contradictions
   **When** gold labels are assembled
   **Then** `contradictions/intra_doc_contradictions.jsonl`, `contradictions/inter_doc_contradictions.jsonl`, and `contradictions/all_contradictions.jsonl` are produced
   **And** every line validates against `ContradictionLabel` schema (NFR5)

## Tasks / Subtasks

### Task 1: Create verify_dataset.py (AC: 1, 2, 3, 4, 5, 6)

- [x] Create `generation/verify_dataset.py` as a standalone CLI script
- [x] CLI: `python generation/verify_dataset.py --case <case_dir>` and `--all` mode
- [x] For each case:
  1. Load original documents from a backup/snapshot (before injection)
  2. Load modified documents from `anonymized_docs/`
  3. Load agent self-reported labels from `contradictions/gold_labels.jsonl` (written by annotator)
  4. For each label: compute mechanical diff between original and modified document
  5. Derive `char_start`/`char_end` from the diff (not from the label)
  6. Check +-200 char context is identical (contamination check)
  7. Detect unintended secondary changes (multiple diffs when only one expected)
  8. Compare diff-derived offsets with agent-reported offsets (log discrepancies)
  9. Build verified `ContradictionLabel` with diff-derived offsets
  10. Write verified labels and validation artifacts

### Task 2: Implement diff engine (AC: 1, 2, 3)

- [x] Use Python's `difflib.SequenceMatcher` to find differences between original and modified text
- [x] For each modification block: extract `char_start`, `char_end`, `original_text`, `modified_text`
- [x] Context check: compare `original[char_start-200:char_start]` with `modified[adj_start-200:adj_start]` — must be identical
- [x] Same for trailing context: `original[char_end:char_end+200]` vs `modified[adj_end:adj_end+200]`

### Task 3: Handle pre-injection backup (AC: 1)

- [x] The injector should save original documents before modification — add `_backup_originals()` to injector.py that copies `anonymized_docs/` to `anonymized_docs_original/` before first injection
- [x] verify_dataset.py reads from `anonymized_docs_original/` (pre-injection) and `anonymized_docs/` (post-injection)
- [x] If no backup exists, verification cannot run — log error and skip case

### Task 4: Write validation output files (AC: 4, 5, 6)

- [x] Create `case_dir/validation/` directory
- [x] Write `diff_verification_log.json` — full results per label
- [x] Write `rejected_contradictions.jsonl` — failed labels with reason
- [x] Write `unintended_modifications.json` — labels with extra changes
- [x] Write `agent_label_discrepancies.json` — offset mismatches
- [x] Write verified labels split by scope:
  - `contradictions/intra_doc_contradictions.jsonl`
  - `contradictions/inter_doc_contradictions.jsonl`
  - `contradictions/all_contradictions.jsonl`

### Task 5: Write tests (AC: 1-6)

- [x] Create `tests/test_verify_dataset.py`
- [x] Test clean injection: single diff matches label → passes verification
- [x] Test contamination: context differs → flagged
- [x] Test unintended changes: multiple diffs → rejected
- [x] Test offset discrepancy: agent says char_start=100 but diff says 150 → logged, diff wins
- [x] Test output files created in validation/
- [x] Test scope-split JSONL output

### Task 6: Update injector to backup originals (AC: 1)

- [x] Add `_backup_originals(case_dir)` to injector.py — called once before any modifications
- [x] Only backs up if `anonymized_docs_original/` doesn't already exist (idempotent)

### Task 7: Run full test suite (AC: all)

- [x] `pytest tests/test_verify_dataset.py -v` — 29 passed
- [x] `pytest tests/ -q` — 592 passed (563 existing + 29 new)

## Dev Notes

### Architecture

- `generation/verify_dataset.py` lives in `generation/` — outside `src/crossfire/`
- It MAY import from `crossfire.shared.schemas` for schema validation (allowed exception per architecture)
- It's a standalone CLI script, not a Python library

### Diff Strategy

Using `difflib.SequenceMatcher.get_opcodes()`:
```python
sm = difflib.SequenceMatcher(None, original_text, modified_text)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'replace':
        # This is a modification: original[i1:i2] → modified[j1:j2]
        diff_original = original_text[i1:i2]
        diff_modified = modified_text[j1:j2]
    elif tag == 'insert':
        # Text was added at position i1 in original
    elif tag == 'delete':
        # Text was removed from original[i1:i2]
```

A clean injection should produce exactly ONE `replace` opcode (plus surrounding `equal` opcodes). Multiple `replace`/`insert`/`delete` opcodes indicate contamination.

### References

- [Source: epics.md#Story 3.4] — acceptance criteria
- [Source: prd.md FR10, FR12, FR14, NFR5] — minimal-pair, contamination check, diff-derived truth
- [Source: architecture.md#Generation Boundary] — verification in generation/

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
N/A

### Completion Notes List
- All 6 acceptance criteria met
- `difflib.SequenceMatcher` used for mechanical diff; produces character-level opcodes
- Note: SequenceMatcher may split what appears as a single word replacement into multiple opcodes if the old and new text share characters. Test data must use fully distinct replacement strings to get exactly 1 opcode.
- Inter-doc verification diffs against the second document_reference (target doc)
- Full test suite: 592 passed (29 new + 563 existing)

### File List
- `generation/verify_dataset.py` — NEW: standalone CLI verification script
- `src/crossfire/generator/injector.py` — MODIFIED: added `_backup_originals()` and `import shutil`
- `tests/test_verify_dataset.py` — NEW: 29 tests covering all ACs
- `_bmad-output/implementation-artifacts/3-4-new-diff-based-gold-label-verification.md` — UPDATED: status complete

### Change Log
- 2026-04-11: Story implemented — verification script, injector backup, tests
