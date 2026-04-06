---
stepsCompleted:
  - "step-01-validate-prerequisites"
  - "step-02-design-epics"
  - "step-03-create-stories"
  - "step-04-final-validation"
status: 'complete'
completedAt: '2026-04-06'
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/architecture.md"
---

# CROSSFIRE - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for CROSSFIRE, decomposing the requirements from the PRD and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

- FR1: Researcher can generate a multi-source document corpus in the NTSB/industrial incident domain with configurable parameters (subcorpora count, documents per subcorpus, document type mix)
- FR2: Researcher can configure connectivity level between subcorpora (level 0: no shared entities, level 1: identical naming, level 2: paraphrased naming, level 3: dense shared entities)
- FR3: Researcher can specify a random seed to produce identical corpora across runs and machines
- FR4: Researcher can select from 3-4 preset configurations that reproduce the paper's experimental conditions
- FR5: Researcher can generate corpora containing heterogeneous document types (investigation reports, technical analyses, witness testimonies, regulatory filings, press coverage, expert depositions, internal memos, preliminary reports)
- FR6: Researcher can configure incoherence scope distribution (intra-document, intra-subcorpus cross-document, inter-subcorpus)
- FR7: Researcher can configure incoherence mechanism (numeric drift, entity swap, causal inversion, temporal contradiction, omission-based implicit, temporal revision conflict)
- FR8: Researcher can configure incoherence detectability distribution (single-hop, multi-hop, entity-resolution-dependent)
- FR9: Researcher can configure system affinity (balanced, graph-favoring, agentic-favoring)
- FR10: Generator produces incoherences using minimal-pair construction (modifying only the target fact, not surrounding prose)
- FR11: Generator produces distractor labels (legitimate perspective divergences that should NOT be flagged as incoherences) at a configurable ratio
- FR12: Generator uses same LLM temperature and prompt structure for original and modified text to prevent stylistic tells
- FR13: Generator produces a gold entity graph capturing all entities and relationships across the corpus
- FR14: Generator produces gold incoherence labels identifying every injected incoherence with its scope, mechanism, detectability, and system affinity metadata
- FR15: Generator produces gold distractor labels identifying every legitimate divergence
- FR16: Gold annotations are versioned — label corrections trigger a new benchmark version identifier
- FR17: Researcher can run a hybrid auditing pipeline (graph representation + LLM-driven reasoning) against a generated corpus
- FR18: Researcher can run an agentic auditing pipeline (claim extraction + cross-checking, graph layer disabled) against a generated corpus
- FR19: Researcher can run a graph-native auditing pipeline (KG construction + structural anomaly detection, LLM reasoning disabled) against a generated corpus — contingent on experimental feasibility
- FR20: All pipeline modes produce incoherence reports in a standardized output format enabling cross-pipeline comparison
- FR21: Researcher can run a hypothesis-only baseline that evaluates whether incoherences are detectable from surface features alone (contamination validation)
- FR22: Researcher can run trivial baselines (random, BM25 keyword contradiction) for lower-bound comparison
- FR23: Researcher can evaluate a pipeline's incoherence report against gold labels using binary (exact match) scoring
- FR24: Researcher can evaluate a pipeline's incoherence report against gold labels using partial credit (localization proximity) scoring
- FR25: Researcher can view evaluation results broken down per-scope (intra-document, intra-subcorpus, inter-subcorpus) independently
- FR26: Researcher can view evaluation results broken down per-stage (entity resolution, graph construction, scanning) independently without cascading failures
- FR27: Researcher can evaluate a pipeline's internal knowledge graph against the gold entity graph (Layer 1: representation quality)
- FR28: Researcher can measure false positive rate on distractor labels separately from incoherence detection accuracy
- FR29: Researcher can run evaluation across multiple seeds and obtain aggregate statistics with significance measures
- FR30: Researcher can use pre-generated gold baseline datasets included in the repository without running the generator
- FR31: Generator outputs corpus documents with metadata (document type, subcorpus membership, reliability signal)
- FR32: All outputs (corpora, annotations, evaluation results) are stored in documented, machine-readable formats
- FR33: README provides instructions sufficient to clone the repo, install dependencies, and reproduce all published experimental results

### Non-Functional Requirements

- NFR1: Same seed + same parameters produces bit-identical corpus output across runs, machines, and operating systems
- NFR2: Evaluation scripts are fully deterministic — identical inputs produce identical scores with no variance
- NFR3: Pre-generated datasets run through shipped pipelines reproduce published baseline numbers exactly
- NFR4: All sources of randomness (Python random, numpy, LLM generation) are seeded and documented
- NFR5: Gold annotations are verifiably correct — every injected incoherence is labeled, no false labels exist in shipped datasets
- NFR6: Evaluation scoring is mathematically correct against gold labels — no off-by-one errors, no input/label misalignment
- NFR7: Minimal-pair construction does not introduce unintended secondary incoherences beyond the target modification
- NFR8: Gold entity graph accurately represents all entities and relationships present in the generated corpus
- NFR9: Runs on Linux and macOS without platform-specific dependencies
- NFR10: No GPU requirement for corpus generation or evaluation (LLM calls are API-based)
- NFR11: Reference pipelines executable on academic-grade hardware (consumer GPU or CPU-only with API calls)
- NFR12: Python 3.10+ with standard scientific Python ecosystem (no exotic or platform-locked dependencies)
- NFR13: Generation cost per subcorpus is estimable before execution (~$5-20 with GPT-4o-mini at default scale)
- NFR14: Generation fails gracefully on API errors with clear reporting — no silent retries that accumulate charges
- NFR15: Dry-run or cost estimation mode available before committing to full generation

### Additional Requirements (Architecture)

- AR1: Project uses src/crossfire/ layout with importable package structure
- AR2: Pydantic models for all data contracts — no raw dict construction
- AR3: Centralized SeedManager for all randomness — no direct random.seed() calls
- AR4: Thin LLM wrapper (llm_call) for all LLM interactions with cost tracking and dry-run mode
- AR5: Strategy pattern for pipeline mode switching — GraphStrategy/ReasoningStrategy injected dependencies
- AR6: loguru for all logging — no print() statements
- AR7: Return-value error handling for expected failures, exceptions only for unrecoverable
- AR8: JSONL for corpus documents, JSON for annotations/reports, YAML for configs
- AR9: .env file with python-dotenv for API key management
- AR10: Benchmark version field in metadata.json per dataset
- AR11: Pipeline NEVER reads gold annotations — hard architectural boundary
- AR12: output/ directory for runtime output (gitignored)

### UX Design Requirements

N/A — CLI/research tool, no UX design document.

### FR Coverage Map

| FR | Epic | Description |
|---|---|---|
| FR1 | Epic 2 | Configurable corpus generation |
| FR2 | Epic 2 | Connectivity level configuration |
| FR3 | Epic 1 | Seeded generation (SeedManager) |
| FR4 | Epic 2 | Preset configurations |
| FR5 | Epic 2 | Heterogeneous document types |
| FR6 | Epic 3 | Incoherence scope distribution |
| FR7 | Epic 3 | Incoherence mechanism configuration |
| FR8 | Epic 3 | Incoherence detectability distribution |
| FR9 | Epic 3 | System affinity configuration |
| FR10 | Epic 3 | Minimal-pair construction |
| FR11 | Epic 3 | Distractor labels at configurable ratio |
| FR12 | Epic 3 | Same LLM temp/prompt for contamination prevention |
| FR13 | Epic 2 | Gold entity graph production |
| FR14 | Epic 3 | Gold incoherence labels with metadata |
| FR15 | Epic 3 | Gold distractor labels |
| FR16 | Epic 3 | Annotation versioning |
| FR17 | Epic 4 | Hybrid pipeline |
| FR18 | Epic 4 | Agentic pipeline |
| FR19 | Epic 4 | Graph-native pipeline (contingent) |
| FR20 | Epic 4 | Standardized report format |
| FR21 | Epic 4 | Hypothesis-only baseline |
| FR22 | Epic 4 | Trivial baselines (random, BM25) |
| FR23 | Epic 5 | Binary scoring |
| FR24 | Epic 5 | Partial credit scoring |
| FR25 | Epic 5 | Per-scope breakdown |
| FR26 | Epic 5 | Per-stage breakdown |
| FR27 | Epic 5 | Representation quality evaluation |
| FR28 | Epic 5 | Distractor false positive rate |
| FR29 | Epic 5 | Multi-seed aggregation + significance |
| FR30 | Epic 6 | Pre-generated gold datasets |
| FR31 | Epic 2 | Document metadata in output |
| FR32 | Epic 1 | Machine-readable output formats (schemas) |
| FR33 | Epic 6 | README for reproduction |

## Epic List

### Epic 1: Project Foundation & Shared Infrastructure
Establish the runnable project with all shared contracts and infrastructure that every subsequent epic depends on.
**FRs covered:** FR3, FR32
**ARs covered:** AR1-AR12
**NFRs enforced:** NFR1-NFR4 (seeding), NFR9-NFR12 (portability), NFR13-NFR15 (cost predictability)

### Epic 2: Corpus Generation
Researcher can generate multi-source document corpora with configurable parameters, connectivity levels, and a gold entity graph.
**FRs covered:** FR1, FR2, FR4, FR5, FR13, FR31

### Epic 3: Incoherence Injection & Gold Annotation
Generator injects controlled incoherences into corpora and produces complete gold annotations (incoherence labels, distractor labels, versioned metadata).
**FRs covered:** FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR14, FR15, FR16

### Epic 4: Auditing Pipelines
Researcher can run auditing systems against generated corpora in three modes (hybrid, agentic, graph-native) plus baselines, producing standardized incoherence reports.
**FRs covered:** FR17, FR18, FR19, FR20, FR21, FR22

### Epic 5: Evaluation & Diagnostics
Researcher can evaluate pipeline results with diagnostic granularity — binary/partial scoring, per-scope, per-stage, representation quality, distractor false positives, multi-seed aggregation.
**FRs covered:** FR23, FR24, FR25, FR26, FR27, FR28, FR29

### Epic 6: Benchmark Release
Ship pre-generated gold datasets, complete README, and verify end-to-end reproducibility.
**FRs covered:** FR30, FR33

---

## Epic 1: Project Foundation & Shared Infrastructure

Establish the runnable project with all shared contracts and infrastructure that every subsequent epic depends on.

### Story 1.1: Project Scaffolding

As a developer,
I want the complete project directory structure with dependencies and configuration,
So that I can clone the repo, install dependencies, and start building components.

**Acceptance Criteria:**

**Given** a fresh clone of the repository
**When** I run `pip install -r requirements.txt`
**Then** all dependencies install successfully (openai, networkx, numpy, scipy, scikit-learn, pydantic, loguru, python-dotenv, pyyaml, pytest)
**And** the `src/crossfire/` package structure exists with `shared/`, `generator/`, `pipeline/`, `evaluation/` directories and `__init__.py` files
**And** `.env.example` exists with `OPENAI_API_KEY=your-key-here`
**And** `.gitignore` excludes `.env`, `output/`, `__pycache__/`, `*.pyc`
**And** `configs/presets/` contains YAML preset files (default, low_connectivity, high_connectivity, stress_test)
**And** `output/` directory structure exists (generated/, reports/, evaluation/)

### Story 1.2: Pydantic Schemas for All Data Contracts

As a developer,
I want all data contracts defined as Pydantic models,
So that every component produces and consumes validated, type-safe data structures.

**Acceptance Criteria:**

**Given** the schemas module at `src/crossfire/shared/schemas/`
**When** I import from schemas
**Then** `corpus.py` exports `Document` and `SubcorpusMetadata` models with fields for document_type, subcorpus_id, reliability_signal, and content
**And** `entities.py` exports `EntityNode`, `EntityEdge`, and `EntityGraph` models serializable to NetworkX adjacency JSON
**And** `incoherences.py` exports `IncoherenceLabel` with scope, mechanism, detectability, system_affinity, and document_references fields, plus `DistractorLabel` with same structure
**And** `reports.py` exports `DetectedIncoherence` and `PipelineReport` with evidence_references and confidence fields
**And** `evaluation.py` exports `ScopeResult`, `StageResult`, and `EvaluationResult` with per-scope and per-stage breakdowns
**And** `config.py` exports `GeneratorConfig`, `PipelineConfig`, and `PresetConfig` matching YAML preset structure
**And** all models serialize to snake_case JSON and deserialize back without data loss

### Story 1.3: Centralized SeedManager

As a researcher,
I want deterministic, reproducible execution controlled by a single master seed,
So that identical parameters produce identical results across runs and machines.

**Acceptance Criteria:**

**Given** a `SeedManager` initialized with master_seed=42
**When** I call `get_seed("generator", 0)` and `get_seed("pipeline", 0)`
**Then** each returns a deterministic integer derived from the master seed + component name + index
**And** the same master_seed always produces the same derived seeds
**And** different component names produce different seeds (no collision)
**And** `SeedManager` is importable from `src/crossfire/shared/seed_manager.py`
**And** seed values are logged at INFO level via loguru at initialization
**And** pytest tests verify determinism across multiple instantiations

### Story 1.4: Thin LLM Wrapper

As a developer,
I want a single function for all LLM API interactions with cost tracking and dry-run mode,
So that all generation goes through one controlled, auditable interface.

**Acceptance Criteria:**

**Given** an `llm_call` function in `src/crossfire/shared/llm.py`
**When** I call `llm_call(prompt, model="gpt-4o-mini", temperature=0)`
**Then** it calls the OpenAI API and returns `(response_text, error)` tuple
**And** the API key is loaded from `.env` via python-dotenv
**And** token usage is tracked and accumulated across calls
**And** total cost is loggable at INFO level at any point
**When** I call `llm_call(prompt, dry_run=True)`
**Then** it returns estimated token count and cost without making an API call
**When** the API returns a rate limit error
**Then** it retries with exponential backoff up to 3 times
**When** the API returns an auth or quota error
**Then** it returns immediately with `(None, error_message)` — no retry

---

## Epic 2: Corpus Generation

Researcher can generate multi-source document corpora with configurable parameters, connectivity levels, and a gold entity graph.

### Story 2.1: NTSB Data Scraping & Structure Analysis

As a researcher,
I want to scrape and analyze real NTSB investigation dockets,
So that the generator's document types, entity patterns, and corpus structure are grounded in real-world data.

**Acceptance Criteria:**

**Given** access to data.ntsb.gov docket search
**When** I run the NTSB scraping script
**Then** it identifies and downloads 5-8 major accident dockets with shared entities (companies, equipment, regulators across incidents)
**And** it catalogs document types present in each docket (reports, testimonies, technical analyses, regulatory filings, etc.)
**And** it analyzes entity density and natural overlap patterns across dockets
**And** it produces a structured analysis report documenting: document type taxonomy discovered, entity types and frequency, cross-docket entity sharing patterns, and document length/structure characteristics
**And** the analysis informs the document type templates in Story 2.2 (real structure, not assumed)
**And** if scraping fails or data is too sparse (3-day timebox), the analysis documents what was found and the decision to proceed with fully synthetic generation informed by whatever structure was observed

### Story 2.2: Document Type Templates

As a developer,
I want LLM prompt templates for each NTSB document type,
So that the generator can produce realistic, domain-appropriate documents.

**Acceptance Criteria:**

**Given** the templates module at `src/crossfire/generator/templates/`
**When** I load a template for any of the 8 document types (investigation_report, technical_analysis, witness_testimony, regulatory_filing, press_coverage, expert_deposition, internal_memo, preliminary_report)
**Then** each template provides a prompt that accepts entity references, subcorpus context, and document-specific parameters
**And** each template produces documents with distinct voice, structure, and content style appropriate to the document type
**And** templates accept a SeedManager-derived seed for reproducible generation
**And** a `document_factory.py` exposes a `create_document(doc_type, entities, context, llm, seed_mgr)` function that dispatches to the correct template
**And** the factory returns a `(Document, error)` tuple following return-value error handling

### Story 2.3: Entity Graph Builder

As a researcher,
I want the generator to produce a gold entity graph with configurable connectivity,
So that I have ground-truth entity relationships for evaluation.

**Acceptance Criteria:**

**Given** a `GeneratorConfig` with `subcorpora_count=5` and `connectivity_level=2`
**When** I run the entity graph builder
**Then** it produces an `EntityGraph` with entities (companies, equipment, regulators, locations, people) distributed across subcorpora
**And** at connectivity level 0, no entities are shared across subcorpora
**And** at connectivity level 1, shared entities use identical naming across subcorpora
**And** at connectivity level 2, shared entities use paraphrased/abbreviated naming (entity resolution challenge)
**And** at connectivity level 3, dense shared entities exist across subcorpora with mixed naming
**And** the entity graph is serializable to NetworkX adjacency JSON format
**And** entity nodes include attributes (type, canonical_name, aliases, subcorpus_memberships)
**And** the builder uses SeedManager for all random entity placement and naming decisions

### Story 2.4: Corpus Generator Orchestrator

As a researcher,
I want to generate a complete multi-source corpus from a configuration file,
So that I can produce evaluation-ready document collections with a single command.

**Acceptance Criteria:**

**Given** a preset YAML config (e.g., `configs/presets/default.yaml`) specifying subcorpora_count, docs_per_subcorpus, connectivity_level, and doc_type_mix
**When** I run the corpus generator
**Then** it builds the entity graph via Story 2.3
**And** generates documents for each subcorpus using document templates from Story 2.2, with entities from the graph woven into document content
**And** outputs one JSONL file per subcorpus in the output directory, each line being a serialized `Document`
**And** outputs the gold entity graph as a JSON file
**And** outputs a `metadata.json` with generation parameters, master seed, timestamp, and benchmark version
**And** each `Document` includes metadata: document_type, subcorpus_id, reliability_signal (FR31)
**And** the doc_type_mix parameter controls the proportion of each document type per subcorpus
**And** generation progress is logged at INFO level (subcorpus N of M, document N of M)
**And** total LLM cost is logged at INFO level upon completion

---

## Epic 3: Incoherence Injection & Gold Annotation

Generator injects controlled incoherences into corpora and produces complete gold annotations.

### Story 3.1: Incoherence Injector

As a researcher,
I want controlled incoherences injected into generated corpora using the 4D design space,
So that the benchmark tests specific detection capabilities with known ground truth.

**Acceptance Criteria:**

**Given** a generated corpus (from Epic 2) and an incoherence configuration specifying scope_distribution, mechanism, detectability_distribution, system_affinity, and count
**When** I run the injector
**Then** it modifies existing documents using minimal-pair construction — changing only the target fact, not surrounding prose (FR10)
**And** it uses the same LLM temperature and prompt structure for both original and modified text to prevent stylistic tells (FR12)
**And** incoherences are distributed across the configured scope axis: intra-document, intra-subcorpus cross-document, inter-subcorpus (FR6)
**And** incoherence mechanisms are applied per configuration: numeric drift, entity swap, causal inversion, temporal contradiction, omission-based implicit, temporal revision conflict (FR7)
**And** detectability levels are distributed per configuration: single-hop, multi-hop, entity-resolution-dependent (FR8)
**And** system affinity is applied per configuration: balanced, graph-favoring, agentic-favoring (FR9)
**And** each injected incoherence is tracked with full metadata (scope, mechanism, detectability, system_affinity, source_document_refs, modified_fact, original_fact)
**And** the injector uses SeedManager for all random selection decisions
**And** injection count is configurable (fixed or "auto" for empirical tuning)

### Story 3.2: Distractor Generator

As a researcher,
I want legitimate perspective divergences planted alongside real incoherences,
So that the benchmark measures whether systems can distinguish contradictions from valid disagreements.

**Acceptance Criteria:**

**Given** a generated corpus and a `distractor_ratio` parameter (e.g., 0.3)
**When** I run the distractor generator
**Then** it produces perspective divergences that should NOT be flagged as incoherences (FR11)
**And** distractors include: differing expert opinions, preliminary vs final assessments, different measurement methodologies yielding different numbers, legitimate uncertainty expressions
**And** the number of distractors is proportional to the configured ratio relative to incoherence count
**And** each distractor is tracked as a `DistractorLabel` with document references and divergence type
**And** distractors are indistinguishable in format from real incoherences — the only difference is the gold label
**And** the generator uses SeedManager for all random decisions

### Story 3.3: Gold Annotation Assembler

As a researcher,
I want complete, versioned gold annotations produced alongside every generated corpus,
So that evaluation has reliable ground truth with full traceability.

**Acceptance Criteria:**

**Given** a corpus with injected incoherences (Story 3.1) and distractors (Story 3.2)
**When** I run the gold annotation assembler
**Then** it produces a gold incoherence labels JSON file containing every injected incoherence with scope, mechanism, detectability, system_affinity, and document references (FR14)
**And** it produces a gold distractor labels JSON file identifying every legitimate divergence (FR15)
**And** both files validate against their respective Pydantic schemas
**And** `metadata.json` is updated with a `version` field — label corrections trigger a new version identifier (FR16)
**And** the assembler cross-validates: every incoherence in the labels file corresponds to an actual modification in the corpus documents
**And** the assembler logs total counts at INFO level: N incoherences (X intra-doc, Y intra-subcorpus, Z inter-subcorpus), M distractors

---

## Epic 4: Auditing Pipelines

Researcher can run auditing systems against generated corpora in three modes plus baselines, producing standardized incoherence reports.

### Story 4.1: Strategy Interfaces & Pipeline Skeleton

As a developer,
I want the strategy interfaces and hybrid pipeline skeleton with mode switching,
So that all pipeline modes produce reports through a single, consistent architecture.

**Acceptance Criteria:**

**Given** the pipeline module at `src/crossfire/pipeline/`
**When** I import the strategy interfaces
**Then** `base.py` exports abstract `GraphStrategy` and `ReasoningStrategy` with a `run(corpus) → result` interface
**And** `null_strategies.py` exports `NullGraphStrategy` (returns empty graph) and `NullReasoningStrategy` (returns empty detections)
**And** `hybrid_pipeline.py` exports `HybridPipeline` that accepts graph_strategy and reasoning_strategy as constructor arguments
**And** `HybridPipeline.run(corpus_path)` loads corpus JSONL, runs both strategies, merges results, and outputs a `PipelineReport` JSON (FR20)
**And** the pipeline NEVER loads gold annotation files — only corpus documents (AR11)
**And** running with both null strategies produces a valid but empty `PipelineReport`
**And** the pipeline uses SeedManager for any random decisions
**And** pytest tests verify mode switching: hybrid (both real), agentic (null graph), graph-native (null reasoning)

### Story 4.2: Reasoning Strategy (Agentic Mode)

As a researcher,
I want an LLM-agentic auditing pipeline that extracts claims and cross-checks them,
So that I can evaluate CLAIRE-style approaches on CROSSFIRE corpora.

**Acceptance Criteria:**

**Given** a `ReasoningStrategy` implementation in `reasoning_strategy.py`
**When** I run it against a corpus
**Then** it extracts atomic claims from each document using LLM calls
**And** it cross-checks claims across documents for contradictions
**And** it produces `DetectedIncoherence` entries with evidence_references (source documents) and confidence scores
**And** running `HybridPipeline` with `NullGraphStrategy` + this reasoning strategy constitutes agentic mode (FR18)
**And** the strategy uses SeedManager for any random decisions
**And** LLM calls go through the thin wrapper with cost tracking

### Story 4.3: Graph Strategy (Graph-Native Mode)

As a researcher,
I want a graph-native auditing pipeline that builds a knowledge graph and detects structural anomalies,
So that I can evaluate KG-based approaches on CROSSFIRE corpora.

**Acceptance Criteria:**

**Given** a `GraphStrategy` implementation in `graph_strategy.py`
**When** I run it against a corpus
**Then** it constructs a knowledge graph from corpus documents using entity extraction and relationship identification
**And** it detects structural anomalies and contradictions in the graph (conflicting attribute values, contradictory relationships)
**And** it produces `DetectedIncoherence` entries with evidence_references and confidence scores
**And** it exposes its internal knowledge graph for Layer 1 evaluation (FR27)
**And** running `HybridPipeline` with this graph strategy + `NullReasoningStrategy` constitutes graph-native mode (FR19)
**And** this story is contingent on experimental feasibility — if graph-native proves unviable, this strategy is removed and the pipeline operates with agentic and hybrid modes only
**And** removal requires only deleting this file and `NullReasoningStrategy` — no changes to `HybridPipeline`

### Story 4.4: Baselines

As a researcher,
I want trivial and hypothesis-only baselines,
So that I can establish lower bounds and validate that the benchmark isn't solvable by shortcuts.

**Acceptance Criteria:**

**Given** the baselines module at `src/crossfire/pipeline/baselines/`
**When** I run `random_baseline.py` against a corpus
**Then** it produces a `PipelineReport` with randomly flagged document pairs as incoherences, using SeedManager for reproducibility (FR22)
**When** I run `bm25_baseline.py` against a corpus
**Then** it uses BM25 keyword matching to find contradictory passages and produces a `PipelineReport` (FR22)
**When** I run `hypothesis_only.py` against a corpus
**Then** it evaluates whether incoherences are detectable from surface features alone (document length, vocabulary, formatting) without reading content (FR21)
**And** it produces a `PipelineReport` — if scores are significantly above random, this indicates contamination in the generated corpus
**And** all baselines output reports in the same standardized format as the main pipeline (FR20)

---

## Epic 5: Evaluation & Diagnostics

Researcher can evaluate pipeline results with diagnostic granularity.

### Story 5.1: Binary & Partial Credit Scorers

As a researcher,
I want to score pipeline results using both exact match and localization proximity,
So that I get both strict and lenient measures of detection accuracy.

**Acceptance Criteria:**

**Given** a `PipelineReport` and gold incoherence labels
**When** I run the binary scorer
**Then** it computes exact match precision, recall, and F1 — a detected incoherence counts only if it matches a gold label on the same document pair and fact (FR23)
**When** I run the partial credit scorer
**Then** it computes localization proximity scores — partial credit for detections that identify the right documents but wrong fact, or right fact area but imprecise localization (FR24)
**And** both scorers return `EvaluationResult` Pydantic models
**And** both scorers are fully deterministic — same inputs always produce identical scores (NFR2)
**And** both scorers correctly handle edge cases: empty pipeline report (all zeros), empty gold labels (perfect precision, zero recall), no overlap (all zeros)
**And** pytest tests verify scoring against hand-crafted examples with known expected results

### Story 5.2: Per-Scope Breakdown

As a researcher,
I want evaluation results broken down by incoherence scope,
So that I can see where my system succeeds or fails across document boundaries.

**Acceptance Criteria:**

**Given** a `PipelineReport` and gold incoherence labels with scope metadata
**When** I run scope breakdown evaluation
**Then** it computes separate scores for intra-document, intra-subcorpus, and inter-subcorpus incoherences independently (FR25)
**And** each scope produces its own precision, recall, F1 (binary) and proximity score (partial credit)
**And** results are returned as `ScopeResult` models nested within `EvaluationResult`
**And** a detection is assigned to the scope of its matching gold label — not the scope the pipeline claims
**And** scope breakdown is independent — poor performance in one scope does not affect scores in another

### Story 5.3: Per-Stage Breakdown

As a researcher,
I want evaluation results broken down by pipeline stage,
So that I can pinpoint whether failures occur in entity resolution, graph construction, or scanning.

**Acceptance Criteria:**

**Given** a `PipelineReport` with stage-level metadata and gold labels
**When** I run stage breakdown evaluation
**Then** it computes separate scores for entity resolution, graph construction, and scanning stages independently (FR26)
**And** stage scores do NOT cascade — a failure in entity resolution does not automatically penalize graph construction or scanning scores
**And** each stage is evaluated against its own relevant subset of gold labels
**And** results are returned as `StageResult` models nested within `EvaluationResult`
**And** if graph-native mode is dropped (FR19 contingency), graph construction stage evaluation gracefully returns N/A rather than failing

### Story 5.4: Representation Quality Evaluation

As a researcher,
I want to evaluate a pipeline's internal knowledge graph against the gold entity graph,
So that I can measure representation quality independently from auditing accuracy.

**Acceptance Criteria:**

**Given** a pipeline's internal knowledge graph (exposed by GraphStrategy in Story 4.3) and the gold entity graph
**When** I run representation quality evaluation
**Then** it computes entity coverage: what fraction of gold entities appear in the system graph (FR27)
**And** it computes relationship accuracy: what fraction of system relationships match gold relationships
**And** it computes entity resolution quality: how well the system merges entities with paraphrased/abbreviated naming
**And** results are returned as a dedicated section within `EvaluationResult` (Layer 1: representation quality)
**And** this evaluation is independent from Layer 2 (auditing strategy) — both can run separately
**And** if graph-native mode is dropped, this evaluation still works for hybrid mode's graph component

### Story 5.5: Distractor Evaluation & Multi-Seed Aggregation

As a researcher,
I want to measure false positive rates on distractors and aggregate results across seeds,
So that I know whether my system flags legitimate divergences and my results are statistically significant.

**Acceptance Criteria:**

**Given** a `PipelineReport` and gold distractor labels
**When** I run distractor evaluation
**Then** it computes false positive rate: what fraction of distractors the pipeline incorrectly flags as incoherences (FR28)
**And** distractor false positive rate is reported separately from incoherence detection accuracy
**Given** evaluation results from multiple runs with different seeds
**When** I run multi-seed aggregation
**Then** it computes mean, standard deviation, and confidence intervals across seeds for all metrics (FR29)
**And** it computes statistical significance (p-values) for performance differences between pipeline modes
**And** aggregated results include per-scope and per-stage breakdowns with significance measures
**And** all aggregation uses scipy for statistical tests

---

## Epic 6: Benchmark Release

Ship pre-generated gold datasets, complete README, and verify end-to-end reproducibility.

### Story 6.1: Pre-Generated Gold Datasets

As a researcher,
I want pre-generated gold datasets included in the repository,
So that I can evaluate my system immediately without running the generator or spending on LLM API calls.

**Acceptance Criteria:**

**Given** the 4 preset configurations (default, low_connectivity, high_connectivity, stress_test)
**When** I run the generator with each preset
**Then** each produces a complete dataset in `data/datasets/{preset_name}/` containing corpus JSONL files, gold entity graph JSON, gold incoherence labels JSON, gold distractor labels JSON, and metadata.json with seed, parameters, and version
**And** all 4 datasets are committed to the repository (FR30)
**And** each dataset's metadata.json records the exact seed and parameters used, enabling regeneration verification
**And** running the generator with the same preset and seed produces bit-identical output to the committed dataset (NFR1)
**And** all datasets pass Pydantic schema validation

### Story 6.2: README & Reproduction Verification

As a researcher,
I want a README that lets me reproduce all published results from clone to final evaluation,
So that I can verify the benchmark's claims and build on its results with confidence.

**Acceptance Criteria:**

**Given** a fresh clone of the repository
**When** I follow the README instructions
**Then** it covers: prerequisites (Python 3.10+, API key setup), installation (`pip install -r requirements.txt`, `.env` configuration), running evaluation on pre-generated datasets (without generation), running the generator with preset configs, running all pipeline modes against a corpus, running evaluation and reading diagnostic results, and reproducing published baselines end-to-end (FR33)
**And** following the reproduction steps produces evaluation results matching published numbers exactly (NFR3)
**And** the README documents the standardized incoherence report format for researchers adapting their own systems
**And** the README includes a quick-start section (evaluate pre-generated datasets in <5 commands) and a full walkthrough section
**And** a dry-run verification is performed: a fresh environment clone → install → evaluate pre-generated dataset → compare against committed baseline results → all match
