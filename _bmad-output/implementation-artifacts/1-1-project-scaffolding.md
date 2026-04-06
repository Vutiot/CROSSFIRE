# Story 1.1: Project Scaffolding

Status: done

## Story

As a developer,
I want the complete project directory structure with dependencies and configuration,
so that I can clone the repo, install dependencies, and start building components.

## Acceptance Criteria

1. Running `pip install -r requirements.txt` installs all dependencies successfully
2. `src/crossfire/` package structure exists with `shared/`, `generator/`, `pipeline/`, `evaluation/` directories and `__init__.py` files
3. `.env.example` exists with `OPENAI_API_KEY=your-key-here`
4. `.gitignore` excludes `.env`, `output/`, `__pycache__/`, `*.pyc`
5. `configs/presets/` contains YAML preset files (default, low_connectivity, high_connectivity, stress_test)
6. `output/` directory structure exists (generated/, reports/, evaluation/)
7. `run.py` exists as the entry point skeleton

## Tasks / Subtasks

- [x] Task 1: Create project root files (AC: #1, #3, #4)
  - [x] Create `requirements.txt` with all dependencies
  - [x] Create `.env.example` with API key placeholder
  - [x] Create `.gitignore` with exclusions
  - [x] Create `run.py` entry point skeleton (AC: #7)

- [x] Task 2: Create src/crossfire/ package structure (AC: #2)
  - [x] Create `src/crossfire/__init__.py`
  - [x] Create `src/crossfire/shared/__init__.py`
  - [x] Create `src/crossfire/shared/schemas/__init__.py`
  - [x] Create `src/crossfire/generator/__init__.py`
  - [x] Create `src/crossfire/generator/templates/` directory
  - [x] Create `src/crossfire/pipeline/__init__.py`
  - [x] Create `src/crossfire/pipeline/strategies/__init__.py`
  - [x] Create `src/crossfire/pipeline/baselines/__init__.py`
  - [x] Create `src/crossfire/evaluation/__init__.py`

- [x] Task 3: Create preset configuration files (AC: #5)
  - [x] Create `configs/presets/default.yaml`
  - [x] Create `configs/presets/low_connectivity.yaml`
  - [x] Create `configs/presets/high_connectivity.yaml`
  - [x] Create `configs/presets/stress_test.yaml`
  - [x] Create `configs/example_custom.yaml`

- [x] Task 4: Create output and data directories (AC: #6)
  - [x] Create `output/generated/` with `.gitkeep`
  - [x] Create `output/reports/` with `.gitkeep`
  - [x] Create `output/evaluation/` with `.gitkeep`
  - [x] Create `data/datasets/` directory

- [x] Task 5: Create test structure
  - [x] Create `tests/conftest.py`
  - [x] Create `tests/shared/`, `tests/generator/`, `tests/pipeline/`, `tests/evaluation/` directories
  - [x] Create `notebooks/` directory

- [x] Task 6: Verify (AC: #1)
  - [x] Run `pip install -r requirements.txt` in a clean venv
  - [x] Verify `import crossfire` works from project root
  - [x] Run `pytest` (should collect 0 tests, no errors)

## Dev Notes

### Architecture Compliance (CRITICAL)

All decisions below are from the Architecture Decision Document and MUST be followed exactly.

**Project layout:** `src/crossfire/` — importable package structure. This enables `pip install -e .` in Phase 2.
[Source: architecture.md#Project Structure Decision]

**Python version:** 3.10+ required.
[Source: architecture.md#Architectural Decisions Established by Foundation]

### requirements.txt — Exact Contents

```
openai
networkx
numpy
scipy
scikit-learn
pydantic
loguru
python-dotenv
pyyaml
```

Dev dependencies (separate or commented):
```
pytest
```

Do NOT pin versions for MVP. Do NOT add extras like `black`, `ruff`, `mypy` — linting/type-checking is explicitly skipped.
[Source: architecture.md#Linting & Type Checking]

### .env.example — Exact Contents

```
OPENAI_API_KEY=your-key-here
```

No other env vars needed for MVP.
[Source: architecture.md#Gaps Resolved — API key management via python-dotenv]

### .gitignore — Must Include

```
.env
output/
__pycache__/
*.pyc
*.egg-info/
dist/
build/
.pytest_cache/
notebooks/.ipynb_checkpoints/
```

### Preset Configuration Structure

Each preset YAML in `configs/presets/` must match the `PresetConfig` Pydantic schema (Story 1.2 will define the schema, but the structure is known from the PRD distillate):

**default.yaml:**
```yaml
name: default
description: "Default benchmark configuration — 5 subcorpora, connectivity 2, balanced incoherences"
master_seed: 42
subcorpora_count: 5
docs_per_subcorpus: 80
connectivity_level: 2
doc_type_mix: "balanced"
incoherences:
  scope_distribution:
    intra_doc: 0.2
    intra_corpus: 0.5
    inter_corpus: 0.3
  mechanism: "uniform"
  detectability_distribution:
    single_hop: 0.3
    multi_hop: 0.5
    entity_resolution: 0.2
  system_affinity: "balanced"
  count: "auto"
distractor_ratio: 0.3
```

**low_connectivity.yaml:** Same structure, `connectivity_level: 1`, `system_affinity: "agentic-favoring"`

**high_connectivity.yaml:** Same structure, `connectivity_level: 3`, `system_affinity: "graph-favoring"`

**stress_test.yaml:** Same structure, `subcorpora_count: 10`, `docs_per_subcorpus: 100`, `connectivity_level: 3`

[Source: product-brief-CROSSFIRE-distillate.md#Generator Core API]

### run.py — Entry Point Skeleton

```python
"""CROSSFIRE — Cross-corpus Fact Incoherence Reasoning Evaluation

Entry points for corpus generation, pipeline execution, and evaluation.
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="CROSSFIRE benchmark toolkit")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate corpus
    gen_parser = subparsers.add_parser("generate", help="Generate a benchmark corpus")
    gen_parser.add_argument("--config", required=True, help="Path to preset YAML config")
    gen_parser.add_argument("--output", default="output/generated", help="Output directory")
    gen_parser.add_argument("--dry-run", action="store_true", help="Estimate cost without generating")

    # Run pipeline
    pipe_parser = subparsers.add_parser("pipeline", help="Run auditing pipeline")
    pipe_parser.add_argument("--corpus", required=True, help="Path to corpus directory")
    pipe_parser.add_argument("--mode", choices=["hybrid", "agentic", "graph-native"], required=True)
    pipe_parser.add_argument("--output", default="output/reports", help="Output directory")

    # Run evaluation
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate pipeline results")
    eval_parser.add_argument("--report", required=True, help="Path to pipeline report")
    eval_parser.add_argument("--gold", required=True, help="Path to gold annotations directory")
    eval_parser.add_argument("--output", default="output/evaluation", help="Output directory")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Command dispatch will be implemented in later stories
    print(f"Command '{args.command}' not yet implemented.")


if __name__ == "__main__":
    main()
```

This is a SKELETON only — actual command dispatch will be wired in Stories 2.4 (generate), 4.1 (pipeline), and 5.1 (evaluate). Do NOT implement the commands now.

### Complete Directory Tree to Create

```
crossfire/
├── run.py
├── requirements.txt
├── .env.example
├── .gitignore
├── configs/
│   ├── presets/
│   │   ├── default.yaml
│   │   ├── low_connectivity.yaml
│   │   ├── high_connectivity.yaml
│   │   └── stress_test.yaml
│   └── example_custom.yaml
├── data/
│   └── datasets/
│       └── .gitkeep
├── output/
│   ├── generated/
│   │   └── .gitkeep
│   ├── reports/
│   │   └── .gitkeep
│   └── evaluation/
│       └── .gitkeep
├── src/
│   └── crossfire/
│       ├── __init__.py
│       ├── shared/
│       │   ├── __init__.py
│       │   └── schemas/
│       │       └── __init__.py
│       ├── generator/
│       │   ├── __init__.py
│       │   └── templates/
│       │       └── __init__.py
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── strategies/
│       │   │   └── __init__.py
│       │   └── baselines/
│       │       └── __init__.py
│       └── evaluation/
│           └── __init__.py
├── tests/
│   ├── conftest.py
│   ├── shared/
│   │   └── .gitkeep
│   ├── generator/
│   │   └── .gitkeep
│   ├── pipeline/
│   │   └── .gitkeep
│   └── evaluation/
│       └── .gitkeep
└── notebooks/
    └── .gitkeep
```

### Anti-Patterns to Avoid

- Do NOT create any Pydantic models — that's Story 1.2
- Do NOT implement SeedManager — that's Story 1.3
- Do NOT implement llm_call — that's Story 1.4
- Do NOT add linting configs (ruff, black, mypy, pre-commit) — explicitly skipped for MVP
- Do NOT add a pyproject.toml — using requirements.txt per architecture decision
- Do NOT pin dependency versions — let pip resolve latest compatible
- Do NOT create placeholder implementations in module files — `__init__.py` files should be empty or have minimal package-level imports
- Do NOT use `print()` anywhere — even in run.py skeleton, use it only as temporary placeholder that will be replaced with loguru in Story 1.4

### Project Structure Notes

- All paths relative to project root `crossfire/`
- `src/crossfire/` is the importable package — tests import from `crossfire.*`
- `configs/` is separate from `src/` — configs are user-facing, not package internals
- `data/datasets/` will hold pre-generated gold datasets (Story 6.1)
- `output/` is gitignored runtime output
- `.gitkeep` files in empty directories ensure git tracks the structure

### References

- [Source: architecture.md#Complete Project Directory Structure]
- [Source: architecture.md#Starter Template & Project Foundation]
- [Source: architecture.md#Updated Dependencies]
- [Source: architecture.md#Updated Project Root Files]
- [Source: prd.md#Developer Tool Specific Requirements]
- [Source: product-brief-CROSSFIRE-distillate.md#Generator Core API]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- Task 1: Created all project root files (requirements.txt, .env.example, .gitignore, run.py) with exact contents from architecture specs
- Task 2: Created complete src/crossfire/ package structure with all __init__.py files across shared, generator, pipeline, and evaluation modules
- Task 3: Created 4 preset YAML configs (default, low_connectivity, high_connectivity, stress_test) and example_custom.yaml, all following PresetConfig schema structure
- Task 4: Created output/ (generated, reports, evaluation) and data/datasets/ directories with .gitkeep files
- Task 5: Created test directory structure (tests/conftest.py, test subdirectories with .gitkeep) and notebooks/ directory
- Task 6: Verified pip install succeeds, import crossfire works (via PYTHONPATH=src), and pytest runs without errors
- All 7 acceptance criteria satisfied

### File List

- requirements.txt (new)
- .env.example (new)
- .gitignore (new)
- run.py (new)
- src/crossfire/__init__.py (new)
- src/crossfire/shared/__init__.py (new)
- src/crossfire/shared/schemas/__init__.py (new)
- src/crossfire/generator/__init__.py (new)
- src/crossfire/generator/templates/__init__.py (new)
- src/crossfire/pipeline/__init__.py (new)
- src/crossfire/pipeline/strategies/__init__.py (new)
- src/crossfire/pipeline/baselines/__init__.py (new)
- src/crossfire/evaluation/__init__.py (new)
- configs/presets/default.yaml (new)
- configs/presets/low_connectivity.yaml (new)
- configs/presets/high_connectivity.yaml (new)
- configs/presets/stress_test.yaml (new)
- configs/example_custom.yaml (new)
- output/generated/.gitkeep (new)
- output/reports/.gitkeep (new)
- output/evaluation/.gitkeep (new)
- data/datasets/.gitkeep (new)
- tests/conftest.py (new)
- tests/shared/.gitkeep (new)
- tests/generator/.gitkeep (new)
- tests/pipeline/.gitkeep (new)
- tests/evaluation/.gitkeep (new)
- notebooks/.gitkeep (new)

### Change Log

- 2026-04-06: Story 1.1 implemented — complete project scaffolding with directory structure, dependencies, configuration presets, and entry point skeleton
