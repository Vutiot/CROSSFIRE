# Sprint Change Proposal — Agentic Dataset Generation Pivot

**Date:** 2026-04-09
**Author:** Al (with SM guidance)
**Status:** Approved (2026-04-09)
**Scope Classification:** Major

---

## 1. Issue Summary

### Problem Statement

The current CROSSFIRE dataset generation pipeline (Epics 2-3, 6) uses a programmatic Python pipeline that generates synthetic documents from scratch via LLM API calls with hardcoded entity pools, connectivity levels, and document templates. This approach produces documents that approximate NTSB structure but lack the authenticity of real investigation dockets.

A new approach has been designed (`docs/crossfire_agent_plan.md`) that processes real NTSB investigation docket files through a Claude Code CLI agentic pipeline: anonymization, NTSB reformatting, claim extraction, and contradiction injection. This produces more realistic, domain-grounded benchmark data.

### Discovery Context

Discovered during implementation review after Epics 2-5 were substantially built. The `crossfire_agent_plan.md` document provides a complete 780-line specification for the new approach.

### Key Advantages of the Pivot

- **Authenticity:** Real NTSB documents provide genuine structure, terminology, and inter-document relationships
- **Stronger gold labels:** Diff-based verification makes gold truth mechanically provable
- **Cost efficiency:** Fan-out architecture with Sonnet for extraction, Opus only for cross-document reasoning (~1/10th cost of full-Opus approach)
- **No context window juggling:** Claude Code CLI reads files from disk as needed
- **Dataset versioning:** Injection parameters are tunable across versions without regenerating base corpus

---

## 2. Impact Analysis

### 2.1 Epic Impact

| Epic | Verdict | Details |
|------|---------|---------|
| Epic 1: Foundation | **Modify** | Schemas rewritten (remove EntityGraph, add DomainRegistry/ScopeMap/KnowledgeGraph/ContradictionLabel). SeedManager scope reduced (generation non-deterministic). LLM wrapper scope reduced (used by pipelines only). |
| Epic 2: Corpus Generation | **Replace entirely** | Synthetic generation removed. Replaced by agentic processing of real NTSB dockets with fan-out architecture (chunk → parallel Sonnet extraction → KG merge → per-doc processing → cross-doc Opus pass). |
| Epic 3: Incoherence Injection & Gold Annotation | **Significantly change** | Same 6 mechanisms but agentic execution. Distractors kept with versioning. New label format with char offsets. Diff-based gold verification added. |
| Epic 4: Auditing Pipelines | **Modify** | Format adaptation (case directories, .txt files instead of JSONL). Scope taxonomy 3→2 (intra_doc, inter_doc). Strategy pattern and mode switching survive. |
| Epic 5: Evaluation & Diagnostics | **Modify** | Scope breakdown 3→2. Per-stage redefined (claim extraction, cross-ref identification, contradiction detection). Gold references are injection-derived only — full KG is NOT a gold evaluation reference. Multi-seed → multi-version aggregation. |
| Epic 6: Benchmark Release | **Rewrite** | Versioned dataset releases instead of preset-based generation. New reproduction model (re-evaluate frozen datasets, not regenerate). |

### 2.2 Artifact Impact

| Artifact | Impact |
|----------|--------|
| PRD | 15 FRs rewritten, 6 NFRs modified, editorial updates to Executive Summary, User Journeys, Computational Constraints |
| Architecture | Project structure redrawn (generation/ outside src/crossfire/), data format changes, boundary redraw |
| Epics & Stories | Full rewrite of Epics 2-3-6, story modifications across 1-4-5 |
| `configs/presets/*.yaml` | Replace with `generation_params.json` per dataset version |
| Tests | Generator tests become verification tests, pipeline/eval tests adapt to new formats |
| `data/datasets/` | Restructure from `{preset}/corpus/` to `{version}/case_NNN/` |
| Sprint status | Major update after approval |

### 2.3 Code Impact

**Remove:**
- `src/crossfire/generator/entity_graph_builder.py`
- `src/crossfire/generator/orchestrator.py`
- `src/crossfire/generator/templates/` (all 8 templates + factory + base)
- `src/crossfire/shared/schemas/entities.py` (EntityNode/Edge/Graph)
- Entity pool constants

**Add:**
- `generation/crossfire_agent_plan.md` (system prompt for Claude Code CLI)
- `generation/generate_case.sh` (bash wrapper per case)
- `generation/generate_all.sh` (outer loop over cases)
- `generation/verify_dataset.py` (post-generation diff verification)
- `generation/chunk_documents.py` (deterministic document chunking)
- `src/crossfire/shared/schemas/domain_registry.py`
- `src/crossfire/shared/schemas/scope_map.py`
- `src/crossfire/shared/schemas/knowledge_graph.py`
- `src/crossfire/shared/schemas/anonymization.py`
- `src/crossfire/shared/schemas/contradictions.py` (replaces parts of incoherences.py)
- `src/crossfire/generator/validation/diff_verifier.py`
- `src/crossfire/generator/validation/domain_checker.py`
- `src/crossfire/generator/validation/contamination_checker.py`

**Modify:**
- `src/crossfire/shared/schemas/corpus.py` (remove SubcorpusMetadata, adapt Document)
- `src/crossfire/shared/schemas/config.py` (remove GeneratorConfig presets, add DatasetVersion)
- `src/crossfire/evaluation/scope_breakdown.py` (3 scopes → 2)
- `src/crossfire/evaluation/stage_breakdown.py` (new stage definitions)
- `src/crossfire/evaluation/representation_eval.py` (injection-derived gold only)
- `src/crossfire/evaluation/aggregate.py` (multi-seed → multi-version)
- `src/crossfire/pipeline/hybrid_pipeline.py` (load case directories)

---

## 3. Recommended Approach

### Selected Path: Hybrid Discard + Rewrite

1. **Discard** Epic 2 code (synthetic generation — no longer needed)
2. **Rewrite** Epics 2, 3, 6 for agentic generation with diff verification
3. **Adapt** Epics 1, 4, 5 for new formats, scopes, and evaluation design
4. **Update** PRD with all approved FR/NFR rewrites
5. **Update** Architecture with new boundary (generation/ outside src/crossfire/)

### Rationale

- The pivot strengthens the benchmark's credibility (real documents > synthetic)
- Diff-based gold verification is more rigorous than programmatic string replacement
- Dataset versioning directly enables injection rate tuning
- The evaluation layer (Epics 4-5) survives with manageable adaptations
- Fan-out architecture is cost-effective and parallelizable
- Total effort is comparable — different distribution (less Python coding for generation, more for schema/eval adaptation)

### Trade-offs

| Gained | Lost |
|--------|------|
| Authentic NTSB document structure | Configurable connectivity levels (FR2) |
| Diff-verified gold labels | Bit-identical generation reproducibility (NFR1) |
| Character-level evaluation precision | Subcorpus-level scope granularity |
| Dataset versioning with tunable injection rates | Programmatic generation speed |
| Lower contamination risk (real prose) | SeedManager-controlled generation |

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Agentic generation produces inconsistent quality across cases | Medium | Diff-based verification catches errors; rejected contradictions are logged |
| Claude Code CLI costs higher than expected | Low | Fan-out with Sonnet keeps per-chunk costs low; Opus only for cross-doc pass |
| Real NTSB dockets have insufficient variety | Low | NTSB publishes thousands of major investigation dockets |
| Diff verification catches too many unintended changes, slowing generation | Medium | Iterative prompt refinement in plan document; contamination threshold tunable |
| Gold KG extraction bias leaks into evaluation | Mitigated | Full KG is NOT a gold eval reference — injection-derived claims only |

---

## 4. Detailed Change Proposals

### 4.1 PRD Changes

#### Functional Requirements — Corpus Generation

```
FR1-NEW: Researcher can process real NTSB investigation docket files 
         through an agentic pipeline that anonymizes, reformats, 
         extracts claims, and injects contradictions.

FR2: [Removed — connectivity is organic to real corpus]

FR3-NEW: Researcher can reproduce evaluation results deterministically
         against shipped dataset versions.

FR4-NEW: Researcher can select from versioned datasets with different 
         injection parameters (contradiction rates, distractor ratios, 
         mechanism distributions).

FR5-NEW: Corpus contains heterogeneous NTSB document types as present 
         in the source docket (investigation reports, witness testimonies, 
         meteorology reports, ATC transcripts, maintenance records, etc.).
```

#### Functional Requirements — Incoherence Injection

```
FR6-NEW: Researcher can configure incoherence scope distribution 
         (intra-document, inter-document).

FR10-NEW: Generator produces incoherences using minimal-pair modification,
          verified by mechanical diff between original and modified 
          documents to confirm only the target fact changed.

FR12-NEW: Diff-based validation confirms no stylistic contamination —
          surrounding context (±200 chars) must be identical between 
          original and modified documents.
```

FR7, FR8, FR9, FR11 unchanged.

#### Functional Requirements — Gold Annotation

```
FR13-NEW: Generator produces a knowledge graph of factual claim triples 
          with cross-references as an intermediate artifact. Ships for 
          transparency and reproducibility but is NOT used as gold 
          evaluation reference. Gold references are injection-derived only.

FR14-NEW: Generator produces gold contradiction labels verified by 
          mechanical diff, including: scope, mechanism, detectability, 
          system affinity, difficulty, char_start/char_end offsets, 
          original and contradicted text, rationale, and ground_truth 
          indicator.

FR16-NEW: Dataset versions track both label corrections and injection 
          parameter changes (contradiction rates, distractor ratios, 
          mechanism/difficulty distributions). Each version ships with 
          generation_params.json documenting all parameters.
```

FR15 unchanged.

#### Functional Requirements — Auditing Pipelines

```
FR17-NEW: Researcher can run a hybrid auditing pipeline against a 
          dataset case directory containing anonymized document files 
          and metadata.

FR18-NEW: Researcher can run an agentic auditing pipeline against a 
          dataset case directory.

FR19-NEW: Researcher can run a graph-native auditing pipeline against 
          a dataset case directory — contingent on experimental 
          feasibility. Pipeline's internal KG is evaluated against 
          injection-derived gold claims, not full knowledge graph.

FR20-NEW: All pipeline modes produce contradiction reports in a 
          standardized format with 2-scope taxonomy (intra_doc, 
          inter_doc), document references, text spans, and confidence.
```

FR21, FR22 unchanged.

#### Functional Requirements — Evaluation & Diagnostics

```
FR23-NEW: Researcher can evaluate a pipeline's contradiction report 
          against gold labels using binary scoring with character-span 
          IoU matching (threshold-configurable).

FR24-NEW: Researcher can evaluate using tiered partial credit: precise 
          span match (1.0), approximate span (0.7), correct section 
          (0.4), correct documents only (0.2).

FR25-NEW: Researcher can view evaluation results broken down per-scope 
          (intra-document, inter-document) independently.

FR26-NEW: Researcher can view evaluation results broken down per-stage 
          (claim extraction, cross-reference identification, 
          contradiction detection) independently, evaluated against 
          injection-derived gold references only. Stages do not cascade.

FR27-NEW: Researcher can evaluate a pipeline's internal representation 
          against injection-targeted gold claims and cross-references 
          — not against the full generation-time knowledge graph.

FR28-NEW: Researcher can measure false positive rate on distractor 
          labels, with per-divergence-type breakdown.

FR29-NEW: Researcher can aggregate evaluation results across dataset 
          versions and cases, with significance measures for 
          cross-pipeline comparison.
```

#### Functional Requirements — Data & Output Management

```
FR30-NEW: Versioned gold datasets ship with the repository. Each 
          version contains processed cases with anonymized documents, 
          diff-verified contradiction labels, distractor labels, and 
          generation_params.json.

FR31-NEW: Each document includes metadata: NTSB document type, 
          source case ID, and document classification per scope_map.

FR33-NEW: README provides instructions to: install dependencies, 
          evaluate shipped datasets with auditing pipelines, reproduce 
          published baseline results, and (optionally) run the agentic 
          generation pipeline on new NTSB docket files.
```

FR32 unchanged.

#### Non-Functional Requirements

```
NFR1-NEW: Shipped datasets are frozen, versioned artifacts. Evaluation 
          against shipped datasets produces identical results across 
          runs and machines. Generation is non-deterministic.

NFR4-NEW: All sources of randomness in evaluation and auditing 
          pipelines are seeded and documented. Generation randomness 
          is inherent to agentic execution.

NFR5-NEW: Gold contradiction labels are mechanically verified via diff 
          between original and modified documents. No self-reported 
          labels without diff confirmation.

NFR7-NEW: Diff-based validation confirms each modification touches 
          only the target fact. Unintended secondary changes are 
          flagged and rejected.

NFR8-NEW: Gold evaluation references are injection-derived (targeted 
          claims, used cross-references, contradiction labels). Full 
          knowledge graph ships for transparency but is not a gold 
          evaluation reference.

NFR13-NEW: Generation cost per case is estimable before execution. 
           Fan-out architecture with Sonnet for extraction and Opus 
           for cross-document reasoning. Cost breakdown logged per 
           phase.
```

NFR2, NFR3, NFR6, NFR9-12, NFR14-15 unchanged.

#### PRD Prose Updates

- **Executive Summary:** Replace "configurable benchmark generator" framing with "agentic pipeline processing real NTSB dockets with versioned injection parameters"
- **Core Architectural Insight:** Reframe from synthetic subcorpora community boundaries to natural NTSB domain boundaries (ops vs structures vs meteorology)
- **User Journey — Marcus:** Shift from parameterized connectivity to running pipeline on different cases / dataset versions
- **Computational Constraints:** New cost model for Sonnet/Opus fan-out; remove subcorpus-based sizing
- **Contamination Prevention:** Add diff-based verification; keep multi-model generation note

### 4.2 Architecture Changes

#### Boundary Redraw

```
Current:
  src/crossfire/ = generator + pipeline + evaluation

New:
  generation/    = bash scripts + plan document + verification utilities
  src/crossfire/ = pipeline + evaluation + shared schemas
```

#### Project Structure Delta

```
Remove:
  src/crossfire/generator/entity_graph_builder.py
  src/crossfire/generator/orchestrator.py
  src/crossfire/generator/templates/  (entire directory)
  src/crossfire/shared/schemas/entities.py

Add:
  generation/
    crossfire_agent_plan.md
    generate_case.sh
    generate_all.sh
    verify_dataset.py
    chunk_documents.py
  src/crossfire/generator/validation/
    diff_verifier.py
    domain_checker.py
    contamination_checker.py
  src/crossfire/shared/schemas/
    domain_registry.py
    scope_map.py
    knowledge_graph.py
    anonymization.py
    contradictions.py
```

#### Data Format Changes

```
Current dataset layout:
  data/datasets/{preset}/
    corpus/subcorpus_sc-N.jsonl
    gold/entity_graph.json
    gold/gold_incoherence_labels.json
    gold/gold_distractor_labels.json
    metadata.json

New dataset layout:
  data/datasets/{version}/
    generation_params.json
    dataset_manifest.json
    case_NNN/
      metadata/
        domain_registry.json
        scope_map.json
        knowledge_graph.json      (intermediate, NOT gold eval reference)
        entity_mapping.json
      anonymized_docs/
        ops_group_report.txt
        meteorology_report.txt
        ...
      contradictions/
        intra_doc_contradictions.jsonl
        inter_doc_contradictions.jsonl
        all_contradictions.jsonl
      original_claims/
        ops_group_claims.json
        ...
      distractors/
        distractor_labels.jsonl
      validation/
        domain_check_log.json
        rejected_contradictions.jsonl
        diff_verification_log.json
        agent_label_discrepancies.json
        unintended_modifications.json
```

#### Data Flow Redraw

```
corpus/ (real NTSB dockets)
       │
       ▼
┌─────────────────┐  anonymized docs   ┌──────────────┐  PipelineReport   ┌─────────────┐
│  generation/     │  + gold labels    │  Pipeline     │                   │  Evaluator   │
│  (Claude Code    │ ────────────────▶ │  (FR17-FR22)  │ ────────────────▶│  (FR23-FR29) │
│   CLI agentic)   │                   │              │                   │              │
└─────────────────┘                   └──────────────┘                   └─────────────┘
       │                                                                        ▲
       │              injection-derived gold labels                             │
       └────────────────────────────────────────────────────────────────────────┘

verify_dataset.py validates generation output before it enters the pipeline.
```

### 4.3 Epic & Story Changes

#### Epic 1: Project Foundation (Modify)

**Story 1.1 (Project Scaffolding):** Update directory structure to include `generation/` directory. Update `data/datasets/` layout.

**Story 1.2 (Pydantic Schemas):** Remove `EntityNode`, `EntityEdge`, `EntityGraph`, `SubcorpusMetadata`. Add `DomainRegistry`, `ScopeMap`, `KnowledgeGraphClaim`, `CrossReference`, `AnonymizationMapping`, `ContradictionLabel` (with char offsets, rationale, difficulty, ground_truth), `DatasetVersion`, `GenerationParams`. Adapt `Document` (remove subcorpus_id). Rename `incoherences.py` → `contradictions.py`.

**Story 1.3 (SeedManager):** Unchanged code, reduced scope documentation. Note that generation is non-deterministic.

**Story 1.4 (LLM Wrapper):** Unchanged code, reduced scope documentation. Used by auditing pipelines only.

#### Epic 2: Corpus Processing (Replace — new stories)

**Story 2.1-NEW: Source Corpus Acquisition & Inventory**
As a researcher, I want real NTSB investigation docket files organized by case, so that the agentic pipeline has authentic input material.

Acceptance Criteria:
- Case folders in `corpus/` each contain all docket files for one investigation
- Each file is classified by NTSB document type per the plan's taxonomy (16 types)
- Minimum 5 cases with sufficient document variety for meaningful benchmark

**Story 2.2-NEW: Document Chunking & Manifest**
As a developer, I want documents split into processing-sized segments with provenance tracking, so that fan-out extraction produces traceable results.

Acceptance Criteria:
- `chunk_documents.py` splits documents into 1-2 page segments
- `chunk_manifest.json` maps each chunk to source document, page range, section
- Chunking is deterministic (same document always produces same chunks)
- Chunks are intermediate artifacts — do not ship with dataset

**Story 2.3-NEW: Agentic Plan Document (CLI System Prompt)**
As a developer, I want the `crossfire_agent_plan.md` adapted for Claude Code CLI-native execution, so that a single CLI session processes one case end-to-end.

Acceptance Criteria:
- Plan document replaces "dispatch to Document Agent" with sequential filesystem-based phases
- Plan includes fan-out instructions: Sonnet for per-chunk extraction, Opus for cross-doc reasoning
- Plan references `generation_params.json` for injection rate configuration
- Plan instructs agent to save originals before modification (for diff verification)

**Story 2.4-NEW: Generation Bash Wrapper**
As a researcher, I want bash scripts that invoke Claude Code CLI per case, so that dataset generation is a single command.

Acceptance Criteria:
- `generate_case.sh` runs one CLI session per case directory
- `generate_all.sh` loops over all cases in `corpus/`
- Scripts pass `crossfire_agent_plan.md` as system prompt
- Scripts pass `generation_params.json` for injection configuration
- Exit codes and logs captured per case

#### Epic 3: Contradiction Injection & Gold Annotation (Rewrite — new stories)

**Story 3.1-NEW: Intra-Document Contradiction Injection**
As a researcher, I want the Document Agent phase to inject 2-5 contradictions per document using the 6 mechanisms, so that intra-doc detection is testable.

Acceptance Criteria:
- Agent saves original document before modification
- Agent applies mechanisms from plan (numeric_drift, entity_swap, causal_inversion, temporal_contradiction, omission_based_implicit, temporal_revision_conflict)
- Agent validates each contradiction against domain_registry (6-check validation gate)
- Agent self-reports labels with mechanism, detectability, difficulty, affinity, rationale
- Injection rates configurable via generation_params.json

**Story 3.2-NEW: Inter-Document Contradiction Injection**
As a researcher, I want the Cross-Document Agent phase to inject 3-8 contradictions across documents per case, so that cross-document detection is testable.

Acceptance Criteria:
- Agent uses knowledge graph cross-references to identify natural contradiction sites
- Agent generates same-fact disagreements and cross-witness disagreements per plan
- Agent respects anti-patterns (no cross-domain contamination, no anachronisms, no disclaimer-wrapped irrelevance)
- Agent self-reports labels with same metadata as intra-doc
- Injection rates configurable via generation_params.json

**Story 3.3-NEW: Distractor Generation**
As a researcher, I want legitimate perspective divergences planted alongside contradictions, so that false positive rates are measurable.

Acceptance Criteria:
- Agent generates distractors at configurable ratio relative to contradiction count
- Four divergence types: expert_opinion, preliminary_vs_final, measurement_methodology, uncertainty_expression
- Distractors are labeled with scope, type, description, and location
- Distractor ratio configurable via generation_params.json

**Story 3.4-NEW: Diff-Based Gold Label Verification**
As a researcher, I want gold labels mechanically verified against actual document changes, so that gold truth is provably correct.

Acceptance Criteria:
- `verify_dataset.py` diffs original vs modified documents for every processed file
- Gold labels (char_start, char_end, original_text, modified_text) are generated from diffs, not self-reported
- Agent's self-reported mechanism, difficulty, rationale are preserved as metadata
- Unintended secondary changes (surrounding text modified) are flagged
- Contamination check: surrounding ±200 chars must be identical
- Output: `diff_verification_log.json`, `agent_label_discrepancies.json`, `unintended_modifications.json`
- Contradictions failing verification are moved to `rejected_contradictions.jsonl` with rejection reason

**Story 3.5-NEW: Dataset Versioning**
As a researcher, I want dataset versions with documented injection parameters, so that I can tune rates and compare across versions.

Acceptance Criteria:
- Each version has `generation_params.json` recording: version ID, base_version (if re-injection), contradiction rates per scope, distractor ratio, mechanism distribution, difficulty distribution
- `dataset_manifest.json` aggregates statistics across all cases in the version
- Re-injection workflow: same anonymized base corpus, different injection parameters → new version
- Version comparison utilities for evaluation (Story 5.5)

#### Epic 4: Auditing Pipelines (Modify)

**Story 4.1:** Modify corpus loading to read case directories with individual .txt files instead of JSONL. Update `PipelineConfig` to accept `case_dir`. Update `PipelineReport` to use 2-scope taxonomy.

**Story 4.2:** Adapt reasoning strategy input format. No algorithmic changes.

**Story 4.3:** Adapt graph strategy input format. Internal KG evaluated against injection-derived claims only.

**Story 4.4:** Adapt all baselines to new input format. No algorithmic changes.

#### Epic 5: Evaluation & Diagnostics (Modify)

**Story 5.1:** Update gold label parsing for new ContradictionLabel format. Binary scorer uses char-span IoU matching. Partial credit scorer uses tiered scoring (1.0/0.7/0.4/0.2).

**Story 5.2:** Simplify from 3 scopes to 2 (intra_doc, inter_doc).

**Story 5.3:** Redefine stages: claim extraction, cross-reference identification, contradiction detection. Evaluate against injection-derived gold only. Non-cascading.

**Story 5.4:** Rewrite: evaluate pipeline representation against injection-targeted claims and cross-references only. Full KG is not gold reference. Measure claim coverage, claim precision, cross-reference recovery.

**Story 5.5:** Distractor evaluation adds per-divergence-type breakdown. Aggregation shifts from multi-seed to multi-version/multi-case. Statistical significance for cross-pipeline comparison.

#### Epic 6: Benchmark Release (Rewrite)

**Story 6.1-NEW:** Generate versioned datasets via Claude Code CLI. Run diff verification on all outputs. Ship verified datasets in `data/datasets/{version}/`. Include `generation_params.json` and `dataset_manifest.json`.

**Story 6.2-NEW:** README covers: installing dependencies, evaluating shipped datasets, running auditing pipelines, reproducing baselines, and (optionally) running agentic generation on new NTSB dockets. Reproduction means re-evaluating frozen datasets deterministically.

---

## 5. Implementation Handoff

### Scope Classification: Major

This is a fundamental replan requiring PM/Architect involvement.

### Handoff Responsibilities

| Role | Responsibility |
|------|---------------|
| **Architect (Winston)** | Update architecture document with new boundary (generation/ outside src/crossfire/), new data formats, revised project structure |
| **Product Manager (John)** | Update PRD with all approved FR/NFR rewrites and prose updates |
| **Scrum Master (Bob)** | Rewrite epics.md with new story definitions. Update sprint-status.yaml. Run sprint planning for revised backlog. |
| **Developer (Amelia)** | Implement schema changes (Epic 1), pipeline adaptations (Epic 4), evaluation changes (Epic 5), verification utilities (Story 3.4), bash wrapper (Story 2.4) |
| **Tech Writer (Paige)** | Update plan document for CLI-native execution (Story 2.3). README (Story 6.2). |

### Implementation Sequence

```
Phase A — Foundation updates (can start immediately):
  1.2  Schema rewrites
  2.3  Adapt plan document for CLI-native execution
  
Phase B — Generation infrastructure:
  2.1  Source corpus acquisition
  2.2  Document chunking
  2.4  Bash wrapper
  3.4  Diff verification utility
  3.5  Dataset versioning

Phase C — Injection (depends on Phase B):
  3.1  Intra-doc injection (via CLI)
  3.2  Inter-doc injection (via CLI)
  3.3  Distractor generation (via CLI)

Phase D — Pipeline & evaluation adaptation (can parallel with B-C):
  4.1-4.4  Pipeline format adaptation
  5.1-5.5  Evaluation changes

Phase E — Release:
  6.1  Generate and verify datasets
  6.2  README
```

### Success Criteria

- [ ] All shipped datasets pass diff verification (no unverified gold labels)
- [ ] Pipeline loads and processes case directories correctly
- [ ] Evaluation produces per-scope (2-level) and per-stage (3-stage) breakdowns
- [ ] Gold labels use injection-derived references only (no full KG dependency)
- [ ] Dataset versioning supports re-injection with different parameters
- [ ] At least 2 dataset versions shipped demonstrating parameter variation
- [ ] README enables reproduction of published baselines from shipped datasets
