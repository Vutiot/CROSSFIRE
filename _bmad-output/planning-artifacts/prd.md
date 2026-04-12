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
  - "step-e-01-discovery"
  - "step-e-02-review"
  - "step-e-03-edit"
inputDocuments:
  - "_bmad-output/planning-artifacts/product-brief-CROSSFIRE.md"
  - "_bmad-output/planning-artifacts/product-brief-CROSSFIRE-distillate.md"
  - "_bmad-output/brainstorming/brainstorming-session-2026-04-05-001.md"
  - "_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-09.md"
  - "_bmad-output/planning-artifacts/architecture.md"
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
lastEdited: '2026-04-11'
editHistory:
  - date: '2026-04-11'
    changes: 'Multi-source generalization — added Grenfell Tower Inquiry (primary) and Chicago COPA OIS (secondary) alongside NTSB'
  - date: '2026-04-10'
    changes: 'Agentic dataset generation pivot — 15 FRs rewritten, 6 NFRs modified, prose updates across Executive Summary, User Journeys, Domain Requirements, Innovation, Developer Tool Requirements, and Project Scoping'
---

# Product Requirements Document - CROSSFIRE

**Author:** Al
**Date:** 2026-04-05

## Executive Summary

CROSSFIRE (Cross-corpus Fact Incoherence Reasoning Evaluation) is a benchmark for unsupervised corpus-level coherence auditing — the task of detecting all factual incoherences in a multi-source document corpus without queries, hints, or human guidance. It targets NLP/IR researchers evaluating retrieval-augmented systems, knowledge graph construction, and fact verification approaches, as well as GraphRAG practitioners who need to understand when graph-based approaches justify their complexity for multi-source consistency tasks.

The project delivers two co-equal outcomes: (1) a benchmark for comparing architectural approaches to corpus auditing (graph-native, LLM-agentic, hybrid), and (2) a standalone research infrastructure — an agentic pipeline that processes real investigation documents from multiple sources through anonymization, claim extraction, and controlled contradiction injection — independently useful for entity resolution, KG construction, and multi-hop reasoning research.

CROSSFIRE ships as open-source tooling alongside a peer-reviewed publication targeting EMNLP. Corpora are derived from real investigation sources — primarily the Grenfell Tower Inquiry (300+ public hearings, 1,600+ witness statements), with the Chicago COPA officer-involved shooting database as a secondary validation corpus and NTSB aviation investigation dockets as a tertiary option. Heterogeneous document types within each source and cross-document shared entities mirror the real-world environments where coherence auditing matters most.

### What Makes This Special

No existing benchmark evaluates unsupervised corpus auditing on heterogeneous, unstructured documents. CLAIRE/WikiCollide (Stanford, EMNLP 2025) established corpus-level inconsistency detection as a research task but operates on clean Wikipedia articles with a fixed 955-fact dataset and no graph-based evaluation. CROSSFIRE addresses every gap CLAIRE's own limitations section acknowledges.

The agentic generation pipeline is the differentiator. Real investigation documents from multiple sources are processed through anonymization, claim extraction, and contradiction injection via Claude Code CLI — producing benchmark corpora grounded in authentic domain structure. Multi-source support demonstrates domain-agnostic applicability: Grenfell's party-based testimony threads (Arconic, Celotex, Kingspan), COPA's per-case forensic files, and NTSB's aviation dockets each present distinct document taxonomies and entity structures, yet the same pipeline processes all of them. Researchers work with versioned datasets shipping tunable injection parameters (contradiction rates, distractor ratios, mechanism/difficulty distributions) rather than a static evaluation set. Pre-generated gold datasets ship for reproducibility; the pipeline ships for extensibility. This dual delivery is what gives the project legs beyond a single publication.

The architectural comparison is empirical, not ideological. Three families start as the experimental setup (graph-native via KG construction, LLM-agentic via claim extraction, hybrid combining both), implemented as one architecture with three operating modes. If the benchmark reveals that graph-native approaches can't be adapted to this task, that's a valid finding — the benchmark scopes down and the result still publishes.

### Core Architectural Insight

Real investigation sources contain natural domain boundaries that challenge graph-based approaches differently. The Grenfell Tower Inquiry is the primary example: hearing transcripts, witness statements, and expert reports are organized around parties (Arconic, Celotex, Kingspan, RBKC TMO, London Fire Brigade) whose testimony threads overlap on shared factual claims about cladding product safety knowledge, fire spread timelines, and regulatory compliance. GraphRAG community detection (Leiden/Louvain) will likely cluster documents by party or document type, placing cross-party shared entities — the "who knew what when" about combustible cladding — at community boundaries where they are least visible to both global search (which summarizes per-community) and local search (which stays local). COPA case files present a different boundary structure: forensic shooting reconstruction reports, tactical response reports, body-worn camera descriptions, and 911 call logs within a single case each describe overlapping events from different vantage points. NTSB dockets similarly span operations, meteorology, ATC, and witness domains. CROSSFIRE exposes these capability gaps using authentic domain structure from multiple sources — measuring when graph-native, agentic, or hybrid approaches each win at detecting contradictions that span natural document boundaries.

## Project Classification

- **Project Type:** Developer tool — research library/CLI for benchmark generation and evaluation
- **Domain:** Scientific research — NLP benchmarking with reproducibility, validation, and peer review requirements
- **Complexity:** Medium — no regulatory compliance, but high rigor around reproducibility, contamination prevention, and annotation validation
- **Project Context:** Greenfield

## Success Criteria

### User Success

- **Time-to-evaluation:** A researcher evaluates against shipped dataset versions immediately, or runs the agentic pipeline on new source documents (Grenfell transcripts, COPA case files, NTSB dockets, or other configured sources), without needing to understand pipeline internals.
- **Diagnostic clarity:** A researcher compares their system against reference pipelines and immediately identifies which pipeline stage fails — entity resolution, graph construction, or reasoning — rather than staring at a single accuracy number.
- **Reproducibility:** Any researcher can reproduce published baselines by running versioned gold datasets through shipped evaluation scripts with identical results.
- **Extensibility moment:** A team working on entity resolution or KG construction adapts the generator to produce corpora for their own task, without touching the auditing or evaluation components.

### Business Success

- **Research impact:** Accepted at a top NLP venue (EMNLP target). Cited as a reference for unsupervised corpus auditing.
- **Benchmark adoption:** External research groups evaluate their systems on CROSSFIRE within 12 months of publication.
- **Generator adoption (co-equal metric):** Teams independently adapt the generator to new corpus domains or use it for non-coherence-auditing tasks (entity resolution, KG construction, multi-hop reasoning). This is 50% of project success — the generator outliving the benchmark paper.
- **Open-source traction:** Clean, documented codebase. Versioned gold datasets for immediate use. Community contributions or forks within the first year.

### Technical Success

- **Generator validity:** Produces diff-verified gold labels across all dataset versions. Hypothesis-only baseline confirms shortcuts aren't driving performance.
- **Annotation quality:** Gold annotations pass cross-validation. Living annotations with benchmark versioning.
- **Meaningful baselines:** All reference pipelines produce non-trivial, non-ceiling results — establishing the task as hard but tractable.
- **Architecture-dependent patterns:** Results reveal when and why different approaches succeed or fail across the evaluation matrix (connectivity x semantic proximity x detectability).

### Measurable Outcomes

| Metric | Target | Timeframe |
|---|---|---|
| EMNLP submission | Paper submitted with baselines + ablations | 6-8 weeks |
| Reference pipeline results | Non-trivial for all families tested | Before submission |
| Versioned gold datasets | Shipped alongside code at publication | At release |
| Generator standalone reuse | At least 1 external team adapts to new domain | 12 months post-publication |
| Diagnostic evaluation | Per-stage scores differentiate pipeline failure modes | At release |

## User Journeys

### Journey 1: Dr. Priya Mehta — Benchmark Evaluator

**Situation:** Priya is a postdoc at a European NLP lab. Her team built a multi-hop RAG system for legal document analysis and needs to demonstrate it handles cross-document contradictions — a claim they make in their paper draft but can't back up because no benchmark tests this capability.

**Opening Scene:** Priya finds CROSSFIRE through a citation in the CLAIRE paper. She clones the repo and sees versioned gold datasets ready to use. She doesn't need to run the generation pipeline — she just needs evaluation-ready corpora with ground truth.

**Rising Action:** She loads a shipped dataset version containing Grenfell Tower Inquiry cases with balanced incoherences and runs her system against it. She adapts her pipeline's output to CROSSFIRE's standardized contradiction report format. She runs the evaluation scripts and gets back per-stage, per-scope diagnostic scores — not a single number, but a breakdown showing her system's claim extraction is strong but inter-document detection collapses across heterogeneous document types.

**Climax:** The diagnostic breakdown shows her system scores well on intra-document incoherences (where semantic similarity drives retrieval) but fails on inter-document cases requiring entity resolution across different document types (e.g., linking claims between hearing transcripts and witness statements in the Grenfell corpus). She can now say exactly *where* her pipeline breaks and *why* — something no other benchmark offered.

**Resolution:** Priya adds a CROSSFIRE evaluation section to her paper, showing per-scope results that honestly characterize her system's strengths and limitations. The diagnostic granularity makes the evaluation section more compelling than a single AUROC number on WikiCollide.

---

### Journey 2: Marcus Chen — Custom Corpus Researcher

**Situation:** Marcus is a PhD student studying how knowledge graph construction degrades when documents use inconsistent entity naming across heterogeneous report types. He needs corpora with authentic cross-document entity variation and ground truth for evaluation.

**Opening Scene:** Marcus discovers CROSSFIRE's versioned datasets contain real investigation documents from multiple sources — Grenfell Tower Inquiry transcripts and witness statements, COPA forensic case files, NTSB dockets — each with naturally heterogeneous document types referencing shared entities with domain-specific naming conventions. This authentic variation is exactly the controlled experimental setup he needs.

**Rising Action:** Marcus evaluates across multiple CROSSFIRE dataset versions with different injection parameters. Each dataset ships with extracted claim triples and cross-references as intermediate artifacts. He doesn't care about the contradiction detection task — he's using the pipeline's claim extraction and the dataset's entity structure for KG evaluation.

**Climax:** Marcus runs his KG construction pipeline on cases of varying complexity and evaluates against the injection-derived gold claims and cross-references. The authentic domain variation lets him produce results showing exactly how cross-document entity naming degrades his graph quality — with statistical significance across dataset versions and cases.

**Resolution:** Marcus publishes a KG construction paper citing CROSSFIRE's datasets and pipeline infrastructure. He never runs the contradiction detection evaluation. The infrastructure served a purpose entirely independent of the benchmark's core task.

---

### Journey 3: Dr. Aisha Okafor — Infrastructure Adopter

**Situation:** Aisha leads a small research group working on multi-hop reasoning for medical literature. She needs corpora of interconnected clinical reports with known entity relationships and controlled contradictions — but no such dataset exists for her domain. Building an agentic generation pipeline from scratch would take months.

**Opening Scene:** Aisha reads Marcus's paper and traces the pipeline back to CROSSFIRE. She inspects the codebase and finds the generation toolchain — the agentic pipeline's plan document and verification utilities are separated from the evaluation infrastructure.

**Rising Action:** Aisha forks CROSSFIRE and adapts the agent plan document for clinical report processing (case reports, lab results, radiology findings, discharge summaries). She defines a medical entity schema (patients, conditions, medications, procedures) and updates the domain registry. The contradiction injection approach (agentic with diff verification) and evaluation pipeline work without modification — they operate on anonymized text documents regardless of domain.

**Climax:** Aisha processes her clinical document corpus through the adapted pipeline, producing anonymized reports with diff-verified contradiction labels. Her team uses it to evaluate multi-hop reasoning chains across clinical documents — a task no existing medical NLP benchmark supports.

**Resolution:** Aisha's team publishes with their adapted generator, citing CROSSFIRE as the infrastructure foundation. The generator has now been proven in two domains, validating the domain abstraction design.

---

### Journey 4: Leo Park — Reproducer and Contributor

**Situation:** Leo is a first-year PhD student whose advisor assigned him to reproduce CROSSFIRE's baselines as a way to learn the field. He needs to go from zero to running all reference pipelines and matching published numbers.

**Opening Scene:** Leo clones the repo and follows the quickstart guide. He installs dependencies and finds the versioned gold datasets already included — no generation step needed.

**Rising Action:** Leo runs the three reference pipelines (agentic, graph-native, hybrid) on the default dataset version using the shipped evaluation scripts. He compares his numbers against the published baselines. They match — frozen datasets and deterministic evaluation ensure reproducibility.

**Climax:** After reproducing baselines, Leo modifies the hybrid pipeline's entity resolution component with a new approach his advisor suggested. He re-runs evaluation and sees improved inter-document scores but degraded intra-document scores. The per-stage diagnostic tells him his new entity resolution helps cross-document linking but introduces false matches within documents.

**Resolution:** Leo submits a pull request with his modified pipeline as an additional baseline. He's gone from reproducer to contributor, and the diagnostic evaluation suite made it possible for him to understand his own results well enough to write them up.

---

### Journey Requirements Summary

| Capability | Journeys | Priority |
|---|---|---|
| Versioned gold datasets (download and evaluate immediately) | Priya, Leo | MVP |
| Standardized contradiction report format (cross-pipeline comparison) | Priya, Leo | MVP |
| Diagnostic evaluation scripts (per-stage, per-scope) | Priya, Marcus, Leo | MVP |
| Agentic generation pipeline with tunable injection parameters | Marcus, Aisha | MVP |
| Deterministic evaluation against frozen datasets | Marcus, Leo | MVP |
| Injection-derived gold claims and cross-references (intermediate KG for transparency) | Marcus, Aisha | MVP |
| Reference pipeline implementations (runnable baselines) | Priya, Leo | MVP |
| Domain abstraction layer (adaptable plan document and entity schemas) | Aisha | Growth |
| Quickstart documentation and reproducibility guide | Leo | MVP |
| Contribution guidelines and pipeline extension patterns | Leo | Growth |

## Domain-Specific Requirements

### Reproducibility & Scientific Rigor

- Deterministic evaluation: same dataset version + same pipeline seed = identical evaluation results across machines and runs. Generation is non-deterministic (agentic execution).
- Versioned gold datasets ship with the code — researchers can evaluate without running generation
- Hypothesis-only baseline experiment validates that contamination shortcuts don't drive performance
- Dataset versioning: each version tracks injection parameters and label corrections via generation_params.json
- Statistical significance: results reported across dataset versions and cases, not single-run numbers

### Computational Constraints

- Generation cost per case uses fan-out architecture: Sonnet for per-chunk claim extraction, Opus for cross-document reasoning (~1/10th cost of full-Opus approach). Cost breakdown logged per phase.
- Reference pipelines must run on academic-grade hardware (single GPU or CPU-only with API calls)
- Dataset scale bounded by source document availability (Grenfell transcripts, COPA records, NTSB dockets) and processing cost per case

### Contamination Prevention

- Minimal-pair construction: change only the target fact, not surrounding prose
- Diff-based verification: mechanical diff between original and modified documents confirms only the target fact changed (±200 char context must be identical). Unintended secondary changes are flagged and rejected.
- Real investigation document prose (from Grenfell, COPA, NTSB, or other sources) reduces contamination risk vs. fully synthetic generation
- Canary facts and adversarial filtering planned for v2

### Annotation Policy

- When ambiguous, label as contradiction — assumes human reviewer deconflicts in practice
- Gold labels are injection-derived and diff-verified. Full knowledge graph ships as intermediate artifact for transparency but is NOT a gold evaluation reference.
- Distractor labels (legitimate perspective divergences) included to measure false positive rates, with per-divergence-type breakdown (expert_opinion, preliminary_vs_final, measurement_methodology, uncertainty_expression)

## Innovation & Novel Patterns

### Detected Innovation Areas

**Novel Task Definition — Unsupervised Corpus-Level Coherence Auditing:**
No existing benchmark evaluates the task of autonomously scanning a multi-source document corpus for factual incoherences without queries, hints, or human guidance. CLAIRE/WikiCollide introduced corpus-level inconsistency detection but as per-fact binary classification on clean Wikipedia articles. CROSSFIRE defines and benchmarks the fully unsupervised version: corpus in, incoherence list out. This is a new evaluation paradigm.

**Agentic Benchmark Pipeline with Versioned Injection:**
The shift from fixed dataset to an agentic pipeline processing real documents with tunable injection parameters is methodologically novel in this problem space. The 4D incoherence design space (scope x mechanism x detectability x system affinity) enables controlled experimentation across a parameter space no existing benchmark offers. Versioned datasets with configurable contradiction rates, distractor ratios, and mechanism distributions replace static evaluation sets.

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
- Diff-based verification + multiple dataset versions validate gold label reliability
- Architecture-dependent performance patterns confirm the system affinity axis produces meaningful differentiation (if all architectures perform identically, the axis fails)
- Graph-native family treated as hypothesis under test — dropping it if experimentation shows it can't adapt is a valid, publishable outcome

## Developer Tool Specific Requirements

### Project-Type Overview

CROSSFIRE ships as a clone-and-run Python repository, not a pip-installable package. The primary interface is running scripts/commands that produce outputs — not importing a library API. The codebase serves two audiences: researchers reproducing/extending the benchmark, and teams adapting the generator for their own tasks.

### Technical Architecture Considerations

**Delivery model:** Git repository with dependencies managed via `requirements.txt`. No package registry publication for v1. Generation toolchain (`generation/` directory) lives outside the Python package (`src/crossfire/`), enforcing a hard boundary between agentic generation and the evaluable pipeline.

**Primary outputs (not API surfaces):**
- **Generation output:** Case directories containing anonymized .txt document files, diff-verified contradiction labels (JSONL), distractor labels (JSONL), intermediate knowledge graph (JSON), and validation logs. Each dataset version ships with `generation_params.json`.
- **Pipeline output:** A contradiction report in standardized JSON format with 2-scope taxonomy (intra_doc, inter_doc), document references, text spans, and confidence.

**Formal API design deferred.** Whether the pipelines expose a programmatic Python API or are script-driven with file I/O is an implementation decision. Generation is CLI-driven by design (Claude Code CLI sessions). The requirement is that outputs are well-defined and consistent — the interface to those outputs is secondary.

**Two-layer evaluation framework:**
- **Layer 1 — Representation quality:** How well does the system's internal representation capture injection-targeted claims and cross-references? Evaluated against injection-derived gold only — NOT the full generation-time knowledge graph.
- **Layer 2 — Auditing strategy:** Given that representation, how effectively does the system detect contradictions? Evaluated against gold contradiction labels.

These layers are evaluated independently, enabling diagnostic isolation of representation failures vs. reasoning failures.

### Code Examples & Onboarding

- **Versioned gold datasets** included in the repo for immediate evaluation without running the generation pipeline
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
- Generation dependency: Claude Code CLI with access to Sonnet (per-chunk extraction) and Opus (cross-document reasoning) models — fan-out architecture
- LLM API dependencies for auditing pipelines: model-agnostic (OpenAI, Anthropic, or others)
- Graph libraries: NetworkX or similar for entity graph construction and manipulation in auditing pipelines
- Evaluation dependencies: standard scientific Python (numpy, scipy, scikit-learn for metrics)
- Seeded randomness in evaluation and pipeline execution only — generation is non-deterministic (agentic execution)

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-solving MVP — the minimum that produces a publishable benchmark with meaningful, non-trivial results across architecture families.

**Resource Requirements:** Solo researcher, 6-8 weeks. No external dependencies except LLM API access and public investigation data (Grenfell Tower Inquiry transcripts, COPA records, NTSB dockets).

**Core constraint:** Paper deadline drives all MVP prioritization. Everything in MVP must contribute directly to the submission package. Generator standalone quality (domain abstraction, clean interfaces for reuse) is a Phase 2 concern — the generator must work correctly for all three configured sources (Grenfell, COPA, NTSB) via pluggable source adapters, but doesn't need to be plug-and-play for entirely new domains at launch.

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Priya (benchmark evaluator) — full support
- Leo (reproducer) — full support
- Marcus (custom corpus generator) — partial (Grenfell/COPA/NTSB sources, no arbitrary domain abstraction)
- Aisha (infrastructure adopter) — not supported until Phase 2

**Must-Have Capabilities:**

| Capability | Rationale |
|---|---|
| Agentic generation pipeline with versioned injection parameters | Paper experiments require controlled corpus variants with tunable rates |
| Deterministic evaluation against frozen, versioned datasets | Scientific rigor; reviewers will check |
| Injection-derived gold annotations (contradiction labels, distractor labels, intermediate KG for transparency) | Minimum for diagnostic evaluation |
| Hybrid pipeline with 3 operating modes (graph-native contingent on experimentation) | Architecture comparison is the paper's contribution |
| Diagnostic evaluation suite (per-stage, per-scope, binary + partial credit) | Differentiator vs. WikiCollide |
| Versioned gold datasets with diff-verified labels | Lowers barrier for reproducers; required for credibility |
| Standardized contradiction report format with 2-scope taxonomy | Fair comparison across pipeline families |
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
- Generation pipeline refactored for standalone reuse: domain abstraction in plan document, clean interfaces for new document domains
- Entity resolution mappings and retrieval path gold layers (v2 annotations)
- Jupyter notebook for end-to-end walkthrough
- Contribution guidelines and pipeline extension patterns
- Camera-ready revisions based on reviewer feedback
- Full generator parameter space documentation

### Phase 3 — Community & Expansion

- Additional source adapters and domain plan documents contributed by community or author
- Query-driven evaluation mode
- Open architecture category beyond initial families
- Living annotations infrastructure (versioned gold label updates)
- Community-maintained benchmark with expanding domain coverage

### Risk Mitigation Strategy

**Technical Risks:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Graph-native approach can't adapt to unsupervised auditing | Medium | Medium | Test early with litmus incoherences; drop to 2 families if needed — still publishable |
| LLM-generated incoherences have stylistic tells | Medium | High | Diff-based verification (±200 char context must be identical) + hypothesis-only baseline; if contamination detected, tighten diff thresholds or revise injection methodology |
| Source data too sparse or inconsistent for realistic generation | Low | High | 3-day hard timebox per source on real data exploration; three sources provide fallback — if one source underperforms, others compensate |
| Evaluation metrics don't differentiate architectures | Medium | High | System affinity litmus test early; if no differentiation, redesign incoherence parameters before full runs |
| Novel task not recognized by reviewers | Low | High | Position explicitly against CLAIRE's stated limitations and future work section |
| System affinity axis shows no differentiation | Medium | Medium | Litmus test with 2-3 designed incoherences early in development; pivot if no signal |

**Resource Risks:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Timeline slips past EMNLP deadline | Medium | High | Build evaluation scripts from Day 1; write paper incrementally; accept reduced dataset version count if needed |
| LLM API costs exceed budget | Low | Medium | Fan-out architecture with Sonnet keeps per-chunk costs low; Opus only for cross-doc reasoning (~1/10th full-Opus cost) |
| Solo bandwidth insufficient for 3 pipeline modes | Medium | Medium | Hybrid-first implementation with mode switches; if time-constrained, ship 2 modes + analysis of why third was cut |
| No adoption post-publication | Medium | Medium | Pre-generated datasets + reference pipelines lower barrier; Phase 2 focus on standalone generator quality |
| Another group publishes similar benchmark before submission | Low | High | Differentiate on configurability and diagnostic evaluation; fixed datasets can't compete with a generator |

## Functional Requirements

### Corpus Processing

- **FR1:** Researcher can process real investigation source documents (Grenfell Tower Inquiry transcripts, COPA case files, NTSB dockets, or other configured sources) through an agentic pipeline that anonymizes, reformats, extracts claims, and injects contradictions
- **FR3:** Researcher can reproduce evaluation results deterministically against shipped dataset versions
- **FR4:** Researcher can select from versioned datasets with different injection parameters (contradiction rates, distractor ratios, mechanism distributions)
- **FR5:** Corpus contains heterogeneous document types as defined by each source's document taxonomy — Grenfell: hearing transcripts, witness statements, expert reports, Phase 1/Phase 2 report sections; COPA: forensic shooting reconstructions, tactical response reports, body-worn camera descriptions, 911 call logs; NTSB: operations group reports, meteorology reports, witness testimonies, ATC transcripts, maintenance records, structures/powerplants analyses

### Incoherence Injection

- **FR6:** Researcher can configure incoherence scope distribution (intra-document, inter-document)
- **FR7:** Researcher can configure incoherence mechanism (numeric drift, entity swap, causal inversion, temporal contradiction, omission-based implicit, temporal revision conflict)
- **FR8:** Researcher can configure incoherence detectability distribution (single-hop, multi-hop, entity-resolution-dependent)
- **FR9:** Researcher can configure system affinity (balanced, graph-favoring, agentic-favoring)
- **FR10:** Generator produces incoherences using minimal-pair modification, verified by mechanical diff between original and modified documents to confirm only the target fact changed
- **FR11:** Generator produces distractor labels (legitimate perspective divergences that should NOT be flagged as incoherences) at a configurable ratio
- **FR12:** Diff-based validation confirms no stylistic contamination — surrounding context (±200 chars) must be identical between original and modified documents

### Gold Annotation

- **FR13:** Generator produces a knowledge graph of factual claim triples with cross-references as an intermediate artifact. Ships for transparency and reproducibility but is NOT used as gold evaluation reference. Gold references are injection-derived only.
- **FR14:** Generator produces gold contradiction labels verified by mechanical diff, including: scope, mechanism, detectability, system affinity, difficulty, char_start/char_end offsets, original and contradicted text, rationale, and ground_truth indicator
- **FR15:** Generator produces gold distractor labels identifying every legitimate divergence
- **FR16:** Dataset versions track both label corrections and injection parameter changes (contradiction rates, distractor ratios, mechanism/difficulty distributions). Each version ships with generation_params.json documenting all parameters.

### Auditing Pipelines

- **FR17:** Researcher can run a hybrid auditing pipeline (graph representation + LLM-driven reasoning) against a dataset case directory containing anonymized document files and metadata
- **FR18:** Researcher can run an agentic auditing pipeline (claim extraction + cross-checking, graph layer disabled) against a dataset case directory
- **FR19:** Researcher can run a graph-native auditing pipeline (KG construction + structural anomaly detection, LLM reasoning disabled) against a dataset case directory — contingent on experimental feasibility. Pipeline's internal KG is evaluated against injection-derived gold claims, not full knowledge graph.
- **FR20:** All pipeline modes produce contradiction reports in a standardized format with 2-scope taxonomy (intra_doc, inter_doc), document references, text spans, and confidence
- **FR21:** Researcher can run a hypothesis-only baseline that evaluates whether incoherences are detectable from surface features alone (contamination validation)
- **FR22:** Researcher can run trivial baselines (random, BM25 keyword contradiction) for lower-bound comparison

### Evaluation & Diagnostics

- **FR23:** Researcher can evaluate a pipeline's contradiction report against gold labels using binary scoring with character-span IoU matching (threshold-configurable)
- **FR24:** Researcher can evaluate using tiered partial credit: precise span match (1.0), approximate span (0.7), correct section (0.4), correct documents only (0.2)
- **FR25:** Researcher can view evaluation results broken down per-scope (intra-document, inter-document) independently
- **FR26:** Researcher can view evaluation results broken down per-stage (claim extraction, cross-reference identification, contradiction detection) independently, evaluated against injection-derived gold references only. Stages do not cascade.
- **FR27:** Researcher can evaluate a pipeline's internal representation against injection-targeted gold claims and cross-references — not against the full generation-time knowledge graph
- **FR28:** Researcher can measure false positive rate on distractor labels, with per-divergence-type breakdown
- **FR29:** Researcher can aggregate evaluation results across dataset versions and cases, with significance measures for cross-pipeline comparison

### Data & Output Management

- **FR30:** Versioned gold datasets ship with the repository. Each version contains processed cases with anonymized documents, diff-verified contradiction labels, distractor labels, and generation_params.json.
- **FR31:** Each document includes metadata: source_id (grenfell, copa, ntsb), source-specific document type, source case ID, and document classification per scope_map
- **FR32:** All outputs (corpora, annotations, evaluation results) are stored in documented, machine-readable formats
- **FR33:** README provides instructions to: install dependencies, evaluate shipped datasets with auditing pipelines, reproduce published baseline results, and (optionally) run the agentic generation pipeline on new source documents with multi-source support (Grenfell, COPA, NTSB)

## Non-Functional Requirements

### Reproducibility

- Shipped datasets are frozen, versioned artifacts. Evaluation against shipped datasets produces identical results across runs and machines. Generation is non-deterministic (agentic execution).
- Evaluation scripts are fully deterministic — identical inputs produce identical scores with no variance
- Pre-generated datasets run through shipped pipelines reproduce published baseline numbers exactly
- All sources of randomness in evaluation and auditing pipelines are seeded and documented. Generation randomness is inherent to agentic execution.

### Correctness

- Gold contradiction labels are mechanically verified via diff between original and modified documents. No self-reported labels without diff confirmation.
- Evaluation scoring is mathematically correct against gold labels — no off-by-one errors, no input/label misalignment
- Diff-based validation confirms each modification touches only the target fact. Unintended secondary changes are flagged and rejected.
- Gold evaluation references are injection-derived (targeted claims, used cross-references, contradiction labels). Full knowledge graph ships for transparency but is not a gold evaluation reference.

### Portability

- Runs on Linux and macOS without platform-specific dependencies
- No GPU requirement for corpus generation or evaluation (LLM calls are API-based)
- Reference pipelines executable on academic-grade hardware (consumer GPU or CPU-only with API calls)
- Python 3.10+ with standard scientific Python ecosystem (no exotic or platform-locked dependencies)

### Cost Predictability

- Generation cost per case is estimable before execution. Fan-out architecture with cost-efficient model for per-chunk extraction and reasoning-capable model for cross-document analysis. Cost breakdown logged per phase.
- Generation fails gracefully on API errors with clear reporting — no silent retries that accumulate charges
- Dry-run or cost estimation mode available before committing to full generation
