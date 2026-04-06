# Story 1.3: Centralized SeedManager

Status: done

## Story

As a researcher,
I want deterministic, reproducible execution controlled by a single master seed,
so that identical parameters produce identical results across runs and machines.

## Acceptance Criteria

1. `SeedManager` initialized with `master_seed=42` accepts an integer master seed
2. `get_seed("generator", 0)` and `get_seed("pipeline", 0)` each return a deterministic integer derived from the master seed + component name + index
3. The same master_seed always produces the same derived seeds across multiple instantiations
4. Different component names produce different seeds (no collision)
5. `SeedManager` is importable from `src/crossfire/shared/seed_manager.py`
6. Seed values are logged at INFO level via loguru at initialization
7. pytest tests verify determinism across multiple instantiations

## Tasks / Subtasks

- [x] Task 1: Create `src/crossfire/shared/seed_manager.py` (AC: #1, #2, #4, #5)
  - [x] Implement `SeedManager.__init__(self, master_seed: int)` storing master_seed
  - [x] Implement `get_seed(self, component: str, index: int = 0) -> int` using deterministic derivation: `hash((master_seed, component, index)) % (2**32)`
  - [x] Ensure derived seeds are deterministic integers within 32-bit unsigned range
  - [x] Add loguru INFO log of master_seed at initialization (AC: #6)

- [x] Task 2: Write determinism tests (AC: #3, #7)
  - [x] Test: same master_seed + same component + same index → same seed across multiple SeedManager instances
  - [x] Test: different component names → different seeds (no collision for common component names)
  - [x] Test: different indices → different seeds for same component
  - [x] Test: different master_seeds → different derived seeds

- [x] Task 3: Write edge case and integration tests
  - [x] Test: index defaults to 0 when not provided
  - [x] Test: seed values are within valid 32-bit unsigned range (0 to 2^32-1)
  - [x] Test: loguru INFO message is emitted at initialization (capture log output)
  - [x] Test: import from `crossfire.shared.seed_manager` works

- [x] Task 4: Verify and run full test suite
  - [x] Run all tests — no regressions from Story 1.1 and 1.2
  - [x] Verify `SeedManager` is importable with `PYTHONPATH=src`

## Dev Notes

### Architecture Compliance (CRITICAL)

**Exact implementation pattern from architecture document:**

```python
class SeedManager:
    def __init__(self, master_seed: int):
        self.master_seed = master_seed

    def get_seed(self, component: str, index: int = 0) -> int:
        # Deterministic derivation from master + component name + index
        return hash((self.master_seed, component, index)) % (2**32)
```

[Source: architecture.md#Seeding & Reproducibility]

**CRITICAL — Python hash determinism:** Python's built-in `hash()` is NOT deterministic across Python sessions by default (PYTHONHASHSEED randomization since Python 3.3). To guarantee cross-run reproducibility (NFR1), use `hashlib` instead:

```python
import hashlib

def get_seed(self, component: str, index: int = 0) -> int:
    key = f"{self.master_seed}:{component}:{index}"
    return int(hashlib.sha256(key.encode()).hexdigest(), 16) % (2**32)
```

This ensures bit-identical seeds across runs, machines, and OS versions. The architecture doc shows `hash()` as pseudocode — the implementation MUST use a deterministic hash function.

**Enforcement rules:**
- Every component receives its seed from SeedManager, never from `random.seed()` directly
- SeedManager is instantiated once per generation/pipeline run from config
- Seed is logged in output metadata for reproducibility verification
[Source: architecture.md#Seeding & Reproducibility]

### Logging

Use `loguru` for the INFO log at initialization. loguru is already in `requirements.txt`.

```python
from loguru import logger

class SeedManager:
    def __init__(self, master_seed: int):
        self.master_seed = master_seed
        logger.info(f"SeedManager initialized with master_seed={master_seed}")
```

[Source: architecture.md#Logging]

### File Location

`src/crossfire/shared/seed_manager.py` — this is a standalone module in the shared package, NOT inside `schemas/`.
[Source: architecture.md#Complete Project Directory Structure]

### Previous Story (1.2) Learnings

- All Pydantic schemas are in `src/crossfire/shared/schemas/` — SeedManager is separate at `src/crossfire/shared/seed_manager.py`
- Tests run with `PYTHONPATH=src pytest` from project root
- Test files go in `tests/shared/` (e.g., `tests/shared/test_seed_manager.py`)
- 60 existing tests pass — do not break them

### Anti-Patterns to Avoid

- Do NOT use Python's built-in `hash()` — it is NOT deterministic across sessions (PYTHONHASHSEED)
- Do NOT use `random.seed()` inside SeedManager — the point is to derive seeds for others to use
- Do NOT make SeedManager a singleton or global — it's instantiated per run and injected
- Do NOT add numpy or scipy dependency for seeding — use hashlib from stdlib
- Do NOT implement any consumer logic — SeedManager only produces seeds, consumers use them
- Do NOT add any methods beyond `__init__` and `get_seed` — keep it minimal

### Testing Strategy

Test file: `tests/shared/test_seed_manager.py`

Key test patterns:
1. **Determinism:** Create two SeedManager instances with same seed, verify `get_seed()` returns identical values
2. **Collision avoidance:** Common component names ("generator", "pipeline", "evaluation", "injector") produce distinct seeds
3. **Index variation:** Same component with different indices produces different seeds
4. **Master seed variation:** Different master seeds produce entirely different seed families
5. **Range validation:** All seeds within `[0, 2^32-1]`
6. **Log verification:** Use `caplog` or loguru sink capture to verify INFO log

### Project Structure Notes

Files to create:
```
src/crossfire/shared/
├── seed_manager.py      # NEW

tests/shared/
├── test_seed_manager.py  # NEW
```

### References

- [Source: architecture.md#Seeding & Reproducibility]
- [Source: architecture.md#Logging]
- [Source: architecture.md#Enforcement Guidelines]
- [Source: architecture.md#Complete Project Directory Structure]
- [Source: epics.md#Story 1.3]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- Task 1: Created seed_manager.py with SeedManager class using hashlib.sha256 for cross-session deterministic seed derivation (not Python's hash() which is randomized). Logs master_seed at INFO via loguru.
- Task 2: 5 determinism tests — same seed/component/index produces identical results, different components/indices/master_seeds produce different seeds. Verified across 100 instantiations.
- Task 3: 4 edge case tests — index defaults to 0, seeds within 32-bit range, loguru INFO captured, import verification.
- Task 4: Full suite of 70 tests pass (60 from Story 1.2 + 10 new). No regressions.
- All 7 acceptance criteria satisfied.

### File List

- src/crossfire/shared/seed_manager.py (new)
- tests/shared/test_seed_manager.py (new)

### Change Log

- 2026-04-06: Story 1.3 implemented — centralized SeedManager with hashlib-based deterministic seed derivation and 10 tests
