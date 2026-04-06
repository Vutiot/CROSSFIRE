---
stepsCompleted:
  - "step-01-init"
  - "step-02-context"
  - "step-03-starter"
  - "step-04-decisions"
  - "step-05-patterns"
  - "step-06-structure"
  - "step-07-validation"
  - "step-08-complete"
status: 'complete'
completedAt: '2026-04-06'
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/product-brief-CROSSFIRE.md"
  - "_bmad-output/planning-artifacts/product-brief-CROSSFIRE-distillate.md"
  - "_bmad-output/brainstorming/brainstorming-session-2026-04-05-001.md"
  - "_bmad-output/planning-artifacts/implementation-readiness-report-2026-04-06.md"
workflowType: 'architecture'
project_name: 'CROSSFIRE'
user_name: 'Al'
date: '2026-04-06'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
33 FRs across 6 capability areas. The generator subsystem (FR1-FR16, 16 FRs) is the largest and most complex, handling corpus generation, incoherence injection, and gold annotation production. The auditing subsystem (FR17-FR22, 6 FRs) implements one hybrid architecture with mode switching. The evaluation subsystem (FR23-FR29, 7 FRs) implements two-layer diagnostic scoring. Data management (FR30-FR33, 4 FRs) handles output persistence and pre-generated datasets.

**Non-Functional Requirements:**
15 NFRs, dominated by reproducibility (bit-identical outputs, deterministic evaluation, seeded randomness) and correctness (verifiable gold annotations, no scoring errors). Portability (Linux/macOS, no GPU, academic hardware) and cost predictability (~$5-20/subcorpus, graceful API failure) are secondary but firm constraints.

**Scale & Complexity:**

- Primary domain: CLI/batch processing pipeline
- Complexity level: Medium
- Estimated architectural components: 5 major subsystems (generator, injector, annotator, pipeline, evaluator) + shared infrastructure (seeding, output formats, configuration)

### Technical Constraints & Dependencies

- Python 3.10+, clone-and-run repository
- LLM API dependency: OpenAI GPT-4o-mini (generation), potentially multi-model
- Graph library: NetworkX or similar for entity graph construction/manipulation
- Scientific Python: numpy, scipy, scikit-learn for evaluation metrics
- Seeded randomness at every level (Python random, numpy, LLM temperature 0)
- Scale ceiling: 10K docs / 100K chunks
- Output formats TBD: JSON, JSONL, or directory structure
- No package registry publication for v1

### Cross-Cutting Concerns Identified

- **Reproducibility/Seeding:** Affects every component — generation, injection, pipeline execution, evaluation. Must be architecturally enforced, not per-component ad hoc.
- **Gold Annotation Schema:** Produced by generator, consumed by evaluator. Schema must be versioned and consistent across the boundary.
- **Output Format Standardization:** Generator outputs (corpus + annotations) and pipeline outputs (incoherence reports) must follow documented formats enabling cross-component interoperability.
- **Contamination Prevention:** Spans injection methodology — minimal-pair construction, same LLM temp/prompt, multi-model generation. Baked into generator architecture, not bolt-on.
- **Mode Switching:** The hybrid pipeline's ability to disable graph or LLM layers must be architecturally clean, not feature-flagged spaghetti.

## Starter Template & Project Foundation

### Primary Technology Domain

Python 3.10+ CLI/batch processing pipeline. No framework scaffolding — standard Python project structure.

### Project Structure Decision

**Selected: `src/` layout** with importable package structure.

```
crossfire/
├── src/
│   └── crossfire/
│       ├── __init__.py
│       ├── generator/       # Corpus generation, injection, annotation
│       ├── pipeline/        # Hybrid auditing pipeline with mode switching
│       ├── evaluation/      # Two-layer diagnostic evaluation
│       └── shared/          # Seeding, config, output formats, schemas
├── tests/
├── data/
│   └── presets/             # Pre-generated gold datasets
├── configs/                 # Preset configurations for paper experiments
├── notebooks/               # Optional Jupyter notebook
├── requirements.txt
├── README.md
└── run.py                   # Entry points for generation, pipeline, evaluation
```

**Rationale:** `src/` layout enables the generator to be independently installable in Phase 2 (domain abstraction layer) without restructuring the project. For MVP, it's clone-and-run via `run.py` or direct module execution; for Phase 2, it becomes `pip install -e .` compatible.

### Dependency Management

**Selected: `requirements.txt`** — academic standard, zero learning curve for researchers.

Core dependencies:
- `openai` — LLM API calls for corpus generation
- `networkx` — Entity graph construction and manipulation
- `numpy` — Numerical operations, seeded randomness
- `scipy` — Statistical significance testing
- `scikit-learn` — Evaluation metrics
- `pytest` — Testing (dev dependency)

### Testing Framework

**Selected: `pytest`** — standard for Python scientific tooling. Tests organized in `tests/` mirroring `src/crossfire/` structure.

### Linting & Type Checking

**Skipped for MVP.** No ruff, black, mypy, or pre-commit hooks. Speed of iteration takes priority over code style enforcement during the 6-8 week timeline.

### Architectural Decisions Established by Foundation

| Decision | Choice | Rationale |
|---|---|---|
| Package layout | `src/crossfire/` | Enables independent generator installation in Phase 2 |
| Entry point | `run.py` + module execution | Clone-and-run for researchers, no CLI framework overhead |
| Dependencies | `requirements.txt` | Academic standard, minimal friction |
| Testing | `pytest` | Standard, no setup overhead |
| Code style | None enforced | MVP speed priority |
| Python version | 3.10+ | Standard for current NLP tooling |

**Note:** Project initialization with this structure should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Output format schema (generator ↔ evaluator contract)
- Pipeline mode switching architecture
- Seeding/reproducibility enforcement
- LLM integration layer

**Deferred Decisions (Post-MVP):**
- Multi-model LLM provider abstraction (Phase 2, contamination prevention)
- Aggregated metric design (deferred per brainstorming)
- Domain abstraction layer interfaces (Phase 2)

### Data Architecture — Output Formats

**Decision: JSONL for documents + JSON for annotations and reports**

- **Corpus documents:** One JSONL file per subcorpus. Each line is a document with metadata (type, subcorpus ID, reliability signal). Streamable, appendable, HuggingFace-compatible.
- **Gold entity graph:** Single JSON file per corpus. NetworkX-serializable adjacency format with entity attributes and relationship types.
- **Gold incoherence labels:** Single JSON file per corpus. Array of incoherence objects with scope, mechanism, detectability, system affinity, and document references.
- **Gold distractor labels:** Single JSON file per corpus. Same structure as incoherence labels, flagged as distractor.
- **Pipeline incoherence reports:** Single JSON file per run. Standardized format across all pipeline modes — array of detected incoherences with evidence references and confidence.
- **Evaluation results:** Single JSON file per evaluation run. Per-scope, per-stage breakdowns with aggregate statistics.
- **Preset configurations:** YAML files in `configs/`. Human-readable, version-controlled.

**Rationale:** JSONL is the NLP dataset standard. Separate files per annotation layer keeps concerns decoupled — the evaluator loads only what it needs. YAML for configs because researchers read and edit these directly.

### Pipeline Architecture — Mode Switching

**Decision: Strategy pattern with injected dependencies**

```
HybridPipeline
├── graph_strategy: GraphStrategy | NullGraphStrategy
├── reasoning_strategy: ReasoningStrategy | NullReasoningStrategy
└── run(corpus) → incoherence_report
```

- **Hybrid mode:** Real graph strategy + real reasoning strategy
- **Agentic mode:** Null graph strategy + real reasoning strategy (CLAIRE-style claim extraction)
- **Graph-native mode:** Real graph strategy + null reasoning strategy (KG structural anomaly detection)

**FR19 contingency:** If graph-native is dropped, delete `GraphStrategy` and `NullReasoningStrategy` implementations. `HybridPipeline` still works with only agentic mode. No conditionals to remove, no dead code paths.

**Rationale:** Each strategy is independently testable. Mode switching is constructor injection, not runtime branching. Adding a new strategy (Phase 3, open architecture) is adding a class, not modifying existing code.

### Seeding & Reproducibility

**Decision: Centralized SeedManager**

```python
class SeedManager:
    def __init__(self, master_seed: int):
        self.master_seed = master_seed

    def get_seed(self, component: str, index: int = 0) -> int:
        # Deterministic derivation from master + component name + index
        return hash((self.master_seed, component, index)) % (2**32)
```

- Every component receives its seed from `SeedManager`, never from `random.seed()` directly
- LLM calls use temperature 0 (deterministic from provider side)
- `SeedManager` is instantiated once per generation/pipeline run from config
- Seed is logged in output metadata for reproducibility verification

**Rationale:** Single point of control for all randomness. Per-component derived seeds prevent collision. Changing master seed changes everything deterministically. Auditable — every output file records the seed that produced it.

### LLM Integration

**Decision: Thin wrapper function**

```python
def llm_call(prompt, model="gpt-4o-mini", temperature=0, seed_manager=None, dry_run=False):
    # Cost estimation logging
    # Dry-run mode returns estimated cost without calling API
    # Retry with exponential backoff on transient errors
    # Fail loudly on non-transient errors (no silent retries)
    # Returns response + token usage for cost tracking
```

- Single function for all LLM interactions
- Cost tracking: accumulates token usage across calls, reports total at end
- Dry-run mode (NFR15): estimates cost from prompt token count without API call
- Graceful failure (NFR14): exponential backoff on rate limits, immediate fail on auth/quota errors
- Multi-model support deferred — thin wrapper handles one provider, refactor to provider abstraction in Phase 2

**Rationale:** Fastest path to working generation. All LLM calls go through one function, making the future refactor to multi-model a single-point change.

### Decision Impact Analysis

**Implementation Sequence:**
1. SeedManager + LLM wrapper (shared infrastructure, everything depends on these)
2. Output format schemas (define the contract before building producer/consumer)
3. Generator pipeline (produces corpora using LLM wrapper and SeedManager)
4. Auditing pipeline with strategy pattern (consumes corpora, produces reports)
5. Evaluation suite (consumes gold annotations + pipeline reports)

**Cross-Component Dependencies:**
- SeedManager → used by generator, injector, pipeline
- LLM wrapper → used by generator (corpus generation, injection) and agentic/hybrid pipeline modes
- Output schemas → produced by generator, consumed by pipeline and evaluator
- Strategy interfaces → define the contract between pipeline and its graph/reasoning components

## Implementation Patterns & Consistency Rules

### Critical Conflict Points

5 areas where AI agents could make inconsistent choices, all resolved below.

### Naming Patterns

**Python Code:**
- Functions/variables: `snake_case` (Python standard)
- Classes: `PascalCase` (Python standard)
- Constants: `UPPER_SNAKE_CASE`
- Module files: `snake_case.py`

**JSON Output Fields: `snake_case`**
- All JSON/JSONL output files use `snake_case` field names: `document_type`, `subcorpus_id`, `system_affinity`
- Pydantic models serialize to snake_case by default — no aliasing needed
- This applies to corpus documents, entity graphs, incoherence labels, distractor labels, pipeline reports, and evaluation results

**Configuration (YAML):**
- Keys use `snake_case` matching JSON convention: `subcorpora_count`, `connectivity_level`

### Schema Enforcement

**Decision: Pydantic models for all data contracts**

- Every output format (corpus document, entity graph node/edge, incoherence label, distractor label, pipeline report entry, evaluation result) has a corresponding Pydantic model in `src/crossfire/shared/schemas/`
- Models enforce types, required fields, and value constraints (e.g., `connectivity_level: Literal[0, 1, 2, 3]`)
- Serialization/deserialization always goes through Pydantic — no raw dict construction
- Schema changes are versioned alongside benchmark versioning (FR16)

**Schema organization:**
```
src/crossfire/shared/schemas/
├── __init__.py
├── corpus.py          # Document, SubcorpusMetadata
├── entities.py        # EntityNode, EntityEdge, EntityGraph
├── incoherences.py    # IncoherenceLabel, DistractorLabel
├── reports.py         # DetectedIncoherence, PipelineReport
├── evaluation.py      # ScopeResult, StageResult, EvaluationResult
└── config.py          # GeneratorConfig, PipelineConfig, PresetConfig
```

**Rationale:** Pydantic gives type validation, JSON serialization, and documentation in one place. If a generator produces a malformed incoherence label, Pydantic catches it at creation time — not when the evaluator reads it three pipeline stages later.

### File I/O Pattern

**Deferred.** Shared loaders/savers vs per-component I/O will be determined during implementation based on actual data complexity. Pydantic models provide the contract regardless of how files are read/written.

### Logging

**Decision: `loguru`**

- All components use `loguru` for logging — no `print()` statements, no stdlib `logging`
- Log levels: `DEBUG` for internal state, `INFO` for progress/milestones, `WARNING` for recoverable issues, `ERROR` for failures
- Generation progress logged at `INFO` level (subcorpus N of M, document N of M)
- LLM API calls logged at `DEBUG` level with token counts
- Cost accumulation logged at `INFO` level at end of generation
- Seed values logged at `INFO` level at start of every run

**Rationale:** `loguru` has zero-config setup, structured output, and better formatting than stdlib logging. Research debugging (why did generation produce different output?) benefits from detailed but filterable logs.

### Error Handling

**Decision: Return-value error handling first, exceptions for unrecoverable failures**

- Functions that can fail return `Result`-style tuples or Optional values — caller decides how to handle
- LLM wrapper returns `(response, error)` — caller can retry, skip, or abort
- Pydantic validation errors are caught at component boundaries and returned as error values
- Exceptions reserved for truly unrecoverable situations: missing config files, invalid master seed, file permission errors
- No custom exception hierarchy — keep it simple

**Pattern:**
```python
# Good: return-value error
def generate_document(params, llm, seed_mgr) -> tuple[Document | None, str | None]:
    response, error = llm_call(prompt, ...)
    if error:
        return None, f"LLM call failed: {error}"
    return Document(**parse(response)), None

# Good: exception for unrecoverable
def load_config(path: str) -> GeneratorConfig:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    return GeneratorConfig.parse_file(path)
```

**Rationale:** Return-value errors make failure handling explicit and visible in code flow. Researchers debugging "why did my generation produce 398 docs instead of 400" can trace exactly which documents failed and why, rather than hunting through exception stack traces.

### Enforcement Guidelines

**All AI agents implementing CROSSFIRE MUST:**
- Define Pydantic models for any new data structure before writing producer/consumer code
- Use `snake_case` for all JSON field names — no exceptions
- Use `loguru` for all output — no `print()` statements
- Return error values from fallible functions — no exceptions for expected failures
- Obtain seeds from `SeedManager` — never call `random.seed()` directly

**Anti-Patterns:**
- Constructing raw dicts instead of Pydantic model instances
- Using camelCase in JSON output "because JavaScript convention"
- Catching and silencing errors with bare `except: pass`
- Hardcoding seeds or using `random.random()` without SeedManager
- Using `print()` for debugging and leaving it in

## Project Structure & Boundaries

### Complete Project Directory Structure

```
crossfire/
├── README.md
├── requirements.txt
├── run.py                              # CLI entry points: generate, pipeline, evaluate
├── .gitignore
├── configs/
│   ├── presets/
│   │   ├── default.yaml                # 5 subcorpora, connectivity 2, balanced
│   │   ├── low_connectivity.yaml       # Connectivity 0-1, agentic-favoring
│   │   ├── high_connectivity.yaml      # Connectivity 3, graph-favoring
│   │   └── stress_test.yaml            # Maximum parameters for scale testing
│   └── example_custom.yaml             # Documented example for custom configs
├── data/
│   └── datasets/                        # Pre-generated gold datasets (FR30)
│       ├── default/
│       │   ├── corpus/                  # JSONL files per subcorpus
│       │   ├── gold/                    # Entity graph + labels JSON
│       │   └── metadata.json            # Generation params, seed, version
│       ├── low_connectivity/
│       ├── high_connectivity/
│       └── stress_test/
├── src/
│   └── crossfire/
│       ├── __init__.py
│       ├── shared/
│       │   ├── __init__.py
│       │   ├── seed_manager.py          # Centralized SeedManager
│       │   ├── llm.py                   # Thin LLM wrapper (llm_call)
│       │   ├── io.py                    # File I/O utilities (if needed)
│       │   └── schemas/
│       │       ├── __init__.py
│       │       ├── corpus.py            # Document, SubcorpusMetadata
│       │       ├── entities.py          # EntityNode, EntityEdge, EntityGraph
│       │       ├── incoherences.py      # IncoherenceLabel, DistractorLabel
│       │       ├── reports.py           # DetectedIncoherence, PipelineReport
│       │       ├── evaluation.py        # ScopeResult, StageResult, EvaluationResult
│       │       └── config.py            # GeneratorConfig, PipelineConfig, PresetConfig
│       ├── generator/
│       │   ├── __init__.py
│       │   ├── corpus_generator.py      # Orchestrates subcorpus + document generation (FR1-FR5)
│       │   ├── document_factory.py      # Produces individual documents by type
│       │   ├── entity_graph_builder.py  # Builds gold entity graph (FR13)
│       │   ├── injector.py              # Incoherence injection with minimal-pair (FR6-FR12)
│       │   ├── distractor_generator.py  # Produces distractor labels (FR11, FR15)
│       │   ├── annotator.py             # Produces gold incoherence labels (FR14)
│       │   └── templates/               # NTSB document type templates/prompts
│       │       ├── investigation_report.py
│       │       ├── technical_analysis.py
│       │       ├── witness_testimony.py
│       │       ├── regulatory_filing.py
│       │       ├── press_coverage.py
│       │       ├── expert_deposition.py
│       │       ├── internal_memo.py
│       │       └── preliminary_report.py
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── hybrid_pipeline.py       # Main pipeline with strategy injection (FR17-FR20)
│       │   ├── strategies/
│       │   │   ├── __init__.py
│       │   │   ├── base.py              # GraphStrategy, ReasoningStrategy interfaces
│       │   │   ├── graph_strategy.py    # KG construction + anomaly detection (FR19)
│       │   │   ├── reasoning_strategy.py # LLM claim extraction + cross-checking (FR18)
│       │   │   └── null_strategies.py   # NullGraphStrategy, NullReasoningStrategy
│       │   └── baselines/
│       │       ├── __init__.py
│       │       ├── hypothesis_only.py   # Surface feature detection (FR21)
│       │       ├── random_baseline.py   # Random guess baseline (FR22)
│       │       └── bm25_baseline.py     # BM25 keyword contradiction (FR22)
│       └── evaluation/
│           ├── __init__.py
│           ├── evaluator.py             # Main evaluation orchestrator
│           ├── binary_scorer.py         # Exact match scoring (FR23)
│           ├── partial_scorer.py        # Localization proximity scoring (FR24)
│           ├── scope_breakdown.py       # Per-scope analysis (FR25)
│           ├── stage_breakdown.py       # Per-stage analysis (FR26)
│           ├── representation_eval.py   # Layer 1: KG vs gold graph (FR27)
│           ├── distractor_eval.py       # False positive rate on distractors (FR28)
│           └── aggregate.py             # Multi-seed aggregation + significance (FR29)
├── tests/
│   ├── conftest.py                      # Shared fixtures, test SeedManager
│   ├── shared/
│   │   ├── test_seed_manager.py
│   │   ├── test_llm.py
│   │   └── test_schemas.py
│   ├── generator/
│   │   ├── test_corpus_generator.py
│   │   ├── test_injector.py
│   │   └── test_annotator.py
│   ├── pipeline/
│   │   ├── test_hybrid_pipeline.py
│   │   ├── test_strategies.py
│   │   └── test_baselines.py
│   └── evaluation/
│       ├── test_binary_scorer.py
│       ├── test_partial_scorer.py
│       └── test_scope_breakdown.py
└── notebooks/
    └── walkthrough.ipynb                # Optional end-to-end demo
```

### Architectural Boundaries

**Generator → Pipeline Boundary:**
- Generator produces: corpus JSONL files + gold annotation JSON files
- Pipeline consumes: corpus JSONL files only (no access to gold annotations)
- Contract: `Document` and `SubcorpusMetadata` Pydantic schemas

**Pipeline → Evaluator Boundary:**
- Pipeline produces: `PipelineReport` JSON (standardized across all modes)
- Evaluator consumes: `PipelineReport` + gold annotation JSON files
- Contract: `PipelineReport` and `IncoherenceLabel` Pydantic schemas

**Shared Infrastructure → All Components:**
- `SeedManager` injected into generator, pipeline, and evaluator at initialization
- `llm_call` used by generator (corpus generation, injection) and pipeline (agentic/hybrid modes)
- Pydantic schemas imported by all components for serialization/deserialization

**Strategy Boundary (Pipeline Internal):**
- `HybridPipeline` depends only on `GraphStrategy` and `ReasoningStrategy` interfaces
- Concrete implementations are injected — pipeline doesn't know which mode it's running
- Null strategies produce empty results, not errors

### Requirements to Structure Mapping

| FR Category | Directory | Key Files |
|---|---|---|
| Corpus Generation (FR1-FR5) | `src/crossfire/generator/` | `corpus_generator.py`, `document_factory.py`, `templates/` |
| Incoherence Injection (FR6-FR12) | `src/crossfire/generator/` | `injector.py`, `distractor_generator.py` |
| Gold Annotation (FR13-FR16) | `src/crossfire/generator/` | `entity_graph_builder.py`, `annotator.py` |
| Auditing Pipelines (FR17-FR22) | `src/crossfire/pipeline/` | `hybrid_pipeline.py`, `strategies/`, `baselines/` |
| Evaluation & Diagnostics (FR23-FR29) | `src/crossfire/evaluation/` | All evaluator modules |
| Data & Output Management (FR30-FR33) | `data/datasets/`, `configs/`, `README.md` | Pre-generated datasets, preset configs |

### Data Flow

```
configs/presets/*.yaml
       │
       ▼
┌─────────────┐    corpus JSONL     ┌──────────────┐    PipelineReport    ┌─────────────┐
│  Generator   │ ──────────────────▶│   Pipeline    │ ──────────────────▶│  Evaluator   │
│  (FR1-FR16)  │    gold JSON       │  (FR17-FR22)  │                     │  (FR23-FR29) │
│              │ ──────────────────────────────────────────────────────▶│              │
└─────────────┘                     └──────────────┘                     └─────────────┘
       │                                    │                                    │
       ▼                                    ▼                                    ▼
  data/datasets/                   output/reports/                     output/evaluation/
```

- Generator writes corpus + gold to `data/datasets/` or `output/generated/`
- Pipeline reads corpus only, writes report to `output/reports/`
- Evaluator reads gold + report, writes results to `output/evaluation/`
- Pipeline NEVER reads gold annotations — this is a hard architectural boundary

## Architecture Validation Results

### Coherence Validation ✓

**Decision Compatibility:**
- Python 3.10+ / Pydantic / NetworkX / loguru / pytest / python-dotenv — all compatible, no version conflicts
- Thin LLM wrapper + SeedManager + Pydantic schemas form a coherent shared infrastructure layer
- Strategy pattern for pipeline modes is compatible with all evaluation approaches

**Pattern Consistency:**
- snake_case enforced across Python code, JSON output, and YAML config — no convention splits
- Return-value error handling is consistent with loguru logging (errors logged, then returned)
- Pydantic models as the universal data contract — generator, pipeline, and evaluator all speak the same schema language

**Structure Alignment:**
- `src/crossfire/` with `shared/`, `generator/`, `pipeline/`, `evaluation/` maps cleanly to the 4 architectural subsystems
- Strategy pattern files live inside `pipeline/strategies/` — boundary is physical, not just logical
- Test structure mirrors source structure — no ambiguity about where tests go

### Requirements Coverage Validation ✓

**Functional Requirements (33/33 covered):**

| FR | Architectural Support |
|---|---|
| FR1-FR5 | `generator/corpus_generator.py`, `document_factory.py`, `templates/` |
| FR6-FR12 | `generator/injector.py`, `distractor_generator.py`, `llm.py` |
| FR13 | `generator/entity_graph_builder.py` → `schemas/entities.py` |
| FR14-FR15 | `generator/annotator.py` → `schemas/incoherences.py` |
| FR16 | `version` field in `metadata.json` per dataset |
| FR17-FR19 | `pipeline/hybrid_pipeline.py` + `strategies/` (FR19 contingent) |
| FR20 | `schemas/reports.py` enforces standardized format |
| FR21-FR22 | `pipeline/baselines/` |
| FR23-FR24 | `evaluation/binary_scorer.py`, `partial_scorer.py` |
| FR25-FR26 | `evaluation/scope_breakdown.py`, `stage_breakdown.py` |
| FR27 | `evaluation/representation_eval.py` |
| FR28 | `evaluation/distractor_eval.py` |
| FR29 | `evaluation/aggregate.py` |
| FR30 | `data/datasets/` with pre-generated gold datasets |
| FR31 | `schemas/corpus.py` defines Document with metadata |
| FR32 | JSONL + JSON format decision |
| FR33 | `README.md` |

**Non-Functional Requirements (15/15 covered):**

| NFR | Architectural Support |
|---|---|
| NFR1-NFR4 (Reproducibility) | SeedManager, temperature 0, deterministic evaluation |
| NFR5-NFR8 (Correctness) | Pydantic validation at creation time, schema enforcement |
| NFR9-NFR12 (Portability) | No GPU, standard Python ecosystem, Linux/macOS |
| NFR13-NFR15 (Cost) | LLM wrapper with cost tracking, dry-run mode, graceful failure |

### Gaps Resolved

| Gap | Resolution |
|---|---|
| Missing `pydantic`, `loguru` in dependencies | Added to requirements.txt |
| API key management | `.env` file loaded via `python-dotenv` |
| `output/` directory undocumented | Runtime output directory, gitignored |
| Benchmark versioning (FR16) | `version` field in `metadata.json` per dataset |

### Updated Dependencies

```
requirements.txt:
  openai
  networkx
  numpy
  scipy
  scikit-learn
  pydantic
  loguru
  python-dotenv
  pyyaml
  pytest  # dev
```

### Updated Project Root Files

```
crossfire/
├── .env                   # OPENAI_API_KEY (gitignored)
├── .env.example           # Template with placeholder values
├── .gitignore             # Includes .env, output/, __pycache__, etc.
├── output/                # Runtime output (gitignored)
│   ├── generated/         # Generator output for custom runs
│   ├── reports/           # Pipeline incoherence reports
│   └── evaluation/        # Evaluation results
...
```

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed (33 FRs, 15 NFRs)
- [x] Scale and complexity assessed (medium, batch pipeline)
- [x] Technical constraints identified (Python 3.10+, no GPU, API costs)
- [x] Cross-cutting concerns mapped (seeding, schemas, output formats, contamination prevention)

**✅ Architectural Decisions**
- [x] Data architecture: JSONL + JSON + YAML
- [x] Pipeline architecture: Strategy pattern with injected dependencies
- [x] Reproducibility: Centralized SeedManager
- [x] LLM integration: Thin wrapper with cost tracking and dry-run
- [x] Schema enforcement: Pydantic models for all data contracts
- [x] Logging: loguru
- [x] Error handling: Return-value first, exceptions for unrecoverable

**✅ Implementation Patterns**
- [x] Naming conventions: snake_case everywhere
- [x] Schema enforcement: Pydantic before producer/consumer code
- [x] Logging: loguru only, no print statements
- [x] Error handling: Return-value errors for expected failures
- [x] Seeding: SeedManager only, no direct random calls

**✅ Project Structure**
- [x] Complete directory structure with FR mapping
- [x] Component boundaries defined (generator → pipeline → evaluator)
- [x] Hard boundary: pipeline never reads gold annotations
- [x] Data flow documented with input/output per subsystem

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**
- Clean separation between generator, pipeline, and evaluator with Pydantic schema contracts
- Strategy pattern makes FR19 contingency (drop graph-native) architecturally trivial
- SeedManager enforces reproducibility at the architectural level, not per-component
- Every FR maps to a specific file — no ambiguity about where to implement

**Areas for Future Enhancement (Phase 2+):**
- LLM provider abstraction for multi-model generation
- Domain abstraction layer for non-NTSB corpus generation
- Formal Python API with documented public interfaces
- Aggregated metric design (deferred, implementation will inform design)

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use Pydantic models for every data structure — no raw dicts
- Respect component boundaries — pipeline never reads gold annotations
- Use SeedManager for all randomness — no direct random calls
- Use loguru for all output — no print statements
- Return error values from fallible functions — exceptions only for unrecoverable

**Implementation Sequence:**
1. Project scaffolding (directory structure, requirements.txt, .env, .gitignore)
2. Shared infrastructure (SeedManager, LLM wrapper, Pydantic schemas)
3. Generator (corpus generation → injection → annotation)
4. Pipeline (strategy interfaces → hybrid pipeline → baselines)
5. Evaluation (scorers → breakdowns → aggregation)
6. Pre-generated datasets (run generator with preset configs, commit to data/datasets/)
7. README (reproduction instructions)
