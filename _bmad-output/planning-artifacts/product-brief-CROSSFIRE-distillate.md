---
title: "Product Brief Distillate: CROSSFIRE"
type: llm-distillate
source: "product-brief-CROSSFIRE.md"
created: "2026-04-05"
purpose: "Token-efficient context for downstream PRD creation"
---

# CROSSFIRE Product Brief Distillate

## Rejected Ideas and Scope Exclusions

- **Query-driven evaluation mode** rejected for v1. CROSSFIRE is unsupervised (corpus in, incoherence list out). Query-driven may be added as future extension but dilutes the novel contribution.
- **Benchmark lite mode** rejected. Full diagnostic matrix is the value proposition. No subset configurations.
- **Open architecture category** rejected. Only three families (graph-native, agentic, hybrid). Keeps benchmark focused. Expand later if needed.
- **Separate per-subcorpus graphs** rejected. Cannot detect cross-subcorpus incoherences by construction. Unified graph mandatory; connectivity level 0 serves as baseline.
- **5-layer gold annotations for v1** rejected per feasibility review. Ship 3 layers (entity graph, incoherence labels, distractor labels). Add entity resolution mappings and retrieval paths for v2/camera-ready.
- **3 separate pipeline implementations** rejected per feasibility review. Build one hybrid architecture with 3 operating modes (disable graph = agentic, disable LLM reasoning = graph-native).
- **Full generator parameter space evaluation** rejected for paper. Fix most parameters, generate 3-4 preset configurations varying connectivity level. Ship code with full parameter space documented but not exhaustively evaluated.
- **Commercial vision / startup angle** removed from brief. Not substantiated. Personal motivation only — not part of research contribution.
- **RAG hallucination reframing** ("your RAG isn't hallucinating, your corpus is incoherent") — deferred, not convinced. May revisit.
- **Distractor labels as headline differentiator** — deferred, depends on experimental difficulty. A priori non-essential.
- **Dimension reduction for >10K docs** — out of scope. External preprocessing.
- **Domains beyond NTSB** — out of scope for v1.

## Requirements Hints

- Generator must support seeded generation for reproducibility across researchers
- Pre-generated gold datasets must ship alongside generator code — researchers can use benchmark without running generation
- Generator should have a domain abstraction layer (even if only NTSB ships in v1) to support future domain extension
- Output format for system incoherence reports must be standardized across all three architecture families
- Evaluation scripts should be built from Day 1 alongside generator, not after
- Annotation policy: when ambiguous, label as contradiction. Human reviewer deconflicts in practice. Living annotations with benchmark versioning.
- Incoherence counts are empirically tuned, not pre-specified. Fixed or distribution-based, determined by statistical significance during pilot runs.

## Technical Context

### Generator Core API (from brainstorming)
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
        count: "auto"
    },
    distractor_ratio=0.3,
    doc_type_mix="from_data"
)
```

### Incoherence Design Space (4-dimensional)
- **Scope:** intra-document / intra-subcorpus cross-document / inter-subcorpus
- **Mechanism:** numeric drift (date, figure) / entity swap (wrong person/org) / causal inversion / temporal contradiction (event ordering) / omission-based implicit / temporal revision conflict (preliminary vs final)
- **Detectability:** single-hop (blatant, same naming) / multi-hop (chain 2-3 docs) / entity-resolution-dependent (paraphrased naming)
- **System affinity:** high connectivity + low semantic proximity (favors GraphRAG) / low connectivity + high semantic proximity (favors Multi-Hop RAG) / high both (easy) / low both (hard)

### Document Type Taxonomy (starting template, adjusted from real data)
Investigation report, technical analysis, regulatory filing, press coverage, expert deposition, witness testimony, internal memo, preliminary report. Variable proportions per subcorpus. Taxonomy discovered from NTSB data, not pre-imposed.

### Connectivity Levels
- Level 0: No shared entities (baseline, equivalent to separate graphs)
- Level 1: Shared entities with identical naming
- Level 2: Shared entities with paraphrased/abbreviated naming (entity resolution challenge)
- Level 3: Dense shared entities across subcorpora

### Connectivity vs Hop Distance Asymmetry
| GraphRAG parameter | Multi-Hop RAG equivalent |
|---|---|
| Connectivity level 0 (no shared entities) | Infinite hop distance (no retrieval path) |
| Connectivity level 1 (identical naming) | Low hop distance (keyword match bridges) |
| Connectivity level 2 (paraphrased naming) | Medium hop distance (needs query reformulation) |
| Connectivity level 3 (dense shared entities) | Low hop distance (many semantic entry points) |
These don't always correlate — creating scenarios where one approach has a structural advantage.

### Scale Constraints
- Target: up to 10K docs / 100K chunks
- Default: ~400 docs (5 subcorpora x ~80 docs)
- GraphRAG practical limits: ~1K-10K chunks. Degradation starts at 10K+ chunks.
- Indexing cost at default scale: ~$5-20 per subcorpus with GPT-4o-mini

### Contamination Prevention (baked into generator methodology)
- **Minimal-pair construction** (priority) — change only the fact, not surrounding prose
- **Same LLM temperature/prompt** for both original and modified text to prevent stylistic tells
- Hypothesis-only baseline experiment in paper to demonstrate shortcuts aren't driving performance
- Canary facts and adversarial filtering deferred to v2

### Three Architecture Families — Implementation Strategy
One hybrid pipeline with three operating modes:
1. **Hybrid (full):** Graph representation + LLM-driven reasoning over graph
2. **Agentic mode:** Disable graph layer → CLAIRE-style claim extraction + cross-checking
3. **Graph-native mode:** Disable LLM reasoning → KG construction + structural anomaly detection (KGrist-style)

### Two-Layer Evaluation
- **Layer 1: Representation quality** — system's internal KG vs gold entity graph
- **Layer 2: Auditing strategy** — contradiction detection given representation vs gold incoherence labels

### Evaluation Metrics
- Binary (exact match) + partial credit (localization proximity) as separate metrics
- Per-scope: intra-doc / intra-subcorpus / inter-subcorpus independently + aggregated metric (design TBD)
- Per-stage: entity resolution / graph construction / scanning — independent, no cascading
- False positive rate on distractor labels (legitimate divergences)

## CLAIRE/WikiCollide Reference Details (from paper)

### CLAIRE Architecture
- ReAct agent (Yao et al., 2023) with research + verification interleaved
- 10 steps per fact, 15 passages retrieved per query
- `clarify` tool (entity disambiguation) + `explain` tool (terminology explanation)
- GPT-4o backbone, mGTE embeddings, RankGPT reranking
- Greedy decoding (temperature 0)
- Total experimental cost: <$4,000

### WikiCollide Dataset
- 955 atomic facts from Wikipedia Level 5 Vital Articles
- 34.7% inconsistent (331), 65.3% consistent (624)
- Validation/test split: 477/478
- Inconsistency types: Numerical 54.7% (off-by-one 23.0%, clear 31.7%), Logical 17.5% (direct 14.8%, indirect 2.7%), Definition 10.6%, Temporal 7.9%, Named Entity 6.0%, Categorical 2.1%, Spatial 1.2%

### CLAIRE Performance (GPT-4o, test set)
- CLAIRE: Accuracy 69.3, F1 69.6, AUROC 75.1
- Retrieve-and-verify: 69.0 / 69.7 / 73.0
- NLI pipeline: 67.0 / 70.2 / 72.2
- Substantial headroom remains (best AUROC 75.1%)

### CLAIRE Error Patterns (directly informs CROSSFIRE design)
- Systems conflate distinct entities sharing same name → false positive inconsistency flags
- Numerical context failures (rounding vs real errors)
- Perspective/belief distinction failures ("Alice believes X" flagged as contradicting "Bob believes Y")
- Legitimate scholarly interpretation variation flagged incorrectly
- Language context issues (translation variants treated as inconsistencies)

## Competitive Landscape

### Direct Competitors (corpus-level inconsistency)
- **CLAIRE/WikiCollide** (Stanford, EMNLP 2025): Closest. Wikipedia-only, fixed dataset, no graph evaluation, per-fact classification not corpus audit. CROSSFIRE addresses all stated limitations.
- **WikiContradict** (IBM, NeurIPS 2024): 253 inter-context conflict instances from Wikipedia. Tests LLM behavior under knowledge conflicts, not autonomous auditing.
- **ContraDoc** (NAACL 2024): 449 intra-document self-contradictions only. Misses cross-document scope.

### Adjacent Benchmarks (fact verification / RAG evaluation)
- **FEVER/FEVEROUS/HoVer/VitaminC**: Query-driven, assume corpus consistency. CROSSFIRE challenges this assumption.
- **GraphRAG-Bench** (ICLR 2026): Evaluates GraphRAG on QA accuracy, not consistency auditing.
- **GRADE** (EMNLP 2025): 2D difficulty matrix for multi-hop RAG — conceptually adjacent but for QA.
- **MultiHop-RAG** (COLM 2024): 2556 queries over news articles. Infrastructure useful but no contradiction detection.

### Graph-Based Audit Methods (potential baselines)
- **KGrist** (Belth 2020): Learns Horn clauses from KG, flags violating triples. Needs pre-built KG.
- **SDValidate/DEAN** (Paulheim 2014-15): Statistical anomaly detection on KG values. Only distributional outliers.
- **TruthFinder/CRH**: Trust propagation through source-fact graphs. Structured data only.
- **OWL Reasoners** (HermiT, Pellet): Formal logic consistency checking. Requires hand-built axioms.
- **SAFE** (DeepMind 2024): Atomic fact decomposition + retrieval scoring. Query-driven but adaptable.

### Key Market Signals
- GraphRAG underperforms vanilla RAG by 13.4% on simple queries — only wins on complex multi-source synthesis. CROSSFIRE targets exactly this capability.
- GPT-4 and LLaMA-3 perform barely above random at detecting contradictions in RAG contexts (2025 study).
- NTSB data has NLP precedent (SafeAeroBERT from NASA, topic modeling) but zero prior work on cross-document contradiction detection.
- Configurable benchmark generators becoming accepted paradigm (LiveBench, BenchmarkDataNLP.jl).

## Failure Modes and Mitigations (from brainstorming)

1. **Nobody can run it** → Ship pre-generated gold datasets + generator code
2. **Incoherences too easy** → Contamination prevention in generator methodology
3. **Metrics don't capture what matters** → Binary + partial, per-scope, per-stage independent
4. **Nobody adopts it** → Reference pipelines shipped, clear differentiator vs WikiCollide
5. **Gold annotations wrong** → Label ambiguous as contradiction, living annotations, gold graph validation
6. **Architecture families incomplete** → Three families closed for now
7. **Scale doesn't transfer** → Up to 10K docs / 100K chunks ceiling
8. **Evaluation too slow** → No lite mode, full matrix is value proposition

## Timeline and Feasibility Notes

- **Target:** EMNLP submission. Generator + gold dataset in 2 weeks. All pipelines benchmarked in 1 month. Paper in 6 weeks.
- **Solo project.** Feasibility review suggests 8 weeks realistic, or 6 weeks with pre-work (NTSB data exploration + related work drafting before clock starts).
- **Critical path:** NTSB data scraping (3-day hard timebox, then go synthetic) → Generator with preset configs → Hybrid pipeline with 3 modes → Evaluation runs + baselines → Paper
- **Build evaluation scripts from Day 1.** Run baselines (random, BM25 keyword contradiction) in Week 3 while building pipelines.
- **Write incrementally:** Related work + methodology in Weeks 1-2, results + analysis in Weeks 5-6.
- **Litmus test before full experiments:** Design 2-3 test incoherences that should show architecture-dependent detection to validate the system affinity hypothesis early.

## Open Questions

- Exact document type taxonomy (emerges from NTSB data analysis)
- Incoherence distribution parameters (empirical pilot runs)
- Aggregated metric design for total task scoring across scopes
- Gold entity graph validation methodology
- Generator implementation architecture (Python library? CLI? Both?)
- Comparable diagnostic checkpoints across architecturally different pipelines
- Whether distractor labels become a headline contribution (depends on experimental difficulty)
- Whether RAG hallucination angle adds value to paper positioning
