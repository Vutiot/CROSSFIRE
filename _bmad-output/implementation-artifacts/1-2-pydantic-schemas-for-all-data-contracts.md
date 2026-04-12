# Story 1.2: Pydantic Schemas for All Data Contracts (Rewrite)

Status: review

## Story

As a researcher,
I want validated data models for every structured format in the system,
So that generation output, pipeline reports, and evaluation results have enforced contracts preventing malformed data from crossing component boundaries.

## Context: Why This Is a Rewrite

The 2026-04-09 sprint change proposal pivoted CROSSFIRE from synthetic corpus generation to agentic processing of real investigation source documents (Grenfell, COPA, NTSB). This story rewrites all Pydantic schemas to match the new multi-source data architecture. The existing schemas were built for the old synthetic pipeline and must be replaced.

**This story's scope is limited to schema files, `__init__.py`, and schema tests.** Downstream consumer code (pipeline, evaluation, generator, scripts, run.py) will break — those are updated in their respective stories (4.x, 5.x) and the deprecated generator code is removed separately.

## Acceptance Criteria

1. **Given** the schemas package at `src/crossfire/shared/schemas/`
   **When** I import corpus models
   **Then** `Document` model exists with fields: `document_id`, `source` (e.g., "grenfell", "copa", "ntsb"), `document_type` (str, source-specific — not a fixed enum), `source_case_id`, `scope_classification`, `content` (text), and metadata fields — no `subcorpus_id`

2. **Given** the schemas package
   **When** I import contradiction models
   **Then** `ContradictionLabel` model exists with fields: `scope` (Literal["intra_doc", "inter_doc"]), `mechanism`, `detectability`, `system_affinity`, `difficulty`, `char_start`, `char_end`, `original_text`, `modified_text`, `rationale`, `ground_truth`, and document references
   **And** `DistractorLabel` model exists with divergence type field (Literal["expert_opinion", "preliminary_vs_final", "measurement_methodology", "uncertainty_expression"])

3. **Given** the schemas package
   **When** I import knowledge graph models
   **Then** `KnowledgeGraphClaim` and `CrossReference` models exist — marked as intermediate artifacts, not gold evaluation references

4. **Given** the schemas package
   **When** I import pipeline report models
   **Then** `DetectedContradiction` model exists with 2-scope taxonomy (intra_doc, inter_doc), document references, text spans, and confidence
   **And** `PipelineReport` model exists containing a list of `DetectedContradiction` entries plus run metadata

5. **Given** the schemas package
   **When** I import evaluation models
   **Then** `ScopeResult`, `StageResult`, and `EvaluationResult` models exist with per-scope (2-level: intra_doc, inter_doc) and per-stage (3-stage: claim_extraction, cross_reference_identification, contradiction_detection) breakdowns

6. **Given** the schemas package
   **When** I import config models
   **Then** `PipelineConfig` model exists with `case_dir` path and strategy configuration
   **And** `DatasetVersion` model exists tracking version ID, base version, and label correction history
   **And** `GenerationParams` model exists with contradiction rates per scope, distractor ratio, and mechanism/difficulty distributions

7. **Given** any Pydantic model
   **When** I serialize it to JSON
   **Then** all field names are `snake_case`

8. **Given** a malformed data dict (e.g., missing required field, wrong type, invalid scope literal)
   **When** I attempt to construct a Pydantic model from it
   **Then** a `ValidationError` is raised with a clear message identifying the invalid field

## Tasks / Subtasks

### Phase 1: Remove Old Schemas

- [x] Delete `src/crossfire/shared/schemas/entities.py` entirely (AC: all — removes `EntityNode`, `EntityEdge`, `EntityGraph`)
- [x] Remove `SubcorpusMetadata` from `corpus.py` (AC: 1)
- [x] Delete `src/crossfire/shared/schemas/incoherences.py` (replaced by `contradictions.py`) (AC: 2)

### Phase 2: Create New Schema Files

- [x] Create `src/crossfire/shared/schemas/contradictions.py` with `ContradictionLabel` and `DistractorLabel` (AC: 2)
- [x] Create `src/crossfire/shared/schemas/knowledge_graph.py` with `KnowledgeGraphClaim` and `CrossReference` (AC: 3)
- [x] Create `src/crossfire/shared/schemas/domain_registry.py` with `DomainRegistry` (AC: 6)
- [x] Create `src/crossfire/shared/schemas/scope_map.py` with `ScopeMap` (AC: 6)
- [x] Create `src/crossfire/shared/schemas/anonymization.py` with `AnonymizationMapping` (AC: 6)

### Phase 3: Modify Existing Schema Files

- [x] Rewrite `corpus.py` — adapt `Document` model (AC: 1)
- [x] Rewrite `config.py` — remove old generator configs, add `PipelineConfig`, `DatasetVersion`, `GenerationParams` (AC: 6)
- [x] Rewrite `reports.py` — `DetectedContradiction` replaces `DetectedIncoherence`, update `PipelineReport` (AC: 4)
- [x] Rewrite `evaluation.py` — adapt for 2-scope, 3-stage, injection-derived gold (AC: 5)

### Phase 4: Update Exports and Tests

- [x] Rewrite `__init__.py` — update all imports and `__all__` (AC: all)
- [x] Rewrite `tests/shared/test_schemas.py` — full coverage for all new/modified models (AC: 7, 8)
- [x] Verify all schema tests pass: `PYTHONPATH=src pytest tests/shared/test_schemas.py -v` (AC: all)

## Dev Notes

### What to REMOVE (old synthetic-generation schemas)

| Model | File | Reason |
|-------|------|--------|
| `EntityNode` | `entities.py` | DELETE FILE — entity graph is now built by agentic pipeline, not Python code |
| `EntityEdge` | `entities.py` | DELETE FILE |
| `EntityGraph` | `entities.py` | DELETE FILE |
| `SubcorpusMetadata` | `corpus.py` | No subcorpus concept in agentic pipeline |
| `IncoherenceLabel` | `incoherences.py` | DELETE FILE — replaced by `ContradictionLabel` in `contradictions.py` |
| `ScopeDistribution` | `config.py` | Old 3-scope distribution, no longer applicable |
| `DetectabilityDistribution` | `config.py` | Old distribution config |
| `IncoherenceConfig` | `config.py` | Old synthetic injection config |
| `PresetConfig` | `config.py` | Old preset-based generation |
| `GeneratorConfig` | `config.py` | Old synthetic generator config |
| `DetectedIncoherence` | `reports.py` | Renamed to `DetectedContradiction` |
| `RepresentationQualityResult` | `evaluation.py` | Rewritten for injection-derived gold |

### What to CREATE

#### `contradictions.py` — Gold Labels (replaces `incoherences.py`)

```python
# Enums/Literals
Scope = Literal["intra_doc", "inter_doc"]  # 2-scope only (was 3)
Mechanism = Literal["numeric_drift", "entity_swap", "causal_inversion",
                    "temporal_contradiction", "omission_based_implicit",
                    "temporal_revision_conflict"]  # unchanged
Detectability = Literal["single_hop", "multi_hop", "entity_resolution_dependent"]
SystemAffinity = Literal["balanced", "graph_favoring", "agentic_favoring"]
DivergenceType = Literal["expert_opinion", "preliminary_vs_final",
                         "measurement_methodology", "uncertainty_expression"]
Difficulty = Literal["easy", "medium", "hard"]  # per architecture

class ContradictionLabel(BaseModel):
    scope: Scope
    mechanism: Mechanism
    detectability: Detectability
    system_affinity: SystemAffinity
    difficulty: Difficulty
    char_start: int  # character offset in modified document
    char_end: int    # character offset in modified document
    original_text: str
    modified_text: str
    rationale: str
    ground_truth: bool  # True = real contradiction, used for validation
    document_references: list[str]

class DistractorLabel(BaseModel):
    scope: Scope
    divergence_type: DivergenceType  # constrained Literal, not free str
    document_references: list[str]
    description: str
```

Key changes from old `IncoherenceLabel`:
- `id` field removed (JSONL lines are self-contained)
- `modified_fact`/`original_fact` replaced by `char_start`/`char_end`/`original_text`/`modified_text` (char-span based)
- Added `difficulty`, `rationale`, `ground_truth`
- Scope reduced from 3 to 2 values
- `DistractorLabel.divergence_type` is now a constrained Literal (was free `str`)

#### `knowledge_graph.py` — Intermediate Artifacts (NOT gold eval)

```python
class KnowledgeGraphClaim(BaseModel):
    claim_id: str
    subject: str
    predicate: str
    object: str
    source_document: str
    confidence: float  # 0.0-1.0

class CrossReference(BaseModel):
    reference_id: str
    source_claim: str  # claim_id
    target_claim: str  # claim_id
    relationship: str
    source_documents: list[str]
```

These are intermediate artifacts that ship for transparency. The evaluator NEVER imports these for scoring.

#### `domain_registry.py`

```python
class DomainEntry(BaseModel):
    domain: str
    original_value: str
    anonymized_value: str

class DomainRegistry(BaseModel):
    case_id: str
    entries: list[DomainEntry]
```

Maps to `metadata/domain_registry.json` in case directories.

#### `scope_map.py`

```python
class ScopeMapEntry(BaseModel):
    document_id: str
    scope_classification: str  # how this document relates to other documents

class ScopeMap(BaseModel):
    case_id: str
    entries: list[ScopeMapEntry]
```

Maps to `metadata/scope_map.json` in case directories.

#### `anonymization.py`

```python
class AnonymizationMapping(BaseModel):
    original: str
    anonymized: str
    entity_type: str
```

Maps to `metadata/entity_mapping.json` in case directories.

### What to MODIFY

#### `corpus.py` — Document Model

```python
# DocumentType is no longer a fixed Literal enum — it is a plain str field.
# Document types are source-specific (e.g., "hearing_transcript" for Grenfell,
# "tactical_response_report" for COPA, "investigation_report" for NTSB).

class Document(BaseModel):
    document_id: str           # was "id"
    source: str                # e.g., "grenfell", "copa", "ntsb"
    document_type: str         # source-specific type (not a fixed enum)
    source_case_id: str        # source-specific case identifier
    scope_classification: str  # per scope_map
    content: str
    # metadata fields as needed
```

Key changes: removed `subcorpus_id`, removed `reliability_signal`, renamed `id` to `document_id`, added `source` field (FR31), changed `document_type` from fixed `Literal` enum to `str` for multi-source support (FR5), added `source_case_id` and `scope_classification` per FR31.

#### `config.py` — Pipeline and Dataset Config

Remove all old generator configs. Keep/rewrite:

```python
class PipelineConfig(BaseModel):
    mode: Literal["hybrid", "agentic", "graph_native"]  # underscore not hyphen
    case_dir: str  # path to case directory (was corpus_path)
    output_dir: str = "output/reports"

class DatasetVersion(BaseModel):
    version_id: str
    base_version: str | None = None  # if re-injection on same anonymized base
    label_corrections: list[str] = []

class GenerationParams(BaseModel):
    version_id: str
    base_version: str | None = None
    contradiction_rate_intra_doc: float
    contradiction_rate_inter_doc: float
    distractor_ratio: float
    mechanism_distribution: dict[str, float]  # mechanism -> proportion
    difficulty_distribution: dict[str, float]  # difficulty -> proportion
```

#### `reports.py` — Pipeline Output

```python
class DetectedContradiction(BaseModel):  # renamed from DetectedIncoherence
    scope: Literal["intra_doc", "inter_doc"]
    document_references: list[str]
    text_span_start: int
    text_span_end: int
    evidence_text: str
    confidence: float  # 0.0-1.0
    description: str

class PipelineReport(BaseModel):
    pipeline_mode: str
    case_dir: str  # was corpus_path
    detections: list[DetectedContradiction] = []
    timestamp: str
    run_metadata: dict = {}  # token counts, timing, etc.
```

#### `evaluation.py` — Evaluation Results

Adapt for 2-scope taxonomy, 3 defined stages, injection-derived gold:

```python
class ScopeResult(BaseModel):
    scope: Literal["intra_doc", "inter_doc"]  # constrained, was free str
    precision: float
    recall: float
    f1: float
    partial_credit_score: float

class StageResult(BaseModel):
    stage: Literal["claim_extraction", "cross_reference_identification",
                   "contradiction_detection"]  # constrained, was free str
    precision: float
    recall: float
    f1: float

class RepresentationQualityResult(BaseModel):
    claim_coverage: float  # vs injection-targeted gold claims, not full KG
    cross_reference_accuracy: float
    # removed entity_resolution_quality (old entity graph concept)

class EvaluationResult(BaseModel):
    overall_precision: float
    overall_recall: float
    overall_f1: float
    overall_partial_credit_score: float | None = None
    distractor_false_positive_rate: float | None = None
    per_scope: list[ScopeResult] = []
    per_stage: list[StageResult] = []
    representation_quality: RepresentationQualityResult | None = None
```

### Downstream Blast Radius (DO NOT FIX in this story)

These files import from schemas and will break after this rewrite. They are fixed in their own stories:

| Consumer | Imports | Fixed In |
|----------|---------|----------|
| `src/crossfire/generator/*` | `EntityGraph`, `EntityNode`, `GeneratorConfig`, `IncoherenceLabel`, etc. | DEPRECATED — entire generator package removed |
| `src/crossfire/pipeline/strategies/base.py` | `EntityGraph`, `DetectedIncoherence` | Story 4-1 |
| `src/crossfire/pipeline/strategies/graph_strategy.py` | `EntityGraph`, `EntityNode`, `EntityEdge`, `DetectedIncoherence` | Story 4-3 |
| `src/crossfire/pipeline/strategies/reasoning_strategy.py` | `DetectedIncoherence` | Story 4-2 |
| `src/crossfire/pipeline/hybrid_pipeline.py` | `DetectedIncoherence`, `PipelineReport` | Story 4-1 |
| `src/crossfire/pipeline/baselines/*.py` | `DetectedIncoherence`, `PipelineReport` | Story 4-4 |
| `src/crossfire/evaluation/*.py` | `IncoherenceLabel`, `EntityGraph`, `DetectedIncoherence` | Stories 5-1 through 5-5 |
| `scripts/*.py` | `GeneratorConfig`, `EntityGraph`, `IncoherenceLabel` | DEPRECATED |
| `run.py` | `GeneratorConfig` | Updated when generator is removed |
| `tests/generator/*`, `tests/pipeline/*`, `tests/evaluation/*` | Various old schemas | Updated in respective stories |
| `configs/presets/*.yaml` | Old `PresetConfig` format | DEPRECATED — do not delete in this story |

### Architecture Constraints

- **snake_case everywhere**: Python code, JSON output fields, config keys. Pydantic defaults to snake_case — no aliasing needed.
- **Pydantic v2**: Use `BaseModel`, `model_dump_json()`, `model_validate_json()`, `model_dump()`. No v1 methods.
- **Literal constraints**: Use `Literal[...]` for all enum-like fields (scope, mechanism, detectability, system_affinity, difficulty, divergence_type, stage, pipeline mode). No free `str` where values are known.
- **No `id` fields on JSONL records**: `ContradictionLabel` and `DistractorLabel` are JSONL line items — they don't need an `id` field.
- **Serialization through Pydantic only**: No raw dict construction. Always construct model instances.
- **Evaluator boundary**: `evaluation.py` models must NEVER import or reference `KnowledgeGraphClaim` or `CrossReference`.
- **loguru**: No `print()` statements. (Schemas are pure data models so this is trivially satisfied — no logging needed in schema files.)

### Testing Requirements

Rewrite `tests/shared/test_schemas.py` completely. Cover:

- Construction of every model with valid data
- Round-trip serialization (`model_dump_json()` → `model_validate_json()`)
- snake_case verification on JSON output for every model
- `ValidationError` on invalid data (wrong type, missing required field, invalid Literal value)
- All Literal enum values accepted (all mechanisms, all scopes, all stages, all divergence types, all difficulties)
- `char_start` / `char_end` are non-negative integers
- `confidence` fields are bounded [0.0, 1.0]
- Optional fields default correctly (`None`, `[]`, `{}`)

Do NOT test: preset YAML loading (presets are deprecated), NetworkX conversion (entities.py deleted), downstream consumer integration.

Run: `PYTHONPATH=src pytest tests/shared/test_schemas.py -v`

### Project Structure Notes

Target file layout after this story:

```
src/crossfire/shared/schemas/
├── __init__.py              # updated exports
├── anonymization.py         # NEW: AnonymizationMapping
├── config.py                # REWRITTEN: PipelineConfig, DatasetVersion, GenerationParams
├── contradictions.py        # NEW (replaces incoherences.py): ContradictionLabel, DistractorLabel
├── corpus.py                # MODIFIED: Document (adapted)
├── domain_registry.py       # NEW: DomainRegistry, DomainEntry
├── evaluation.py            # MODIFIED: 2-scope, 3-stage, injection-derived gold
├── knowledge_graph.py       # NEW: KnowledgeGraphClaim, CrossReference
├── reports.py               # MODIFIED: DetectedContradiction, PipelineReport
└── scope_map.py             # NEW: ScopeMap, ScopeMapEntry
```

Deleted:
- `entities.py` (removed)
- `incoherences.py` (replaced by `contradictions.py`)

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Schema Enforcement] — schema organization and file layout
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture] — output formats and case directory layout
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries] — generation/dataset/pipeline/evaluator boundaries
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2] — acceptance criteria and user story
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-09.md#Section 4.3] — specific schema changes for pivot
- [Source: _bmad-output/planning-artifacts/prd.md#FR14-NEW] — ContradictionLabel field requirements
- [Source: _bmad-output/planning-artifacts/prd.md#FR31-NEW] — Document metadata requirements

### Previous Story Intelligence

From Story 1-1:
- Project uses `PYTHONPATH=src pytest` for test execution
- Empty `__init__.py` files with no placeholder implementations
- `pyproject.toml` now exists (added in later commits)
- Preset YAML configs exist in `configs/presets/` — these are deprecated but should not be deleted in this story (separate cleanup)

From existing Story 1-2 implementation (pre-pivot):
- 18 models across 6 files, 60 tests passing
- Known bugs: `system_affinity` Literal uses hyphens in `config.py` but underscores in `incoherences.py` — moot now since both files are rewritten
- Known bug: `EntityGraph.from_networkx()` integer node ID coercion — moot since `entities.py` is deleted

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- All 127 schema tests pass (`PYTHONPATH=src pytest tests/shared/test_schemas.py -v`)
- 1 pre-existing failure in `test_llm.py` (retry count mismatch — unrelated to schema changes)

### Completion Notes List

- Deleted `entities.py` (EntityNode, EntityEdge, EntityGraph removed) and `incoherences.py` (replaced by contradictions.py)
- Removed `SubcorpusMetadata` from `corpus.py`
- Created 5 new schema files: `contradictions.py`, `knowledge_graph.py`, `domain_registry.py`, `scope_map.py`, `anonymization.py`
- Rewrote 4 existing files: `corpus.py` (Document adapted for multi-source case dirs with `source` field and `document_type` as str), `config.py` (PipelineConfig, DatasetVersion, GenerationParams), `reports.py` (DetectedContradiction, PipelineReport with run_metadata), `evaluation.py` (2-scope, 3-stage, injection-derived gold)
- All Literal constraints enforced: 2 scopes, 6 mechanisms, 3 detectabilities, 3 affinities, 3 difficulties, 4 divergence types, 3 pipeline modes, 3 stages. Document type is now a free str (source-specific, not a fixed enum).
- `char_start`/`char_end` validated as non-negative, `confidence` bounded [0.0, 1.0]
- Updated `__init__.py` with 21 model exports
- Rewrote `test_schemas.py` with 127 tests covering construction, round-trip serialization, snake_case keys, ValidationError on invalid data, and all Literal enum values

### Change Log

- 2026-04-10: Complete schema rewrite for agentic pipeline pivot — deleted 2 files, created 5 new files, rewrote 4 existing files, rewrote test file (127 tests)

### File List

- `src/crossfire/shared/schemas/entities.py` — DELETED
- `src/crossfire/shared/schemas/incoherences.py` — DELETED
- `src/crossfire/shared/schemas/contradictions.py` — NEW
- `src/crossfire/shared/schemas/knowledge_graph.py` — NEW
- `src/crossfire/shared/schemas/domain_registry.py` — NEW
- `src/crossfire/shared/schemas/scope_map.py` — NEW
- `src/crossfire/shared/schemas/anonymization.py` — NEW
- `src/crossfire/shared/schemas/corpus.py` — MODIFIED
- `src/crossfire/shared/schemas/config.py` — MODIFIED
- `src/crossfire/shared/schemas/reports.py` — MODIFIED
- `src/crossfire/shared/schemas/evaluation.py` — MODIFIED
- `src/crossfire/shared/schemas/__init__.py` — MODIFIED
- `tests/shared/test_schemas.py` — MODIFIED
