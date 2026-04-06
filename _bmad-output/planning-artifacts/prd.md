---
stepsCompleted:
  - "step-01-init"
  - "step-02-discovery"
  - "step-02b-vision"
  - "step-02c-executive-summary"
  - "step-03-success"
  - "step-04-journeys"
  - "step-05-domain"
  - "step-06-innovation"
  - "step-07-project-type"
  - "step-08-scoping"
  - "step-09-functional"
  - "step-10-nonfunctional"
  - "step-11-polish"
inputDocuments:
  - "_bmad-output/planning-artifacts/product-brief-CROSSFIRE.md"
  - "_bmad-output/planning-artifacts/product-brief-CROSSFIRE-distillate.md"
  - "_bmad-output/brainstorming/brainstorming-session-2026-04-05-001.md"
documentCounts:
  briefs: 2
  research: 0
  brainstorming: 1
  projectDocs: 0
workflowType: 'prd'
classification:
  projectType: developer_tool
  domain: scientific
  complexity: medium
  projectContext: greenfield
---

# Product Requirements Document - CROSSFIRE

**Author:** Al
**Date:** 2026-04-05

## Executive Summary

CROSSFIRE (Cross-corpus Fact Incoherence Reasoning Evaluation) is a configurable benchmark generator that evaluates unsupervised corpus-level coherence auditing — the task of detecting all factual incoherences in a multi-source document corpus without queries, hints, or human guidance. It targets NLP/IR researchers evaluating retrieval-augmented systems, knowledge graph construction, and fact verification approaches, as well as GraphRAG practitioners who need to understand when graph-based approaches justify their complexity for multi-source consistency tasks.

The project delivers two co-equal outcomes: (1) a benchmark for comparing architectural approaches to corpus auditing (graph-native, LLM-agentic, hybrid), and (2) a standalone research infrastructure — the generator itself — that produces synthetic multi-source corpora with ground-truth entity graphs and controlled incoherences, independently useful for entity resolution, KG construction, and multi-hop reasoning research.

CROSSFIRE ships as open-source tooling alongside a peer-reviewed publication targeting EMNLP. Corpora are generated in the NTSB/industrial incident domain, where heterogeneous document types (investigation reports, technical analyses, witness testimonies, regulatory filings) and cross-incident shared entities mirror the real-world environments where coherence auditing matters most.

### What Makes This Special

No existing benchmark evaluates unsupervised corpus auditing on heterogeneous, unstructured documents. CLAIRE/WikiCollide (Stanford, EMNLP 2025) established corpus-level inconsistency detection as a research task but operates on clean Wikipedia articles with a fixed 955-fact dataset and no graph-based evaluation. CROSSFIRE addresses every gap CLAIRE's own limitations section acknowledges.

The generator is the differentiator. Researchers parameterize corpus generation — subcorpora count, connectivity level, incoherence scope/mechanism/detectability, system affinity — rather than working with a static dataset. Pre-generated gold datasets ship for reproducibility; the generator ships for extensibility. This dual delivery is what gives the project legs beyond a single publication.

The architectural comparison is empirical, not ideological. Three families start as the experimental setup (graph-native via KG construction, LLM-agentic via claim extraction, hybrid combining both), implemented as one architecture with three operating modes. If the benchmark reveals that graph-native approaches can't be adapted to this task, that's a valid finding — the benchmark scopes down and the result still publishes.

### Core Architectural Insight

GraphRAG community detection (Leiden/Louvain) will likely separate subcorpora into distinct communities due to dense intra-subcorpus connections and sparse inter-subcorpus links. Cross-subcorpus shared entities sit at community boundaries where they are least visible to both global search (which summarizes per-community) and local search (which stays local). CROSSFIRE is designed to expose this specific capability gap — measuring when graph-native, agentic, or hybrid approaches each win at detecting contradictions that span community boundaries.

## Project Classification

- **Project Type:** Developer tool — research library/CLI for benchmark generation and evaluation
- **Domain:** Scientific research — NLP benchmarking with reproducibility, validation, and peer review requirements
- **Complexity:** Medium — no regulatory compliance, but high rigor around reproducibility, contamination prevention, and annotation validation
- **Project Context:** Greenfield

## Success Criteria

### User Success

- **Time-to-evaluation:** A researcher generates evaluation-ready corpora with custom parameters in under an hour, without needing to understand generator internals.
- **Diagnostic clarity:** A researcher compares their system against reference pipelines and immediately identifies which pipeline stage fails — entity resolution, graph construction, or reasoning — rather than staring at a single accuracy number.
- **Reproducibility:** Any researcher can reproduce published baselines by running pre-generated gold datasets through shipped evaluation scripts with identical results.
- **Extensibility moment:** A team working on entity resolution or KG construction adapts the generator to produce corpora for their own task, without touching the auditing or evaluation components.

### Business Success

- **Research impact:** Accepted at a top NLP venue (EMNLP target). Cited as a reference for unsupervised corpus auditing.
- **Benchmark adoption:** External research groups evaluate their systems on CROSSFIRE within 12 months of publication.
- **Generator adoption (co-equal metric):** Teams independently adapt the generator to new corpus domains or use it for non-coherence-auditing tasks (entity resolution, KG construction, multi-hop reasoning). This is 50% of project success — the generator outliving the benchmark paper.
- **Open-source traction:** Clean, documented codebase. Pre-generated gold datasets for immediate use. Community contributions or forks within the first year.

### Technical Success

- **Generator validity:** Produces contamination-resistant corpora across all preset configurations. Hypothesis-only baseline confirms shortcuts aren't driving performance.
- **Annotation quality:** Gold annotations pass cross-validation. Living annotations with benchmark versioning.
- **Meaningful baselines:** All reference pipelines produce non-trivial, non-ceiling results — establishing the task as hard but tractable.
- **Architecture-dependent patterns:** Results reveal when and why different approaches succeed or fail across the evaluation matrix (connectivity x semantic proximity x detectability).

### Measurable Outcomes

| Metric | Target | Timeframe |
|---|---|---|
| EMNLP submission | Paper submitted with baselines + ablations | 6-8 weeks |
| Reference pipeline results | Non-trivial for all families tested | Before submission |
| Pre-generated gold datasets | Shipped alongside code at publication | At release |
| Generator standalone reuse | At least 1 external team adapts to new domain | 12 months post-publication |
| Diagnostic evaluation | Per-stage scores differentiate pipeline failure modes | At release |

## User Journeys

### Journey 1: Dr. Priya Mehta — Benchmark Evaluator

**Situation:** Priya is a postdoc at a European NLP lab. Her team built a multi-hop RAG system for legal document analysis and needs to demonstrate it handles cross-document contradictions — a claim they make in their paper draft but can't back up because no benchmark tests this capability.

**Opening Scene:** Priya finds CROSSFIRE through a citation in the CLAIRE paper. She clones the repo and sees pre-generated gold datasets ready to use. She doesn't need to run the generator — she just needs evaluation-ready corpora with ground truth.

**Rising Action:** She loads the default preset corpus (5 subcorpora, connectivity level 2, balanced incoherences) and runs her system against it. She adapts her pipeline's output to CROSSFIRE's standardized incoherence report format. She runs the evaluation scripts and gets back per-stage, per-scope diagnostic scores — not a single number, but a breakdown showing her system's entity resolution is strong but cross-subcorpus detection collapses at connectivity level 2.

**Climax:** The diagnostic breakdown shows her system scores well on intra-subcorpus incoherences (where semantic similarity drives retrieval) but fails on inter-subcorpus cases requiring entity resolution across paraphrased naming. She can now say exactly *where* her pipeline breaks and *why* — something no other benchmark offered.

**Resolution:** Priya adds a CROSSFIRE evaluation section to her paper, showing per-scope results that honestly characterize her system's strengths and limitations. The diagnostic granularity makes the evaluation section more compelling than a single AUROC number on WikiCollide.

---

### Journey 2: Marcus Chen — Custom Corpus Generator

**Situation:** Marcus is a PhD student studying how knowledge graph construction degrades when documents use inconsistent entity naming. He needs corpora where he controls exactly how entities are named across documents — identical, abbreviated, paraphrased — with ground truth for evaluation.

**Opening Scene:** Marcus discovers CROSSFIRE's generator can produce corpora with configurable connectivity levels that directly map to entity naming variation. This is exactly the controlled experimental setup he needs.

**Rising Action:** Marcus writes a Python script using the generator API. He generates three corpus variants: connectivity level 1 (identical naming), level 2 (paraphrased), level 3 (dense, mixed naming). Each corpus comes with a gold entity graph showing the true entity resolution mappings. He doesn't care about the incoherence detection task — he's using the generator for KG evaluation.

**Climax:** Marcus runs his KG construction pipeline on all three variants and evaluates against the gold entity graphs. The controlled parameter variation lets him produce clean ablation results showing exactly how entity naming variation degrades his graph quality — with statistical significance across multiple generated corpora using different seeds.

**Resolution:** Marcus publishes a KG construction paper citing CROSSFIRE's generator as evaluation infrastructure. He never runs the auditing pipelines or uses the incoherence labels. The generator served a purpose entirely independent of the benchmark's core task.

---

### Journey 3: Dr. Aisha Okafor — Infrastructure Adopter

**Situation:** Aisha leads a small research group working on multi-hop reasoning for medical literature. She needs synthetic corpora of interconnected clinical reports with known entity relationships — but no such dataset exists for her domain. Building a corpus generator from scratch would take months.

**Opening Scene:** Aisha reads Marcus's paper and traces the generator back to CROSSFIRE. She inspects the codebase and finds the domain abstraction layer — the generator's document templates and entity schemas are separated from the generation logic.

**Rising Action:** Aisha forks CROSSFIRE and replaces the NTSB document templates with clinical report templates (case reports, lab results, radiology findings, discharge summaries). She defines a medical entity schema (patients, conditions, medications, procedures) and maps it to the generator's entity graph structure. The incoherence injection and gold annotation pipelines work without modification — they operate on the abstract entity graph, not the domain-specific text.

**Climax:** Aisha generates a medical multi-source corpus with ground-truth entity graphs and controlled incoherences. Her team uses it to evaluate multi-hop reasoning chains across clinical documents — a task no existing medical NLP benchmark supports.

**Resolution:** Aisha's team publishes with their adapted generator, citing CROSSFIRE as the infrastructure foundation. The generator has now been proven in two domains, validating the domain abstraction design.

---

### Journey 4: Leo Park — Reproducer and Contributor

**Situation:** Leo is a first-year PhD student whose advisor assigned him to reproduce CROSSFIRE's baselines as a way to learn the field. He needs to go from zero to running all reference pipelines and matching published numbers.

**Opening Scene:** Leo clones the repo and follows the quickstart guide. He installs dependencies and finds the pre-generated gold datasets already included — no generation step needed.

**Rising Action:** Leo runs the three reference pipelines (agentic, graph-native, hybrid) on the default preset corpus using the shipped evaluation scripts. He compares his numbers against the published baselines. They match — seeded generation and deterministic evaluation ensure reproducibility.

**Climax:** After reproducing baselines, Leo modifies the hybrid pipeline's entity resolution component with a new approach his advisor suggested. He re-runs evaluation and sees improved inter-subcorpus scores but degraded intra-document scores. The per-stage diagnostic tells him his new entity resolution helps cross-document linking but introduces false matches within documents.

**Resolution:** Leo submits a pull request with his modified pipeline as an additional baseline. He's gone from reproducer to contributor, and the diagnostic evaluation suite made it possible for him to understand his own results well enough to write them up.

---

### Journey Requirements Summary

| Capability | Journeys | Priority |
|---|---|---|
| Pre-generated gold datasets (download and evaluate immediately) | Priya, Leo | MVP |
| Standardized incoherence report format (cross-pipeline comparison) | Priya, Leo | MVP |
| Diagnostic evaluation scripts (per-stage, per-scope) | Priya, Marcus, Leo | MVP |
| Generator with parameterized corpus generation | Marcus, Aisha | MVP |
| Seeded generation for reproducibility | Marcus, Leo | MVP |
| Gold entity graph output (independent of incoherence labels) | Marcus, Aisha | MVP |
| Reference pipeline implementations (runnable baselines) | Priya, Leo | MVP |
| Domain abstraction layer (swappable templates and entity schemas) | Aisha | Growth |
| Quickstart documentation and reproducibility guide | Leo | MVP |
| Contribution guidelines and pipeline extension patterns | Leo | Growth |

## Domain-Specific Requirements

### Reproducibility & Scientific Rigor

- Seeded generation: identical parameters + seed = identical corpus across machines and runs
- Pre-generated gold datasets ship with the code — researchers can evaluate without running generation
- Hypothesis-only baseline experiment validates that contamination shortcuts don't drive performance
- Benchmark versioning: living annotations are version-tracked; gold label corrections trigger new benchmark versions
- Statistical significance: results reported across multiple seeds, not single-run numbers

### Computational Constraints

- Generator LLM API costs: ~$5-20 per subcorpus at default scale with GPT-4o-mini
- Scale ceiling: up to 10K docs / 100K chunks; dimension reduction for larger corpora is external preprocessing
- Reference pipelines must run on academic-grade hardware (single GPU or CPU-only with API calls)
- Default corpus (~400 docs, 5 subcorpora x ~80 docs) stays within GraphRAG practical limits (~1K-10K chunks)

### Contamination Prevention

- Minimal-pair construction: change only the target fact, not surrounding prose
- Same LLM temperature/prompt for both original and modified text to prevent stylistic tells
- Multi-model generation to avoid style fingerprinting
- Canary facts and adversarial filtering planned for v2

### Annotation Policy

- When ambiguous, label as contradiction — assumes human reviewer deconflicts in practice
- Gold entity graph requires its own validation step before release
- Distractor labels (legitimate perspective divergences) included to measure false positive rates

## Innovation & Novel Patterns

### Detected Innovation Areas

**Novel Task Definition — Unsupervised Corpus-Level Coherence Auditing:**
No existing benchmark evaluates the task of autonomously scanning a multi-source document corpus for factual incoherences without queries, hints, or human guidance. CLAIRE/WikiCollide introduced corpus-level inconsistency detection but as per-fact binary classification on clean Wikipedia articles. CROSSFIRE defines and benchmarks the fully unsupervised version: corpus in, incoherence list out. This is a new evaluation paradigm.

**Configurable Benchmark Generator:**
The shift from fixed dataset to parameterized corpus generator is methodologically novel in this problem space. The generator's 4D incoherence design space (scope x mechanism x detectability x system affinity) enables controlled experimentation across a parameter space no existing benchmark offers. Researchers generate corpora at specific configurations rather than working with static evaluation sets.

**System Affinity as a Design Axis:**
Incoherences are deliberately engineered to structurally favor specific architecture families. The connectivity-hop distance asymmetry — where GraphRAG and Multi-Hop RAG face different difficulty parameters that don't always correlate — means the benchmark reveals *when each approach wins* rather than producing a single leaderboard ranking. This is a novel approach to benchmark design that prioritizes diagnostic insight over competition.

### Market Context & Competitive Landscape

- **CLAIRE/WikiCollide** (Stanford, EMNLP 2025): Closest prior work. Wikipedia-only, fixed 955-fact dataset, no graph evaluation, per-fact classification. CROSSFIRE addresses every gap in CLAIRE's stated limitations.
- **WikiContradict** (IBM, NeurIPS 2024): 253 inter-context conflict instances. Tests LLM behavior, not autonomous auditing.
- **ContraDoc** (NAACL 2024): 449 intra-document contradictions only. Misses cross-document scope entirely.
- **FEVER/FEVEROUS/HoVer**: Query-driven, assume corpus consistency. CROSSFIRE challenges this assumption.
- **GraphRAG-Bench** (ICLR 2026): Evaluates GraphRAG on QA accuracy, not consistency auditing.
- Configurable benchmark generators are an emerging paradigm (LiveBench, BenchmarkDataNLP.jl) but none target this task.

### Validation Approach

- Hypothesis-only baseline proves contamination shortcuts don't drive performance
- Multiple seeds + statistical significance across generated corpora validate generator reliability
- Architecture-dependent performance patterns confirm the system affinity axis produces meaningful differentiation (if all architectures perform identically, the axis fails)
- Graph-native family treated as hypothesis under test — dropping it if experimentation shows it can't adapt is a valid, publishable outcome

## Developer Tool Specific Requirements

### Project-Type Overview

CROSSFIRE ships as a clone-and-run Python repository, not a pip-installable package. The primary interface is running scripts/commands that produce outputs — not importing a library API. The codebase serves two audiences: researchers reproducing/extending the benchmark, and teams adapting the generator for their own tasks.

### Technical Architecture Considerations

**Delivery model:** Git repository with dependencies managed via `requirements.txt` or `pyproject.toml`. No package registry publication for v1.

**Primary outputs (not API surfaces):**
- **Generator output:** A corpus — documents with metadata, gold entity graph, gold incoherence labels, gold distractor labels. Output format (JSON, JSONL, directory structure) to be determined during implementation.
- **Pipeline output:** An incoherence report in standardized format across all architecture families. Format to be determined during implementation.

**Formal API design deferred.** Whether the generator and pipelines expose a programmatic Python API (importable functions with documented signatures) or are script-driven with file I/O is an implementation decision. The requirement is that outputs are well-defined and consistent — the interface to those outputs is secondary.

**Two-layer evaluation framework:**
- **Layer 1 — Representation quality:** How well does the system's internal knowledge graph capture entities and relationships? Evaluated against the gold entity graph.
- **Layer 2 — Auditing strategy:** Given that representation, how effectively does the system detect contradictions? Evaluated against gold incoherence labels.

These layers are evaluated independently, enabling diagnostic isolation of representation failures vs. reasoning failures.

### Code Examples & Onboarding

- **Pre-generated gold datasets** included in the repo for immediate evaluation without running the generator
- **Reference pipelines** serve as both baselines and usage examples for all three operating modes
- **One Jupyter notebook** demonstrating end-to-end workflow (generate corpus → run pipeline → evaluate results) — optional but useful for onboarding
- **No tutorials, quickstart guides, or additional example scripts beyond the above**

### Documentation Strategy

- **README:** Sufficient for cloning, installing dependencies, running all experiments (generation, pipeline execution, evaluation), and reproducing published baselines
- **Paper:** Detailed methodology, results, and analysis — the authoritative reference for design decisions and experimental findings
- **Code comments:** Where logic isn't self-evident, not exhaustive docstrings
- **No docs site** (ReadTheDocs, GitHub Pages, etc.) for v1

### Implementation Considerations

- Python 3.10+ (standard for current NLP tooling)
- LLM API dependencies: OpenAI API (GPT-4o-mini for generation), potentially others for multi-model generation
- Graph libraries: NetworkX or similar for entity graph construction and manipulation
- Evaluation dependencies: standard scientific Python (numpy, scipy, scikit-learn for metrics)
- Seeded randomness at every level (Python random, numpy, LLM temperature 0 or fixed seed where supported)

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-solving MVP — the minimum that produces a publishable benchmark with meaningful, non-trivial results across architecture families.

**Resource Requirements:** Solo researcher, 6-8 weeks. No external dependencies except LLM API access and public NTSB data.

**Core constraint:** Paper deadline drives all MVP prioritization. Everything in MVP must contribute directly to the submission package. Generator standalone quality (domain abstraction, clean interfaces for reuse) is a Phase 2 concern — the generator must work correctly for NTSB, but doesn't need to be plug-and-play for new domains at launch.

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Priya (benchmark evaluator) — full support
- Leo (reproducer) — full support
- Marcus (custom corpus generator) — partial (NTSB only, no domain abstraction)
- Aisha (infrastructure adopter) — not supported until Phase 2

**Must-Have Capabilities:**

| Capability | Rationale |
|---|---|
| Corpus generator with 3-4 preset configurations | Paper experiments require controlled corpus variants |
| Seeded generation for reproducibility | Scientific rigor; reviewers will check |
| 3-layer gold annotations (entity graph, incoherence labels, distractor labels) | Minimum for diagnostic evaluation |
| Hybrid pipeline with 3 operating modes (graph-native contingent on experimentation) | Architecture comparison is the paper's contribution |
| Diagnostic evaluation suite (per-stage, per-scope, binary + partial credit) | Differentiator vs. WikiCollide |
| Pre-generated gold baseline datasets | Lowers barrier for reproducers; required for credibility |
| Standardized incoherence report format | Fair comparison across pipeline families |
| Hypothesis-only baseline for contamination validation | Reviewers will question synthetic corpus validity |
| README sufficient for reproducing all experiments | Minimum viable documentation |

**Explicitly NOT in MVP:**
- Formal Python API with documented signatures
- Domain abstraction layer
- Entity resolution mappings and retrieval path gold layers
- Query-driven evaluation mode
- Docs site, tutorials, or extensive onboarding materials
- Jupyter notebook (nice-to-have, not blocking)

### Phase 2 — Post-Publication Polish

Camera-ready revisions + open-source adoption preparation:
- Generator refactored for standalone reuse: domain abstraction layer, clean interfaces
- Entity resolution mappings and retrieval path gold layers (v2 annotations)
- Jupyter notebook for end-to-end walkthrough
- Contribution guidelines and pipeline extension patterns
- Camera-ready revisions based on reviewer feedback
- Full generator parameter space documentation

### Phase 3 — Community & Expansion

- Non-NTSB domain templates contributed by community or author
- Query-driven evaluation mode
- Open architecture category beyond initial families
- Living annotations infrastructure (versioned gold label updates)
- Community-maintained benchmark with expanding domain coverage

### Risk Mitigation Strategy

**Technical Risks:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Graph-native approach can't adapt to unsupervised auditing | Medium | Medium | Test early with litmus incoherences; drop to 2 families if needed — still publishable |
| LLM-generated incoherences have stylistic tells | Medium | High | Minimal-pair construction + hypothesis-only baseline in Week 3; if contamination detected, revise generator methodology before full experiments |
| NTSB data too sparse or inconsistent for realistic generation | Low | High | 3-day hard timebox on real data exploration; go fully synthetic informed by structure analysis |
| Evaluation metrics don't differentiate architectures | Medium | High | System affinity litmus test early; if no differentiation, redesign incoherence parameters before full runs |
| Novel task not recognized by reviewers | Low | High | Position explicitly against CLAIRE's stated limitations and future work section |
| System affinity axis shows no differentiation | Medium | Medium | Litmus test with 2-3 designed incoherences early in development; pivot if no signal |

**Resource Risks:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Timeline slips past EMNLP deadline | Medium | High | Build evaluation scripts from Day 1; write paper incrementally; accept reduced preset count (2 instead of 4) if needed |
| LLM API costs exceed budget | Low | Medium | GPT-4o-mini keeps costs low (~$5-20/subcorpus); reduce corpus scale if needed |
| Solo bandwidth insufficient for 3 pipeline modes | Medium | Medium | Hybrid-first implementation with mode switches; if time-constrained, ship 2 modes + analysis of why third was cut |
| No adoption post-publication | Medium | Medium | Pre-generated datasets + reference pipelines lower barrier; Phase 2 focus on standalone generator quality |
| Another group publishes similar benchmark before submission | Low | High | Differentiate on configurability and diagnostic evaluation; fixed datasets can't compete with a generator |

## Functional Requirements

### Corpus Generation

- **FR1:** Researcher can generate a multi-source document corpus in the NTSB/industrial incident domain with configurable parameters (subcorpora count, documents per subcorpus, document type mix)
- **FR2:** Researcher can configure connectivity level between subcorpora (level 0: no shared entities, level 1: identical naming, level 2: paraphrased naming, level 3: dense shared entities)
- **FR3:** Researcher can specify a random seed to produce identical corpora across runs and machines
- **FR4:** Researcher can select from 3-4 preset configurations that reproduce the paper's experimental conditions
- **FR5:** Researcher can generate corpora containing heterogeneous document types (investigation reports, technical analyses, witness testimonies, regulatory filings, press coverage, expert depositions, internal memos, preliminary reports)

### Incoherence Injection

- **FR6:** Researcher can configure incoherence scope distribution (intra-document, intra-subcorpus cross-document, inter-subcorpus)
- **FR7:** Researcher can configure incoherence mechanism (numeric drift, entity swap, causal inversion, temporal contradiction, omission-based implicit, temporal revision conflict)
- **FR8:** Researcher can configure incoherence detectability distribution (single-hop, multi-hop, entity-resolution-dependent)
- **FR9:** Researcher can configure system affinity (balanced, graph-favoring, agentic-favoring)
- **FR10:** Generator produces incoherences using minimal-pair construction (modifying only the target fact, not surrounding prose)
- **FR11:** Generator produces distractor labels (legitimate perspective divergences that should NOT be flagged as incoherences) at a configurable ratio
- **FR12:** Generator uses same LLM temperature and prompt structure for original and modified text to prevent stylistic tells

### Gold Annotation

- **FR13:** Generator produces a gold entity graph capturing all entities and relationships across the corpus
- **FR14:** Generator produces gold incoherence labels identifying every injected incoherence with its scope, mechanism, detectability, and system affinity metadata
- **FR15:** Generator produces gold distractor labels identifying every legitimate divergence
- **FR16:** Gold annotations are versioned — label corrections trigger a new benchmark version identifier

### Auditing Pipelines

- **FR17:** Researcher can run a hybrid auditing pipeline (graph representation + LLM-driven reasoning) against a generated corpus
- **FR18:** Researcher can run an agentic auditing pipeline (claim extraction + cross-checking, graph layer disabled) against a generated corpus
- **FR19:** Researcher can run a graph-native auditing pipeline (KG construction + structural anomaly detection, LLM reasoning disabled) against a generated corpus — contingent on experimental feasibility
- **FR20:** All pipeline modes produce incoherence reports in a standardized output format enabling cross-pipeline comparison
- **FR21:** Researcher can run a hypothesis-only baseline that evaluates whether incoherences are detectable from surface features alone (contamination validation)
- **FR22:** Researcher can run trivial baselines (random, BM25 keyword contradiction) for lower-bound comparison

### Evaluation & Diagnostics

- **FR23:** Researcher can evaluate a pipeline's incoherence report against gold labels using binary (exact match) scoring
- **FR24:** Researcher can evaluate a pipeline's incoherence report against gold labels using partial credit (localization proximity) scoring
- **FR25:** Researcher can view evaluation results broken down per-scope (intra-document, intra-subcorpus, inter-subcorpus) independently
- **FR26:** Researcher can view evaluation results broken down per-stage (entity resolution, graph construction, scanning) independently without cascading failures
- **FR27:** Researcher can evaluate a pipeline's internal knowledge graph against the gold entity graph (Layer 1: representation quality)
- **FR28:** Researcher can measure false positive rate on distractor labels separately from incoherence detection accuracy
- **FR29:** Researcher can run evaluation across multiple seeds and obtain aggregate statistics with significance measures

### Data & Output Management

- **FR30:** Researcher can use pre-generated gold baseline datasets included in the repository without running the generator
- **FR31:** Generator outputs corpus documents with metadata (document type, subcorpus membership, reliability signal)
- **FR32:** All outputs (corpora, annotations, evaluation results) are stored in documented, machine-readable formats
- **FR33:** README provides instructions sufficient to clone the repo, install dependencies, and reproduce all published experimental results

## Non-Functional Requirements

### Reproducibility

- Same seed + same parameters produces bit-identical corpus output across runs, machines, and operating systems
- Evaluation scripts are fully deterministic — identical inputs produce identical scores with no variance
- Pre-generated datasets run through shipped pipelines reproduce published baseline numbers exactly
- All sources of randomness (Python random, numpy, LLM generation) are seeded and documented

### Correctness

- Gold annotations are verifiably correct — every injected incoherence is labeled, no false labels exist in shipped datasets
- Evaluation scoring is mathematically correct against gold labels — no off-by-one errors, no input/label misalignment
- Minimal-pair construction does not introduce unintended secondary incoherences beyond the target modification
- Gold entity graph accurately represents all entities and relationships present in the generated corpus

### Portability

- Runs on Linux and macOS without platform-specific dependencies
- No GPU requirement for corpus generation or evaluation (LLM calls are API-based)
- Reference pipelines executable on academic-grade hardware (consumer GPU or CPU-only with API calls)
- Python 3.10+ with standard scientific Python ecosystem (no exotic or platform-locked dependencies)

### Cost Predictability

- Generation cost per subcorpus is estimable before execution (~$5-20 with GPT-4o-mini at default scale)
- Generation fails gracefully on API errors with clear reporting — no silent retries that accumulate charges
- Dry-run or cost estimation mode available before committing to full generation
