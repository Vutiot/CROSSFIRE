# Story 3.2: Distractor Generator

Status: review

## Story

As a researcher,
I want legitimate perspective divergences planted alongside real incoherences,
so that the benchmark measures whether systems can distinguish contradictions from valid disagreements.

## Acceptance Criteria

1. Given a generated corpus and a `distractor_ratio` parameter (e.g., 0.3) — when I run the distractor generator — then it produces perspective divergences that should NOT be flagged as incoherences (FR11)
2. Distractors include: differing expert opinions, preliminary vs final assessments, different measurement methodologies yielding different numbers, legitimate uncertainty expressions
3. The number of distractors is proportional to the configured ratio relative to incoherence count — `distractor_count = round(incoherence_count * distractor_ratio)`
4. Each distractor is tracked as a `DistractorLabel` with document references and divergence type
5. Distractors are indistinguishable in format from real incoherences — the only difference is the gold label
6. The generator uses SeedManager for all random decisions

## Tasks / Subtasks

- [x] Task 1: Create `src/crossfire/generator/distractor_generator.py` with core `generate_distractors` function (AC: #1, #3, #6)
  - [x] Define function signature: `generate_distractors(corpus_dir: Path, config: GeneratorConfig, entity_graph: EntityGraph, incoherence_count: int, seed_mgr: SeedManager, llm=None) -> tuple[list[DistractorLabel] | None, str | None]`
  - [x] Load all subcorpus JSONL files from `corpus_dir` using same pattern as injector (`_load_corpus`)
  - [x] Compute distractor count: `round(incoherence_count * config.distractor_ratio)`
  - [x] Initialize `random.Random(seed_mgr.get_seed("distractor_generator", 0))` for all random decisions
  - [x] Return `(list[DistractorLabel], None)` on success or `(None, error)` on failure

- [x] Task 2: Define divergence types and implement selection (AC: #2)
  - [x] Define 4 divergence types as constants: `"expert_opinion"`, `"preliminary_vs_final"`, `"measurement_methodology"`, `"uncertainty_expression"`
  - [x] Distribute divergence types approximately evenly across distractors using RNG
  - [x] For `expert_opinion`: generate a plausible difference of interpretation between experts (e.g., two investigators disagree on root cause)
  - [x] For `preliminary_vs_final`: generate a preliminary finding that legitimately differs from the final conclusion (e.g., early suspicion later ruled out)
  - [x] For `measurement_methodology`: generate different but valid numbers from different measurement approaches (e.g., radar altitude vs barometric altitude)
  - [x] For `uncertainty_expression`: generate hedged/qualified statements that express legitimate uncertainty (e.g., "approximately", "estimated", "may have contributed")

- [x] Task 3: Implement LLM-based distractor generation (AC: #1, #5)
  - [x] Select target documents for each distractor — distribute across subcorpora
  - [x] Create LLM prompt that generates a legitimate perspective divergence, NOT a factual contradiction
  - [x] The prompt MUST instruct the LLM to: add the divergence naturally into the document, keep the divergence clearly within the bounds of legitimate professional disagreement, use the same style/voice as the document
  - [x] Call `llm_call(prompt, model="gpt-4o-mini", temperature=0)` — same model and temperature as injector
  - [x] Parse LLM response to extract: modified passage and a description of the divergence
  - [x] Apply the modification to the target document's content

- [x] Task 4: Build DistractorLabel metadata for each distractor (AC: #4)
  - [x] For each distractor, create a `DistractorLabel` with:
    - `id`: deterministic ID (e.g., `f"distractor_{index:04d}"`)
    - `scope`: scope of the divergence (intra_doc or intra_corpus — use same Scope type as incoherences)
    - `document_references`: list of document IDs involved
    - `divergence_type`: one of the 4 types defined in Task 2
    - `description`: human-readable description of the divergence
  - [x] Validate each label against the Pydantic schema before appending

- [x] Task 5: Write modified corpus back to disk (AC: #5)
  - [x] After all distractors are generated, write modified documents back to JSONL files (overwrite)
  - [x] Ensure document IDs and all metadata are preserved — only `content` field changes
  - [x] Log at INFO level: total distractors attempted, successful, failed, and per-type counts

- [x] Task 6: Write tests in `tests/generator/test_distractor_generator.py` (AC: #1-#6)
  - [x] Create `_mock_llm` for tests that returns predictable distractor text
  - [x] Create helper to generate a small test corpus (reuse pattern from test_injector.py)
  - [x] Test: distractor count matches `round(incoherence_count * distractor_ratio)`
  - [x] Test: each DistractorLabel has all required fields populated
  - [x] Test: all 4 divergence types appear when count >= 4
  - [x] Test: document_references point to valid document IDs
  - [x] Test: deterministic — same seed produces identical distractors
  - [x] Test: LLM errors handled gracefully (distractor skipped, not crashed)
  - [x] Test: zero distractor_ratio produces empty list
  - [x] Test: modified documents written back to disk correctly

- [x] Task 7: Run full test suite — no regressions
  - [x] Verify all existing tests (259) still pass alongside new distractor tests
  - [x] Verify imports work with `PYTHONPATH=src`

## Dev Notes

### Architecture Compliance

**File location:** `src/crossfire/generator/distractor_generator.py` per architecture.md FR11/FR15 mapping.
[Source: architecture.md#Requirements to Structure Mapping]

**Function signature pattern** (follow injector.py):
```python
def generate_distractors(
    corpus_dir: Path,
    config: GeneratorConfig,
    entity_graph: EntityGraph,
    incoherence_count: int,
    seed_mgr: SeedManager,
    llm=None,
) -> tuple[list[DistractorLabel] | None, str | None]:
```
[Source: architecture.md#Error Handling]

**Error handling:** Return `(result, error)` tuples. Individual distractor failures logged and skipped.
[Source: architecture.md#Error Handling]

**Logging:** loguru only — no print(). Progress at INFO, failures at WARNING.
[Source: architecture.md#Logging]

**Randomness:** `random.Random(seed_mgr.get_seed("distractor_generator", 0))`. Never call `random.seed()` directly.
[Source: architecture.md#Seeding & Reproducibility]

### Existing DistractorLabel Schema

The schema is already defined in `src/crossfire/shared/schemas/incoherences.py:31`:

```python
class DistractorLabel(BaseModel):
    id: str
    scope: Scope  # Literal["intra_doc", "intra_corpus", "inter_corpus"]
    document_references: list[str]
    divergence_type: str
    description: str
```

Note: `divergence_type` is `str` (not a Literal) — the 4 divergence types are convention, not enforced by schema. This is intentional per the existing design.

Do NOT modify this schema. Import it:
```python
from crossfire.shared.schemas.incoherences import DistractorLabel, Scope
```
[Source: src/crossfire/shared/schemas/incoherences.py]

### Relationship to Injector (Story 3.1)

The distractor generator runs AFTER the injector. It takes `incoherence_count` as input to compute distractor count. The calling sequence in the pipeline will be:

1. `generate_corpus()` → produces corpus + entity graph
2. `inject_incoherences()` → modifies corpus, returns `list[IncoherenceLabel]`
3. `generate_distractors(corpus_dir, config, entity_graph, len(incoherence_labels), seed_mgr)` → modifies corpus again, returns `list[DistractorLabel]`

The distractor generator operates on the ALREADY-MODIFIED corpus (after incoherence injection). This is important — distractors should be placed in documents that may already have injected incoherences.

### Patterns to Reuse from Injector (Story 3.1)

The injector established these patterns that the distractor generator MUST follow:

**Corpus loading:** Use `_load_corpus()` pattern — glob `subcorpus_*.jsonl`, deserialize each line as `Document`.

**Corpus writing:** Use `_write_corpus()` pattern — overwrite JSONL files, preserving all document metadata.

**LLM interaction:** Two-stage JSON pipeline — extract context, then generate modification. Use `json.loads()` for parsing with error handling.

**Document modification:** Modify `Document.content` directly on the in-memory object, then write all docs back.

**Error handling:** Per-distractor try/skip pattern. Log failures at WARNING, count them, continue to next.

**Important:** Do NOT import from `crossfire.generator.injector`. Duplicate the small helper patterns (corpus load/write) rather than coupling the modules. They may diverge independently.
[Source: src/crossfire/generator/injector.py]

### Distractor vs Incoherence — Critical Distinction

Distractors must be **legitimate** divergences, NOT factual contradictions:
- **Expert opinion**: "Investigator A attributed the failure to metal fatigue, while Investigator B suggested manufacturing defect" — both are valid professional opinions
- **Preliminary vs final**: "Preliminary findings suggested pilot error" followed by "Final analysis identified mechanical failure" — this is normal investigation evolution, not contradiction
- **Measurement methodology**: "Radar indicated altitude of 16,200 feet" vs "Barometric reading showed 16,450 feet" — different instruments, both valid
- **Uncertainty expression**: "The component may have been compromised" vs "Evidence suggests the component was intact" — qualified vs definitive, legitimate ambiguity

The key distinction from incoherences: a well-functioning auditing system should NOT flag these as contradictions.

### Config Fields

- `config.distractor_ratio`: `float` (e.g., 0.3 means 30% of incoherence count)
- Default preset uses 0.3

Formula: `distractor_count = round(incoherence_count * config.distractor_ratio)`
- If incoherence_count=40 and ratio=0.3: 12 distractors
- If ratio=0: no distractors (valid use case — test without distractors)
[Source: src/crossfire/shared/schemas/config.py, configs/presets/default.yaml]

### Previous Story Learnings (Story 3.1)

- Two-stage LLM pipeline (extract + modify) works well for structured modifications
- JSON output format from LLM is reliable when the prompt explicitly says "Return ONLY valid JSON"
- `_distribute()` helper is useful for proportional allocation — can be replicated for divergence type distribution
- `random.Random(seed_mgr.get_seed(...))` pattern ensures reproducibility
- Passage-level fallback is needed when exact text match fails
- 28 tests with parametrized mechanism tests was a good coverage pattern
- Test helper `_create_test_corpus()` creates 2 subcorpora × 4 docs — reuse this pattern

### Anti-Patterns to Avoid

- Do NOT use `print()` — use loguru
- Do NOT call `random.seed()` or `random.random()` — use `random.Random(seed_mgr.get_seed(...))`
- Do NOT construct raw dicts for labels — use `DistractorLabel(...)` Pydantic model
- Do NOT modify Document schema — change only `content` field
- Do NOT import from `crossfire.generator.injector` — keep modules independent
- Do NOT generate factual contradictions — distractors are LEGITIMATE divergences
- Do NOT couple to incoherence injection order — distractor generator reads whatever corpus state exists

### Project Structure Notes

Files to create:
```
src/crossfire/generator/
├── distractor_generator.py    # NEW — distractor generator

tests/generator/
├── test_distractor_generator.py  # NEW — distractor tests
```

No other files need modification.

### References

- [Source: architecture.md#Incoherence Injection (FR6-FR12) — includes FR11 distractor labels]
- [Source: architecture.md#Error Handling]
- [Source: architecture.md#Seeding & Reproducibility]
- [Source: architecture.md#Logging]
- [Source: architecture.md#Enforcement Guidelines]
- [Source: epics.md#Story 3.2: Distractor Generator]
- [Source: prd.md#Annotation Policy — distractor labels]
- [Source: src/crossfire/shared/schemas/incoherences.py — DistractorLabel schema]
- [Source: src/crossfire/shared/schemas/config.py — distractor_ratio field]
- [Source: src/crossfire/generator/injector.py — patterns to follow]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- Task 1: Created `distractor_generator.py` with `generate_distractors()` function. Takes corpus_dir, config, entity_graph, incoherence_count, seed_mgr, llm. Computes count as `round(incoherence_count * distractor_ratio)`. Returns `(list[DistractorLabel], error)` tuple. Zero ratio returns empty list immediately.
- Task 2: Defined 4 divergence types as module constants. `_assign_divergence_types()` distributes via round-robin then shuffle for randomized but even coverage. `_divergence_instruction()` generates type-specific LLM prompts with NTSB-grounded examples.
- Task 3: Single-stage LLM pipeline — prompt instructs to add a legitimate divergence naturally. `_select_targets()` distributes across scopes (50% intra_doc, 35% intra_corpus, 15% inter_corpus). JSON output parsed for modified_passage and description.
- Task 4: `DistractorLabel` created with deterministic ID (`distractor_NNNN`), scope, doc references, divergence_type, and description. Validated by Pydantic at creation.
- Task 5: `_write_corpus()` overwrites JSONL files preserving all document metadata. Per-type counts logged at INFO.
- Task 6: 14 tests across 6 classes: scaffold (5), divergence types (2), labels (3), disk I/O (2), determinism (1), error handling (1).
- Task 7: Full suite — 273 tests pass (259 existing + 14 new). No regressions.

### File List

- src/crossfire/generator/distractor_generator.py (new)
- tests/generator/test_distractor_generator.py (new)

### Change Log

- 2026-04-06: Story 3.2 implemented — distractor generator with 4 divergence types, LLM-based generation, DistractorLabel tracking, and 14 tests
