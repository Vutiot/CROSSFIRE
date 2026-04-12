# CROSSFIRE: COPA Agentic Processing Plan

## Overview

This plan drives a Claude Code CLI session that processes Chicago COPA (Civilian Office of Police Accountability) investigation documents. The source corpus contains tactical response reports, final summary reports, case incident reports, arrest reports, and superintendent concurrences organized under `corpus/copa/{case_id}/`.

COPA documents represent **multi-vantage investigations** where the same incident is described from multiple perspectives: the involved officer's account, the complainant's account, witness statements, forensic evidence, and the investigator's summary. This multi-vantage structure is valuable for testing cross-perspective contradiction detection.

**Objective:** For each case, anonymize all identifying information (officer names, badge numbers, complainant/witness identities, addresses), preserve forensic document structure (TRR, FSR, OCIR formats), extract factual claim triples from every chunk, and assemble a cross-document knowledge graph that captures inter-vantage relationships.

### COPA Document Types

The corpus classifier recognizes 6 COPA document types:

| Document Type | Content Focus |
|---|---|
| `tactical_response_report` | Officer's account of force used, subject actions, environmental conditions |
| `final_summary_report` | COPA investigator's comprehensive analysis and findings |
| `case_incident_report` | Original complaint and incident description |
| `arrest_report` | Arrest details, charges, subject information |
| `superintendent_concurrence` | CPD superintendent's response to COPA findings |
| `document` | Catch-all: witness statements, evidence logs, other documents |

---

## Phase 1: Anonymization (Model: claude-sonnet-4-20250514)

Read every document in the case directory. Apply the following entity replacement rules to anonymize identifying information while preserving the multi-vantage investigation structure.

### Entity Replacement Rules

| Entity Type | Replacement Strategy | Example |
|---|---|---|
| Officer names | Sequential numbered identifiers | `Officer John Smith` -> `Officer-1`, `Sgt. Jane Doe` -> `Officer-2` |
| Officer badge/star numbers | Sequential generic numbers | `Star #12345` -> `Badge-001`, `Star #67890` -> `Badge-002` |
| Complainant names | Labeled identifiers | `Michael Johnson` -> `Subject-A` |
| Witness names | Sequential lettered identifiers | `Lisa Brown` -> `Witness-A`, `Robert Davis` -> `Witness-B` |
| Specific addresses | Generic neighborhood labels | `1234 S. Michigan Ave` -> `Location-North`, `5678 W. Madison St` -> `Location-South` |
| Neighborhood names | Generic area labels | `Englewood` -> `Area-1`, `Austin` -> `Area-2` |
| Case identifiers (RD numbers) | Sequential generic IDs | `RD# JA-123456` -> `Case-001` |
| Log numbers | Sequential generic IDs | `Log# 2019-0001234` -> `Log-001` |
| OEMC event numbers | Sequential generic IDs | `Event# 1234-5678` -> `Event-001` |
| Phone numbers, SSNs | Redacted | `[REDACTED]` |
| Dates of birth | Redacted | `[REDACTED]` |

### Preservation Rules

**DO preserve:**
- Use-of-force classifications (levels, types)
- Injury descriptions and medical treatment details
- Tactical terminology (TRR categories, force mitigation efforts)
- Procedural references (CPD General Orders, Special Orders)
- Environmental conditions (lighting, weather, location type)
- Weapon types and descriptions
- Temporal ordering of events within the incident
- All measurement values (distances, times, counts)
- COPA finding categories (Sustained, Not Sustained, Exonerated, Unfounded)
- Allegation categories and rule violations cited

**DO NOT preserve / MUST anonymize:**
- Any real person's name (officers, subjects, witnesses, investigators)
- Any real badge or star number
- Any real address or specific location
- Any real case, log, or event number
- Any identifying demographic details beyond what is procedurally relevant

### Multi-Vantage Consistency

COPA cases contain multiple accounts of the same incident. Each account may describe events differently -- this is an intended feature. Maintain consistent anonymization across all documents in a case (the same officer is always `Officer-1` everywhere), but preserve the natural variation in how different vantage points describe the same events.

### Output

Write the anonymization mapping to `metadata/entity_mapping.json` in the case directory.

Format (conforming to `AnonymizationMapping` schema):
```json
[
  {"original": "Officer John Smith", "anonymized": "Officer-1", "entity_type": "officer"},
  {"original": "Star #12345", "anonymized": "Badge-001", "entity_type": "badge_number"},
  {"original": "Michael Johnson", "anonymized": "Subject-A", "entity_type": "complainant"},
  {"original": "1234 S. Michigan Ave", "anonymized": "Location-North", "entity_type": "address"},
  {"original": "RD# JA-123456", "anonymized": "Case-001", "entity_type": "case_identifier"}
]
```

---

## Phase 2: Reformatting (Model: claude-sonnet-4-20250514)

Reformat each anonymized document to preserve authentic COPA/CPD document structure. Each document type has specific formatting conventions.

### Structure Preservation Rules

**Tactical Response Report (TRR):**
- Structured form layout with numbered fields
- Force categories and levels (checkboxes, codes)
- Subject resistance descriptions
- Officer response descriptions
- Environmental conditions section
- Supervisor review section

**Final Summary Report (FSR):**
- Formal investigative report structure
- Numbered allegations with findings
- Evidence summary (documentary, testimonial, forensic)
- Analysis section with credibility assessments
- Conclusions and recommendations

**Case Incident Report (OCIR):**
- Standardized complaint intake format
- Incident description (complainant's account)
- Involved parties list
- Allegation categories
- Preliminary investigation notes

**Arrest Report:**
- Booking information format
- Charges and statute references
- Narrative section
- Property inventory

**Superintendent Concurrence:**
- Brief memorandum format
- Reference to COPA findings
- Concurrence or non-concurrence statement
- Disciplinary recommendation

### Output

Write reformatted documents as `.txt` files in `anonymized_docs/` within the case directory.

```
corpus/copa/{case_id}/anonymized_docs/
  tactical_response_report.txt
  final_summary_report.txt
  case_incident_report.txt
  arrest_report.txt
  superintendent_concurrence.txt
  ...
```

---

## Phase 3: Per-Chunk Claim Extraction (Model: claude-sonnet-4-20250514)

This phase uses **fan-out architecture**: process each chunk independently to maximize throughput and minimize per-call cost.

### Input

Read the chunk manifest at `corpus/copa/{case_id}/chunks/chunk_manifest.json` to get the list of all chunks and their source document mappings.

### Processing

For each chunk in the manifest:

1. Read the chunk file from `chunks/{chunk_filename}`
2. Extract all atomic factual claims as structured triples
3. Categorize each claim by type
4. Pay special attention to claims about the same event from different vantage points (officer account vs complainant account vs witness account)

### Claim Triple Format

Each claim is a subject-predicate-object triple conforming to the `KnowledgeGraphClaim` schema:

```json
{
  "claim_id": "COPA_001",
  "subject": "Officer-1",
  "predicate": "used_force_type",
  "object": "emergency_takedown",
  "source_document": "tactical_response_report",
  "confidence": 0.95
}
```

### Claim Categories (COPA-specific)

- **force_event**: use-of-force descriptions, resistance descriptions, force levels
- **temporal**: timestamps, event sequences, response times
- **procedural**: CPD General Orders compliance, notification procedures, reporting
- **testimonial**: officer statements, complainant accounts, witness observations
- **forensic**: injury descriptions, medical records, physical evidence
- **environmental**: location descriptions, lighting, weather, crowd conditions
- **administrative**: investigation timeline, finding categories, disciplinary actions

### Cross-Reference Identification

When a claim references the same fact as a claim in another chunk or document, record it as a cross-reference conforming to the `CrossReference` schema:

```json
{
  "reference_id": "xref_001",
  "source_claim": "COPA_001",
  "target_claim": "COPA_042",
  "relationship": "same_event_different_vantage",
  "source_documents": ["tactical_response_report", "case_incident_report"]
}
```

### Output

Write per-document claim files to `original_claims/` within the case directory:

```
corpus/copa/{case_id}/original_claims/
  tactical_response_report.json
  final_summary_report.json
  case_incident_report.json
  ...
```

---

## Phase 4: Cross-Document Reasoning (Model: claude-opus-4-20250514)

This phase requires the more capable Opus model because it performs cross-vantage reasoning and entity resolution across the full case.

### Input

- All per-document claim files from `original_claims/`
- The anonymization mapping from `metadata/entity_mapping.json`
- All anonymized documents from `anonymized_docs/`

### Processing

1. **Knowledge Graph Assembly**: Merge per-chunk claims into a unified knowledge graph. Deduplicate claims that appear in multiple chunks of the same document.

2. **Entity Resolution**: Identify when different labels across documents refer to the same entity. COPA documents may refer to the same person as "the subject", "the complainant", "Mr. [Name]", or "the arrested individual." Build an entity equivalence map.

3. **Cross-Vantage Reasoning**: Map the relationships between different accounts of the same incident. Identify claims where the officer's account differs from the complainant's, where witness observations conflict with the TRR, or where the FSR analysis contradicts the original incident report.

4. **Cross-Reference Validation**: For each cross-reference identified in Phase 3, verify that the linked claims genuinely refer to the same fact. Discard false cross-references.

5. **Domain Registry Construction**: Extract domain-specific entities (force types, allegation categories, procedural references, personnel roles, temporal bounds) into a structured registry.

6. **Scope Map Construction**: Assign each document its content domain classification -- what topics it covers (e.g., force description, investigation analysis, complaint intake).

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
  "case_id": "COPA_CASE_001",
  "entries": [
    {"domain": "officer", "original_value": "Officer John Smith", "anonymized_value": "Officer-1"},
    {"domain": "address", "original_value": "1234 S. Michigan Ave", "anonymized_value": "Location-North"},
    {"domain": "case_identifier", "original_value": "RD# JA-123456", "anonymized_value": "Case-001"}
  ]
}
```

**Scope Map** (`metadata/scope_map.json`) conforming to `ScopeMap` schema:
```json
{
  "case_id": "COPA_CASE_001",
  "entries": [
    {"document_id": "tactical_response_report", "scope_classification": "force_description, officer_account, environmental_conditions"},
    {"document_id": "final_summary_report", "scope_classification": "investigation_analysis, credibility_assessment, findings"},
    {"document_id": "case_incident_report", "scope_classification": "complaint_intake, complainant_account, initial_allegations"}
  ]
}
```

---

## Output Directory Layout

After all phases complete, the case directory should contain:

```
corpus/copa/{case_id}/
  chunks/                          # (pre-existing from Story 2.2)
    chunk_manifest.json
    {document_id}_chunk_001.txt
    ...
  anonymized_docs/                 # Phase 2 output
    tactical_response_report.txt
    final_summary_report.txt
    case_incident_report.txt
    arrest_report.txt
    superintendent_concurrence.txt
    ...
  original_claims/                 # Phase 3 output
    tactical_response_report.json
    final_summary_report.json
    case_incident_report.json
    ...
  metadata/                        # Phase 1 + Phase 4 output
    entity_mapping.json            # AnonymizationMapping entries
    knowledge_graph.json           # KnowledgeGraphClaim + CrossReference
    domain_registry.json           # DomainRegistry
    scope_map.json                 # ScopeMap
```
