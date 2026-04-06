---
stepsCompleted:
  - "step-01-document-discovery"
  - "step-02-prd-analysis"
  - "step-03-epic-coverage-validation (skipped - no epics document)"
  - "step-04-ux-alignment (skipped - no UX document)"
  - "step-05-epic-quality-review (skipped - no epics document)"
  - "step-06-final-assessment"
documentsAssessed:
  prd: "_bmad-output/planning-artifacts/prd.md"
  architecture: null
  epics: null
  ux: null
---

# Implementation Readiness Assessment Report

**Date:** 2026-04-06
**Project:** CROSSFIRE

## PRD Analysis

### Functional Requirements

**Corpus Generation (FR1-FR5):**
- FR1: Researcher can generate a multi-source document corpus in the NTSB/industrial incident domain with configurable parameters (subcorpora count, documents per subcorpus, document type mix)
- FR2: Researcher can configure connectivity level between subcorpora (level 0-3)
- FR3: Researcher can specify a random seed to produce identical corpora across runs and machines
- FR4: Researcher can select from 3-4 preset configurations that reproduce the paper's experimental conditions
- FR5: Researcher can generate corpora containing heterogeneous document types (8 types listed)

**Incoherence Injection (FR6-FR12):**
- FR6: Researcher can configure incoherence scope distribution (3 scopes)
- FR7: Researcher can configure incoherence mechanism (6 mechanisms)
- FR8: Researcher can configure incoherence detectability distribution (3 levels)
- FR9: Researcher can configure system affinity (balanced, graph-favoring, agentic-favoring)
- FR10: Generator produces incoherences using minimal-pair construction
- FR11: Generator produces distractor labels at a configurable ratio
- FR12: Generator uses same LLM temperature and prompt structure for original and modified text

**Gold Annotation (FR13-FR16):**
- FR13: Generator produces a gold entity graph capturing all entities and relationships
- FR14: Generator produces gold incoherence labels with scope, mechanism, detectability, and system affinity metadata
- FR15: Generator produces gold distractor labels identifying every legitimate divergence
- FR16: Gold annotations are versioned — label corrections trigger a new benchmark version identifier

**Auditing Pipelines (FR17-FR22):**
- FR17: Researcher can run a hybrid auditing pipeline
- FR18: Researcher can run an agentic auditing pipeline (graph layer disabled)
- FR19: Researcher can run a graph-native auditing pipeline (LLM reasoning disabled) — contingent on experimental feasibility
- FR20: All pipeline modes produce incoherence reports in a standardized output format
- FR21: Researcher can run a hypothesis-only baseline (contamination validation)
- FR22: Researcher can run trivial baselines (random, BM25 keyword contradiction)

**Evaluation & Diagnostics (FR23-FR29):**
- FR23: Binary (exact match) scoring against gold labels
- FR24: Partial credit (localization proximity) scoring against gold labels
- FR25: Per-scope evaluation breakdown (intra-document, intra-subcorpus, inter-subcorpus)
- FR26: Per-stage evaluation breakdown (entity resolution, graph construction, scanning) without cascading
- FR27: Evaluate pipeline's internal KG against gold entity graph (Layer 1: representation quality)
- FR28: Measure false positive rate on distractor labels separately
- FR29: Evaluation across multiple seeds with aggregate statistics and significance measures

**Data & Output Management (FR30-FR33):**
- FR30: Pre-generated gold baseline datasets included in the repository
- FR31: Generator outputs corpus documents with metadata
- FR32: All outputs stored in documented, machine-readable formats
- FR33: README sufficient to reproduce all published experimental results

**Total FRs: 33**

### Non-Functional Requirements

**Reproducibility (NFR1-NFR4):**
- NFR1: Same seed + same parameters produces bit-identical corpus output across runs, machines, and operating systems
- NFR2: Evaluation scripts are fully deterministic — identical inputs produce identical scores
- NFR3: Pre-generated datasets reproduce published baseline numbers exactly
- NFR4: All sources of randomness are seeded and documented

**Correctness (NFR5-NFR8):**
- NFR5: Gold annotations verifiably correct — no false labels in shipped datasets
- NFR6: Evaluation scoring mathematically correct — no off-by-one or misalignment errors
- NFR7: Minimal-pair construction does not introduce unintended secondary incoherences
- NFR8: Gold entity graph accurately represents all entities and relationships

**Portability (NFR9-NFR12):**
- NFR9: Runs on Linux and macOS without platform-specific dependencies
- NFR10: No GPU requirement for corpus generation or evaluation
- NFR11: Reference pipelines executable on academic-grade hardware
- NFR12: Python 3.10+ with standard scientific Python ecosystem

**Cost Predictability (NFR13-NFR15):**
- NFR13: Generation cost per subcorpus estimable before execution (~$5-20)
- NFR14: Graceful failure on API errors — no silent retries accumulating charges
- NFR15: Dry-run or cost estimation mode available

**Total NFRs: 15**

### Additional Requirements

- **Contamination prevention methodology:** Minimal-pair construction, same LLM temp/prompt, multi-model generation, canary facts (v2)
- **Annotation policy:** Ambiguous cases labeled as contradiction; human reviewer deconflicts
- **Two-layer evaluation framework:** Layer 1 (representation quality) and Layer 2 (auditing strategy) evaluated independently
- **Scale ceiling:** Up to 10K docs / 100K chunks; dimension reduction is external
- **Benchmark versioning:** Living annotations version-tracked; gold label corrections trigger new versions
- **Core architectural insight:** Leiden/Louvain community detection buries cross-subcorpus entities at community boundaries

### PRD Completeness Assessment

**Strengths:**
- Comprehensive FR coverage across 6 well-defined capability areas (33 FRs)
- NFRs are specific and measurable, not vague quality attributes
- Clear traceability from user journeys → journey requirements → FRs
- Explicit scope boundaries (MVP vs Phase 2 vs Phase 3)
- Risk mitigation with contingency plans (graph-native drop, timeline compression)
- Domain requirements well-tailored to scientific tooling context

**Potential gaps to validate in subsequent steps:**
- No architecture document yet — FRs will need architectural mapping
- No epics/stories yet — FR-to-epic traceability cannot be validated
- UX not applicable (CLI/research tool), but onboarding flow could benefit from design thinking

## Epic Coverage Validation

**SKIPPED** — No epics document exists. Cannot validate FR-to-epic traceability.

## UX Alignment

**SKIPPED** — No UX document exists. For a CLI/research tool, formal UX design may not be needed, but the onboarding flow (clone → install → run baselines) should be designed intentionally during architecture.

## Epic Quality Review

**SKIPPED** — No epics document exists.

## Summary and Recommendations

### Overall Readiness Status

**PRD: READY** — The PRD is comprehensive, well-structured, and ready for downstream work.
**Implementation: NOT READY** — Architecture, epics, and stories must be created before implementation begins.

### Critical Issues Requiring Immediate Action

None for the PRD itself. The PRD is complete and of high quality.

### PRD Quality Assessment

| Criterion | Status | Notes |
|---|---|---|
| Executive Summary with clear vision | ✓ Pass | Dual-outcome vision clearly articulated |
| Measurable success criteria | ✓ Pass | Specific targets with timeframes |
| User journeys covering all personas | ✓ Pass | 4 journeys covering benchmark, generator, infrastructure, and reproducer users |
| Domain-specific requirements | ✓ Pass | Reproducibility, contamination prevention, annotation policy |
| Functional requirements (capability contract) | ✓ Pass | 33 FRs across 6 capability areas, implementation-agnostic |
| Non-functional requirements (measurable) | ✓ Pass | 15 NFRs, specific and testable |
| Scope boundaries (MVP/Growth/Vision) | ✓ Pass | Clear phase separation with rationale |
| Risk mitigation strategy | ✓ Pass | Technical and resource risks with concrete mitigations |
| Traceability chain | ✓ Pass | Vision → Success Criteria → Journeys → FRs |
| Information density | ✓ Pass | Zero fluff, high signal-to-noise |

### Minor Observations (Not Blocking)

1. **FR15 and FR11 overlap slightly** — FR11 says generator produces distractor labels at configurable ratio; FR15 says generator produces gold distractor labels identifying every legitimate divergence. These are complementary (generation vs. annotation) but could be clearer about the distinction.
2. **FR19 contingency** — The "contingent on experimental feasibility" qualifier on FR19 is appropriate but means downstream architecture must handle the possibility of this FR being removed. Architecture should design for easy mode removal.
3. **NFR15 (dry-run mode)** — Not mentioned in the MVP must-have list or FRs. If this is MVP, it should have an FR. If it's post-MVP, the NFR should note that.
4. **Aggregated metric design** — Listed as an open question in the brainstorming but not resolved in the PRD. The FRs cover per-scope and per-stage metrics but don't specify how they aggregate into a total task score. This may be intentional (deferred to implementation) but should be noted.

### Recommended Next Steps

1. **[CA] Create Architecture** (`bmad-create-architecture`) — Map FRs to system components, define the hybrid pipeline architecture with mode switching, resolve output format decisions (JSON/JSONL/directory structure)
2. **[CE] Create Epics and Stories** (`bmad-create-epics-and-stories`) — Break 33 FRs into implementable work packages, establish critical path (NTSB data → generator → pipelines → evaluation → paper)
3. **Re-run this validation** after architecture and epics are complete for full traceability check

### Final Note

This assessment validated the PRD only, as architecture and epics do not yet exist. The PRD scored well across all quality criteria — 33 FRs, 15 NFRs, clear scope boundaries, and strong traceability from vision through requirements. 4 minor observations were noted, none blocking. The PRD is ready to feed architecture and epic creation.
