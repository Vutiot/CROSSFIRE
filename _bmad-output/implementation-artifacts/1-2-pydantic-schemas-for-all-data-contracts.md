# Story 1.2: Pydantic Schemas for All Data Contracts

Status: in-progress

## Story

As a developer,
I want all data contracts defined as Pydantic models,
so that every component produces and consumes validated, type-safe data structures.

## Acceptance Criteria

1. `corpus.py` exports `Document` and `SubcorpusMetadata` models with fields for document_type, subcorpus_id, reliability_signal, and content
2. `entities.py` exports `EntityNode`, `EntityEdge`, and `EntityGraph` models serializable to NetworkX adjacency JSON
3. `incoherences.py` exports `IncoherenceLabel` with scope, mechanism, detectability, system_affinity, and document_references fields, plus `DistractorLabel` with same structure
4. `reports.py` exports `DetectedIncoherence` and `PipelineReport` with evidence_references and confidence fields
5. `evaluation.py` exports `ScopeResult`, `StageResult`, and `EvaluationResult` with per-scope and per-stage breakdowns
6. `config.py` exports `GeneratorConfig`, `PipelineConfig`, and `PresetConfig` matching YAML preset structure
7. All models serialize to snake_case JSON and deserialize back without data loss

## Tasks / Subtasks

- [x] Task 1: Create `src/crossfire/shared/schemas/config.py` (AC: #6)
  - [x] Define `ScopeDistribution` sub-model with `intra_doc`, `intra_corpus`, `inter_corpus` float fields summing to 1.0
  - [x] Define `DetectabilityDistribution` sub-model with `single_hop`, `multi_hop`, `entity_resolution` float fields summing to 1.0
  - [x] Define `IncoherenceConfig` sub-model with scope_distribution, mechanism, detectability_distribution, system_affinity, count fields
  - [x] Define `PresetConfig` with all fields matching existing YAML presets (name, description, master_seed, subcorpora_count, docs_per_subcorpus, connectivity_level, doc_type_mix, incoherences, distractor_ratio)
  - [x] Define `GeneratorConfig` extending PresetConfig with output_dir and dry_run fields
  - [x] Define `PipelineConfig` with mode, corpus_path, output_dir fields
  - [x] Write tests: load each existing preset YAML, parse into PresetConfig, round-trip serialize/deserialize

- [x] Task 2: Create `src/crossfire/shared/schemas/corpus.py` (AC: #1)
  - [x] Define `Document` model with id (str), document_type (Literal of 8 types), subcorpus_id (str), reliability_signal (float 0-1), content (str)
  - [x] Define `SubcorpusMetadata` model with subcorpus_id (str), document_count (int), document_types (list[str])
  - [x] Write tests: create, serialize to JSON, deserialize back, verify snake_case field names

- [x] Task 3: Create `src/crossfire/shared/schemas/entities.py` (AC: #2)
  - [x] Define `EntityNode` with id (str), entity_type (str), canonical_name (str), aliases (list[str]), subcorpus_memberships (list[str])
  - [x] Define `EntityEdge` with source (str), target (str), relationship_type (str)
  - [x] Define `EntityGraph` with nodes (list[EntityNode]), edges (list[EntityEdge])
  - [x] Implement `to_networkx()` method on EntityGraph that converts to NetworkX graph
  - [x] Implement `from_networkx()` classmethod on EntityGraph that constructs from NetworkX graph
  - [x] Write tests: create EntityGraph, convert to NetworkX, convert back, verify lossless round-trip

- [x] Task 4: Create `src/crossfire/shared/schemas/incoherences.py` (AC: #3)
  - [x] Define `IncoherenceLabel` with id, scope (Literal), mechanism (Literal), detectability (Literal), system_affinity (Literal), document_references (list[str]), modified_fact (str), original_fact (str)
  - [x] Define `DistractorLabel` with id, scope, document_references (list[str]), divergence_type (str), description (str)
  - [x] Write tests: create instances, serialize, verify all fields present in JSON output

- [x] Task 5: Create `src/crossfire/shared/schemas/reports.py` (AC: #4)
  - [x] Define `DetectedIncoherence` with id (str), evidence_references (list[str]), confidence (float 0-1), description (str)
  - [x] Define `PipelineReport` with pipeline_mode (str), corpus_path (str), detections (list[DetectedIncoherence]), timestamp (str)
  - [x] Write tests: create PipelineReport with detections, serialize/deserialize round-trip

- [x] Task 6: Create `src/crossfire/shared/schemas/evaluation.py` (AC: #5)
  - [x] Define `ScopeResult` with scope (str), precision (float), recall (float), f1 (float), partial_credit_score (float)
  - [x] Define `StageResult` with stage (str), precision (float), recall (float), f1 (float)
  - [x] Define `EvaluationResult` with overall_precision, overall_recall, overall_f1 (floats), per_scope (list[ScopeResult]), per_stage (list[StageResult])
  - [x] Write tests: create nested EvaluationResult, serialize/deserialize, verify structure

- [x] Task 7: Update `src/crossfire/shared/schemas/__init__.py` and verify (AC: #7)
  - [x] Re-export all public models from `__init__.py` for convenient imports
  - [x] Write a comprehensive round-trip test for every model: create → JSON → back → assert equal
  - [x] Verify all JSON output uses snake_case field names (no camelCase aliasing)
  - [x] Run full test suite — no regressions

## Dev Notes

### Architecture Compliance (CRITICAL)

All schemas MUST follow the architecture document exactly. These are the data contracts that every other component depends on.

**Schema location:** `src/crossfire/shared/schemas/` — already created in Story 1.1 with empty `__init__.py`.
[Source: architecture.md#Schema Enforcement]

**Pydantic enforcement rule:** "Every output format has a corresponding Pydantic model. Serialization/deserialization always goes through Pydantic — no raw dict construction."
[Source: architecture.md#Schema Enforcement]

**Naming rule:** All JSON output fields use `snake_case`. "Pydantic models serialize to snake_case by default — no aliasing needed."
[Source: architecture.md#Naming Patterns]

**Constraint example from architecture:** `connectivity_level: Literal[0, 1, 2, 3]`
[Source: architecture.md#Schema Enforcement]

### Exact Field Specifications

#### config.py — PresetConfig MUST match existing YAML presets

The 4 preset YAML files created in Story 1.1 (`configs/presets/default.yaml`, etc.) define the exact structure that `PresetConfig` must parse. Here is the default.yaml structure:

```yaml
name: default
description: "Default benchmark configuration — 5 subcorpora, connectivity 2, balanced incoherences"
master_seed: 42
subcorpora_count: 5
docs_per_subcorpus: 80
connectivity_level: 2
doc_type_mix: "balanced"
incoherences:
  scope_distribution:
    intra_doc: 0.2
    intra_corpus: 0.5
    inter_corpus: 0.3
  mechanism: "uniform"
  detectability_distribution:
    single_hop: 0.3
    multi_hop: 0.5
    entity_resolution: 0.2
  system_affinity: "balanced"
  count: "auto"
distractor_ratio: 0.3
```

Critical: `count` field is `str | int` — it can be `"auto"` (string) or a fixed integer. Use `Union[str, int]` or Pydantic's discriminated approach.

#### corpus.py — Document types from architecture

The 8 document types: `investigation_report`, `technical_analysis`, `witness_testimony`, `regulatory_filing`, `press_coverage`, `expert_deposition`, `internal_memo`, `preliminary_report`
[Source: epics.md#Story 2.2, product-brief-CROSSFIRE-distillate.md#Document Type Taxonomy]

#### entities.py — NetworkX serialization

`EntityGraph` must convert to/from NetworkX format. Use `networkx.node_link_data()` and `networkx.node_link_graph()` for JSON-compatible serialization. Entity nodes include attributes: type, canonical_name, aliases, subcorpus_memberships.
[Source: architecture.md#Data Architecture, epics.md#Story 2.3]

#### incoherences.py — 4D design space enums

Scope: `intra_doc`, `intra_corpus`, `inter_corpus`
Mechanism: `numeric_drift`, `entity_swap`, `causal_inversion`, `temporal_contradiction`, `omission_based_implicit`, `temporal_revision_conflict`
Detectability: `single_hop`, `multi_hop`, `entity_resolution_dependent`
System affinity: `balanced`, `graph_favoring`, `agentic_favoring`
[Source: product-brief-CROSSFIRE-distillate.md#Incoherence Design Space, epics.md#Story 3.1]

#### reports.py — Standardized across pipeline modes

Pipeline reports must use a standardized format enabling cross-pipeline comparison (FR20). DetectedIncoherence needs evidence_references (list of document IDs) and confidence (float).
[Source: architecture.md#Data Architecture, epics.md#Story 4.1]

#### evaluation.py — Two-layer evaluation

ScopeResult covers: intra-document, intra-subcorpus, inter-subcorpus (FR25).
StageResult covers: entity_resolution, graph_construction, scanning (FR26).
EvaluationResult aggregates both plus overall metrics.
[Source: architecture.md#Two-Layer Evaluation, epics.md#Stories 5.1-5.3]

### Previous Story (1.1) Learnings

- Project structure exists with `src/crossfire/shared/schemas/__init__.py` (empty)
- All dependencies including `pydantic` are installed via `requirements.txt`
- Tests run with `PYTHONPATH=src pytest` from project root
- Test directory `tests/shared/` exists (with `.gitkeep`)
- No `pyproject.toml` — `PYTHONPATH=src` is required for imports
- No linting/type-checking configured — skip type annotations beyond what Pydantic requires

### Anti-Patterns to Avoid

- Do NOT implement any business logic in schema models — these are pure data contracts
- Do NOT add computed properties beyond serialization helpers (to_networkx/from_networkx)
- Do NOT add custom validators that enforce cross-field business rules — keep models simple, validation happens at component boundaries
- Do NOT use `model_config = ConfigDict(alias_generator=to_camel)` or any camelCase aliasing
- Do NOT use `Field(alias=...)` for any field — snake_case by default
- Do NOT import or use loguru in schema files — schemas are dependency-free data definitions
- Do NOT implement SeedManager (Story 1.3) or llm_call (Story 1.4)
- Do NOT use `from __future__ import annotations` — it can break Pydantic v2 in some edge cases
- Do NOT add pydantic `model_validator` for distribution sums — a simple `@model_validator` that checks sum is fine, but don't over-engineer it

### Testing Strategy

Test files go in `tests/shared/` (e.g., `tests/shared/test_schemas.py` or split per module).

Key test patterns:
1. **Construction:** Create model instance with valid data
2. **Serialization:** `model.model_dump_json()` → verify snake_case keys
3. **Deserialization:** `Model.model_validate_json(json_str)` → verify fields match
4. **Round-trip:** create → JSON → back → assert original == deserialized
5. **Validation:** Invalid values (e.g., connectivity_level=5) raise `ValidationError`
6. **YAML preset loading:** `yaml.safe_load()` → `PresetConfig(**data)` for each existing preset

### Project Structure Notes

Files to create:
```
src/crossfire/shared/schemas/
├── __init__.py          # UPDATE: re-export all models
├── config.py            # NEW
├── corpus.py            # NEW
├── entities.py          # NEW
├── incoherences.py      # NEW
├── reports.py           # NEW
└── evaluation.py        # NEW

tests/shared/
├── test_schemas.py      # NEW (or split per module)
```

### References

- [Source: architecture.md#Schema Enforcement]
- [Source: architecture.md#Naming Patterns]
- [Source: architecture.md#Data Architecture — Output Formats]
- [Source: architecture.md#Complete Project Directory Structure]
- [Source: epics.md#Story 1.2]
- [Source: epics.md#Story 2.2 — Document Types]
- [Source: epics.md#Story 2.3 — Entity Graph]
- [Source: epics.md#Story 3.1 — Incoherence 4D Design Space]
- [Source: product-brief-CROSSFIRE-distillate.md#Generator Core API]
- [Source: product-brief-CROSSFIRE-distillate.md#Incoherence Design Space]
- [Source: product-brief-CROSSFIRE-distillate.md#Document Type Taxonomy]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- Task 1: Created config.py with ScopeDistribution, DetectabilityDistribution, IncoherenceConfig, PresetConfig, GeneratorConfig, PipelineConfig. All 4 existing preset YAMLs parse and round-trip successfully. Union[str, int] for count field handles both "auto" and integer values.
- Task 2: Created corpus.py with Document (8 Literal document types, reliability_signal bounded 0-1) and SubcorpusMetadata. All serialization uses snake_case.
- Task 3: Created entities.py with EntityNode, EntityEdge, EntityGraph. Implemented to_networkx() and from_networkx() classmethod for lossless NetworkX conversion. Round-trip verified.
- Task 4: Created incoherences.py with IncoherenceLabel (full 4D design space as Literal types) and DistractorLabel. All 6 mechanisms, 3 scopes, 3 detectability levels, 3 system affinities validated.
- Task 5: Created reports.py with DetectedIncoherence (confidence bounded 0-1) and PipelineReport with detection list.
- Task 6: Created evaluation.py with ScopeResult, StageResult, EvaluationResult with nested per-scope and per-stage breakdowns.
- Task 7: Updated __init__.py to re-export all 18 public models. All 60 tests pass. All JSON output uses snake_case. No regressions.
- All 7 acceptance criteria satisfied.

### File List

- src/crossfire/shared/schemas/__init__.py (modified)
- src/crossfire/shared/schemas/config.py (new)
- src/crossfire/shared/schemas/corpus.py (new)
- src/crossfire/shared/schemas/entities.py (new)
- src/crossfire/shared/schemas/incoherences.py (new)
- src/crossfire/shared/schemas/reports.py (new)
- src/crossfire/shared/schemas/evaluation.py (new)
- tests/shared/test_schemas.py (new)

### Review Findings

- [ ] [Review][Patch] system_affinity Literal uses hyphens in config.py but underscores in incoherences.py; YAML presets also use hyphens — violates AC5 (snake_case enum values) and creates silent mismatch between config and annotation schemas [config.py:24, incoherences.py:17, configs/presets/high_connectivity.yaml:18, configs/presets/low_connectivity.yaml:18]
- [ ] [Review][Patch] from_networkx passes node_id directly to EntityNode(id=...) without coercing to str — Pydantic v2 raises ValidationError if a manually-constructed NetworkX graph uses integer node IDs [entities.py:47]
- [x] [Review][Defer] EntityGraph.to_networkx() returns undirected nx.Graph — directional relationships like "caused_by" silently lose direction [entities.py:25] — deferred, pre-existing design choice; no directed graph requirement in current stories
- [x] [Review][Defer] ScopeDistribution and DetectabilityDistribution floats have no sum-to-1.0 validation — downstream sampling silently non-normalized [config.py:8-17] — deferred, beyond current story scope

### Change Log

- 2026-04-06: Story 1.2 implemented — all Pydantic data contract schemas created with 60 tests covering construction, validation, round-trip serialization, YAML preset loading, and snake_case verification
