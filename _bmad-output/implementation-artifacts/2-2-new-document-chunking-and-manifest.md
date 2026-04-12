# Story 2.2-NEW: Document Chunking & Manifest

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a researcher,
I want raw source documents deterministically chunked into processable segments,
So that the agentic pipeline can process each chunk independently via fan-out architecture with per-chunk cost efficiency.

## Context

This is the SECOND story in Epic 2-NEW (Corpus Processing & Anonymization). Story 2.1-NEW created the organized `corpus/` directory with source documents organized by `corpus/{source_id}/{case_id}/`. This story creates the source-agnostic chunking utility that splits those documents into LLM-processable segments.

**Why chunking matters:** The fan-out architecture uses Sonnet for per-chunk claim extraction and Opus for cross-document reasoning. Document sizes range from 108 words to 208,212 words. Without chunking, large documents would exceed Sonnet's effective processing window and prevent parallel extraction. Small documents (< ~1000 words) should remain as single chunks.

**Source-agnostic design:** Chunking works on any text files in any case directory regardless of source (Grenfell, COPA, or NTSB). For PDF sources (Grenfell, COPA), PDF-to-text parsing precedes chunking.

**Downstream dependents:** Story 2.3 (source-specific agent plan documents) and Story 2.4 (bash wrapper scripts) consume chunks as input to Claude Code CLI sessions. Chunks must be deterministic so re-running produces identical output.

**Key constraint:** Chunks are intermediate artifacts. They are NOT shipped with the final dataset. They exist only to enable the fan-out processing architecture.

## Acceptance Criteria

1. **(AC1) Chunking Utility Exists**
   **Given** the `generation/` directory
   **When** I inspect `generation/chunk_documents.py`
   **Then** a Python script exists that chunks documents for a given case

2. **(AC2) Per-Case Chunking with CLI**
   **Given** a case directory with source documents (e.g., `corpus/ntsb/DCA19FA089/` or `corpus/grenfell/hearing_day_1/`)
   **When** I run `python generation/chunk_documents.py --case corpus/ntsb/DCA19FA089/`
   **Then** the files are split into chunks sized for efficient LLM processing (Sonnet per-chunk extraction)
   **And** a `chunk_manifest.json` is produced in the case directory mapping each chunk back to its source document and character offsets
   **And** chunking is source-agnostic (works on any text files in any case directory)

3. **(AC3) Deterministic Output**
   **Given** the same input files
   **When** I run the chunking utility twice
   **Then** identical chunks and manifest are produced (deterministic)

4. **(AC4) Small Document Preservation**
   **Given** a document that fits within a single chunk
   **When** it is processed
   **Then** it remains as a single chunk without unnecessary splitting

5. **(AC5) Logging**
   **Given** a chunking run
   **When** it completes
   **Then** progress and chunk count are logged via loguru at `INFO` level

6. **(AC6) All-Cases Mode**
   **Given** the `corpus/` directory with multiple cases
   **When** I run `python generation/chunk_documents.py --all`
   **Then** all cases in `corpus/` are chunked and each case gets its own `chunk_manifest.json`

## Tasks / Subtasks

### Task 1: Create `generation/` directory (AC: 1)

- [x] Create `generation/` directory at project root
- [x] This directory is deliberately outside `src/crossfire/` per architecture spec (generation is CLI-driven, not a Python library)
- [x] No `__init__.py` — this is NOT a Python package

### Task 2: Implement text chunking logic (AC: 2, 3, 4)

- [x] Create `generation/chunk_documents.py`
- [x] Implement `chunk_text(text: str, max_words: int = 800) -> list[dict]` function
  - Splits text into chunks of approximately `max_words` words
  - Splits on double-newline (paragraph) boundaries first
  - If a paragraph exceeds `max_words`, splits on single-newline boundaries
  - If a single line exceeds `max_words`, splits at the word boundary nearest to `max_words`
  - Each chunk dict contains: `chunk_index` (int), `char_start` (int), `char_end` (int), `word_count` (int), `text` (str)
  - `char_start` and `char_end` are character offsets into the original text
  - Documents with total word count <= `max_words` produce a single chunk (AC4)
  - Deterministic: no randomness, no floating-point, no dict ordering issues (AC3)
  - Chunks cover the full text without gaps or overlaps: `text[char_start:char_end]` for each chunk, concatenated, equals the original text

### Task 3: Implement per-case chunking (AC: 2, 5)

- [x] Implement `chunk_case(case_dir: Path, max_words: int = 800) -> dict` function
  - Reads `manifest.json` from `corpus/` root to get document metadata (title, document_type) for the case
  - Falls back to filename-derived metadata if case not found in manifest
  - Iterates over all `.txt` files in `case_dir` (sorted by filename for determinism)
  - Calls `chunk_text()` for each file
  - Writes chunk files to `case_dir/chunks/` directory:
    - Filename pattern: `{original_stem}_chunk_{NNN}.txt` (e.g., `001_METEOROLOGY_FACTUAL_-_ADDENDUM_1_chunk_001.txt`)
    - Single-chunk documents still get `_chunk_001.txt` suffix for consistency
  - Returns the manifest dict for this case

### Task 4: Generate chunk manifest (AC: 2)

- [x] Implement manifest generation within `chunk_case()`
  - Write `case_dir/chunks/chunk_manifest.json` with structure:
    ```json
    {
      "case_id": "DCA19FA089",
      "generated_at": "2026-04-11T...",
      "max_words": 800,
      "documents": [
        {
          "source_file": "001_METEOROLOGY_FACTUAL_-_ADDENDUM_1.txt",
          "title": "METEOROLOGY FACTUAL - ADDENDUM 1",
          "document_type": "meteorology_report",
          "total_words": 6216,
          "chunk_count": 8,
          "chunks": [
            {
              "chunk_file": "001_METEOROLOGY_FACTUAL_-_ADDENDUM_1_chunk_001.txt",
              "chunk_index": 0,
              "char_start": 0,
              "char_end": 4523,
              "word_count": 798
            }
          ]
        }
      ],
      "summary": {
        "total_documents": 27,
        "total_chunks": 156,
        "single_chunk_documents": 15,
        "multi_chunk_documents": 12
      }
    }
    ```
  - Write with `json.dumps(indent=2, sort_keys=False)` for readability
  - `sort_keys=False` preserves logical field ordering

### Task 5: CLI entry point (AC: 2, 5, 6)

- [x] Implement `main()` with `argparse`:
  - `--case PATH` — chunk a single case directory
  - `--all` — chunk all cases found in `corpus/`
  - `--max-words N` — override default chunk size (default: 800)
  - `--corpus-dir PATH` — corpus root directory (default: `corpus`)
  - Mutually exclusive: `--case` or `--all` (one required)
- [x] Add project root to `sys.path` for imports
- [x] Configure loguru: `logger.remove()` then `logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}")`
- [x] Log per-case summary: `"Chunked {case_id}: {doc_count} documents → {chunk_count} chunks"`
- [x] Log final summary for `--all`: `"Chunked {case_count} cases: {total_docs} documents → {total_chunks} chunks"`
- [x] Add `if __name__ == "__main__": main()` guard

### Task 6: Write tests (AC: 1-6)

- [x] Create `tests/test_chunk_documents.py`
- [x] Test `chunk_text()`:
  - Short text (< max_words) → single chunk covering full text
  - Text with paragraph breaks splits on `\n\n` boundaries
  - Very long single paragraph splits at word boundaries
  - Empty text → single chunk with empty content
  - Chunk offsets cover full text without gaps: verify `text[c['char_start']:c['char_end']]` concatenation equals original
  - Determinism: running twice produces identical results
  - All chunks have `word_count > 0` (except empty text edge case)
- [x] Test `chunk_case()` with `tmp_path` fixture:
  - Create mock case directory with 2-3 `.txt` files of varying sizes
  - Create a `corpus/manifest.json` at the parent with matching metadata
  - Run `chunk_case()` and verify:
    - `chunks/` subdirectory created
    - Correct number of chunk files
    - `chunk_manifest.json` exists and is valid JSON
    - Manifest `summary.total_documents` matches input files
    - Manifest `summary.total_chunks` >= `summary.total_documents`
    - Single-chunk documents have `chunk_count: 1`
    - Large documents have `chunk_count > 1`
  - Verify chunk file content matches original text slices
- [x] Test determinism: chunk same case twice, compare manifests (excluding `generated_at`)
- [x] Test `--all` mode: create 2 mock cases, run in all mode, verify both get chunk manifests

### Task 7: Verify end-to-end (AC: all)

- [x] Run `python generation/chunk_documents.py --case corpus/DCA19FA089/`
- [x] Verify `corpus/DCA19FA089/chunks/` directory created with chunk files
- [x] Verify `corpus/DCA19FA089/chunks/chunk_manifest.json` exists and is valid
- [x] Verify small documents (< 800 words) have single chunks
- [x] Verify large documents (e.g., 20,000+ word interview transcripts) are split into multiple chunks
- [x] Run chunking twice on same case, verify identical output (diff the manifests)
- [x] Run `python generation/chunk_documents.py --all` and verify all 5 cases are chunked
- [x] Run `pytest tests/test_chunk_documents.py -v`

## Dev Notes

### Architecture Compliance

- `generation/` lives at **project root**, deliberately OUTSIDE `src/crossfire/`. Generation tooling is CLI-driven (bash scripts + Claude Code CLI), not a Python library. [Source: architecture.md#Architectural Boundaries]
- `generation/` is NOT a Python package — no `__init__.py`. Scripts in this directory are standalone utilities. [Source: architecture.md#Project Structure]
- Chunks are **intermediate artifacts** — they do NOT ship with the final dataset in `data/datasets/{version}/`. The shipped dataset contains `anonymized_docs/`, `contradictions/`, `distractors/`, `metadata/`, `original_claims/`, and `validation/`. [Source: architecture.md#Data Architecture]
- Chunk files go inside `corpus/{CASE_ID}/chunks/` — keeping them co-located with the source documents they derive from. The `corpus/` directory is already gitignored (Story 2.1-NEW).
- The script MAY import from `crossfire.shared.schemas` for type validation — this is an allowed exception to the generation boundary. [Source: architecture.md#Generation Boundary]

### What to REUSE

| Existing Resource | Location | How to Use |
|---|---|---|
| Corpus manifest | `corpus/manifest.json` | Read for document metadata (title, document_type, word_count). Created by Story 2.1-NEW |
| `DocumentType` literal | `src/crossfire/shared/schemas/corpus.py` | Import for type validation if needed: `Literal["investigation_report", "witness_testimony", ...]` |
| Script entry pattern | `scripts/build_corpus.py` | Follow same loguru config pattern. But this script lives in `generation/`, not `scripts/` |
| `.txt` source files | `corpus/{source_id}/{case_id}/*.txt` | Input files to chunk. Plain text, one file per source document |

### What to CREATE

| File | Purpose |
|---|---|
| `generation/chunk_documents.py` | Chunking utility with text splitter, per-case chunking, manifest generation, CLI |
| `tests/test_chunk_documents.py` | Tests for chunking logic, manifest generation, determinism, CLI modes |
| `corpus/{CASE_ID}/chunks/` (gitignored) | Per-case chunk directories with chunk files + manifest (created by script) |

### What NOT to Create or Modify

- Do NOT create an `__init__.py` in `generation/` — it's not a Python package
- Do NOT modify any files in `src/crossfire/` — chunking is generation tooling
- Do NOT modify `corpus/manifest.json` — the corpus manifest from Story 2.1-NEW is read-only input
- Do NOT add new entries to `.gitignore` — `corpus/` is already gitignored

### Chunking Strategy Details

**Document size distribution (from corpus manifest):**

| Size Range | Count | Strategy |
|---|---|---|
| > 100,000 words | 5 docs | Heavy chunking (~125-250 chunks each) |
| 10,000 - 100,000 words | 21 docs | Moderate chunking (~12-125 chunks each) |
| 5,000 - 10,000 words | 19 docs | Light chunking (~6-12 chunks each) |
| 1,000 - 5,000 words | 69 docs | Few chunks (~2-6 each) |
| < 1,000 words | 76 docs | Single chunk (no splitting) |

**Default chunk size: ~800 words** (configurable via `--max-words`). Rationale:
- Sonnet processes ~800 words of dense technical text comfortably for claim extraction
- NTSB documents contain tabular data, lists, and technical specs — 800 words keeps each chunk coherent
- Roughly 1-2 pages of text, matching the architecture spec "1-2 page segments"

**Splitting priority:**
1. Double newline (`\n\n`) — paragraph boundaries. Most NTSB documents use blank lines between sections.
2. Single newline (`\n`) — line boundaries. Fallback for documents with no paragraph breaks.
3. Word boundary — last resort for extremely long lines (rare in NTSB text, but possible in tabular data).

**Determinism guarantee:** No randomness, no floating-point rounding, no set ordering. Sorted file iteration. Fixed `max_words` parameter. Character offsets are exact integers.

### Logging

All output via loguru. No `print()` statements. Pattern:

```python
from loguru import logger
logger.info(f"Chunking case {case_id}: {len(txt_files)} documents")
logger.info(f"  → {chunk_count} chunks from {doc_count} documents")
```

### Error Handling

- Missing case directory → log error and exit (for `--case` mode)
- Missing case directory → log warning and skip (for `--all` mode)
- Empty `.txt` file → produce single chunk with empty content, log warning
- No `.txt` files in case directory → skip case with warning
- Return-value error handling: `chunk_case()` returns the manifest dict or `None` on failure

### Test Execution

```bash
# Run from project root
PYTHONPATH=src pytest tests/test_chunk_documents.py -v

# Run chunking utility
python generation/chunk_documents.py --case corpus/DCA19FA089/
python generation/chunk_documents.py --all
```

### Project Structure Notes

After this story, the project gains:

```
generation/                               # NEW directory (not a Python package)
  chunk_documents.py                      # NEW — chunking utility
corpus/                                   # Already exists (gitignored)
  DCA19FA089/
    *.txt                                 # Source documents (from Story 2.1-NEW)
    chunks/                               # NEW (created by script)
      001_METEOROLOGY_FACTUAL_..._chunk_001.txt
      001_METEOROLOGY_FACTUAL_..._chunk_002.txt
      ...
      chunk_manifest.json                 # NEW — chunk-to-source mapping
  DCA19MA086/
    *.txt
    chunks/
      ...
  (3 more cases)
tests/
  test_chunk_documents.py                 # NEW
```

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure] — generation/ at project root, outside src/crossfire/
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries] — generation boundary, allowed schema imports
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture] — chunks are intermediate artifacts, not shipped
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2-NEW, Story 2.2] — story requirements and acceptance criteria
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-09.md] — agentic pivot, fan-out architecture rationale
- [Source: _bmad-output/planning-artifacts/prd.md#FR1] — agentic pipeline processing requirement
- [Source: _bmad-output/planning-artifacts/prd.md#Computational Constraints] — Sonnet for per-chunk extraction, Opus for cross-document reasoning
- [Source: corpus/manifest.json] — document metadata (titles, types, word counts)
- [Source: scripts/build_corpus.py] — entry point pattern, loguru configuration

### Previous Story Intelligence

From Story 2.1-NEW (Source Corpus Acquisition & Inventory):
- `corpus/` directory structure is `corpus/{source_id}/{case_id}/` with source files inside (e.g., `corpus/ntsb/DCA19FA089/`)
- NTSB case IDs are real NTSB IDs: DCA19FA089, DCA19MA086, DCA24MA063, ERA18FA120, WPR19FA080
- `corpus/manifest.json` exists with per-source, per-case document metadata
- Document types are source-specific strings (not a fixed enum)
- Script entry pattern: `sys.path.insert(0, str(project_root / "src"))` then import from crossfire
- loguru config: `logger.remove()` then `logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}")`
- All 229 tests pass (24 new + 205 existing). 10 pre-existing collection errors from Story 1-2 schema rewrite (unrelated)
- `_extraction_meta.json` files exist in `data/ntsb_extracted/` but NOT in `corpus/` — they were deliberately excluded

From git history:
- Recent commits follow pattern: loguru logging, Pydantic schemas, `(result, error)` return tuples
- Story 2.1-NEW used `json.dumps(indent=2)` for manifest output
- Script pattern from `scripts/build_corpus.py`: project root detection via `Path(__file__).resolve().parent.parent`

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

No debug issues encountered.

### Completion Notes List

- Created `generation/` directory at project root (no `__init__.py`, not a Python package)
- Implemented 3-level text chunking: paragraph boundaries (`\n\n`) → line boundaries (`\n`) → word boundaries
- Accumulation algorithm ensures chunks stay within `max_words` while preserving text integrity
- Critical invariant maintained: `"".join(c["text"] for c in chunks) == text` (no gaps, no overlaps)
- `chunk_case()` reads corpus manifest for metadata, falls back to filename-derived title
- Chunk files written to `corpus/{CASE_ID}/chunks/` with `_chunk_NNN.txt` naming
- `chunk_manifest.json` produced per case with full document/chunk metadata and summary
- CLI supports `--case` (single), `--all` (batch), `--max-words`, `--corpus-dir`
- 35 tests: 20 unit (TestChunkText), 13 integration (TestChunkCase), 2 CLI validation
- End-to-end verified: 5 cases, 190 documents → 2826 chunks
- Determinism verified: identical output across multiple runs
- 210 tests pass total (35 new + 175 existing), 0 regressions
- 10 pre-existing collection errors from Story 1-2 schema rewrite (unrelated)

### File List

- `generation/chunk_documents.py` — NEW: chunking utility (text splitter, per-case chunking, manifest, CLI)
- `tests/test_chunk_documents.py` — NEW: 35 tests for chunking logic, manifest, determinism, CLI
- `_bmad-output/implementation-artifacts/2-2-new-document-chunking-and-manifest.md` — MODIFIED: task checkboxes, Dev Agent Record, status
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — MODIFIED: story status ready-for-dev → review

### Change Log

- 2026-04-11: Implemented Story 2.2-NEW — Document Chunking & Manifest
  - Created `generation/chunk_documents.py` with deterministic 3-level text chunking
  - Created `tests/test_chunk_documents.py` with 35 tests (unit + integration + CLI)
  - Verified end-to-end on real corpus: 190 documents → 2826 chunks across 5 cases
