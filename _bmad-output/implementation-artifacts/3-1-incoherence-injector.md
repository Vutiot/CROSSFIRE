# Story 3.1: Incoherence Injector

Status: review

## Story

As a researcher,
I want controlled incoherences injected into generated corpora using the 4D design space,
so that the benchmark tests specific detection capabilities with known ground truth.

## Acceptance Criteria

1. Given a generated corpus (from Epic 2) and an incoherence configuration specifying scope_distribution, mechanism, detectability_distribution, system_affinity, and count — when I run the injector — then it modifies existing documents using minimal-pair construction, changing only the target fact, not surrounding prose (FR10)
2. The injector uses the same LLM temperature and prompt structure for both original and modified text to prevent stylistic tells (FR12)
3. Incoherences are distributed across the configured scope axis: intra-document, intra-subcorpus cross-document, inter-subcorpus (FR6)
4. Incoherence mechanisms are applied per configuration: numeric drift, entity swap, causal inversion, temporal contradiction, omission-based implicit, temporal revision conflict (FR7)
5. Detectability levels are distributed per configuration: single-hop, multi-hop, entity-resolution-dependent (FR8)
6. System affinity is applied per configuration: balanced, graph-favoring, agentic-favoring (FR9)
7. Each injected incoherence is tracked with full metadata: scope, mechanism, detectability, system_affinity, source_document_refs, modified_fact, original_fact
8. The injector uses SeedManager for all random selection decisions
9. Injection count is configurable (fixed integer or "auto" for empirical tuning)
10. The injector returns modified corpus documents alongside a list of IncoherenceLabel records

## Tasks / Subtasks

- [x] Task 1: Create `src/crossfire/generator/injector.py` with core `inject_incoherences` function (AC: #1, #8, #9, #10)
  - [x] Define function signature: `inject_incoherences(corpus_dir: Path, config: GeneratorConfig, entity_graph: EntityGraph, seed_mgr: SeedManager, llm=None) -> tuple[list[IncoherenceLabel] | None, str | None]`
  - [x] Load all subcorpus JSONL files from `corpus_dir`, deserialize each line as `Document`
  - [x] Read `IncoherenceConfig` from `config.incoherences` to get scope_distribution, mechanism, detectability_distribution, system_affinity, count
  - [x] Compute injection count: if count is `"auto"`, use heuristic `max(10, total_doc_count // 10)`; if integer, use directly
  - [x] Initialize `random.Random(seed_mgr.get_seed("injector", 0))` for all random decisions
  - [x] Return `(list[IncoherenceLabel], None)` on success or `(None, error)` on failure

- [x] Task 2: Implement scope selection — distribute injections across scope axis (AC: #3)
  - [x] Read `ScopeDistribution` (intra_doc, intra_corpus, inter_corpus) from config
  - [x] Allocate injection count proportionally: `n_intra_doc = round(count * scope_dist.intra_doc)`, etc. — adjust last bucket so total matches count exactly
  - [x] For `intra_doc`: select a single document, identify two facts within it to make contradictory
  - [x] For `intra_corpus` (cross-document within subcorpus): select two documents from the SAME subcorpus that share entity references
  - [x] For `inter_corpus` (cross-subcorpus): select two documents from DIFFERENT subcorpora that reference shared entities (use entity_graph.nodes with multiple subcorpus_memberships)

- [x] Task 3: Implement mechanism selection and application (AC: #4)
  - [x] If `config.incoherences.mechanism == "uniform"`: assign mechanisms uniformly across injections using RNG
  - [x] If mechanism is a specific value (e.g., `"numeric_drift"`): apply that mechanism to all injections
  - [x] `numeric_drift`: identify numeric values (altitudes, speeds, dates, counts) in source fact and change to a different plausible value
  - [x] `entity_swap`: replace an entity reference with a different entity of the same type from entity_graph (e.g., swap one organization for another)
  - [x] `causal_inversion`: reverse a cause-effect relationship (e.g., "failure caused by X" becomes "X resulted from failure" or a contradictory causal chain)
  - [x] `temporal_contradiction`: change temporal ordering or dates to create a timeline conflict
  - [x] `omission_based_implicit`: remove a qualifying statement that makes surrounding facts implicitly contradictory
  - [x] `temporal_revision_conflict`: create conflict between preliminary and final assessments (e.g., preliminary says X, final says not-X)

- [x] Task 4: Implement detectability assignment (AC: #5)
  - [x] Read `DetectabilityDistribution` from config
  - [x] Allocate proportionally (same approach as scope)
  - [x] `single_hop`: incoherence visible by comparing two directly related statements — place contradictory facts in obvious proximity or with direct entity overlap
  - [x] `multi_hop`: incoherence requires combining 3+ pieces of evidence — distribute contradictory facts across multiple documents or embed in complex reasoning chains
  - [x] `entity_resolution_dependent`: incoherence only visible after resolving entity aliases — use alias variants from entity_graph for the entity references in contradictory facts (only effective at connectivity_level >= 2)

- [x] Task 5: Implement system affinity logic (AC: #6)
  - [x] Read `system_affinity` from config (normalize: replace hyphens with underscores for label storage — see Dev Notes)
  - [x] `balanced`: no structural bias — distribute incoherences evenly across document positions and entity patterns
  - [x] `graph_favoring`: place incoherences at entity graph boundaries — target shared entities between subcorpora where KG community detection would find them, but claim-extraction might miss cross-boundary connections
  - [x] `agentic_favoring`: embed incoherences in prose patterns (narrative contradictions, nuanced phrasing) where LLM claim-extraction excels but graph structural analysis would miss them — avoid entity-centric patterns

- [x] Task 6: Implement minimal-pair LLM modification (AC: #1, #2)
  - [x] Create a prompt template that instructs the LLM to modify ONLY the target fact while preserving all surrounding prose
  - [x] The prompt MUST include: original text passage, the specific fact to modify, the mechanism to apply, and explicit instruction to change nothing else
  - [x] Call `llm_call(prompt, model="gpt-4o-mini", temperature=0)` — same model and temperature as corpus generation
  - [x] Parse LLM response to extract: modified passage, the original_fact string, and the modified_fact string
  - [x] Validate: modified text differs from original only in the target fact region — log WARNING if surrounding text also changed
  - [x] Replace the original passage in the Document.content with the modified passage

- [x] Task 7: Build IncoherenceLabel metadata for each injection (AC: #7)
  - [x] For each injection, create an `IncoherenceLabel` with:
    - `id`: deterministic ID derived from SeedManager (e.g., `f"incoherence_{index:04d}"`)
    - `scope`: one of `"intra_doc"`, `"intra_corpus"`, `"inter_corpus"`
    - `mechanism`: the applied mechanism value
    - `detectability`: the assigned detectability level
    - `system_affinity`: normalized value (underscored, not hyphenated)
    - `document_references`: list of document IDs involved
    - `modified_fact`: the new contradictory statement
    - `original_fact`: the original statement that was changed
  - [x] Validate each label against the Pydantic schema before appending

- [x] Task 8: Write modified corpus back to disk (AC: #10)
  - [x] After all injections, write modified documents back to the SAME JSONL files (overwrite originals)
  - [x] Ensure document IDs and all other metadata are preserved — only `content` field changes
  - [x] Log at INFO level: total injections attempted, successful, failed per scope

- [x] Task 9: Write tests in `tests/generator/test_injector.py` (AC: #1-#10)
  - [x] Create `_mock_llm` for tests that returns predictable modified text
  - [x] Create helper to generate a small test corpus (2 subcorpora, 4 docs each) using `_mock_llm` + `generate_corpus`
  - [x] Test: injection produces correct number of IncoherenceLabel records for fixed count
  - [x] Test: injection produces correct number for "auto" count
  - [x] Test: scope distribution matches config proportions (within rounding)
  - [x] Test: each IncoherenceLabel has all required fields populated
  - [x] Test: modified documents differ from originals only in content field
  - [x] Test: document_references in labels point to valid document IDs
  - [x] Test: deterministic — same seed produces identical injections
  - [x] Test: LLM errors are handled gracefully (injection skipped, logged, not crashed)
  - [x] Test: system_affinity normalization (hyphen-to-underscore)
  - [x] Test: all 6 mechanisms can be triggered via config

- [x] Task 10: Run full test suite — no regressions
  - [x] Verify all existing tests still pass alongside new injector tests
  - [x] Verify imports work with `PYTHONPATH=src`

## Dev Notes

### Architecture Compliance

**File location:** `src/crossfire/generator/injector.py` per architecture.md FR6-FR12 mapping.
[Source: architecture.md#Requirements to Structure Mapping]

**Function signature pattern** (follow orchestrator.py):
```python
def inject_incoherences(
    corpus_dir: Path,
    config: GeneratorConfig,
    entity_graph: EntityGraph,
    seed_mgr: SeedManager,
    llm=None,
) -> tuple[list[IncoherenceLabel] | None, str | None]:
```
[Source: architecture.md#Error Handling]

**Error handling:** Return `(result, error)` tuples. Individual injection failures should be logged and skipped, not abort the entire run.
[Source: architecture.md#Error Handling]

**Logging:** loguru only — no print(). Log progress at INFO (injection N of M), failures at WARNING, fatal errors at ERROR.
[Source: architecture.md#Logging]

**Randomness:** All random decisions via `random.Random(seed_mgr.get_seed("injector", index))`. Never call `random.seed()` directly.
[Source: architecture.md#Seeding & Reproducibility]

### Schema Mismatch — CRITICAL

`IncoherenceConfig.system_affinity` in `src/crossfire/shared/schemas/config.py:24` uses **hyphenated** values:
```python
system_affinity: Literal["balanced", "graph-favoring", "agentic-favoring"]
```

`SystemAffinity` in `src/crossfire/shared/schemas/incoherences.py:17` uses **underscored** values:
```python
SystemAffinity = Literal["balanced", "graph_favoring", "agentic_favoring"]
```

**Resolution:** The injector MUST normalize config values before storing in labels. Convert `"graph-favoring"` to `"graph_favoring"` and `"agentic-favoring"` to `"agentic_favoring"`. Use `config_affinity.replace("-", "_")`.

Do NOT change the existing schemas — the config uses hyphens for YAML readability, labels use underscores for Python/JSON convention. Both are intentional.

### IncoherenceConfig.mechanism Field

The `mechanism` field in `IncoherenceConfig` is typed as `str`, not a Literal. The preset configs use `"uniform"` to mean "distribute all 6 mechanisms evenly". The injector must handle:
- `"uniform"` → assign mechanisms via RNG, roughly equal distribution
- A specific mechanism name (e.g., `"numeric_drift"`) → apply that mechanism to all injections
[Source: src/crossfire/shared/schemas/config.py:22]

### Existing Schemas to Import

```python
from crossfire.shared.schemas.incoherences import IncoherenceLabel, Scope, Mechanism, Detectability, SystemAffinity
from crossfire.shared.schemas.config import GeneratorConfig, IncoherenceConfig
from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.entities import EntityGraph, EntityNode
from crossfire.shared.seed_manager import SeedManager
from crossfire.shared.llm import llm_call
```

All schemas are already defined and tested. Do NOT redefine them.
[Source: src/crossfire/shared/schemas/incoherences.py, config.py, corpus.py, entities.py]

### Corpus File Format

Generated corpus is stored as JSONL files at `{output_dir}/subcorpus_sc-{N}.jsonl`. Each line is a serialized `Document`:
```json
{"id": "sc-0_doc_000", "document_type": "investigation_report", "subcorpus_id": "sc-0", "reliability_signal": 0.85, "content": "..."}
```

Entity graph is at `{output_dir}/entity_graph.json` — can be loaded with `EntityGraph.model_validate_json(...)`.
[Source: src/crossfire/generator/orchestrator.py]

### Minimal-Pair Prompt Design

The LLM prompt for fact modification must be carefully designed to prevent stylistic tells (FR12). Key principles:

1. **Same model and temperature** as corpus generation (`gpt-4o-mini`, `temperature=0`)
2. **Prompt structure**: Provide the original passage, identify the target fact, specify the modification type, instruct to preserve ALL surrounding text
3. **Output format**: Ask LLM to return a structured response with `modified_passage`, `original_fact`, and `modified_fact` clearly delineated (use JSON output format for reliable parsing)
4. **Validation**: Compare original and modified passages — if more than the target fact changed, log a WARNING but still use the result (overly strict validation would reduce yield)

### Document Fact Selection Strategy

To select "facts" from documents for modification:
1. Use LLM to extract key factual claims from a document passage (entities, numbers, dates, causal statements)
2. From extracted facts, select one that matches the target mechanism
3. For cross-document incoherences, select facts that reference shared entities (use entity_graph to identify shared entities between target documents)

This is an LLM-intensive operation — each injection requires 2 LLM calls minimum (extract facts + modify fact). For a corpus of 400 docs with 40 injections, expect ~80-120 LLM calls.

### Entity Graph Usage

The entity_graph is critical for:
- `entity_swap` mechanism: provides alternative entities of the same type for swapping
- `inter_corpus` scope: identifies shared entities across subcorpora via `EntityNode.subcorpus_memberships`
- `entity_resolution_dependent` detectability: uses `EntityNode.aliases` to reference entities by different names
- `graph_favoring` affinity: targets entities at subcorpus boundaries (multi-membership nodes)

Access pattern:
```python
# Find shared entities between subcorpora
shared_nodes = [n for n in entity_graph.nodes if len(n.subcorpus_memberships) > 1]

# Find entities in a specific subcorpus
sc_nodes = [n for n in entity_graph.nodes if "sc-0" in n.subcorpus_memberships]

# Get alias for entity resolution difficulty
node.aliases  # list of name variants
```
[Source: src/crossfire/shared/schemas/entities.py, src/crossfire/generator/entity_graph_builder.py]

### Known Deferred Issues

- `ScopeDistribution` and `DetectabilityDistribution` lack sum-to-1.0 validation — the injector should NOT add this validation (it's deferred work). Just use the distribution values as-is for proportional allocation.
- `EntityGraph.to_networkx()` returns undirected `nx.Graph` — the injector does not need NetworkX traversal; use the Pydantic model directly (iterate `entity_graph.nodes` and `entity_graph.edges`).
[Source: _bmad-output/implementation-artifacts/deferred-work.md]

### Previous Story Patterns

**From orchestrator.py** (Story 2.4):
- Injects `llm` as optional parameter, defaults to `llm_call`
- Uses `Path` for file operations
- Writes JSONL with `doc.model_dump_json() + "\n"`
- Reads config fields directly from Pydantic model attributes
- Logs progress at INFO level per subcorpus

**From entity_graph_builder.py** (Story 2.3):
- Uses `random.Random(seed_mgr.get_seed("component_name", 0))` for all randomness
- Helper functions prefixed with `_` for internal use
- Clean separation: data selection → assignment → output

**Test patterns** (from test_orchestrator.py):
- `_mock_llm` function matching `llm_call` signature
- Helper `_make_config` to build test configurations
- Test classes grouping related tests
- `tmp_path` fixture for file output
- Determinism test: run twice with same seed, compare output

### Anti-Patterns to Avoid

- Do NOT use `print()` — use loguru
- Do NOT call `random.seed()` or `random.random()` — use `random.Random(seed_mgr.get_seed(...))`
- Do NOT construct raw dicts for labels — use `IncoherenceLabel(...)` Pydantic model
- Do NOT modify Document schema or add new fields — change only the `content` field
- Do NOT add async/concurrent execution — keep synchronous for MVP
- Do NOT hard-code injection counts — read from config
- Do NOT retry on individual injection LLM failures — skip and log, move to next
- Do NOT import from `crossfire.generator.orchestrator` — the injector runs AFTER orchestrator, no dependency needed

### Project Structure Notes

Files to create:
```
src/crossfire/generator/
├─��� injector.py              # NEW — main incoherence injector

tests/generator/
├── test_injector.py         # NEW — injector tests
```

No other files need modification. The injector is a new module that reads existing corpus output and writes modified versions.

### References

- [Source: architecture.md#Incoherence Injection (FR6-FR12)]
- [Source: architecture.md#Error Handling]
- [Source: architecture.md#Seeding & Reproducibility]
- [Source: architecture.md#Logging]
- [Source: architecture.md#Enforcement Guidelines]
- [Source: epics.md#Story 3.1: Incoherence Injector]
- [Source: prd.md#Incoherence Injection: FR6-FR12]
- [Source: prd.md#Contamination Prevention]
- [Source: src/crossfire/shared/schemas/incoherences.py]
- [Source: src/crossfire/shared/schemas/config.py]
- [Source: src/crossfire/shared/schemas/corpus.py]
- [Source: src/crossfire/shared/schemas/entities.py]
- [Source: src/crossfire/generator/orchestrator.py]
- [Source: src/crossfire/generator/entity_graph_builder.py]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- Task 1: Created `injector.py` with `inject_incoherences()` function. Loads JSONL corpus, computes injection count (fixed or "auto" heuristic), initializes seeded RNG, returns `(list[IncoherenceLabel], error)` tuple.
- Task 2: Implemented `_distribute()` for proportional scope allocation. `_select_targets()` handles all 3 scopes: intra_doc (single doc), intra_corpus (2 docs same subcorpus), inter_corpus (2 docs different subcorpora using shared entities).
- Task 3: `_assign_mechanisms()` handles "uniform" (round-robin + shuffle across all 6) and specific mechanism names. `_mechanism_instruction()` generates LLM prompts per mechanism type. `_filter_facts_for_mechanism()` maps mechanisms to fact types.
- Task 4: Detectability distributed proportionally via same `_distribute()` helper. `_detectability_instruction()` generates LLM guidance for single_hop, multi_hop, and entity_resolution_dependent levels.
- Task 5: System affinity normalized from config hyphens to label underscores via `str.replace("-", "_")`. `_select_targets()` uses affinity to bias scope selection — graph_favoring targets shared entities at subcorpus boundaries.
- Task 6: Two-stage LLM pipeline: `_extract_facts()` extracts factual claims as JSON, `_apply_modification()` applies minimal-pair change. Both use `model="gpt-4o-mini", temperature=0` matching corpus generation. Passage-level fallback if exact fact not found in content.
- Task 7: `IncoherenceLabel` created with deterministic ID (`incoherence_NNNN`), all 4D axes, document references, and original/modified facts. Validated by Pydantic schema at creation.
- Task 8: `_write_corpus()` overwrites original JSONL files with modified documents. All metadata preserved — only content field changes. Summary logged at INFO with per-scope counts.
- Task 9: 28 tests across 8 test classes covering: scaffold (5), scope distribution (2), mechanism selection (3), detectability (2), system affinity (3), labels/metadata (3), disk I/O (2), determinism (1), error handling (1), parametrized mechanism tests (6).
- Task 10: Full suite — 259 tests pass (231 existing + 28 new). No regressions. Imports verified with PYTHONPATH=src.

### File List

- src/crossfire/generator/injector.py (new)
- tests/generator/test_injector.py (new)

### Change Log

- 2026-04-06: Story 3.1 implemented — incoherence injector with 4D design space (scope, mechanism, detectability, system_affinity), minimal-pair LLM construction, full metadata tracking, and 28 tests
