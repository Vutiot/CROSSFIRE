---
stepsCompleted:
  - "step-01-validate-prerequisites"
  - "step-02-design-epics"
  - "step-03-create-stories"
  - "step-04-final-validation"
status: 'complete'
completedAt: '2026-04-10'
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/architecture.md"
---

# CROSSFIRE - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for CROSSFIRE, decomposing the requirements from the PRD and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

- FR1: Researcher can process real investigation source documents (from multiple sources: Grenfell Tower Inquiry, Chicago COPA, NTSB aviation dockets) through an agentic pipeline that anonymizes, reformats, extracts claims, and injects contradictions
- FR3: Researcher can reproduce evaluation results deterministically against shipped dataset versions
- FR4: Researcher can select from versioned datasets with different injection parameters (contradiction rates, distractor ratios, mechanism distributions)
- FR5: Corpus contains heterogeneous document types as present in each source (e.g., hearing transcripts, witness statements, and final report for Grenfell; FSR, TRRs, OCIR, BWC descriptions for COPA; investigation reports, witness testimonies, meteorology reports, ATC transcripts for NTSB). Document types are source-specific strings, not a fixed enum.
- FR6: Researcher can configure incoherence scope distribution (intra-document, inter-document)
- FR7: Researcher can configure incoherence mechanism (numeric drift, entity swap, causal inversion, temporal contradiction, omission-based implicit, temporal revision conflict)
- FR8: Researcher can configure incoherence detectability distribution (single-hop, multi-hop, entity-resolution-dependent)
- FR9: Researcher can configure system affinity (balanced, graph-favoring, agentic-favoring)
- FR10: Generator produces incoherences using minimal-pair modification, verified by mechanical diff between original and modified documents to confirm only the target fact changed
- FR11: Generator produces distractor labels (legitimate perspective divergences that should NOT be flagged as incoherences) at a configurable ratio
- FR12: Diff-based validation confirms no stylistic contamination — surrounding context (±200 chars) must be identical between original and modified documents
- FR13: Generator produces a knowledge graph of factual claim triples with cross-references as an intermediate artifact. Ships for transparency and reproducibility but is NOT used as gold evaluation reference. Gold references are injection-derived only.
- FR14: Generator produces gold contradiction labels verified by mechanical diff, including: scope, mechanism, detectability, system affinity, difficulty, char_start/char_end offsets, original and contradicted text, rationale, and ground_truth indicator
- FR15: Generator produces gold distractor labels identifying every legitimate divergence
- FR16: Dataset versions track both label corrections and injection parameter changes (contradiction rates, distractor ratios, mechanism/difficulty distributions). Each version ships with generation_params.json documenting all parameters.
- FR17: Researcher can run a hybrid auditing pipeline (graph representation + LLM-driven reasoning) against a dataset case directory containing anonymized document files and metadata
- FR18: Researcher can run an agentic auditing pipeline (claim extraction + cross-checking, graph layer disabled) against a dataset case directory
- FR19: Researcher can run a graph-native auditing pipeline (KG construction + structural anomaly detection, LLM reasoning disabled) against a dataset case directory — contingent on experimental feasibility. Pipeline's internal KG is evaluated against injection-derived gold claims, not full knowledge graph.
- FR20: All pipeline modes produce contradiction reports in a standardized format with 2-scope taxonomy (intra_doc, inter_doc), document references, text spans, and confidence
- FR21: Researcher can run a hypothesis-only baseline that evaluates whether incoherences are detectable from surface features alone (contamination validation)
- FR22: Researcher can run trivial baselines (random, BM25 keyword contradiction) for lower-bound comparison
- FR23: Researcher can evaluate a pipeline's contradiction report against gold labels using binary scoring with character-span IoU matching (threshold-configurable)
- FR24: Researcher can evaluate using tiered partial credit: precise span match (1.0), approximate span (0.7), correct section (0.4), correct documents only (0.2)
- FR25: Researcher can view evaluation results broken down per-scope (intra-document, inter-document) independently
- FR26: Researcher can view evaluation results broken down per-stage (claim extraction, cross-reference identification, contradiction detection) independently, evaluated against injection-derived gold references only. Stages do not cascade.
- FR27: Researcher can evaluate a pipeline's internal representation against injection-targeted gold claims and cross-references — not against the full generation-time knowledge graph
- FR28: Researcher can measure false positive rate on distractor labels, with per-divergence-type breakdown
- FR29: Researcher can aggregate evaluation results across dataset versions and cases, with significance measures for cross-pipeline comparison
- FR30: Versioned gold datasets ship with the repository. Each version contains processed cases with anonymized documents, diff-verified contradiction labels, distractor labels, and generation_params.json.
- FR31: Each document includes metadata: source ID (e.g., "grenfell", "copa", "ntsb"), source-specific document type, source case ID, and document classification per scope_map
- FR32: All outputs (corpora, annotations, evaluation results) are stored in documented, machine-readable formats
- FR33: README provides instructions to: install dependencies, evaluate shipped datasets with auditing pipelines, reproduce published baseline results, and (optionally) run the agentic generation pipeline on new source documents (Grenfell, COPA, or NTSB)

### NonFunctional Requirements

- NFR1: Shipped datasets are frozen, versioned artifacts. Evaluation against shipped datasets produces identical results across runs and machines. Generation is non-deterministic (agentic execution).
- NFR2: Evaluation scripts are fully deterministic — identical inputs produce identical scores with no variance
- NFR3: Pre-generated datasets run through shipped pipelines reproduce published baseline numbers exactly
- NFR4: All sources of randomness in evaluation and auditing pipelines are seeded and documented. Generation randomness is inherent to agentic execution.
- NFR5: Gold contradiction labels are mechanically verified via diff between original and modified documents. No self-reported labels without diff confirmation.
- NFR6: Evaluation scoring is mathematically correct against gold labels — no off-by-one errors, no input/label misalignment
- NFR7: Diff-based validation confirms each modification touches only the target fact. Unintended secondary changes are flagged and rejected.
- NFR8: Gold evaluation references are injection-derived (targeted claims, used cross-references, contradiction labels). Full knowledge graph ships for transparency but is not a gold evaluation reference.
- NFR9: Runs on Linux and macOS without platform-specific dependencies
- NFR10: No GPU requirement for corpus generation or evaluation (LLM calls are API-based)
- NFR11: Reference pipelines executable on academic-grade hardware (consumer GPU or CPU-only with API calls)
- NFR12: Python 3.10+ with standard scientific Python ecosystem (no exotic or platform-locked dependencies)
- NFR13: Generation cost per case is estimable before execution. Fan-out architecture with cost-efficient model for per-chunk extraction and reasoning-capable model for cross-document analysis. Cost breakdown logged per phase.
- NFR14: Generation fails gracefully on API errors with clear reporting — no silent retries that accumulate charges
- NFR15: Dry-run or cost estimation mode available before committing to full generation

### Additional Requirements

- Architecture specifies `src/` layout with `generation/` at project root — hard boundary between evaluable Python package and CLI-driven agentic generation toolchain
- Pydantic models required for all data contracts before writing producer/consumer code (`src/crossfire/shared/schemas/`)
- SeedManager (centralized) for pipeline and evaluation randomness only — generation is non-deterministic
- Thin LLM wrapper function for auditing pipelines only — generation uses Claude Code CLI directly
- loguru for all Python logging — no print() statements, no stdlib logging
- Strategy pattern with constructor injection for pipeline mode switching (HybridPipeline with GraphStrategy/ReasoningStrategy interfaces)
- Diff-based verification gate between generation output and shipped datasets (`verify_dataset.py`)
- Dataset versioning with `generation_params.json` per version — re-injection on same anonymized base produces new versions
- Case directory layout at `corpus/{source_id}/{case_id}/` with source-agnostic subdirectories (anonymized_docs/, contradictions/, distractors/, metadata/, original_claims/, validation/)
- Three architectural boundaries: generation→dataset (verification gate), dataset→pipeline (pipeline never reads gold labels), pipeline+gold→evaluator (evaluator never references full KG for scoring)
- Return-value error handling first, exceptions only for unrecoverable failures
- snake_case enforced across Python code, JSON output fields, and config files
- `requirements.txt` for dependency management (academic standard)
- `pytest` for testing framework
- No linting/type checking enforcement for MVP (speed priority)
- `run.py` as CLI entry point for pipeline execution and evaluation

### UX Design Requirements

N/A — CROSSFIRE has no user interface component. All interaction is via CLI scripts and file I/O.

### FR Coverage Map

| FR | Epic | Description |
|---|---|---|
| FR1 | Epic 2 | Agentic pipeline processing of multi-source investigation documents |
| FR3 | Epic 6 | Deterministic reproduction against shipped datasets |
| FR4 | Epic 6 | Versioned datasets with different injection parameters |
| FR5 | Epic 2 | Heterogeneous source-specific document types preserved |
| FR6 | Epic 3 | Configurable scope distribution (intra/inter-doc) |
| FR7 | Epic 3 | Configurable mechanism (6 types) |
| FR8 | Epic 3 | Configurable detectability distribution |
| FR9 | Epic 3 | Configurable system affinity |
| FR10 | Epic 3 | Minimal-pair modification with diff verification |
| FR11 | Epic 3 | Distractor labels at configurable ratio |
| FR12 | Epic 3 | ±200 char diff-based contamination validation |
| FR13 | Epic 3 | Intermediate knowledge graph (not gold eval ref) |
| FR14 | Epic 3 | Gold contradiction labels with full metadata |
| FR15 | Epic 3 | Gold distractor labels |
| FR16 | Epic 3 | Dataset versioning with generation_params.json |
| FR17 | Epic 4 | Hybrid auditing pipeline |
| FR18 | Epic 4 | Agentic auditing pipeline |
| FR19 | Epic 4 | Graph-native pipeline (contingent) |
| FR20 | Epic 4 | Standardized report format, 2-scope taxonomy |
| FR21 | Epic 4 | Hypothesis-only baseline |
| FR22 | Epic 4 | Trivial baselines (random, BM25) |
| FR23 | Epic 5 | Binary scoring with char-span IoU |
| FR24 | Epic 5 | Tiered partial credit scoring |
| FR25 | Epic 5 | Per-scope breakdown |
| FR26 | Epic 5 | Per-stage breakdown |
| FR27 | Epic 5 | Representation quality evaluation |
| FR28 | Epic 5 | Distractor FP rate per-divergence-type |
| FR29 | Epic 5 | Multi-version/case aggregation |
| FR30 | Epic 6 | Versioned gold datasets ship with repo |
| FR31 | Epic 6 | Document metadata (source ID, source-specific type, case ID, scope_map) |
| FR32 | Epic 1 | Documented, machine-readable output formats |
| FR33 | Epic 6 | README with full multi-source instructions |

## Epic List

### Epic 1: Project Foundation & Data Contracts
Researcher has a working project skeleton with validated Pydantic schemas for every data format in the system, including multi-source support (Document.source field, source-agnostic document_type as string), enabling development of all subsequent components.
**FRs covered:** FR32; supports all FRs (cross-cutting schemas, seeding, logging)

### Epic 2: Corpus Processing & Anonymization
Researcher can process real investigation source documents (Grenfell Tower Inquiry, Chicago COPA, NTSB aviation dockets) through source-specific agentic pipelines to produce anonymized, chunked documents organized by source and case with heterogeneous document types preserved. Uses `corpus/{source_id}/{case_id}/` directory layout with pluggable source adapters.
**FRs covered:** FR1, FR5

### Epic 3: Contradiction Injection & Gold Annotation
Researcher can inject controlled contradictions with configurable scope, mechanism, detectability, and system affinity parameters, producing diff-verified gold labels and distractor labels with full metadata.
**FRs covered:** FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR14, FR15, FR16

### Epic 4: Auditing Pipelines
Researcher can run hybrid, agentic, and graph-native pipeline modes plus baselines (hypothesis-only, random, BM25) against a dataset case directory, producing standardized contradiction reports with 2-scope taxonomy.
**FRs covered:** FR17, FR18, FR19, FR20, FR21, FR22

### Epic 5: Evaluation & Diagnostics
Researcher can score pipeline output with binary and partial-credit metrics, view per-scope and per-stage diagnostic breakdowns, evaluate representation quality against injection-derived gold, measure distractor FP rates, and aggregate across dataset versions with significance measures.
**FRs covered:** FR23, FR24, FR25, FR26, FR27, FR28, FR29

### Epic 6: Benchmark Release & Reproducibility
Other researchers can clone the repo, evaluate versioned gold datasets with auditing pipelines, and reproduce published baseline results deterministically — without running the generation pipeline.
**FRs covered:** FR3, FR4, FR30, FR31, FR33

## Epic 1: Project Foundation & Data Contracts

Researcher has a working project skeleton with validated Pydantic schemas for every data format in the system, enabling development of all subsequent components.

### Story 1.1: Project Scaffolding & Directory Structure

As a researcher,
I want a well-organized project structure with all directories, dependencies, and entry points in place,
So that I can begin developing and running CROSSFIRE components immediately after cloning.

**Acceptance Criteria:**

**Given** a fresh clone of the repository
**When** I inspect the project structure
**Then** the `src/crossfire/` package exists with `__init__.py` and subpackages: `shared/`, `shared/schemas/`, `generator/`, `generator/validation/`, `pipeline/`, `pipeline/strategies/`, `pipeline/baselines/`, `evaluation/`
**And** the `generation/` directory exists at project root (outside `src/crossfire/`)
**And** `data/datasets/` directory exists for versioned gold datasets
**And** `tests/` directory exists mirroring `src/crossfire/` structure
**And** `corpus/` directory is listed in `.gitignore` (source investigation documents not shipped)
**And** `output/` directory is listed in `.gitignore` (runtime output)
**And** `.env` is listed in `.gitignore`
**And** `.env.example` exists with placeholder API key entries

**Given** the project is cloned
**When** I run `pip install -r requirements.txt`
**Then** all core dependencies install successfully (networkx, numpy, scipy, scikit-learn, pydantic, loguru, python-dotenv, pyyaml, pytest)

**Given** the project is set up
**When** I run `python run.py --help`
**Then** a help message displays showing available entry points for pipeline execution and evaluation

### Story 1.2: Pydantic Schemas for All Data Contracts

As a researcher,
I want validated data models for every structured format in the system,
So that generation output, pipeline reports, and evaluation results have enforced contracts preventing malformed data from crossing component boundaries.

**Acceptance Criteria:**

**Given** the schemas package at `src/crossfire/shared/schemas/`
**When** I import corpus models
**Then** `Document` model exists with fields: `document_id`, `source` (e.g., "grenfell", "copa", "ntsb"), `document_type` (str, source-specific — not a fixed enum), `source_case_id`, `scope_classification`, `content` (text), and metadata fields — no `subcorpus_id`

**Given** the schemas package
**When** I import contradiction models
**Then** `ContradictionLabel` model exists with fields: `scope` (Literal["intra_doc", "inter_doc"]), `mechanism`, `detectability`, `system_affinity`, `difficulty`, `char_start`, `char_end`, `original_text`, `modified_text`, `rationale`, `ground_truth`, and document references
**And** `DistractorLabel` model exists with divergence type field (Literal["expert_opinion", "preliminary_vs_final", "measurement_methodology", "uncertainty_expression"])

**Given** the schemas package
**When** I import knowledge graph models
**Then** `KnowledgeGraphClaim` and `CrossReference` models exist — marked as intermediate artifacts, not gold evaluation references

**Given** the schemas package
**When** I import pipeline report models
**Then** `DetectedContradiction` model exists with 2-scope taxonomy (intra_doc, inter_doc), document references, text spans, and confidence
**And** `PipelineReport` model exists containing a list of `DetectedContradiction` entries plus run metadata

**Given** the schemas package
**When** I import evaluation models
**Then** `ScopeResult`, `StageResult`, and `EvaluationResult` models exist with per-scope (2-level) and per-stage (3-stage: claim_extraction, cross_reference_identification, contradiction_detection) breakdowns

**Given** the schemas package
**When** I import config models
**Then** `PipelineConfig` model exists with `case_dir` path and strategy configuration
**And** `DatasetVersion` model exists tracking version ID, base version, and label correction history
**And** `GenerationParams` model exists with contradiction rates per scope, distractor ratio, and mechanism/difficulty distributions

**Given** any Pydantic model
**When** I serialize it to JSON
**Then** all field names are `snake_case`

**Given** a malformed data dict (e.g., missing required field, wrong type, invalid scope literal)
**When** I attempt to construct a Pydantic model from it
**Then** a `ValidationError` is raised with a clear message identifying the invalid field

### Story 1.3: Centralized Seed Manager

As a researcher,
I want deterministic, reproducible randomness across pipeline and evaluation runs,
So that the same dataset + same seed produces identical evaluation results on any machine.

**Acceptance Criteria:**

**Given** a `SeedManager` initialized with `master_seed=42`
**When** I call `get_seed("binary_scorer", index=0)` twice
**Then** both calls return the same integer value

**Given** two `SeedManager` instances with the same `master_seed`
**When** I call `get_seed` with the same component and index on both
**Then** they produce identical seeds

**Given** a `SeedManager` with `master_seed=42`
**When** I call `get_seed("binary_scorer")` and `get_seed("partial_scorer")`
**Then** the returned seeds are different (no collisions across components)

**Given** a `SeedManager`
**When** it is instantiated
**Then** the master seed is logged at `INFO` level via loguru for reproducibility verification

### Story 1.4: Thin LLM Wrapper

As a researcher,
I want a single LLM call function for auditing pipelines with cost tracking and failure handling,
So that all pipeline LLM usage is centralized, costs are visible, and failures are explicit.

**Acceptance Criteria:**

**Given** a configured LLM wrapper
**When** I call `llm_call(prompt, model="default", temperature=0)`
**Then** it returns a `(response, error)` tuple — response on success, error string on failure

**Given** a pipeline run making multiple LLM calls
**When** the run completes
**Then** total token usage (input + output) is accumulated and logged at `INFO` level

**Given** `dry_run=True` passed to `llm_call`
**When** the function executes
**Then** it returns an estimated cost based on prompt token count without making an API call

**Given** an API rate limit error (transient)
**When** `llm_call` encounters it
**Then** it retries with exponential backoff up to a configurable max retries

**Given** an authentication or quota error (non-transient)
**When** `llm_call` encounters it
**Then** it fails immediately and returns an error string — no silent retries

**Given** any LLM call
**When** it executes
**Then** the call is logged at `DEBUG` level with token counts via loguru

## Epic 2: Corpus Processing & Anonymization

Researcher can process real investigation source documents (Grenfell Tower Inquiry, Chicago COPA, NTSB aviation dockets) through source-specific agentic pipelines to produce anonymized, chunked documents organized by source and case with heterogeneous document types preserved. Uses `corpus/{source_id}/{case_id}/` directory layout with pluggable source adapters.

### Story 2.1: Source Corpus Acquisition & Inventory

As a researcher,
I want a structured inventory of raw investigation source documents organized by source and case,
So that the agentic pipeline knows which sources, cases, and document types are available for processing.

**Acceptance Criteria:**

**Given** raw source documents placed in `corpus/`
**When** I organize them by source and case
**Then** each case has its own directory (`corpus/{source_id}/{case_id}/`) containing the source document files (e.g., `corpus/grenfell/hearing_day_1/`, `corpus/copa/case_12345/`, `corpus/ntsb/DCA19FA089/`)

**Given** a populated `corpus/` directory
**When** I inspect the inventory
**Then** a manifest file documents each source's cases and their available document types (source-specific: hearing transcripts and witness statements for Grenfell; FSR, TRRs, OCIR for COPA; operations group reports, meteorology reports, ATC transcripts for NTSB)

**Given** the `corpus/` directory
**When** I check `.gitignore`
**Then** `corpus/` is excluded from version control (source investigation documents are not shipped)

**Given** a case directory
**When** I review its contents
**Then** heterogeneous document types from the source are preserved as-is — no filtering or homogenization of document types (FR5)
**And** each source has its own acquisition process (PDF parsing for Grenfell and COPA; text extraction for NTSB)

### Story 2.2: Document Chunking & Manifest

As a researcher,
I want raw source documents deterministically chunked into processable segments,
So that the agentic pipeline can process each chunk independently via fan-out architecture with per-chunk cost efficiency.

**Acceptance Criteria:**

**Given** a case directory with source documents (text or PDF)
**When** I run `python generation/chunk_documents.py --case corpus/{source_id}/{case_id}/`
**Then** PDF files are first parsed to text (Grenfell and COPA sources are PDF), then all text files are split into chunks sized for efficient LLM processing (Sonnet per-chunk extraction)
**And** a chunk manifest JSON is produced mapping each chunk back to its source document and character offsets

**Given** the same input files
**When** I run the chunking utility twice
**Then** identical chunks and manifest are produced (deterministic)

**Given** a document that fits within a single chunk
**When** it is processed
**Then** it remains as a single chunk without unnecessary splitting

**Given** a chunking run
**When** it completes
**Then** progress and chunk count are logged via loguru at `INFO` level
**And** chunking is source-agnostic — works on any text files in any case directory regardless of source

### Story 2.3: Agentic Plan Document

As a researcher,
I want source-specific plan documents that drive Claude Code CLI sessions through anonymization, reformatting, and claim extraction for each data source,
So that the agentic pipeline produces consistently structured output from heterogeneous source documents across all sources.

**Acceptance Criteria:**

**Given** source-specific plan documents at `generation/sources/{source_id}/agent_plan.md` (e.g., `generation/sources/grenfell/agent_plan.md`, `generation/sources/copa/agent_plan.md`, `generation/sources/ntsb/agent_plan.md`)
**When** a Claude Code CLI session loads the appropriate plan as system prompt
**Then** the plan instructs the agent to: (1) anonymize identifying information per source-specific rules, (2) reformat documents preserving source-specific structure, (3) extract factual claim triples with cross-references, and (4) output results in the case directory layout

**Given** a source-specific plan document
**When** it specifies output format
**Then** anonymized documents are written as `.txt` files in `anonymized_docs/` per the architecture spec
**And** extracted claims are written as per-document JSON files in `original_claims/`
**And** a knowledge graph JSON is assembled in `metadata/knowledge_graph.json`
**And** domain registry and scope map are written to `metadata/`

**Given** a source-specific plan document
**When** it specifies the processing approach
**Then** it uses fan-out architecture: Sonnet for per-chunk claim extraction, Opus for cross-document reasoning (FR1, NFR13)

**Given** a source-specific plan document
**When** it specifies source-specific handling
**Then** it defines source-specific anonymization rules, entity handling, and document type mapping (e.g., Grenfell plan specifies party anonymization for 8 cladding inquiry parties; COPA plan specifies officer/witness anonymization; NTSB plan preserves natural cross-document entity variation)

### Story 2.4: Generation Bash Wrapper Scripts

As a researcher,
I want bash scripts that orchestrate Claude Code CLI sessions for corpus processing across any source type,
So that I can generate one case or all cases for any source with a single command.

**Acceptance Criteria:**

**Given** `generation/generate_case.sh` exists
**When** I run `./generation/generate_case.sh --source grenfell corpus/grenfell/hearing_day_1/`
**Then** it loads the source-specific plan document from `generation/sources/grenfell/agent_plan.md` and invokes a Claude Code CLI session against the chunked source files for that case
**And** output is written to a staging directory following the case directory layout

**Given** `generation/generate_all.sh` exists
**When** I run `./generation/generate_all.sh --source ntsb`
**Then** it iterates over all case directories in `corpus/ntsb/` and runs `generate_case.sh` for each
**And** running without `--source` iterates over all sources and all cases

**Given** a generation run
**When** a Claude Code CLI session fails for a case
**Then** the error is logged and the outer loop continues to the next case — no silent failures, no accumulated charges from retries

**Given** a completed generation run
**When** I inspect the output
**Then** each processed case directory contains `anonymized_docs/`, `original_claims/`, and `metadata/` subdirectories matching the architecture spec

**Given** a generation run
**When** it completes
**Then** a summary is printed showing: cases processed, cases failed, and approximate cost per case

## Epic 3: Contradiction Injection & Gold Annotation

Researcher can inject controlled contradictions with configurable scope, mechanism, detectability, and system affinity parameters, producing diff-verified gold labels and distractor labels with full metadata.

### Story 3.1: Intra-Document Contradiction Injection

As a researcher,
I want to inject controlled contradictions within individual documents using minimal-pair modification,
So that I can benchmark systems on detecting intra-document factual incoherences with known ground truth.

**Acceptance Criteria:**

**Given** an anonymized document from a processed case
**When** the agentic injection pipeline runs with scope set to `intra_doc`
**Then** contradictions are injected by modifying only the target fact, not surrounding prose (minimal-pair construction, FR10)

**Given** injection parameters specifying mechanism distribution
**When** contradictions are injected
**Then** each uses one of the 6 supported mechanisms: numeric drift, entity swap, causal inversion, temporal contradiction, omission-based implicit, or temporal revision conflict (FR7)

**Given** injection parameters specifying detectability distribution
**When** contradictions are injected
**Then** each is tagged with detectability level: single-hop, multi-hop, or entity-resolution-dependent (FR8)

**Given** injection parameters specifying system affinity
**When** contradictions are injected
**Then** each is tagged with system affinity: balanced, graph-favoring, or agentic-favoring (FR9)

**Given** a completed intra-doc injection
**When** I inspect the output
**Then** each injected contradiction has a self-reported label including: scope, mechanism, detectability, system_affinity, difficulty, char_start, char_end, original_text, modified_text, and rationale

**Given** the injection scope is `intra_doc`
**When** contradictions are injected
**Then** both the original claim and the contradicting modification exist within the same document (FR6)

### Story 3.2: Inter-Document Contradiction Injection

As a researcher,
I want to inject controlled contradictions across documents within a case,
So that I can benchmark systems on detecting cross-document factual incoherences requiring entity resolution and multi-document reasoning.

**Acceptance Criteria:**

**Given** anonymized documents from a processed case with cross-document shared entities
**When** the agentic injection pipeline runs with scope set to `inter_doc`
**Then** contradictions are injected where the original claim is in one document and the contradicting modification is in a different document (FR6)

**Given** inter-document injection
**When** contradictions target shared entities across document types
**Then** the injection leverages natural cross-document entity references (e.g., a fact in the operations report contradicted in the meteorology report)

**Given** injection parameters for mechanism, detectability, and system affinity
**When** inter-doc contradictions are injected
**Then** the same 6 mechanisms, 3 detectability levels, and 3 system affinity options are available as for intra-doc (FR7, FR8, FR9)

**Given** an inter-doc injection
**When** a modification is made
**Then** only the target fact is changed in the target document — minimal-pair construction applies across documents (FR10)

**Given** a completed inter-doc injection
**When** I inspect the output
**Then** each contradiction label includes document references for both the original claim location and the modified location

### Story 3.3: Distractor Generation

As a researcher,
I want legitimate perspective divergences injected alongside real contradictions,
So that I can measure false positive rates and ensure systems distinguish genuine incoherences from natural disagreement.

**Acceptance Criteria:**

**Given** injection parameters specifying a distractor ratio
**When** the agentic pipeline generates distractors
**Then** distractors are produced at the configured ratio relative to real contradictions (FR11)

**Given** a generated distractor
**When** I inspect its label
**Then** it is tagged with a divergence type: `expert_opinion`, `preliminary_vs_final`, `measurement_methodology`, or `uncertainty_expression`

**Given** a distractor
**When** I review the content
**Then** it represents a legitimate perspective divergence that should NOT be flagged as an incoherence — genuine domain disagreement, not a factual error

**Given** distractors for a case
**When** they are written to disk
**Then** they are stored in `distractors/distractor_labels.jsonl` in the case directory
**And** each line validates against the `DistractorLabel` Pydantic schema

### Story 3.4: Diff-Based Gold Label Verification

As a researcher,
I want mechanical verification that each injected contradiction changed only the target fact,
So that gold labels are provably correct and contamination-free — not dependent on agent self-reporting.

**Acceptance Criteria:**

**Given** an original document and its modified version after injection
**When** `verify_dataset.py` runs diff verification
**Then** character offsets (char_start, char_end) are derived from the mechanical diff, not from the agent's self-reported offsets (FR14)

**Given** a diff between original and modified documents
**When** the surrounding context is checked
**Then** the ±200 characters around each modification must be identical between original and modified — any deviation flags a contamination failure (FR12)

**Given** an injection where the agent introduced unintended secondary changes
**When** diff verification detects them
**Then** the contradiction is flagged and written to `validation/unintended_modifications.json`
**And** it is rejected from the gold label set (FR10)

**Given** discrepancies between agent self-reported labels and diff-derived labels
**When** verification detects them
**Then** discrepancies are logged to `validation/agent_label_discrepancies.json`
**And** diff-derived values take precedence for gold truth

**Given** contradictions that fail verification
**When** they are rejected
**Then** they are written to `validation/rejected_contradictions.jsonl` with rejection reason
**And** `validation/diff_verification_log.json` records the full verification results for the case

**Given** all contradictions for a case pass verification
**When** gold labels are assembled
**Then** `contradictions/intra_doc_contradictions.jsonl`, `contradictions/inter_doc_contradictions.jsonl`, and `contradictions/all_contradictions.jsonl` are produced
**And** every line validates against the `ContradictionLabel` Pydantic schema (NFR5)

### Story 3.5: Dataset Versioning & Release Packaging

As a researcher,
I want versioned datasets with tracked injection parameters,
So that I can produce multiple dataset versions with different contradiction rates and distributions from the same anonymized base corpus.

**Acceptance Criteria:**

**Given** a completed and verified injection run
**When** the dataset is packaged
**Then** output is assembled into `data/datasets/{version}/` with the full case directory layout per architecture spec

**Given** a dataset version
**When** I inspect `generation_params.json`
**Then** it contains: version ID, base_version (if re-injection), contradiction rates per scope (intra_doc, inter_doc), distractor ratio, mechanism distribution, and difficulty distribution (FR16)

**Given** a previously anonymized and verified base corpus
**When** I run injection with different parameters
**Then** a new dataset version is produced without regenerating the base anonymized documents

**Given** a dataset version
**When** I inspect its `dataset_manifest.json`
**Then** it contains aggregate statistics across all cases: total contradictions per scope, total distractors, mechanism distribution, detectability distribution, and case count

**Given** a dataset version
**When** I inspect `metadata/knowledge_graph.json` in each case
**Then** the intermediate knowledge graph is present for transparency and reproducibility (FR13)
**And** it is clearly documented as NOT a gold evaluation reference

**Given** verified gold labels for a dataset version
**When** distractor labels are packaged
**Then** `distractors/distractor_labels.jsonl` is included in each case directory with all distractor labels (FR15)

## Epic 3.5: Knowledge Graph Visualization (Research Utility)

Lightweight interactive viewer for inspecting entity graphs, KG claims, contradictions, and distractors produced by E3. Supports both entity-graph (default dataset) and claims-based (v1-test) layouts. No new Python dependencies.

### Story 3.5-1: Interactive KG Viewer

**Status:** done (2026-04-12)

**Files:** `tools/kg_viewer/serve.py`, `tools/kg_viewer/index.html`, `tools/kg_viewer/README.md`

**Acceptance Criteria:**
- `python tools/kg_viewer/serve.py data/datasets/default` serves interactive graph at localhost:8080
- Nodes color-coded by entity type (person, organization, equipment, regulation, location)
- Contradiction overlay: orange borders on affected nodes, click for details (mechanism, scope, original vs modified text)
- Distractor overlay: purple dashed borders, click for divergence type and description
- Filter controls: toggle entity types, contradiction/distractor visibility, scope filter
- Supports both dataset layouts (entity_graph and claims-based)
- Standalone drag-and-drop mode (no server required)

---

## Epic 4: Auditing Pipelines

Researcher can run hybrid, agentic, and graph-native pipeline modes plus baselines (hypothesis-only, random, BM25) against a dataset case directory, producing standardized contradiction reports with 2-scope taxonomy.

### Story 4.1: Strategy Interfaces & Pipeline Skeleton

As a researcher,
I want a pipeline framework that loads case directories and produces standardized contradiction reports via pluggable strategies,
So that I can run different auditing approaches against the same dataset with comparable output.

**Acceptance Criteria:**

**Given** `HybridPipeline` initialized with a `GraphStrategy` and a `ReasoningStrategy`
**When** I call `run(case_dir)`
**Then** it loads anonymized `.txt` files from `case_dir/anonymized_docs/` and returns a `PipelineReport`

**Given** a `PipelineReport` produced by any pipeline mode
**When** I inspect its structure
**Then** every `DetectedContradiction` entry uses the 2-scope taxonomy (`intra_doc`, `inter_doc`) with document references, text spans, and confidence (FR20)

**Given** `HybridPipeline` with `NullGraphStrategy` and a real `ReasoningStrategy`
**When** I run the pipeline
**Then** it operates in agentic mode — graph layer produces empty results, no errors

**Given** `HybridPipeline` with a real `GraphStrategy` and `NullReasoningStrategy`
**When** I run the pipeline
**Then** it operates in graph-native mode — reasoning layer produces empty results, no errors

**Given** `HybridPipeline` with both real strategies
**When** I run the pipeline
**Then** it operates in hybrid mode — both strategies contribute to the contradiction report (FR17)

**Given** a `PipelineConfig` with `case_dir` path and strategy selection
**When** the pipeline initializes
**Then** the appropriate strategies are injected via constructor — no runtime branching or feature flags

**Given** a pipeline run
**When** it reads the case directory
**Then** it NEVER reads gold contradiction labels, distractor labels, or knowledge graph — hard architectural boundary

**Given** a pipeline run
**When** it completes
**Then** the `PipelineReport` is written to `output/reports/` as a JSON file
**And** the seed value and run metadata are logged at `INFO` level

### Story 4.2: Reasoning Strategy — Agentic Mode

As a researcher,
I want an LLM-driven auditing strategy that extracts claims and cross-checks them for contradictions,
So that I can evaluate agentic (CLAIRE-style) approaches to corpus-level coherence auditing.

**Acceptance Criteria:**

**Given** a `ReasoningStrategy` initialized with the LLM wrapper and a `SeedManager`
**When** it processes documents from a case directory
**Then** it extracts factual claims from each document via LLM calls and cross-checks claims across documents for contradictions (FR18)

**Given** the reasoning strategy detects a contradiction
**When** it produces a `DetectedContradiction`
**Then** the entry includes: scope (intra_doc or inter_doc), source and target document references, text spans identifying the contradicting passages, and a confidence score

**Given** `HybridPipeline` with `NullGraphStrategy` and this `ReasoningStrategy`
**When** the pipeline runs
**Then** the result is a pure agentic auditing pipeline — claim extraction + cross-checking with no graph layer (FR18)

**Given** the reasoning strategy
**When** LLM calls are made
**Then** all calls go through the thin LLM wrapper with cost tracking and `temperature=0`
**And** the `SeedManager` provides seeds for any randomized operations

**Given** a reasoning strategy run
**When** an LLM call fails
**Then** the error is returned as a value (not thrown), and the strategy continues processing remaining documents — partial results are included in the report

### Story 4.3: Graph Strategy — Graph-Native Mode

As a researcher,
I want a graph-based auditing strategy that constructs a knowledge graph and detects structural anomalies,
So that I can evaluate graph-native approaches to corpus auditing — contingent on experimental feasibility.

**Acceptance Criteria:**

**Given** a `GraphStrategy` initialized with a `SeedManager`
**When** it processes documents from a case directory
**Then** it constructs a knowledge graph using NetworkX from extracted entities and relationships (FR19)

**Given** a constructed knowledge graph
**When** the strategy runs anomaly detection
**Then** it identifies structural inconsistencies (contradictory edges, entity attribute conflicts) as candidate contradictions

**Given** the graph strategy detects a contradiction
**When** it produces a `DetectedContradiction`
**Then** the entry includes: scope, document references, text spans, and confidence — in the same standardized format as the reasoning strategy

**Given** `HybridPipeline` with this `GraphStrategy` and `NullReasoningStrategy`
**When** the pipeline runs
**Then** the result is a pure graph-native auditing pipeline — KG construction + structural anomaly detection with no LLM reasoning (FR19)

**Given** the graph strategy's internal KG
**When** it is evaluated
**Then** evaluation is against injection-derived gold claims only — NOT against the full generation-time knowledge graph

**Given** experimental results show graph-native can't adapt to unsupervised auditing
**When** this strategy is dropped
**Then** deleting `GraphStrategy` and `NullReasoningStrategy` implementations leaves no dead code — `HybridPipeline` continues to work with agentic mode only

### Story 4.4: Baselines

As a researcher,
I want hypothesis-only, random, and BM25 baselines that produce standardized pipeline reports,
So that I can validate contamination prevention and establish lower-bound comparison for real pipeline results.

**Acceptance Criteria:**

**Given** the hypothesis-only baseline
**When** it runs against a case directory
**Then** it evaluates whether incoherences are detectable from surface features alone (document length, vocabulary statistics, stylistic markers) — without reading document content for meaning (FR21)
**And** it produces a `PipelineReport` in the standardized format

**Given** the random baseline
**When** it runs against a case directory
**Then** it generates random contradiction predictions at a configurable rate using `SeedManager`
**And** it produces a `PipelineReport` in the standardized format (FR22)

**Given** the BM25 keyword contradiction baseline
**When** it runs against a case directory
**Then** it uses BM25 keyword matching to find passages with contradictory vocabulary (negation, antonyms) (FR22)
**And** it produces a `PipelineReport` in the standardized format

**Given** any baseline
**When** it produces a `PipelineReport`
**Then** the report uses the same 2-scope taxonomy and format as the full pipeline modes — enabling direct comparison via the evaluation suite

**Given** the hypothesis-only baseline results
**When** they show high performance
**Then** this indicates contamination — incoherences are detectable from surface features rather than content understanding, invalidating the benchmark

## Epic 5: Evaluation & Diagnostics

Researcher can score pipeline output with binary and partial-credit metrics, view per-scope and per-stage diagnostic breakdowns, evaluate representation quality against injection-derived gold, measure distractor FP rates, and aggregate across dataset versions with significance measures.

### Story 5.1: Binary & Partial Credit Scorers

As a researcher,
I want to score pipeline contradiction reports against gold labels using both exact-match and graded metrics,
So that I can measure detection accuracy at different levels of localization precision.

**Acceptance Criteria:**

**Given** a `PipelineReport` and gold `ContradictionLabel` entries for a case
**When** I run the binary scorer
**Then** each predicted contradiction is matched to gold labels using character-span IoU (intersection over union of char ranges)
**And** a match is counted when IoU exceeds a configurable threshold (FR23)

**Given** a configurable IoU threshold
**When** I adjust it (e.g., 0.5, 0.7, 0.9)
**Then** precision, recall, and F1 scores change accordingly — enabling sensitivity analysis on localization strictness

**Given** a `PipelineReport` and gold labels
**When** I run the partial credit scorer
**Then** each prediction receives tiered credit: 1.0 for precise span match, 0.7 for approximate span (overlapping but imprecise), 0.4 for correct section (same document region), 0.2 for correct documents only (right document pair, wrong location) (FR24)

**Given** either scorer
**When** it produces results
**Then** the output is an `EvaluationResult` Pydantic model with aggregate precision, recall, F1, and per-prediction match details

**Given** either scorer
**When** all computation is deterministic
**Then** the same inputs produce identical scores across runs and machines (NFR2)

### Story 5.2: Per-Scope Breakdown

As a researcher,
I want evaluation results broken down by contradiction scope,
So that I can independently assess pipeline performance on intra-document vs inter-document incoherences.

**Acceptance Criteria:**

**Given** evaluation results from any scorer
**When** I request per-scope breakdown
**Then** separate precision, recall, and F1 scores are produced for `intra_doc` and `inter_doc` scopes independently (FR25)

**Given** the per-scope breakdown
**When** I inspect results
**Then** each scope's metrics are computed only from predictions and gold labels matching that scope — no cross-scope contamination

**Given** a pipeline that performs well on `intra_doc` but poorly on `inter_doc`
**When** I view the breakdown
**Then** this performance gap is clearly visible — not hidden by aggregate scores

**Given** per-scope results
**When** they are produced
**Then** the output is a `ScopeResult` Pydantic model per scope, nested within the `EvaluationResult`

### Story 5.3: Per-Stage Breakdown

As a researcher,
I want evaluation results broken down by pipeline stage,
So that I can diagnose exactly where a pipeline fails — claim extraction, cross-reference identification, or contradiction detection.

**Acceptance Criteria:**

**Given** evaluation results
**When** I request per-stage breakdown
**Then** separate scores are produced for three stages: `claim_extraction`, `cross_reference_identification`, and `contradiction_detection` (FR26)

**Given** per-stage evaluation
**When** each stage is scored
**Then** it is evaluated against injection-derived gold references only — not the full generation-time knowledge graph (NFR8)

**Given** the per-stage breakdown
**When** stages are evaluated
**Then** stages do NOT cascade — a failure in claim extraction does not automatically count as failures in later stages (FR26)

**Given** per-stage results
**When** they are produced
**Then** the output is a `StageResult` Pydantic model per stage, nested within the `EvaluationResult`

### Story 5.4: Representation Quality Evaluation

As a researcher,
I want to evaluate how well a pipeline's internal knowledge graph captures injection-targeted claims,
So that I can isolate representation failures from reasoning failures (Layer 1 of two-layer evaluation).

**Acceptance Criteria:**

**Given** a pipeline's internal knowledge graph and injection-derived gold claims and cross-references
**When** I run representation quality evaluation
**Then** it measures how many injection-targeted claims and cross-references are present in the pipeline's representation (FR27)

**Given** the representation evaluation
**When** it computes metrics
**Then** it evaluates ONLY against injection-targeted gold claims — NOT against the full generation-time knowledge graph (FR27, NFR8)

**Given** a pipeline with good representation but poor contradiction detection
**When** I view Layer 1 (representation) vs Layer 2 (auditing strategy) results
**Then** the diagnostic clearly shows the system captures the relevant facts but fails at reasoning over them

**Given** representation evaluation results
**When** they are produced
**Then** the output includes precision and recall for captured claims and cross-references relative to injection-derived gold

### Story 5.5: Distractor Evaluation & Multi-Version Aggregation

As a researcher,
I want to measure false positive rates on distractors and aggregate results across dataset versions,
So that I can assess system robustness to legitimate divergences and report statistically meaningful cross-pipeline comparisons.

**Acceptance Criteria:**

**Given** a `PipelineReport` and gold `DistractorLabel` entries
**When** I run distractor evaluation
**Then** the false positive rate is computed: what fraction of distractors did the pipeline incorrectly flag as contradictions (FR28)

**Given** distractor evaluation results
**When** I request per-divergence-type breakdown
**Then** separate FP rates are reported for each divergence type: `expert_opinion`, `preliminary_vs_final`, `measurement_methodology`, `uncertainty_expression` (FR28)

**Given** evaluation results from multiple dataset versions and/or multiple cases
**When** I run aggregation
**Then** results are aggregated with mean, standard deviation, and confidence intervals across versions and cases (FR29)

**Given** aggregated results for two or more pipelines
**When** I request significance measures
**Then** statistical significance tests are computed for cross-pipeline comparison (e.g., paired bootstrap or permutation test) (FR29)

**Given** aggregation
**When** it processes results
**Then** all computation uses `SeedManager` for any randomized significance testing
**And** the output is an `EvaluationResult` Pydantic model with aggregate and per-version breakdowns

## Epic 6: Benchmark Release & Reproducibility

Other researchers can clone the repo, evaluate versioned gold datasets with auditing pipelines, and reproduce published baseline results deterministically — without running the generation pipeline.

### Story 6.1: Versioned Gold Dataset Generation & Verification

As a researcher,
I want at least one fully verified gold dataset version shipped with the repository,
So that other researchers can evaluate their systems immediately without running the generation pipeline.

**Acceptance Criteria:**

**Given** the generation pipeline (Epics 2–3) has processed source cases (Grenfell, COPA, or NTSB)
**When** `verify_dataset.py` runs on the generated output
**Then** all gold contradiction labels pass diff verification — no unverified labels ship

**Given** a verified dataset
**When** it is packaged into `data/datasets/{version}/`
**Then** every case directory contains: `anonymized_docs/` with `.txt` files, `contradictions/` with JSONL files, `distractors/` with JSONL, `metadata/` with knowledge graph and registry JSONs, `original_claims/` with per-document claim JSONs, and `validation/` with verification logs

**Given** a dataset version
**When** I inspect the version-level files
**Then** `generation_params.json` documents all injection parameters (version ID, contradiction rates per scope, distractor ratio, mechanism/difficulty distributions) (FR4)
**And** `dataset_manifest.json` provides aggregate statistics across all cases (FR30)

**Given** each document in the dataset
**When** I inspect its metadata
**Then** it includes source ID, source-specific document type, source case ID, and scope_map classification (FR31)

**Given** the dataset
**When** I validate all JSONL and JSON files against Pydantic schemas
**Then** every record validates successfully — no schema violations in shipped data

**Given** the shipped dataset
**When** it is committed to the repository
**Then** it is versioned in `data/datasets/` and included in version control (not gitignored)

### Story 6.2: README & Reproduction Verification

As a researcher,
I want clear documentation and verified end-to-end reproducibility,
So that I can clone the repo, run published baselines, and get identical results on any machine.

**Acceptance Criteria:**

**Given** the README
**When** a researcher reads it
**Then** it provides instructions to: install dependencies (`pip install -r requirements.txt`), evaluate shipped datasets with auditing pipelines, reproduce published baseline results, and optionally run the agentic generation pipeline on new source documents from any supported source (Grenfell, COPA, or NTSB) (FR33)

**Given** a fresh clone of the repository on a Linux or macOS machine with Python 3.10+
**When** a researcher follows the README instructions to install and run evaluation
**Then** all dependencies install and evaluation scripts execute without platform-specific errors (NFR9, NFR12)

**Given** a shipped dataset version and the reference pipelines
**When** a researcher runs all pipeline modes (agentic, graph-native if shipped, hybrid) and baselines against the shipped dataset
**Then** evaluation produces identical scores to the published baseline numbers (FR3, NFR1, NFR3)

**Given** two independent runs of the same pipeline with the same seed on the same dataset version
**When** evaluation results are compared
**Then** they are bit-for-bit identical — no variance from unseeded randomness (NFR2, NFR4)

**Given** the README
**When** it describes the generation pipeline
**Then** it clearly states that generation is optional (requires Claude Code CLI + API access), non-deterministic, and not required for evaluation or reproduction
