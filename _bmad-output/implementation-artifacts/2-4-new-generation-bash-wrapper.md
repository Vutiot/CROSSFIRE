# Story 2.4-NEW: Generation Bash Wrapper Scripts

Status: review

## Story

As a researcher,
I want bash scripts that orchestrate Claude Code CLI sessions for corpus processing across any source type,
So that I can generate one case or all cases for any source with a single command.

## Context

This is the FOURTH and final story in Epic 2-NEW. Story 2.1-NEW created the corpus directory, Story 2.2-NEW created the chunking utility, Story 2.3-NEW created source-specific agent plan documents. This story creates the bash wrapper scripts that tie everything together — invoking Claude Code CLI sessions with the appropriate plan document for each source and case.

**Generation boundary:** These scripts live in `generation/` at project root. They invoke Claude Code CLI externally — they do NOT import from `src/crossfire/`. [Source: architecture.md#Architectural Boundaries]

**Fan-out cost model:** Sonnet for per-chunk extraction (~$3/1M tokens), Opus for cross-document reasoning (~$15/1M tokens). Scripts should log approximate cost per case from Claude Code CLI session output.

## Acceptance Criteria

1. **(AC1) Per-Case Generation Script**
   **Given** `generation/generate_case.sh` exists
   **When** I run `./generation/generate_case.sh --source grenfell corpus/grenfell/module_1_cladding/`
   **Then** it loads the source-specific plan document from `generation/sources/grenfell/agent_plan.md` and invokes a Claude Code CLI session against the chunked source files for that case
   **And** output is written to a staging directory following the case directory layout

2. **(AC2) All-Cases Generation Script**
   **Given** `generation/generate_all.sh` exists
   **When** I run `./generation/generate_all.sh --source ntsb`
   **Then** it iterates over all case directories in `corpus/ntsb/` and runs `generate_case.sh` for each
   **And** running without `--source` iterates over all sources and all cases

3. **(AC3) Graceful Failure Handling**
   **Given** a generation run
   **When** a Claude Code CLI session fails for a case
   **Then** the error is logged and the outer loop continues to the next case — no silent failures, no accumulated charges from retries

4. **(AC4) Output Directory Structure**
   **Given** a completed generation run
   **When** I inspect the output
   **Then** each processed case directory contains `anonymized_docs/`, `original_claims/`, and `metadata/` subdirectories matching the architecture spec

5. **(AC5) Cost Summary**
   **Given** a generation run
   **When** it completes
   **Then** a summary is printed showing: cases processed, cases failed, and approximate cost per case

## Tasks / Subtasks

### Task 1: Create generate_case.sh (AC: 1, 3, 4)

- [x] Create `generation/generate_case.sh` with `#!/usr/bin/env bash` and `set -euo pipefail`
- [x] Parse CLI arguments: `--source SOURCE_ID` (required) and `CASE_DIR` (positional, required)
- [x] Validate that `CASE_DIR` exists and is a directory
- [x] Validate that the source plan exists at `generation/sources/${SOURCE_ID}/agent_plan.md`
- [x] Check that chunks exist at `${CASE_DIR}/chunks/chunk_manifest.json` — if not, run chunking first: `python generation/chunk_documents.py --case "${CASE_DIR}"`
- [x] Invoke Claude Code CLI with the plan document:
  ```bash
  claude --print --system-prompt "$(cat generation/sources/${SOURCE_ID}/agent_plan.md)" \
    --message "Process case directory: ${CASE_DIR}" \
    --model claude-sonnet-4-20250514
  ```
  (The plan document itself specifies when to use Opus for Phase 4)
- [x] Create output staging directory structure if needed: `${CASE_DIR}/anonymized_docs/`, `${CASE_DIR}/original_claims/`, `${CASE_DIR}/metadata/`
- [x] Log success/failure with case ID and timing
- [x] On failure: log error message, exit with non-zero status (caller handles continuation)
- [x] Make script executable: `chmod +x generation/generate_case.sh`

### Task 2: Create generate_all.sh (AC: 2, 3, 5)

- [x] Create `generation/generate_all.sh` with `#!/usr/bin/env bash` and `set -euo pipefail`
- [x] Parse CLI arguments: `--source SOURCE_ID` (optional — if omitted, iterate all sources)
- [x] Discover sources from `generation/sources/*/agent_plan.md` glob pattern
- [x] For each source, discover cases from `corpus/${SOURCE_ID}/*/` directories
- [x] For each case, call `./generation/generate_case.sh --source ${SOURCE_ID} ${CASE_DIR}`
- [x] Track per-case results: success/failure count, timing, cost estimate
- [x] On per-case failure: log warning, increment failure counter, continue to next case (AC3)
- [x] Print final summary: total cases, successes, failures, total time, estimated total cost (AC5)
- [x] Make script executable: `chmod +x generation/generate_all.sh`

### Task 3: Create dry-run mode (AC: 5)

- [x] Add `--dry-run` flag to both scripts
- [x] In dry-run mode: list cases that would be processed, estimate chunk counts, estimate cost, but do NOT invoke Claude Code CLI
- [x] Useful for cost estimation before committing to a full generation run

### Task 4: Write tests (AC: 1-5)

- [x] Create `tests/test_generation_scripts.py`
- [x] Test scripts exist and are executable
- [x] Test `generate_case.sh --help` or missing args produces usage message
- [x] Test `generate_all.sh --help` or missing args produces usage message
- [x] Test `--dry-run` mode lists cases without invoking CLI
- [x] Test source discovery from `generation/sources/*/agent_plan.md`
- [x] Test case discovery from `corpus/{source_id}/*/` pattern

### Task 5: Verify end-to-end (AC: all)

- [x] Run `./generation/generate_all.sh --dry-run` to verify source/case discovery
- [x] Run `./generation/generate_case.sh --source ntsb --dry-run corpus/ntsb/WPR19FA080/` to verify per-case logic
- [x] Run `pytest tests/test_generation_scripts.py -v`
- [x] Run `pytest tests/ -q` — verify no regressions

## Dev Notes

### Architecture Compliance

- Scripts live in `generation/` — outside `src/crossfire/`. [Source: architecture.md#Generation Boundary]
- Scripts are **bash**, not Python. They orchestrate Claude Code CLI sessions externally.
- Generation costs tracked by CLI session logs, NOT by Python `llm.py` wrapper. [Source: architecture.md#LLM Integration]
- Scripts may call `python generation/chunk_documents.py` for chunking — this is an allowed cross-script dependency within `generation/`.
- Scripts MUST NOT import from `src/crossfire/` (bash scripts don't import Python anyway).

### Claude Code CLI Invocation

The `claude` CLI tool should be invoked with:
```bash
claude --print \
  --system-prompt "$(cat generation/sources/${SOURCE_ID}/agent_plan.md)" \
  --message "Process case: ${CASE_DIR}. Chunks at: ${CASE_DIR}/chunks/chunk_manifest.json" \
  --model claude-sonnet-4-20250514
```

Key flags:
- `--print` — output to stdout (non-interactive)
- `--system-prompt` — load the agent plan as system prompt
- `--model` — start with Sonnet; plan document instructs when to use Opus for Phase 4
- The plan document itself specifies the 4-phase pipeline and model switching

### What Exists Already

| Resource | Location | Relevance |
|---|---|---|
| NTSB agent plan | `generation/sources/ntsb/agent_plan.md` | System prompt for NTSB CLI sessions |
| Grenfell agent plan | `generation/sources/grenfell/agent_plan.md` | System prompt for Grenfell CLI sessions |
| COPA agent plan | `generation/sources/copa/agent_plan.md` | System prompt for COPA CLI sessions |
| Chunking utility | `generation/chunk_documents.py` | Pre-chunking step called by wrapper |
| Corpus structure | `corpus/{source_id}/{case_id}/` | Input directories for generation |
| Chunk manifests | `corpus/{source_id}/{case_id}/chunks/chunk_manifest.json` | Fan-out input for CLI sessions |

### What to CREATE

| File | Purpose |
|---|---|
| `generation/generate_case.sh` | Per-case Claude Code CLI orchestration |
| `generation/generate_all.sh` | Multi-case/multi-source batch orchestration |
| `tests/test_generation_scripts.py` | Script validation tests |

### Previous Story Intelligence

From Story 2.3-NEW:
- Agent plans at `generation/sources/{source_id}/agent_plan.md` for ntsb, grenfell, copa
- Plans specify 4 phases with Sonnet (Phases 1-3) and Opus (Phase 4)
- Plans reference `chunks/chunk_manifest.json` for fan-out input

From Story 2.2-NEW:
- Chunking at `generation/chunk_documents.py --case <path>`
- Chunks stored in `{case_dir}/chunks/` with `chunk_manifest.json`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2-NEW, Story 2.4] — acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#Generation Boundary] — scripts in generation/, not src/
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure, lines 96-125] — directory layout
- [Source: _bmad-output/planning-artifacts/prd.md line 254] — "Generation is CLI-driven by design (Claude Code CLI sessions)"
- [Source: _bmad-output/planning-artifacts/prd.md line 279] — "Generation dependency: Claude Code CLI with access to Sonnet and Opus models"

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

No debug issues encountered. All scripts implemented and tested in a single pass.

### Completion Notes List

- Created `generation/generate_case.sh` — per-case Claude Code CLI orchestration with argument parsing, validation, chunk auto-generation, output directory creation, dry-run mode, and timing/logging.
- Created `generation/generate_all.sh` — multi-source/multi-case batch orchestration with source discovery from `generation/sources/*/agent_plan.md`, case discovery from `corpus/{source_id}/*/`, graceful per-case failure handling, and summary reporting.
- Both scripts use `set -euo pipefail`, have `--help` usage messages, and support `--dry-run`.
- Created `tests/test_generation_scripts.py` with 32 tests covering: script existence/executability, shebang/strict mode, argument validation, source discovery (ntsb/grenfell/copa), case discovery, and dry-run mode behavior.
- Dry-run verified: `generate_all.sh --dry-run` discovers 3 sources, 14 cases (7 copa, 2 grenfell, 5 ntsb).
- Full test suite: 515 passed, 0 failed (no regressions).

### File List

- `generation/generate_case.sh` (new) — per-case CLI orchestration
- `generation/generate_all.sh` (new) — batch multi-source orchestration
- `tests/test_generation_scripts.py` (new) — 32 tests for wrapper scripts
- `_bmad-output/implementation-artifacts/2-4-new-generation-bash-wrapper.md` (modified) — story status updates
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified) — status tracking

### Change Log

- 2026-04-11: Implemented Story 2.4-NEW — generation bash wrapper scripts (generate_case.sh, generate_all.sh, tests)
