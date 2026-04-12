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
revisionDate: '2026-04-11'
revisionReason: 'Multi-source generalization — pluggable source adapters for Grenfell, COPA, and NTSB (previously NTSB-only)'
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/product-brief-CROSSFIRE.md"
  - "_bmad-output/planning-artifacts/product-brief-CROSSFIRE-distillate.md"
  - "_bmad-output/brainstorming/brainstorming-session-2026-04-05-001.md"
  - "_bmad-output/planning-artifacts/implementation-readiness-report-2026-04-06.md"
  - "_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-09.md"
workflowType: 'architecture'
project_name: 'CROSSFIRE'
user_name: 'Al'
date: '2026-04-06'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

> **Revision note (2026-04-10):** Updated to reflect the agentic dataset generation pivot. Synthetic generation replaced by real NTSB docket processing via Claude Code CLI. See sprint-change-proposal-2026-04-09.md for full rationale.
>
> **Revision note (2026-04-11):** Generalized from NTSB-only to multi-source architecture. System is now source-agnostic with pluggable source adapters. Three initial sources: Grenfell Tower Inquiry (primary), Chicago COPA (secondary), NTSB Aviation (tertiary). Source-specific processing in `generation/sources/{source_id}/`, shared pipelines remain source-agnostic.

### Requirements Overview

**Functional Requirements:**
32 FRs across 6 capability areas. FR2 (configurable connectivity levels) removed — connectivity is organic to real corpus structure. The corpus processing subsystem (FR1, FR3-FR5, 4 FRs) drives agentic processing of real investigation documents from configured sources (Grenfell Tower Inquiry, Chicago COPA, NTSB Aviation) through anonymization, reformatting, claim extraction, and contradiction injection. Incoherence injection (FR6-FR12, 7 FRs) retains the same 6 mechanisms but executes agentically with diff-based verification. Gold annotation (FR13-FR16, 4 FRs) produces injection-derived gold labels only — the full knowledge graph ships as an intermediate artifact for transparency but is NOT a gold evaluation reference. The auditing subsystem (FR17-FR22, 6 FRs) implements one hybrid architecture with mode switching, now consuming case directories with .txt files and a 2-scope taxonomy (intra_doc, inter_doc). The evaluation subsystem (FR23-FR29, 7 FRs) implements character-span IoU matching, tiered partial credit, and 3 redefined stages (claim extraction, cross-reference identification, contradiction detection). Data management (FR30-FR33, 4 FRs) handles versioned dataset releases with generation_params.json.

**Non-Functional Requirements:**
15 NFRs, 6 rewritten (NFR1, NFR4, NFR5, NFR7, NFR8, NFR13). Reproducibility now means deterministic evaluation against frozen, versioned datasets — generation is inherently non-deterministic (agentic execution). Correctness is strengthened: gold labels are mechanically verified via diff between original and modified documents, not self-reported. Gold evaluation references are injection-derived only. Portability (Linux/macOS, no GPU, academic hardware) and cost predictability (Sonnet/Opus fan-out architecture) remain firm constraints.

**Scale & Complexity:**

- Primary domain: CLI/batch processing pipeline
- Complexity level: Medium
- Estimated architectural components: 3 major subsystems in Python (pipeline, evaluation, shared infrastructure) + 1 external generation toolchain (Claude Code CLI scripts + verification utilities)

### Technical Constraints & Dependencies

- Python 3.10+, clone-and-run repository
- Generation dependency: Claude Code CLI with Sonnet (per-chunk extraction) and Opus (cross-document reasoning) — fan-out architecture
- LLM API dependency for auditing pipelines: model-agnostic (used by agentic/hybrid pipeline modes)
- Graph library: NetworkX or similar for entity graph construction/manipulation in auditing pipelines
- Scientific Python: numpy, scipy, scikit-learn for evaluation metrics
- Seeded randomness in evaluation and pipeline execution only — generation is non-deterministic
- Real investigation documents from configured sources as source material (publicly available): Grenfell Tower Inquiry transcripts/reports (PDF), Chicago COPA case packages (PDF), NTSB aviation docket files (PDF/text)
- PDF parsing: `pypdf` or similar for extracting text from Grenfell transcripts and COPA documents
- Output formats: case directories with .txt files, JSON/JSONL for annotations, JSON for generation parameters
- No package registry publication for v1

### Cross-Cutting Concerns Identified

- **Reproducibility/Seeding:** Reduced scope — applies to evaluation and pipeline execution only. Generation is non-deterministic (agentic). Reproducibility means deterministic evaluation against frozen, versioned datasets.
- **Gold Annotation Schema:** Injection-derived gold labels only. Full knowledge graph ships as intermediate artifact for transparency but is NOT a gold evaluation reference. Schema must be versioned and consistent across the generation→evaluator boundary.
- **Output Format Standardization:** Generation outputs (case directories with anonymized docs + diff-verified gold labels) and pipeline outputs (contradiction reports with 2-scope taxonomy) must follow documented formats enabling cross-component interoperability. Processed datasets are source-agnostic — once documents pass through source-specific processing, the output format is identical regardless of origin source.
- **Diff-Based Verification:** Replaces same-LLM-temp contamination prevention. Mechanical proof that only the target fact changed (±200 char context must be identical). Unintended secondary changes are flagged and rejected. This is the gold truth guarantee.
- **Mode Switching:** The hybrid pipeline's ability to disable graph or LLM layers must be architecturally clean, not feature-flagged spaghetti. Unchanged from original architecture.
- **Dataset Versioning:** Versioned releases with tunable injection parameters (contradiction rates, distractor ratios, mechanism/difficulty distributions). Re-injection on same anonymized base corpus produces new versions without regenerating base material.
- **Generation Boundary:** Generation lives outside `src/crossfire/` as CLI-driven scripts and verification utilities. Hard boundary between generation tooling (bash scripts, plan documents, Claude Code CLI) and the evaluable Python package. Source-specific processing (parsers, agent plans, anonymization rules) lives in `generation/sources/{source_id}/`. Shared generation utilities (chunking, verification, dataset assembly) remain at the `generation/` level.

## Starter Template & Project Foundation

> **Revision note (2026-04-10):** Updated for generation boundary redraw. Generation toolchain moves outside `src/crossfire/` to top-level `generation/` directory.

### Primary Technology Domain

Python 3.10+ CLI/batch processing pipeline + Claude Code CLI agentic generation toolchain. The Python package handles auditing pipelines, evaluation, and shared infrastructure. Generation is driven by bash scripts invoking Claude Code CLI sessions.

### Project Structure Decision

**Selected: `src/` layout** with importable package structure + top-level `generation/` directory.

```
crossfire/
├── src/
│   └── crossfire/
│       ├── __init__.py
│       ├── generator/       # Validation utilities only (diff verification, domain checks)
│       ├── pipeline/        # Hybrid auditing pipeline with mode switching
│       ├── evaluation/      # Two-layer diagnostic evaluation
│       └── shared/          # Seeding, config, output formats, schemas
├── generation/              # Claude Code CLI agentic generation toolchain
│   ├── crossfire_agent_plan.md
│   ├── generate_case.sh
│   ├── generate_all.sh
│   ├── verify_dataset.py
│   ├── chunk_documents.py
│   └── sources/             # Source-specific processing
│       ├── grenfell/        # Grenfell Tower Inquiry (primary)
│       │   ├── agent_plan.md
│       │   └── parser.py
│       ├── copa/            # Chicago COPA (secondary)
│       │   ├── agent_plan.md
│       │   └── parser.py
│       └── ntsb/            # NTSB Aviation (tertiary)
│           ├── agent_plan.md
│           └── parser.py
├── corpus/                  # Source investigation documents (input to generation)
│   ├── grenfell/            # Grenfell Tower Inquiry transcripts and reports
│   ├── copa/                # Chicago COPA case packages
│   └── ntsb/                # NTSB aviation docket files
├── tests/
├── data/
│   └── datasets/            # Versioned gold datasets (output of generation)
├── notebooks/               # Optional Jupyter notebook
├── requirements.txt
├── README.md
└── run.py                   # Entry points for pipeline execution and evaluation
```

**Rationale:** `src/` layout keeps the evaluable Python package independently installable. The `generation/` directory is deliberately outside `src/crossfire/` because generation is a CLI-driven agentic process (bash scripts + Claude Code CLI), not a Python library. This hard boundary prevents generation tooling from leaking into the evaluable package and makes the separation of concerns physical, not just logical.

### Dependency Management

**Selected: `requirements.txt`** — academic standard, zero learning curve for researchers.

Core dependencies:
- `networkx` — Entity graph construction and manipulation in auditing pipelines
- `numpy` — Numerical operations, seeded randomness
- `scipy` — Statistical significance testing
- `scikit-learn` — Evaluation metrics
- `pydantic` — Schema enforcement for all data contracts
- `loguru` — Structured logging
- `python-dotenv` — API key management
- `pyyaml` — Configuration file parsing
- `pytest` — Testing (dev dependency)

Optional dependencies:
- `openai` / `anthropic` — LLM API calls for auditing pipeline modes (model-agnostic)

Generation dependencies (outside Python package):
- Claude Code CLI with access to Sonnet and Opus models
- `pypdf` — PDF text extraction for Grenfell transcripts and COPA documents

### Testing Framework

**Selected: `pytest`** — standard for Python scientific tooling. Tests organized in `tests/` mirroring `src/crossfire/` structure. Generation verification tests live alongside verification utilities.

### Linting & Type Checking

**Skipped for MVP.** No ruff, black, mypy, or pre-commit hooks. Speed of iteration takes priority over code style enforcement during the 6-8 week timeline.

### Architectural Decisions Established by Foundation

| Decision | Choice | Rationale |
|---|---|---|
| Package layout | `src/crossfire/` + `generation/` | Hard boundary between evaluable Python package and CLI generation toolchain |
| Entry point | `run.py` + module execution | Clone-and-run for researchers, no CLI framework overhead |
| Dependencies | `requirements.txt` | Academic standard, minimal friction |
| Testing | `pytest` | Standard, no setup overhead |
| Code style | None enforced | MVP speed priority |
| Python version | 3.10+ | Standard for current NLP tooling |
| Generation toolchain | Claude Code CLI + bash | Agentic execution, not Python library |

**Note:** Project initialization with this structure should be the first implementation story.

## Core Architectural Decisions

> **Revision note (2026-04-10):** Data architecture rewritten for case directory layout. SeedManager and LLM wrapper scopes reduced. Gold truth architecture decision added. Implementation sequence updated for phased approach.

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Gold truth architecture (injection-derived vs full KG)
- Output format schema (generation ↔ pipeline ↔ evaluator contracts)
- Pipeline mode switching architecture (input format adaptation)
- Dataset versioning model
- Diff-based verification pipeline

**Deferred Decisions (Post-MVP):**
- Multi-model LLM provider abstraction for auditing pipelines (Phase 2)
- Aggregated metric design (deferred per brainstorming)
- Additional source adapters beyond initial three (Phase 2)

### Gold Truth Architecture

**Decision: Injection-derived gold only. Full KG is NOT a gold evaluation reference.**

The agentic generation pipeline produces two classes of structured output:

- **Full Knowledge Graph** — extracted during claim extraction phase. Contains all factual claim triples and cross-references discovered by the agent. Ships with the dataset for transparency and reproducibility, but may contain extraction biases (the agent's interpretation of what constitutes a "claim"). **NOT used for evaluation scoring.**
- **Injection-derived gold labels** — produced during contradiction injection, mechanically verified via diff between original and modified documents. Character offsets, original text, and modified text are derived from diffs, not self-reported. Agent's self-reported mechanism, difficulty, and rationale are preserved as metadata. **This is the only gold truth used for evaluation.**

**Rationale:** Using the full KG as gold would mean evaluating pipelines against one agent's interpretation of claims — circular and bias-prone. Injection-derived gold is mechanically provable: if the diff shows the text changed at position X, the gold label at position X is correct by construction. This makes CROSSFIRE's gold truth stronger than any self-reported annotation scheme.

**Architectural implication:** The evaluator imports `ContradictionLabel` and `DistractorLabel` schemas only. It never imports or references `KnowledgeGraphClaim` or `CrossReference` schemas for scoring purposes.

### Data Architecture — Output Formats

**Decision: Case directories with .txt files + JSON/JSONL for structured data**

**Dataset-level files:**
- **`generation_params.json`:** Per-version injection parameters (version ID, base_version, contradiction rates per scope, distractor ratio, mechanism/difficulty distributions). JSON.
- **`dataset_manifest.json`:** Aggregate statistics across all cases in the version. JSON.

**Per-case layout:**
- **Anonymized documents:** Individual `.txt` files per document type in `anonymized_docs/` (e.g., `hearing_transcript_day_01.txt`, `witness_statement.txt`, `ops_group_report.txt`). Plain text, source-agnostic after processing. Document types are source-dependent strings (not a fixed enum).
- **Gold contradiction labels:** JSONL files in `contradictions/` — `intra_doc_contradictions.jsonl`, `inter_doc_contradictions.jsonl`, `all_contradictions.jsonl`. Each line is a `ContradictionLabel` with scope, mechanism, detectability, system affinity, difficulty, char_start/char_end, original_text, modified_text, rationale, ground_truth.
- **Distractor labels:** JSONL in `distractors/distractor_labels.jsonl`. Same structure, flagged as distractor with divergence type.
- **Knowledge graph:** JSON in `metadata/knowledge_graph.json`. Intermediate artifact — ships for transparency, NOT for evaluation.
- **Supporting metadata:** `metadata/domain_registry.json`, `metadata/scope_map.json`, `metadata/entity_mapping.json`.
- **Validation logs:** `validation/diff_verification_log.json`, `validation/rejected_contradictions.jsonl`, `validation/agent_label_discrepancies.json`, `validation/unintended_modifications.json`.
- **Original claims:** Per-document JSON files in `original_claims/` (intermediate, for reproducibility).

**Pipeline contradiction reports:** Single JSON file per run. Standardized format across all pipeline modes — array of detected contradictions with 2-scope taxonomy (intra_doc, inter_doc), document references, text spans, and confidence.

**Evaluation results:** Single JSON file per evaluation run. Per-scope (2-level), per-stage (3-stage) breakdowns with aggregate statistics.

**Rationale:** Case directories mirror real investigation docket structure, making the benchmark more authentic and the data more navigable. Plain .txt for documents because auditing pipelines should work with unstructured text. JSONL for labels because they're appendable and per-line parseable. JSON for metadata because it's read-once structured data. The output format is source-agnostic — all sources produce the same case directory structure after processing.

### Pipeline Architecture — Mode Switching

**Decision: Strategy pattern with injected dependencies (unchanged)**

```
HybridPipeline
├── graph_strategy: GraphStrategy | NullGraphStrategy
├── reasoning_strategy: ReasoningStrategy | NullReasoningStrategy
└── run(case_dir) → contradiction_report
```

- **Hybrid mode:** Real graph strategy + real reasoning strategy
- **Agentic mode:** Null graph strategy + real reasoning strategy (CLAIRE-style claim extraction)
- **Graph-native mode:** Real graph strategy + null reasoning strategy (KG structural anomaly detection)

**Input format adaptation:** Pipeline loads case directories with individual .txt files from `anonymized_docs/` instead of JSONL subcorpus files. `PipelineConfig` accepts `case_dir` path. `PipelineReport` uses 2-scope taxonomy (intra_doc, inter_doc).

**FR19 contingency:** If graph-native is dropped, delete `GraphStrategy` and `NullReasoningStrategy` implementations. `HybridPipeline` still works with only agentic mode. No conditionals to remove, no dead code paths.

**Rationale:** Each strategy is independently testable. Mode switching is constructor injection, not runtime branching. Adding a new strategy (Phase 3, open architecture) is adding a class, not modifying existing code. The input format change is a loading concern, not a strategy concern — strategies receive parsed documents regardless of on-disk format.

### Seeding & Reproducibility

**Decision: Centralized SeedManager (reduced scope)**

```python
class SeedManager:
    def __init__(self, master_seed: int):
        self.master_seed = master_seed

    def get_seed(self, component: str, index: int = 0) -> int:
        # Deterministic derivation from master + component name + index
        return hash((self.master_seed, component, index)) % (2**32)
```

- Used by auditing pipelines and evaluation only — **not used by generation**
- Generation is non-deterministic (agentic execution via Claude Code CLI)
- Reproducibility = deterministic evaluation against frozen, versioned datasets
- LLM calls in auditing pipelines use temperature 0 where supported
- `SeedManager` is instantiated once per pipeline/evaluation run from config
- Seed is logged in output metadata for reproducibility verification

**Rationale:** Single point of control for randomness in the evaluable components. Generation non-determinism is acceptable because gold truth is diff-verified, not seed-dependent. What matters is that the same dataset + same pipeline seed = same evaluation results.

### LLM Integration

**Decision: Thin wrapper function (reduced scope)**

```python
def llm_call(prompt, model="default", temperature=0, seed_manager=None, dry_run=False):
    # Cost estimation logging
    # Dry-run mode returns estimated cost without calling API
    # Retry with exponential backoff on transient errors
    # Fail loudly on non-transient errors (no silent retries)
    # Returns response + token usage for cost tracking
```

- Used by auditing pipelines only — **generation uses Claude Code CLI directly**
- Model parameter is configurable (pipelines may use different LLM providers)
- Cost tracking: accumulates token usage across pipeline calls, reports total at end
- Dry-run mode: estimates cost from prompt token count without API call
- Graceful failure: exponential backoff on rate limits, immediate fail on auth/quota errors

**Rationale:** All pipeline LLM calls go through one function, keeping cost tracking centralized and making model switching a single-point change. Generation LLM costs are tracked by the Claude Code CLI session, not by this wrapper.

### Decision Impact Analysis

**Implementation Sequence (Phased):**

```
Phase A — Foundation updates (can start immediately):
  Schema rewrites (new Pydantic models for contradictions, KG, anonymization)
  Adapt plan document for CLI-native execution

Phase B — Generation infrastructure:
  Source corpus acquisition & inventory
  Document chunking utility
  Bash wrapper scripts (generate_case.sh, generate_all.sh)
  Diff verification utility (verify_dataset.py)
  Dataset versioning support

Phase C — Injection (depends on Phase B):
  Intra-doc contradiction injection (via CLI)
  Inter-doc contradiction injection (via CLI)
  Distractor generation (via CLI)

Phase D — Pipeline & evaluation adaptation (can parallel with B-C):
  Pipeline format adaptation (case directories, 2-scope taxonomy)
  Evaluation changes (char-span IoU, tiered partial credit, 3-stage redefined)

Phase E — Release:
  Generate and verify datasets
  README
```

**Cross-Component Dependencies:**
- SeedManager → used by pipeline and evaluation
- LLM wrapper → used by agentic/hybrid pipeline modes
- Output schemas → produced by generation toolchain, consumed by pipeline and evaluator
- Strategy interfaces → define the contract between pipeline and its graph/reasoning components
- Diff verification → validates generation output before it enters the pipeline/evaluation boundary
- `generation_params.json` → consumed by dataset versioning, evaluation aggregation

## Implementation Patterns & Consistency Rules

> **Revision note (2026-04-10):** Schema organization updated for new data models. Enforcement guidelines updated for generation boundary. Core patterns (naming, logging, error handling) unchanged.

### Critical Conflict Points

6 areas where AI agents could make inconsistent choices, all resolved below.

### Naming Patterns

**Python Code:**
- Functions/variables: `snake_case` (Python standard)
- Classes: `PascalCase` (Python standard)
- Constants: `UPPER_SNAKE_CASE`
- Module files: `snake_case.py`

**JSON Output Fields: `snake_case`**
- All JSON/JSONL output files use `snake_case` field names: `document_type`, `char_start`, `system_affinity`
- Pydantic models serialize to snake_case by default — no aliasing needed
- This applies to contradiction labels, distractor labels, knowledge graph claims, pipeline reports, and evaluation results

**Configuration (JSON/YAML):**
- Keys use `snake_case` matching JSON convention: `contradiction_rate`, `distractor_ratio`

### Schema Enforcement

**Decision: Pydantic models for all data contracts**

- Every output format (contradiction label, distractor label, knowledge graph claim, pipeline report entry, evaluation result) has a corresponding Pydantic model in `src/crossfire/shared/schemas/`
- Models enforce types, required fields, and value constraints (e.g., `scope: Literal["intra_doc", "inter_doc"]`)
- Serialization/deserialization always goes through Pydantic — no raw dict construction
- Schema changes are versioned alongside dataset versioning (FR16-NEW)

**Schema organization:**
```
src/crossfire/shared/schemas/
├── __init__.py
├── corpus.py              # Document (with source field, source-dependent document_type)
├── contradictions.py      # ContradictionLabel, DistractorLabel (replaces incoherences.py)
├── knowledge_graph.py     # KnowledgeGraphClaim, CrossReference (intermediate, not gold)
├── domain_registry.py     # DomainRegistry
├── scope_map.py           # ScopeMap
├── anonymization.py       # AnonymizationMapping
├── reports.py             # DetectedContradiction, PipelineReport (2-scope taxonomy)
├── evaluation.py          # ScopeResult, StageResult, EvaluationResult
└── config.py              # PipelineConfig, DatasetVersion, GenerationParams
```

**Rationale:** Pydantic gives type validation, JSON serialization, and documentation in one place. If the verification utility produces a malformed contradiction label, Pydantic catches it at creation time — not when the evaluator reads it later.

### File I/O Pattern

**Deferred.** Shared loaders/savers vs per-component I/O will be determined during implementation based on actual data complexity. Pydantic models provide the contract regardless of how files are read/written.

### Logging

**Decision: `loguru`**

- All Python components use `loguru` for logging — no `print()` statements, no stdlib `logging`
- Log levels: `DEBUG` for internal state, `INFO` for progress/milestones, `WARNING` for recoverable issues, `ERROR` for failures
- Pipeline progress logged at `INFO` level (case N of M, document N of M)
- LLM API calls logged at `DEBUG` level with token counts
- Cost accumulation logged at `INFO` level at end of pipeline run
- Seed values logged at `INFO` level at start of every pipeline/evaluation run
- Generation logging handled by Claude Code CLI session logs (outside Python)

**Rationale:** `loguru` has zero-config setup, structured output, and better formatting than stdlib logging. Research debugging benefits from detailed but filterable logs.

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
def run_pipeline(case_dir, strategy, seed_mgr) -> tuple[PipelineReport | None, str | None]:
    response, error = llm_call(prompt, ...)
    if error:
        return None, f"LLM call failed: {error}"
    return PipelineReport(**parse(response)), None

# Good: exception for unrecoverable
def load_config(path: str) -> PipelineConfig:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    return PipelineConfig.parse_file(path)
```

**Rationale:** Return-value errors make failure handling explicit and visible in code flow. Researchers debugging "why did my pipeline skip case 7" can trace exactly which cases failed and why, rather than hunting through exception stack traces.

### Enforcement Guidelines

**All AI agents implementing CROSSFIRE MUST:**
- Define Pydantic models for any new data structure before writing producer/consumer code
- Use `snake_case` for all JSON field names — no exceptions
- Use `loguru` for all output — no `print()` statements
- Return error values from fallible functions — no exceptions for expected failures
- Obtain seeds from `SeedManager` in pipeline/evaluation code — never call `random.seed()` directly
- Respect the generation boundary — Python code in `src/crossfire/` never drives generation; `generation/` scripts never import from `src/crossfire/` (except shared schemas for verification)
- Use injection-derived gold labels for evaluation scoring — never reference full KG as gold truth

**Anti-Patterns:**
- Constructing raw dicts instead of Pydantic model instances
- Using camelCase in JSON output "because JavaScript convention"
- Catching and silencing errors with bare `except: pass`
- Hardcoding seeds or using `random.random()` without SeedManager
- Using `print()` for debugging and leaving it in
- Importing generation tooling into the evaluable Python package
- Evaluating pipeline output against full knowledge graph instead of injection-derived gold

## Project Structure & Boundaries

> **Revision note (2026-04-10):** Complete redraw for agentic generation pivot. Generation toolchain moved to top-level `generation/`. Dataset layout restructured to case directories. Boundaries expanded from 2 to 3. Data flow redrawn.

### Complete Project Directory Structure

```
crossfire/
├── README.md
├── requirements.txt
├── run.py                                  # CLI entry points: pipeline, evaluate
├── .env                                    # API keys (gitignored)
├── .env.example                            # Template with placeholder values
├── .gitignore
├── generation/                             # Claude Code CLI agentic generation toolchain
│   ├── crossfire_agent_plan.md             # System prompt for CLI sessions
│   ├── generate_case.sh                    # Bash wrapper: one CLI session per case
│   ├── generate_all.sh                     # Outer loop over all cases
│   ├── verify_dataset.py                   # Post-generation diff verification
│   ├── chunk_documents.py                  # Deterministic document chunking
│   └── sources/                            # Source-specific processing
│       ├── grenfell/                       # Grenfell Tower Inquiry adapter
│       │   ├── agent_plan.md               # Source-specific generation plan
│       │   └── parser.py                   # PDF transcript/report parser
│       ├── copa/                           # Chicago COPA adapter
│       │   ├── agent_plan.md
│       │   └── parser.py                   # COPA document package parser
│       └── ntsb/                           # NTSB Aviation adapter
│           ├── agent_plan.md
│           └── parser.py                   # NTSB docket file parser
├── corpus/                                 # Source investigation documents (not shipped, gitignored)
│   ├── grenfell/                           # Grenfell Tower Inquiry
│   │   └── {case_id}/                      # e.g., grenfell_main
│   │       ├── hearing_transcript_day_01.pdf
│   │       ├── witness_statement_xyz.pdf
│   │       └── ...
│   ├── copa/                               # Chicago COPA
│   │   └── {case_id}/                      # e.g., copa_2023_0456
│   │       ├── firearm_summary_report.pdf
│   │       ├── tactical_response_report.pdf
│   │       └── ...
│   └── ntsb/                               # NTSB Aviation
│       └── {case_id}/                      # e.g., ntsb_ERA22FA123
│           ├── ops_group_report.pdf
│           ├── meteorology_report.pdf
│           └── ...
├── data/
│   └── datasets/                           # Versioned gold datasets (FR30-NEW)
│       └── {version}/
│           ├── generation_params.json      # Injection parameters for this version
│           ├── dataset_manifest.json       # Aggregate statistics across cases
│           └── {case_id}/                       # Source-agnostic after processing
│               ├── metadata/
│               │   ├── domain_registry.json
│               │   ├── scope_map.json
│               │   ├── knowledge_graph.json      # Intermediate — NOT gold eval reference
│               │   └── entity_mapping.json
│               ├── anonymized_docs/
│               │   ├── {document_type}.txt       # Source-dependent document types
│               │   └── ...
│               ├── contradictions/
│               │   ├── intra_doc_contradictions.jsonl
│               │   ├── inter_doc_contradictions.jsonl
│               │   └── all_contradictions.jsonl
│               ├── original_claims/
│               │   ├── ops_group_claims.json
│               │   └── ...
│               ├── distractors/
│               │   └── distractor_labels.jsonl
│               └── validation/
│                   ├── domain_check_log.json
│                   ├── rejected_contradictions.jsonl
│                   ├── diff_verification_log.json
│                   ├── agent_label_discrepancies.json
│                   └── unintended_modifications.json
├── src/
│   └── crossfire/
│       ├── __init__.py
│       ├── shared/
│       │   ├── __init__.py
│       │   ├── seed_manager.py              # Centralized SeedManager (pipeline/eval only)
│       │   ├── llm.py                       # Thin LLM wrapper (pipeline only)
│       │   ├── io.py                        # File I/O utilities (if needed)
│       │   └── schemas/
│       │       ├── __init__.py
│       │       ├── corpus.py                # Document (with source field, source-dependent document_type)
│       │       ├── contradictions.py        # ContradictionLabel, DistractorLabel
│       │       ├── knowledge_graph.py       # KnowledgeGraphClaim, CrossReference
│       │       ├── domain_registry.py       # DomainRegistry
│       │       ├── scope_map.py             # ScopeMap
│       │       ├── anonymization.py         # AnonymizationMapping
│       │       ├── reports.py               # DetectedContradiction, PipelineReport
│       │       ├── evaluation.py            # ScopeResult, StageResult, EvaluationResult
│       │       └── config.py               # PipelineConfig, DatasetVersion, GenerationParams
│       ├── generator/
│       │   ├── __init__.py
│       │   └── validation/                  # Post-generation verification utilities
│       │       ├── __init__.py
│       │       ├── diff_verifier.py         # Diff-based gold label verification
│       │       ├── domain_checker.py        # Domain consistency validation
│       │       └── contamination_checker.py # Stylistic contamination detection
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── hybrid_pipeline.py           # Main pipeline with strategy injection (FR17-FR20)
│       │   ├── strategies/
│       │   │   ├── __init__.py
│       │   │   ├── base.py                  # GraphStrategy, ReasoningStrategy interfaces
│       │   │   ├── graph_strategy.py        # KG construction + anomaly detection (FR19)
│       │   │   ├── reasoning_strategy.py    # LLM claim extraction + cross-checking (FR18)
│       │   │   └── null_strategies.py       # NullGraphStrategy, NullReasoningStrategy
│       │   └── baselines/
│       │       ├── __init__.py
│       │       ├── hypothesis_only.py       # Surface feature detection (FR21)
│       │       ├── random_baseline.py       # Random guess baseline (FR22)
│       │       └── bm25_baseline.py         # BM25 keyword contradiction (FR22)
│       └── evaluation/
│           ├── __init__.py
│           ├── evaluator.py                 # Main evaluation orchestrator
│           ├── binary_scorer.py             # Char-span IoU scoring (FR23-NEW)
│           ├── partial_scorer.py            # Tiered partial credit scoring (FR24-NEW)
│           ├── scope_breakdown.py           # Per-scope analysis: 2 scopes (FR25-NEW)
│           ├── stage_breakdown.py           # Per-stage analysis: 3 stages redefined (FR26-NEW)
│           ├── representation_eval.py       # Injection-derived gold only (FR27-NEW)
│           ├── distractor_eval.py           # Per-divergence-type FP rate (FR28-NEW)
│           └── aggregate.py                 # Multi-version/case aggregation (FR29-NEW)
├── tests/
│   ├── conftest.py                          # Shared fixtures, test SeedManager
│   ├── shared/
│   │   ├── test_seed_manager.py
│   │   ├── test_llm.py
│   │   └── test_schemas.py
│   ├── generator/
│   │   └── test_validation.py               # Diff verifier, domain checker tests
│   ├── pipeline/
│   │   ├── test_hybrid_pipeline.py
│   │   ├── test_strategies.py
│   │   └── test_baselines.py
│   └── evaluation/
│       ├── test_binary_scorer.py
│       ├── test_partial_scorer.py
│       └── test_scope_breakdown.py
├── output/                                  # Runtime output (gitignored)
│   ├── reports/                             # Pipeline contradiction reports
│   └── evaluation/                          # Evaluation results
└── notebooks/
    └── walkthrough.ipynb                    # Optional end-to-end demo
```

### Architectural Boundaries

**Generation → Dataset Boundary (Verification Gate):**
- Generation toolchain produces: case directories with anonymized .txt files + self-reported gold labels
- `verify_dataset.py` validates: diffs original vs modified docs, generates char-offset gold from diffs, flags unintended changes, rejects failing contradictions
- Only verified output crosses into `data/datasets/`
- Contract: `ContradictionLabel`, `DistractorLabel`, `GenerationParams` Pydantic schemas

**Dataset → Pipeline Boundary:**
- Pipeline consumes: anonymized .txt files from `case_NNN/anonymized_docs/` only
- Pipeline NEVER reads gold contradiction labels, distractor labels, or knowledge graph
- Pipeline loads case directories via `PipelineConfig.case_dir`
- Contract: `Document` Pydantic schema (loaded from .txt files + metadata)

**Pipeline + Gold → Evaluator Boundary:**
- Pipeline produces: `PipelineReport` JSON with 2-scope taxonomy (standardized across all modes)
- Evaluator consumes: `PipelineReport` + injection-derived gold labels (`ContradictionLabel`, `DistractorLabel`)
- Evaluator NEVER references full `knowledge_graph.json` for scoring purposes
- Contract: `PipelineReport`, `ContradictionLabel`, `DistractorLabel` Pydantic schemas

**Shared Infrastructure → Pipeline + Evaluation:**
- `SeedManager` injected into pipeline and evaluator at initialization (not generation)
- `llm_call` used by pipeline (agentic/hybrid modes) only
- Pydantic schemas imported by verification utilities, pipeline, and evaluator

**Strategy Boundary (Pipeline Internal):**
- `HybridPipeline` depends only on `GraphStrategy` and `ReasoningStrategy` interfaces
- Concrete implementations are injected — pipeline doesn't know which mode it's running
- Null strategies produce empty results, not errors

### Requirements to Structure Mapping

| FR Category | Directory | Key Files |
|---|---|---|
| Corpus Processing (FR1, FR3-FR5) | `generation/` | `crossfire_agent_plan.md`, `generate_case.sh`, `generate_all.sh`, `chunk_documents.py` |
| Contradiction Injection (FR6-FR12) | `generation/` (agentic) + `src/crossfire/generator/validation/` | `crossfire_agent_plan.md` (injection phases), `diff_verifier.py` (FR10-NEW, FR12-NEW) |
| Gold Annotation (FR13-FR16) | `generation/` + `src/crossfire/generator/validation/` | `verify_dataset.py` (FR14-NEW), `diff_verifier.py`, `config.py` (FR16-NEW DatasetVersion) |
| Auditing Pipelines (FR17-FR22) | `src/crossfire/pipeline/` | `hybrid_pipeline.py`, `strategies/`, `baselines/` |
| Evaluation & Diagnostics (FR23-FR29) | `src/crossfire/evaluation/` | All evaluator modules |
| Data & Output Management (FR30-FR33) | `data/datasets/`, `README.md` | Versioned datasets, `generation_params.json` |

### Data Flow

```
corpus/{source_id}/{case_id}/ (real investigation documents)
       │
       ▼
┌─────────────────┐                    ┌──────────────┐                    ┌─────────────┐
│  generation/     │  verified case    │  Pipeline     │  ContradictionRpt  │  Evaluator   │
│  sources/{id}/   │  directories      │  (FR17-FR22)  │                    │  (FR23-FR29) │
│  (source-specific│  (source-agnostic)│               │                    │              │
│   + shared)      │ ───────────────▶ │               │ ─────────────────▶│              │
└─────────────────┘                    └──────────────┘                    └─────────────┘
       │         ▲                                                              ▲
       │         │                                                              │
       │   verify_dataset.py              injection-derived gold labels         │
       │   (diff verification gate)                                             │
       └────────────────────────────────────────────────────────────────────────┘
                                    data/datasets/{version}/

```

- Source-specific parsers in `generation/sources/{source_id}/` process raw documents from `corpus/{source_id}/`
- Generation produces source-agnostic anonymized docs + gold labels in `data/datasets/{version}/`
- `verify_dataset.py` validates all gold labels via diff before they ship
- Pipeline reads anonymized docs only from case directories, writes report to `output/reports/`
- Evaluator reads injection-derived gold labels + pipeline report, writes results to `output/evaluation/`
- Pipeline NEVER reads gold labels — hard architectural boundary
- Evaluator NEVER references full knowledge graph for scoring — hard architectural boundary

## Architecture Validation Results

> **Revision note (2026-04-10):** Re-validated against revised FR/NFR set from sprint change proposal. All mappings updated for agentic generation pivot.

### Coherence Validation ✓

**Decision Compatibility:**
- Python 3.10+ / Pydantic / NetworkX / loguru / pytest / python-dotenv — all compatible, no version conflicts
- Claude Code CLI (generation) + Python package (pipeline/evaluation) — clean separation, no runtime dependency conflicts
- Thin LLM wrapper + SeedManager + Pydantic schemas form a coherent shared infrastructure layer for the evaluable package
- Strategy pattern for pipeline modes is compatible with all evaluation approaches
- Diff-based verification is compatible with Pydantic schema enforcement — diffs produce data, Pydantic validates it

**Pattern Consistency:**
- snake_case enforced across Python code, JSON output, and config files — no convention splits
- Return-value error handling is consistent with loguru logging (errors logged, then returned)
- Pydantic models as the universal data contract — verification utilities, pipeline, and evaluator all speak the same schema language
- 2-scope taxonomy (intra_doc, inter_doc) used consistently across gold labels, pipeline reports, and evaluation breakdowns

**Structure Alignment:**
- `generation/` at project root separates CLI-driven tooling from evaluable Python package — boundary is physical
- `src/crossfire/` with `shared/`, `generator/validation/`, `pipeline/`, `evaluation/` maps cleanly to the architectural subsystems
- Strategy pattern files live inside `pipeline/strategies/` — boundary is physical, not just logical
- Test structure mirrors source structure — no ambiguity about where tests go
- `data/datasets/{version}/{case_id}/` layout is source-agnostic after processing

### Requirements Coverage Validation ✓

**Functional Requirements (32/32 covered):**

| FR | Architectural Support |
|---|---|
| FR1-NEW | `generation/crossfire_agent_plan.md`, `generate_case.sh`, `generate_all.sh` |
| FR2 | Removed — connectivity is organic to real corpus structure |
| FR3-NEW | Frozen versioned datasets in `data/datasets/`, deterministic evaluation via SeedManager |
| FR4-NEW | `data/datasets/{version}/generation_params.json`, `config.py` DatasetVersion |
| FR5-NEW | `generation/sources/{source_id}/agent_plan.md` preserves source-specific document type diversity |
| FR6-NEW | `generation/crossfire_agent_plan.md` (2-scope: intra_doc, inter_doc), `contradictions.py` |
| FR7 | `generation/crossfire_agent_plan.md` (6 mechanisms unchanged) |
| FR8 | `generation/crossfire_agent_plan.md` (detectability distribution unchanged) |
| FR9 | `generation/crossfire_agent_plan.md` (system affinity unchanged) |
| FR10-NEW | `generation/crossfire_agent_plan.md` + `generator/validation/diff_verifier.py` |
| FR11 | `generation/crossfire_agent_plan.md` (distractor generation), `contradictions.py` DistractorLabel |
| FR12-NEW | `generator/validation/diff_verifier.py`, `contamination_checker.py` (±200 char validation) |
| FR13-NEW | `metadata/knowledge_graph.json` (intermediate, NOT gold eval reference), `knowledge_graph.py` |
| FR14-NEW | `generation/verify_dataset.py` + `generator/validation/diff_verifier.py` → `contradictions.py` |
| FR15 | `contradictions.py` DistractorLabel, `distractors/distractor_labels.jsonl` |
| FR16-NEW | `config.py` DatasetVersion + GenerationParams, `generation_params.json` per version |
| FR17-NEW | `pipeline/hybrid_pipeline.py` loading case directories |
| FR18-NEW | `pipeline/strategies/reasoning_strategy.py` + `null_strategies.py` |
| FR19-NEW | `pipeline/strategies/graph_strategy.py` (contingent), evaluated against injection-derived gold only |
| FR20-NEW | `schemas/reports.py` PipelineReport with 2-scope taxonomy |
| FR21 | `pipeline/baselines/hypothesis_only.py` |
| FR22 | `pipeline/baselines/random_baseline.py`, `bm25_baseline.py` |
| FR23-NEW | `evaluation/binary_scorer.py` with char-span IoU matching |
| FR24-NEW | `evaluation/partial_scorer.py` with tiered scoring (1.0/0.7/0.4/0.2) |
| FR25-NEW | `evaluation/scope_breakdown.py` (2 scopes: intra_doc, inter_doc) |
| FR26-NEW | `evaluation/stage_breakdown.py` (3 stages: claim extraction, cross-ref ID, contradiction detection) |
| FR27-NEW | `evaluation/representation_eval.py` (injection-derived gold only, not full KG) |
| FR28-NEW | `evaluation/distractor_eval.py` (per-divergence-type breakdown) |
| FR29-NEW | `evaluation/aggregate.py` (multi-version/case aggregation + significance) |
| FR30-NEW | `data/datasets/{version}/` with diff-verified labels + generation_params.json |
| FR31-NEW | `schemas/corpus.py` Document with source field, source-dependent document_type, case ID, scope_map classification |
| FR32 | Case directories with .txt + JSON/JSONL format decision |
| FR33-NEW | `README.md` covering evaluation, reproduction, and optional generation |

**Non-Functional Requirements (15/15 covered):**

| NFR | Architectural Support |
|---|---|
| NFR1-NEW (Frozen datasets) | Versioned datasets in `data/datasets/`, deterministic evaluation |
| NFR2-NFR3 (Deterministic eval) | SeedManager for pipeline/evaluation, temperature 0 |
| NFR4-NEW (Seeded pipeline/eval) | SeedManager, generation randomness is inherent to agentic execution |
| NFR5-NEW (Diff-verified gold) | `verify_dataset.py`, `diff_verifier.py` — no self-reported labels without diff |
| NFR6 (Scoring correctness) | Pydantic validation, schema enforcement |
| NFR7-NEW (Single-fact modification) | `diff_verifier.py` flags unintended secondary changes |
| NFR8-NEW (Injection-derived gold only) | Evaluator imports ContradictionLabel only, never KnowledgeGraphClaim for scoring |
| NFR9-NFR12 (Portability) | No GPU, standard Python ecosystem, Linux/macOS, Claude Code CLI |
| NFR13-NEW (Cost predictability) | Fan-out: Sonnet for extraction, Opus for cross-doc. Cost breakdown logged per phase. |
| NFR14-NFR15 (Graceful failure, dry-run) | LLM wrapper with backoff + dry-run mode for pipeline costs |

### Gaps Identified & Resolved

| Gap | Resolution |
|---|---|
| `corpus/` directory not in .gitignore | Add to .gitignore — source investigation documents not shipped |
| `generation/` scripts may need to import shared schemas | Allowed exception to generation boundary — verification utilities import Pydantic schemas for validation |
| Verification utility placement ambiguity | `verify_dataset.py` in `generation/` (orchestrator), `diff_verifier.py` in `src/crossfire/generator/validation/` (reusable logic) |
| Claude Code CLI cost tracking not in Python | Generation costs tracked by CLI session logs, not LLM wrapper. Document this separation. |
| `output/` directory undocumented | Runtime output directory, gitignored |

### Updated Dependencies

```
requirements.txt:
  networkx
  numpy
  scipy
  scikit-learn
  pydantic
  loguru
  python-dotenv
  pyyaml
  pytest  # dev

Optional (for auditing pipeline LLM calls):
  openai
  anthropic

Generation dependencies (outside Python package):
  pypdf  # PDF text extraction for Grenfell/COPA source documents
```

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed (32 FRs, 15 NFRs — updated for pivot)
- [x] Scale and complexity assessed (medium, batch pipeline + agentic generation)
- [x] Technical constraints identified (Python 3.10+, Claude Code CLI, no GPU, API costs)
- [x] Cross-cutting concerns mapped (seeding, schemas, diff verification, dataset versioning, generation boundary, mode switching)

**✅ Architectural Decisions**
- [x] Gold truth architecture: injection-derived only, full KG is intermediate artifact
- [x] Data architecture: case directories + .txt + JSON/JSONL
- [x] Pipeline architecture: Strategy pattern with injected dependencies (unchanged)
- [x] Reproducibility: SeedManager for pipeline/eval, frozen datasets for generation
- [x] LLM integration: Thin wrapper for pipeline only, generation via Claude Code CLI
- [x] Diff-based verification: mechanical gold truth guarantee
- [x] Dataset versioning: generation_params.json per version, re-injection support
- [x] Schema enforcement: Pydantic models for all data contracts
- [x] Logging: loguru
- [x] Error handling: Return-value first, exceptions for unrecoverable

**✅ Implementation Patterns**
- [x] Naming conventions: snake_case everywhere
- [x] Schema enforcement: Pydantic before producer/consumer code
- [x] Logging: loguru only, no print statements
- [x] Error handling: Return-value errors for expected failures
- [x] Seeding: SeedManager for pipeline/eval, no direct random calls
- [x] Generation boundary: Python package never drives generation, generation scripts only import shared schemas

**✅ Project Structure**
- [x] Complete directory structure with FR mapping
- [x] Three architectural boundaries defined (generation→dataset, dataset→pipeline, pipeline+gold→evaluator)
- [x] Hard boundary: pipeline never reads gold labels
- [x] Hard boundary: evaluator never references full KG for scoring
- [x] Hard boundary: generation tooling outside evaluable Python package
- [x] Data flow documented with input/output per subsystem

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION (post-pivot)

**Confidence Level:** High

**Key Strengths:**
- Real investigation documents from multiple sources provide authentic benchmark data that no synthetic pipeline can match
- Diff-based gold verification is mechanically provable — stronger than any self-reported annotation scheme
- Clean 3-boundary architecture with physical separation (generation/, src/crossfire/, data/datasets/)
- Strategy pattern makes FR19 contingency (drop graph-native) architecturally trivial
- Dataset versioning enables injection rate tuning without regenerating base corpus
- Every FR maps to specific files — no ambiguity about where to implement

**Areas for Future Enhancement (Phase 2+):**
- LLM provider abstraction for multi-model auditing pipelines
- Additional source adapters beyond the initial three (Grenfell, COPA, NTSB)
- Formal Python API with documented public interfaces
- Aggregated metric design (deferred, implementation will inform design)

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use Pydantic models for every data structure — no raw dicts
- Respect all three architectural boundaries:
  - Generation tooling stays in `generation/` — never in `src/crossfire/` (except shared schemas for verification)
  - Pipeline never reads gold labels from dataset
  - Evaluator never references full KG for scoring — injection-derived gold only
- Use SeedManager for pipeline/evaluation randomness — no direct random calls
- Use loguru for all Python output — no print statements
- Return error values from fallible functions — exceptions only for unrecoverable
- Validate all gold labels via diff verification before shipping datasets

**Implementation Sequence:**
1. Schema rewrites + plan document adaptation (Phase A)
2. Source corpus acquisition + chunking + bash wrapper + verification utilities (Phase B)
3. Agentic injection via Claude Code CLI (Phase C, depends on B)
4. Pipeline format adaptation + evaluation changes (Phase D, parallel with B-C)
5. Generate and verify datasets + README (Phase E)
