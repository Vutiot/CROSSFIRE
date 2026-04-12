# CROSSFIRE: Grenfell Tower Inquiry Agentic Processing Plan

## Overview

This plan drives a Claude Code CLI session that processes Grenfell Tower Inquiry documents. The source corpus contains hearing transcripts, expert reports, and documentary evidence from the public inquiry into the Grenfell Tower fire. Documents are organized under `corpus/grenfell/{case_id}/`.

The Grenfell corpus is structured around **parties to the inquiry** -- companies and organizations whose actions are examined through adversarial questioning. This party-vs-party testimony structure is a key feature for cross-entity boundary testing in contradiction detection.

**Objective:** For each case (inquiry module), anonymize all identifying information with special attention to the 8 cladding inquiry parties, preserve hearing transcript structure (Q&A format with page/line references), extract factual claim triples from every chunk, and assemble a cross-document knowledge graph that captures inter-party relationships.

### Grenfell Document Types

The corpus classifier recognizes 2 Grenfell document types:

| Document Type | Content Focus |
|---|---|
| `hearing_transcript` | Verbatim hearing transcripts with Q&A testimony, page/line references |
| `document` | Expert reports, documentary evidence, correspondence, technical analyses |

---

## Phase 1: Anonymization (Model: claude-sonnet-4-20250514)

Read every document in the case directory. Apply the following entity replacement rules to anonymize identifying information while preserving the party-vs-party testimony structure.

### Party Anonymization (8 Cladding Inquiry Parties)

The Grenfell inquiry centers on 8 key parties. Each must be consistently anonymized across all documents:

| Original Party | Anonymized Label | Role |
|---|---|---|
| Arconic | Company-A | Cladding panel manufacturer |
| Celotex | Company-B | Insulation manufacturer |
| Kingspan | Company-C | Insulation manufacturer |
| RBKC TMO (Royal Borough of Kensington and Chelsea Tenant Management Organisation) | Organization-D | Building management |
| London Fire Brigade | Service-E | Emergency response |
| BRE (Building Research Establishment) | Agency-F | Testing and certification |
| Exova (Warringtonfire) | Agency-G | Fire testing laboratory |
| Studio E | Firm-H | Architect |

### Other Entity Replacement Rules

| Entity Type | Replacement Strategy | Example |
|---|---|---|
| Witness names | Sequential numbered identifiers | `Dr. Lane` -> `Witness-1`, `Mr. Hyett` -> `Witness-2` |
| Specific locations | Generic place labels | `Grenfell Tower` -> `Tower-X`, `Lancaster West Estate` -> `Estate-Y` |
| Addresses | Generic location labels | `Bramley Road` -> `Street-1`, `Latimer Road` -> `Street-2` |
| Counsel names | Role-based identifiers | `Ms. Barwise QC` -> `Counsel-A`, `Mr. Millett QC` -> `Lead-Counsel` |
| Specific dates | Offset by a fixed random delta per case | All dates shifted by same offset to preserve intervals |
| Phone numbers, emails | Redacted | `[REDACTED]` |

### Preservation Rules

**DO preserve:**
- Technical specifications (fire resistance ratings, test results, material properties)
- Building construction details (cladding system components, installation methods)
- Regulatory references (Building Regulations, Approved Document B, BS standards)
- Causal relationships and event sequences
- Temporal ordering between events
- Test report numbers and certification references
- Fire behavior descriptions (spread rates, temperatures, timelines)
- All measurement units and numeric values

**DO NOT preserve / MUST anonymize:**
- Any real person's name
- Any real company or organization name (use party labels above)
- Specific London addresses and locations
- The name "Grenfell Tower" itself

### Party-vs-Party Testimony Structure

Hearing transcripts contain cross-examination where one party's counsel questions witnesses from another party. **Preserve this adversarial structure** -- it creates natural cross-party entity boundaries that are valuable for contradiction detection testing.

When anonymizing, maintain the party attribution so it is clear which anonymized party is being questioned and by whom: `Counsel for Company-A questioned Witness-3 (employed by Company-B)`.

### Output

Write the anonymization mapping to `metadata/entity_mapping.json` in the case directory.

Format (conforming to `AnonymizationMapping` schema):
```json
[
  {"original": "Arconic", "anonymized": "Company-A", "entity_type": "cladding_party"},
  {"original": "Celotex", "anonymized": "Company-B", "entity_type": "cladding_party"},
  {"original": "Grenfell Tower", "anonymized": "Tower-X", "entity_type": "location"},
  {"original": "Dr. Lane", "anonymized": "Witness-1", "entity_type": "witness"}
]
```

---

## Phase 2: Reformatting (Model: claude-sonnet-4-20250514)

Reformat each anonymized document to preserve authentic hearing transcript and inquiry document structure.

### Structure Preservation Rules

**Hearing Transcripts:**
- Page and line number references must be preserved (e.g., `[page 42, line 15]`)
- Q&A format: Questions from counsel, answers from witness
- Speaker identification with party affiliation
- Preserve exhibit references (`Exhibit {number}`)
- Maintain day/session structure (morning session, afternoon session)
- Preserve procedural language ("Mr Chairman", "if I may", "I put it to you")

**Documentary Evidence / Expert Reports:**
- Section and paragraph numbering
- Technical appendices with test data
- Cross-references to other documents and exhibits
- Formal report structure (introduction, findings, conclusions)

### Output

Write reformatted documents as `.txt` files in `anonymized_docs/` within the case directory.

```
corpus/grenfell/{case_id}/anonymized_docs/
  hearing_transcript_day_01.txt
  hearing_transcript_day_02.txt
  expert_report_01.txt
  ...
```

---

## Phase 3: Per-Chunk Claim Extraction (Model: claude-sonnet-4-20250514)

This phase uses **fan-out architecture**: process each chunk independently to maximize throughput and minimize per-call cost.

### Input

Read the chunk manifest at `corpus/grenfell/{case_id}/chunks/chunk_manifest.json` to get the list of all chunks and their source document mappings.

### Processing

For each chunk in the manifest:

1. Read the chunk file from `chunks/{chunk_filename}`
2. Extract all atomic factual claims as structured triples
3. Categorize each claim by type
4. Pay special attention to claims that cross party boundaries (e.g., Company-A's product was tested by Agency-F)

### Claim Triple Format

Each claim is a subject-predicate-object triple conforming to the `KnowledgeGraphClaim` schema:

```json
{
  "claim_id": "GT_001",
  "subject": "Company-A",
  "predicate": "manufactured",
  "object": "PE-core ACM panels",
  "source_document": "hearing_transcript_day_01",
  "confidence": 0.95
}
```

### Claim Categories (Grenfell-specific)

- **material**: cladding specifications, insulation types, fire ratings
- **procedural**: building regulations compliance, testing procedures, approval processes
- **temporal**: dates of tests, installations, correspondence, fire events
- **causal**: cause-effect assertions about fire spread, material behavior
- **testimonial**: witness statements, disputed facts between parties
- **regulatory**: Building Regulations requirements, BS standards, Approved Document B interpretations

### Cross-Reference Identification

When a claim references the same fact as a claim in another chunk or document, record it as a cross-reference conforming to the `CrossReference` schema:

```json
{
  "reference_id": "xref_001",
  "source_claim": "GT_001",
  "target_claim": "GT_042",
  "relationship": "same_test_different_party_account",
  "source_documents": ["hearing_transcript_day_01", "hearing_transcript_day_05"]
}
```

### Output

Write per-document claim files to `original_claims/` within the case directory:

```
corpus/grenfell/{case_id}/original_claims/
  hearing_transcript_day_01.json
  hearing_transcript_day_02.json
  expert_report_01.json
  ...
```

---

## Phase 4: Cross-Document Reasoning (Model: claude-opus-4-20250514)

This phase requires the more capable Opus model because it performs cross-party reasoning and entity resolution across the full inquiry module.

### Input

- All per-document claim files from `original_claims/`
- The anonymization mapping from `metadata/entity_mapping.json`
- All anonymized documents from `anonymized_docs/`

### Processing

1. **Knowledge Graph Assembly**: Merge per-chunk claims into a unified knowledge graph. Deduplicate claims that appear in multiple chunks of the same transcript.

2. **Entity Resolution**: Identify when different labels across documents refer to the same entity. Inquiry documents may refer to the same product by trade name, generic description, or test sample identifier. Build an entity equivalence map.

3. **Cross-Party Reasoning**: Map the relationships between the 8 anonymized parties. Identify claims where one party's testimony contradicts another's, where test results from one agency conflict with claims by a manufacturer, or where the building manager's records conflict with the architect's specifications.

4. **Cross-Reference Validation**: For each cross-reference identified in Phase 3, verify that the linked claims genuinely refer to the same fact. Discard false cross-references.

5. **Domain Registry Construction**: Extract domain-specific entities (building materials, fire test results, regulatory standards, party roles, temporal bounds) into a structured registry.

6. **Scope Map Construction**: Assign each document its content domain classification -- what topics it covers (e.g., cladding procurement, fire testing, emergency response).

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
  "case_id": "MODULE_01",
  "entries": [
    {"domain": "cladding_party", "original_value": "Arconic", "anonymized_value": "Company-A"},
    {"domain": "cladding_party", "original_value": "Celotex", "anonymized_value": "Company-B"},
    {"domain": "location", "original_value": "Grenfell Tower", "anonymized_value": "Tower-X"}
  ]
}
```

**Scope Map** (`metadata/scope_map.json`) conforming to `ScopeMap` schema:
```json
{
  "case_id": "MODULE_01",
  "entries": [
    {"document_id": "hearing_transcript_day_01", "scope_classification": "cladding_procurement, manufacturer_testimony, fire_testing"},
    {"document_id": "expert_report_01", "scope_classification": "fire_engineering, material_analysis, regulatory_compliance"}
  ]
}
```

---

## Output Directory Layout

After all phases complete, the case directory should contain:

```
corpus/grenfell/{case_id}/
  chunks/                          # (pre-existing from Story 2.2)
    chunk_manifest.json
    {document_id}_chunk_001.txt
    ...
  anonymized_docs/                 # Phase 2 output
    hearing_transcript_day_01.txt
    hearing_transcript_day_02.txt
    expert_report_01.txt
    ...
  original_claims/                 # Phase 3 output
    hearing_transcript_day_01.json
    hearing_transcript_day_02.json
    expert_report_01.json
    ...
  metadata/                        # Phase 1 + Phase 4 output
    entity_mapping.json            # AnonymizationMapping entries
    knowledge_graph.json           # KnowledgeGraphClaim + CrossReference
    domain_registry.json           # DomainRegistry
    scope_map.json                 # ScopeMap
```
