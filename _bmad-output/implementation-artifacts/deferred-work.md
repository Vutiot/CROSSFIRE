# Deferred Work

## Deferred from: code review of Epic 1 stories 1-1 through 1-4 (2026-04-06)

- No version pins in `requirements.txt` — unpinned deps risk breaking on major releases of openai, pydantic, networkx. Consider `pip-compile` or at minimum `>=x.y,<x+1` ranges for a future hardening pass.
- `EntityGraph.to_networkx()` always returns undirected `nx.Graph` — directional relationships like "caused_by" or "preceded_by" silently lose direction. Consider switching to `nx.DiGraph` if any Epic 2+ component requires directed traversal.
- `ScopeDistribution` and `DetectabilityDistribution` have no sum-to-1.0 validation — invalid distributions pass silently and cause skewed benchmark sampling. Add `@model_validator` to both classes.
- `_usage` dict in `llm.py` is not thread-safe — concurrent LLM calls (expected in Epic 4 parallel pipeline runs) will corrupt token counts. Protect with `threading.Lock` before adding concurrency.
- `get_usage_summary()` always applies `_DEFAULT_PRICING` (gpt-4o-mini rates) regardless of which model generated the tokens — cost is wrong if any non-default model is used. Full fix requires per-model token accumulation in `_usage`.
