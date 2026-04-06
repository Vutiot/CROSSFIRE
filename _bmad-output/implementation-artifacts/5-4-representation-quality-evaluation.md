# Story 5.4: Representation Quality Evaluation

Status: review

## Story

As a researcher,
I want to evaluate a pipeline's internal knowledge graph against the gold entity graph,
so that I can measure representation quality independently from auditing accuracy.

## Acceptance Criteria

1. Given a pipeline's internal knowledge graph (exposed by GraphStrategy in Story 4.3) and the gold entity graph — when I run representation quality evaluation — then it computes entity coverage: what fraction of gold entities appear in the system graph (FR27)
2. It computes relationship accuracy: what fraction of system relationships match gold relationships
3. It computes entity resolution quality: how well the system merges entities with paraphrased/abbreviated naming
4. Results are returned as a dedicated section within `EvaluationResult` (Layer 1: representation quality)
5. This evaluation is independent from Layer 2 (auditing strategy) — both can run separately
6. If graph-native mode is dropped, this evaluation still works for hybrid mode's graph component

## Tasks / Subtasks

- [x] Task 1: Add `RepresentationQualityResult` schema to `evaluation.py` (AC: #4)
  - [x] Define `RepresentationQualityResult(entity_coverage: float, relationship_accuracy: float, entity_resolution_quality: float)`
  - [x] Add `representation_quality: RepresentationQualityResult | None = None` to `EvaluationResult`
  - [x] Export from `schemas/__init__.py`
  - [x] Keep backward compatible — existing tests must still pass

- [x] Task 2: Create `src/crossfire/evaluation/representation_eval.py` (AC: #1, #2, #3, #4, #5, #6)
  - [x] `score_representation(system_graph: EntityGraph, gold_graph: EntityGraph) -> EvaluationResult`
  - [x] Entity matching: match system entities to gold entities by canonical_name (case-insensitive) or alias overlap
  - [x] Entity coverage = matched_gold_entities / total_gold_entities (AC #1)
  - [x] Relationship accuracy = matched_system_edges / total_system_edges (AC #2)
  - [x] Entity resolution quality = correctly_resolved_aliases / total_aliases (AC #3)
  - [x] Return `EvaluationResult` with `representation_quality` populated
  - [x] Handle edge cases: empty graphs, no aliases, no edges

- [x] Task 3: Update `src/crossfire/evaluation/__init__.py` with exports
  - [x] Add `score_representation` export

- [x] Task 4: Write tests in `tests/evaluation/test_representation_eval.py` (AC: #1-#6)
  - [x] Test: perfect graph match → coverage=1.0, accuracy=1.0, resolution=1.0
  - [x] Test: partial entity coverage (some gold entities missing from system)
  - [x] Test: relationship accuracy (some system edges are wrong)
  - [x] Test: entity resolution quality (aliases resolved vs. split)
  - [x] Test: empty system graph → coverage=0.0
  - [x] Test: empty gold graph → edge case handling
  - [x] Test: independence from Layer 2 (no PipelineReport needed)
  - [x] Test: determinism across calls

- [x] Task 5: Run full test suite — no regressions

## Dev Notes

### Architecture Compliance

**Layer 1 vs Layer 2:**
This evaluation measures representation quality (Layer 1) — how well the pipeline builds its internal knowledge graph. It is completely independent from Layer 2 (auditing quality — how well the pipeline detects incoherences). Layer 1 takes two EntityGraphs; Layer 2 takes PipelineReport + gold labels.
[Source: architecture.md#Pipeline → Evaluator Boundary, epics.md#Story 5.4]

**NFR2 — Deterministic Evaluation:** Must be deterministic. Use sorted iteration for entity matching.
[Source: prd.md#NFR2]

### Existing Schemas

**EntityGraph** in `src/crossfire/shared/schemas/entities.py`:
```python
class EntityNode(BaseModel):
    id: str
    entity_type: str
    canonical_name: str
    aliases: list[str] = []
    subcorpus_memberships: list[str] = []

class EntityEdge(BaseModel):
    source: str
    target: str
    relationship_type: str

class EntityGraph(BaseModel):
    nodes: list[EntityNode] = []
    edges: list[EntityEdge] = []
```

**GraphResult** in `src/crossfire/pipeline/strategies/base.py`:
```python
class GraphResult(BaseModel):
    detected_incoherences: list[DetectedIncoherence] = []
    internal_graph: EntityGraph | None = None  # Exposed for Layer 1 evaluation
```

The pipeline's `GraphResult.internal_graph` is the system graph input for this story.
[Source: src/crossfire/shared/schemas/entities.py, pipeline/strategies/base.py]

### Schema Extension

Add to `src/crossfire/shared/schemas/evaluation.py`:
```python
class RepresentationQualityResult(BaseModel):
    entity_coverage: float       # fraction of gold entities found in system graph
    relationship_accuracy: float  # fraction of system edges matching gold edges
    entity_resolution_quality: float  # fraction of gold aliases correctly resolved

class EvaluationResult(BaseModel):
    ...
    representation_quality: RepresentationQualityResult | None = None
```

Also export `RepresentationQualityResult` from `schemas/__init__.py`.
[Source: src/crossfire/shared/schemas/evaluation.py]

### Entity Matching Semantics

System and gold graphs have different entity IDs. Match entities by name:

**Name normalization:** `canonical_name.strip().lower()` for comparison.

**Match algorithm:**
1. Build gold name index: for each gold entity, index its canonical_name + all aliases (normalized)
2. For each system entity, check if its canonical_name (normalized) appears in the gold name index
3. If matched, record the (system_entity_id → gold_entity_id) mapping
4. A gold entity is "covered" if any system entity matched it

**Why name-based:** Entity IDs are implementation-specific (gold uses `entity_NNN`, system uses `entity_NNNN`). Names are the semantic bridge. The gold graph's aliases field captures the paraphrased/abbreviated names that entity resolution should resolve.

### Metric Definitions

**Entity coverage (AC #1):**
```
entity_coverage = |gold entities matched by ≥1 system entity| / |gold entities|
```
- 0.0 if no gold entities exist (edge case)
- Measures recall: "what fraction of the ground truth did the system capture?"

**Relationship accuracy (AC #2):**
```
relationship_accuracy = |system edges matching a gold edge| / |system edges|
```
- Matching: system edge (A, B, rel_type) matches gold edge if mapped source matches gold source, mapped target matches gold target, and relationship_type matches
- Edges are undirected for matching (since EntityGraph uses nx.Graph — undirected)
- 1.0 if no system edges exist (vacuous truth — no wrong edges)
- Measures precision: "what fraction of system relationships are correct?"

**Entity resolution quality (AC #3):**
```
entity_resolution_quality = |gold aliases found under correct system entity| / |total gold aliases|
```
- For each gold entity with aliases, check if those aliases map to the same system entity as the canonical name
- 1.0 if no gold entities have aliases (vacuous truth — nothing to resolve)
- Measures: "how well does the system merge alternative names?"

### Edge Cases

| Scenario | Coverage | Accuracy | Resolution |
|----------|----------|----------|------------|
| Both graphs empty | 0.0 | 0.0 | 0.0 |
| Empty system, non-empty gold | 0.0 | 0.0 | 0.0 |
| Non-empty system, empty gold | 0.0 | 1.0 (vacuous) | 0.0 |
| Perfect match | 1.0 | 1.0 | 1.0 |
| No aliases in gold | coverage/accuracy normal | 1.0 (vacuous) |
| No edges in either graph | coverage normal | 0.0 | resolution normal |

### Error Handling

Pure computation — no I/O, no LLM calls. Let Pydantic validation propagate.
[Source: architecture.md#Error Handling]

### Logging

```python
from loguru import logger
logger.info(f"Representation eval: system={len(system_graph.nodes)} nodes, gold={len(gold_graph.nodes)} nodes")
logger.info(f"Representation result: coverage={r.entity_coverage:.4f} accuracy={r.relationship_accuracy:.4f} resolution={r.entity_resolution_quality:.4f}")
```
loguru only. No `print()`.
[Source: architecture.md#Logging]

### Previous Story Learnings (from Stories 5.1-5.3)

- Keep functions pure — take Pydantic models, return Pydantic models
- Use sorted iteration for determinism
- Test with hand-crafted examples with known expected values
- 383 tests currently pass — must not break them

### Anti-Patterns to Avoid

- Do NOT use `print()` — use loguru
- Do NOT use SeedManager or randomness — pure computation
- Do NOT modify EntityGraph or EntityNode schemas — only extend evaluation.py
- Do NOT import or depend on PipelineReport — Layer 1 is independent from Layer 2
- Do NOT use NetworkX for matching — work directly with Pydantic models (faster, simpler)

### Project Structure Notes

Files to create/modify:
```
src/crossfire/shared/schemas/
├── evaluation.py           # UPDATE — add RepresentationQualityResult, extend EvaluationResult
└── __init__.py             # UPDATE — export RepresentationQualityResult

src/crossfire/evaluation/
├── __init__.py             # UPDATE — add score_representation export
└── representation_eval.py  # NEW — Layer 1 representation quality evaluation (FR27)

tests/evaluation/
└── test_representation_eval.py  # NEW — representation quality tests
```

Existing files (read-only reference):
- `src/crossfire/shared/schemas/entities.py` — EntityNode, EntityEdge, EntityGraph
- `src/crossfire/pipeline/strategies/base.py` — GraphResult.internal_graph
- `src/crossfire/pipeline/strategies/graph_strategy.py` — how LLMGraphStrategy builds internal_graph

### References

- [Source: architecture.md#Pipeline → Evaluator Boundary]
- [Source: architecture.md#Logging]
- [Source: epics.md#Story 5.4: Representation Quality Evaluation]
- [Source: epics.md#Epic 5: Evaluation & Diagnostics]
- [Source: prd.md#FR27, NFR2]
- [Source: src/crossfire/shared/schemas/entities.py]
- [Source: src/crossfire/shared/schemas/evaluation.py]
- [Source: src/crossfire/pipeline/strategies/base.py — GraphResult.internal_graph]
- [Source: src/crossfire/pipeline/strategies/graph_strategy.py — LLMGraphStrategy]
- [Source: _bmad-output/implementation-artifacts/5-1-binary-and-partial-credit-scorers.md]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- Task 1: Added `RepresentationQualityResult` model to evaluation.py with entity_coverage, relationship_accuracy, entity_resolution_quality fields. Extended `EvaluationResult` with optional `representation_quality` field. Exported from `schemas/__init__.py`. Backward compatible — all 383 existing tests still pass.
- Task 2: Created `representation_eval.py` — `score_representation()` takes system and gold EntityGraphs. Entity matching by normalized canonical_name + aliases (case-insensitive). Coverage = fraction of gold entities found. Relationship accuracy = fraction of system edges matching gold (undirected). Entity resolution quality = fraction of gold aliases correctly merged under same system entity.
- Task 3: Updated `evaluation/__init__.py` with `score_representation` export.
- Task 4: 19 tests across 8 test classes covering: perfect match, partial entity coverage, coverage via aliases, case-insensitive matching, relationship accuracy (correct/wrong/mixed/undirected), entity resolution (all resolved/all split/partial), no-aliases vacuous truth, edge cases (both empty/empty system/empty gold/no edges), Layer 2 independence, and determinism.
- Task 5: 402 tests pass (383 existing + 19 new). Zero regressions.

### File List

- src/crossfire/shared/schemas/evaluation.py (modified — added RepresentationQualityResult, extended EvaluationResult)
- src/crossfire/shared/schemas/__init__.py (modified — added RepresentationQualityResult export)
- src/crossfire/evaluation/__init__.py (modified — added score_representation export)
- src/crossfire/evaluation/representation_eval.py (new)
- tests/evaluation/test_representation_eval.py (new)

### Change Log

- 2026-04-06: Story 5.4 implemented — Layer 1 representation quality evaluation with 19 tests
