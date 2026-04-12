# Story 1.4: Thin LLM Wrapper

Status: review

## Story

As a developer,
I want a single function for all LLM API interactions with cost tracking and dry-run mode,
so that all generation goes through one controlled, auditable interface.

## Acceptance Criteria

1. `llm_call` function exists in `src/crossfire/shared/llm.py`
2. Calling `llm_call(prompt, model="gpt-4o-mini", temperature=0)` calls the OpenAI API and returns `(response_text, error)` tuple
3. The API key is loaded from `.env` via python-dotenv
4. Token usage is tracked and accumulated across calls
5. Total cost is loggable at INFO level at any point
6. Calling `llm_call(prompt, dry_run=True)` returns estimated token count and cost without making an API call
7. Rate limit errors retry with exponential backoff up to 3 times
8. Auth or quota errors return immediately with `(None, error_message)` — no retry

## Tasks / Subtasks

- [x] Task 1: Create `src/crossfire/shared/llm.py` with core `llm_call` function (AC: #1, #2, #3)
  - [x] Load API key from `.env` via python-dotenv at module level
  - [x] Implement `llm_call(prompt, model, temperature, dry_run)` returning `(response_text, error)` tuple
  - [x] Create OpenAI client and call `chat.completions.create` with the prompt as a user message
  - [x] Extract response text from `response.choices[0].message.content`

- [x] Task 2: Add cost tracking (AC: #4, #5)
  - [x] Create module-level `_usage_tracker` dict accumulating `prompt_tokens`, `completion_tokens`, `total_tokens`
  - [x] After each successful API call, add token counts from `response.usage`
  - [x] Implement `get_usage_summary() -> dict` returning accumulated tokens and estimated cost
  - [x] Implement `log_usage_summary()` that logs the summary at INFO via loguru
  - [x] Implement `reset_usage()` to zero out tracking between runs

- [x] Task 3: Add dry-run mode (AC: #6)
  - [x] When `dry_run=True`, estimate token count from prompt length (~4 chars per token)
  - [x] Calculate estimated cost based on model pricing
  - [x] Return `(estimate_string, None)` without making an API call
  - [x] Log the estimate at INFO level

- [x] Task 4: Add retry logic for transient errors (AC: #7, #8)
  - [x] Catch `openai.RateLimitError` — retry up to 3 times with exponential backoff (1s, 2s, 4s)
  - [x] Catch `openai.AuthenticationError` — return `(None, error_message)` immediately, no retry
  - [x] Catch `openai.APIError` for other API errors — return `(None, error_message)` immediately
  - [x] Log retries at WARNING level, failures at ERROR level

- [x] Task 5: Write tests with mocked OpenAI client (AC: #1-#8)
  - [x] Test: successful API call returns `(response_text, None)`
  - [x] Test: token usage is accumulated across calls
  - [x] Test: dry_run returns estimate without API call
  - [x] Test: rate limit error triggers retry (mock 429 then success)
  - [x] Test: auth error returns immediately with error message
  - [x] Test: get_usage_summary returns correct totals
  - [x] Test: reset_usage zeros out tracking

- [x] Task 6: Run full test suite — no regressions
  - [x] Verify all 70 existing tests still pass
  - [x] Verify `llm_call` is importable with `PYTHONPATH=src`

## Dev Notes

### Architecture Compliance (CRITICAL)

**Function signature from architecture:**

```python
def llm_call(prompt, model="gpt-4o-mini", temperature=0, dry_run=False):
    # Returns (response_text, error) tuple
```

[Source: architecture.md#LLM Integration]

**Error handling pattern:** Return-value errors for expected failures. `(None, error_message)` on failure, `(response_text, None)` on success.
[Source: architecture.md#Error Handling]

**Logging:** Use loguru — no print() statements.
[Source: architecture.md#Logging]

### OpenAI SDK v2 API Pattern

The project uses `openai>=2.0` (v2 SDK with client-based API). The correct pattern:

```python
from openai import OpenAI
import openai

client = OpenAI()  # reads OPENAI_API_KEY from environment

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    temperature=0,
)
text = response.choices[0].message.content
tokens = response.usage  # CompletionUsage(prompt_tokens=X, completion_tokens=Y, total_tokens=Z)
```

**Error types in openai v2:**
- `openai.RateLimitError` — 429, should retry
- `openai.AuthenticationError` — 401, don't retry
- `openai.APIError` — base class for other API errors, don't retry

### API Key Loading

Use python-dotenv to load `.env` at module level:

```python
from dotenv import load_dotenv
load_dotenv()
```

This makes `OPENAI_API_KEY` available in environment. The OpenAI client reads it automatically.
[Source: architecture.md#Gaps Resolved — API key management via python-dotenv]

### Cost Estimation (Dry-Run)

Approximate GPT-4o-mini pricing for cost estimates:
- Input: ~$0.15 per 1M tokens
- Output: ~$0.60 per 1M tokens
- Token estimate: ~4 characters per token (rough heuristic)

These are estimates — exact pricing changes over time. The dry-run mode is for ballpark cost prediction, not exact billing.

### Retry Logic

Exponential backoff for rate limits only:
- Attempt 1: immediate
- Retry 1: wait 1s
- Retry 2: wait 2s
- Retry 3: wait 4s
- After 3 retries: return `(None, error_message)`

Use `time.sleep()` for backoff delays.

### Testing Strategy — Mocking OpenAI

Tests MUST mock the OpenAI client — never call the real API. Use `unittest.mock.patch` or `monkeypatch`.

**Mock pattern for successful call:**
```python
from unittest.mock import MagicMock, patch

mock_response = MagicMock()
mock_response.choices = [MagicMock()]
mock_response.choices[0].message.content = "Generated text"
mock_response.usage.prompt_tokens = 10
mock_response.usage.completion_tokens = 20
mock_response.usage.total_tokens = 30
```

**Mock pattern for rate limit:**
```python
import openai
with patch.object(client, 'chat') as mock_chat:
    mock_chat.completions.create.side_effect = openai.RateLimitError(
        message="Rate limit exceeded", response=MagicMock(status_code=429), body={}
    )
```

Test file: `tests/shared/test_llm.py`

### Previous Story Learnings

- SeedManager uses `hashlib.sha256` for determinism — LLM wrapper doesn't need SeedManager directly (temperature=0 handles LLM determinism)
- Tests run with `PYTHONPATH=src pytest`
- 70 existing tests pass — do not break them
- loguru is the logging library (imported as `from loguru import logger`)

### Anti-Patterns to Avoid

- Do NOT use `print()` — use loguru
- Do NOT make the OpenAI client global/singleton — create it lazily or at module level after dotenv load
- Do NOT retry on auth/quota errors — only rate limits
- Do NOT silently swallow errors — always return error messages
- Do NOT add multi-model provider abstraction — that's Phase 2
- Do NOT add async support — keep synchronous for MVP
- Do NOT pin OpenAI model versions (e.g., don't use "gpt-4o-mini-2024-07-18") — use the base model name

### Project Structure Notes

Files to create:
```
src/crossfire/shared/
├── llm.py               # NEW

tests/shared/
├── test_llm.py           # NEW
```

### References

- [Source: architecture.md#LLM Integration]
- [Source: architecture.md#Error Handling]
- [Source: architecture.md#Logging]
- [Source: architecture.md#Enforcement Guidelines]
- [Source: epics.md#Story 1.4]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- Task 1: Created llm.py with `llm_call()` function using OpenAI v2 SDK. Loads .env via python-dotenv, lazy-initializes client, returns (response_text, error) tuple per architecture pattern.
- Task 2: Module-level `_usage` dict tracks prompt/completion/total tokens across calls. `get_usage_summary()` returns totals + estimated cost, `log_usage_summary()` logs at INFO, `reset_usage()` zeros out.
- Task 3: Dry-run mode estimates ~4 chars/token, calculates cost from model pricing table, returns estimate string without API call.
- Task 4: Exponential backoff (1s, 2s, 4s) on `RateLimitError` up to 3 retries. `AuthenticationError` and `APIError` return immediately with error — no retry. Retries logged at WARNING, failures at ERROR.
- Task 5: 14 tests with mocked OpenAI client covering success, usage tracking, dry-run, retry logic, auth errors, and import verification.
- Task 6: Full suite of 84 tests pass (70 existing + 14 new). No regressions.
- All 8 acceptance criteria satisfied.

### File List

- src/crossfire/shared/llm.py (new)
- tests/shared/test_llm.py (new)

### Review Findings

- [x] [Review][Patch] Dead pricing variable in llm_call — removed unused `pricing` assignment from call path
- [x] [Review][Patch] response.choices is never guarded for emptiness — already fixed with empty-choices guard + retry
- [x] [Review][Patch] response.choices[0].message.content can be None (e.g. tool-call response) — added explicit None check returning error tuple
- [x] [Review][Patch] Post-loop return None on line 80 is dead code — kept as safety fallback with descriptive error message
- [x] [Review][Defer] get_usage_summary() hardcodes _DEFAULT_PRICING regardless of which model generated tokens — inaccurate cost for non-default models [llm.py:98] — deferred, requires per-model token tracking; larger change for future story
- [x] [Review][Defer] _usage dict not thread-safe — will corrupt under concurrent LLM calls [llm.py:14] — deferred, MVP is synchronous per spec

### Change Log

- 2026-04-06: Story 1.4 implemented — thin LLM wrapper with cost tracking, dry-run mode, exponential backoff retry, and 14 mocked tests
- 2026-04-10: Resolved 4 review findings — removed dead pricing var, added None content guard, fixed test for configurable retry count (LLM_MAX_RETRIES env var)
