# Story 4.1: Strategy Interfaces & Pipeline Skeleton

Status: review

## Story

As a developer,
I want the strategy interfaces and hybrid pipeline skeleton with mode switching,
so that all pipeline modes produce reports through a single, consistent architecture.

## Acceptance Criteria

1. Given the pipeline module at `src/crossfire/pipeline/` — when I import the strategy interfaces — then `strategies/base.py` exports abstract `GraphStrategy` and `ReasoningStrategy` with a `run(corpus_path) -> result` interface
2. `strategies/null_strategies.py` exports `NullGraphStrategy` (returns empty graph) and `NullReasoningStrategy` (returns empty detections)
3. `hybrid_pipeline.py` exports `HybridPipeline` that accepts `graph_strategy` and `reasoning_strategy` as constructor arguments
4. `HybridPipeline.run(corpus_path)` loads corpus JSONL, runs both strategies, merges results, and outputs a `PipelineReport` JSON (FR20)
5. The pipeline NEVER loads gold annotation files — only corpus documents (AR11)
6. Running with both null strategies produces a valid but empty `PipelineReport`
7. The pipeline uses SeedManager for any random decisions
8. pytest tests verify mode switching: hybrid (both real), agentic (null graph), graph-native (null reasoning)

## Tasks / Subtasks

- [x] Task 1: Create intermediate result models in `strategies/base.py` (AC: #1)
  - [x] Define `GraphResult` Pydantic model with `detected_incoherences: list[DetectedIncoherence]` and `internal_graph: EntityGraph | None`
  - [x] Define `ReasoningResult` Pydantic model with `detected_incoherences: list[DetectedIncoherence]`
  - [x] Define abstract `GraphStrategy` base class (ABC) with `run(corpus_path: str) -> tuple[GraphResult | None, str | None]`
  - [x] Define abstract `ReasoningStrategy` base class (ABC) with `run(corpus_path: str) -> tuple[ReasoningResult | None, str | None]`

- [x] Task 2: Create null strategy implementations in `strategies/null_strategies.py` (AC: #2, #6)
  - [x] `NullGraphStrategy(GraphStrategy)` — `run()` returns `(GraphResult(detected_incoherences=[], internal_graph=None), None)`
  - [x] `NullReasoningStrategy(ReasoningStrategy)` — `run()` returns `(ReasoningResult(detected_incoherences=[]), None)`

- [x] Task 3: Create `HybridPipeline` in `hybrid_pipeline.py` (AC: #3, #4, #5, #7)
  - [x] Constructor: `__init__(self, graph_strategy: GraphStrategy, reasoning_strategy: ReasoningStrategy, seed_manager: SeedManager)`
  - [x] `run(self, corpus_path: str) -> tuple[PipelineReport | None, str | None]`
  - [x] Load corpus documents from `corpus_path` directory (glob `subcorpus_*.jsonl`, parse each line as `Document`)
  - [x] Run `graph_strategy.run(corpus_path)` and `reasoning_strategy.run(corpus_path)` — if either fails, log WARNING and use empty result
  - [x] Merge detected incoherences from both strategies (deduplicate by matching `evidence_references`)
  - [x] Build `PipelineReport` with merged detections and return `(report, None)`
  - [x] HARD BOUNDARY: never load `gold_*.json` files — only `subcorpus_*.jsonl`

- [x] Task 4: Update `__init__.py` files for clean imports (AC: #1, #2, #3)
  - [x] `pipeline/strategies/__init__.py`: export `GraphStrategy`, `ReasoningStrategy`, `GraphResult`, `ReasoningResult`, `NullGraphStrategy`, `NullReasoningStrategy`
  - [x] `pipeline/__init__.py`: export `HybridPipeline` + strategy re-exports

- [x] Task 5: Write tests in `tests/pipeline/test_hybrid_pipeline.py` (AC: #6, #8)
  - [x] Create `tests/pipeline/` directory with `__init__.py` and `conftest.py`
  - [x] Create a small test corpus fixture (2 subcorpora x 2 docs each, written as JSONL)
  - [x] Test: both null strategies produces valid empty PipelineReport
  - [x] Test: mode switching — hybrid (mock both strategies returning detections), agentic (NullGraphStrategy + mock reasoning), graph-native (mock graph + NullReasoningStrategy)
  - [x] Test: strategy failure is handled gracefully (returns WARNING, uses empty result)
  - [x] Test: pipeline does not access any `gold_*.json` files (mock filesystem or verify via corpus_path only)
  - [x] Test: PipelineReport validates against Pydantic schema
  - [x] Test: determinism — same seed + same input = same output

- [x] Task 6: Run full test suite — no regressions
  - [x] Verify all existing tests (284) still pass alongside new pipeline tests

## Dev Notes

### Architecture Compliance

**Strategy Pattern — Dependency Injection, NOT Runtime Branching:**
Mode selection happens at construction time. HybridPipeline should NEVER contain `if isinstance(self.graph_strategy, NullGraphStrategy)` or similar checks. The null strategies handle mode switching by returning empty results — the pipeline code path is identical regardless of mode.

```python
# Hybrid mode
pipeline = HybridPipeline(GraphStrategyImpl(...), ReasoningStrategyImpl(...), seed_mgr)

# Agentic mode (FR18)
pipeline = HybridPipeline(NullGraphStrategy(), ReasoningStrategyImpl(...), seed_mgr)

# Graph-native mode (FR19, contingent)
pipeline = HybridPipeline(GraphStrategyImpl(...), NullReasoningStrategy(), seed_mgr)
```

[Source: architecture.md#Strategy Pattern]

**AR11 — Hard Architectural Boundary:**
The pipeline NEVER reads gold annotation files. It loads ONLY corpus JSONL files (`subcorpus_*.jsonl`). Gold files (`gold_incoherence_labels.json`, `gold_distractor_labels.json`, `entity_graph.json`) are consumed ONLY by the evaluation layer (Epic 5). If a developer loads gold files in pipeline code, they've broken the architecture.
[Source: architecture.md#Generator → Pipeline Boundary, epics.md#Story 4.1 AC]

### Existing Schemas — DO NOT MODIFY

**PipelineReport and DetectedIncoherence** are already defined in `src/crossfire/shared/schemas/reports.py`:
```python
class DetectedIncoherence(BaseModel):
    id: str
    evidence_references: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    description: str

class PipelineReport(BaseModel):
    pipeline_mode: str  # "hybrid", "agentic", "graph-native"
    corpus_path: str
    detections: list[DetectedIncoherence] = []
    timestamp: str      # ISO format datetime string
```

**PipelineConfig** is in `src/crossfire/shared/schemas/config.py`:
```python
class PipelineConfig(BaseModel):
    mode: Literal["hybrid", "agentic", "graph-native"]
    corpus_path: str
    output_dir: str = "output/reports"
```

**EntityGraph** is in `src/crossfire/shared/schemas/entities.py` — used for `GraphResult.internal_graph` (Layer 1 evaluation in Epic 5).

**Document** is in `src/crossfire/shared/schemas/corpus.py`:
```python
class Document(BaseModel):
    id: str
    document_type: DocumentType  # 8 types
    subcorpus_id: str
    reliability_signal: float = Field(ge=0.0, le=1.0)
    content: str
```

Import all schemas from `crossfire.shared.schemas.*` — do NOT create duplicate models.
[Source: src/crossfire/shared/schemas/reports.py, entities.py, corpus.py, config.py]

### New Models to Create

**GraphResult** and **ReasoningResult** are intermediate result types for strategy outputs. Define them in `strategies/base.py`:

```python
class GraphResult(BaseModel):
    detected_incoherences: list[DetectedIncoherence] = []
    internal_graph: EntityGraph | None = None  # Exposed for Layer 1 evaluation (FR27)

class ReasoningResult(BaseModel):
    detected_incoherences: list[DetectedIncoherence] = []
```

These are NOT serialized to JSON output — they're internal data transfer objects between strategies and the pipeline orchestrator.

### Corpus Loading Pattern

Established in Epic 3. Use the same pattern:
```python
from crossfire.shared.schemas.corpus import Document

docs: list[Document] = []
for jsonl_path in sorted(Path(corpus_path).glob("subcorpus_*.jsonl")):
    text = jsonl_path.read_text(encoding="utf-8").strip()
    for line in text.split("\n"):
        if line:
            doc = Document.model_validate_json(line)
            docs.append(doc)
```

Corpus files are at `{corpus_path}/subcorpus_sc-{N}.jsonl`, each line is a JSON-serialized `Document`.
[Source: src/crossfire/generator/orchestrator.py, Story 3.1 dev notes]

### Error Handling

Return `(result, error)` tuples. Strategy failures are recoverable — use empty result and continue:
```python
graph_result, error = self.graph_strategy.run(corpus_path)
if error:
    logger.warning(f"Graph strategy failed: {error}")
    graph_result = GraphResult()  # Empty fallback
```

Pipeline-level failures (e.g., corpus_path doesn't exist, no JSONL files found) return `(None, error_message)`.
[Source: architecture.md#Error Handling]

### Logging

loguru only. No `print()`.
- INFO: pipeline start, pipeline complete, merged detection count
- WARNING: strategy failures (recovered with empty result)
- ERROR: unrecoverable failures (corpus not found)
- DEBUG: individual document loading, strategy timing

```python
from loguru import logger
logger.info(f"Pipeline starting: corpus_path={corpus_path}")
logger.info(f"Loaded {len(docs)} documents from {len(jsonl_files)} subcorpora")
logger.info(f"Pipeline complete: {len(report.detections)} incoherences detected")
```
[Source: architecture.md#Logging]

### SeedManager Usage

Pipeline receives `SeedManager` at construction and passes it to strategies. Use `seed_mgr.get_seed("pipeline", 0)` for pipeline-level randomness (e.g., tie-breaking in deduplication). Strategies will use their own component names when they're implemented in Stories 4.2/4.3.
[Source: src/crossfire/shared/seed_manager.py]

### Deduplication in Merge

When merging results from both strategies, deduplicate by comparing `evidence_references` sets. If both strategies detect the same document pair as incoherent, keep the detection with higher confidence. This is a simple merge for the skeleton — refinement happens as strategies mature.

### Known Technical Debt (from deferred-work.md)

- `EntityGraph.to_networkx()` returns undirected `nx.Graph` — directional relationships lose direction. May affect GraphStrategy in Story 4.3 if directed traversal is needed.
- `_usage` dict in `llm.py` is not thread-safe — relevant if strategies run in parallel (not in this story's scope).
[Source: _bmad-output/implementation-artifacts/deferred-work.md]

### Test Organization

```
tests/
├── pipeline/               # NEW
│   ├── __init__.py         # NEW
│   ├── conftest.py         # NEW — shared fixtures
│   └── test_hybrid_pipeline.py  # NEW — pipeline + strategy tests
```

**Test fixtures (conftest.py):**
- `tmp_corpus_dir`: Creates a temp dir with 2 subcorpus JSONL files (2 docs each) — minimal but sufficient
- `seed_manager`: `SeedManager(master_seed=42)`
- `sample_detections`: Pre-built `DetectedIncoherence` list for mock strategies

**Mock strategy pattern:**
```python
class MockGraphStrategy(GraphStrategy):
    def __init__(self, detections=None):
        self._detections = detections or []
    def run(self, corpus_path):
        return GraphResult(detected_incoherences=self._detections), None

class MockReasoningStrategy(ReasoningStrategy):
    def __init__(self, detections=None):
        self._detections = detections or []
    def run(self, corpus_path):
        return ReasoningResult(detected_incoherences=self._detections), None

class FailingStrategy(GraphStrategy):
    def run(self, corpus_path):
        return None, "Strategy failed intentionally"
```

Run tests with `PYTHONPATH=src pytest tests/pipeline/ -v`.

### Previous Story Learnings (Epic 3)

- Use `model_validate_json(line)` for JSONL parsing, `model_dump_json()` for serialization
- Use `sorted(path.glob(...))` for deterministic file ordering
- Individual strategy failures should be WARNING, not ERROR — the pipeline continues with partial results
- Test helpers: create minimal fixture data, don't over-engineer
- 284 tests currently pass — must not break them

### Anti-Patterns to Avoid

- Do NOT use `print()` — use loguru
- Do NOT construct raw dicts for Pydantic models — use constructors
- Do NOT add runtime mode checks in HybridPipeline (no `if isinstance(...)`)
- Do NOT load `gold_*.json`, `entity_graph.json`, or `metadata.json` in pipeline code
- Do NOT modify existing schemas in `src/crossfire/shared/schemas/`
- Do NOT add LLM calls — this story is pure Python orchestration (no API calls)
- Do NOT use `random.seed()` directly — use SeedManager

### Project Structure Notes

Files to create:
```
src/crossfire/pipeline/
├── __init__.py             # UPDATE — add exports
├── hybrid_pipeline.py      # NEW — HybridPipeline orchestrator
├── strategies/
│   ├── __init__.py         # UPDATE — add exports
│   ├── base.py             # NEW — GraphStrategy, ReasoningStrategy ABCs + result models
│   └── null_strategies.py  # NEW — NullGraphStrategy, NullReasoningStrategy

tests/pipeline/
├── __init__.py             # NEW
├── conftest.py             # NEW — shared fixtures
└── test_hybrid_pipeline.py # NEW — pipeline + strategy + mode switching tests
```

Existing files (read-only reference):
- `src/crossfire/shared/schemas/reports.py` — PipelineReport, DetectedIncoherence
- `src/crossfire/shared/schemas/entities.py` — EntityGraph (for GraphResult)
- `src/crossfire/shared/schemas/corpus.py` — Document (for corpus loading)
- `src/crossfire/shared/schemas/config.py` — PipelineConfig
- `src/crossfire/shared/seed_manager.py` — SeedManager
- `src/crossfire/shared/llm.py` — NOT used in this story

### References

- [Source: architecture.md#Strategy Pattern — Dependency Injection]
- [Source: architecture.md#Generator → Pipeline Boundary (AR11)]
- [Source: architecture.md#Error Handling]
- [Source: architecture.md#Logging]
- [Source: epics.md#Story 4.1: Strategy Interfaces & Pipeline Skeleton]
- [Source: epics.md#Epic 4: Auditing Pipelines]
- [Source: prd.md#FR17-FR20, FR21-FR22]
- [Source: src/crossfire/shared/schemas/reports.py]
- [Source: src/crossfire/shared/schemas/entities.py]
- [Source: src/crossfire/shared/schemas/corpus.py]
- [Source: src/crossfire/shared/seed_manager.py]
- [Source: _bmad-output/implementation-artifacts/deferred-work.md]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- Task 1: Created `strategies/base.py` with `GraphResult` and `ReasoningResult` Pydantic models, plus abstract `GraphStrategy` and `ReasoningStrategy` base classes (ABC). GraphResult includes optional `internal_graph: EntityGraph | None` for Layer 1 evaluation (FR27).
- Task 2: Created `null_strategies.py` with `NullGraphStrategy` and `NullReasoningStrategy`. Both return empty result objects with no errors, enabling mode switching via constructor injection.
- Task 3: Created `hybrid_pipeline.py` with `HybridPipeline` orchestrator. Loads corpus from JSONL only (AR11 enforced), runs both strategies, merges results with deduplication (higher confidence wins on duplicate evidence_references), and infers pipeline mode from strategy types.
- Task 4: Updated both `__init__.py` files with clean re-exports. `from crossfire.pipeline import HybridPipeline, GraphStrategy, ...` works.
- Task 5: 22 tests across 9 test classes covering: result models (4), null strategies (4), null pipeline (2), mode switching (3), strategy failure (3), corpus errors (2), AR11 boundary (1), merge deduplication (2), determinism (1). Fixtures in conftest.py: tmp_corpus_dir, seed_manager, sample_detections.
- Task 6: Full suite — 306 tests pass (284 existing + 22 new). Zero regressions.

### File List

- src/crossfire/pipeline/__init__.py (modified)
- src/crossfire/pipeline/hybrid_pipeline.py (new)
- src/crossfire/pipeline/strategies/__init__.py (modified)
- src/crossfire/pipeline/strategies/base.py (new)
- src/crossfire/pipeline/strategies/null_strategies.py (new)
- tests/pipeline/__init__.py (new)
- tests/pipeline/conftest.py (new)
- tests/pipeline/test_hybrid_pipeline.py (new)

### Change Log

- 2026-04-06: Story 4.1 implemented — strategy interfaces, null strategies, HybridPipeline orchestrator with mode switching, and 22 tests
