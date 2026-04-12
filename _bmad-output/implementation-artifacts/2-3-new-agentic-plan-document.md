# Story 2.3-NEW: Agentic Plan Document

Status: review

## Story

As a researcher,
I want source-specific plan documents that drive Claude Code CLI sessions through anonymization, reformatting, and claim extraction for each data source,
So that the agentic pipeline produces consistently structured output from heterogeneous source documents across all sources.

## Context

This is the THIRD story in Epic 2-NEW (Corpus Processing & Anonymization). Story 2.1-NEW created the organized `corpus/{source_id}/{case_id}/` directory with source documents. Story 2.2-NEW created the chunking utility that splits documents into LLM-processable segments stored in `corpus/{source_id}/{case_id}/chunks/`.

This story creates the **agent plan documents** that Claude Code CLI sessions load as system prompts. Each source (Grenfell, COPA, NTSB) gets its own plan document with source-specific anonymization rules, entity handling, and document type mapping. The plans specify the **fan-out architecture**: Sonnet for per-chunk claim extraction, Opus for cross-document reasoning.

**Generation boundary:** These plan documents live in `generation/sources/{source_id}/` — deliberately outside `src/crossfire/`. Generation is CLI-driven by design (Claude Code CLI sessions), not a Python library. [Source: architecture.md#Architectural Boundaries]

**Downstream dependents:** Story 2.4 (bash wrapper scripts) will invoke Claude Code CLI sessions using these plans. Stories 3.1-3.5 (contradiction injection) consume the output.

## Acceptance Criteria

1. **(AC1) Source-Specific Plan Documents Exist**
   **Given** the `generation/sources/` directory
   **When** I inspect it
   **Then** plan documents exist at:
   - `generation/sources/ntsb/agent_plan.md`
   - `generation/sources/grenfell/agent_plan.md`
   - `generation/sources/copa/agent_plan.md`

2. **(AC2) Plan Instructs Four Processing Phases**
   **Given** a source-specific plan document
   **When** a Claude Code CLI session loads the plan as system prompt
   **Then** the plan instructs the agent to:
   1. Anonymize identifying information per source-specific rules
   2. Reformat documents preserving source-specific structure
   3. Extract factual claim triples with cross-references
   4. Output results in the case directory layout

3. **(AC3) Output Directory Structure**
   **Given** a source-specific plan document
   **When** it specifies output format
   **Then** anonymized documents are written as `.txt` files in `anonymized_docs/`
   **And** extracted claims are written as per-document JSON files in `original_claims/`
   **And** a knowledge graph JSON is assembled in `metadata/knowledge_graph.json`
   **And** domain registry and scope map are written to `metadata/`

4. **(AC4) Fan-Out Architecture Specified**
   **Given** a source-specific plan document
   **When** it specifies the processing approach
   **Then** it uses fan-out architecture: **Sonnet for per-chunk claim extraction**, **Opus for cross-document reasoning** (FR1, NFR13)

5. **(AC5) Source-Specific Handling**
   **Given** a source-specific plan document
   **When** it specifies source-specific handling
   **Then** it defines:
   - **Grenfell:** Party anonymization for 8 cladding inquiry parties (Arconic, Celotex, Kingspan, RBKC TMO, London Fire Brigade, etc.), hearing transcript structure preservation
   - **COPA:** Officer/witness anonymization, tactical/forensic document structure
   - **NTSB:** Preserves natural cross-document entity variation, aviation-specific anonymization (flight numbers, tail numbers, airports)

## Tasks / Subtasks

### Task 1: Create source directory structure (AC: 1)

- [x] Create `generation/sources/` directory
- [x] Create `generation/sources/ntsb/`
- [x] Create `generation/sources/grenfell/`
- [x] Create `generation/sources/copa/`

### Task 2: Write NTSB agent plan (AC: 1, 2, 3, 4, 5)

- [x] Create `generation/sources/ntsb/agent_plan.md`
- [x] Define 4 processing phases: anonymize, reformat, extract claims, output
- [x] Specify fan-out architecture: Sonnet (extraction) + Opus (cross-doc reasoning)
- [x] Specify NTSB-specific anonymization rules:
  - Anonymize tail numbers (N-numbers) → generic identifiers
  - Anonymize airline names → "Airline-A", "Airline-B"
  - Anonymize airport identifiers → generic codes
  - Anonymize personnel names → role-based identifiers
  - Preserve natural cross-document entity variation (same entity may appear differently across reports — this is an intended feature for entity resolution testing)
- [x] Specify output structure: `anonymized_docs/`, `original_claims/`, `metadata/`
- [x] Include chunk manifest reading: plan should reference `chunks/chunk_manifest.json` for fan-out processing
- [x] Define NTSB document type mapping (9 types from `build_corpus.py` classifier)

### Task 3: Write Grenfell agent plan (AC: 1, 2, 3, 4, 5)

- [x] Create `generation/sources/grenfell/agent_plan.md`
- [x] Specify Grenfell-specific anonymization rules:
  - Anonymize 8 cladding inquiry parties: Arconic, Celotex, Kingspan, RBKC TMO, London Fire Brigade, BRE, Exova, Studio E → "Company-A" through "Company-H"
  - Anonymize witness names → "Witness-1", "Witness-2" etc.
  - Anonymize specific locations (Grenfell Tower, Lancaster West Estate) → generic names
  - Preserve party-vs-party testimony structure (key for cross-party entity boundary testing)
- [x] Specify hearing transcript structure preservation (Q&A format, page/line references)
- [x] Specify fan-out: Sonnet for per-chunk extraction, Opus for cross-party reasoning
- [x] Specify output structure matching case directory layout

### Task 4: Write COPA agent plan (AC: 1, 2, 3, 4, 5)

- [x] Create `generation/sources/copa/agent_plan.md`
- [x] Specify COPA-specific anonymization rules:
  - Anonymize officer names/badge numbers → "Officer-1", "Officer-2"
  - Anonymize complainant/witness names → "Witness-A", "Subject-B"
  - Anonymize specific addresses and locations → generic neighborhoods
  - Anonymize case-specific identifiers (RD numbers, log numbers)
- [x] Specify forensic document structure preservation (TRR format, FSR format, OCIR format)
- [x] Specify fan-out: Sonnet for per-document extraction, Opus for cross-vantage reasoning
- [x] Specify output structure matching case directory layout

### Task 5: Write tests (AC: 1-5)

- [x] Create `tests/test_agent_plans.py`
- [x] Test plan files exist at expected paths
- [x] Test each plan contains required sections (anonymization, extraction, output format, fan-out)
- [x] Test each plan references Sonnet and Opus models
- [x] Test each plan specifies the 4 processing phases
- [x] Test each plan specifies source-specific anonymization rules

### Task 6: Verify end-to-end (AC: all)

- [x] Verify all 3 plan documents exist and are readable
- [x] Verify plans reference the chunk manifest for fan-out input
- [x] Verify output directory structure matches architecture spec
- [x] Run `pytest tests/test_agent_plans.py -v`
- [x] Run `pytest tests/ -q` — verify no regressions

## Dev Notes

### Architecture Compliance

- **Generation boundary is CRITICAL.** Plan documents live in `generation/sources/{source_id}/`, NOT in `src/crossfire/`. Generation is CLI-driven (Claude Code CLI), not a Python library. [Source: architecture.md#Architectural Boundaries, line 73]
- `generation/` directory is NOT a Python package — no `__init__.py`. [Source: architecture.md#Project Structure]
- Plan documents are **markdown files** loaded as system prompts by Claude Code CLI sessions. They are NOT Python code.
- Generation LLM costs are tracked by Claude Code CLI session logs, NOT by the Python `llm.py` wrapper. [Source: architecture.md#LLM Integration, line 288]

### Fan-Out Architecture (NFR13)

The fan-out architecture is the cost management strategy specified in the PRD:

| Phase | Model | Purpose | Cost Tier |
|---|---|---|---|
| Per-chunk claim extraction | **Claude Sonnet** (`claude-sonnet-4-20250514`) | Extract factual claims from each chunk independently | Low (~$3/1M input) |
| Cross-document reasoning | **Claude Opus** (`claude-opus-4-20250514`) | Assemble knowledge graph, identify cross-references, resolve entities | High (~$15/1M input) |

**Cost impact:** Fan-out with Sonnet for extraction is ~1/10th the cost of using Opus for everything. [Source: prd.md line 194, 361]

The plan documents MUST specify which model to use for each phase. The bash wrapper scripts (Story 2.4) will pass the model parameter to Claude Code CLI.

### What Exists Already

| Resource | Location | Relevance |
|---|---|---|
| NTSB corpus | `corpus/ntsb/` (5 cases, 190 docs) | Input for NTSB plan |
| Grenfell corpus | `corpus/grenfell/` (2 modules, 30 transcripts) | Input for Grenfell plan |
| COPA corpus | `corpus/copa/` (7 cases, 23 docs) | Input for COPA plan |
| Chunk manifests | `corpus/{source_id}/{case_id}/chunks/chunk_manifest.json` | Fan-out input mapping |
| Draft agent plan | `docs/crossfire_agent_plan.md` | NTSB-specific draft plan (pre-multi-source) — use as reference but create source-specific versions |
| NTSB classifier | `scripts/build_corpus.py:classify_ntsb()` | Document type rules for NTSB |
| Grenfell classifier | `scripts/build_corpus.py:classify_grenfell()` | Document type rules for Grenfell |
| COPA classifier | `scripts/build_corpus.py:classify_copa()` | Document type rules for COPA |
| GenerationParams schema | `src/crossfire/shared/schemas/config.py` | Has `extraction_model` and `reasoning_model` fields |
| KnowledgeGraphClaim schema | `src/crossfire/shared/schemas/knowledge_graph.py` | Output format for extracted claims |
| ContradictionLabel schema | `src/crossfire/shared/schemas/contradictions.py` | Downstream label format |
| AnonymizationMapping schema | `src/crossfire/shared/schemas/anonymization.py` | Anonymization tracking format |
| DomainRegistry schema | `src/crossfire/shared/schemas/domain_registry.py` | Domain entity tracking format |
| ScopeMap schema | `src/crossfire/shared/schemas/scope_map.py` | Document scope classification format |

### What to CREATE

| File | Purpose |
|---|---|
| `generation/sources/ntsb/agent_plan.md` | NTSB-specific Claude Code CLI system prompt |
| `generation/sources/grenfell/agent_plan.md` | Grenfell-specific Claude Code CLI system prompt |
| `generation/sources/copa/agent_plan.md` | COPA-specific Claude Code CLI system prompt |
| `tests/test_agent_plans.py` | Validation tests for plan document structure |

### What NOT to Create or Modify

- Do NOT create Python code in `generation/sources/` — these are markdown plan documents
- Do NOT modify `src/crossfire/` — respect the generation boundary
- Do NOT modify the existing `docs/crossfire_agent_plan.md` — it's a reference draft
- Do NOT create `__init__.py` anywhere in `generation/`

### Plan Document Structure

Each agent plan should follow this structure:

```markdown
# CROSSFIRE: {Source Name} Agentic Processing Plan

## Overview
- Source description
- Document types
- Processing objectives

## Phase 1: Anonymization (Model: Sonnet)
- Source-specific PII rules
- Entity replacement strategy
- Anonymization mapping output format (AnonymizationMapping schema)

## Phase 2: Reformatting (Model: Sonnet)
- Document structure preservation rules
- Source-specific format handling
- Output: anonymized_docs/*.txt

## Phase 3: Claim Extraction (Model: Sonnet, per-chunk fan-out)
- Read chunk_manifest.json for chunk listing
- Per-chunk claim extraction prompt
- Claim triple format (subject, predicate, object)
- Output: original_claims/{document_id}.json
- Cross-reference identification
- Output: metadata/knowledge_graph.json

## Phase 4: Cross-Document Reasoning (Model: Opus)
- Knowledge graph assembly from per-chunk claims
- Entity resolution across documents
- Cross-reference validation
- Domain registry: metadata/domain_registry.json
- Scope map: metadata/scope_map.json

## Output Directory Layout
- anonymized_docs/
- original_claims/
- metadata/
  - knowledge_graph.json
  - domain_registry.json
  - scope_map.json
  - entity_mapping.json (anonymization mappings)
```

### Previous Story Intelligence

From Story 2.2-NEW (Document Chunking & Manifest):
- Chunk files at `corpus/{source_id}/{case_id}/chunks/` with `_chunk_NNN.txt` naming
- `chunk_manifest.json` maps each chunk back to source document with `char_start`/`char_end` offsets
- Default chunk size: ~800 words (Sonnet's effective processing window)
- Chunking is source-agnostic — plans consume chunks regardless of source

From Story 2.1-NEW (Source Corpus Acquisition):
- `corpus/{source_id}/{case_id}/` layout with multi-source manifest at `corpus/manifest.json`
- 3 sources registered: ntsb, grenfell, copa
- Per-source classifiers in `build_corpus.py`
- Source-specific document types (strings, not fixed enum)

From code review findings:
- Current `src/crossfire/generator/injector.py` hardcodes `gpt-4o-mini` — WRONG. Plans must specify Claude models.
- `GenerationParams` now has `extraction_model` and `reasoning_model` fields
- PRD line 279: "Generation dependency: Claude Code CLI with access to Sonnet and Opus models"
- Architecture line 73: "Hard boundary between generation tooling (bash scripts, plan documents, Claude Code CLI) and the evaluable Python package"

### Test Strategy

Tests should validate plan document structure and content, not execution:
- File existence at expected paths
- Required section presence (grep for headers)
- Model specification (plans must mention Sonnet and Opus)
- Source-specific anonymization rules present
- Output directory structure specified
- Fan-out architecture described

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2-NEW, Story 2.3] — acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries, line 73] — generation boundary
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure, lines 96-125] — directory layout
- [Source: _bmad-output/planning-artifacts/architecture.md#LLM Integration, line 282-288] — generation uses CLI, not wrapper
- [Source: _bmad-output/planning-artifacts/prd.md#NFR13, lines 194, 279, 361, 443] — fan-out architecture, cost management
- [Source: docs/crossfire_agent_plan.md] — draft NTSB-specific agent plan (reference only)
- [Source: src/crossfire/shared/schemas/config.py] — GenerationParams with extraction_model/reasoning_model
- [Source: src/crossfire/shared/schemas/knowledge_graph.py] — KnowledgeGraphClaim, CrossReference
- [Source: src/crossfire/shared/schemas/anonymization.py] — AnonymizationMapping
- [Source: src/crossfire/shared/schemas/domain_registry.py] — DomainEntry, DomainRegistry
- [Source: src/crossfire/shared/schemas/scope_map.py] — ScopeMap, ScopeMapEntry

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — all tests passed on first run.

### Completion Notes List

- Created 3 source-specific agent plan documents (NTSB, Grenfell, COPA) as markdown files in `generation/sources/{source_id}/agent_plan.md`
- Each plan specifies 4 processing phases: Anonymization (Sonnet), Reformatting (Sonnet), Per-Chunk Claim Extraction (Sonnet fan-out), Cross-Document Reasoning (Opus)
- NTSB plan: aviation-specific anonymization (N-numbers, airlines, airports, role-based personnel), 9 document types from classifier, cross-document entity variation preserved
- Grenfell plan: 8 cladding inquiry party anonymization (Arconic->Company-A through Studio E->Firm-H), hearing transcript Q&A structure preservation, party-vs-party testimony structure
- COPA plan: officer/badge/complainant/witness anonymization, generic neighborhood addresses, case identifier anonymization, TRR/FSR/OCIR document structure preservation
- All plans reference chunk_manifest.json for fan-out input and specify output conforming to project schemas (KnowledgeGraphClaim, CrossReference, AnonymizationMapping, DomainRegistry, ScopeMap)
- 63 tests in test_agent_plans.py covering file existence, phase structure, model specifications, output directory layout, source-specific rules, and schema conformance
- Full test suite: 483 passed, 0 failures

### File List

- `generation/sources/ntsb/agent_plan.md` (new)
- `generation/sources/grenfell/agent_plan.md` (new)
- `generation/sources/copa/agent_plan.md` (new)
- `tests/test_agent_plans.py` (new)

### Change Log

- 2026-04-11: Created 3 source-specific agent plan documents and validation test suite (63 tests). All acceptance criteria satisfied.
