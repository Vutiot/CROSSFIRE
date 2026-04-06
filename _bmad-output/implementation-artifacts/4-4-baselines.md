# Story 4.4: Baselines

Status: review

## Story

As a researcher,
I want trivial and hypothesis-only baselines,
so that I can establish lower bounds and validate that the benchmark isn't solvable by shortcuts.

## Acceptance Criteria

1. Given the baselines module at `src/crossfire/pipeline/baselines/` — when I run `random_baseline.py` against a corpus — then it produces a `PipelineReport` with randomly flagged document pairs as incoherences, using SeedManager for reproducibility (FR22)
2. When I run `bm25_baseline.py` against a corpus — then it uses BM25 keyword matching to find contradictory passages and produces a `PipelineReport` (FR22)
3. When I run `hypothesis_only.py` against a corpus — then it evaluates whether incoherences are detectable from surface features alone (document length, vocabulary, formatting) without reading content (FR21) — and produces a `PipelineReport`
4. If hypothesis-only scores are significantly above random, this indicates contamination in the generated corpus
5. All baselines output reports in the same standardized format as the main pipeline (FR20)

## Tasks / Subtasks

- [x] Task 1: Create `src/crossfire/pipeline/baselines/random_baseline.py` (AC: #1, #5)
  - [x] `run_random_baseline(corpus_path, seed_manager, detection_rate)` — randomly flag document pairs
  - [x] SeedManager for reproducibility
  - [x] Return standardized `PipelineReport`

- [x] Task 2: Create `src/crossfire/pipeline/baselines/bm25_baseline.py` (AC: #2, #5)
  - [x] `run_bm25_baseline(corpus_path, seed_manager, top_k)` — TF-IDF keyword matching with contradiction signal boost
  - [x] Purely computational (no LLM calls)
  - [x] Return standardized `PipelineReport`

- [x] Task 3: Create `src/crossfire/pipeline/baselines/hypothesis_only.py` (AC: #3, #4, #5)
  - [x] `run_hypothesis_only_baseline(corpus_path, seed_manager, top_k)` — surface feature extraction and divergence scoring
  - [x] Features: word count, unique ratio, avg word length, avg sentence length, paragraph count, digit ratio, upper ratio
  - [x] Return standardized `PipelineReport`

- [x] Task 4: Update `baselines/__init__.py` with exports

- [x] Task 5: Write tests in `tests/pipeline/test_baselines.py` (AC: #1-#5)
  - [x] Test each baseline: valid report, valid fields, deterministic, error handling
  - [x] Test standardized format: all baselines produce PipelineReport with DetectedIncoherence entries

- [x] Task 6: Run full test suite — no regressions

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Completion Notes List

- Task 1: Random baseline — SeedManager-seeded random document pair selection with configurable detection rate. Deterministic output.
- Task 2: BM25 baseline — TF-IDF keyword overlap scoring with contradiction signal boost (asymmetric negation word detection). No LLM calls.
- Task 3: Hypothesis-only baseline — extracts 7 surface features per document (word count, unique ratio, avg word/sentence length, paragraph count, digit/upper ratios). Scores pairs by normalized Euclidean feature divergence.
- Task 4: Updated baselines/__init__.py with exports.
- Task 5: 15 tests across 5 classes covering all baselines + standardized format verification.
- Task 6: 339 tests pass (zero regressions).

### File List

- src/crossfire/pipeline/baselines/__init__.py (modified)
- src/crossfire/pipeline/baselines/random_baseline.py (new)
- src/crossfire/pipeline/baselines/bm25_baseline.py (new)
- src/crossfire/pipeline/baselines/hypothesis_only.py (new)
- tests/pipeline/test_baselines.py (new)

### Change Log

- 2026-04-06: Story 4.4 implemented — random, BM25, and hypothesis-only baselines with 15 tests
