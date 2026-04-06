---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: []
session_topic: 'CROSSFIRE benchmark design validation — corpus architecture, domain, data composition'
session_goals: 'Confirm/kill design choices, find blind spots, explore alternatives, refine corpus data'
selected_approach: 'ai-recommended'
techniques_used: ['assumption-reversal', 'morphological-analysis', 'reverse-brainstorming']
ideas_generated: [42]
context_file: ''
technique_execution_complete: true
session_active: false
workflow_completed: true
---

# Brainstorming Session Results

**Facilitator:** Al
**Date:** 2026-04-05

## Session Overview

**Topic:** CROSSFIRE benchmark design validation — corpus architecture, domain, data composition
**Goals:** Confirm/kill design choices, find blind spots, explore alternatives, refine corpus data

### Context Guidance

_Project context from prior Claude.ai conversation: CROSSFIRE is a benchmark for evaluating GraphRAG vs Multi-Hop RAG on cross-document coherence/fake news detection. Current design: NTSB/industrial incident domain, 10-100 docs per subcorpus with ~<5 planted incoherences, mix of factual reports + witness testimonies, inter-subcorpus interactions via shared entities, 3-tier incoherence taxonomy._

### Session Setup

_Validation-focused session. User wants to pressure-test existing design before committing, with special emphasis on refining corpus data composition._

## Technique Selection

**Approach:** AI-Recommended Techniques
**Analysis Context:** CROSSFIRE benchmark design validation with focus on corpus data refinement

**Recommended Techniques:**

- **Assumption Reversal:** Surface and challenge every assumption baked into the current CROSSFIRE design
- **Morphological Analysis:** Systematically explore corpus design parameter space
- **Reverse Brainstorming:** Attack from opposite direction — "How could CROSSFIRE fail as a benchmark?"

**AI Rationale:** Validation sessions need structured challenge, not free-form ideation. This sequence moves from destabilizing assumptions -> rebuilding systematically -> stress-testing the result.

---

## Phase 1: Assumption Reversal — Results

### Confirmed Decisions

- **NTSB / industrial incident domain** — confirmed. Public availability, natural report+testimony mix, shared entities across incidents are strong enough reasons.
- **~400 docs scale (5 subcorpora x ~80 docs)** — confirmed. Well within GraphRAG practical limits (~1K-10K chunks). Exact counts tuned experimentally.
- **Diverse document types** — expanded from binary (report/testimony) to variable proportions per subcorpus. Taxonomy to be discovered from real NTSB data. Starting template: investigation report, technical analysis, regulatory filing, press coverage, expert deposition, witness testimony, internal memo, preliminary report.
- **Unified graph, not separate** — confirmed. Separate graphs cannot detect cross-subcorpus incoherences by construction. Connectivity level 0 (no shared entities) serves as baseline within the unified approach.
- **Diagnostic benchmark** — evaluate every pipeline stage (entity resolution, graph construction, retrieval, detection), not just final output. Gold annotations at 5 levels required.
- **Real data first, synthetic fallback** — scrape NTSB, analyze structure, try editing for control. Go fully synthetic only if editing breaks realism, but informed by real structure analysis.
- **Incoherence counts** — tuned empirically, not pre-specified. Fixed or distribution-based, determined by statistical significance during pilot runs.
- **Temporal revisions** — valid document type (preliminary vs final report), no special treatment in attack design — same frequency as any other incoherence mechanism.

### New Design Elements Surfaced

- **3D benchmark matrix:** connectivity x semantic proximity x attack difficulty
- **Entity resolution as explicit evaluation dimension** — vary naming across connectivity levels (identical / paraphrased / abbreviated)
- **Gold annotations at 5 levels:** entity graph, resolution mappings, retrieval paths, incoherence labels, distractor labels
- **System affinity axis:** design incoherences that favor specific architectures to reveal when each wins

### Critical Insight: Cross-Subcorpus Graph Reasoning

GraphRAG community detection (Leiden/Louvain) will likely separate subcorpora into distinct communities due to dense intra-subcorpus connections and sparse inter-subcorpus links. Cross-subcorpus shared entities sit at community boundaries where they're least visible. This is a genuine capability gap the benchmark exposes — neither global search (summarizes per-community) nor local search (stays local) naturally surfaces cross-community contradictions.

### Connectivity vs Hop Distance Asymmetry

GraphRAG and Multi-Hop RAG have different difficulty parameters:

| GraphRAG parameter | Multi-Hop RAG equivalent |
|---|---|
| Connectivity level 0 (no shared entities) | Infinite hop distance (no retrieval path) |
| Connectivity level 1 (identical naming) | Low hop distance (keyword match bridges) |
| Connectivity level 2 (paraphrased naming) | Medium hop distance (needs query reformulation) |
| Connectivity level 3 (dense shared entities) | Low hop distance (many semantic entry points) |

These don't always correlate — creating scenarios where one approach has a structural advantage over the other. This asymmetry is what makes the benchmark informative.

---

## Phase 2: Morphological Analysis — Results

### CROSSFIRE is a Configurable Generator (not a fixed dataset)

Researchers dial parameters and generate corpora at different configurations. Pre-generated gold datasets with full annotations serve as official benchmark baselines for reproducibility.

### Generator Core API

```
generate_corpus(
    subcorpora_count=5,
    docs_per_subcorpus=80,
    connectivity_level=2,
    incoherences={
        scope_distribution: {intra_doc: 0.2, intra_corpus: 0.5, inter_corpus: 0.3},
        mechanism: "uniform",
        detectability_distribution: {single_hop: 0.3, multi_hop: 0.5, entity_resolution: 0.2},
        system_affinity: "balanced",
        count: "auto"  # empirically determined
    },
    distractor_ratio=0.3,
    doc_type_mix="from_data"
)
```

### Task Definition: Unsupervised Coherence Audit

- **NOT query-driven QA** — no evaluation queries, no hints, no prompts
- **Task: corpus in -> incoherence list out** — fully autonomous detection
- **This is a novel task** — no existing system (GraphRAG, Multi-Hop RAG, CLAIRE) does this out of the box

### Three Architecture Families Benchmarked

1. **Graph-native audit** — KG construction + structural consistency detection (KGrist-style)
2. **LLM-agentic audit** — claim extraction + cross-checking without explicit graph (CLAIRE-style)
3. **Hybrid** — graph representation + LLM-driven reasoning over it

Closed set for now. Reference pipeline shipped for each family.

### Two-Layer Evaluation

- **Layer 1: Representation quality** — how well does the system's internal representation capture facts and relationships? Evaluated against gold entity graph.
- **Layer 2: Auditing strategy** — given that representation, how effectively does the system scan for contradictions? Evaluated against gold incoherence labels.

### Incoherence Design Space

**Scope axis:**
- Intra-document
- Intra-subcorpus, cross-document
- Inter-subcorpus

**Mechanism axis:**
- Numeric drift (date, figure, statistic)
- Entity swap (wrong person/org)
- Causal inversion
- Temporal contradiction (event ordering)
- Omission-based implicit contradiction
- Temporal revision conflict (preliminary vs final)

**Detectability axis:**
- Single-hop (blatant, same named entity)
- Multi-hop (requires chaining 2-3 docs)
- Entity-resolution-dependent (paraphrased naming)

**System affinity axis:**
- High connectivity / low semantic proximity (favors GraphRAG)
- Low connectivity / high semantic proximity (favors Multi-Hop RAG)
- High both (easy for all)
- Low both (hard for all)

### Generator Outputs

1. Corpus (documents with metadata — doc type, reliability signal, subcorpus membership)
2. Gold entity graph + entity resolution mappings
3. Gold incoherence labels + distractor labels

### System Output

4. Detected incoherence list (unsupervised, no queries)

### Scale Ceiling

Up to 10,000 docs / 100K chunks. If corpus exceeds that, dimension reduction is external preprocessing outside CROSSFIRE's scope.

---

## Phase 3: Reverse Brainstorming — Results

### "How Could CROSSFIRE Fail?"

**FM1: Nobody can run it**
- Mitigation: Ship pre-generated gold datasets alongside generator code. Generator for custom configurations, gold datasets for reproducible baselines.

**FM2: Incoherences too easy to find**
- LLM contamination risk (models "know" NTSB facts from training data)
- Stylistic tells in LLM-planted incoherences
- Distribution tells (shortcuts rather than reasoning)
- Mitigation: Handled in corpus construction methodology — canary facts, minimal-pair construction, multi-model generation, adversarial filtering. Not a benchmark parameter, baked into the generator.

**FM3: Evaluation metrics don't capture what matters**
- Matching: Both binary (exact match) and partial credit (localization proximity) as separate metrics
- Per-scope scores: Intra-doc, intra-subcorpus, inter-subcorpus reported independently, plus an aggregated metric (design TBD)
- Per-stage scores: Entity resolution, graph construction, scanning — each scored independently, no cascading

**FM4: Nobody adopts it**
- Reference auditing pipelines shipped (one per architecture family) — lowers barrier to entry
- Query-driven mode as possible future extension, not MVP
- Differentiator vs WikiCollide: unstructured multi-source documents, not clean Wikipedia articles

**FM5: Gold annotations are wrong or subjective**
- Annotation policy: when ambiguous, label as contradiction. Real-world use assumes human reviewer deconflicts.
- Living annotations: gold labels updated when accidental incoherences discovered. Benchmark versioning tracks updates.
- Gold graph quality: requires its own validation step before release.

**FM6: Architecture families incomplete**
- Three families only (graph-native, agentic, hybrid). Closed for now, can expand later.

**FM7: Scale doesn't transfer**
- CROSSFIRE targets up to 10K docs / 100K chunks
- Beyond that, dimension reduction techniques outside CROSSFIRE's scope

**FM8: Evaluation too slow**
- No lite mode. Full diagnostic matrix is the benchmark's value proposition.

---

## Research Landscape (from investigation during session)

### Graph-Based Audit Methods — State of the Art

| Approach | Method | Gap for CROSSFIRE |
|---|---|---|
| CLAIRE/WikiCollide (Stanford 2025) | LLM agent extracts claims, clusters, cross-checks. Unsupervised. | Text-based, no graph structure. |
| KGrist (Belth 2020) | Learns Horn clauses from KG, flags violating triples. Unsupervised. | Needs pre-built KG. No NL. |
| SDValidate/DEAN (Paulheim 2014-15) | Statistical anomaly detection on KG values. | Only distributional outliers. |
| TruthFinder/CRH | Trust propagation through source-fact graphs. | Structured data only. |
| OWL Reasoners (HermiT, Pellet) | Formal logic consistency checking. | Requires hand-built axioms. |
| SAFE (DeepMind 2024) | Atomic fact decomposition + retrieval scoring. | Query-driven, but adaptable. |

**Key finding:** No existing system combines graph-structured representation with unsupervised corpus-level contradiction detection end-to-end. CROSSFIRE addresses a genuine gap.

### Contamination & Shortcut Prevention Techniques

- **Dynamic/Live Benchmarks** (LiveBench): monthly regeneration defeats memorization
- **Canary strings** (Oren et al., 2024): detect training data leakage
- **Adversarial filtering** (AFLite/WinoGrande): remove shortcut-exploitable items
- **Contrastive/minimal-pair construction** (VitaminC): modifications differ only in target phenomenon
- **Multi-model generation**: prevent style fingerprinting
- **Annotation artifacts awareness** (Gururangan et al., 2018): hypothesis-only baselines expose shortcuts

---

## Session Summary

### What CROSSFIRE Is (Refined)

CROSSFIRE is a **configurable benchmark generator** for evaluating **unsupervised corpus-level coherence auditing** across three architecture families (graph-native, LLM-agentic, hybrid). It produces multi-source document corpora in the NTSB/industrial incident domain with controlled incoherences, rich gold annotations at 5 levels, and diagnostic evaluation at every pipeline stage.

### Key Differentiators

1. **Unsupervised coherence audit** — no queries, corpus in -> incoherence list out (novel task)
2. **Configurable generator** — not a fixed dataset, researchers control parameters
3. **Diagnostic evaluation** — per-stage, per-scope, binary + partial metrics
4. **Multi-source unstructured documents** — not clean structured Wikipedia (vs WikiCollide)
5. **3D evaluation matrix** — connectivity x semantic proximity x attack difficulty
6. **Three architecture families** with reference pipelines

### Open Items for Next Phase

- Exact document type taxonomy (from NTSB data analysis)
- Incoherence distribution parameters (empirical pilot runs)
- Aggregated metric design for total task scoring
- Gold graph validation methodology
- Generator implementation architecture

---

## Idea Organization and Prioritization

### Thematic Organization

**Theme 1: Corpus Architecture** — What the benchmark data looks like
- NTSB/industrial incident domain with diverse doc types (variable proportions per subcorpus)
- Real data first, synthetic fallback — structure analysis informs both paths
- Doc type taxonomy discovered from data, not pre-imposed
- Up to 10K docs / 100K chunks ceiling
- Temporal revisions as a doc type with no special attack treatment

**Theme 2: Benchmark Topology** — How the evaluation space is structured
- 3D matrix: connectivity x semantic proximity x attack difficulty
- Connectivity-hop distance asymmetry between GraphRAG and Multi-Hop RAG
- Configurable generator + gold baselines for reproducibility
- Unified graph mandatory — connectivity level 0 as baseline config

**Theme 3: Task Definition** — What systems are asked to do
- Unsupervised coherence audit — corpus in, incoherence list out, no queries
- Novel task — nothing existing does this end-to-end
- Three architecture families: graph-native, LLM-agentic, hybrid
- Reference pipelines shipped per family

**Theme 4: Evaluation Design** — How results are measured
- Two-layer evaluation: representation quality + auditing strategy
- Binary + partial credit as separate metrics
- Per-scope scores (intra-doc / intra-subcorpus / inter-subcorpus) + aggregated metric TBD
- Per-stage scores (entity resolution / graph construction / scanning) — independent, no cascading
- Annotation policy: ambiguous = contradiction, human reviewer deconflicts

**Theme 5: Robustness & Integrity** — How the benchmark stays trustworthy
- Contamination prevention baked into generator methodology
- Living annotations — gold labels versioned and updated
- Gold graph requires its own validation step

### Breakthrough Concepts

- **Cross-subcorpus graph reasoning gap:** Leiden community detection buries inter-subcorpus links — a genuine capability gap CROSSFIRE exposes
- **System affinity axis:** deliberately design incoherences favoring specific architectures, revealing *when* each wins
- **Unsupervised audit as novel task:** no existing system combines graph representation with unsupervised corpus-level contradiction detection

### Prioritization Results

**P0 — Must resolve before anything else:**
1. NTSB data scraping + structure analysis (everything depends on understanding the real data)
2. Generator architecture design (core deliverable)

**P1 — Design during generator build:**
3. Incoherence injection methodology (contamination-aware)
4. Gold annotation schema + validation methodology
5. Evaluation metric formalization

**P2 — After generator exists:**
6. Reference pipeline implementations (3 families)
7. Aggregated metric design
8. Pilot runs for empirical parameter tuning

### Action Planning

**P0-1: NTSB Data Scraping + Structure Analysis**
- Immediate: Access data.ntsb.gov docket search, identify 5-8 major accident dockets with shared entities
- Analyze: Document types present, entity density, natural overlap patterns
- Deliverable: Data structure report informing generator design

**P0-2: Generator Architecture Design**
- Immediate: Define generator input schema (the API spec from Phase 2)
- Design: Corpus construction pipeline, annotation generation pipeline
- Deliverable: Technical architecture document

**P1-3: Incoherence Injection Methodology**
- Apply: Minimal-pair construction, canary facts, multi-model generation, adversarial filtering
- Deliverable: Injection protocol baked into generator

**P1-4: Gold Annotation Schema**
- Define: 5-layer annotation format (entity graph, resolution mappings, retrieval paths, incoherence labels, distractor labels)
- Validate: Cross-check methodology for gold graph quality
- Deliverable: Annotation specification

**P1-5: Evaluation Metric Formalization**
- Define: Binary + partial credit metrics, per-scope and per-stage scoring
- Design: Standard output format for system incoherence reports
- Deliverable: Evaluation protocol document

---

## Session Completion

**Session Achievements:**
- 3 techniques executed (Assumption Reversal, Morphological Analysis, Reverse Brainstorming)
- 5 thematic clusters organized
- 3 breakthrough concepts identified
- 8 failure modes addressed with mitigations
- 8 prioritized action items across 3 tiers
- 2 research investigations completed (GraphRAG scalability, contamination prevention)

**CROSSFIRE is now a validated, well-defined benchmark concept ready for formalization into a product brief.**
