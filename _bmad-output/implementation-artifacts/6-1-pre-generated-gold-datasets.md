# Story 6.1: Pre-Generated Gold Datasets

Status: review

## Story

As a researcher,
I want pre-generated gold datasets included in the repository,
so that I can evaluate my system immediately without running the generator or spending on LLM API calls.

## Acceptance Criteria

1. Given the 4 preset configurations (default, low_connectivity, high_connectivity, stress_test) — when I run the generator with each preset — then each produces a complete dataset in `data/datasets/{preset_name}/` containing corpus JSONL files, gold entity graph JSON, gold incoherence labels JSON, gold distractor labels JSON, and metadata.json with seed, parameters, and version
2. All 4 datasets are committed to the repository (FR30)
3. Each dataset's metadata.json records the exact seed and parameters used, enabling regeneration verification
4. Running the generator with the same preset and seed produces bit-identical output to the committed dataset (NFR1)
5. All datasets pass Pydantic schema validation

## Tasks / Subtasks

- [x] Task 1: Create end-to-end dataset generation script (AC: #1, #3)
  - [x] Create `scripts/generate_dataset.py` that chains: corpus generation → incoherence injection → distractor generation → gold annotation assembly
  - [x] Accept `--config` (preset YAML path), `--output` (dataset output dir) arguments
  - [x] Organize output into architecture-specified structure: `corpus/` (JSONL files), `gold/` (entity graph + labels JSON), `metadata.json` at root
  - [x] Ensure the orchestrator writes corpus JSONL to `{output}/corpus/`, entity graph to `{output}/gold/entity_graph.json`
  - [x] Load entity graph back from disk for injection/distractor steps
  - [x] Run `inject_incoherences()` against `{output}/corpus/` dir
  - [x] Run `generate_distractors()` against `{output}/corpus/` dir with incoherence count
  - [x] Run `assemble_gold_annotations()` to write `gold_incoherence_labels.json` and `gold_distractor_labels.json` to `{output}/gold/`
  - [x] Ensure metadata.json at `{output}/metadata.json` includes full config dump, seed, version, annotation summary

- [x] Task 2: Make generation outputs deterministic and structurally correct (AC: #4)
  - [x] Ensure `generation_timestamp` in metadata.json is NOT included in reproducibility checks (it will differ between runs) — or use a fixed sentinel value for committed datasets
  - [x] Verify SeedManager-derived seeds produce identical entity graphs, documents, incoherences, and distractors across runs
  - [x] Ensure JSONL line ordering is deterministic (sorted by subcorpus index, then document index)
  - [x] Ensure JSON files use `indent=2` and `sort_keys=True` for reproducible serialization

- [x] Task 3: Create batch generation script for all presets (AC: #1, #2)
  - [x] Create `scripts/generate_all_datasets.py` that iterates over all 4 presets in `configs/presets/` (excluding `example_custom.yaml`)
  - [x] For each preset: run full pipeline → write to `data/datasets/{preset_name}/`
  - [x] Log progress and per-preset cost summary
  - [x] Add `--presets` flag to optionally select specific presets (default: all 4)

- [x] Task 4: Create Pydantic schema validation script (AC: #5)
  - [x] Create `scripts/validate_datasets.py` that loads each dataset and validates:
    - All JSONL lines parse as `Document` models
    - `entity_graph.json` parses as `EntityGraph` model
    - `gold_incoherence_labels.json` parses as `list[IncoherenceLabel]`
    - `gold_distractor_labels.json` parses as `list[DistractorLabel]`
    - `metadata.json` is valid JSON with required fields (benchmark_version, master_seed, config, generation_summary, annotation_summary)
  - [x] Report pass/fail per dataset with counts (N documents, N entities, N edges, N incoherences, N distractors)

- [ ] Task 5: Generate and commit all 4 datasets (AC: #1, #2, #3) — REQUIRES LLM API with sufficient rate limits
  - [ ] Run `PYTHONPATH=src:. LLM_MODEL="<model>" python -m scripts.generate_all_datasets` to produce all datasets
  - [ ] Run `PYTHONPATH=src:. python -m scripts.validate_datasets` to confirm all pass
  - [ ] Verify directory structure matches architecture:
    ```
    data/datasets/
    ├── default/
    │   ├── corpus/
    │   │   ├── subcorpus_sc-0.jsonl
    │   │   ├── subcorpus_sc-1.jsonl
    │   │   ├── subcorpus_sc-2.jsonl
    │   │   ├── subcorpus_sc-3.jsonl
    │   │   └── subcorpus_sc-4.jsonl
    │   ├── gold/
    │   │   ├── entity_graph.json
    │   │   ├── gold_incoherence_labels.json
    │   │   └── gold_distractor_labels.json
    │   └── metadata.json
    ├── low_connectivity/
    │   └── (same structure)
    ├── high_connectivity/
    │   └── (same structure)
    └── stress_test/
        └── (same structure — 10 subcorpora)
    ```
  - [ ] Remove `data/datasets/.gitkeep` (no longer needed with actual content)

- [x] Task 6: Create reproducibility verification test (AC: #4)
  - [x] Create `tests/test_dataset_reproducibility.py`
  - [x] Test: load `default` dataset metadata, extract seed and config, regenerate corpus with same params, verify entity graph JSON is identical
  - [x] Test: verify regenerated corpus JSONL files match committed ones (content comparison, ignoring generation_timestamp in metadata)
  - [x] Note: full regeneration test is expensive (LLM calls) — mark with `@pytest.mark.slow` and skip by default. Add `--run-slow` pytest option or use `pytest -m slow` to run explicitly

- [x] Task 7: Write tests for generation scripts (AC: #1, #5)
  - [x] Create `tests/test_generate_dataset.py`
  - [x] Test: generate_dataset with mock LLM produces expected directory structure
  - [x] Test: validate_datasets passes on a well-formed minimal dataset
  - [x] Test: validate_datasets reports errors on a malformed dataset (bad JSON, missing files)

## Dev Notes

### Critical Architecture Gap: run.py Only Calls generate_corpus

The current `run.py` `_run_generate()` only calls `generate_corpus()` from `orchestrator.py`. It does NOT chain:
1. `inject_incoherences()` from `injector.py`
2. `generate_distractors()` from `distractor_generator.py`
3. `assemble_gold_annotations()` from `annotator.py`

The story must create a script that chains all 4 steps. Do NOT modify `orchestrator.py` to include injection/annotation — those are separate concerns (Story 3.x). Instead, create a new script that orchestrates the full pipeline.

### Orchestrator Output Restructuring

The current orchestrator writes everything flat to `output_dir`:
- `entity_graph.json` (flat in output dir)
- `subcorpus_sc-*.jsonl` (flat in output dir)
- `metadata.json` (flat in output dir)

The architecture specifies a nested structure: `corpus/` for JSONL, `gold/` for annotation JSON. The new dataset generation script must either:
- Pass a modified `output_dir` to `generate_corpus()` that points to a temp or corpus subdir, then move files — OR
- Set `config.output_dir` to `{dataset_dir}/corpus/`, then move `entity_graph.json` and `metadata.json` to their correct locations

**Recommended approach:** Set `config.output_dir = {dataset_dir}` (write flat), then reorganize:
1. Move `subcorpus_*.jsonl` → `corpus/`
2. Move `entity_graph.json` → `gold/`
3. Keep `metadata.json` at root
4. After injection/annotation, write gold labels to `gold/`

### Entity Graph Loading for Injection

After corpus generation, the injection and distractor steps need the `EntityGraph` object. The orchestrator doesn't return it, but it writes `entity_graph.json`. Load it back:
```python
from crossfire.shared.schemas.entities import EntityGraph
graph = EntityGraph.model_validate_json(Path(f"{dataset_dir}/gold/entity_graph.json").read_text())
```

### Injection Step Integration

Call sequence after corpus generation:
```python
from crossfire.generator.injector import inject_incoherences
from crossfire.generator.distractor_generator import generate_distractors
from crossfire.generator.annotator import assemble_gold_annotations

# 1. Inject incoherences
labels, error = inject_incoherences(corpus_dir, config, entity_graph, seed_mgr)

# 2. Generate distractors
distractors, error = generate_distractors(corpus_dir, config, entity_graph, len(labels), seed_mgr)

# 3. Assemble gold annotations
summary, error = assemble_gold_annotations(gold_dir, labels, distractors, corpus_dir)
```

### Determinism Concerns

- `generation_timestamp` in `metadata.json` breaks bit-identical comparison. Two options:
  - Option A: Exclude timestamp from reproducibility checks in the test
  - Option B: Use a fixed timestamp for committed datasets and compare everything else
  - **Recommend Option A** — timestamp is informational, not part of the benchmark data

- All other fields must be deterministic:
  - Entity graph: SeedManager controls entity selection, naming, placement
  - Documents: SeedManager controls template dispatch, entity assignment, LLM prompts use temperature 0
  - Incoherences: SeedManager controls target selection, mechanism choice, fact modification
  - Distractors: SeedManager controls divergence type and document selection

### JSON Serialization Determinism

For bit-identical JSON output:
- Use `json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)` consistently
- Pydantic's `model_dump_json(indent=2)` does NOT sort keys by default — may need `json.dumps(model.model_dump(), indent=2, sort_keys=True)`
- Check current orchestrator and annotator serialization — they may not use `sort_keys=True`

### Dataset Size Estimates

| Preset | Subcorpora | Docs/Sub | Total Docs | Approx Size |
|--------|-----------|----------|------------|-------------|
| default | 5 | 80 | 400 | ~2-5 MB |
| low_connectivity | 5 | 80 | 400 | ~2-5 MB |
| high_connectivity | 5 | 80 | 400 | ~2-5 MB |
| stress_test | 10 | 100 | 1,000 | ~5-12 MB |

Total committed data: ~11-27 MB. Acceptable for git.

### LLM Cost Estimate

At ~$5-20 per subcorpus with GPT-4o-mini:
- default: 5 subcorpora × ~$10 = ~$50
- low_connectivity: 5 subcorpora × ~$10 = ~$50
- high_connectivity: 5 subcorpora × ~$10 = ~$50
- stress_test: 10 subcorpora × ~$10 = ~$100

**Total estimated cost: ~$250** for all 4 datasets. This is a one-time cost.

### Existing Code to Reuse

| Component | Location | Usage |
|-----------|----------|-------|
| `generate_corpus()` | `src/crossfire/generator/orchestrator.py` | Core corpus generation |
| `inject_incoherences()` | `src/crossfire/generator/injector.py` | Incoherence injection |
| `generate_distractors()` | `src/crossfire/generator/distractor_generator.py` | Distractor generation |
| `assemble_gold_annotations()` | `src/crossfire/generator/annotator.py` | Gold label assembly |
| `SeedManager` | `src/crossfire/shared/seed_manager.py` | Deterministic seeding |
| `GeneratorConfig` | `src/crossfire/shared/schemas/config.py` | Config parsing |
| `EntityGraph` | `src/crossfire/shared/schemas/entities.py` | Graph deserialization |
| Preset YAML configs | `configs/presets/*.yaml` | Input configurations |

### Anti-Patterns to Avoid

- Do NOT modify `orchestrator.py` to include injection/annotation — keep it focused on corpus generation
- Do NOT use `print()` — use loguru
- Do NOT hardcode preset paths — discover from `configs/presets/` directory
- Do NOT skip schema validation — every output must round-trip through Pydantic
- Do NOT include `generation_timestamp` in bit-identical comparison assertions
- Do NOT use `random.seed()` directly — all randomness through SeedManager
- Do NOT write to `output/` — write to `data/datasets/` for committed datasets

### Project Structure Notes

Files to create:
```
scripts/
├── generate_dataset.py         # NEW — single preset → dataset
├── generate_all_datasets.py    # NEW — all presets → data/datasets/
└── validate_datasets.py        # NEW — Pydantic validation of datasets

tests/
├── test_generate_dataset.py    # NEW — generation script tests
└── test_dataset_reproducibility.py  # NEW — bit-identical reproduction test
```

Files to modify:
```
data/datasets/
├── .gitkeep                    # DELETE — replaced by actual datasets
├── default/                    # NEW — generated dataset
├── low_connectivity/           # NEW — generated dataset
├── high_connectivity/          # NEW — generated dataset
└── stress_test/                # NEW — generated dataset
```

Existing files (read-only reference):
- `src/crossfire/generator/orchestrator.py` — generate_corpus function
- `src/crossfire/generator/injector.py` — inject_incoherences function
- `src/crossfire/generator/distractor_generator.py` — generate_distractors function
- `src/crossfire/generator/annotator.py` — assemble_gold_annotations function
- `src/crossfire/shared/seed_manager.py` — SeedManager class
- `src/crossfire/shared/schemas/config.py` — GeneratorConfig model
- `configs/presets/*.yaml` — preset configurations

### References

- [Source: architecture.md#Project Structure — data/datasets/ layout]
- [Source: architecture.md#Data Architecture — Output Formats]
- [Source: architecture.md#Seeding & Reproducibility — SeedManager]
- [Source: epics.md#Story 6.1: Pre-Generated Gold Datasets]
- [Source: prd.md#FR30 — pre-generated gold datasets]
- [Source: prd.md#FR33 — README for reproduction]
- [Source: prd.md#NFR1 — bit-identical reproduction]
- [Source: src/crossfire/generator/orchestrator.py — generate_corpus function]
- [Source: src/crossfire/generator/injector.py — inject_incoherences function]
- [Source: src/crossfire/generator/distractor_generator.py — generate_distractors function]
- [Source: src/crossfire/generator/annotator.py — assemble_gold_annotations function]
- [Source: configs/presets/default.yaml — preset config structure]
- [Source: _bmad-output/implementation-artifacts/5-5-distractor-evaluation-and-multi-seed-aggregation.md — previous story patterns]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Free-tier OpenRouter (`qwen/qwen3.6-plus:free`) rate limits too aggressive for dataset generation — blocked after single API call. Task 5 deferred to manual execution with paid model.

### Completion Notes List

- Task 1: Created `scripts/generate_dataset.py` — end-to-end pipeline chaining generate_corpus → inject_incoherences → generate_distractors → assemble_gold_annotations. Reorganizes flat orchestrator output into `corpus/` + `gold/` + `metadata.json` structure. Accepts `--config` and `--output` args. Reuses all existing generator functions without modification.
- Task 2: Determinism verified by `test_deterministic_generation` test — same seed produces identical entity graphs, corpus JSONL, gold labels across two runs. metadata.json serialized with `sort_keys=True`. generation_timestamp excluded from comparison.
- Task 3: Created `scripts/generate_all_datasets.py` — iterates 4 presets, generates each to `data/datasets/{name}/`. Supports `--presets` flag for selective generation. Resets LLM usage per preset.
- Task 4: Created `scripts/validate_datasets.py` — validates corpus JSONL (Document), entity_graph.json (EntityGraph), gold labels (IncoherenceLabel/DistractorLabel), metadata.json. Reports per-dataset pass/fail with counts.
- Task 5: PENDING — requires LLM API with sufficient rate limits. All scripts ready; run `PYTHONPATH=src:. LLM_MODEL="<model>" python -m scripts.generate_all_datasets` when API available.
- Task 6: Created `tests/test_dataset_reproducibility.py` — 25 parameterized tests across 4 presets validating schema, structure, metadata. Full reproduction test marked `@pytest.mark.slow`. Tests skip gracefully when datasets not yet generated.
- Task 7: Created `tests/test_generate_dataset.py` — 8 tests: directory structure, corpus JSONL validity, gold annotation files, metadata fields, deterministic generation, validation pass/fail for valid/malformed datasets. All use mock LLM.
- Infrastructure: Added `LLM_MODEL` env var override to `llm.py` for model flexibility. Added OpenRouter API support via `OPENROUTER_API_KEY` env var. Registered `slow` pytest marker. Added `.` to pytest pythonpath for scripts import.
- 435 tests pass, 25 skipped (dataset-dependent), 0 regressions.

### File List

- scripts/__init__.py (new)
- scripts/generate_dataset.py (new)
- scripts/generate_all_datasets.py (new)
- scripts/validate_datasets.py (new)
- tests/test_generate_dataset.py (new)
- tests/test_dataset_reproducibility.py (new)
- src/crossfire/shared/llm.py (modified — added OpenRouter support, LLM_MODEL env override)
- pyproject.toml (modified — added `.` to pythonpath, registered `slow` marker)

### Change Log

- 2026-04-06: Story 6.1 implemented — dataset generation scripts, validation, and tests. Task 5 (actual generation) pending LLM API access.
