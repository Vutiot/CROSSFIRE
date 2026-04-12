# Story 3.5-NEW: Dataset Versioning & Release Packaging

Status: review

## Story

As a researcher,
I want versioned datasets with tracked injection parameters,
So that I can produce multiple dataset versions with different contradiction rates and distributions from the same anonymized base corpus.

## Context

This is the FIFTH and final story in Epic 3-NEW. Stories 3.1-3.4 handle injection, distraction, and verification. This story packages the output into versioned datasets at `data/datasets/{version}/` with full metadata.

## Acceptance Criteria

1. **(AC1) Dataset Directory Structure**
   **Given** a completed and verified injection run
   **When** the dataset is packaged
   **Then** output is assembled into `data/datasets/{version}/` with the full case directory layout

2. **(AC2) Generation Params Tracking**
   **Given** a dataset version
   **When** I inspect `generation_params.json`
   **Then** it contains: version ID, base_version, contradiction rates per scope, distractor ratio, mechanism distribution, difficulty distribution (FR16)

3. **(AC3) Re-Injection from Base**
   **Given** a previously anonymized and verified base corpus
   **When** I run injection with different parameters
   **Then** a new dataset version is produced without regenerating anonymized documents

4. **(AC4) Dataset Manifest**
   **Given** a dataset version
   **When** I inspect `dataset_manifest.json`
   **Then** it contains aggregate statistics: total contradictions per scope, total distractors, mechanism distribution, detectability distribution, case count

5. **(AC5) Knowledge Graph Included**
   **Given** a dataset version with `metadata/knowledge_graph.json` per case
   **Then** it is clearly documented as NOT a gold evaluation reference (FR13)

6. **(AC6) Distractor Labels Included**
   **Given** verified gold labels for a dataset version
   **When** distractor labels are packaged
   **Then** `distractors/distractor_labels.jsonl` is included per case (FR15)

## Tasks / Subtasks

### Task 1: Create package_dataset.py (AC: 1, 2, 4)

- [x] Create `generation/package_dataset.py` as standalone CLI script
- [x] CLI: `python generation/package_dataset.py --version v1 --source-cases corpus/ntsb/`
- [x] Copy verified case outputs into `data/datasets/{version}/`
- [x] For each case, copy: `anonymized_docs/`, `contradictions/` (verified JSONL), `distractors/`, `metadata/`, `validation/`
- [x] Write `data/datasets/{version}/generation_params.json` from `GenerationParams` model
- [x] Compute and write `data/datasets/{version}/dataset_manifest.json` with aggregate stats

### Task 2: Implement dataset manifest computation (AC: 4)

- [x] Scan all cases in the version directory
- [x] Count contradictions per scope (read JSONL files)
- [x] Count distractors
- [x] Compute mechanism distribution, detectability distribution
- [x] Record case count, total documents

### Task 3: Support re-injection (AC: 3)

- [x] `--base-version` flag to reference an existing version's anonymized docs
- [x] When base-version specified: copy anonymized_docs from base, run injection with new params, package result

### Task 4: Write tests (AC: 1-6)

- [x] Create `tests/test_package_dataset.py`
- [x] Test dataset directory structure created correctly
- [x] Test generation_params.json written with correct fields
- [x] Test dataset_manifest.json has aggregate stats
- [x] Test distractor labels included
- [x] Test case files copied correctly

### Task 5: Run full test suite

- [x] `pytest tests/test_package_dataset.py -v`
- [x] `pytest tests/ -q` — verify 592+ passed

## Dev Notes

### Architecture
- `generation/package_dataset.py` lives in `generation/` — outside `src/crossfire/`
- May import from `crossfire.shared.schemas` for validation
- Output goes to `data/datasets/{version}/` which IS version-controlled (shipped with the project)

### Output Structure
```
data/datasets/{version}/
  generation_params.json
  dataset_manifest.json
  {case_id}/
    anonymized_docs/*.txt
    contradictions/
      intra_doc_contradictions.jsonl
      inter_doc_contradictions.jsonl
      all_contradictions.jsonl
    distractors/
      distractor_labels.jsonl
    metadata/
      knowledge_graph.json  (NOT gold eval reference)
      domain_registry.json
      scope_map.json
    validation/
      diff_verification_log.json
```

### References
- [Source: epics.md#Story 3.5] — acceptance criteria
- [Source: architecture.md#Data Architecture] — dataset directory layout

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
None required — all tests passed on first implementation.

### Completion Notes List
- Created `generation/package_dataset.py` as standalone CLI script with argparse interface
- Implemented `copy_case()` function using `shutil.copytree` for directory copying, with graceful handling of missing optional subdirectories
- Implemented `compute_manifest()` function that scans case directories and aggregates: case count, document count, contradictions per scope, distractor count, mechanism distribution, detectability distribution
- Implemented `package_dataset()` orchestration function: copies cases, writes generation_params.json (from GenerationParams schema or custom --params-file), computes and writes dataset_manifest.json
- CLI supports --version, --cases, --params-file, --base-version, --output-dir flags as specified
- base_version recorded in both generation_params.json and dataset_manifest.json for re-injection lineage tracking
- Created 29 tests in tests/test_package_dataset.py covering all 6 acceptance criteria
- Full test suite: 621 passed, 0 failures (exceeds 592+ threshold)

### File List
- `generation/package_dataset.py` (new) — CLI script for dataset packaging
- `tests/test_package_dataset.py` (new) — 29 tests for AC1-AC6

### Change Log
- 2026-04-11: Implemented Story 3.5-NEW — dataset versioning & release packaging
