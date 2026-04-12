# CROSSFIRE: Agentic Synthetic Contradiction Generation Pipeline

## Full Context Plan for LLM Execution

---

## 1. PROJECT OBJECTIVE

You are building a synthetic dataset for **fact contradiction detection** in aviation investigation documents. The source material is real NTSB (National Transportation Safety Board) investigation docket files. Your job is to:

1. Read real NTSB case corpora
2. Anonymize all identifying information
3. Reformat documents to match authentic NTSB structure
4. Inject realistic, labeled contradictions at multiple granularities
5. Output a structured benchmark dataset

The end product is a dataset where each sample contains documents with known contradictions, labeled by type, scope, detectability, and difficulty — usable for training and evaluating contradiction detection systems (both graph-based and LLM-agentic).

---

## 2. ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR AGENT                     │
│  Per case corpus: inventory, knowledge graph, dispatch   │
│                                                          │
│  Outputs: domain_registry.json, scope_map.json,          │
│           knowledge_graph.json                           │
├──────────────────────┬──────────────────────────────────┤
│                      │                                    │
│   ┌──────────────────▼───────────────────┐               │
│   │         DOCUMENT AGENT               │               │
│   │  Per file: anonymize, reformat,      │  ◄── Repeated │
│   │  extract claims, intra-doc inject    │      per file  │
│   └──────────────────┬───────────────────┘               │
│                      │                                    │
│   ┌──────────────────▼───────────────────┐               │
│   │      CROSS-DOCUMENT AGENT            │               │
│   │  Across files: inter-doc inject,     │               │
│   │  cross-witness, validate             │               │
│   └──────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

Three agent levels execute sequentially per case. Each downstream agent receives context artifacts from the level above.

---

## 3. ORCHESTRATOR AGENT

### 3.1 Purpose

Manages the full pipeline for one investigation case. Reads the entire corpus before any modifications begin.

### 3.2 Inputs

- A case folder containing all docket files (PDFs/text): factual reports, group chair reports, technical analyses, witness interviews, party submissions, maintenance records, ATC transcripts, METAR data, preliminary reports, press coverage, regulatory filings, internal memos.

### 3.3 Tasks

#### 3.3.1 Corpus Inventory

Scan the case folder. Classify every file by NTSB document type:

| Document Type | NTSB Group | Content Focus |
|---|---|---|
| Operations Group Chair Report | Operations | Crew qualifications, decisions, SOPs, dispatch, flight planning |
| Structures Group Chair Report | Structures | Wreckage distribution, fracture analysis, structural failure |
| Powerplants Group Chair Report | Powerplants | Engine teardown, fuel system, propeller/rotor |
| Systems Group Chair Report | Systems | Hydraulics, electrical, avionics, flight controls |
| Meteorology Group Factual Report | Meteorology | Weather observations, forecasts, METAR/TAF, PIREPs |
| Maintenance Records Group Report | Maintenance | Logbooks, ADs, service bulletins, inspection history |
| ATC Transcript / Radar Data | ATC | Communications, radar returns, timestamps |
| Witness Interview Transcript | Human Factors | Q&A testimony, sensory observations |
| Survival Factors Report | Survival | Cabin safety, egress, injuries, crashworthiness |
| Flight Data Recorder Report | Recorders | FDR/CVR data, parameter readouts |
| Manufacturer Party Submission | Party | Technical defense, service history, design rationale |
| Preliminary Report | NTSB | Initial public summary, limited facts |
| Final Probable Cause Report | NTSB | Findings, probable cause, recommendations |
| Press Coverage | External | Journalistic accounts |
| Regulatory Filing / AD | FAA | Airworthiness directives, regulatory actions |
| Internal Memo | Operator | Company communications, safety notices |

#### 3.3.2 Domain Registry Construction

Extract from the corpus and compile into `domain_registry.json`:

```json
{
  "case_id": "CASE_001",
  "aircraft": {
    "type": "rotorcraft",
    "make": "Sikorsky",
    "model": "S-76B",
    "registration": "N72EX",
    "engine_type": "PT6B-36A",
    "engine_count": 2,
    "engine_manufacturer": "Pratt & Whitney Canada",
    "max_gross_weight_lbs": 11700,
    "rotor_system": "4-blade main, 4-blade tail"
  },
  "operation": {
    "cfr_part": "Part 135",
    "operation_type": "on-demand air taxi",
    "operator": "Island Express Helicopters"
  },
  "flight": {
    "origin_airport": "KSNA",
    "destination_airport": "KCMA",
    "date": "2020-01-26",
    "departure_time_utc": "2020-01-26T17:06:00Z",
    "accident_time_utc": "2020-01-26T17:47:00Z"
  },
  "regulatory_context": {
    "applicable_cfr_parts": ["14 CFR 135", "14 CFR 91"],
    "applicable_ads": [
      {"number": "AD 2019-XX-XX", "issued": "2019-03-15", "subject": "..."}
    ],
    "applicable_service_bulletins": []
  },
  "personnel": [
    {"role": "Pilot in Command", "certificates": ["ATP", "CFII"], "total_hours": 8215}
  ],
  "temporal_bounds": {
    "earliest_relevant_date": "2018-01-01",
    "accident_date": "2020-01-26",
    "investigation_close_date": "2021-06-XX",
    "no_ad_after": "2020-01-26"
  },
  "valid_entity_pools": {
    "swappable_engines": ["PT6B-36A", "PT6B-36B", "PT6B-37A"],
    "swappable_aircraft": ["S-76B", "S-76C", "S-76D"],
    "swappable_airports": ["KSNA", "KVNY", "KBUR", "KLAX"],
    "numeric_bounds": {
      "altitude_ft": [0, 5000],
      "airspeed_kts": [0, 180],
      "visibility_sm": [0.25, 10],
      "flight_hours": [7000, 10000]
    }
  }
}
```

**CRITICAL RULES for the domain registry:**
- `engine_type` must match the aircraft. Never assign a turbofan to a turboshaft aircraft.
- `engine_count` must be factually correct for the model. A 737 has 2 engines, never 3.
- `no_ad_after` prevents anachronistic regulatory citations. No AD issued after the accident date may appear in factual reports written during the investigation.
- `swappable_*` pools contain only same-type, same-domain entities. A helicopter engine pool contains only turboshaft variants. An airport pool contains only airports in the same geographic region.

#### 3.3.3 Scope Map Construction

Assign each document its content domain. Output `scope_map.json`:

```json
{
  "ops_group_report": {
    "primary_focus": ["crew_decisions", "sops", "dispatch", "flight_planning", "weather_briefing"],
    "allowed_overlap": ["accident_summary_header"],
    "forbidden_content": ["metallurgy", "engine_teardown", "structural_failure_analysis"]
  },
  "structures_report": {
    "primary_focus": ["wreckage_distribution", "fracture_surfaces", "material_analysis"],
    "allowed_overlap": ["accident_summary_header"],
    "forbidden_content": ["crew_qualifications", "dispatch_procedures", "weather_modeling"]
  },
  "meteorology_report": {
    "primary_focus": ["metar_taf", "pireps", "weather_modeling", "visibility_conditions"],
    "allowed_overlap": ["accident_summary_header"],
    "forbidden_content": ["engine_specs", "maintenance_history", "crew_decisions"]
  },
  "witness_testimony": {
    "primary_focus": ["sensory_observations", "timeline_from_witness_pov", "environmental_conditions_observed"],
    "allowed_overlap": ["accident_summary_header"],
    "forbidden_content": ["regulatory_citations", "technical_specifications"]
  }
}
```

This map enforces document specialization. Each document covers its group's domain. Cross-domain content is restricted to a one-sentence accident summary header.

#### 3.3.4 Knowledge Graph Extraction

Build a structured knowledge graph of all factual claims in the corpus. Each claim is a triple:

```json
{
  "claims": [
    {
      "id": "claim_001",
      "subject": "PIC",
      "predicate": "held_certificate",
      "object": "ATP",
      "source_doc": "ops_group_report",
      "source_section": "2.1",
      "confidence": "stated_fact"
    },
    {
      "id": "claim_042",
      "subject": "flight",
      "predicate": "departed_at",
      "object": "2020-01-26T17:06:00Z",
      "source_doc": "atc_transcript",
      "source_section": "line_23",
      "confidence": "stated_fact"
    }
  ],
  "cross_references": [
    {
      "claim_a": "claim_042",
      "claim_b": "claim_043",
      "relationship": "same_event_different_source",
      "docs": ["atc_transcript", "ops_group_report"]
    }
  ]
}
```

The knowledge graph is the basis for all contradiction injection. Cross-references identify where the same fact appears in multiple documents — these are the natural sites for inter-document contradictions.

#### 3.3.5 Dispatch

Pass to the Document Agent (per file):
- The file content
- `domain_registry.json`
- `scope_map.json` (this file's entry)
- The knowledge graph (claims relevant to this file)
- Anonymization mapping table (starts empty, grows as files are processed; ensures consistency)

After all files are processed, pass to the Cross-Document Agent:
- All anonymized files
- Full knowledge graph with cross-references
- `domain_registry.json`
- Complete anonymization mapping

---

## 4. DOCUMENT AGENT

### 4.1 Purpose

Processes a single file: anonymization, reformatting, claim extraction, and intra-document contradiction injection.

### 4.2 Task 1: Anonymization

#### 4.2.1 Entity Replacement Rules

| Entity Type | Replacement Strategy | Example |
|---|---|---|
| Person names | Role-based placeholder + numeric ID | "John Smith" → "Pilot-1", "Jane Doe" → "Mechanic-A" |
| Company/operator names | Generic category + ID | "Island Express Helicopters" → "Operator-1" |
| Aircraft registration | Synthetic N-number | "N72EX" → "N-ANON-001" |
| Airport names | Region-based abstraction | "John Wayne Airport (KSNA)" → "Regional Airport Alpha (RAPT-A)" |
| City/location names | Region identifier | "Calabasas, CA" → "Location-7, Region-West" |
| Flight numbers | Synthetic | "Flight 1282" → "Flight ANON-042" |
| Specific dates | Offset by random fixed delta per case | All dates shifted by same offset to preserve intervals |
| Phone numbers, addresses | Redacted | "[REDACTED]" |
| Airline names (third party) | Generic | "Southwest Airlines" → "Carrier-B" |

#### 4.2.2 Preservation Rules

**DO preserve:**
- Technical facts (altitudes, airspeeds, weights, temperatures)
- Causal relationships and event sequences
- Temporal ordering between events (even if absolute dates are shifted)
- Part numbers and serial numbers (these will be used for contradiction injection)
- Regulatory citation numbers (14 CFR Part 135, etc.)
- Aircraft make/model (needed for domain validity)
- Weather observations and METAR data values
- All measurement units and numeric values

**DO NOT anonymize:**
- Aircraft manufacturer names (Boeing, Airbus, Sikorsky) — needed for domain coherence
- Engine manufacturer names — needed for domain coherence
- FAA, NTSB, TSB — institutional names stay
- Standard aviation terminology

#### 4.2.3 Mapping Table

Maintain a growing JSON mapping:

```json
{
  "persons": {
    "John Smith": {"anon": "Pilot-1", "role": "PIC", "first_seen": "ops_group_report"},
    "Jane Doe": {"anon": "Mechanic-A", "role": "lead_mechanic", "first_seen": "maintenance_report"}
  },
  "locations": {
    "John Wayne Airport": {"anon": "Regional Airport Alpha", "icao_anon": "RAPT-A"},
    "Calabasas": {"anon": "Location-7"}
  },
  "organizations": {
    "Island Express Helicopters": {"anon": "Operator-1", "type": "Part 135 operator"}
  },
  "dates": {
    "offset_days": 47
  }
}
```

This mapping is shared across all Document Agent invocations for the same case to ensure cross-document consistency.

### 4.3 Task 2: NTSB Document Reformatting

Every anonymized document must be wrapped in authentic NTSB scaffolding. This is critical for realism.

#### 4.3.1 Required Boilerplate Structure

```
========================================================
NATIONAL TRANSPORTATION SAFETY BOARD
Office of Aviation Safety
Washington, D.C. 20594
========================================================

Docket: SA-XXX
Exhibit No. [X][X]
Case ID: [CASE_ID]

[DOCUMENT TYPE]
[GROUP NAME] FACTUAL REPORT

========================================================

A. ACCIDENT

Location:           [Anonymized Location]
Date:               [Anonymized Date]
Time:               [Anonymized Time] local
Aircraft:           [Make/Model], [Anonymized Registration]
Injuries:           [X] Fatal, [X] Serious, [X] Minor, [X] None
Aircraft Damage:    [Destroyed/Substantial/Minor/None]

B. GROUP

Group Chairman:     [Anonymized Name], [Title], NTSB
Group Members:
  - [Anonymized Name], [Title], [Organization-Anon]
  - [Anonymized Name], [Title], [Organization-Anon]

C. SUMMARY
[One-sentence accident summary — this is the ONLY overlap allowed across document types]

D. DETAILS
[Domain-specific content begins here, using lettered sub-sections]

========================================================
[DOCUMENT TYPE]  |  [CASE_ID]  |  Page [X] of [Y]
========================================================
```

#### 4.3.2 Register Rules

These rules control the writing style per document type:

**Factual Reports (all group types):**
- Terse, declarative sentences. No explanatory clauses.
- WRONG: "14 CFR Part 135, which governs commuter and on-demand operations, required..."
- RIGHT: "The flight was operated under 14 CFR Part 135."
- Cite regulations by number only. Never explain what a regulation does.
- No adjectives expressing judgment. No "unfortunately", "tragically", "inadequate".
- Use passive voice for findings: "The left engine was found separated from the airframe."
- Use specific measurements with units: "2,300 feet MSL", "1.5 statute miles", "127 knots IAS".

**Witness Testimony Transcripts:**
- Q&A format: "Q: [Investigator question]\nA: [Witness response]"
- Witnesses use natural speech: hesitations ("uh", "um", "I think..."), self-corrections, vague descriptions of technical concepts.
- Witnesses should NOT cite regulations fluently. Replace regulatory fluency with phrases like "I'm not sure of the exact rule, but...", "I think there's a regulation about that...", "whatever the minimum is supposed to be..."
- Include sensory details: what they saw, heard, smelled, felt.
- Minimum target length: 5,000 words per testimony (real transcripts average 36,000 words). Include investigator follow-ups, clarifications, and tangential but realistic digressions.

**Manufacturer/Party Submissions:**
- Defensive and technical tone. Focus on design compliance, service history, known limitations.
- NOT white-paper style with sweeping recommendations.
- Include specific test data, certification references, and service bulletin history.
- Tone: "The [component] was designed and certified in accordance with [standard]. Service history across the fleet of [X] aircraft shows [Y] incidents in [Z] flight hours."

**Preliminary Reports:**
- Brief (800–2,000 words). Facts only, no analysis.
- Uses conditional language: "reportedly", "initial examination indicated", "according to preliminary information".
- Target: 800–2,000 words.

**Press Coverage:**
- Journalistic register. Lead paragraph with who/what/when/where.
- Do NOT include disclaimers like "While [X] is entirely unrelated to [Y], its legacy has reinforced..." — either the reference is natural or omit it entirely.
- Quotes from officials use attribution: "according to an NTSB spokesperson".

### 4.4 Task 3: Claim Extraction

Extract all atomic factual claims from the document as structured triples:

```json
{
  "doc_id": "ops_group_report_anon",
  "claims": [
    {
      "id": "OPS_001",
      "text": "The pilot held an Airline Transport Pilot certificate.",
      "triple": ["PIC", "held_certificate", "ATP"],
      "category": "personnel",
      "section": "D.1",
      "numeric_value": null
    },
    {
      "id": "OPS_007",
      "text": "The aircraft departed at 0906 local time.",
      "triple": ["flight", "departed_at", "0906L"],
      "category": "temporal",
      "section": "D.3",
      "numeric_value": {"value": 906, "unit": "local_time"}
    },
    {
      "id": "OPS_015",
      "text": "Visibility was reported as 2.5 statute miles.",
      "triple": ["conditions", "visibility", "2.5 SM"],
      "category": "meteorological",
      "section": "D.4",
      "numeric_value": {"value": 2.5, "unit": "statute_miles"}
    }
  ]
}
```

Categorize each claim:
- **temporal**: dates, times, durations, sequences
- **numeric**: altitudes, speeds, weights, distances, hours
- **personnel**: qualifications, experience, roles
- **meteorological**: weather observations, conditions
- **mechanical**: component states, part numbers, serial numbers, inspection findings
- **procedural**: actions taken, SOPs followed or violated
- **causal**: cause-effect assertions

### 4.5 Task 4: Intra-Document Contradiction Injection

For each document, select a subset of claims and generate contradicted versions. Not every claim gets contradicted — aim for 2–5 contradictions per document depending on length.

#### 4.5.1 Mechanism Application Rules

**numeric_drift:**
- Change a numeric value to a plausible but incorrect alternative.
- The new value MUST fall within the `numeric_bounds` defined in `domain_registry.json`.
- Drift should be proportional to the original value: ±5-20% for subtle (hard), ±20-50% for moderate (medium), ±50%+ or unit change for obvious (easy).
- Example: altitude 2,300 ft → 2,800 ft (hard), 2,300 ft → 3,500 ft (medium), 2,300 ft → 8,000 ft (easy — outside flight envelope for the operation).
- For measurement_unit_conflict subtype: same quantity reported in two units that don't convert correctly. Example: "29.92 inches Hg" in one section and "1012.5 millibars" in another (correct conversion is 1013.2 mb).

**entity_swap:**
- Replace an entity with another entity of the SAME TYPE from the `valid_entity_pools` in the domain registry.
- NEVER swap across domains. A turboshaft engine can only be swapped with another turboshaft. An airport can only be swapped with a nearby airport.
- For serial_number_mismatch subtype: change a part serial number so it doesn't match between the claim and a reference elsewhere. Example: "S/N 12847" → "S/N 12857".
- Difficulty: swapping PT6B-36A for PT6B-36B is hard (same family); swapping for CT7-8A is medium (different family, same category); swapping for CFM56 is FORBIDDEN (cross-domain).

**causal_inversion:**
- Reverse a cause-effect relationship.
- The inversion must remain grammatically natural and domain-plausible at surface level.
- Example: "The loss of visual reference caused the pilot to become spatially disoriented" → "Spatial disorientation caused the pilot to lose visual reference."
- Difficulty: subtle reorderings within a plausible chain are hard; reversing an obvious root cause is easy.

**temporal_contradiction:**
- Change a date, time, or event sequence.
- The new value MUST respect the `temporal_bounds` in the domain registry. No ADs, service bulletins, or regulatory actions can be cited from after the accident date.
- For sequence contradictions: swap the order of two events. Example: "The pilot requested and received a Special VFR clearance, then departed" → "The pilot departed, then requested a Special VFR clearance."
- Difficulty: small time shifts (0906 → 0911) are hard; large shifts (0906 → 1430) are easy; sequence swaps of closely related events are hard; swaps of clearly ordered events (departure before accident) are easy.

**omission_based_implicit:**
- Remove or alter a qualifier that changes the meaning of remaining text.
- Example: Remove "preliminary" from "preliminary findings suggest..." → "findings suggest..." (now conflicts with the final report if findings changed).
- Example: Remove "approximately" from "approximately 2,300 feet" → "2,300 feet" (now conflicts with another document that says "about 2,400 feet" — without the qualifier, the discrepancy becomes a contradiction).
- Difficulty: always medium to hard (requires noticing what's missing).

**temporal_revision_conflict:**
- Create a conflict between an earlier and later assessment.
- The preliminary report says X; the final report says not-X. This is naturally occurring in real investigations, so it's the most realistic mechanism.
- Example: Preliminary says "no evidence of mechanical failure"; final report identifies a fatigue crack.
- Difficulty: depends on how directly the statements oppose each other.

#### 4.5.2 Injection Format

Each injected contradiction modifies the document text in place and generates a label:

```json
{
  "id": "CASE001_INTRA_OPS_003",
  "scope": "intra_doc",
  "mechanism": "numeric_drift",
  "source_doc": "ops_group_report_anon",
  "original_claim": {
    "id": "OPS_015",
    "text": "Visibility was reported as 2.5 statute miles.",
    "location": {"section": "D.4", "paragraph": 3, "char_start": 142, "char_end": 194}
  },
  "contradicted_claim": {
    "text": "Visibility was reported as 4.0 statute miles.",
    "location": {"section": "D.7", "paragraph": 1, "char_start": 55, "char_end": 107}
  },
  "ground_truth": "original",
  "detectability": "single_hop",
  "affinity": "balanced",
  "difficulty": "medium",
  "domain_valid": true,
  "rationale": "Changed visibility from 2.5 SM to 4.0 SM. Both values are within VFR/IFR boundary range, making this a meaningful contradiction for determining whether VFR flight was appropriate."
}
```

#### 4.5.3 Validation Gate

After generating each contradiction, validate against the domain registry:

- [ ] The contradicted value falls within `numeric_bounds`?
- [ ] The swapped entity exists in `valid_entity_pools`?
- [ ] No date/AD/SB violates `temporal_bounds`?
- [ ] The aircraft specs remain internally consistent (correct engine count, correct engine type for airframe)?
- [ ] The contradiction stays within this document's `scope_map` domain?
- [ ] The modified text maintains the correct register for this document type?

If any check fails, reject the contradiction and generate a new one.

---

## 5. CROSS-DOCUMENT AGENT

### 5.1 Purpose

Generates contradictions BETWEEN documents in the same case corpus. These are the highest-value contradictions because they require cross-referencing multiple sources.

### 5.2 Inputs

- All anonymized documents (post Document Agent)
- Full knowledge graph with cross-references
- `domain_registry.json`
- All intra-document contradictions already injected (to avoid double-contradicting the same claims)

### 5.3 Strategy: Same-Fact Disagreements

Identify claims that appear in multiple documents (via the knowledge graph cross-references) and modify ONE document's version to contradict the other.

#### 5.3.1 High-Value Cross-Document Contradiction Sites

These are the natural fault lines where real NTSB documents can disagree:

| Document A | Document B | Contradiction Type | Example |
|---|---|---|---|
| Meteorology Report | Ops Group Report | numeric_drift | Different visibility values from same METAR |
| ATC Transcript | FDR Report | temporal_contradiction | Different timestamps for same event |
| Witness A Testimony | Witness B Testimony | causal_inversion + numeric_drift | Different accounts of impact direction, altitude, sound |
| Maintenance Log | Structures Report | entity_swap (serial_number) | Part S/N doesn't match between logbook and teardown |
| Preliminary Report | Final Report | temporal_revision_conflict | Changed findings between preliminary and final |
| Pilot Records | Ops Group Report | numeric_drift | Different total flight hours |
| Manufacturer Submission | Maintenance Report | temporal_contradiction | Different last-inspection dates |
| Weather Briefing (in Ops) | Meteorology Report | numeric_drift | Different wind/visibility values |

#### 5.3.2 Cross-Witness Disagreement Generation

This is the most naturalistic inter-document contradiction. Two witnesses observed the same event but report irreconcilable details.

**Process:**
1. Identify a shared event that two or more witnesses could have observed (the accident itself, a pre-accident maneuver, weather conditions at the scene).
2. In Witness A's testimony, the event is described one way.
3. In Witness B's testimony, modify the description to contradict Witness A's account.
4. The contradiction should be embedded in natural speech, surrounded by realistic conversational context.

**Subtypes:**
- **Directional disagreement**: "It came from the east" vs. "It was heading north"
- **Temporal disagreement**: "It was about 9 AM" vs. "It was closer to 10"
- **Sensory disagreement**: "I heard a loud bang" vs. "I didn't hear any unusual sound"
- **Quantity disagreement**: "It was flying very low, maybe 500 feet" vs. "It was at a normal altitude"
- **Sequence disagreement**: "I saw the smoke first, then heard the impact" vs. "The impact sound came first"

**Difficulty calibration:**
- Easy (single_hop): Direct contradiction of the same explicit fact in both testimonies.
- Medium (multi_hop): One witness mentions a time, another mentions a TV show they were watching — cross-referencing the show's schedule reveals the time conflict.
- Hard (entity_resolution_dependent): One witness refers to "the helicopter", another to "the aircraft" — the reader must resolve that these are the same entity and then notice their descriptions conflict.

#### 5.3.3 What NOT to Do (Anti-Patterns)

**FORBIDDEN — these are the errors identified in the critique:**

1. **Cross-domain entity injection**: NEVER reference MCAS in a helicopter report. NEVER reference a CFM56 engine in a turboshaft investigation. NEVER reference systems, components, or procedures from a different aircraft type/category.

2. **Anachronistic citations**: NEVER cite an AD, service bulletin, or regulatory action that was issued after the accident date in a factual report written during the investigation.

3. **Forced cross-entity connectivity**: NEVER mention an unrelated carrier, aircraft type, or accident in a factual report just to create graph connectivity. Factual reports are scoped tightly to the accident aircraft. If a cross-reference is needed, it must be organic (e.g., the same pilot flew for a different operator previously — that's natural context).

4. **Disclaimer-wrapped irrelevance**: NEVER write "While [X] is entirely unrelated to [topic], it is worth noting..." — if something is unrelated, it does not appear in the document. Real NTSB investigators don't pad reports with tangentially related content.

5. **Factual generation errors masquerading as contradictions**: "Three engines on a 737" is not a contradiction — it's a bug. The domain registry validation gate must catch these. Every generated fact must be consistent with the aircraft's real specifications.

### 5.4 Injection Format

```json
{
  "id": "CASE001_INTER_007",
  "scope": "inter_doc",
  "mechanism": "numeric_drift",
  "source_doc": "meteorology_report_anon",
  "source_claim": {
    "id": "MET_003",
    "text": "The 0853 METAR reported visibility of 2.5 statute miles.",
    "location": {"section": "D.2", "paragraph": 1}
  },
  "target_doc": "ops_group_report_anon",
  "target_claim": {
    "id": "OPS_015_modified",
    "text": "The METAR observation indicated visibility of 4.0 statute miles.",
    "location": {"section": "D.4", "paragraph": 3}
  },
  "ground_truth": "source_doc_correct",
  "detectability": "single_hop",
  "affinity": "graph_favoring",
  "difficulty": "medium",
  "domain_valid": true,
  "rationale": "Both documents reference the same METAR observation but report different visibility values. Detectable by comparing the meteorological data across both documents."
}
```

### 5.5 Detectability Design

**single_hop**: Comparing two directly related statements reveals the contradiction. Reader needs exactly 2 documents.

Example: Meteorology report says visibility 2.5 SM. Ops report says visibility 4.0 SM for the same METAR. Comparing the two sentences reveals the conflict.

**multi_hop**: Requires combining 3+ pieces of evidence across documents.

Example: Maintenance log says last inspection was at 8,100 flight hours. Ops report says pilot's logbook shows aircraft total time at 8,215 hours on accident date. Manufacturer submission says the inspection interval is 100 hours. The reader must compute: 8,215 - 8,100 = 115 hours since inspection, which exceeds the 100-hour interval — contradiction requires combining three documents and doing arithmetic.

**entity_resolution_dependent**: Only visible after resolving aliases.

Example: One document refers to "the Federal Aviation Administration's oversight review". Another refers to "the Administration's position was that the operator met all requirements." A third says "FAA inspectors found three discrepancies during the most recent review." The reader must resolve that all three refer to the same entity and the same review, then notice that "met all requirements" contradicts "found three discrepancies."

### 5.6 Affinity Design

**balanced**: The contradiction is equally detectable by graph-based and text-based approaches.

**graph_favoring**: The contradiction is at an entity-relationship boundary — e.g., the same part serial number node connects to two conflicting inspection-result edges. A knowledge graph makes this trivially visible; an LLM reading linearly might miss it.

**agentic_favoring**: The contradiction is embedded in narrative flow, hedging language, or implicit reasoning — e.g., a witness says "I think it was around 9" while another says "it was definitely before 8:30." A graph would need to parse the hedging; an LLM naturally understands the pragmatic implication.

---

## 6. OUTPUT SPECIFICATION

### 6.1 Directory Structure

```
dataset/
  case_001/
    metadata/
      domain_registry.json
      scope_map.json
      entity_mapping.json
      knowledge_graph.json
    anonymized_docs/
      ops_group_report.txt
      structures_group_report.txt
      meteorology_report.txt
      powerplants_report.txt
      maintenance_records_report.txt
      atc_transcript.txt
      witness_testimony_01.txt
      witness_testimony_02.txt
      witness_testimony_03.txt
      manufacturer_submission.txt
      preliminary_report.txt
      final_report.txt
      press_coverage.txt
      regulatory_filing.txt
      internal_memo.txt
    contradictions/
      intra_doc_contradictions.jsonl
      inter_doc_contradictions.jsonl
      all_contradictions.jsonl
    original_claims/
      ops_group_claims.json
      structures_claims.json
      meteorology_claims.json
      ... (one per document)
    validation/
      domain_check_log.json
      rejected_contradictions.jsonl
  case_002/
    ...
  dataset_manifest.json
```

### 6.2 Dataset Manifest

```json
{
  "version": "1.0",
  "total_cases": 25,
  "total_documents": 375,
  "total_contradictions": 1250,
  "contradiction_distribution": {
    "by_scope": {"intra_doc": 500, "inter_doc": 750},
    "by_mechanism": {
      "numeric_drift": 300,
      "entity_swap": 200,
      "causal_inversion": 175,
      "temporal_contradiction": 250,
      "omission_based_implicit": 150,
      "temporal_revision_conflict": 175
    },
    "by_detectability": {"single_hop": 500, "multi_hop": 450, "entity_resolution_dependent": 300},
    "by_difficulty": {"easy": 350, "medium": 500, "hard": 400},
    "by_affinity": {"balanced": 450, "graph_favoring": 400, "agentic_favoring": 400}
  }
}
```

### 6.3 Quality Checklist (per case)

Before finalizing a case, verify:

- [ ] Every document has NTSB boilerplate (docket header, group roster, TOC, lettered sections, page footers)
- [ ] No cross-domain entity contamination (search for engine types, aircraft systems that don't belong to this aircraft)
- [ ] No anachronistic citations (all ADs predate the accident)
- [ ] Aircraft specs are internally consistent across all documents (engine count, type, registration)
- [ ] Each document focuses on its group's domain (Ops doesn't contain metallurgy, Structures doesn't contain weather modeling)
- [ ] Witness testimonies are ≥5,000 words in Q&A format with natural speech patterns
- [ ] Witnesses do NOT cite regulations fluently
- [ ] Factual reports do NOT explain regulations (cite only)
- [ ] All anonymization is consistent across documents (same person → same placeholder everywhere)
- [ ] Contradiction labels have correct char_start/char_end offsets
- [ ] Every contradiction passes the domain registry validation gate
- [ ] Distribution targets are approximately met (mechanism, scope, detectability, difficulty, affinity)
- [ ] No single claim is contradicted more than once (unless intentionally creating a contradiction chain)
- [ ] The `rejected_contradictions.jsonl` log explains why each rejected contradiction failed validation

---

## 7. EXECUTION SEQUENCE

```
For each case_folder in corpus/:

  1. ORCHESTRATOR reads all files
  2. ORCHESTRATOR builds domain_registry.json
  3. ORCHESTRATOR builds scope_map.json
  4. ORCHESTRATOR builds knowledge_graph.json

  5. For each file in case_folder:
     a. DOCUMENT AGENT anonymizes (using shared mapping table)
     b. DOCUMENT AGENT reformats with NTSB boilerplate
     c. DOCUMENT AGENT enforces scope_map (strips out-of-domain content)
     d. DOCUMENT AGENT enforces register rules
     e. DOCUMENT AGENT extracts claims → claims.json
     f. DOCUMENT AGENT injects 2-5 intra-doc contradictions
     g. DOCUMENT AGENT validates each contradiction against domain_registry
     h. DOCUMENT AGENT outputs: anonymized_doc, claims, intra_contradictions

  6. CROSS-DOCUMENT AGENT receives all anonymized docs + all claims + knowledge_graph
  7. CROSS-DOCUMENT AGENT identifies cross-reference sites
  8. CROSS-DOCUMENT AGENT generates inter-doc contradictions (target: 3-8 per case)
  9. CROSS-DOCUMENT AGENT generates cross-witness disagreements
  10. CROSS-DOCUMENT AGENT validates all contradictions against domain_registry
  11. CROSS-DOCUMENT AGENT outputs: inter_contradictions

  12. ORCHESTRATOR merges all contradictions into all_contradictions.jsonl
  13. ORCHESTRATOR runs quality checklist
  14. ORCHESTRATOR outputs final case directory
```

---

## 8. CONSTRAINTS & GUARDRAILS

### 8.1 Hard Rules (never violate)

1. **Domain coherence**: Every entity, component, system, and regulation referenced in a document must be relevant to the accident aircraft type and operation. No turbofan references in turboshaft investigations. No MCAS in non-Boeing-737-MAX reports.
2. **Temporal coherence**: No regulatory action (AD, SB, SAFO) issued after the accident date appears in factual reports. Exception: the final report may reference post-accident regulatory actions in its recommendations section.
3. **Aircraft spec accuracy**: Engine count, engine type, rotor configuration, max weights, performance limits must be factually correct for the aircraft model. These are never contradicted — they are the ground truth that bounds all other contradictions.
4. **Anonymization consistency**: The same real entity always maps to the same anonymized placeholder across all documents in a case.
5. **Register fidelity**: Each document type uses its prescribed tone and style. Factual reports are terse. Testimonies are conversational. Party submissions are defensive-technical.

### 8.2 Soft Guidelines (aim for)

1. Target 2–5 intra-doc contradictions per document, 3–8 inter-doc contradictions per case.
2. Balance the distribution across mechanisms, detectabilities, and difficulties.
3. Prefer contradictions that are meaningful to the investigation (visibility at the time of a VFR-into-IMC accident is more consequential than a typo in a phone number).
4. Make hard contradictions genuinely hard — they should require domain expertise, arithmetic, or multi-document reasoning to detect.
5. Make easy contradictions clearly detectable but still naturalistic — they should look like real clerical errors, not obvious sabotage.
