"""Tests for the thin LLM wrapper with mocked OpenAI client."""

import io
from unittest.mock import MagicMock, patch

import openai
import pytest
from loguru import logger

from crossfire.shared import llm
from crossfire.shared.llm import llm_call, get_usage_summary, log_usage_summary, reset_usage


def _mock_response(content="Generated text", prompt_tokens=10, completion_tokens=20):
    """Create a mock OpenAI ChatCompletion response."""
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    resp.usage.prompt_tokens = prompt_tokens
    resp.usage.completion_tokens = completion_tokens
    resp.usage.total_tokens = prompt_tokens + completion_tokens
    return resp


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset module state before each test."""
    reset_usage()
    llm._client = None
    yield
    reset_usage()
    llm._client = None


class TestLlmCallSuccess:
    @patch.object(llm, "_get_client")
    def test_successful_call_returns_text(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_response("Hello world")
        mock_get_client.return_value = mock_client

        text, error = llm_call("Say hello")
        assert text == "Hello world"
        assert error is None

    @patch.object(llm, "_get_client")
    def test_calls_openai_with_correct_params(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_response()
        mock_get_client.return_value = mock_client

        llm_call("Test prompt", model="gpt-4o-mini", temperature=0.5)
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Test prompt"}],
            temperature=0.5,
        )


class TestUsageTracking:
    @patch.object(llm, "_get_client")
    def test_tokens_accumulated(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_response(
            prompt_tokens=10, completion_tokens=20
        )
        mock_get_client.return_value = mock_client

        llm_call("First call")
        llm_call("Second call")

        summary = get_usage_summary()
        assert summary["prompt_tokens"] == 20
        assert summary["completion_tokens"] == 40
        assert summary["total_tokens"] == 60

    @patch.object(llm, "_get_client")
    def test_get_usage_summary_cost(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_response(
            prompt_tokens=1_000_000, completion_tokens=1_000_000
        )
        mock_get_client.return_value = mock_client

        llm_call("Big prompt")
        summary = get_usage_summary()
        # Input: 1M tokens * $0.15/1M = $0.15
        # Output: 1M tokens * $0.60/1M = $0.60
        assert summary["estimated_cost_usd"] == 0.75

    @patch.object(llm, "_get_client")
    def test_log_usage_summary(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_response(
            prompt_tokens=100, completion_tokens=50
        )
        mock_get_client.return_value = mock_client

        llm_call("Test")

        sink = io.StringIO()
        handler_id = logger.add(sink, format="{message}", level="INFO")
        try:
            log_usage_summary()
            output = sink.getvalue()
            assert "prompt: 100" in output
            assert "completion: 50" in output
            assert "total: 150" in output
        finally:
            logger.remove(handler_id)

    @patch.object(llm, "_get_client")
    def test_reset_usage(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_response()
        mock_get_client.return_value = mock_client

        llm_call("Test")
        reset_usage()
        summary = get_usage_summary()
        assert summary["prompt_tokens"] == 0
        assert summary["completion_tokens"] == 0
        assert summary["total_tokens"] == 0


class TestDryRun:
    def test_dry_run_returns_estimate(self):
        text, error = llm_call("A test prompt for estimation", dry_run=True)
        assert error is None
        assert "Dry-run estimate" in text
        assert "input tokens" in text
        assert "estimated input cost" in text

    def test_dry_run_no_api_call(self):
        # No client setup — if it tried to call API it would fail
        llm._client = None
        text, error = llm_call("Test", dry_run=True)
        assert error is None

    def test_dry_run_does_not_track_usage(self):
        llm_call("Test prompt", dry_run=True)
        summary = get_usage_summary()
        assert summary["total_tokens"] == 0


class TestRetryLogic:
    @patch("time.sleep")
    @patch.object(llm, "_get_client")
    def test_rate_limit_retries_then_succeeds(self, mock_get_client, mock_sleep):
        mock_client = MagicMock()
        rate_limit_error = openai.RateLimitError(
            message="Rate limit", response=MagicMock(status_code=429), body={}
        )
        mock_client.chat.completions.create.side_effect = [
            rate_limit_error,
            rate_limit_error,
            _mock_response("Success after retry"),
        ]
        mock_get_client.return_value = mock_client

        text, error = llm_call("Test")
        assert text == "Success after retry"
        assert error is None
        assert mock_sleep.call_count == 2

    @patch("time.sleep")
    @patch.object(llm, "_get_client")
    def test_rate_limit_exhausts_retries(self, mock_get_client, mock_sleep):
        mock_client = MagicMock()
        rate_limit_error = openai.RateLimitError(
            message="Rate limit", response=MagicMock(status_code=429), body={}
        )
        mock_client.chat.completions.create.side_effect = rate_limit_error
        mock_get_client.return_value = mock_client

        text, error = llm_call("Test")
        assert text is None
        assert "Rate limit exceeded after 3 retries" in error
        assert mock_sleep.call_count == 3

    @patch.object(llm, "_get_client")
    def test_auth_error_no_retry(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.AuthenticationError(
            message="Invalid API key", response=MagicMock(status_code=401), body={}
        )
        mock_get_client.return_value = mock_client

        text, error = llm_call("Test")
        assert text is None
        assert "Authentication error" in error
        # Should only be called once — no retries
        assert mock_client.chat.completions.create.call_count == 1

    @patch.object(llm, "_get_client")
    def test_api_error_no_retry(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.APIError(
            message="Server error", request=MagicMock(), body={}
        )
        mock_get_client.return_value = mock_client

        text, error = llm_call("Test")
        assert text is None
        assert "API error" in error
        assert mock_client.chat.completions.create.call_count == 1


class TestImport:
    def test_importable(self):
        from crossfire.shared.llm import llm_call as lc
        assert lc is llm_call
