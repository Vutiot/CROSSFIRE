# Story 4.3: Graph Strategy (Graph-Native Mode)

Status: review

## Story

As a researcher,
I want a graph-native auditing pipeline that builds a knowledge graph and detects structural anomalies,
so that I can evaluate KG-based approaches on CROSSFIRE corpora.

## Acceptance Criteria

1. Given a `GraphStrategy` implementation in `graph_strategy.py` — when I run it against a corpus — then it constructs a knowledge graph from corpus documents using entity extraction and relationship identification
2. It detects structural anomalies and contradictions in the graph (conflicting attribute values, contradictory relationships)
3. It produces `DetectedIncoherence` entries with evidence_references and confidence scores
4. It exposes its internal knowledge graph for Layer 1 evaluation (FR27)
5. Running `HybridPipeline` with this graph strategy + `NullReasoningStrategy` constitutes graph-native mode (FR19)
6. This story is contingent on experimental feasibility — if graph-native proves unviable, this strategy is removed and the pipeline operates with agentic and hybrid modes only

## Tasks / Subtasks

- [x] Task 1: Create `src/crossfire/pipeline/strategies/graph_strategy.py` (AC: #1-#5)
  - [x] Implement `LLMGraphStrategy(GraphStrategy)` with LLM-based entity extraction and relationship identification
  - [x] Build `EntityGraph` from extracted entities and relationships
  - [x] Detect structural anomalies via LLM analysis of graph
  - [x] Expose internal graph in `GraphResult.internal_graph` for Layer 1 evaluation
  - [x] Return `(GraphResult, None)` on success, `(None, error)` on failure

- [x] Task 2: Write tests in `tests/pipeline/test_graph_strategy.py` (AC: #1-#5)
  - [x] Mock LLM for entity extraction and anomaly detection
  - [x] Test: entities extracted and graph built
  - [x] Test: anomalies detected with valid fields
  - [x] Test: internal graph exposed and convertible to NetworkX
  - [x] Test: integration with HybridPipeline in graph-native mode
  - [x] Test: LLM failure and empty corpus handled gracefully

- [x] Task 3: Run full test suite — no regressions

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Completion Notes List

- Task 1: Created `LLMGraphStrategy` with two-phase pipeline: (1) LLM-based entity/relationship extraction per document, building EntityGraph, (2) LLM-based anomaly detection across the full graph. Exposes `internal_graph` for FR27 Layer 1 evaluation.
- Task 2: 9 tests covering entity extraction, edge building, anomaly detection, graph exposure, graph-native mode integration, error handling, and empty corpus.
- Task 3: 339 tests pass (zero regressions).

### File List

- src/crossfire/pipeline/strategies/graph_strategy.py (new)
- tests/pipeline/test_graph_strategy.py (new)

### Change Log

- 2026-04-06: Story 4.3 implemented — LLM graph strategy with KG construction and anomaly detection, 9 tests
