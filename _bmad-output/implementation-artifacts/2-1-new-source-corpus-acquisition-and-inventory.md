# Story 2.1-NEW: Source Corpus Acquisition & Inventory

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a researcher,
I want a structured inventory of raw investigation source documents organized by source and case,
So that the agentic pipeline knows which sources, cases, and document types are available for processing.

## Context

This is the FIRST story in Epic 2-NEW (Corpus Processing & Anonymization). The 2026-04-09 sprint change proposal pivoted CROSSFIRE from synthetic corpus generation to agentic processing of real investigation source documents. This story creates the organized corpus directory and manifest that all downstream stories depend on.

The system supports multiple data sources with `corpus/{source_id}/{case_id}/` directory layout: Grenfell Tower Inquiry (primary), Chicago COPA (secondary), and NTSB aviation dockets (tertiary). NTSB source data already exists: 5 cases have been scraped and text-extracted to `data/ntsb_extracted/`. Each source has its own acquisition process and source-specific document types. Document types are strings (not a fixed enum) to accommodate source-specific types.

**Downstream dependents:** Story 2.2 (chunking), Story 2.3 (agent plan), Story 2.4 (bash wrappers), Stories 3.1-3.5 (injection & verification).

## Acceptance Criteria

1. **(AC1) Case Directory Organization**
   **Given** extracted source documents (e.g., NTSB text files in `data/ntsb_extracted/`)
   **When** I run `python scripts/build_corpus.py --source ntsb`
   **Then** each case has its own directory under `corpus/{source_id}/{case_id}/` (e.g., `corpus/ntsb/DCA19FA089/`) containing the source files

2. **(AC2) Document Type Inventory & Manifest**
   **Given** a populated `corpus/` directory
   **When** I inspect `corpus/manifest.json`
   **Then** a manifest documents each source's cases and their available document types (source-specific strings, e.g., "hearing_transcript" for Grenfell, "tactical_response_report" for COPA, "investigation_report" for NTSB)

3. **(AC3) Version Control Exclusion**
   **Given** the `corpus/` directory
   **When** I check `.gitignore`
   **Then** `corpus/` is excluded from version control (source investigation documents are not shipped)

4. **(AC4) Heterogeneous Document Preservation**
   **Given** a case directory
   **When** I review its contents
   **Then** ALL document types from the source are preserved as-is — no filtering or homogenization of document types (FR5)

## Tasks / Subtasks

### Task 1: Add `corpus/` to `.gitignore` (AC: 3)

- [x] Open `.gitignore` and add `corpus/` line (after the existing `data/ntsb_extracted/` entry)

### Task 2: Create document type classifier (AC: 2)

- [x] Create `scripts/build_corpus.py`
- [x] Implement `classify_document_type(title: str) -> str` function
  - Returns one of the 9 `DocumentType` values from `src/crossfire/shared/schemas/corpus.py`
  - Uses regex-based title matching (first match wins), following the pattern in `src/crossfire/generator/scraper/classifier.py` but with NEW taxonomy rules
  - Classification rules in priority order:
    1. `METEOROLOG|WEATHER STUDY|WEATHER FACTUAL` → `meteorology_report`
    2. `AIR TRAFFIC CONTROL|\\bATC\\b|CTAF TRANSCRIPT` → `atc_transcript`
    3. `OPERATIONAL? FACTORS|OPERATIONS GROUP` → `ops_group_report`
    4. `STRUCTURES GROUP|STRUCTURES FACTUAL` → `structures_analysis`
    5. `POWERPLANTS?\\b` → `powerplants_analysis`
    6. `MAINTENANCE RECORD` → `maintenance_record`
    7. `INTERVIEW|STATEMENT|DEPOSITION|TESTIMONY|WITNESS|RECORD OF CONVERSATION` → `witness_testimony`
    8. `PRELIMINARY|ORDER OF HEARING|EXHIBIT LIST|BOARD MEETING|STATEMENT OF PURPOSE|WITNESS LIST|DESIGNATION` → `preliminary_report`
    9. Everything else → `investigation_report` (catch-all: FDR, CVR, systems, survival, human performance, medical, airworthiness, performance studies, party submissions, etc.)
  - Import and validate against `DocumentType` literal from `crossfire.shared.schemas.corpus`

### Task 3: Build corpus directory structure (AC: 1, 4)

- [x] Implement `build_corpus(source: Path, target: Path) -> dict` function in `scripts/build_corpus.py`
  - Iterates over case directories in `data/ntsb_extracted/`
  - For each case with `.txt` files:
    - Creates `corpus/{NTSB_ID}/` directory
    - Copies ALL `.txt` files from source to target (use `shutil.copy2` to preserve metadata)
    - Does NOT copy `_extraction_meta.json` (extraction metadata, not source documents)
    - Reads `_extraction_meta.json` for document titles and word counts (used for manifest)
  - Copies ALL files regardless of quality `passed` status — AC4 requires no filtering
  - Log progress with loguru: one line per case, summary at end

### Task 4: Generate corpus manifest (AC: 2)

- [x] Implement manifest generation in `build_corpus()`
  - After building all case directories, write `corpus/manifest.json`
  - Manifest structure:
    ```json
    {
      "generated_at": "2026-04-10T...",
      "cases": [
        {
          "case_id": "DCA19FA089",
          "document_count": 27,
          "documents": [
            {
              "filename": "001_METEOROLOGY_FACTUAL_-_ADDENDUM_1.txt",
              "title": "METEOROLOGY FACTUAL - ADDENDUM 1",
              "document_type": "meteorology_report",
              "word_count": 6216
            }
          ],
          "type_distribution": {
            "meteorology_report": 3,
            "atc_transcript": 8,
            "investigation_report": 10
          }
        }
      ],
      "summary": {
        "total_cases": 5,
        "total_documents": 195,
        "document_types_found": ["investigation_report", "meteorology_report", ...]
      }
    }
    ```
  - Document titles come from `_extraction_meta.json` field `title`
  - Word counts come from `_extraction_meta.json` field `word_count`
  - `document_type` is computed by the classifier from Task 2
  - For `.txt` files not listed in `_extraction_meta.json`, use the filename (without numeric prefix and `.txt`) as the title
  - Write with `json.dumps(indent=2)` for readability

### Task 5: CLI entry point (AC: 1)

- [x] Implement `main()` in `scripts/build_corpus.py`
  - Follow the pattern from `scripts/scrape_ntsb.py`:
    - Add project root to `sys.path`
    - Configure loguru: `logger.remove()` then `logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}")`
  - Constants: `SOURCE = Path("data/ntsb_extracted")`, `TARGET = Path("corpus")`
  - Call `build_corpus(SOURCE, TARGET)`
  - Log summary: "Built corpus: N cases, M documents, K document types"
  - Add `if __name__ == "__main__": main()` guard

### Task 6: Write tests (AC: 1, 2, 3, 4)

- [x] Create `tests/test_build_corpus.py`
- [x] Test classifier with real document titles from extracted data:
  - `"METEOROLOGY FACTUAL - ADDENDUM 1"` → `meteorology_report`
  - `"METEOROLOGY ATTACHMENT 2 - DISPATCH STATEMENT"` → `meteorology_report`
  - `"WEATHER STUDY"` → `meteorology_report`
  - `"AIR TRAFFIC CONTROL FACTUAL REPORT"` → `atc_transcript`
  - `"AIR TRAFFIC CONTROL ATTACHMENT 1 INTERVIEW SUMMARIES"` → `atc_transcript` (ATC takes priority over INTERVIEW)
  - `"OPERATIONAL FACTORS FACTUAL REPORT"` → `ops_group_report`
  - `"OPERATIONS GROUP CHAIRMAN'S FACTUAL REPORT"` → `ops_group_report`
  - `"STRUCTURES GROUP CHAIRMAN'S FACTUAL REPORT"` → `structures_analysis`
  - `"POWERPLANTS GROUP FACTUAL REPORT"` → `powerplants_analysis`
  - `"MAINTENANCE RECORDS GROUP FACTUAL REPORT"` → `maintenance_record`
  - `"HUMAN PERFORMANCE ATTACHMENT 1 - INTERVIEW SUMMARIES"` → `witness_testimony`
  - `"RECORD OF CONVERSATION (PILOT FRIEND)"` → `witness_testimony`
  - `"COCKPIT VOICE RECORDER - GROUP CHAIRMAN'S FACTUAL REPORT"` → `investigation_report`
  - `"FLIGHT DATA RECORDER - SPECIALIST'S FACTUAL REPORT"` → `investigation_report`
  - `"HUMAN PERFORMANCE FACTUAL"` → `investigation_report`
  - `"MEDICAL FACTUAL REPORT"` → `investigation_report`
  - `"AIRPLANE PERFORMANCE STUDY"` → `investigation_report`
  - `"SURVIVAL FACTORS GROUP CHAIR'S FACTUAL REPORT"` → `investigation_report`
  - `"SYSTEMS GROUP CHAIRMAN'S FACTUAL REPORT"` → `investigation_report`
  - `"AIRWORTHINESS GROUP CHAIRMAN'S FACTUAL REPORT"` → `investigation_report`
- [x] Test build function with `tmp_path` fixture:
  - Create mock source directory with 2 cases, each with a few `.txt` files and `_extraction_meta.json`
  - Run `build_corpus()` on mock data
  - Assert target directories created with correct file counts
  - Assert `manifest.json` exists and is valid JSON
  - Assert manifest `cases` count matches
  - Assert no `_extraction_meta.json` in target directories
- [x] Test no-filtering: include a document with `passed: false` in mock `_extraction_meta.json` and verify it's still copied

### Task 7: Verify end-to-end (AC: all)

- [x] Run `python scripts/build_corpus.py`
- [x] Verify `corpus/` has 5 case directories (DCA19FA089, DCA19MA086, DCA24MA063, ERA18FA120, WPR19FA080)
- [x] Verify `corpus/manifest.json` contains all 5 cases with document type distributions
- [x] Verify each case directory file count matches `data/ntsb_extracted/` (minus `_extraction_meta.json`)
- [x] Verify `corpus/` is in `.gitignore`
- [x] Run `PYTHONPATH=src pytest tests/test_build_corpus.py -v`

## Dev Notes

### Architecture Compliance

- `corpus/` MUST be at **project root**, NOT inside `data/`. It is the INPUT to the agentic generation pipeline. `data/datasets/{version}/` is the OUTPUT. [Source: architecture.md#Project Structure]
- `corpus/` MUST be in `.gitignore` — raw source documents are not shipped. [Source: architecture.md#Gitignore]
- Hard boundary: `generation/` = bash scripts + plan document, `src/crossfire/` = pipeline + evaluation + shared schemas. This script lives in `scripts/` which is the utility home for one-off operations. [Source: architecture.md#Architectural Boundaries]
- Directory layout: `corpus/{source_id}/{case_id}/` (e.g., `corpus/ntsb/DCA19FA089/`, `corpus/grenfell/hearing_day_1/`, `corpus/copa/case_12345/`). Source-specific case IDs are the natural, stable, traceable identifiers.

### What to REUSE

| Existing Resource | Location | How to Use |
|---|---|---|
| `_extraction_meta.json` per case | `data/ntsb_extracted/{ID}/_extraction_meta.json` | Read for document titles, word counts. Fields: `documents[].title`, `documents[].word_count`, `documents[].item_number`, `documents[].passed` |
| Classifier pattern | `src/crossfire/generator/scraper/classifier.py` | Copy the regex-first-match-wins pattern. Do NOT import — it uses the old 8-type taxonomy |
| `Document.document_type` field | `src/crossfire/shared/schemas/corpus.py` | `document_type` is now a `str` field (not a fixed Literal enum) — source-specific types are validated per source, not globally |
| Script entry pattern | `scripts/scrape_ntsb.py` | Follow same structure: `sys.path` setup, loguru config, `main()` function |

### What to CREATE

| File | Purpose |
|---|---|
| `scripts/build_corpus.py` | Corpus builder script with classifier, builder, manifest generator |
| `tests/test_build_corpus.py` | Tests for classifier and build function |
| `corpus/` (gitignored) | Organized case directories + manifest (created by script) |

### What to MODIFY

| File | Change |
|---|---|
| `.gitignore` | Add `corpus/` line |

### Taxonomy Mapping (NTSB source — example of source-specific document types)

Document types are source-specific strings. For the NTSB source, the classifier maps real NTSB titles to these types (other sources will have their own type sets):

| NTSB Group / Document | DocumentType |
|---|---|
| Meteorology Group, Weather Study, Weather Factual | `meteorology_report` |
| Air Traffic Control, ATC transcripts, CTAF | `atc_transcript` |
| Operations Group, Operational Factors | `ops_group_report` |
| Structures Group | `structures_analysis` |
| Powerplants Group | `powerplants_analysis` |
| Maintenance Records Group | `maintenance_record` |
| Interviews, Statements, Depositions, Witness | `witness_testimony` |
| Preliminary Report, Hearing docs | `preliminary_report` |
| FDR, CVR, Systems, Survival, Human Performance, Medical, Airworthiness, Performance Study, Party Submissions, etc. | `investigation_report` (catch-all) |

### Available Cases (5 extracted, meets minimum requirement)

| Case ID | Raw PDFs | Extracted .txt | Key NTSB Groups Present |
|---|---|---|---|
| DCA19FA089 | 30 | 27 | Meteorology, ATC, Airport, Ops, Human Performance, CVR, FDR, Airworthiness, Medical |
| DCA19MA086 | 67 | 50 | Ops Group, Meteorology, ATC, Powerplants, Structures, Systems, CVR, Maintenance |
| DCA24MA063 | 92 | 65 | Hearing docs, Ops, Structures, Systems, Survival, Manufacturing, FDR |
| ERA18FA120 | 42 | 24 | Structures, Materials Lab, Meteorology, Witness interviews |
| WPR19FA080 | 28 | 24 | Weather, ATC, Witness, Maintenance, Airframe exam |

Three additional cases (CEN17MA183, ERA18MA099, ERA19FA034) have raw PDFs but no extracted text — they are out of scope for this story.

### Logging

All output via loguru. No `print()` statements. Pattern:

```python
from loguru import logger
logger.info(f"Processing case {case_id}: {len(txt_files)} documents")
```

### Project Structure Notes

After this story, the project root gains:

```
corpus/                         # NEW (gitignored)
  ntsb/                         # Source-specific directory
    DCA19FA089/                 # Case directories
      001_METEOROLOGY_FACTUAL_-_ADDENDUM_1.txt
      ...
    DCA19MA086/
      ...
    (3 more cases)
  grenfell/                     # Future: Grenfell Tower Inquiry source
  copa/                         # Future: Chicago COPA source
  manifest.json                 # Corpus inventory (all sources)
scripts/
  build_corpus.py               # NEW
tests/
  test_build_corpus.py          # NEW
```

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure] — corpus/ at project root, gitignored
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries] — generation vs. pipeline boundary
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2-NEW] — story requirements and acceptance criteria
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-09.md#Section 4] — agentic pivot rationale, minimum 5 cases
- [Source: _bmad-output/planning-artifacts/prd.md#FR1, FR5] — corpus processing and heterogeneous document preservation
- [Source: src/crossfire/shared/schemas/corpus.py] — canonical DocumentType (9 values)
- [Source: src/crossfire/generator/scraper/classifier.py] — regex classifier pattern (old taxonomy)
- [Source: data/ntsb_extracted/DCA19FA089/_extraction_meta.json] — extraction metadata structure

### Previous Story Intelligence

From Story 1-2 (Pydantic Schema Rewrite):
- `Document.source` field identifies the data source (e.g., "grenfell", "copa", "ntsb")
- `Document.document_type` is a `str` field (source-specific, not a fixed Literal enum)
- Test execution: `PYTHONPATH=src pytest tests/... -v`
- All 127 schema tests currently pass

From Story 1-1 (Project Scaffolding):
- `scripts/` directory exists with `__init__.py` and 4 scripts
- loguru, pydantic, pyyaml in `requirements.txt`
- `pyproject.toml` has `pythonpath = ["src", "."]`

From git history (last 5 commits):
- Story 6.1 implemented dataset generation scripts
- Epics 3-5 implemented injection, pipeline, evaluation
- Code follows consistent patterns: loguru logging, Pydantic schemas, `(result, error)` return tuples

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation, no debugging required.

### Completion Notes List

- Task 1: Added `corpus/` to `.gitignore` after `data/ntsb_extracted/`
- Task 2: Implemented `classify_document_type()` with 8 ordered regex rules + `investigation_report` catch-all. All outputs validated against `DocumentType` literal at module load time.
- Task 3: Implemented `build_corpus()` — iterates case dirs, copies all `.txt` files via `shutil.copy2`, reads `_extraction_meta.json` for metadata. No filtering (AC4).
- Task 4: Manifest generation integrated into `build_corpus()` — writes `corpus/manifest.json` with per-case documents, type distributions, and summary.
- Task 5: CLI entry point follows `scrape_ntsb.py` pattern — sys.path setup, loguru config, summary logging.
- Task 6: 24 tests — 20 parametrized classifier tests with real NTSB titles, 4 build function tests (directory creation, manifest structure, no-filtering, multi-case).
- Task 7: End-to-end verified — 5 cases, 190 documents, all 9 document types found, file counts match source.
- Full test suite: 229 tests pass (24 new + 205 existing). 10 pre-existing collection errors from Story 1-2 schema rewrite (unrelated).
- Multi-source generalization (2026-04-11):
  - Added `--source` CLI flag (AC1): `python scripts/build_corpus.py --source ntsb`
  - Directory layout now `corpus/{source_id}/{case_id}/` (AC1): e.g. `corpus/ntsb/DCA19FA089/`
  - Manifest includes `source_id` per case and top-level `sources` list (AC2)
  - Source registry (`SOURCE_DIRECTORIES`) maps source_id to raw data directory
  - Per-source classifier registry: NTSB uses regex rules, unknown sources use passthrough returning "document"
  - Manifest supports incremental multi-source builds (preserves other sources' cases)
  - 32 tests pass (8 new: passthrough classifier, source_id in manifest, different source layout, CLI flag tests)
  - Full suite: 402 passed, 3 skipped — no regressions

### Change Log

- 2026-04-11: Story 2.1-NEW implemented — corpus builder, classifier, manifest generator, tests
- 2026-04-11: Multi-source generalization — added --source CLI flag, corpus/{source_id}/{case_id}/ layout, per-source classifiers, source_id in manifest

### File List

- `.gitignore` (modified — added `corpus/`)
- `scripts/build_corpus.py` (modified — multi-source: --source CLI, source_id dir layout, per-source classifiers, source registry)
- `tests/test_build_corpus.py` (modified — 32 tests: added passthrough, source_id, different source, CLI flag tests)
- `corpus/` (gitignored — corpus/{source_id}/{case_id}/ layout + manifest.json, generated by script)
