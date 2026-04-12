# CROSSFIRE: NTSB Agentic Processing Plan

## Overview

This plan drives a Claude Code CLI session that processes NTSB (National Transportation Safety Board) aviation investigation docket files. The source corpus contains factual reports, group chair reports, technical analyses, witness interviews, party submissions, maintenance records, ATC transcripts, and preliminary/final reports organized under `corpus/ntsb/{case_id}/`.

**Objective:** For each case, anonymize all identifying information, preserve authentic NTSB document structure, extract factual claim triples from every chunk, and assemble a cross-document knowledge graph with entity resolution.

### NTSB Document Types

The corpus classifier recognizes 9 NTSB document types:

| Document Type | Content Focus |
|---|---|
| `ops_group_report` | Crew qualifications, decisions, SOPs, dispatch, flight planning |
| `structures_analysis` | Wreckage distribution, fracture analysis, structural failure |
| `powerplants_analysis` | Engine teardown, fuel system, propeller/rotor |
| `meteorology_report` | Weather observations, forecasts, METAR/TAF, PIREPs |
| `maintenance_record` | Logbooks, ADs, service bulletins, inspection history |
| `atc_transcript` | Communications, radar returns, timestamps |
| `witness_testimony` | Q&A testimony, sensory observations |
| `preliminary_report` | Initial public summary, limited facts, hearing logistics |
| `investigation_report` | Catch-all: final report, party submissions, other documents |

---

## Phase 1: Anonymization (Model: claude-sonnet-4-20250514)

Read every document in the case directory. Apply the following entity replacement rules to anonymize identifying information while preserving technical facts.

### Entity Replacement Rules

| Entity Type | Replacement Strategy | Example |
|---|---|---|
| Tail numbers (N-numbers) | Generic N-number identifier | `N72EX` -> `N-XXXX` |
| Airline / operator names | Sequential generic labels | `Island Express Helicopters` -> `Airline-A`, `Southwest Airlines` -> `Airline-B` |
| Airport identifiers | NATO phonetic alphabet labels | `John Wayne Airport (KSNA)` -> `Airport-Alpha`, `Van Nuys (KVNY)` -> `Airport-Bravo` |
| Personnel names | Role-based identifiers | `John Smith` -> `PIC`, `Jane Doe` -> `FO`, `Bob Wilson` -> `Controller-1` |
| City / location names | Generic regional labels | `Calabasas, CA` -> `Location-1, Region-West` |
| Flight numbers | Synthetic identifiers | `Flight 1282` -> `Flight-ANON-001` |
| Specific dates | Offset by a fixed random delta per case | All dates shifted by same offset to preserve intervals |
| Phone numbers, addresses | Redacted | `[REDACTED]` |

### Preservation Rules

**DO preserve:**
- Technical facts (altitudes, airspeeds, weights, temperatures, pressures)
- Causal relationships and event sequences
- Temporal ordering between events (even if absolute dates are shifted)
- Part numbers and serial numbers
- Regulatory citation numbers (14 CFR Part 135, etc.)
- Aircraft make/model (needed for domain coherence)
- Weather observation values and METAR data
- All measurement units and numeric values
- Aircraft manufacturer names (Boeing, Airbus, Sikorsky)
- Engine manufacturer names (Pratt & Whitney, GE, Rolls-Royce)
- Institutional names (FAA, NTSB, TSB)

**DO NOT preserve / MUST anonymize:**
- Any real person's name
- Any real operator or airline name (except manufacturers)
- Any real airport name or ICAO/IATA code
- Any real registration number

### Cross-Document Entity Variation (Intended Feature)

NTSB documents naturally refer to the same entity differently across reports. For example, one report may call the pilot "the pilot in command" while another says "the captain" and a witness says "the guy flying." **Preserve this natural variation** -- do NOT force all documents to use the same anonymized label for the same entity. This variation is an intended feature for testing entity resolution in downstream evaluation.

However, within each document, maintain internal consistency: if a person is introduced as `PIC` in a document, continue using `PIC` throughout that document.

### Output

Write the anonymization mapping to `metadata/entity_mapping.json` in the case directory.

Format (conforming to `AnonymizationMapping` schema):
```json
[
  {"original": "N72EX", "anonymized": "N-XXXX", "entity_type": "tail_number"},
  {"original": "Island Express Helicopters", "anonymized": "Airline-A", "entity_type": "operator"},
  {"original": "John Wayne Airport", "anonymized": "Airport-Alpha", "entity_type": "airport"}
]
```

---

## Phase 2: Reformatting (Model: claude-sonnet-4-20250514)

Reformat each anonymized document to preserve authentic NTSB document structure. Each document type has specific structural conventions.

### Structure Preservation Rules

**Factual Reports (all group types):**
- NTSB boilerplate header (docket number, exhibit number, case ID)
- Lettered section structure (A. ACCIDENT, B. GROUP, C. SUMMARY, D. DETAILS)
- Terse, declarative sentences. No explanatory clauses.
- Cite regulations by number only. Never explain what a regulation does.
- Use passive voice for findings.
- Use specific measurements with units.

**Witness Testimony Transcripts:**
- Q&A format: `Q: [Investigator question]\nA: [Witness response]`
- Natural speech patterns: hesitations, self-corrections, vague descriptions
- Witnesses do NOT cite regulations fluently
- Include sensory details: what they saw, heard, smelled, felt

**Preliminary Reports:**
- Brief (800-2,000 words). Facts only, no analysis.
- Conditional language: "reportedly", "initial examination indicated"

### Output

Write reformatted documents as `.txt` files in `anonymized_docs/` within the case directory.

```
corpus/ntsb/{case_id}/anonymized_docs/
  ops_group_report.txt
  structures_analysis.txt
  meteorology_report.txt
  witness_testimony_01.txt
  ...
```

---

## Phase 3: Per-Chunk Claim Extraction (Model: claude-sonnet-4-20250514)

This phase uses **fan-out architecture**: process each chunk independently to maximize throughput and minimize per-call cost.

### Input

Read the chunk manifest at `corpus/ntsb/{case_id}/chunks/chunk_manifest.json` to get the list of all chunks and their source document mappings.

### Processing

For each chunk in the manifest:

1. Read the chunk file from `chunks/{chunk_filename}`
2. Extract all atomic factual claims as structured triples
3. Categorize each claim by type

### Claim Triple Format

Each claim is a subject-predicate-object triple conforming to the `KnowledgeGraphClaim` schema:

```json
{
  "claim_id": "OPS_001",
  "subject": "PIC",
  "predicate": "held_certificate",
  "object": "ATP",
  "source_document": "ops_group_report",
  "confidence": 0.95
}
```

### Claim Categories

Categorize each claim into one of:
- **temporal**: dates, times, durations, sequences
- **numeric**: altitudes, speeds, weights, distances, hours
- **personnel**: qualifications, experience, roles
- **meteorological**: weather observations, conditions
- **mechanical**: component states, part numbers, serial numbers, inspection findings
- **procedural**: actions taken, SOPs followed or violated
- **causal**: cause-effect assertions

### Cross-Reference Identification

When a claim references the same fact as a claim in another chunk or document, record it as a cross-reference conforming to the `CrossReference` schema:

```json
{
  "reference_id": "xref_001",
  "source_claim": "OPS_015",
  "target_claim": "MET_003",
  "relationship": "same_event_different_source",
  "source_documents": ["ops_group_report", "meteorology_report"]
}
```

### Output

Write per-document claim files to `original_claims/` within the case directory:

```
corpus/ntsb/{case_id}/original_claims/
  ops_group_report.json
  structures_analysis.json
  meteorology_report.json
  ...
```

Each file contains a JSON array of `KnowledgeGraphClaim` objects extracted from that document's chunks.

---

## Phase 4: Cross-Document Reasoning (Model: claude-opus-4-20250514)

This phase requires the more capable Opus model because it performs entity resolution and cross-document reasoning over the full case corpus.

### Input

- All per-document claim files from `original_claims/`
- The anonymization mapping from `metadata/entity_mapping.json`
- All anonymized documents from `anonymized_docs/`

### Processing

1. **Knowledge Graph Assembly**: Merge per-chunk claims into a unified knowledge graph. Deduplicate claims that appear in multiple chunks of the same document.

2. **Entity Resolution**: Identify when different labels across documents refer to the same entity. NTSB documents use natural variation (e.g., "PIC" vs "the captain" vs "the pilot in command"). Build an entity equivalence map.

3. **Cross-Reference Validation**: For each cross-reference identified in Phase 3, verify that the linked claims genuinely refer to the same fact. Discard false cross-references.

4. **Domain Registry Construction**: Extract domain-specific entities (aircraft specs, operation type, regulatory context, personnel, temporal bounds) into a structured registry.

5. **Scope Map Construction**: Assign each document its content domain classification -- what topics it covers and what is forbidden for its document type.

### Output

Write the following to `metadata/` within the case directory:

**Knowledge Graph** (`metadata/knowledge_graph.json`):
```json
{
  "claims": [
    {"claim_id": "...", "subject": "...", "predicate": "...", "object": "...", "source_document": "...", "confidence": 0.95}
  ],
  "cross_references": [
    {"reference_id": "...", "source_claim": "...", "target_claim": "...", "relationship": "...", "source_documents": ["...", "..."]}
  ]
}
```

**Domain Registry** (`metadata/domain_registry.json`) conforming to `DomainRegistry` schema:
```json
{
  "case_id": "CASE_001",
  "entries": [
    {"domain": "aircraft", "original_value": "S-76B", "anonymized_value": "S-76B"},
    {"domain": "operator", "original_value": "Island Express", "anonymized_value": "Airline-A"},
    {"domain": "airport", "original_value": "KSNA", "anonymized_value": "Airport-Alpha"}
  ]
}
```

**Scope Map** (`metadata/scope_map.json`) conforming to `ScopeMap` schema:
```json
{
  "case_id": "CASE_001",
  "entries": [
    {"document_id": "ops_group_report", "scope_classification": "crew_decisions, sops, dispatch, flight_planning"},
    {"document_id": "meteorology_report", "scope_classification": "metar_taf, pireps, weather_modeling, visibility_conditions"},
    {"document_id": "structures_analysis", "scope_classification": "wreckage_distribution, fracture_surfaces, material_analysis"}
  ]
}
```

---

## Output Directory Layout

After all phases complete, the case directory should contain:

```
corpus/ntsb/{case_id}/
  chunks/                          # (pre-existing from Story 2.2)
    chunk_manifest.json
    {document_id}_chunk_001.txt
    ...
  anonymized_docs/                 # Phase 2 output
    ops_group_report.txt
    structures_analysis.txt
    meteorology_report.txt
    powerplants_analysis.txt
    maintenance_record.txt
    atc_transcript.txt
    witness_testimony_01.txt
    witness_testimony_02.txt
    preliminary_report.txt
    investigation_report.txt
    ...
  original_claims/                 # Phase 3 output
    ops_group_report.json
    structures_analysis.json
    meteorology_report.json
    ...
  metadata/                        # Phase 1 + Phase 4 output
    entity_mapping.json            # AnonymizationMapping entries
    knowledge_graph.json           # KnowledgeGraphClaim + CrossReference
    domain_registry.json           # DomainRegistry
    scope_map.json                 # ScopeMap
```
