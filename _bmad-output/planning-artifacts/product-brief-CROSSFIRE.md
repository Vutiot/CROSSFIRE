---
title: "Product Brief: CROSSFIRE"
status: "complete"
created: "2026-04-05"
updated: "2026-04-05"
inputs:
  - "_bmad-output/brainstorming/brainstorming-session-2026-04-05-001.md"
  - "docs/2509.23233v1.pdf (CLAIRE/WikiCollide, Stanford, Sep 2025)"
  - "github.com/stanford-oval/inconsistency-detection"
---

# Product Brief: CROSSFIRE

**Cross-corpus Fact Incoherence Reasoning Evaluation**

## Executive Summary

Large document corpora -- investigation reports, technical analyses, witness testimonies, regulatory filings -- inevitably accumulate factual contradictions. A date shifts between documents. An attribution changes. A causal chain quietly inverts. In domains like aviation safety, where the NTSB investigates incidents that cost lives, undetected contradictions between reports, testimonies, and technical analyses are not academic curiosities -- they are failure modes with real-world consequences.

Today, no general-purpose NLP benchmark evaluates the task of autonomously detecting these incoherences across heterogeneous document corpora. Existing approaches either require someone to ask the right question first (fact verification), or operate only on clean, structured sources like Wikipedia (CLAIRE/WikiCollide).

CROSSFIRE is a configurable benchmark generator that defines and evaluates the task of **unsupervised corpus-level coherence auditing**: given a multi-source document corpus, detect all factual incoherences without queries, hints, or human guidance. It benchmarks three architecture families -- graph-native, LLM-agentic, and hybrid -- across a controlled parameter space, with diagnostic evaluation at every pipeline stage. Beyond the benchmark itself, the generator serves as **standalone research infrastructure** -- teams working on entity resolution, knowledge graph construction, or multi-hop reasoning can use it to produce synthetic corpora with ground truth for their own tasks.

CROSSFIRE ships as an open-source tool alongside a peer-reviewed publication targeting EMNLP.

The timing is right. Stanford's CLAIRE/WikiCollide (EMNLP 2025) just established corpus-level inconsistency detection as a recognized research task, but left critical gaps that its own limitations section acknowledges: Wikipedia-only, no exploration of technical texts (academic, medical, legal), fixed dataset, no graph-based evaluation, no diagnostic metrics. GraphRAG systems are maturing rapidly but lack benchmarks that test cross-document reasoning rather than QA accuracy. CROSSFIRE fills both gaps simultaneously.

## The Problem

Fact verification research has operated under a foundational assumption: the reference corpus is internally consistent. FEVER, FEVEROUS, HoVer -- all assume that if you find supporting evidence in the corpus, the claim is verified. But CLAIRE demonstrated that at least 3.3% of English Wikipedia facts contradict another fact in the corpus, propagating into 7.3% of FEVEROUS "Supports" labels. The assumption is broken.

Meanwhile, practitioners deploying GraphRAG and multi-hop RAG systems in enterprise settings encounter multi-source contradictions daily -- conflicting reports, inconsistent records, contradictory testimony. A 2025 study showed GPT-4 and LLaMA-3 perform barely above random guessing at detecting contradictions in retrieved contexts.

The research community lacks three things:
1. **A benchmark for unsupervised corpus auditing on heterogeneous corpora** -- CLAIRE evaluates inconsistency detection on clean Wikipedia articles; no existing benchmark tests the ability to proactively scan a corpus of diverse, unstructured document types for contradictions without being told where to look
2. **A principled comparison of architectural approaches** -- no benchmark evaluates graph-native, agentic, and hybrid systems on the same task under the same conditions
3. **Diagnostic evaluation** -- existing benchmarks produce a single accuracy number; researchers cannot pinpoint where their pipeline fails (entity resolution? graph construction? reasoning?)

## The Solution

CROSSFIRE is a **configurable benchmark generator** that produces document corpora with controlled incoherences, rich gold annotations, and diagnostic evaluation tools.

**The task:** Corpus in, incoherence list out. No queries. Fully unsupervised.

**The corpus:** Multi-source documents from the NTSB/industrial incident investigation domain -- a domain where corpus incoherence has caused real-world harm. Investigation reports, technical analyses, witness testimonies, regulatory filings, and press coverage are organized into interconnected subcorpora sharing entities (companies, equipment, regulators, locations) across incident boundaries. This heterogeneous, multi-voice structure mirrors the real-world document environments where coherence auditing matters most.

**The generator** takes parameters and produces evaluation-ready corpora:
- Subcorpora count, documents per subcorpus, document type mix
- Cross-subcorpus connectivity level (none to dense, with entity naming variation)
- Incoherence configuration: scope (intra-doc / cross-doc / inter-subcorpus), mechanism (numeric drift, entity swap, causal inversion, temporal contradiction, omission-based), detectability (single-hop / multi-hop / entity-resolution-dependent), and system affinity (favoring graph-native vs agentic approaches)

**The generator as standalone infrastructure:** Beyond its role in the CROSSFIRE benchmark, the generator produces synthetic multi-source corpora with ground-truth entity graphs and controlled incoherences. This makes it independently useful for research on entity resolution, knowledge graph construction, multi-hop reasoning, and any task requiring annotated heterogeneous document collections.

**Gold annotations at 3 levels (v1):** entity graph, incoherence labels, and distractor labels (legitimate perspective divergences that should NOT be flagged). Entity resolution mappings and retrieval paths are planned for v2.

**Three architecture families benchmarked:**
1. **Graph-native** -- KG construction + structural consistency detection
2. **LLM-agentic** -- claim extraction + cross-checking (CLAIRE-style)
3. **Hybrid** -- graph representation + LLM-driven reasoning

Reference pipelines ship for each family, lowering the barrier to entry.

## What Makes This Different

| | WikiCollide | FEVER family | CROSSFIRE |
|---|---|---|---|
| **Task** | Per-fact inconsistency classification | Query-driven fact verification | Unsupervised corpus audit |
| **Corpus** | Clean Wikipedia articles | Curated claims + evidence | Unstructured multi-source documents |
| **Dataset** | Fixed (955 facts) | Fixed | Configurable generator |
| **Evaluation** | AUROC on binary classification | Accuracy/F1 on claim labels | Diagnostic per-stage, per-scope, binary + partial |
| **Graph evaluation** | None | None | Explicit (entity resolution, graph quality, reasoning) |
| **Architecture comparison** | Single system type | Single system type | Three families head-to-head |

**The core insight:** GraphRAG community detection (Leiden/Louvain) will likely separate subcorpora into distinct communities, burying cross-subcorpus shared entities at community boundaries. CROSSFIRE is designed to expose this specific capability gap and measure when graph-native, agentic, or hybrid approaches each win.

## Who This Serves

**Primary: NLP/IR researchers** evaluating retrieval-augmented systems, knowledge graph construction, or fact verification approaches. They need a benchmark that tests real-world coherence reasoning on heterogeneous documents, not just QA accuracy on clean data.

**Secondary: GraphRAG practitioners** in enterprise settings who need to understand when graph-based approaches justify their complexity over simpler vector retrieval for multi-source consistency tasks.

## Success Criteria

**Research impact:**
- Accepted at a top NLP venue (EMNLP target)
- Adopted as an evaluation benchmark by external research groups
- Cited as a reference for the unsupervised corpus auditing task

**Technical milestones:**
- Generator produces valid, contamination-resistant corpora across preset configurations
- Gold annotations pass validation (cross-checked, versioned)
- All three reference pipelines produce meaningful (non-trivial, non-ceiling) results -- establishing that the task is hard but tractable
- Results reveal architecture-dependent performance patterns across the evaluation matrix

**Open-source adoption:**
- Clean, documented codebase with reproducible results
- Pre-generated gold datasets for immediate use without running the generator
- Generator adopted independently by teams working on entity resolution, KG construction, or multi-hop reasoning

## Scope

**In for v1:**
- Configurable corpus generator with NTSB-domain documents (preset configurations for paper, full parameter space documented)
- 3-layer gold annotation pipeline (entity graph, incoherence labels, distractor labels)
- Three reference auditing pipelines built as one hybrid architecture with three operating modes
- Diagnostic evaluation suite (per-stage, per-scope, binary + partial credit)
- Pre-generated gold baseline datasets
- EMNLP-ready paper with baselines, ablations, and error analysis

**Out for v1:**
- Query-driven evaluation mode (future extension)
- Benchmark lite mode (full matrix is the value proposition)
- Open architecture category beyond three families
- Dimension reduction for corpora exceeding 10K docs / 100K chunks
- Domains beyond NTSB/industrial incidents
- Entity resolution mappings and retrieval path gold layers (v2)

## Vision

CROSSFIRE establishes unsupervised corpus-level coherence auditing as a recognized research task, with a rigorous benchmark and open-source tooling that reveals when and why different architectural approaches succeed or fail on heterogeneous, multi-source document corpora.
