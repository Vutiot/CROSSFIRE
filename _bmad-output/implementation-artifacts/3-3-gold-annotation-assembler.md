# Story 3.3: Gold Annotation Assembler

Status: review

## Story

As a researcher,
I want complete, versioned gold annotations produced alongside every generated corpus,
so that evaluation has reliable ground truth with full traceability.

## Acceptance Criteria

1. Given a corpus with injected incoherences (Story 3.1) and distractors (Story 3.2) — when I run the gold annotation assembler — then it produces a gold incoherence labels JSON file containing every injected incoherence with scope, mechanism, detectability, system_affinity, and document references (FR14)
2. It produces a gold distractor labels JSON file identifying every legitimate divergence (FR15)
3. Both files validate against their respective Pydantic schemas (`IncoherenceLabel`, `DistractorLabel`)
4. `metadata.json` is updated with a `version` field — label corrections trigger a new version identifier (FR16)
5. The assembler cross-validates: every incoherence in the labels file corresponds to an actual modification in the corpus documents (modified_fact text exists in some document)
6. The assembler logs total counts at INFO level: N incoherences (X intra-doc, Y intra-subcorpus, Z inter-subcorpus), M distractors

## Tasks / Subtasks

- [x] Task 1: Create `src/crossfire/generator/annotator.py` with core `assemble_gold_annotations` function (AC: #1, #2, #3)
  - [x] Define function signature: `assemble_gold_annotations(output_dir: Path, incoherence_labels: list[IncoherenceLabel], distractor_labels: list[DistractorLabel], corpus_dir: Path, version: str = "1.0") -> tuple[dict | None, str | None]`
  - [x] Serialize `incoherence_labels` to JSON using Pydantic `model_dump()` and write to `output_dir/gold_incoherence_labels.json`
  - [x] Serialize `distractor_labels` to JSON using Pydantic `model_dump()` and write to `output_dir/gold_distractor_labels.json`
  - [x] Return `(summary_dict, None)` on success or `(None, error)` on failure

- [x] Task 2: Implement cross-validation (AC: #5)
  - [x] Load all corpus documents from `corpus_dir` (glob `subcorpus_*.jsonl`)
  - [x] For each `IncoherenceLabel`, verify that `modified_fact` text appears in at least one document whose ID is in `document_references`
  - [x] Log WARNING for any incoherence label that fails cross-validation but do NOT remove it — the label is still valid, just potentially a sign of a prior-stage issue
  - [x] Return cross-validation results as part of the summary

- [x] Task 3: Update metadata.json with version field (AC: #4)
  - [x] Load existing `output_dir/metadata.json` if it exists
  - [x] Add or update the `version` field with the provided version string
  - [x] Add `annotation_summary` to metadata with counts from the assembler
  - [x] Write updated metadata back to disk

- [x] Task 4: Log summary counts (AC: #6)
  - [x] Count incoherences by scope: intra_doc, intra_corpus, inter_corpus
  - [x] Count total distractors
  - [x] Log at INFO level: "Gold annotations: N incoherences (X intra_doc, Y intra_corpus, Z inter_corpus), M distractors"
  - [x] Log cross-validation results: "Cross-validation: P/N incoherences verified in corpus"

- [x] Task 5: Write tests in `tests/generator/test_annotator.py` (AC: #1-#6)
  - [x] Create test helpers: sample IncoherenceLabel list, sample DistractorLabel list, sample corpus
  - [x] Test: gold_incoherence_labels.json is written and validates against schema
  - [x] Test: gold_distractor_labels.json is written and validates against schema
  - [x] Test: both JSON files are loadable and round-trip through Pydantic
  - [x] Test: metadata.json is updated with version field and annotation_summary
  - [x] Test: cross-validation passes when modified_fact exists in corpus
  - [x] Test: cross-validation warns when modified_fact is missing from corpus
  - [x] Test: summary counts are correct (per-scope incoherence breakdown + distractor total)
  - [x] Test: empty label lists produce valid (empty array) JSON files
  - [x] Test: function returns error when output_dir does not exist

- [x] Task 6: Run full test suite — no regressions
  - [x] Verify all existing tests (273) still pass alongside new annotator tests
  - [x] Verify imports work with `PYTHONPATH=src`

## Dev Notes

### Architecture Compliance

**File location:** `src/crossfire/generator/annotator.py` per architecture.md FR14/FR15 mapping.
[Source: architecture.md#Requirements to Structure Mapping]

**Function signature pattern:**
```python
def assemble_gold_annotations(
    output_dir: Path,
    incoherence_labels: list[IncoherenceLabel],
    distractor_labels: list[DistractorLabel],
    corpus_dir: Path,
    version: str = "1.0",
) -> tuple[dict | None, str | None]:
```
[Source: architecture.md#Error Handling]

**Error handling:** Return `(result, error)` tuples. Cross-validation failures are warnings, not errors.
[Source: architecture.md#Error Handling]

**Logging:** loguru only. Counts at INFO, validation issues at WARNING.
[Source: architecture.md#Logging]

### This Story Does NOT Use LLM

The annotator is a pure data assembly and validation module. It takes the already-computed label lists from Stories 3.1 and 3.2 and writes them to JSON files. No LLM calls needed.

### Output File Format

**gold_incoherence_labels.json:**
```json
[
  {
    "id": "incoherence_0000",
    "scope": "intra_doc",
    "mechanism": "numeric_drift",
    "detectability": "single_hop",
    "system_affinity": "balanced",
    "document_references": ["sc-0_doc_000"],
    "modified_fact": "The aircraft was traveling at 280 knots",
    "original_fact": "The aircraft was traveling at 450 knots"
  }
]
```

**gold_distractor_labels.json:**
```json
[
  {
    "id": "distractor_0000",
    "scope": "intra_doc",
    "document_references": ["sc-0_doc_001"],
    "divergence_type": "expert_opinion",
    "description": "Different expert interpretation of root cause"
  }
]
```

Both are JSON arrays of Pydantic-serialized models. Use `[label.model_dump() for label in labels]` then `json.dumps(..., indent=2)`.
[Source: architecture.md#Data Architecture — Output Formats]

### Metadata.json Update

The orchestrator (Story 2.4) already creates `metadata.json` with:
```json
{
  "benchmark_version": "1.0",
  "generation_timestamp": "...",
  "master_seed": 42,
  "config": {...},
  "generation_summary": {...}
}
```

The annotator MUST:
1. Load existing metadata.json
2. Add/update `version` field (FR16 — benchmark version identifier)
3. Add `annotation_summary` with label counts
4. Preserve all existing fields

Result:
```json
{
  "benchmark_version": "1.0",
  "generation_timestamp": "...",
  "master_seed": 42,
  "config": {...},
  "generation_summary": {...},
  "version": "1.0",
  "annotation_summary": {
    "total_incoherences": 40,
    "incoherences_by_scope": {"intra_doc": 8, "intra_corpus": 20, "inter_corpus": 12},
    "total_distractors": 12,
    "cross_validation_passed": 38,
    "cross_validation_failed": 2
  }
}
```
[Source: src/crossfire/generator/orchestrator.py — metadata format]

### Cross-Validation Logic

For each `IncoherenceLabel`:
1. Get the `document_references` list (document IDs)
2. Look up those documents in the corpus JSONL files
3. Check if `modified_fact` string appears in any referenced document's `content`
4. If found: cross-validation passes
5. If not found: log WARNING — may indicate the injector's passage-level fallback was used, or the modification didn't apply cleanly

This is a best-effort validation. A failing check is a WARNING, not an error — the label is still correct metadata about what was attempted.

### Existing Schemas

```python
from crossfire.shared.schemas.incoherences import IncoherenceLabel, DistractorLabel
from crossfire.shared.schemas.corpus import Document
```

All already defined and tested. Do NOT modify.
[Source: src/crossfire/shared/schemas/incoherences.py]

### Previous Story Learnings (Stories 3.1, 3.2)

- Corpus JSONL files at `corpus_dir/subcorpus_sc-{N}.jsonl`, each line is a `Document`
- `Document.model_validate_json(line)` for deserialization
- `label.model_dump()` for Pydantic → dict serialization
- `json.dumps(data, indent=2)` for readable JSON output
- Injector uses passage-level fallback when exact fact not found — cross-validation may fail for those cases (expected)
- 273 tests currently pass — do not break them

### Anti-Patterns to Avoid

- Do NOT use `print()` — use loguru
- Do NOT construct raw dicts — use Pydantic `model_dump()`
- Do NOT fail on cross-validation mismatches — log WARNING and continue
- Do NOT modify existing metadata fields — only add new ones
- Do NOT re-read labels from the JSON files for validation — validate the in-memory Pydantic models directly
- Do NOT import from injector or distractor_generator — the annotator is independent

### Project Structure Notes

Files to create:
```
src/crossfire/generator/
├── annotator.py            # NEW — gold annotation assembler

tests/generator/
├── test_annotator.py       # NEW — annotator tests
```

No other files need modification.

### References

- [Source: architecture.md#Gold Annotation (FR13-FR16)]
- [Source: architecture.md#Data Architecture — Output Formats]
- [Source: architecture.md#Error Handling]
- [Source: architecture.md#Logging]
- [Source: epics.md#Story 3.3: Gold Annotation Assembler]
- [Source: prd.md#Gold Annotation: FR14-FR16]
- [Source: prd.md#Annotation Policy]
- [Source: src/crossfire/shared/schemas/incoherences.py]
- [Source: src/crossfire/generator/orchestrator.py — metadata.json format]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- Task 1: Created `annotator.py` with `assemble_gold_annotations()`. Serializes IncoherenceLabel and DistractorLabel lists to JSON via Pydantic `model_dump()`. Writes `gold_incoherence_labels.json` and `gold_distractor_labels.json`. Returns `(summary, error)` tuple.
- Task 2: `_cross_validate()` loads all corpus docs indexed by ID, checks that each label's `modified_fact` appears in referenced documents. Failures logged at WARNING — labels kept regardless. Returns (passed, failed) counts.
- Task 3: `_update_metadata()` loads existing metadata.json if present, adds `version` and `annotation_summary` fields, preserves all existing fields, writes back.
- Task 4: Summary counts computed: total incoherences, per-scope breakdown, total distractors, cross-validation results. All logged at INFO.
- Task 5: 11 tests across 4 classes: assembler (5), cross-validation (2), metadata (3), summary (1). Covers JSON round-trip, empty lists, missing dirs, cross-validation pass/fail, metadata preservation.
- Task 6: Full suite — 284 tests pass (273 existing + 11 new). No regressions.

### File List

- src/crossfire/generator/annotator.py (new)
- tests/generator/test_annotator.py (new)

### Change Log

- 2026-04-06: Story 3.3 implemented — gold annotation assembler with cross-validation, metadata versioning, and 11 tests
