"""Thin LLM wrapper — single function for all OpenAI API interactions."""

import time

import openai
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

_client = None

# Module-level usage tracking
_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

# Approximate pricing per 1M tokens (GPT-4o-mini)
_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}
_DEFAULT_PRICING = {"input": 0.15, "output": 0.60}


def _get_client() -> openai.OpenAI:
    global _client
    if _client is None:
        _client = openai.OpenAI()
    return _client


def llm_call(
    prompt: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0,
    dry_run: bool = False,
) -> tuple[str | None, str | None]:
    """Call the OpenAI API and return (response_text, error).

    Returns (response_text, None) on success, (None, error_message) on failure.
    In dry_run mode, returns (estimate_string, None) without calling the API.
    """
    if dry_run:
        return _estimate_cost(prompt, model)

    client = _get_client()
    pricing = _PRICING.get(model, _DEFAULT_PRICING)

    last_error = None
    for attempt in range(4):  # 1 initial + 3 retries
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            text = response.choices[0].message.content
            if response.usage:
                _usage["prompt_tokens"] += response.usage.prompt_tokens
                _usage["completion_tokens"] += response.usage.completion_tokens
                _usage["total_tokens"] += response.usage.total_tokens
            return text, None

        except openai.RateLimitError as e:
            last_error = str(e)
            if attempt < 3:
                wait = 2**attempt  # 1s, 2s, 4s
                logger.warning(f"Rate limit hit, retrying in {wait}s (attempt {attempt + 1}/3)")
                time.sleep(wait)
            else:
                logger.error(f"Rate limit exceeded after 3 retries: {last_error}")
                return None, f"Rate limit exceeded after 3 retries: {last_error}"

        except openai.AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            return None, f"Authentication error: {e}"

        except openai.APIError as e:
            logger.error(f"API error: {e}")
            return None, f"API error: {e}"

    return None, f"Failed after retries: {last_error}"


def _estimate_cost(prompt: str, model: str) -> tuple[str, None]:
    """Estimate token count and cost without calling the API."""
    estimated_tokens = len(prompt) // 4
    pricing = _PRICING.get(model, _DEFAULT_PRICING)
    estimated_cost = (estimated_tokens / 1_000_000) * pricing["input"]
    estimate = (
        f"Dry-run estimate: ~{estimated_tokens} input tokens, "
        f"~${estimated_cost:.4f} estimated input cost (model: {model})"
    )
    logger.info(estimate)
    return estimate, None


def get_usage_summary() -> dict:
    """Return accumulated token usage and estimated cost."""
    pricing = _DEFAULT_PRICING
    input_cost = (_usage["prompt_tokens"] / 1_000_000) * pricing["input"]
    output_cost = (_usage["completion_tokens"] / 1_000_000) * pricing["output"]
    return {
        "prompt_tokens": _usage["prompt_tokens"],
        "completion_tokens": _usage["completion_tokens"],
        "total_tokens": _usage["total_tokens"],
        "estimated_cost_usd": round(input_cost + output_cost, 6),
    }


def log_usage_summary() -> None:
    """Log accumulated usage at INFO level."""
    summary = get_usage_summary()
    logger.info(
        f"LLM usage — prompt: {summary['prompt_tokens']}, "
        f"completion: {summary['completion_tokens']}, "
        f"total: {summary['total_tokens']}, "
        f"estimated cost: ${summary['estimated_cost_usd']:.4f}"
    )


def reset_usage() -> None:
    """Reset accumulated usage tracking."""
    _usage["prompt_tokens"] = 0
    _usage["completion_tokens"] = 0
    _usage["total_tokens"] = 0
